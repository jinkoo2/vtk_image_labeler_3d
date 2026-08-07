# Packaging

Build locally:

```bash
poetry install
poetry run python -m pip install "pyinstaller>=6.3,<7"
poetry run pyinstaller packaging/app.spec --noconfirm --clean
```

Output: `dist/ImageLabeler3D/`

GitHub Releases are produced by `.github/workflows/release.yml` when you push a tag such as `v0.1.0`.

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then download artifacts from the repository **Releases** page.

Release artifacts (from the workflow matrix):

- `ImageLabeler3D-windows-x64.zip`
- `ImageLabeler3D-linux-x64.tar.gz`
- `ImageLabeler3D-macos-arm64.tar.gz` (Apple Silicon)
- `ImageLabeler3D-macos-x64.tar.gz` (Intel Mac)

Release workflows:

1. **Release (Primary Platforms)** — Windows x64, Linux x64, macOS arm64 (publishes the GitHub Release).
2. **Release (macOS x64)** — starts after (1) succeeds and appends the Intel Mac package to the same release.

