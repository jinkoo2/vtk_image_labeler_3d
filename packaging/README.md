# Packaging

Build locally:

```bash
poetry install
poetry run pip install "pyinstaller>=6.3,<7"
poetry run pyinstaller packaging/app.spec --noconfirm --clean
```

Output: `dist/ImageLabeler3D/`

GitHub Releases are produced by `.github/workflows/release.yml` when you push a tag such as `v0.1.0`.

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then download artifacts from the repository **Releases** page.
