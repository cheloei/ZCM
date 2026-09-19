"""ZCombine installer package.

This package contains all installation and uninstallation logic for
ZCombine. It is intentionally isolated from the main `zcm` package so
that the installer binary can bundle only what it needs, and the
runtime binary can stay lean.
"""
from __future__ import annotations