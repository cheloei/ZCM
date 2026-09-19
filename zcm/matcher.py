"""Pattern-matching rules shared by the combiner and the mind-map.

Two kinds of patterns are supported:

  *.ext    -> extension glob   (any file whose name ends with ".ext")
  name.ext -> exact filename   (matched verbatim)
  name/    -> directory name   (trailing slash, only in ignore lists)

The rules are intentionally simple and case-sensitive on the basename,
matching typical Unix conventions. Windows-friendly case-insensitivity
is deliberately not applied because file extensions are case-sensitive
on Linux and mixing the two behaviours would be surprising.
"""
from __future__ import annotations

from pathlib import Path


def is_ext_pattern(pattern: str) -> bool:
    """Return True if ``pattern`` is an extension glob like ``*.py``."""
    return pattern.startswith("*.")


def is_dir_pattern(pattern: str) -> bool:
    """Return True if ``pattern`` is a directory rule like ``node_modules/``."""
    return pattern.endswith("/")


def matches_target(path: Path, patterns: list[str]) -> bool:
    """Return True if ``path`` matches at least one target pattern.

    Directory-style patterns are ignored here — they belong in the
    ignore list, and treating them as file patterns would be a bug.
    """
    name = path.name
    for pattern in patterns:
        if is_ext_pattern(pattern):
            if name.endswith(pattern[1:]):  # strip the leading '*'
                return True
        elif name == pattern:
            return True
    return False


def is_ignored_dir(name: str, patterns: list[str]) -> bool:
    """Return True if a directory named ``name`` should be pruned."""
    for pattern in patterns:
        if is_dir_pattern(pattern) and name == pattern[:-1]:
            return True
    return False


def is_ignored_file(name: str, patterns: list[str]) -> bool:
    """Return True if a file named ``name`` should be excluded."""
    for pattern in patterns:
        if not is_dir_pattern(pattern) and name == pattern:
            return True
    return False