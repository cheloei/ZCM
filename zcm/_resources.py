"""Locate bundled resource files (icons, etc.).

When ``zcm`` runs from a PyInstaller one-file bundle, resources are
extracted to a temporary directory pointed to by ``sys._MEIPASS``.
During development, resources live next to the source tree instead.
This module hides that difference.
"""
from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(name: str) -> Path:
    """Resolve a bundled resource by filename.

    Works in two environments:
      - PyInstaller ``--onefile`` bundle: files live in ``sys._MEIPASS``
      - development tree: files live next to the package source

    Returns a :class:`Path` even if the file does not exist, so callers
    can test ``.exists()`` and fall back gracefully.
    """
    # --- PyInstaller bundle -------------------------------------------
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / name

    # --- Development tree ---------------------------------------------
    here = Path(__file__).resolve().parent  # zcm/
    root = here.parent                      # repository root
    for candidate in (root / name, here / name):
        if candidate.exists():
            return candidate
    return root / name