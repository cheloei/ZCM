#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ZCombine Manager (zcm) - GUI configuration tool for the ZCombine batch script.

Usage:
    zcm setup              # Open the graphical configuration window
    zcm --version / -v     # Show version and exit
"""

import os
import sys
import re
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

# ----------------------------------------------------------------------
# Version
# ----------------------------------------------------------------------
__version__ = "1.0.0"

# ----------------------------------------------------------------------
# Helper to get resource path (for PyInstaller bundled files)
# ----------------------------------------------------------------------
def get_resource_path(relative_path):
    """
    Get absolute path to a resource, works for development and for PyInstaller.
    When bundled, PyInstaller stores files in a temporary folder pointed by sys._MEIPASS.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In development, use the directory of the script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ----------------------------------------------------------------------
# Path to the template file (bundled with the executable)
# ----------------------------------------------------------------------
TEMPLATE_FILE = get_resource_path("zcm-template.bat")

# ----------------------------------------------------------------------
# Default sample tags (always start fresh)
# ----------------------------------------------------------------------
DEFAULT_TARGET_TAGS = ["py", "txt", "json"]
DEFAULT_IGNORE_TAGS = ["node_modules", ".git", "dist"]

# ----------------------------------------------------------------------
# Theme Colors (Modern Dark)
# ----------------------------------------------------------------------
BG_COLOR = "#0D0D15"
CARD_COLOR = "#1A1A2E"
ACCENT_COLOR = "#6C63FF"
HOVER_COLOR = "#5A52D9"
TEXT_PRIMARY = "#E8EDFF"
TEXT_SECONDARY = "#A0B0C0"

# Initialize CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ----------------------------------------------------------------------
# Helper to open GitHub link
# ----------------------------------------------------------------------
def open_link(url):
    """Open the given URL in the default web browser."""
    try:
        webbrowser.open(url)
    except Exception as e:
        messagebox.showerror("Error", f"Could not open link:\n{e}")

# ----------------------------------------------------------------------
# Tag Widget (individual tag with remove button)
# ----------------------------------------------------------------------
class TagWidget(ctk.CTkFrame):
    def __init__(self, parent, text, on_delete, is_target=True):
        """
        A rounded tag with a label and a close button.
        - is_target: if True, uses target colors; otherwise ignore colors.
        """
        tag_bg = "#2A2A3A" if is_target else "#1E3A2E"
        super().__init__(parent, fg_color=tag_bg, corner_radius=12)
        
        self.label = ctk.CTkLabel(
            self, 
            text=text, 
            font=("Segoe UI", 12, "bold"), 
            text_color=TEXT_PRIMARY
        )
        self.label.pack(side="left", padx=(12, 4), pady=6)
        
        self.btn = ctk.CTkButton(
            self, 
            text="✕", 
            width=24, 
            height=24, 
            corner_radius=12,
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent", 
            hover_color="#FF4B4B", 
            text_color=TEXT_PRIMARY,
            command=on_delete
        )
        self.btn.pack(side="left", padx=(0, 6), pady=6)

# ----------------------------------------------------------------------
# Tag List Component (manages a list of tags with add/remove)
# ----------------------------------------------------------------------
class TagList(ctk.CTkFrame):
    def __init__(self, parent, label_text, tag_type='ignore', default_tags=None, **kwargs):
        """
        tag_type: 'target' or 'ignore'
        - target: stores extensions (e.g., 'py') and displays as '*.py'
        - ignore: stores folder names directly
        """
        super().__init__(parent, fg_color=CARD_COLOR, corner_radius=15, 
                         border_width=1, border_color="#2A2A4A", **kwargs)
        self.tag_type = tag_type
        self.tags = []
        self.widgets = []
        self.default_tags = default_tags or []
        
        # Label
        lbl = ctk.CTkLabel(
            self, 
            text=label_text, 
            font=("Segoe UI", 14, "bold"), 
            text_color=TEXT_SECONDARY
        )
        lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))
        
        # Input field with hint
        placeholder = "e.g. py, js, html" if tag_type == 'target' else "e.g. node_modules, .git, dist"
        self.entry = ctk.CTkEntry(
            self, 
            font=("Segoe UI", 13), 
            placeholder_text=placeholder,
            border_color="#3A3A5A",
            fg_color="#12121D",
            text_color=TEXT_PRIMARY,
            height=36
        )
        self.entry.grid(row=1, column=0, sticky="ew", padx=(20, 10))
        self.entry.bind('<Return>', lambda e: self.add_tag())
        
        # Add button
        self.add_btn = ctk.CTkButton(
            self, 
            text="➕ Add", 
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT_COLOR, 
            hover_color=HOVER_COLOR,
            height=36,
            width=90,
            command=self.add_tag
        )
        self.add_btn.grid(row=1, column=1, padx=(0, 20))
        
        # Container for tags (wrap layout)
        self.tags_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tags_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(15, 20))
        
        self.grid_columnconfigure(0, weight=1)
        
        # Initialize with defaults if any
        if not self.tags:
            self.set_tags(self.default_tags)
    
    def _format_display(self, raw):
        """Format tag for display: add '*. ' for target extensions."""
        return f"*.{raw}" if self.tag_type == 'target' else raw
    
    def _clean_input(self, text):
        """Normalize user input, removing leading '*.', dots, and spaces."""
        text = text.strip()
        if self.tag_type == 'target':
            # Remove any leading '*.', '.', or '*' characters
            text = text.lstrip('.*')
        return text.strip()
    
    def add_tag(self, tag=None):
        """Add a new tag (from entry or passed explicitly)."""
        tag = tag if tag is not None else self.entry.get().strip()
        if not tag: return
        raw = self._clean_input(tag)
        if not raw or raw in self.tags: return
        
        self.tags.append(raw)
        self._redisplay()
        self.entry.delete(0, 'end')
    
    def remove_tag(self, tag):
        """Remove a tag by its raw value."""
        if tag in self.tags:
            self.tags.remove(tag)
            self._redisplay()
    
    def get_tags(self):
        """Return the raw list of tags."""
        return self.tags[:]
    
    def set_tags(self, tags):
        """Set the entire list of tags (clears previous)."""
        cleaned = []
        for t in tags:
            raw = self._clean_input(t)
            if raw:
                cleaned.append(raw)
        self.tags = cleaned
        self._redisplay()
    
    def _redisplay(self):
        """Rebuild the tag widgets."""
        for w in self.widgets:
            w.destroy()
        self.widgets.clear()
        
        is_target = (self.tag_type == 'target')
        for i, raw in enumerate(self.tags):
            display_text = self._format_display(raw)
            w = TagWidget(
                self.tags_frame, 
                display_text, 
                lambda r=raw: self.remove_tag(r),
                is_target=is_target
            )
            # Wrap every 4 columns
            w.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="w")
            self.widgets.append(w)

# ----------------------------------------------------------------------
# Main Application Window
# ----------------------------------------------------------------------
class ZcmConfigWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ZCombine Setup")
        self.geometry("740x720")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        
        # ---------- Header ----------
        header_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=110)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)
        
        # Accent line at bottom of header
        accent_line = ctk.CTkFrame(header_frame, fg_color=ACCENT_COLOR, height=3, corner_radius=0)
        accent_line.place(relx=0, rely=1, anchor="sw", relwidth=1)
        
        ctk.CTkLabel(
            header_frame, 
            text="⚡ ZCombine Setup", 
            font=("Segoe UI", 22, "bold"), 
            text_color=TEXT_PRIMARY
        ).place(x=30, y=20)
        
        ctk.CTkLabel(
            header_frame, 
            text="Create batch file to combine your project files into one clean output.", 
            font=("Segoe UI", 12), 
            text_color=ACCENT_COLOR
        ).place(x=35, y=55)
        
        # GitHub link (clickable, styled)
        github_url = "https://github.com/cheloei/ZCM"
        github_label = ctk.CTkLabel(
            header_frame,
            text=github_url,
            font=("Segoe UI", 10, "underline"),
            text_color=ACCENT_COLOR,
            cursor="hand2"
        )
        github_label.place(x=35, y=82)
        github_label.bind("<Button-1>", lambda e: open_link(github_url))
        
        # ---------- Main scrollable body ----------
        self.main_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#3A3A5A",
            scrollbar_button_hover_color="#5A5A7A"
        )
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=25)
        
        # Always start fresh - ignore any existing zcm.bat file
        existing_target, existing_ignore = [], []  # No existing values, always from defaults
        
        # Target Extensions
        self.target_tags = TagList(
            self.main_frame, 
            label_text="📄 Target Extensions", 
            tag_type='target', 
            default_tags=DEFAULT_TARGET_TAGS
        )
        self.target_tags.pack(fill="x", pady=(0, 20))
        # Do NOT override with existing values - keep defaults
        
        # Ignore Directories
        self.ignore_tags = TagList(
            self.main_frame, 
            label_text="📁 Ignore Directories", 
            tag_type='ignore', 
            default_tags=DEFAULT_IGNORE_TAGS
        )
        self.ignore_tags.pack(fill="x", pady=(0, 20))
        # Do NOT override with existing values - keep defaults
        
        # Gitignore checkbox
        self.gitignore_var = ctk.BooleanVar(value=True)
        cb_frame = ctk.CTkFrame(self.main_frame, fg_color=CARD_COLOR, corner_radius=12, 
                                border_width=1, border_color="#2A2A4A")
        cb_frame.pack(fill="x", pady=(0, 25))
        
        ctk.CTkCheckBox(
            cb_frame, 
            text="🔒 Add zcm.bat and zcm_output.txt to .gitignore", 
            variable=self.gitignore_var,
            font=("Segoe UI", 13),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR,
            border_color="#3A3A5A"
        ).pack(anchor="w", padx=20, pady=15)
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(
            btn_frame, 
            text="✨ Generate Script", 
            font=("Segoe UI", 14, "bold"),
            fg_color=ACCENT_COLOR,
            hover_color=HOVER_COLOR,
            height=45,
            width=200,
            command=self.generate
        ).pack(side="left", padx=(0, 15))
        
        ctk.CTkButton(
            btn_frame, 
            text="✖ Exit", 
            font=("Segoe UI", 14, "bold"),
            fg_color="transparent",
            hover_color="#1E1E2E",
            border_width=2,
            border_color="#3A3A5A",
            text_color=TEXT_PRIMARY,
            height=45,
            width=120,
            command=self.destroy
        ).pack(side="left")
        
        # ---------- Status Bar ----------
        self.status_var = ctk.StringVar(value="⚡ Ready")
        status_frame = ctk.CTkFrame(self, fg_color="#12121A", corner_radius=0, height=35)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            status_frame, 
            textvariable=self.status_var, 
            font=("Segoe UI", 11), 
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=20, pady=5)
        
        # ---------- Set window icon (using bundled icon.ico) ----------
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(default=icon_path)
            except Exception:
                pass  # If icon fails, continue without it

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    def _add_to_gitignore(self, filenames):
        """Add filenames to .gitignore in the current directory."""
        gitignore_path = os.path.join(os.getcwd(), ".gitignore")
        existing_lines = []
        if os.path.isfile(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    existing_lines = [line.rstrip('\n') for line in f.readlines()]
            except Exception as e:
                self.status_var.set(f"⚠️ Could not read .gitignore: {e}")
                return False
        
        added_any = False
        to_add = [f for f in filenames if f.strip()]
        for fname in to_add:
            if not any(line.strip() == fname for line in existing_lines):
                existing_lines.append(fname)
                added_any = True
        
        if added_any:
            try:
                with open(gitignore_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write('\n'.join(existing_lines))
                    if existing_lines: f.write('\n')
                self.status_var.set("✅ .gitignore updated")
                return True
            except Exception as e:
                self.status_var.set(f"❌ Could not write .gitignore: {e}")
                return False
        else:
            self.status_var.set("ℹ️ .gitignore already up-to-date")
            return True
    
    def generate(self):
        """Generate the zcm.bat file from the template and current tags."""
        target_list = self.target_tags.get_tags()
        ignore_list = self.ignore_tags.get_tags()
        
        if not target_list:
            messagebox.showerror("Error", "At least one target file extension is required.")
            return
        
        target_str = ' '.join(f"*.{ext}" for ext in target_list)
        ignore_str = ' '.join(ignore_list)
        
        if not os.path.isfile(TEMPLATE_FILE):
            messagebox.showerror(
                "Error", 
                f"Template file not found:\n{TEMPLATE_FILE}\n"
                "Ensure 'zcm-template.bat' is bundled with the executable."
            )
            self.status_var.set("❌ Template missing")
            return
        
        try:
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                template = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Could not read template: {e}")
            return
        
        new_content = template.replace("{{target}}", target_str).replace("{{ignore}}", ignore_str)
        output_path = os.path.join(os.getcwd(), "zcm.bat")
        
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                f.write(new_content)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write zcm.bat: {e}")
            self.status_var.set("❌ Error writing file")
            return
        
        if self.gitignore_var.get():
            self._add_to_gitignore(["zcm.bat", "zcm_output.txt"])
        
        self.status_var.set("✅ Successfully generated zcm.bat")
        
        # Show success message and close the window automatically
        messagebox.showinfo(
            "Success", 
            f"zcm.bat successfully created/updated in:\n{os.getcwd()}\n\nThe application will now close."
        )
        self.destroy()  # Close the window

# ----------------------------------------------------------------------
# Command-line entry point
# ----------------------------------------------------------------------
def main():
    # Version handling
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v"):
        print(f"ZCombine Manager v{__version__}")
        sys.exit(0)
    
    # Normal operation: run GUI if 'setup' is passed
    if len(sys.argv) > 1 and sys.argv[1].lower() == "setup":
        app = ZcmConfigWindow()
        app.mainloop()
    else:
        print(__doc__)
        print("\nTo configure ZCombine, run: zcm setup")
        sys.exit(1)

if __name__ == "__main__":
    main()