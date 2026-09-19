"""Reusable widgets for the ZCombine GUI.

Two widgets are defined here:

  * :class:`TagWidget` — a single chip with a click-to-toggle label and
    a small delete button.
  * :class:`TagList`   — a card that owns a list of tags, plus the
    input field and "Add" button used to create them.

The tag normalisation logic is contained in :class:`TagList` so the
underlying config file never sees malformed patterns.
"""
from __future__ import annotations

import customtkinter as ctk

from zcm.gui.theme import (
    ACCENT_COLOR, ACCENT_HOVER, CARD_BORDER, CARD_COLOR,
    INPUT_BG, TAG_DELETE, TAG_IGNORE_BG, TAG_IGNORE_FG,
    TAG_TARGET_BG, TAG_TARGET_FG, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
)


class TagWidget(ctk.CTkFrame):
    """A single chip with a click-to-toggle label and a delete button.

    The visual style varies by the tag's current interpretation:
        target extension  -> violet chip, 'EXT'  badge
        target file       -> violet chip, 'FILE' badge
        ignore directory  -> teal chip,   'DIR'  badge
        ignore file       -> teal chip,   'FILE' badge
    """

    def __init__(self, parent, raw_value, display_text, kind, badge, on_toggle, on_delete):
        bg = TAG_TARGET_BG if kind == "target" else TAG_IGNORE_BG
        fg = TAG_TARGET_FG if kind == "target" else TAG_IGNORE_FG
        super().__init__(parent, fg_color=bg, corner_radius=10)

        # Stored so the parent can map clicks back to the tag value.
        self.raw_value = raw_value
        self.kind = kind

        # Small "type" badge on the left (EXT / FILE / DIR).
        self.badge = ctk.CTkLabel(
            self,
            text=badge,
            font=("Segoe UI", 9, "bold"),
            text_color=fg,
            width=36,
        )
        self.badge.pack(side="left", padx=(10, 0), pady=6)

        # Main clickable label — clicking toggles extension <-> file or
        # directory <-> file, depending on the kind.
        self.label = ctk.CTkLabel(
            self,
            text=display_text,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
            cursor="hand2",
        )
        self.label.pack(side="left", padx=(4, 4), pady=6)
        self.label.bind("<Button-1>", lambda _e: on_toggle(raw_value))

        # Delete button.
        self.btn = ctk.CTkButton(
            self,
            text="✕",
            width=22, height=22, corner_radius=11,
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            hover_color=TAG_DELETE,
            text_color=TEXT_PRIMARY,
            command=lambda: on_delete(raw_value),
        )
        self.btn.pack(side="left", padx=(2, 6), pady=6)


class TagList(ctk.CTkFrame):
    """A card with an input field, an Add button, and a wrap-layout of tags.

    The list knows how to normalise user input into canonical patterns:

        target:  "py"       -> "*.py"
                 "README.md" -> "README.md"
        ignore:  "node_modules"   -> "node_modules/"
                 "package.json"   -> "package.json"
    """

    def __init__(self, parent, label_text, hint_text, kind, default_tags=None, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
            **kwargs,
        )

        # Either "target" or "ignore" — controls normalisation and colors.
        self.kind = kind
        self.tags: list[str] = []
        self.widgets: list[TagWidget] = []

        # ----- Title row -----------------------------------------------
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 4))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text=label_text,
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        # ----- Hint row ------------------------------------------------
        ctk.CTkLabel(
            self,
            text=hint_text,
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))

        # ----- Input row -----------------------------------------------
        placeholder = (
            "e.g. py, js, md, README.md"
            if kind == "target"
            else "e.g. node_modules, .git, package-lock.json"
        )
        self.entry = ctk.CTkEntry(
            self,
            font=("Segoe UI", 13),
            placeholder_text=placeholder,
            placeholder_text_color=TEXT_MUTED,
            border_color=CARD_BORDER,
            border_width=1,
            fg_color=INPUT_BG,
            text_color=TEXT_PRIMARY,
            height=40,
            corner_radius=8,
        )
        self.entry.grid(row=2, column=0, sticky="ew", padx=(20, 10))
        self.entry.bind("<Return>", lambda _e: self.add_from_entry())

        ctk.CTkButton(
            self,
            text="+ Add",
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            height=40, width=90,
            corner_radius=8,
            command=self.add_from_entry,
        ).grid(row=2, column=1, padx=(0, 20))

        # ----- Tags container ------------------------------------------
        self.tags_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tags_frame.grid(row=3, column=0, columnspan=2, sticky="ew",
                             padx=15, pady=(16, 20))
        self.grid_columnconfigure(0, weight=1)

        # Seed with the defaults.
        for tag in (default_tags or []):
            if tag and tag not in self.tags:
                self.tags.append(tag)
        self._redisplay()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_tags(self) -> list[str]:
        """Return a shallow copy of the current tag list."""
        return self.tags[:]

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_filename(name: str) -> bool:
        """Heuristic: does this string look like a filename?

        We treat anything with a dot after the first character as a
        filename, so ``README.md`` and ``.gitignore`` are filenames but
        ``py`` and ``node_modules`` are not.
        """
        stripped = name.lstrip("*").rstrip("/")
        if not stripped:
            return False
        return "." in stripped[1:]

    def _normalize(self, raw: str) -> str:
        """Turn raw user input into a canonical pattern string."""
        raw = raw.strip()
        if not raw:
            return ""

        if self.kind == "target":
            if raw.startswith("*."):
                return raw
            if self._looks_like_filename(raw):
                return raw
            return f"*.{raw.lstrip('.*')}"

        # ignore kind
        if raw.endswith("/"):
            return raw
        if self._looks_like_filename(raw):
            return raw
        return f"{raw}/"

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _describe(kind: str, raw: str) -> tuple[str, str]:
        """Return (display_text, badge) for a tag."""
        if kind == "target":
            if raw.startswith("*."):
                return raw, "EXT"
            return raw, "FILE"
        if raw.endswith("/"):
            return raw[:-1], "DIR"
        return raw, "FILE"

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add_from_entry(self) -> None:
        """Add whatever is currently in the entry field."""
        raw = self.entry.get().strip()
        if not raw:
            return
        normalized = self._normalize(raw)
        if normalized and normalized not in self.tags:
            self.tags.append(normalized)
            self._redisplay()
        self.entry.delete(0, "end")

    def _remove(self, raw: str) -> None:
        """Remove a tag by its raw value."""
        if raw in self.tags:
            self.tags.remove(raw)
            self._redisplay()

    def _toggle(self, raw: str) -> None:
        """Toggle a tag between its two interpretations.

        target:  *.ext  <->  ext   (extension glob <-> literal filename)
        ignore:  dir/   <->  dir   (directory   <-> literal filename)
        """
        if raw not in self.tags:
            return
        if self.kind == "target":
            new = raw[2:] if raw.startswith("*.") else f"*.{raw}"
        else:
            new = raw[:-1] if raw.endswith("/") else f"{raw}/"
        self.tags[self.tags.index(raw)] = new
        self._redisplay()

    def _redisplay(self) -> None:
        """Rebuild the tag widgets from the current list.

        Simplest correct approach: destroy and recreate. Tag counts are
        small (dozens), so this is not a performance concern.
        """
        for w in self.widgets:
            w.destroy()
        self.widgets.clear()

        for i, raw in enumerate(self.tags):
            display_text, badge = self._describe(self.kind, raw)
            w = TagWidget(
                self.tags_frame,
                raw_value=raw,
                display_text=display_text,
                kind=self.kind,
                badge=badge,
                on_toggle=self._toggle,
                on_delete=self._remove,
            )
            # Wrap: 4 chips per row.
            w.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="w")
            self.widgets.append(w)