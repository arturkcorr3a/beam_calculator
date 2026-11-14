#!/usr/bin/env bash
# Add beam_calculator to the applications menu of the current user, with its
# icon (the .tar.gz has no installer). Run it from the extracted folder:
#   ./install.sh               add the menu entry
#   ./install.sh --uninstall   remove it (the folder itself is not touched)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
entry="${XDG_DATA_HOME:-$HOME/.local/share}/applications/beam_calculator.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$entry"
    echo "Removido do menu: $entry"
    exit 0
fi

icon="$here/_internal/resources/logo/png/icon/beam-app-icon-512.png"
mkdir -p "$(dirname "$entry")"
# The template names the RPM's command and themed icon; point both into this folder
sed -e "s|^Exec=.*|Exec=\"$here/beam_calculator\"|" \
    -e "s|^Icon=.*|Icon=$icon|" \
    "$here/beam_calculator.desktop" > "$entry"
echo "Adicionado ao menu: $entry"
