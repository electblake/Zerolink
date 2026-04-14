from __future__ import annotations
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

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

def _input_prompt(prompt: str, default: str | None = None) -> str | None:
    suffix = f" [{default}]" if default is not None else ""
    reply = input(f"\n\t{prompt}{suffix} ").strip()
    print("")
    if not reply:
        return default
    return reply

def get_program_version():
    try:
        from zerolink import __version__
        return __version__
    except ImportError:
        pass

    try:
        from importlib.metadata import version
        return version("zerolink")
    except Exception:
        return "0.0.0"

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
        "--install-menu",
        action="store_true",
        dest="install_menu",
        help="Install the File Explorer context-menu entry.",
    )
    parser.add_argument(
        "--uninstall-menu",
        action="store_true",
        dest="uninstall_menu",
        help="Remove the File Explorer context-menu entry.",
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
        nargs="?",
        help="Canonical path to actual files storage location.",
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Path to new download input files. Will be symlinked to canonical location.",
    )
    
    # parse args
    args = parser.parse_args(argv)


    if args.install_menu:
        import winreg
        launcher_exe = Path(sys.executable).resolve()
        command_value = f"\"{launcher_exe}\" \"%1\""
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell\Zerolink", 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Run Zerolink")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(launcher_exe))
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\Directory\shell\Zerolink\command",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command_value)
        print(f"[ok] Installed context menu: {launcher_exe}")
        return 0

    if args.uninstall_menu:
        import winreg

        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell\Zerolink\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell\Zerolink")
        print("[ok] Removed Zerolink context menu entry.")
        return 0
    
    if not args.input and args.canon:
        args.input = str(args.canon)
        args.canon = _input_prompt(
            f"[input] What is the Canonical Path to Zerolink {args.input} to?"
        )
    
    if not args.canon:
        parser.error(
            f"[error] Canonical path is required. Instead got {args.canon}"
        )
    canon_path = Path(os.path.expanduser(os.path.expandvars(str(args.canon)))).resolve()
    if not canon_path.exists():
        if _confirm(f"[canon] Create missing canonical path {canon_path}?", default=True):
            print(f"[info] Canonical path missing, creating {canon_path}")
            canon_path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"[abort] canonical path missing {canon_path}")
            return 1
    
    input_path = Path(os.path.expanduser(os.path.expandvars(str(args.input)))).resolve()
    
    print(f"[info] Canonical path to truthy files {canon_path}")
    print(f"[info] Input path set to be rclone replaced {input_path}")
    
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

            
    if not canon_path.exists():
        print(f"[info] Canonical path missing, creating {canon_path}")
        canon_path.mkdir(parents=True, exist_ok=True)
    
    if input_path.exists():
        print(f"[warn] input path will now be replaced {input_path.resolve()}")
        if _confirm("[input] Remove existing input to create new link?", default=True):
            remove_path_or_symlink_tree(input_path)
        else:
            if _confirm("Remove input without creating link?", default=False):
                remove_path_or_symlink_tree(input_path)
                print(f"[ok] removed {input_path}")
                print(f"done")
                sys.exit(0)
            print("[abort] keeping existing symlink")
            sys.exit(0)
    
    print(f"[info] Creating symlink from {canon_path} to {input_path}")
    # Create the symlink
    os.symlink(canon_path, input_path, target_is_directory=True)
    print(f"[ok] linked {input_path} -> {canon_path}")

if __name__ == "__main__":
    main()  # pragma: no cover
    
