"""Shared constants and helpers for the ZCombine installer.

This module is imported by both the Windows and Linux installers, as
well as the uninstallers. Anything that must stay consistent between
platforms — app name, registry key, resource paths, dialog helpers —
belongs here.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------

# Human-readable name shown in dialogs and Add/Remove Programs.
APP_NAME = "ZCombine Manager"

# Machine-friendly key used for registry entries, folder names, and the
# install directory (e.g. %LOCALAPPDATA%\ZCombineManager).
APP_KEY = "ZCombineManager"

# Version string, surfaced in the Add/Remove Programs entry and dialogs.
APP_VERSION = "2.0.0"

PUBLISHER = "Abolfazl Cheloyi"
GITHUB_URL = "https://github.com/cheloei/ZCM"

# ---------------------------------------------------------------------------
# Bundled payload files
#
# These names are the *source* filenames inside the installer bundle.
# Everything is placed under a "payload/" subfolder by PyInstaller's
# --add-data flag, so the runtime never confuses payload files with the
# `zcm` Python package that also lives in the bundle.
# ---------------------------------------------------------------------------

# Main application binary
SRC_BIN_WIN   = "zcm.exe"
SRC_BIN_LINUX = "zcm"

# Uninstaller scripts (bat / sh)
SRC_UNINSTALLER_WIN   = "windows.bat"
SRC_UNINSTALLER_LINUX = "linux.sh"

# Icons
SRC_ICON_WIN   = "icon.ico"
SRC_ICON_LINUX = "icon.png"

# ---------------------------------------------------------------------------
# Destination filenames (after installation)
# ---------------------------------------------------------------------------

DST_UNINSTALLER_WIN   = "zcm-uninstall.bat"
DST_UNINSTALLER_LINUX = "zcm-uninstall.sh"
DST_ICON_WIN          = "icon.ico"
DST_ICON_LINUX        = "icon.png"


# ---------------------------------------------------------------------------
# Resource resolution
# ---------------------------------------------------------------------------

def resource_path(name: str) -> Path:
    """Resolve a file bundled with the installer binary.

    Lookup order:
        1. PyInstaller one-file bundle: ``sys._MEIPASS/payload/<name>``
        2. PyInstaller one-file bundle (legacy layout): ``sys._MEIPASS/<name>``
        3. Development tree: a handful of well-known repository locations

    Returns a :class:`Path` even if the file does not exist, so callers
    can decide how to react (some payload files are optional).
    """
    # --- 1 & 2: running from a PyInstaller bundle ----------------------
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "payload" / name
        if bundled.exists():
            return bundled
        return Path(meipass) / name

    # --- 3: running from the source tree (development) -----------------
    here = Path(__file__).resolve().parent      # installer/
    root = here.parent                          # repository root
    candidates = [
        root / "dist" / name,                   # repo/dist/zcm.exe
        root / name,                            # repo/zcm.exe
        here / "uninstall" / name,              # installer/uninstall/windows.bat
        here / name,                            # installer/windows.bat
    ]
    for c in candidates:
        if c.exists():
            return c

    # Nothing found; return a best-guess path so error messages are useful.
    return root / name


# ---------------------------------------------------------------------------
# Cross-platform dialogs
# ---------------------------------------------------------------------------

def show_success_dialog(title: str, message: str) -> None:
    """Show a modal informational dialog using the best tool available.

    Windows: uses ``MessageBoxW`` from user32 (always present).
    Linux:   tries ``zenity`` first, then ``kdialog``.
    Fallback: prints a banner to stdout.

    This never raises — a missing dialog helper is not a fatal error.
    """
    # --- Windows -------------------------------------------------------
    if sys.platform == "win32":
        try:
            import ctypes
            MB_OK              = 0x00000000
            MB_ICONINFORMATION = 0x00000040
            MB_SETFOREGROUND   = 0x00010000
            ctypes.windll.user32.MessageBoxW(
                0, message, title, MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND,
            )
            return
        except Exception:
            pass

    # --- Linux (GNOME / KDE) -------------------------------------------
    if sys.platform.startswith("linux"):
        if shutil.which("zenity"):
            try:
                subprocess.run(
                    ["zenity", "--info", "--title", title, "--text", message],
                    check=False,
                )
                return
            except Exception:
                pass
        if shutil.which("kdialog"):
            try:
                subprocess.run(
                    ["kdialog", "--title", title, "--msgbox", message],
                    check=False,
                )
                return
            except Exception:
                pass

    # --- Fallback: stdout ----------------------------------------------
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(message)
    print("=" * 60)