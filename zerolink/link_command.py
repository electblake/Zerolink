from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

import typer

from .db import add_user_list_item, get_user_setting


def _norm_src(p: Path | str) -> Path:
    # Resolve the source fully (real path)
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()


def _norm_dst(p: Path | str) -> Path:
    # Keep the link path as an absolute path without resolving symlinks
    return Path(os.path.abspath(os.path.expanduser(os.path.expandvars(str(p)))))


def _same_symlink(dst: Path, src: Path) -> bool:
    """Return True if `dst` is a symlink pointing to `src`.

    Handles Windows/Unix differences, relative link targets, and case.
    """
    if not dst.is_symlink():
        return False

    raw_target = os.readlink(dst)

    # If the stored link target is relative, resolve it relative to the link's directory
    target_path = Path(raw_target)
    if not target_path.is_absolute():
        target_path = (dst.parent / target_path).resolve()
    else:
        target_path = target_path.resolve()

    # Prefer filesystem-level comparison to avoid casing/UNC differences
    return target_path.samefile(src)


def _remove_path(p: Path) -> None:
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


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

    # Read MRU cap from user settings (must be valid int)
    max_items = int(get_user_setting("max_src_history"))

    if _same_symlink(dst_p, src_p):
        # Bump history even if already linked
        add_user_list_item("src_history", str(src_p), max_items=max_items)
        typer.echo(f"{typer.style('[skip]', fg='cyan')} already linked; nothing to do")
        return

    # If destination exists as a real directory and has files, offer to move them to src via rclone
    if dst_p.is_dir() and not dst_p.is_symlink():
        file_count = sum(1 for p in dst_p.rglob('*') if p.is_file())
        if file_count > 0:
            warn = typer.style("[warn]", fg=typer.colors.YELLOW)
            typer.echo(f"{warn} destination directory contains {file_count} files")
            rclone_args = [
                "rclone",
                "move",
                "--progress",
                "--checksum",
                "--delete-empty-src-dirs",
                str(dst_p),
                str(src_p),
            ]
            pretty_cmd = ' '.join(
                [arg if ' ' not in arg else f'\"{arg}\"' for arg in rclone_args]
            )
            info = typer.style("[info]", fg=typer.colors.BRIGHT_BLACK)
            typer.echo(f"{info} proposed move: {pretty_cmd}")
            if typer.confirm("Run this rclone move before linking?"):
                subprocess.run(rclone_args, check=True)

    # Preview and confirmation
    exists = dst_p.exists() or dst_p.is_symlink()
    dst_type = (
        "directory" if dst_p.is_dir() and not dst_p.is_symlink() else
        "symlink" if dst_p.is_symlink() else
        "file" if exists else "missing"
    )
    plan = "replace" if exists else "create"
    src_s = typer.style(str(src_p), fg=typer.colors.GREEN)
    dst_s = typer.style(str(dst_p), fg=typer.colors.WHITE)
    prefix = typer.style("[plan]", fg=typer.colors.BRIGHT_BLACK)
    typer.echo(f"{prefix} {plan} symlink: {src_s} -> {dst_s}")
    if exists:
        info = typer.style("[info]", fg=typer.colors.BRIGHT_BLACK)
        typer.echo(f"{info} destination currently is a {dst_type}")

    question = (
        f"Replace existing {dst_type} with a symlink?" if exists else "Create symlink?"
    )
    if not typer.confirm(question):
        if exists and typer.confirm("Remove existing destination without linking?", default=False):
            _remove_path(dst_p)
            ok = typer.style("[ok]", fg=typer.colors.GREEN)
            typer.echo(f"{ok} removed {dst_type}: {dst_s}")
        else:
            info = typer.style("[info]", fg=typer.colors.BRIGHT_BLACK)
            typer.echo(f"{info} aborted")
        return

    # Ensure parent exists
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    # Remove any existing file/dir/symlink
    if exists:
        _remove_path(dst_p)

    # Create directory symlink
    os.symlink(str(src_p), str(dst_p), target_is_directory=True)
    # Record src dir history (MRU capped)
    add_user_list_item("src_history", str(src_p), max_items=max_items)
    ok = typer.style("[ok]", fg=typer.colors.GREEN)
    typer.echo(f"{ok} done")
