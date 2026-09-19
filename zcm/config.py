"""Configuration schema and persistence for ZCombine.

The config file is strictly valid JSON so it works with ``jq``, linters,
and any editor. Human-readable documentation lives in a top-level
``_readme`` array, which the loader ignores. For backwards
compatibility, full-line ``//`` comments are also tolerated and stripped
before parsing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Default filenames.
CONFIG_FILENAME = "zcm.config.json"
DEFAULT_OUTPUT  = "zcm_output.txt"

# ---------------------------------------------------------------------------
# Default patterns
#
# Deliberately short: just enough to demonstrate the three notation forms
# without overwhelming the user. Users are expected to edit or extend
# these for their project.
#
# Notation reference (also mirrored in the config _readme block):
#     *.ext     -> every file with that extension
#     name.ext  -> one exact filename
#     name/     -> a directory (pruned in place; never entered)
# ---------------------------------------------------------------------------

# Target: one extension pattern + one exact filename.
DEFAULT_TARGET = [
    "*.py",         # extension: every Python file
    "README.md",    # exact file: the project readme
]

# Ignore: two directory patterns + one exact filename.
DEFAULT_IGNORE = [
    "node_modules/",       # directory: JS dependencies (never entered)
    ".git/",               # directory: VCS metadata (never entered)
    "package-lock.json",   # exact file: dependency lockfile
]

# Only full-line ``//`` comments are tolerated (no inline, no /* */).
# We use [ \t] rather than \s so the regex never eats a newline that
# separates two lines.
_LINE_COMMENT_RE = re.compile(r"^[ \t]*//.*$", re.MULTILINE)


def _strip_comments(text: str) -> str:
    """Remove full-line ``//`` comments from JSON text.

    Safe to call on JSON that contains no comments.
    """
    return _LINE_COMMENT_RE.sub("", text)


@dataclass
class ZcmConfig:
    """User configuration persisted as ``zcm.config.json``.

    Pattern conventions:
        *.ext    -> extension glob (any file with that extension)
        name.ext -> exact filename match
        name/    -> directory name (with trailing slash; the directory
                    is pruned and never entered)

    The ``root`` field is resolved relative to the config file's folder,
    so a config committed to a repository is portable across machines.
    """
    root: str = "."
    target: list[str] = field(default_factory=lambda: list(DEFAULT_TARGET))
    ignore: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    output_file: str = DEFAULT_OUTPUT
    strip_empty_lines: bool = True
    draw_mind_map: bool = True
    git_ignore: bool = True

    # ----- load / save --------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "ZcmConfig":
        """Read a config from disk.

        Unknown keys are ignored, and the ``_readme`` documentation
        block is dropped before building the dataclass. This makes the
        loader tolerant of forward-compatible config files.
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw = path.read_text(encoding="utf-8")
        data = json.loads(_strip_comments(raw))
        data.pop("_readme", None)
        allowed = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**allowed)

    def save(self, path: Path) -> None:
        """Write the config to disk as strictly-valid JSON."""
        path.write_text(self.render(), encoding="utf-8")

    def render(self) -> str:
        """Return the exact file content that ``save`` will write."""
        readme = [
            "ZCombine configuration — https://github.com/cheloei/ZCM",
            "",
            "root              Directory to scan.",
            "                  Relative paths resolve from THIS file's folder.",
            "                  Use \".\" for the same folder, or an absolute path.",
            "",
            "target            Patterns to INCLUDE.",
            "                    \"*.ext\"     every file with that extension",
            "                    \"name.ext\"  that exact filename only",
            "",
            "ignore            Patterns to EXCLUDE.",
            "                    \"name/\"     a directory (never entered)",
            "                    \"name.ext\"  that exact filename only",
            "",
            "output_file       Name of the merged output (created next to this file).",
            "strip_empty_lines Remove blank / whitespace-only lines.",
            "draw_mind_map     Prepend a project tree of matched files.",
            "git_ignore        Append output_file to .gitignore next to this file.",
            "",
            "Note: this file and the output are ALWAYS excluded from the merge,",
            "      regardless of the patterns above.",
        ]
        body = {
            "_readme": readme,
            "root": self.root,
            "target": self.target,
            "ignore": self.ignore,
            "output_file": self.output_file,
            "strip_empty_lines": self.strip_empty_lines,
            "draw_mind_map": self.draw_mind_map,
            "git_ignore": self.git_ignore,
        }
        return json.dumps(body, indent=2, ensure_ascii=False) + "\n"


def resolve_config_path(explicit: Path | None) -> Path:
    """Return the config file to use.

    Uses the explicit path when provided (from ``--config``), otherwise
    falls back to ``./zcm.config.json`` in the current working directory.
    """
    if explicit is not None:
        return explicit
    return Path.cwd() / CONFIG_FILENAME


def resolve_root(config: ZcmConfig, config_path: Path) -> Path:
    """Resolve ``config.root`` to an absolute path.

    Relative paths are interpreted relative to the folder containing
    the config file, so a config committed to a repo works no matter
    where the repo is checked out.
    """
    cfg_root = Path(config.root)
    if cfg_root.is_absolute():
        return cfg_root.resolve()
    return (config_path.parent / cfg_root).resolve()