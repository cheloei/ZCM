"""Cross-platform dispatcher for the installer.

At runtime this picks the platform-specific ``install()`` implementation
and returns its exit code. Keeping this file tiny means the actual logic
lives in one place per platform, with no shared branches.
"""
from __future__ import annotations

import sys


def run_installer() -> int:
    """Detect the current platform and run its installer.

    Returns the installer's exit code (0 on success, non-zero on failure).
    """
    if sys.platform.startswith("win"):
        from installer.install.windows import install
    elif sys.platform.startswith("linux"):
        from installer.install.linux import install
    else:
        print(f"[-] Unsupported platform: {sys.platform}", file=sys.stderr)
        return 1

    return install()