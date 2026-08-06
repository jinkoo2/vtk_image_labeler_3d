"""Check GitHub Releases for a newer app version."""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass
from typing import Optional

import requests

from version_info import GITHUB_OWNER, GITHUB_REPO, GITHUB_RELEASES_URL, get_version


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    release_url: str
    asset_name: Optional[str]
    asset_url: Optional[str]
    body: str = ""

    @property
    def available(self) -> bool:
        return _version_tuple(self.latest_version) > _version_tuple(self.current_version)


def _version_tuple(version: str):
    """Parse loose semver-ish tags like v0.1.2-beta into comparable tuples."""
    text = (version or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    text = text.split("+", 1)[0]
    # Keep only leading numeric dotted part for comparison.
    match = re.match(r"^(\d+(?:\.\d+)*)", text)
    if not match:
        return (0,)
    parts = []
    for bit in match.group(1).split("."):
        try:
            parts.append(int(bit))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _platform_asset_preferences():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system.startswith("win"):
        return ("windows", ".zip")
    if system == "darwin":
        # Prefer arm64 artifact name on Apple Silicon runners/builds.
        if "arm" in machine or "aarch64" in machine:
            return ("macos-arm64", ".tar.gz")
        return ("macos", ".tar.gz")
    return ("linux", ".tar.gz")


def _pick_asset(assets: list) -> tuple[Optional[str], Optional[str]]:
    needle, ext = _platform_asset_preferences()
    names_urls = [
        (a.get("name") or "", a.get("browser_download_url") or "")
        for a in assets
        if a.get("browser_download_url")
    ]
    # Prefer name containing platform needle + extension
    for name, url in names_urls:
        lower = name.lower()
        if needle in lower and lower.endswith(ext):
            return name, url
    # Fallback: any matching extension with looser OS hint
    os_hints = {
        "windows": ("windows", "win"),
        "macos-arm64": ("macos", "darwin", "osx"),
        "macos": ("macos", "darwin", "osx"),
        "linux": ("linux", "ubuntu"),
    }
    hints = os_hints.get(needle, (needle,))
    for name, url in names_urls:
        lower = name.lower()
        if lower.endswith(ext) and any(h in lower for h in hints):
            return name, url
    if names_urls:
        return names_urls[0]
    return None, None


def fetch_latest_update(timeout_seconds: float = 8.0) -> UpdateInfo:
    """Query GitHub /releases/latest and compare against the running app version."""
    current = get_version()
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{GITHUB_REPO}-update-check/{current}",
    }
    response = requests.get(url, headers=headers, timeout=timeout_seconds)
    if response.status_code == 404:
        # No releases published yet
        return UpdateInfo(
            current_version=current,
            latest_version=current,
            release_name="",
            release_url=GITHUB_RELEASES_URL,
            asset_name=None,
            asset_url=None,
            body="No releases published yet.",
        )
    response.raise_for_status()
    data = response.json()
    tag = data.get("tag_name") or data.get("name") or current
    asset_name, asset_url = _pick_asset(data.get("assets") or [])
    return UpdateInfo(
        current_version=current,
        latest_version=tag,
        release_name=data.get("name") or tag,
        release_url=data.get("html_url") or GITHUB_RELEASES_URL,
        asset_name=asset_name,
        asset_url=asset_url,
        body=(data.get("body") or "")[:2000],
    )
