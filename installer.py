"""Entry point for the ``zcm-setup`` binary.

PyInstaller bundles this file as:
    zcm-setup.exe   (Windows)
    zcm-setup       (Linux)

All the real work happens in :mod:`installer.install.main`, which
dispatches to the correct platform implementation.
"""
from __future__ import annotations

from installer.install.main import run_installer


if __name__ == "__main__":
    raise SystemExit(run_installer())