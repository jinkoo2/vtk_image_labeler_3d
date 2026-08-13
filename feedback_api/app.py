"""Feedback proxy: desktop app -> this API -> GitHub Issues.

Deploy on CapRover. Set env vars (see README). Users never need a GitHub account;
AI agents continue to triage Issues in the target repo.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Literal, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_OWNER = _env("GITHUB_OWNER", "jinkoo2")
GITHUB_REPO = _env("GITHUB_REPO", "vtk_image_labeler_3d")
# Optional shared secret. If set, clients must send header X-Feedback-Key.
FEEDBACK_API_KEY = _env("FEEDBACK_API_KEY")
RATE_LIMIT_PER_HOUR = int(_env("RATE_LIMIT_PER_HOUR", "20") or "20")
GITHUB_API = _env("GITHUB_API", "https://api.github.com")

KIND_LABELS = {
    "bug": ["bug", "from-app", "needs-triage"],
    "feature": ["enhancement", "from-app", "needs-triage"],
}

app = FastAPI(
    title="Image Labeler 3D Feedback API",
    version="1.0.0",
    description="Creates GitHub Issues from in-app feedback (no user GitHub login).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Simple in-memory rate limit: IP -> timestamps of recent posts
_hits: Dict[str, Deque[float]] = defaultdict(deque)


class FeedbackIn(BaseModel):
    kind: Literal["bug", "feature"]
    title: str = Field(min_length=3, max_length=200)
    details: str = Field(min_length=3, max_length=20000)
    contact_email: Optional[str] = Field(default=None, max_length=200)
    app_version: Optional[str] = Field(default=None, max_length=64)
    os: Optional[str] = Field(default=None, max_length=256)
    python_version: Optional[str] = Field(default=None, max_length=64)
    platform: Optional[str] = Field(default=None, max_length=128)


class FeedbackOut(BaseModel):
    ok: bool
    issue_number: int
    issue_url: str
    html_url: str


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _rate_limit(ip: str) -> None:
    now = time.time()
    window = 3600.0
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({RATE_LIMIT_PER_HOUR}/hour). Try again later.",
        )
    q.append(now)


def _check_api_key(x_feedback_key: Optional[str]) -> None:
    if not FEEDBACK_API_KEY:
        return
    if (x_feedback_key or "").strip() != FEEDBACK_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Feedback-Key")


def _build_issue_body(payload: FeedbackIn) -> str:
    kind_title = "Bug report" if payload.kind == "bug" else "Feature request"
    contact = (payload.contact_email or "").strip() or "_not provided_"
    details = payload.details.strip()
    return f"""## {kind_title}

### Summary
{payload.title.strip()}

### Details
{details}

### Contact
{contact}

### Environment
- App version: `{payload.app_version or "unknown"}`
- OS: `{payload.os or "unknown"}`
- Python: `{payload.python_version or "unknown"}`
- Platform: `{payload.platform or "unknown"}`

### Agent notes
- Label `needs-triage` until investigated.
- After fix: comment what changed (PR/commit), then close with `Fixes #<n>` or remove `needs-triage` and add `resolved`.

---
_Submitted via Image Labeler 3D feedback API (user has no GitHub login)._
"""


@app.get("/health")
def health():
    return {
        "ok": True,
        "github_configured": bool(GITHUB_TOKEN),
        "owner": GITHUB_OWNER,
        "repo": GITHUB_REPO,
        "api_key_required": bool(FEEDBACK_API_KEY),
        "rate_limit_per_hour": RATE_LIMIT_PER_HOUR,
    }


@app.post("/api/v1/feedback", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackIn,
    request: Request,
    x_feedback_key: Optional[str] = Header(default=None, alias="X-Feedback-Key"),
):
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN is not configured on the server")

    _check_api_key(x_feedback_key)
    _rate_limit(_client_ip(request))

    title_prefix = "[Bug] " if payload.kind == "bug" else "[Feature] "
    title = title_prefix + payload.title.strip()
    labels = KIND_LABELS[payload.kind]
    body = _build_issue_body(payload)

    url = f"{GITHUB_API.rstrip('/')}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vtk-image-labeler-3d-feedback-api",
    }
    data = {"title": title, "body": body, "labels": labels}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=data)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub request failed: {exc}") from exc

    if resp.status_code == 403:
        raise HTTPException(status_code=502, detail=f"GitHub forbidden: {resp.text[:500]}")
    if resp.status_code == 401:
        raise HTTPException(status_code=502, detail="GitHub token rejected (401)")
    if resp.status_code >= 400:
        # Label may not exist yet — retry without labels once.
        if resp.status_code == 422 and "label" in resp.text.lower():
            data.pop("labels", None)
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=data)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"GitHub error {resp.status_code}: {resp.text[:800]}",
            )

    issue = resp.json()
    html_url = issue.get("html_url") or ""
    number = int(issue.get("number") or 0)
    return FeedbackOut(ok=True, issue_number=number, issue_url=html_url, html_url=html_url)
