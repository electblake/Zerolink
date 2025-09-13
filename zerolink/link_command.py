from __future__ import annotations

import os
import shutil
from pathlib import Path

import typer


def _norm_src(p: Path | str) -> Path:
    # Resolve the source fully (real path)
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()


def _norm_dst(p: Path | str) -> Path:
    # Keep the link path as an absolute path without resolving symlinks
    return Path(os.path.abspath(os.path.expanduser(os.path.expandvars(str(p)))))


def _same_symlink(dst: Path, src: Path) -> bool:
    if not dst.is_symlink():
        return False
    try:
        target = Path(os.readlink(dst)).resolve()
    except OSError:
        return False
    return target == src.resolve()


def _echo_rule(src: Path, dst: Path, replaced: bool) -> None:
    src_s = typer.style(str(src), fg=typer.colors.GREEN)
    dst_s = typer.style(str(dst), fg=typer.colors.WHITE)
    suffix = " " + typer.style("replaced", fg=typer.colors.RED) if replaced else ""
    typer.echo(f"link: ({src_s}) => {dst_s}{suffix}")


def link_command(
    src: Path = typer.Argument(
        ..., help="Target directory the link should point to"
    ),
    dst: Path = typer.Argument(
        ..., help="Path where symlink should be created/replace"
    ),
) -> None:
    """Create or replace a symlink at dst pointing to src."""

    src_p = _norm_src(src)
    dst_p = _norm_dst(dst)

    if _same_symlink(dst_p, src_p):
        typer.echo("already linked; nothing to do")
        return

    # Preview
    _echo_rule(src_p, dst_p, replaced=dst_p.exists() or dst_p.is_symlink())

    if not typer.confirm("Proceed?"):
        typer.echo("aborted")
        return

    # Ensure parent exists
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    # Remove any existing file/dir/symlink
    if dst_p.exists() or dst_p.is_symlink():
        if dst_p.is_dir() and not dst_p.is_symlink():
            shutil.rmtree(dst_p)
        else:
            dst_p.unlink()

    # Create directory symlink
    os.symlink(str(src_p), str(dst_p), target_is_directory=True)
    typer.echo("done")
