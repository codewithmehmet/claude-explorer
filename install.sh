#!/bin/bash
# Claude Explorer - One-line installer
# Usage: curl -sSL <url>/install.sh | bash
# Or:    git clone <repo> && cd claude-explorer && ./install.sh

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "  ╔══════════════════════════════════╗"
echo "  ║     Claude Explorer Installer    ║"
echo "  ║  Browse your .claude history     ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${NC}"

# Determine install directory
INSTALL_DIR="${CLAUDE_EXPLORER_DIR:-$HOME/.claude-explorer}"
BIN_DIR="$HOME/.local/bin"

echo -e "${BLUE}[1/4]${NC} Setting up install directory..."
mkdir -p "$INSTALL_DIR"

# Copy source files if running from repo
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo -e "${BLUE}[1/4]${NC} Copying from local repo..."
    cp -r "$SCRIPT_DIR/claude_explorer" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/"
fi

echo -e "${BLUE}[2/4]${NC} Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"

echo -e "${BLUE}[3/4]${NC} Installing dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --quiet textual

# Install the package
cd "$INSTALL_DIR"
"$INSTALL_DIR/.venv/bin/pip" install --quiet -e .

echo -e "${BLUE}[4/4]${NC} Creating launcher..."
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/claude-explorer" << 'LAUNCHER'
#!/bin/bash
exec "$HOME/.claude-explorer/.venv/bin/python" -m claude_explorer "$@"
LAUNCHER
chmod +x "$BIN_DIR/claude-explorer"

# Ensure ~/.local/bin is in PATH
SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
if ! grep -qF 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo -e "${BLUE}Added ~/.local/bin to PATH in $(basename $SHELL_RC)${NC}"
fi

echo ""
echo -e "${GREEN}Claude Explorer installed successfully!${NC}"
echo ""
echo -e "  Run: ${PURPLE}claude-explorer${NC}"
echo ""
echo -e "  Keyboard shortcuts:"
echo -e "    ${BLUE}d${NC} Dashboard  ${BLUE}s${NC} Sessions  ${BLUE}f${NC} Search"
echo -e "    ${BLUE}p${NC} Projects   ${BLUE}l${NC} Plans     ${BLUE}t${NC} Stats"
echo -e "    ${BLUE}q${NC} Quit       ${BLUE}Esc${NC} Back"
echo ""
echo -e "  ${BLUE}Note:${NC} Restart your terminal or run: source ~/.bashrc"
