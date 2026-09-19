"""Core file aggregation logic.

Output policy:
    The merged output is written **next to the config file**
    (``config_path.parent``), not inside the scan root. This lets
    ``root`` point to a subfolder (e.g. ``./src``) while the output
    stays at project level, where the user ran ``zcm combine``.

Pruning policy:
    Ignored directories are removed from ``dirnames`` **in place**
    during the walk, so ``os.walk`` never descends into them. This is
    what keeps performance reasonable on projects with large
    ``node_modules`` trees.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from zcm.config import (
    CONFIG_FILENAME, ZcmConfig, resolve_config_path, resolve_root,
)
from zcm.matcher import is_ignored_dir, is_ignored_file, matches_target
from zcm.mindmap import build_tree
from zcm.gitignore import ensure_gitignore_entry


def _is_always_excluded(name: str, config: ZcmConfig) -> bool:
    """Return True for files that must never appear in the output.

    Regardless of the target patterns, we never include the config file
    or the output file — doing so would be circular and confusing.
    """
    return name in (config.output_file, CONFIG_FILENAME)


def collect_files(root: Path, config: ZcmConfig) -> list[Path]:
    """Walk ``root`` and return every file matching the target patterns.

    Ignored directories are pruned in place so ``os.walk`` never enters
    them — this is the critical performance optimisation.
    """
    collected: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored dirs IN PLACE so os.walk never enters them.
        dirnames[:] = [d for d in dirnames if not is_ignored_dir(d, config.ignore)]

        for fname in filenames:
            if _is_always_excluded(fname, config):
                continue
            if is_ignored_file(fname, config.ignore):
                continue
            fpath = Path(dirpath) / fname
            if matches_target(fpath, config.target):
                collected.append(fpath)

    return sorted(collected)


def read_and_clean(path: Path, strip_empty: bool) -> list[str] | None:
    """Read a file and return its lines, optionally stripping blank ones.

    Returns None if the file cannot be read or contains nothing usable.
    Decoding uses ``errors="replace"`` so a stray binary blob does not
    crash the whole run.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    lines = text.splitlines()
    if strip_empty:
        lines = [ln for ln in lines if ln.strip()]
    return lines or None


def combine(root: Path, config: ZcmConfig, output_dir: Path) -> int:
    """Run the merge.

    Args:
        root:       Directory to scan (resolved to an absolute path).
        config:     Active configuration.
        output_dir: Where the merged file is written.

    Returns:
        The number of files added to the output.
    """
    root = root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = collect_files(root, config)
    output_path = output_dir / config.output_file

    parts: list[str] = []
    added = 0

    # Optional project tree at the very top.
    if config.draw_mind_map:
        parts.append("===== Project Structure =====")
        parts.append(build_tree(root, config))
        parts.append("")

    for fpath in files:
        lines = read_and_clean(fpath, config.strip_empty_lines)
        if not lines:
            continue

        # Relative POSIX-style path, so the output is stable across
        # platforms.
        rel = fpath.resolve().relative_to(root).as_posix()
        parts.append(f'===== File: "{rel}" =====')
        parts.extend(lines)
        parts.append("")
        parts.append("")
        added += 1

    output_path.write_text("\n".join(parts), encoding="utf-8")
    return added


def run_combine(
    config_path: Path | None = None,
    root_override: Path | None = None,
) -> int:
    """CLI entry point for ``zcm combine``.

    Resolution order for the scan root:
        1. --root flag (highest priority)
        2. config.root (relative to the config file's folder)
        3. config file's folder (fallback)

    Output policy:
        The merged output is written next to the config file, in
        ``config_path.parent``, regardless of where ``root`` points.
    """
    config_file = resolve_config_path(config_path)
    if not config_file.exists():
        print(f"[!] Config not found: {config_file}", file=sys.stderr)
        print("    Run `zcm setup` first to create one.", file=sys.stderr)
        return 1

    try:
        config = ZcmConfig.load(config_file)
    except Exception as exc:
        print(f"[!] Failed to read config: {exc}", file=sys.stderr)
        return 1

    # --root overrides anything in the config.
    if root_override is not None:
        root_dir = root_override.resolve()
    else:
        root_dir = resolve_root(config, config_file)

    if not root_dir.is_dir():
        print(f"[!] Root directory does not exist: {root_dir}", file=sys.stderr)
        return 1

    output_dir = config_file.parent.resolve()

    print(f"ZCombine v2 — config     : {config_file}")
    print(f"ZCombine v2 — scan root  : {root_dir}")
    print(f"ZCombine v2 — output dir : {output_dir}")

    try:
        added = combine(root_dir, config, output_dir)
    except Exception as exc:
        print(f"[!] Combine failed: {exc}", file=sys.stderr)
        return 1

    if config.git_ignore:
        # The .gitignore lives next to the config file, i.e. at project level.
        ensure_gitignore_entry(output_dir, config.output_file)

    print(f"[+] Added files : {added}")
    print(f"[+] Output file : {config.output_file}")
    return 0