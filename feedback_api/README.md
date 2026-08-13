# Feedback API (CapRover → GitHub Issues)

Small FastAPI service: the desktop app POSTs feedback here; this service creates a
GitHub Issue with a bot token. End users never log into GitHub. AI agents keep
using the repo Issues (`gh`, Cursor, MCP).

## CapRover deploy

1. Create a new CapRover app (e.g. `labeler-feedback`).
2. Enable HTTPS on a hostname (e.g. `labeler-feedback.apps.example.com`).
3. **App Configs → Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | yes | Fine-grained PAT or classic token with `issues: write` on the repo |
| `GITHUB_OWNER` | no | Default `jinkoo2` |
| `GITHUB_REPO` | no | Default `vtk_image_labeler_3d` |
| `FEEDBACK_API_KEY` | recommended | Shared secret; client sends `X-Feedback-Key` |
| `RATE_LIMIT_PER_HOUR` | no | Default `20` |

4. Deploy method: **Method 1 tarball** of this `feedback_api/` folder, or git deploy
   with captain-definition pointing at this directory.
5. Check `GET https://<host>/health` → `"ok": true`, `"github_configured": true`.

### GitHub token

Create a fine-grained PAT (or GitHub App installation token) with:
- Repository access: `vtk_image_labeler_3d`
- Permissions: **Issues: Read and write**

Optional: create labels `from-app`, `needs-triage`, `resolved` in the repo
(API will still work if labels are missing — it retries without labels).

## Desktop app settings

In `settings.json` / Preferences:

```json
{
  "feedback_api_url": "https://labeler-feedback.apps.example.com",
  "feedback_api_key": "same-as-FEEDBACK_API_KEY"
}
```

`feedback_api_url` should be the **origin only** (no `/api/v1/feedback` suffix).

## Test

```bash
curl -sS -X POST "https://HOST/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "X-Feedback-Key: YOUR_KEY" \
  -d '{"kind":"bug","title":"API smoke test","details":"Ignore — deploy check.","app_version":"0.0.0"}'
```

## Agent workflow

1. Watch Issues with label `from-app` / `needs-triage`.
2. Fix in a PR referencing `Fixes #<n>`.
3. Comment what changed; close or label `resolved`.
