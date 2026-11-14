#!/usr/bin/env bash
# Build the Linux app folder (dist/beam_calculator/) and pack it as a .tar.gz.
# Usage, from any folder, with the project's venv active:
#   packaging/build_linux.sh [version]      (default: git describe)
set -euo pipefail

cd "$(dirname "$0")/.."
version="${1:-$(git describe --tags --always --dirty)}"
archive="dist/beam_calculator-${version}-linux-x86_64.tar.gz"

python -m PyInstaller --noconfirm --clean packaging/pyinstaller.spec
# Menu entry and icon for GNOME/KDE: the .tar.gz user runs install.sh once
install -m 644 packaging/linux/beam_calculator.desktop dist/beam_calculator/
install -m 755 packaging/linux/install.sh dist/beam_calculator/
tar -C dist -czf "$archive" beam_calculator
echo "$archive"
