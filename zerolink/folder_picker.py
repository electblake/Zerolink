def pick_folder(dir: str | Path):
    """
    use minifzf python package to pick a folder given a base {dir}
    return picked folder 
    """
    from minifzf import minifzf

    base_path = Path(dir).expanduser().resolve()
    if not base_path.is_dir():
        raise ValueError(f"{base_path} is not a valid directory")

    # List all subdirectories
    subdirs = [str(p.relative_to(base_path)) for p in base_path.rglob('*') if p.is_dir()]

    if not subdirs:
        raise ValueError(f"No subdirectories found in {base_path}")

    # Use minifzf to pick a directory
    picked = minifzf(subdirs, prompt="Select a folder: ")

    if picked is None:
        raise ValueError("No folder selected")

    return base_path / picked
