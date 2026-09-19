"""Linux installation logic for ZCombine.

Design goals:
  * User-level install — everything under ``~/.local``, no sudo needed.
  * Minimal footprint — only what's needed to run ``zcm`` from a
    terminal and open the GUI from the application menu.
  * No file-manager integrations — Nautilus/KDE scripts proved fragile
    across desktops, so they were removed; Linux users are expected to
    use the terminal.

What gets written where:
  ~/.local/share/ZCombineManager/    install directory (zcm, uninstaller)
  ~/.local/bin/zcm                   symlink to the runtime binary
  ~/.local/bin/zcm-uninstall         symlink to the uninstaller
  ~/.local/share/applications/zcm.desktop
                                     app-menu entry for the GUI
  ~/.local/share/icons/hicolor/256x256/apps/zcm.png
                                     application icon
  ~/.bashrc / ~/.zshrc / fish config PATH update (idempotent)
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

from installer.common import (
    APP_KEY, DST_ICON_LINUX, DST_UNINSTALLER_LINUX,
    SRC_BIN_LINUX, SRC_ICON_LINUX, SRC_UNINSTALLER_LINUX,
    resource_path, show_success_dialog,
)

# ---------------------------------------------------------------------------
# Standard user-level install locations (XDG Base Directory spec)
# ---------------------------------------------------------------------------

HOME        = Path.home()
INSTALL_DIR = HOME / ".local" / "share" / APP_KEY
BIN_DIR     = HOME / ".local" / "bin"
APPS_DIR    = HOME / ".local" / "share" / "applications"
ICONS_DIR   = HOME / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"


# Desktop entry installed under ~/.local/share/applications. The
# ``ZCM_BIN`` placeholder is substituted at install time with the actual
# absolute path to the installed binary.
DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=ZCombine Setup
Comment=Configure ZCombine for a project folder
Exec=ZCM_BIN setup
Icon=zcm
Terminal=false
Categories=Development;Utility;
"""


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _make_executable(p: Path) -> None:
    """Set the executable bit on a file (best-effort)."""
    try:
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def _copy(src: Path, dst: Path, executable: bool = False) -> bool:
    """Copy a payload file, optionally marking it executable.

    Returns True on success, False if the source is missing or the copy
    fails.
    """
    if not src.exists():
        print(f"[-] Missing bundle file: {src}")
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if executable:
            _make_executable(dst)
        return True
    except OSError as exc:
        print(f"[-] Copy failed ({src.name}): {exc}")
        return False


def _write(path: Path, content: str, executable: bool = False) -> None:
    """Write text to a file, optionally marking it executable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        _make_executable(path)


def _symlink(src: Path, dst: Path) -> None:
    """Create (or replace) a symlink at ``dst`` pointing to ``src``."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        dst.symlink_to(src)
    except OSError as exc:
        print(f"[-] Symlink failed ({dst.name}): {exc}")


def _update_caches() -> None:
    """Refresh the desktop-database and icon-cache if the tools exist."""
    commands = [
        ["update-desktop-database", str(APPS_DIR)],
        ["gtk-update-icon-cache", "-f", "-t", str(HOME / ".local/share/icons/hicolor")],
    ]
    for cmd in commands:
        try:
            subprocess.run(
                cmd, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass


def _render(template: str, exe: Path) -> str:
    """Substitute the ``ZCM_BIN`` sentinel with the real binary path.

    Using ``str.replace`` instead of ``str.format`` avoids having to
    escape ``%`` and ``{`` characters that appear in desktop-entry
    templates and shell snippets.
    """
    return template.replace("ZCM_BIN", str(exe))


# ---------------------------------------------------------------------------
# PATH registration
# ---------------------------------------------------------------------------

# Marker comment used so the uninstaller can find and remove exactly the
# block we added, and so re-running the installer is idempotent.
PATH_MARKER = "# Added by ZCombine installer"


def _append_if_missing(rc_file: Path, line: str) -> bool:
    """Append a PATH export to a shell rc file if it isn't already there.

    Returns True if the file was modified.
    """
    try:
        content = rc_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    # Any existing reference to ~/.local/bin is good enough — leave the
    # user's shell config alone.
    if ".local/bin" in content:
        return False

    try:
        with rc_file.open("a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write(f"\n{PATH_MARKER}\n{line}\n")
        return True
    except OSError:
        return False


def ensure_shell_path() -> list[Path]:
    """Make sure ``~/.local/bin`` is on the user's PATH.

    Detects the current shell and updates the appropriate rc file(s).
    Any rc file that already mentions ``.local/bin`` is left untouched.
    Returns the list of files actually modified.
    """
    modified: list[Path] = []

    current_shell = Path(os.environ.get("SHELL", "")).name

    bash_line = 'export PATH="$HOME/.local/bin:$PATH"'
    fish_line = "fish_add_path $HOME/.local/bin"

    # Bash
    bashrc = HOME / ".bashrc"
    if bashrc.exists() or current_shell == "bash":
        if bashrc.exists() and _append_if_missing(bashrc, bash_line):
            modified.append(bashrc)

    # Zsh
    zshrc = HOME / ".zshrc"
    if zshrc.exists() or current_shell == "zsh":
        if zshrc.exists() and _append_if_missing(zshrc, bash_line):
            modified.append(zshrc)

    # Fish
    fish_cfg = HOME / ".config" / "fish" / "config.fish"
    if fish_cfg.exists() and _append_if_missing(fish_cfg, fish_line):
        modified.append(fish_cfg)

    return modified


# ---------------------------------------------------------------------------
# Upgrade cleanup
# ---------------------------------------------------------------------------

def cleanup_previous() -> None:
    """Remove artifacts from any previous install.

    Also cleans up file-manager integrations that older versions used to
    install (KDE service menu, Nautilus script/extension) so upgrades
    from those versions leave no residue.
    """
    removed_any = False

    # 1) Symlinks on PATH.
    for name in ("zcm", "zcm-uninstall"):
        p = BIN_DIR / name
        if p.is_symlink() or p.exists():
            try:
                p.unlink()
                print(f"[+] Removed previous symlink: {p}")
                removed_any = True
            except OSError:
                pass

    # 2) Files we currently own, plus anything a previous version may
    #    have dropped. Deleting an absent file is a harmless no-op.
    legacy_paths = [
        APPS_DIR / "zcm.desktop",
        ICONS_DIR / "zcm.png",
        HOME / ".local/share/kio/servicemenus/zcm-setup.desktop",
        HOME / ".local/share/nautilus/scripts/ZCombine Setup",
        HOME / ".local/share/nautilus-python/extensions/zcm.py",
    ]
    for path in legacy_paths:
        if path.exists():
            try:
                path.unlink()
                removed_any = True
            except OSError:
                pass

    # 3) The whole install directory.
    if INSTALL_DIR.exists():
        try:
            shutil.rmtree(INSTALL_DIR)
            print(f"[+] Removed previous install folder: {INSTALL_DIR}")
            removed_any = True
        except OSError as exc:
            print(f"[!] Could not fully remove previous install folder: {exc}")

    if not removed_any:
        print("[*] No previous installation detected.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def install() -> int:
    """Run the full Linux installation.

    Returns 0 on success, 1 on any unrecoverable error.
    """
    print()
    print("=" * 60)
    print("   ZCombine Installer  —  Linux")
    print("=" * 60)

    # ---- Step 1: clean any previous install ---------------------------
    cleanup_previous()

    # ---- Step 2: create fresh install dir -----------------------------
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[+] Install dir: {INSTALL_DIR}")

    # ---- Step 3: copy payload -----------------------------------------
    dst_bin       = INSTALL_DIR / SRC_BIN_LINUX
    dst_uninstall = INSTALL_DIR / DST_UNINSTALLER_LINUX
    dst_icon      = INSTALL_DIR / DST_ICON_LINUX

    # Binary and uninstaller are required; icon is optional.
    ok = True
    ok &= _copy(resource_path(SRC_BIN_LINUX), dst_bin, executable=True)
    ok &= _copy(resource_path(SRC_UNINSTALLER_LINUX), dst_uninstall, executable=True)
    _copy(resource_path(SRC_ICON_LINUX), dst_icon)

    if not ok:
        print("[-] Installation aborted: required files missing.")
        show_success_dialog(
            "ZCombine — Installation Failed",
            "Some required files could not be installed.\n"
            "Please re-run the installer.",
        )
        return 1

    # ---- Step 4: expose binaries on PATH via symlinks -----------------
    _symlink(dst_bin,       BIN_DIR / "zcm")
    _symlink(dst_uninstall, BIN_DIR / "zcm-uninstall")
    print(f"[+] Linked {BIN_DIR / 'zcm'} and {BIN_DIR / 'zcm-uninstall'}")

    # ---- Step 5: icon + desktop entry ---------------------------------
    if dst_icon.exists():
        _copy(dst_icon, ICONS_DIR / "zcm.png")

    _write(APPS_DIR / "zcm.desktop", _render(DESKTOP_ENTRY, dst_bin))
    print("[+] Desktop entry installed.")

    # ---- Step 6: make sure ~/.local/bin is on PATH --------------------
    modified_rcs = ensure_shell_path()
    if modified_rcs:
        for rc in modified_rcs:
            print(f"[+] Added ~/.local/bin to {rc}")
    else:
        print("[*] ~/.local/bin already on PATH (or no shell rc found).")

    # ---- Step 7: refresh desktop / icon caches ------------------------
    _update_caches()

    # ---- Step 8: report PATH status if we couldn't fix it -------------
    path_warning = ""
    if str(BIN_DIR) not in os.environ.get("PATH", "").split(os.pathsep):
        if modified_rcs:
            path_warning = (
                "\n\nNote: PATH was updated in your shell config. Open a new\n"
                "terminal for `zcm` to be available on PATH."
            )
        else:
            path_warning = (
                "\n\nNote: ~/.local/bin is not on your PATH and we could not\n"
                "find a shell rc file to update."
            )
        print()
        print("[!]" + path_warning.replace("\n\n", " "))

    print()
    print("[OK] Installation complete.")

    # ---- Step 9: success dialog ---------------------------------------
    show_success_dialog(
        "ZCombine — Installation Complete",
        f"ZCombine has been installed successfully.\n\n"
        f"Location:\n  {INSTALL_DIR}\n"
        f"Command:\n  {BIN_DIR / 'zcm'}\n\n"
        f"Quick start:\n"
        f"  1. Open a new terminal.\n"
        f"  2. cd into your project folder.\n"
        f"  3. Run  zcm init   to create a config.\n"
        f"  4. Edit zcm.config.json, then run  zcm combine.\n\n"
        f"GUI is available from the app menu (ZCombine Setup)\n"
        f"or by running  zcm setup  in a project folder."
        + path_warning,
    )
    return 0