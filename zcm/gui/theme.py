"""Color palette — "Midnight Aurora" theme (v2).

All GUI colors live here so that restyling the app is a one-file
change. Values are hex strings suitable for passing directly to
CustomTkinter widgets.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------
BG_COLOR    = "#0A0E1A"    # deep space navy — main window background
CARD_COLOR  = "#141B2E"    # elevated surface — cards and the header
CARD_BORDER = "#232C44"    # subtle border around cards and inputs
INPUT_BG    = "#0E1424"    # recessed input field background
STATUS_BG   = "#070A14"    # status bar — darkest surface

# ---------------------------------------------------------------------------
# Brand and actions
# ---------------------------------------------------------------------------
ACCENT_COLOR   = "#7C5CFF"    # violet — primary action (buttons, links)
ACCENT_HOVER   = "#6748E8"    # darker violet on hover
ACCENT_2       = "#00E0B8"    # aurora teal — info / success accents
ACCENT_2_HOVER = "#00C4A0"    # darker teal on hover

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
TEXT_PRIMARY   = "#F5F7FF"    # high-contrast text
TEXT_SECONDARY = "#8892B0"    # muted body text
TEXT_MUTED     = "#5A6480"    # very low contrast — hints, footer

# ---------------------------------------------------------------------------
# Tag chips
# ---------------------------------------------------------------------------
TAG_TARGET_BG = "#1B2244"    # violet-tinted background for target chips
TAG_TARGET_FG = "#A8B0FF"    # "EXT" / "FILE" badge color for target chips
TAG_IGNORE_BG = "#0E2B27"    # teal-tinted background for ignore chips
TAG_IGNORE_FG = "#5FE8C9"    # "DIR" / "FILE" badge color for ignore chips
TAG_DELETE    = "#FF4B7D"    # coral/pink — destructive hover on delete buttons