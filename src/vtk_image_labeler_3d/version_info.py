"""Application version helpers."""

from __future__ import annotations

import re
from pathlib import Path

# Keep in sync with pyproject.toml [project].version when bumping releases.
VERSION = "0.1.10"
GITHUB_OWNER = "jinkoo2"
GITHUB_REPO = "vtk_image_labeler_3d"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


def _version_from_pyproject() -> str | None:
    """Read version from the nearest pyproject.toml (source / editable checkout)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        pyproject = parent / "pyproject.toml"
        if not pyproject.exists():
            continue
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(
            r'(?m)^version\s*=\s*["\']([^"\']+)["\']',
            text,
        )
        if match:
            return match.group(1)
        return None
    return None


def _version_from_package_metadata() -> str | None:
    try:
        from importlib.metadata import version

        return version("vtk-image-labeler-3d")
    except Exception:
        return None


def get_version() -> str:
    """Return the app version string.

    For `poetry run app` / source checkouts, prefer pyproject.toml (and the
    VERSION constant) so bumping the version does not require reinstalling the
    package. Installed / frozen builds still use package metadata when no
    pyproject.toml is nearby.
    """
    from_pyproject = _version_from_pyproject()
    if from_pyproject:
        return from_pyproject

    from_meta = _version_from_package_metadata()
    if from_meta:
        return from_meta

    return VERSION
