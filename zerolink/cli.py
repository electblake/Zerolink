from __future__ import annotations

from pathlib import Path
from typing import Optional
from importlib.metadata import PackageNotFoundError, version as _pkg_version
import typer

from .link_command import link_command as _link
from .db import (
    init_db,
    get_user_setting,
    set_user_setting,
    list_user_settings,
    remove_user_setting,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)

# Sub-CLI: settings
settings_app = typer.Typer(help="Manage user settings")


@settings_app.command("list")
def settings_list() -> None:
    """List all settings as KEY=VALUE."""
    data = list_user_settings()
    for k in sorted(data.keys()):
        typer.echo(f"{k}={data[k]}")


@settings_app.command("get")
def settings_get(name: str) -> None:
    """Get a setting by key."""
    val = get_user_setting(name)
    if val is None:
        err = typer.style("[not found]", fg=typer.colors.YELLOW)
        typer.echo(f"{err} {name}")
        raise typer.Exit(code=1)
    typer.echo(val)


@settings_app.command("set")
def settings_set(name: str, value: str) -> None:
    """Set a KEY to VALUE."""
    set_user_setting(name, value)
    ok = typer.style("[ok]", fg=typer.colors.GREEN)
    typer.echo(f"{ok} {name}={value}")


@settings_app.command("rm")
def settings_remove(name: str) -> None:
    """Remove a setting by key."""
    if remove_user_setting(name):
        ok = typer.style("[ok]", fg=typer.colors.GREEN)
        typer.echo(f"{ok} removed {name}")
    else:
        warn = typer.style("[warn]", fg=typer.colors.YELLOW)
        typer.echo(f"{warn} {name} not set")


app.add_typer(settings_app, name="settings")

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


def _init_callback(value: Optional[bool]) -> None:
    if value:
        path = init_db()
        ok = typer.style("[ok]", fg=typer.colors.GREEN)
        info = typer.style("[info]", fg=typer.colors.BRIGHT_BLACK)
        typer.echo(f"{ok} database initialized")
        typer.echo(f"{info} path: {path}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
    init: Optional[bool] = typer.Option(
        None,
        "--init",
        help="Initialize local database and exit",
        callback=_init_callback,
        is_eager=True,
    ),
) -> None:
    """Zero CLI root. Use subcommands like `link` or `settings`."""
    if ctx.invoked_subcommand:
        return
    # No subcommand -> show help
    typer.echo(ctx.get_help())
    raise typer.Exit()


@app.command("link")
def link(
    src: Path = typer.Argument(..., help="Target directory the link should point to"),
    dst: Path = typer.Argument(..., help="Path where symlink should be created/replace"),
) -> None:
    """Create or replace a symlink at DST pointing to SRC."""
    _link(src=src, dst=dst)
