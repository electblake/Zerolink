from __future__ import annotations

import importlib.metadata

__all__ = ["__app_name__", "__version__"]
__app_name__ = "zerolink"
try:
    __version__ = importlib.metadata.version(__app_name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0+unknown"
