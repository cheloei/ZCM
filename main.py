"""Entry point for the ``zcm`` runtime binary.

PyInstaller bundles this file as:
    zcm.exe   (Windows)
    zcm       (Linux)

The actual command-line handling lives in :mod:`zcm.cli`.
"""
from __future__ import annotations

from zcm.cli import main


if __name__ == "__main__":
    raise SystemExit(main())