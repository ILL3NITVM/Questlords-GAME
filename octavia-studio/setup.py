#!/usr/bin/env python3
"""Cross-platform setup, for environments without bash.

    python setup.py

Prefers the vendored wheels in vendor/wheels/ and falls back to PyPI when
they do not match this platform.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def run(args: list[str]) -> int:
    return subprocess.call([sys.executable, "-m", "pip"] + args)


def main() -> int:
    print("Octavia Studio setup")
    print(f"  python: {sys.version.split()[0]}  ({sys.platform})")

    wheels = ROOT / "vendor" / "wheels"
    req = str(ROOT / "requirements.txt")
    installed = False

    if wheels.is_dir() and any(wheels.iterdir()):
        print("  trying vendored wheels (offline)...")
        code = run(["install", "--quiet", "--no-index",
                    "--find-links", str(wheels), "-r", req])
        if code == 0:
            print("  installed from vendor/wheels")
            installed = True
        else:
            print("  vendored wheels do not match this platform; "
                  "falling back to PyPI")

    if not installed:
        if run(["install", "--quiet", "-r", req]) != 0:
            print("  install failed", file=sys.stderr)
            return 1

    try:
        import PIL
        import yaml
        print(f"\n  PyYAML {yaml.__version__} | Pillow {PIL.__version__}")
    except ImportError as exc:
        print(f"\n  verification failed: {exc}", file=sys.stderr)
        return 1

    print("\nNext:")
    print("  python studio.py doctor")
    print("  python studio.py generate --count 8        # mock renderer, zero cost")
    print("  python -m pytest tests/ -q -m 'not slow'")
    print("\nThe local rendering backend is optional and large:")
    print("  pip install -r requirements-local.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
