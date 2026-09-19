"""Implementation of ``zcm init``.

The command writes a starter ``zcm.config.json`` into the current
working directory. It refuses to overwrite an existing file unless
``--force`` is passed, so users cannot accidentally destroy their
settings.
"""
from __future__ import annotations

import sys
from pathlib import Path

from zcm.config import CONFIG_FILENAME, ZcmConfig


def run_init(force: bool = False) -> int:
    """Create a default ``zcm.config.json`` in the current folder.

    Returns 0 on success, 1 if the file already exists and ``force`` is
    False, or if the write fails.
    """
    target = Path.cwd() / CONFIG_FILENAME

    # Guard against silent data loss.
    if target.exists() and not force:
        print(f"[!] {CONFIG_FILENAME} already exists:")
        print(f"    {target}")
        print("    Use `zcm init --force` to overwrite.")
        return 1

    config = ZcmConfig()
    try:
        config.save(target)
    except OSError as exc:
        print(f"[!] Could not write config: {exc}", file=sys.stderr)
        return 1

    print(f"[+] Created {CONFIG_FILENAME}")
    print(f"    Path : {target}")
    print(f"    Root : {target.parent}")
    print()
    print("    Next steps:")
    print("      1. Edit the file to match your project.")
    print("      2. Run `zcm combine` to build the output.")
    return 0