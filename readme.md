<img alt="poster" src="poster.webp" />

# ⚡ ZCombine (ZCM) — Merge Your Project for AI, in One Command

**A Python-native project aggregator that turns a folder full of source files into a single, well-formatted text file — ready to paste into ChatGPT, Claude, Gemini, or any LLM.**

Stop wasting time opening, copying, and pasting dozens of source files into your AI chat. **ZCombine** scans your project, collects the files you care about, skips the ones you don't (`node_modules`, `.git`, build outputs), strips noise, and produces one clean output. A minimal GUI is there when you want it, and a fast CLI is there when you don't.

---

## 🚀 Why ZCombine?

While other tools require complex terminal commands or heavy runtimes, ZCombine is built for **speed**, **ease of use**, and **portability across platforms**.

### 1️⃣ Modern Graphical Interface
Why remember syntax when you can click? ZCombine ships with a beautiful, dark-themed GUI (**Midnight Aurora** — powered by CustomTkinter) that lets you visually configure:

- **Target patterns** — extensions (`*.py`, `*.js`) or exact filenames (`README.md`).
- **Ignore rules** — directories (`node_modules/`, `.git/`) or exact filenames (`package-lock.json`).
- **Options** — strip empty lines, draw a project mind-map, update `.gitignore`.

Chips toggle between interpretations with a single click: `*.py` ↔ `py`, `node_modules/` ↔ `node_modules`.

### 2️⃣ Native Python Core (No More Batch)
Earlier versions generated a `.bat` script. **v2 is a pure-Python engine** — cross-platform, faster, and dramatically more reliable. No more fragile string parsing, no more PowerShell dependency, no more filename-boundary bugs.

The combiner uses `os.walk` with **real in-place pruning**:
```python
dirnames[:] = [d for d in dirnames if not is_ignored_dir(d, config.ignore)]
```
This means `node_modules` is **never entered**, not visited-and-skipped. Large Node/Nuxt/Python projects finish in seconds.

### 3️⃣ Context Menu & Global CLI
- **Windows** — right-click any folder in Explorer and select **"Setup ZCombine Here"** (the GUI opens with the correct working directory).
- **Global command** — `zcm setup` from any terminal launches the GUI; `zcm combine` builds the output directly.

---

## ✨ Key Features

- **Real folder pruning** — ignored directories are never walked, only skipped at the boundary.
- **Pattern precision** — `*.ext` for extensions, `name.ext` for exact files, `name/` for directories. No substring false positives.
- **AI-optimized output** — empty lines stripped, each file clearly separated (`===== File: "src/main.py" =====`).
- **UTF-8 without BOM** — safely handled on both Windows and Linux.
- **Project mind-map** — optional tree at the top of the output so the LLM sees your structure first.
- **Auto-gitignore** — optionally appends `zcm_output.txt` to `.gitignore` next to the config.
- **Config file** — `zcm.config.json`, human-readable, commit-friendly, with an inline `_readme` block documenting every field.
- **Two workflows** — GUI for visual configuration, CLI for scripting and CI.

---

## 📦 Installation

### Windows

1. Download **`zcm-setup.exe`** from the [latest release](https://github.com/cheloei/ZCM/releases).
2. Run it. It installs to `%LOCALAPPDATA%\ZCombineManager` and updates your user `PATH`.
3. Open a **new** terminal and run:
   ```
   zcm --version
   ```
4. The installer also adds **"Setup ZCombine Here"** to the folder right-click menu and registers the app in **Add/Remove Programs**.

**Requirements:** Windows 7 SP1 or newer. No Python installation required.

### Linux

1. Download **`zcm-setup`** from the [latest release](https://github.com/cheloei/ZCM/releases).
2. Make it executable and run:
   ```bash
   chmod +x zcm-setup
   ./zcm-setup
   ```
3. The installer:
   - Copies the binary to `~/.local/share/ZCombineManager/`
   - Symlinks `zcm` and `zcm-uninstall` into `~/.local/bin/`
   - Adds a **desktop entry** for the GUI (visible in the app menu)
   - Ensures `~/.local/bin` is on your `PATH` (updates `.bashrc` / `.zshrc` / `config.fish` idempotently)

**Requirements:** glibc 2.28 or newer (Debian 10+, Ubuntu 19.04+, RHEL 8+). No Python installation required.

> ⚠️ **Note for Linux users:** ZCombine **does not** install file-manager context-menu entries on Linux. Nautilus and KDE integrations proved fragile across desktop environments, so they were removed in v2. Use the terminal (or the app-menu shortcut) instead — it's faster anyway.

### Developers (Running from Source)

```bash
git clone https://github.com/cheloei/ZCM.git
cd ZCM
pip install -r requirements.txt

python main.py setup       # launch the GUI
python main.py init        # create a starter config
python main.py combine     # build the output
```

---

## 🕹️ Quick Start

### Step 1 — Create a config

Navigate to your project folder and pick one of:

```bash
zcm init          # generates a starter zcm.config.json with defaults
```

or, for a visual editor:

```bash
zcm setup         # opens the GUI
```

Or on Windows, right-click a folder → **Setup ZCombine Here**.

### Step 2 — Customize (optional)

The generated `zcm.config.json` looks like this:

```json
{
  "_readme": [ "..." ],
  "root": ".",
  "target": ["*.py", "*.js", "*.md"],
  "ignore": ["node_modules/", ".git/", "dist/"],
  "output_file": "zcm_output.txt",
  "strip_empty_lines": true,
  "draw_mind_map": true,
  "git_ignore": true
}
```

| Field | Meaning |
|---|---|
| `root` | Directory to scan. Relative paths resolve from this file's folder. |
| `target` | **Include** patterns. `*.ext` = any file with that extension; `name.ext` = exact filename. |
| `ignore` | **Exclude** patterns. `name/` = a directory (never entered); `name.ext` = exact filename. |
| `output_file` | Name of the merged output (written next to the config). |
| `strip_empty_lines` | Remove blank / whitespace-only lines from the output. |
| `draw_mind_map` | Prepend a project tree of matched files. |
| `git_ignore` | Append `output_file` to `.gitignore` next to the config. |

Edit it by hand or regenerate it from the GUI — both work.

### Step 3 — Combine

```bash
zcm combine
```

Output appears next to the config file as **`zcm_output.txt`**. Example:

```
===== Project Structure =====
my-project/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md

===== File: "src/main.py" =====
def main():
    print("hello")

===== File: "src/utils.py" =====
def helper():
    return 42
```

Drop the file into your favorite LLM. Done.

---

## 🖥️ Graphical Interface

Launch with:

```bash
zcm setup
```

The window opens maximized and adapts to your screen. Shortcuts:

| Key | Action |
|---|---|
| `F11` | Toggle fullscreen |
| `Esc` | Exit fullscreen |
| `Enter` | Add the pattern currently in the input field |

The GUI reads and writes `zcm.config.json` in the **current working directory**. If you launch it from a desktop menu (where the cwd is `$HOME`), it shows a folder picker so you can choose your project.

---

## ⌨️ CLI Reference

| Command | Description |
|---|---|
| `zcm --version`, `zcm -v` | Print version and exit. |
| `zcm init [--force]` | Create `zcm.config.json` in the current folder. `--force` overwrites. |
| `zcm setup [DIR]` | Open the GUI, optionally targeting a specific folder. |
| `zcm combine [--config PATH] [--root PATH]` | Merge files using the config. |
| `zcm` (no args) | Print help. |

### `zcm combine` flags

- `--config`, `-c` — path to `zcm.config.json` (default: `./zcm.config.json`).
- `--root`, `-r` — override the `root` field from the config.

### Examples

```bash
# Config stored somewhere else
zcm combine -c /path/to/zcm.config.json

# Scan a different folder, keep the same config
zcm combine -r ./src

# Force-create a fresh config
zcm init --force
```

---

## 🧹 Uninstallation

### Windows
Uninstall from **Add/Remove Programs** → *ZCombine Manager*, or run:

```
%LOCALAPPDATA%\ZCombineManager\zcm-uninstall.bat
```

This removes the install folder, the `PATH` entry, the context-menu entry, and the Add/Remove Programs registration.

### Linux

```bash
~/.local/share/ZCombineManager/zcm-uninstall.sh
```

or, if `~/.local/bin` is on your `PATH`:

```bash
zcm-uninstall
```

This removes the symlinks, the desktop entry, the icon, the `PATH` line we added to your shell config, and the install folder itself. Open a new terminal afterwards.

---

## 🛠️ Development

### Project layout

```
ZCM/
├── main.py                  # entry point (zcm.exe / zcm)
├── installer.py             # entry point (zcm-setup.exe / zcm-setup)
├── zcm/
│   ├── cli.py               # argument parsing + dispatch
│   ├── config.py            # ZcmConfig dataclass, load/save
│   ├── matcher.py           # pattern-matching rules
│   ├── combiner.py          # os.walk with real directory pruning
│   ├── mindmap.py           # project tree generator
│   ├── gitignore.py         # .gitignore helpers
│   ├── init_cmd.py          # `zcm init`
│   ├── _console.py          # Windows console handling
│   ├── _resources.py        # bundled resource resolution
│   └── gui/                 # CustomTkinter UI (theme, widgets, app)
├── installer/
│   ├── common.py            # constants + resource_path + dialogs
│   ├── install/
│   │   ├── main.py          # OS dispatcher
│   │   ├── windows.py       # Win7+ user-level install
│   │   └── linux.py         # Linux user-level install
│   └── uninstall/
│       ├── windows.bat
│       └── linux.sh
└── .github/workflows/
    └── build.yml            # release-triggered cross-platform builds
```

### Building the binaries

The project uses **PyInstaller** and is built automatically on every GitHub Release:

- Windows — `windows-latest` with Python **3.8** (last release supporting Windows 7 SP1).
- Linux — built inside a `python:3.8-slim-bullseye` Docker container (glibc 2.28+), with `apt` pinned to a `snapshot.debian.org` mirror for reproducibility.

To build locally:

```bash
pip install pyinstaller pillow

# Main binary
pyinstaller --onefile --console --icon=icon.ico --name zcm \
    --collect-all customtkinter --collect-submodules zcm \
    --add-data "icon.ico;." --add-data "icon.png;." \
    main.py

# Installer
pyinstaller --onefile --console --icon=icon.ico --name zcm-setup \
    --collect-submodules installer \
    --add-data "dist/zcm.exe;payload" \
    --add-data "installer/uninstall/windows.bat;payload" \
    --add-data "icon.ico;payload" \
    installer.py
```

---

## 🤖 Built by AI, for AI

This project embraces the future of development. ZCombine was built with the assistance of AI, specifically designed to solve the friction of feeding context back into AI models.

It's a perfect loop: AI helping build a tool that makes working with AI easier.

The project is developed under the supervision of **Abolfazl Cheloyi** ([@cheloei](https://github.com/cheloei)).

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/cheloei/ZCM/issues).

If you'd like to work on the codebase, the "Development" section above has everything you need — the layout, build commands, and target-platform details.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.