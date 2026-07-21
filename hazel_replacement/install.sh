#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/sharktopus"
LEGACY_CONFIG_DIR="$HOME/.hazel_replacement"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
OLD_PLIST_NAME="com.user.hazel-replacement.plist"
OLD_PLIST_DEST="$LAUNCHD_DIR/$OLD_PLIST_NAME"
PLIST_NAME="com.user.sharktopus.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/com.user.sharktopus.plist.template"
PLIST_DEST="$LAUNCHD_DIR/$PLIST_NAME"
SHARKTOPUS_BIN="/usr/local/bin/sharktopus"
SP_BIN="/usr/local/bin/sp"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Sharktopus - Installation Script                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}→ Checking for Python 3...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}  ✓ Found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}  ✗ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

echo -e "${YELLOW}→ Installing Sharktopus via uv...${NC}"
if command -v uv &> /dev/null; then
    cd "$SCRIPT_DIR"
    uv tool install --force --editable .
    echo -e "${GREEN}  ✓ Installed via uv tool install${NC}"
else
    echo -e "${RED}  ✗ uv not found. Please install uv.${NC}"
    exit 1
fi

SHARKTOPUS_PATH=$(which sharktopus 2>/dev/null || echo "")
if [ -z "$SHARKTOPUS_PATH" ]; then
    echo -e "${RED}  ✗ sharktopus binary not found after install${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Binary at: $SHARKTOPUS_PATH${NC}"

echo -e "${YELLOW}→ Creating symlinks in /usr/local/bin...${NC}"
mkdir -p /usr/local/bin 2>/dev/null
if ln -sf "$SHARKTOPUS_PATH" "$SHARKTOPUS_BIN" 2>/dev/null; then
    echo -e "${GREEN}  ✓ /usr/local/bin/sharktopus -> $SHARKTOPUS_PATH${NC}"
else
    echo -e "${YELLOW}  → Could not write to /usr/local/bin (needs sudo); using $SHARKTOPUS_PATH directly${NC}"
    SHARKTOPUS_BIN="$SHARKTOPUS_PATH"
fi
if ln -sf "$SHARKTOPUS_PATH" "$SP_BIN" 2>/dev/null; then
    echo -e "${GREEN}  ✓ /usr/local/bin/sp -> $SHARKTOPUS_PATH${NC}"
else
    SP_BIN="$SHARKTOPUS_PATH"
fi

echo -e "${YELLOW}→ Setting up configuration...${NC}"
mkdir -p "$CONFIG_DIR"

if [ -f "$LEGACY_CONFIG_DIR/config.yaml" ] && [ ! -f "$CONFIG_DIR/rules.json" ]; then
    echo -e "${YELLOW}  → Migrating legacy config...${NC}"
    sharktopus migrate
    echo -e "${GREEN}  ✓ Migrated legacy config to $CONFIG_DIR/rules.json${NC}"
elif [ ! -f "$CONFIG_DIR/rules.json" ]; then
    sharktopus list-rules > /dev/null 2>&1 || true
    echo -e "${GREEN}  ✓ Created fresh config at $CONFIG_DIR/rules.json${NC}"
else
    echo -e "${YELLOW}  → Existing config found, keeping it${NC}"
fi

echo -e "${YELLOW}→ Removing old Hazel Replacement service...${NC}"
if launchctl list 2>/dev/null | grep -q "com.user.hazel-replacement"; then
    launchctl unload "$OLD_PLIST_DEST" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Stopped old service${NC}"
else
    echo -e "${YELLOW}  → Old service was not running${NC}"
fi
if [ -f "$OLD_PLIST_DEST" ]; then
    rm -f "$OLD_PLIST_DEST"
    echo -e "${GREEN}  ✓ Removed old plist${NC}"
fi

echo -e "${YELLOW}→ Installing Sharktopus launchd service...${NC}"
if launchctl list 2>/dev/null | grep -q "com.user.sharktopus"; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

mkdir -p "$LAUNCHD_DIR"

if [ -f "$PLIST_TEMPLATE" ]; then
    sed -e "s|__SHARKTOPUS_BIN__|$SHARKTOPUS_BIN|g" \
        -e "s|__INSTALL_PATH__|$SCRIPT_DIR|g" \
        -e "s|__HOME__|$HOME|g" \
        "$PLIST_TEMPLATE" > "$PLIST_DEST"
    chmod 644 "$PLIST_DEST"
    echo -e "${GREEN}  ✓ Installed plist to $PLIST_DEST${NC}"
else
    echo -e "${RED}  ✗ Template not found: $PLIST_TEMPLATE${NC}"
    exit 1
fi

echo -e "${YELLOW}→ Starting service...${NC}"
launchctl load "$PLIST_DEST"

sleep 2
if launchctl list 2>/dev/null | grep -q "com.user.sharktopus"; then
    echo -e "${GREEN}  ✓ Service started successfully${NC}"
else
    echo -e "${RED}  ✗ Service failed to start. Check logs at:${NC}"
    echo -e "${RED}    $CONFIG_DIR/stderr.log${NC}"
    exit 1
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 Installation Complete!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "The service is now running and will start automatically at login."
echo
echo -e "${BLUE}Config:${NC}    $CONFIG_DIR/rules.json"
echo -e "${BLUE}Log:${NC}       $CONFIG_DIR/sharktopus.log"
echo -e "${BLUE}Binary:${NC}    $SHARKTOPUS_BIN (alias: $SP_BIN)"
echo
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  sharktopus status          Check service status"
echo -e "  sharktopus list-rules      List all rules"
echo -e "  sharktopus add-rule ...    Add a new rule"
echo -e "  sharktopus toggle          Toggle service on/off"
echo -e "  sharktopus rules           Open config in editor"
echo -e "  sp status                  (same, using alias)"
echo
