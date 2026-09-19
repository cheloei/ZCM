"""Generate a project tree to prepend to the combined output.

The tree mirrors the files that will actually appear in the merged
result: ignored directories are never entered, ignored files are
skipped, and only files matching the target patterns are shown.

The output uses box-drawing characters (``├──``, ``└──``) which render
correctly in every modern terminal and are easy for an LLM to parse.
"""
from __future__ import annotations

from pathlib import Path

from zcm.config import CONFIG_FILENAME, ZcmConfig
from zcm.matcher import is_ignored_dir, is_ignored_file, matches_target


def build_tree(root: Path, config: ZcmConfig) -> str:
    """Return a multi-line string describing the tree under ``root``."""
    lines = [f"{root.name}/"]
    _recurse(root, "", lines, config)
    return "\n".join(lines)


def _recurse(directory: Path, prefix: str, lines: list[str], config: ZcmConfig) -> None:
    """Recursive worker for :func:`build_tree`.

    ``prefix`` is the running indentation built from the "is last child"
    decisions made at each level.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        # Unreadable directories are silently skipped rather than aborting
        # the whole tree.
        return

    # Files that must never appear in the tree even if the user asks for
    # them via target patterns.
    always_excluded = {config.output_file, CONFIG_FILENAME}

    dirs = sorted(
        (e for e in entries
         if e.is_dir() and not is_ignored_dir(e.name, config.ignore)),
        key=lambda p: p.name.lower(),
    )
    files = sorted(
        (e for e in entries
         if e.is_file()
         and e.name not in always_excluded
         and not is_ignored_file(e.name, config.ignore)
         and matches_target(e, config.target)),
        key=lambda p: p.name.lower(),
    )

    items = dirs + files
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        suffix = "/" if item.is_dir() else ""
        lines.append(f"{prefix}{connector}{item.name}{suffix}")
        if item.is_dir():
            # Children of the last child get blank indent; others get a
            # vertical continuation bar.
            extension = "    " if is_last else "│   "
            _recurse(item, prefix + extension, lines, config)