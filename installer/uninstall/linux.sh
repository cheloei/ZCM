#!/bin/sh
# ============================================================================
# ZCombine Uninstaller - Linux
# Removes: PATH symlinks, shell rc PATH entries, desktop entry, icon,
#          and the installation folder itself. Also cleans up any legacy
#          file-manager integrations from older versions.
# ============================================================================

set -u

APP_KEY="ZCombineManager"

# Resolve our own path robustly, following symlinks. This matters because
# the user may invoke us via ~/.local/bin/zcm-uninstall (a symlink), and in
# that case `dirname "$0"` would wrongly resolve to ~/.local/bin.
SELF="$(readlink -f "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"

BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo
echo "============================================================"
echo "                 ZCombine Uninstaller"
echo "============================================================"
echo
echo "Install dir : $INSTALL_DIR"
echo

# ---------------------------------------------------------------------------
# 1. Symlinks on PATH
# ---------------------------------------------------------------------------
for name in zcm zcm-uninstall; do
    target="$BIN_DIR/$name"
    if [ -L "$target" ] || [ -e "$target" ]; then
        rm -f "$target" && echo "[+] Removed $target"
    fi
done

# ---------------------------------------------------------------------------
# 2. Remove the PATH line we added to shell rc files
#
# The installer appends:
#     # Added by ZCombine installer
#     export PATH="$HOME/.local/bin:$PATH"     (bash/zsh)
#     fish_add_path $HOME/.local/bin           (fish)
#
# We remove the marker line, plus the immediately-following line only if it
# mentions .local/bin. Anything else in the rc file is left untouched.
# ---------------------------------------------------------------------------
remove_zcm_path_entry() {
    rc="$1"
    [ -f "$rc" ] || return 0
    grep -q "^# Added by ZCombine installer" "$rc" 2>/dev/null || return 0

    tmp="${rc}.zcm.tmp.$$"
    awk '
        BEGIN { skip_next = 0 }
        /^# Added by ZCombine installer[ \t]*$/ { skip_next = 1; next }
        skip_next == 1 {
            skip_next = 0
            if (index($0, ".local/bin") > 0) next
        }
        { print }
    ' "$rc" > "$tmp" && mv "$tmp" "$rc"
    echo "[+] Cleaned PATH entry from $rc"
}

remove_zcm_path_entry "$HOME/.bashrc"
remove_zcm_path_entry "$HOME/.zshrc"
remove_zcm_path_entry "$HOME/.config/fish/config.fish"

# ---------------------------------------------------------------------------
# 3. Desktop entry
# ---------------------------------------------------------------------------
if [ -f "$APPS_DIR/zcm.desktop" ]; then
    rm -f "$APPS_DIR/zcm.desktop"
    echo "[+] Removed desktop entry."
fi

# ---------------------------------------------------------------------------
# 4. Icon
# ---------------------------------------------------------------------------
if [ -f "$ICONS_DIR/zcm.png" ]; then
    rm -f "$ICONS_DIR/zcm.png"
    echo "[+] Removed icon."
fi

# ---------------------------------------------------------------------------
# 5. Legacy file-manager integrations (installed by older versions)
# ---------------------------------------------------------------------------
LEGACY_KDE="$HOME/.local/share/kio/servicemenus/zcm-setup.desktop"
LEGACY_NAUTILUS_SCRIPT="$HOME/.local/share/nautilus/scripts/ZCombine Setup"
LEGACY_NAUTILUS_EXT="$HOME/.local/share/nautilus-python/extensions/zcm.py"

[ -f "$LEGACY_KDE" ] && rm -f "$LEGACY_KDE" && \
    echo "[+] Removed legacy KDE service menu."
[ -f "$LEGACY_NAUTILUS_SCRIPT" ] && rm -f "$LEGACY_NAUTILUS_SCRIPT" && \
    echo "[+] Removed legacy Nautilus script."
[ -f "$LEGACY_NAUTILUS_EXT" ] && rm -f "$LEGACY_NAUTILUS_EXT" && \
    echo "[+] Removed legacy Nautilus extension."

# ---------------------------------------------------------------------------
# 6. Refresh caches
# ---------------------------------------------------------------------------
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$APPS_DIR" 2>/dev/null
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null

# ---------------------------------------------------------------------------
# 7. Schedule self-deletion of the install folder
# ---------------------------------------------------------------------------
if [ -d "$INSTALL_DIR" ]; then
    echo "[+] Scheduling cleanup of $INSTALL_DIR..."
    nohup sh -c "sleep 2; rm -rf '$INSTALL_DIR'" >/dev/null 2>&1 &
fi

echo
echo "[OK] ZCombine has been uninstalled."
echo "     Open a new terminal for the PATH change to take effect."
echo
exit 0