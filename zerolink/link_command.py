from __future__ import annotations

import os
import subprocess
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
    """Return True if `dst` is a symlink pointing to `src`.

    Handles Windows/Unix differences, relative link targets, and case.
    """
    if not dst.is_symlink():
        return False

    try:
        raw_target = os.readlink(dst)
    except OSError:
        return False

    # If the stored link target is relative, resolve it relative to the link's directory
    target_path = Path(raw_target)
    if not target_path.is_absolute():
        target_path = (dst.parent / target_path).resolve()
    else:
        target_path = target_path.resolve()

    # Prefer filesystem-level comparison to avoid casing/UNC differences
    try:
        return target_path.samefile(src)
    except (FileNotFoundError, OSError):
        # Fallback to normalized string comparison
        return os.path.normcase(str(target_path)) == os.path.normcase(str(src.resolve()))


def _echo_rule(src: Path, dst: Path, replace: bool, new: bool) -> None:
    src_s = typer.style(str(src), fg=typer.colors.GREEN)
    dst_s = typer.style(str(dst), fg=typer.colors.WHITE)
    suffix = ""
    suffix = suffix + " " + typer.style("replace", fg=typer.colors.RED) if replace else suffix
    if replace:
        # get count of files in dst
        if dst.is_dir() and not dst.is_symlink():
            count = sum(1 for _ in dst.rglob('*'))
            suffix = suffix + f" ({count} items)" if count > 0 else suffix
    suffix = suffix + " " + typer.style("new", fg=typer.colors.BLUE) if new else suffix
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
        typer.echo("[skip] already linked; nothing to do")
        return

    # If destination exists as a real directory and has files, offer to move them to src via rclone
    if dst_p.is_dir() and not dst_p.is_symlink():
        file_count = sum(1 for p in dst_p.rglob('*') if p.is_file())
        if file_count == 0:
            typer.echo(
                typer.style(
                    f"[ok] Found {file_count} files in existing destination directory.",
                    fg=typer.colors.GREEN,
                )
            )
        elif file_count > 0:
            typer.echo(
                typer.style(
                    f"[warn] Found {file_count} files in existing destination directory.",
                    fg=typer.colors.YELLOW,
                )
            )
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
                [arg if ' ' not in arg else f'"{arg}"' for arg in rclone_args]
            )
            typer.echo(f"Proposed: {pretty_cmd}")
            if typer.confirm("Run this rclone move before linking?"):
                try:
                    result = subprocess.run(rclone_args, check=True)
                except FileNotFoundError:
                    typer.echo(
                        typer.style(
                            "rclone not found on PATH. Aborting move.", fg=typer.colors.RED
                        )
                    )
                    return
                except subprocess.CalledProcessError as e:
                    typer.echo(
                        typer.style(
                            f"rclone move failed with exit code {e.returncode}.",
                            fg=typer.colors.RED,
                        )
                    )
                    return
                # Recount after move
                remaining = sum(1 for p in dst_p.rglob('*') if p.is_file())
                if remaining > 0:
                    typer.echo(
                        typer.style(
                            f"Warning: {remaining} files still remain in destination after move.",
                            fg=typer.colors.RED,
                        )
                    )
                    if not typer.confirm(
                        "Proceed to replace the directory with a symlink anyway?"
                    ):
                        typer.echo("aborted")
                        return

    # Preview of the link operation
    _echo_rule(
        src_p,
        dst_p,
        replace=dst_p.exists() or dst_p.is_symlink(),
        new=not dst_p.exists(),
    )

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
