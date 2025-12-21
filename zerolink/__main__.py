from __future__ import annotations
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import logging

# setup standard cli logging with logging and logger so I can debug, info, warn, error


def _expand_path(path: Path) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(str(path))))

def _confirm(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        reply = input(f"\n\t{prompt}{suffix} ").strip().lower()
        print("")
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")

def get_program_version():
    from packaging.version import Version
    import importlib.metadata
    return Version(importlib.metadata.version(__package__ or __name__))

def remove_path_or_symlink_tree(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()

def main(argv: list[str] | None = None):
    # 
    parser = argparse.ArgumentParser(
        prog="zerolink",
        description="Link landing zone download folders to inbox folders.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_program_version()}",
        help="Show version info and exit",
    )
    parser.add_argument(
        "canon",
        type=Path,
        help="Canonical path to actual files storage location",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to new download input files. Will be symlinked to canonical location",
    )
    
    # parse args
    args = parser.parse_args(argv)
    
    # prep paths
    canon_path = _expand_path(args.canon).resolve()
    input_path = _expand_path(args.input).absolute()
    
    # validate input path exists
    if input_path.exists() is False and input_path.is_symlink() is False:
        raise FileNotFoundError(f"Could not find input path {input_path}")

    # if input path is symlink..
    if input_path.is_symlink() and input_path.resolve() == canon_path.resolve(): # .. and is pointed to canon already
        print("[skip] already linked; nothing to do") # skip and exit.
        sys.exit(0)
    
    # move files from input to canonical first
    if input_path.is_dir() and not input_path.is_symlink():
        file_count = sum(1 for p in input_path.rglob("*") if p.is_file())
        if file_count > 0:
            print(f"[warn] input directory contains {file_count:,} files")
            rclone_args = [
                "rclone",
                "move",
                "--progress",
                "--checksum",
                "--delete-empty-src-dirs",
                str(input_path),
                str(canon_path),
            ]
            pretty_cmd = " ".join(
                [arg if " " not in arg else f'"{arg}"' for arg in rclone_args]
            )
            print(f"[info] proposed move: {pretty_cmd}")
            if _confirm("Move files with rclone before linking?", default=True):
                subprocess.run(rclone_args, check=True)
                print(f"[ok] {file_count} files moved to canon path")

            
    # Create parent directories if needed
    print(f"Creating canon paths {canon_path} (exists_ok)")
    canon_path.mkdir(parents=True, exist_ok=True)
    
    if input_path.exists():
        print(f"[warn] input path will now be replaced {input_path.resolve()}")
        if _confirm("Remove existing input to create new link?", default=True):
            remove_path_or_symlink_tree(input_path)
        else:
            if _confirm("Remove input without creating link?", default=False):
                remove_path_or_symlink_tree(input_path)
                print(f"[ok] removed {input_path}")
                print(f"done")
                sys.exit(0)
            print("[abort] keeping existing symlink")
            sys.exit(0)
    
    print(f"Creating symlink from {canon_path} to {input_path}")
    # Create the symlink
    os.symlink(canon_path, input_path, target_is_directory=True)
    print(f"[ok] linked {input_path} -> {canon_path}")

if __name__ == "__main__":
    main()  # pragma: no cover
    