"""ZCombine — merge a project's files into a single text file for AI.

The package is organised as follows:

    cli.py         argument parsing and dispatch
    config.py      ZcmConfig dataclass + load/save
    matcher.py     pattern matching rules (target / ignore)
    combiner.py    the actual file-walking + merging logic
    mindmap.py     project-tree generator used at the top of the output
    gitignore.py   helpers for updating .gitignore
    init_cmd.py    implementation of `zcm init`
    _console.py    Windows console-window handling
    _resources.py  bundled resource resolution (icons, etc.)
    gui/           CustomTkinter GUI (`zcm setup`)
"""
from __future__ import annotations

__version__ = "2.0.0"