from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .link_command import link_command as _link

try:  # Python 3.10+
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
except Exception:  # pragma: no cover
    from importlib_metadata import PackageNotFoundError, version as _pkg_version  # type: ignore


app = typer.Typer(no_args_is_help=True, add_completion=False)


def _get_version() -> str:
    # 1) If installed as a package, use distribution metadata
    try:
        return _pkg_version("zerolinks")
    except PackageNotFoundError:
        pass
    # 2) If a generated version module exists (e.g., during build), use it
    try:  # lazy import to avoid hard dependency
        from ._version import VERSION as _V  # type: ignore
        return str(_V)
    except Exception:
        pass
    # 3) Fallback: parse pyproject.toml nearby (dev checkout)
    try:
        import io, os, re
        text = io.open(os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"), "r", encoding="utf-8").read()
        m = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.M)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "0.0.0"


def _version_callback(value: Optional[bool]) -> None:
    if value:
        typer.echo(f"zero {_get_version()}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
    src: Path = typer.Argument(..., help="Target directory the link should point to"),
    dst: Path = typer.Argument(..., help="Path where symlink should be created/replace"),
) -> None:
    """Link raw 'zero' paths into a single source."""
    _link(src=src, dst=dst)
