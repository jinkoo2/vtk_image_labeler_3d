"""Launch a staged ImageLabeler3D build with --smoke-test and enforce success."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage_dir", type=Path, help="Staged onedir package directory")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--xvfb",
        action="store_true",
        help="Wrap the launch with xvfb-run -a (Linux CI)",
    )
    args = parser.parse_args()

    stage = args.stage_dir.resolve()
    if sys.platform.startswith("win"):
        exe = stage / "ImageLabeler3D.exe"
    else:
        exe = stage / "ImageLabeler3D"

    if not exe.exists():
        print(f"Missing frozen executable: {exe}", file=sys.stderr)
        return 2

    result = stage / "smoke_result.txt"
    if result.exists():
        result.unlink()

    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    cmd = [str(exe), "--smoke-test"]
    if args.xvfb:
        cmd = ["xvfb-run", "-a", *cmd]

    print("Running:", " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=str(stage), env=env)
    try:
        rc = proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        print(f"Smoke test timed out after {args.timeout}s", file=sys.stderr)
        return 1

    if result.exists():
        print(result.read_text(encoding="utf-8", errors="replace"), end="", flush=True)
    else:
        print("smoke_result.txt was not written", file=sys.stderr)

    if rc != 0:
        print(f"Smoke test exit code: {rc}", file=sys.stderr)
        return rc or 1

    if not result.exists() or "SMOKE_OK" not in result.read_text(encoding="utf-8", errors="replace"):
        print("Smoke test did not report SMOKE_OK", file=sys.stderr)
        return 1

    print("Smoke test passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
