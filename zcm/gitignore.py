"""Helpers for updating ``.gitignore``.

The only operation we need is "add this entry if it isn't already
present" — done in a way that is idempotent, preserves existing
formatting, and never duplicates lines.
"""
from __future__ import annotations

from pathlib import Path


def ensure_gitignore_entry(root: Path, entry: str) -> bool:
    """Add ``entry`` to ``root/.gitignore`` if it isn't already there.

    Returns True if the file was modified. Creates the file if it does
    not exist yet.
    """
    gi = root / ".gitignore"
    existing: list[str] = []
    if gi.exists():
        try:
            existing = gi.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False

    # Already present? Exact match, ignoring surrounding whitespace.
    if any(line.strip() == entry for line in existing):
        return False

    existing.append(entry)
    try:
        gi.write_text("\n".join(existing) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True