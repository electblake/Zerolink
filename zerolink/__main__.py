from __future__ import annotations

from zerolink.cli import get_program_version, main
import sys
import traceback

__all__ = ["get_program_version", "main", "run"]

def _wait_for_keypress() -> None:
    try:
        import msvcrt

        print("Press any key to close...", flush=True)
        msvcrt.getch()
    except Exception:
        try:
            input("Press Enter to close...")
        except Exception:
            pass

def run() -> int:
    try:
        result = main()
        return 0 if result is None else result
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        _wait_for_keypress()
        return 1

if __name__ == "__main__":
    raise SystemExit(run())
