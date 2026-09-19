"""Platform-specific installation logic.

Each platform lives in its own module (``windows`` / ``linux``) and
exposes a single ``install() -> int`` entry point. The dispatcher in
:mod:`installer.install.main` picks the right one at runtime.
"""
from __future__ import annotations