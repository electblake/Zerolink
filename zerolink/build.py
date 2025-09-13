from __future__ import annotations

import sys
from typing import Sequence


def main(cli_args: Sequence[str] | None = None) -> int:
    """Build a portable Windows exe via PyInstaller.

    Usage (with uv dev deps):
      uv run --group dev build-zerolink

    Extra args are passed to PyInstaller, e.g.:
      uv run --group dev build-zerolink -- --clean --noconsole
    """
    try:
        from PyInstaller.__main__ import run as pyinstaller_run
    except Exception as exc:  # pragma: no cover
        print("PyInstaller is not installed. Install dev deps with:"
              "\n  uv sync --group dev", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        return 1

    opts: list[str] = [
        "--onefile",
        "--name",
        "zerolink",
        "run_zerolink.py",
    ]
    if cli_args:
        # Allow extra flags after a "--" when invoked via uv run
        opts.extend(cli_args)

    try:
        pyinstaller_run(opts)
        return 0
    except SystemExit as e:  # PyInstaller may call sys.exit
        return int(e.code) if e.code is not None else 0
    except Exception as e:  # pragma: no cover
        print(f"Build failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

