"""Console handling for Windows builds of zcm.

``zcm.exe`` is intentionally built as a **console-subsystem** application
(no ``--noconsole``). This gives us two useful behaviours for free:

  * CLI usage (``zcm combine``):
      The process inherits the caller's terminal, so ``print()``
      naturally goes to the right place — no ``AttachConsole`` magic
      required.

  * GUI usage (``zcm setup``):
      Windows creates a fresh console window for us when launched from
      the file-manager context menu, or we share cmd's console when
      launched from a terminal. We hide the window only when it belongs
      exclusively to this process, so cmd stays visible.

Detecting "our own console" is done via ``GetConsoleProcessList``: if
exactly one process (us) is attached, the console was created for us.
"""
from __future__ import annotations

import sys

# Win32 constant: hide the window entirely.
SW_HIDE = 0


def ensure_console() -> bool:
    """Kept for API compatibility with earlier builds.

    With a console-subsystem binary the standard streams are always
    present, so this simply reports whether they are usable.
    """
    return sys.stdout is not None and sys.stderr is not None


def hide_console_if_own() -> None:
    """Hide the console window when it belongs exclusively to this process.

    Safe no-op on:
        * non-Windows platforms
        * when no console is attached
        * when the console is shared with a parent shell (cmd/powershell)

    Never raises — console cosmetics must not break the app.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return

        # Ask Windows how many processes are attached to our console.
        # 1 => it's ours alone (context-menu launch) => safe to hide.
        # >1 => shared with cmd/powershell => leave it alone.
        buf = (ctypes.c_ulong * 32)()
        count = kernel32.GetConsoleProcessList(buf, 32)
        if count == 1:
            user32.ShowWindow(hwnd, SW_HIDE)
    except Exception:
        pass