"""Application version helpers."""

from __future__ import annotations

import re
from pathlib import Path

# Keep in sync with pyproject.toml [project].version when bumping releases.
VERSION = "0.1.2"
GITHUB_OWNER = "jinkoo2"
GITHUB_REPO = "vtk_image_labeler_3d"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


def get_version() -> str:
    try:
        from importlib.metadata import version

        return version("vtk-image-labeler-3d")
    except Exception:
        pass

    # Source checkout: read pyproject.toml next to the repo root.
    try:
        here = Path(__file__).resolve()
        for parent in here.parents:
            pyproject = parent / "pyproject.toml"
            if pyproject.exists():
                text = pyproject.read_text(encoding="utf-8")
                match = re.search(
                    r'(?m)^version\s*=\s*["\']([^"\']+)["\']',
                    text,
                )
                if match:
                    return match.group(1)
                break
    except Exception:
        pass

    return VERSION
