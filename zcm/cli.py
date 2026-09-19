"""Command-line interface for ZCombine.

Responsibilities:
  * Define the argparse tree (``init``, ``setup``, ``combine``).
  * Provide human-readable help text.
  * Dispatch to the appropriate handler module lazily, so that
    importing this module never pulls in the GUI or the combiner
    unless they are actually needed.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from zcm import __version__


# ---------------------------------------------------------------------------
# Help text
#
# Kept as module-level constants so the argparse setup below stays
# readable, and so translators / contributors can find all user-facing
# prose in one place.
# ---------------------------------------------------------------------------

ROOT_DESCRIPTION = """\
ZCombine — merge your project files into a single text file for AI.

Scans a project folder, collects the files you care about, skips the ones
you don't (node_modules, .git, build outputs, ...), and writes one clean
output ready to paste into an LLM. Configuration lives in zcm.config.json.

Typical workflow:
  zcm init                     create a starter config
  zcm setup                    (or) open the graphical config editor
  zcm combine                  build zcm_output.txt
"""

ROOT_EPILOG = """\
examples:
  zcm init                     Create ./zcm.config.json with defaults.
  zcm setup                    Open the GUI to build the config visually.
  zcm combine                  Merge files using ./zcm.config.json.
  zcm combine -c /tmp/c.json   Use a config stored elsewhere.
  zcm combine -r ./src         Scan a different folder.
  zcm --version                Print version and exit.

config file:
  Written by `zcm init` and `zcm setup`; read by `zcm combine`.
  See the "_readme" array inside zcm.config.json for field docs.

output:
  zcm_output.txt is written NEXT TO the config file, not inside `root`.
  The config file and the output file are always excluded from the merge.
"""

INIT_DESCRIPTION = """\
Create a starter zcm.config.json in the current working directory.

The generated file contains sensible defaults and an inline "_readme"
array documenting every field. Edit it by hand, or use `zcm setup` for a
graphical editor.
"""

INIT_EPILOG = """\
examples:
  zcm init                     Write ./zcm.config.json (fails if exists).
  zcm init --force             Overwrite an existing config.
"""

SETUP_DESCRIPTION = """\
Open the graphical configuration window.

The GUI lets you add/remove target patterns, ignore rules, and toggle
options such as strip_empty_lines and draw_mind_map. On save, it writes
zcm.config.json into the folder given as DIR (or the current directory).

If no DIR is given and the current directory is your home folder, the
GUI opens a folder picker first — useful when launched from a desktop
menu or file manager.
"""

SETUP_EPILOG = """\
examples:
  zcm setup                    Configure the current folder.
  zcm setup ~/code/myproject   Configure a specific folder.

note:
  On Windows the console window is hidden automatically when the GUI is
  launched from the file manager context menu.
"""

COMBINE_DESCRIPTION = """\
Merge project files according to zcm.config.json.

Reads the config, walks `root` (pruning ignored directories in place so
they are never entered), and writes a single UTF-8 output file next to
the config. Empty lines are stripped if enabled in the config.
"""

COMBINE_EPILOG = """\
examples:
  zcm combine                  Use ./zcm.config.json in the cwd.
  zcm combine -c ./cfg/z.json  Use a config stored elsewhere.
  zcm combine -r ./src         Override the scan root.

resolution order for the scan root:
  1. --root flag (highest priority)
  2. the "root" field inside the config file
  3. the folder that contains the config file

output policy:
  The output file is written next to the config file, regardless of
  where `root` points.
"""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> ArgumentParser:
    """Build and return the top-level argparse parser."""
    parser = ArgumentParser(
        prog="zcm",
        description=ROOT_DESCRIPTION,
        epilog=ROOT_EPILOG,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"ZCombine v{__version__}",
    )

    # Subcommands; each gets its own help text block.
    sub = parser.add_subparsers(
        dest="command",
        metavar="<command>",
        title="commands",
        description="Run `zcm <command> --help` for details on a command.",
    )

    # ----- init ---------------------------------------------------------
    init_p = sub.add_parser(
        "init",
        help="Create a default zcm.config.json in the current folder.",
        description=INIT_DESCRIPTION,
        epilog=INIT_EPILOG,
        formatter_class=RawDescriptionHelpFormatter,
    )
    init_p.add_argument(
        "--force", "-f",
        action="store_true",
        help="overwrite an existing zcm.config.json",
    )

    # ----- setup --------------------------------------------------------
    setup_p = sub.add_parser(
        "setup",
        help="Open the graphical configuration window.",
        description=SETUP_DESCRIPTION,
        epilog=SETUP_EPILOG,
        formatter_class=RawDescriptionHelpFormatter,
    )
    setup_p.add_argument(
        "directory", nargs="?", default=None, metavar="DIR",
        help="folder to configure (default: current working directory)",
    )

    # ----- combine ------------------------------------------------------
    combine_p = sub.add_parser(
        "combine",
        help="Merge project files using a zcm.config.json file.",
        description=COMBINE_DESCRIPTION,
        epilog=COMBINE_EPILOG,
        formatter_class=RawDescriptionHelpFormatter,
    )
    combine_p.add_argument(
        "--config", "-c",
        type=Path, default=None,
        metavar="PATH",
        help="path to zcm.config.json (default: ./zcm.config.json)",
    )
    combine_p.add_argument(
        "--root", "-r",
        type=Path, default=None,
        metavar="PATH",
        help="override the scan root from the config file",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the right handler.

    ``argv`` is injected so tests can call ``main([...])`` without
    touching ``sys.argv``.
    """
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        from zcm.init_cmd import run_init
        return run_init(force=args.force)

    if args.command == "setup":
        # Resolve optional target directory before touching the GUI.
        target_dir: Path | None = None
        if args.directory:
            target_dir = Path(args.directory).expanduser()
            if not target_dir.is_dir():
                print(f"[!] Not a directory: {target_dir}", file=sys.stderr)
                return 1
        from zcm._console import hide_console_if_own
        hide_console_if_own()
        from zcm.gui.app import run_gui
        return run_gui(target_dir=target_dir)

    if args.command == "combine":
        from zcm.combiner import run_combine
        return run_combine(config_path=args.config, root_override=args.root)

    # No subcommand → print help.
    parser.print_help()
    return 0