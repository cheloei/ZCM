"""Windows installation logic for ZCombine.

Design goals:
  * User-level install — no administrator privileges required.
  * In-place upgrade — a previous installation is fully removed before
    the new one is written, so there is never a half-mixed state.
  * Locked-file safety — refuses to proceed while ``zcm.exe`` is
    running, since Windows locks running executables.

What gets written where:
  %LOCALAPPDATA%\\ZCombineManager\\   install directory
  HKCU\\Environment\\Path             user PATH entry (appended)
  HKCU\\Software\\Classes\\Directory\\Background\\shell\\ZCombine
                                       Explorer context menu
  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ZCombineManager
                                       Add/Remove Programs entry
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import winreg
from pathlib import Path

from installer.common import (
    APP_KEY, APP_NAME, APP_VERSION, DST_ICON_WIN, DST_UNINSTALLER_WIN,
    PUBLISHER, SRC_BIN_WIN, SRC_ICON_WIN, SRC_UNINSTALLER_WIN,
    resource_path, show_success_dialog,
)

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------

# For broadcasting an environment change to running applications.
HWND_BROADCAST   = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002

# For notifying Explorer that file associations / icons changed.
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST       = 0x0000

# Registry paths we own.
CONTEXT_MENU_REG = r"Software\Classes\Directory\Background\shell\ZCombine"
UNINSTALL_REG    = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_KEY}"


# ---------------------------------------------------------------------------
# Install location
# ---------------------------------------------------------------------------

def install_dir() -> Path:
    """Return the per-user install directory.

    Uses %LOCALAPPDATA% so we never need admin rights and never touch
    machine-wide state.
    """
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / APP_KEY


# ---------------------------------------------------------------------------
# Running-process detection
# ---------------------------------------------------------------------------

def _is_running(image_name: str) -> bool:
    """Return True if a process with this image name is currently running.

    Fails open (returns False) if ``tasklist`` cannot be queried, so a
    tooling problem never blocks a legitimate install.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return image_name.lower() in result.stdout.lower()


def _wait_until_not_running(image_name: str, timeout: float = 15.0) -> bool:
    """Poll until the process exits. Returns True on success.

    Gives the user a short grace period to close an open ZCombine
    window before we give up and report a friendly error.
    """
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_running(image_name):
            return True
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _copy(src: Path, dst: Path) -> bool:
    """Copy a payload file into place. Returns True on success."""
    if not src.exists():
        print(f"[-] Missing bundle file: {src}")
        return False
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as exc:
        print(f"[-] Copy failed ({src.name}): {exc}")
        return False


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _delete_reg_tree(root: int, subkey: str) -> bool:
    """Recursively delete a registry key.

    ``winreg.DeleteKey`` refuses to remove keys with subkeys, so we walk
    the tree depth-first when a direct delete fails. Returns True if
    anything was actually removed.
    """
    # Quick existence check — bail out early for the common "not there" case.
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS):
            pass
    except FileNotFoundError:
        return False
    except OSError:
        return False

    try:
        winreg.DeleteKey(root, subkey)
        return True
    except OSError:
        # Subkeys exist; recurse.
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                    except OSError:
                        break
                    _delete_reg_tree(root, f"{subkey}\\{child}")
            winreg.DeleteKey(root, subkey)
            return True
        except OSError:
            return False


def _remove_from_user_path(folder: Path) -> bool:
    """Remove ``folder`` from the user's PATH registry value.

    Handles the three cases: entry missing (no-op), entry present among
    others (rewrite the value), entry was the only one (delete the value
    entirely). Case-insensitive comparison, matching Windows semantics.
    """
    target = str(folder).lower()
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS,
        )
    except OSError:
        return False
    try:
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            return False
        parts = [p for p in current.split(";") if p]
        new_parts = [p for p in parts if p.lower() != target]
        if len(new_parts) == len(parts):
            return False  # wasn't there
        if new_parts:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(new_parts))
        else:
            winreg.DeleteValue(key, "Path")
        return True
    finally:
        winreg.CloseKey(key)


# ---------------------------------------------------------------------------
# Upgrade cleanup
# ---------------------------------------------------------------------------

def cleanup_previous(folder: Path) -> None:
    """Remove every trace of a previous install so we can start fresh.

    Order matters: we clear registry entries before touching the folder,
    so a failed folder removal leaves us with at least a clean registry.
    """
    removed_any = False

    if _remove_from_user_path(folder):
        print("[+] Removed previous PATH entry.")
        removed_any = True

    if _delete_reg_tree(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_REG):
        print("[+] Removed previous context menu.")
        removed_any = True

    if _delete_reg_tree(winreg.HKEY_CURRENT_USER, UNINSTALL_REG):
        print("[+] Removed previous Uninstall registry entry.")
        removed_any = True

    if folder.exists():
        try:
            shutil.rmtree(folder)
            print(f"[+] Removed previous install folder: {folder}")
            removed_any = True
        except OSError:
            # Something is locked (e.g. a running zcm.exe we somehow missed).
            # Do our best: delete what we can, leave the folder behind.
            print("[!] Could not fully remove previous install folder; "
                  "clearing contents.")
            for item in folder.iterdir():
                try:
                    if item.is_dir() and not item.is_symlink():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink()
                except OSError:
                    pass
            removed_any = True

    if not removed_any:
        print("[*] No previous installation detected.")


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

def add_to_user_path(folder: Path) -> None:
    """Append ``folder`` to the user's PATH, unless already present."""
    target = str(folder)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS,
        )
    except OSError as exc:
        print(f"[-] Could not open user Environment key: {exc}")
        return
    try:
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""
        parts = [p for p in current.split(";") if p]
        if any(p.lower() == target.lower() for p in parts):
            print("[*] Already present in user PATH.")
            return
        parts.append(target)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
        print("[+] Added to user PATH.")
    finally:
        winreg.CloseKey(key)


def add_context_menu(exe: Path, icon: Path) -> None:
    """Install the 'Setup ZCombine Here' Explorer context-menu entry.

    The entry lives under Directory\\Background, i.e. it appears when the
    user right-clicks empty space inside a folder. ``%V`` is expanded by
    Explorer to that folder's path, so the GUI always opens in the folder
    the user actually clicked on.
    """
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_REG) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "Setup ZCombine Here")
            winreg.SetValueEx(
                key, "Icon", 0, winreg.REG_SZ,
                str(icon if icon.exists() else exe),
            )
            with winreg.CreateKey(key, "command") as cmd:
                winreg.SetValue(cmd, "", winreg.REG_SZ, f'"{exe}" setup "%V"')
        print("[+] Context menu installed.")
    except OSError as exc:
        print(f"[-] Context menu failed: {exc}")


def register_uninstaller(folder: Path, uninstaller: Path, main_exe: Path, icon: Path) -> None:
    """Register the app in Windows' Add/Remove Programs (per-user).

    Uses the current-user Uninstall key so no admin rights are needed.
    ``NoModify`` and ``NoRepair`` hide the Modify/Repair buttons in
    Settings, since we don't support either.
    """
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REG) as key:
            winreg.SetValueEx(key, "DisplayName",     0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion",  0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher",       0, winreg.REG_SZ, PUBLISHER)
            winreg.SetValueEx(
                key, "DisplayIcon", 0, winreg.REG_SZ,
                str(icon if icon.exists() else main_exe),
            )
            winreg.SetValueEx(
                key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}"',
            )
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(folder))
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        print("[+] Registered in Add/Remove Programs.")
    except OSError as exc:
        print(f"[-] Registry entry failed: {exc}")


# ---------------------------------------------------------------------------
# Shell notifications
# ---------------------------------------------------------------------------

def broadcast_env_change() -> None:
    """Tell running applications that environment variables changed.

    Without this, already-open Explorer windows and cmd/PowerShell
    sessions keep their old PATH until the user logs out.
    """
    try:
        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
            SMTO_ABORTIFHUNG, 5000, ctypes.byref(result),
        )
    except Exception:
        pass


def refresh_shell() -> None:
    """Ask Explorer to refresh its icon and association cache."""
    try:
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def install() -> int:
    """Run the full Windows installation.

    Returns 0 on success, 1 on any unrecoverable error.
    """
    print()
    print("=" * 60)
    print("   ZCombine Installer  —  Windows")
    print("=" * 60)

    folder = install_dir()
    print(f"[+] Install dir: {folder}")

    # ---- Step 0: make sure no running zcm.exe blocks the upgrade ------
    if _is_running("zcm.exe"):
        print("[!] zcm.exe is currently running. Waiting for it to exit...")
        if not _wait_until_not_running("zcm.exe", timeout=15.0):
            show_success_dialog(
                "ZCombine — Cannot Install",
                "ZCombine is currently running.\n\n"
                "Please close any open ZCombine windows and try again.",
            )
            return 1
        print("[+] zcm.exe exited. Continuing.")

    # ---- Step 1: clean previous install -------------------------------
    cleanup_previous(folder)

    # ---- Step 2: create fresh folder ----------------------------------
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[-] Could not create install dir: {exc}")
        show_success_dialog(
            "ZCombine — Installation Failed",
            f"Could not create the install folder:\n{folder}\n\n{exc}",
        )
        return 1

    # ---- Step 3: copy payload -----------------------------------------
    dst_exe       = folder / SRC_BIN_WIN
    dst_uninstall = folder / DST_UNINSTALLER_WIN
    dst_icon      = folder / DST_ICON_WIN

    # zcm.exe and the uninstaller are required; the icon is optional.
    ok = True
    ok &= _copy(resource_path(SRC_BIN_WIN), dst_exe)
    ok &= _copy(resource_path(SRC_UNINSTALLER_WIN), dst_uninstall)
    _copy(resource_path(SRC_ICON_WIN), dst_icon)

    if not ok:
        print("[-] Installation aborted: required files missing.")
        show_success_dialog(
            "ZCombine — Installation Failed",
            "Some required files could not be installed.\n"
            "Please re-run the installer.",
        )
        return 1

    # ---- Step 4: register everything ----------------------------------
    add_to_user_path(folder)
    add_context_menu(dst_exe, dst_icon)
    register_uninstaller(folder, dst_uninstall, dst_exe, dst_icon)

    # ---- Step 5: notify the shell -------------------------------------
    broadcast_env_change()
    refresh_shell()

    # ---- Step 6: success popup ----------------------------------------
    print()
    print("[OK] Installation complete.")
    show_success_dialog(
        "ZCombine — Installation Complete",
        f"ZCombine has been installed successfully.\n\n"
        f"Location:\n  {folder}\n\n"
        f"Quick start:\n"
        f"  1. Open a new terminal (PATH was updated).\n"
        f"  2. cd into your project folder.\n"
        f"  3. Run  zcm init   to create a config.\n"
        f"  4. Edit zcm.config.json, then run  zcm combine.\n\n"
        f"Or right-click any folder → 'Setup ZCombine Here'.",
    )
    return 0