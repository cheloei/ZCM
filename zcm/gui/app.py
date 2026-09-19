"""Main application window — "Midnight Aurora" theme, grid layout.

Layout overview (all grid-based, no scrollbars needed at normal sizes):

    +-----------------------------------------------------------+
    |  Header: title, subtitle, GitHub link, version badge      |  row 0
    +-----------------------------------------------------------+
    |  Target patterns (left)  |  Ignored items (right)         |  row 1
    |                          |                                |
    +--------------------------+--------------------------------+
    |  Options (spans both columns)                             |
    +-----------------------------------------------------------+
    |  [Generate config]                              [Exit]    |
    +-----------------------------------------------------------+
    |  Status bar                                               |  row 2
    +-----------------------------------------------------------+

On startup, the window tries to load an existing ``zcm.config.json``
from the current working directory. If it loads successfully, the form
reflects the file's current values. Otherwise the form falls back to
the built-in defaults. Loading is wrapped so a malformed or unreadable
config never crashes the GUI.
"""
from __future__ import annotations

from pathlib import Path
import os
import sys
import traceback
import webbrowser
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from zcm import __version__
from zcm._resources import get_resource_path
from zcm.config import (
    CONFIG_FILENAME, DEFAULT_IGNORE, DEFAULT_OUTPUT, DEFAULT_TARGET, ZcmConfig,
)
from zcm.gitignore import ensure_gitignore_entry
from zcm.gui.theme import (
    ACCENT_2, ACCENT_COLOR, ACCENT_HOVER, BG_COLOR, CARD_BORDER,
    CARD_COLOR, INPUT_BG, STATUS_BG, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
)
from zcm.gui.widgets import TagList

GITHUB_URL = "https://github.com/cheloei/ZCM"


# ---------------------------------------------------------------------------
# Existing-config loading
# ---------------------------------------------------------------------------

def _load_existing_config() -> ZcmConfig | None:
    """Try to load ``zcm.config.json`` from the current working directory.

    Returns ``None`` (never raises) if the file is missing, unreadable,
    malformed, or has an incompatible schema. The GUI silently falls back
    to built-in defaults in that case, so a bad config file cannot
    prevent the user from opening the window.
    """
    path = Path.cwd() / CONFIG_FILENAME
    if not path.exists():
        return None
    try:
        return ZcmConfig.load(path)
    except Exception:
        # Malformed JSON, wrong encoding, unknown top-level type,
        # unreadable file, etc. Anything at all — fall back to defaults.
        return None


# ---------------------------------------------------------------------------
# Exception logging
# ---------------------------------------------------------------------------

def _install_excepthook() -> None:
    """Log uncaught exceptions and show a dialog.

    Necessary because the GUI can be launched without a console (from
    the context menu / app menu), where tracebacks would otherwise be
    lost. Every unexpected error is appended to ``zcm-error.log`` in the
    per-user config directory.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        log_dir = base / "ZCombineManager"
    else:
        log_dir = Path.home() / ".local" / "share" / "ZCombineManager"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "zcm-error.log"
    except OSError:
        # Fall back to the home folder if we cannot create the log dir.
        log_file = Path.home() / "zcm-error.log"

    def hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        ts = datetime.now().isoformat(timespec="seconds")
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n{ts}\n{'=' * 60}\n{tb}\n")
        except OSError:
            pass
        try:
            messagebox.showerror(
                "ZCombine — Unexpected Error",
                f"An unexpected error occurred:\n\n{exc_value}\n\n"
                f"A log was written to:\n{log_file}",
            )
        except Exception:
            pass

    sys.excepthook = hook


# ---------------------------------------------------------------------------
# Window icon
# ---------------------------------------------------------------------------

def _set_window_icon(window) -> None:
    """Set the window/taskbar icon, cross-platform, best-effort.

    Strategy (first one that works wins):
        1. Windows: native ``.ico`` via ``iconbitmap``.
        2. Any platform: PNG via ``iconphoto`` (Tk 8.6+ handles PNG).
        3. Any platform: convert ``.ico`` with PIL as a fallback.

    A reference to the PhotoImage is stored on the window so Python's
    garbage collector does not reclaim it.
    """
    from tkinter import PhotoImage

    # 1) Windows: native .ico gives the cleanest result.
    if sys.platform == "win32":
        ico = get_resource_path("icon.ico")
        if ico.exists():
            try:
                window.iconbitmap(default=str(ico))
                return
            except Exception:
                pass

    # 2) PNG (works on Linux and most modern Tk builds).
    png = get_resource_path("icon.png")
    if png.exists():
        try:
            photo = PhotoImage(file=str(png))
            window.iconphoto(True, photo)
            window._icon_ref = photo
            return
        except Exception:
            pass

    # 3) Last resort: convert .ico with PIL.
    try:
        from PIL import Image, ImageTk
        for name in ("icon.png", "icon.ico"):
            p = get_resource_path(name)
            if p.exists():
                img = Image.open(p)
                photo = ImageTk.PhotoImage(img)
                window.iconphoto(True, photo)
                window._icon_ref = photo
                return
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class ZcmConfigWindow(ctk.CTk):
    """The single top-level window of the GUI."""

    def __init__(self):
        super().__init__()
        self.title(f"ZCombine  ·  v{__version__}")
        self.minsize(1000, 640)
        self.configure(fg_color=BG_COLOR)
        self._enter_maximized()
        self._bind_shortcuts()
        _set_window_icon(self)

        # Try to load an existing config from the current folder. If it
        # is missing or malformed, `self._initial_config` stays None and
        # the form falls back to defaults. This must never raise.
        self._initial_config = _load_existing_config()

        # Root grid: header (fixed), body (stretches), status bar (fixed).
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._build_status_bar()

    # ----- window state -------------------------------------------------

    def _enter_maximized(self) -> None:
        """Start maximized, falling back gracefully on non-Windows."""
        try:
            self.state("zoomed")            # Windows
        except Exception:
            try:
                self.attributes("-zoomed", True)   # Linux (some WMs)
            except Exception:
                self.geometry("1200x800")           # last resort

    def _bind_shortcuts(self) -> None:
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", lambda _e: self.attributes("-fullscreen", False))

    def _toggle_fullscreen(self, _event=None) -> None:
        current = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not current)

    # ----- header -------------------------------------------------------

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=120)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        # Bottom accent bar (violet then teal).
        ctk.CTkFrame(header, fg_color=ACCENT_COLOR, height=3, corner_radius=0).place(
            relx=0, rely=1, anchor="sw", relwidth=0.6,
        )
        ctk.CTkFrame(header, fg_color=ACCENT_2, height=3, corner_radius=0).place(
            relx=0.6, rely=1, anchor="sw", relwidth=0.4,
        )

        ctk.CTkLabel(
            header,
            text="⚡  ZCombine",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT_PRIMARY,
        ).place(x=30, y=18)

        ctk.CTkLabel(
            header,
            text="Configure once, combine anywhere — a Python-native project aggregator.",
            font=("Segoe UI", 12),
            text_color=ACCENT_2,
        ).place(x=34, y=62)

        # GitHub link — clickable label styled like a hyperlink.
        link = ctk.CTkLabel(
            header,
            text=GITHUB_URL,
            font=("Segoe UI", 10, "underline"),
            text_color=TEXT_SECONDARY,
            cursor="hand2",
        )
        link.place(x=34, y=88)
        link.bind("<Button-1>", lambda _e: webbrowser.open(GITHUB_URL))

        # Version badge — top-right.
        ctk.CTkLabel(
            header,
            text=f"  v{__version__}  ",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT_COLOR,
            corner_radius=8,
            height=20,
        ).place(relx=1.0, rely=0.0, x=-30, y=22, anchor="ne")

        # Keyboard hint — bottom-right.
        ctk.CTkLabel(
            header,
            text="F11 fullscreen  ·  Esc exit fullscreen",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
        ).place(relx=1.0, rely=1.0, x=-30, y=-14, anchor="se")

    # ----- body ---------------------------------------------------------

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=18)

        # Two equal columns for the tag cards, one expanding row.
        body.grid_columnconfigure(0, weight=1, uniform="cards")
        body.grid_columnconfigure(1, weight=1, uniform="cards")
        body.grid_rowconfigure(0, weight=1)

        # Decide what to seed the tag lists with:
        #   - if a config was loaded and has non-empty lists, use those
        #   - otherwise fall back to the built-in defaults
        cfg = self._initial_config
        initial_target = list(cfg.target) if cfg and cfg.target else list(DEFAULT_TARGET)
        initial_ignore = list(cfg.ignore) if cfg and cfg.ignore else list(DEFAULT_IGNORE)

        # --- Target patterns (left) ---
        self.target_tags = TagList(
            body,
            label_text="🎯  Target patterns",
            hint_text="Click a chip to toggle between  *.ext  and  exact-filename.",
            kind="target",
            default_tags=initial_target,
        )
        self.target_tags.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 14))

        # --- Ignored items (right) ---
        self.ignore_tags = TagList(
            body,
            label_text="🚫  Ignored items",
            hint_text="Click a chip to toggle between  directory  and  exact-filename.",
            kind="ignore",
            default_tags=initial_ignore,
        )
        self.ignore_tags.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 14))

        # --- Options (spans both columns) ---
        opts = ctk.CTkFrame(
            body,
            fg_color=CARD_COLOR,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        opts.grid_columnconfigure((0, 1, 2), weight=1, uniform="opt")

        ctk.CTkLabel(
            opts,
            text="⚙️  Options",
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(14, 8))

        # Boolean state for the three checkboxes — seed from the loaded
        # config if present, otherwise from the built-in defaults.
        self.strip_var     = ctk.BooleanVar(value=(cfg.strip_empty_lines if cfg else True))
        self.mindmap_var   = ctk.BooleanVar(value=(cfg.draw_mind_map     if cfg else True))
        self.gitignore_var = ctk.BooleanVar(value=(cfg.git_ignore        if cfg else True))

        checkboxes = [
            ("Strip empty lines", self.strip_var),
            ("Draw project mind-map", self.mindmap_var),
            (f"Add {DEFAULT_OUTPUT} to .gitignore", self.gitignore_var),
        ]
        for col, (text, var) in enumerate(checkboxes):
            ctk.CTkCheckBox(
                opts,
                text=text,
                variable=var,
                font=("Segoe UI", 13),
                text_color=TEXT_SECONDARY,
                fg_color=ACCENT_COLOR,
                hover_color=ACCENT_HOVER,
                border_color=CARD_BORDER,
                checkmark_color=TEXT_PRIMARY,
            ).grid(row=1, column=col, sticky="w", padx=22, pady=(0, 16))

        # --- Buttons (spans both columns) ---
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.grid(row=2, column=0, columnspan=2, sticky="ew")
        btns.grid_columnconfigure(2, weight=1)  # spacer pushes Exit to the right

        ctk.CTkButton(
            btns,
            text="✨  Generate config",
            font=("Segoe UI", 14, "bold"),
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            height=48, width=260,
            corner_radius=10,
            command=self.generate,
        ).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkButton(
            btns,
            text="Exit",
            font=("Segoe UI", 14, "bold"),
            fg_color="transparent",
            hover_color=INPUT_BG,
            border_width=2,
            border_color=CARD_BORDER,
            text_color=TEXT_SECONDARY,
            height=48, width=110,
            corner_radius=10,
            command=self.destroy,
        ).grid(row=0, column=3, sticky="e")

    # ----- status bar ---------------------------------------------------

    def _build_status_bar(self) -> None:
        if self._initial_config is not None:
            initial = f"Loaded existing {CONFIG_FILENAME}"
        else:
            initial = f"New config — using defaults  ·  {Path.cwd()}"

        self.status_var = ctk.StringVar(value=initial)

        bar = ctk.CTkFrame(self, fg_color=STATUS_BG, corner_radius=0, height=34)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        ctk.CTkLabel(
            bar,
            text="●",
            font=("Segoe UI", 12),
            text_color=ACCENT_2,
        ).pack(side="left", padx=(20, 6), pady=5)

        ctk.CTkLabel(
            bar,
            textvariable=self.status_var,
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        ).pack(side="left", pady=5)

    # ----- generate -----------------------------------------------------

    def generate(self) -> None:
        """Write ``zcm.config.json`` into the current folder and exit.

        Fields that are not editable in the GUI (``root`` and
        ``output_file``) are preserved from the loaded config if one
        existed, so opening and re-saving the config does not silently
        reset them to defaults.
        """
        targets = self.target_tags.get_tags()
        ignores = self.ignore_tags.get_tags()

        if not targets:
            messagebox.showerror("Error", "At least one target pattern is required.")
            return

        cfg = self._initial_config
        config = ZcmConfig(
            root=(cfg.root if cfg else "."),
            target=targets,
            ignore=ignores,
            output_file=(cfg.output_file if cfg else DEFAULT_OUTPUT),
            strip_empty_lines=self.strip_var.get(),
            draw_mind_map=self.mindmap_var.get(),
            git_ignore=self.gitignore_var.get(),
        )

        out = Path.cwd() / CONFIG_FILENAME
        try:
            config.save(out)
        except OSError as exc:
            messagebox.showerror("Error", f"Could not write config:\n{exc}")
            self.status_var.set("Write failed")
            return

        if config.git_ignore:
            try:
                ensure_gitignore_entry(Path.cwd(), config.output_file)
            except Exception:
                # A failed .gitignore update is not fatal — the config
                # was written successfully, which is what matters.
                pass

        self.status_var.set(f"Wrote {out.name}")
        messagebox.showinfo(
            "Success",
            f"{CONFIG_FILENAME} created in:\n{out.parent}\n\n"
            f"Run  zcm combine  here to build the output.",
        )
        self.destroy()


# ---------------------------------------------------------------------------
# Folder picker (for app-menu launches)
# ---------------------------------------------------------------------------

def _ask_for_folder() -> Path | None:
    """Show a native folder picker. Returns None if the user cancels."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.update()
    _set_window_icon(root)
    try:
        chosen = filedialog.askdirectory(
            title="Choose the project folder to configure",
        )
    finally:
        root.destroy()
    return Path(chosen) if chosen else None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_gui(target_dir: Path | None = None) -> int:
    """Launch the configuration GUI.

    Resolution order for the working folder:
        1. ``target_dir`` when given (``zcm setup DIR``).
        2. The current working directory.
        3. If the cwd is ``$HOME`` (typical when launched from the app
           menu), ask the user via a folder picker.
    """
    _install_excepthook()

    if target_dir is not None:
        try:
            os.chdir(target_dir)
        except OSError as exc:
            print(f"[!] Could not enter {target_dir}: {exc}", file=sys.stderr)
            return 1
    elif Path.cwd() == Path.home():
        chosen = _ask_for_folder()
        if chosen is None:
            print("[*] No folder selected. Cancelled.")
            return 0
        os.chdir(chosen)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ZcmConfigWindow()
    app.mainloop()
    return 0