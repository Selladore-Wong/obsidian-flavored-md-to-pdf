#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/obsidian-flavored-md-to-pdf"
TARGET_DIR="${HOME}/.local/bin"
TARGET="${TARGET_DIR}/obsidian-flavored-md-to-pdf"

mkdir -p "$TARGET_DIR"
mkdir -p "$INSTALL_DIR"

install -m 755 "$SCRIPT_DIR/obsidian-flavored-md-to-pdf" "$INSTALL_DIR/obsidian-flavored-md-to-pdf"
install -m 755 "$SCRIPT_DIR/render_obsidian_flavored_md_to_pdf.py" "$INSTALL_DIR/render_obsidian_flavored_md_to_pdf.py"
install -m 644 "$SCRIPT_DIR/obsidian-minimal-print.css" "$INSTALL_DIR/obsidian-minimal-print.css"
ln -sfn "$INSTALL_DIR/obsidian-flavored-md-to-pdf" "$TARGET"

echo "Installed: $TARGET"
echo "Files: $INSTALL_DIR"
echo "If needed, add ~/.local/bin to PATH."
