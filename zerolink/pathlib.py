from pathlib import Path
import os

def norm_path(p: str | Path) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()

def name_from_id(dir: str | Path, id: str | int) -> str:
    normaldir = norm_path(dir)
    target_id = int(id)
    for entry in normaldir.iterdir():
        if os.stat(entry).st_ino == target_id:
            return entry.name
    raise FileNotFoundError(f"No entry with id {id} found in {dir}")
