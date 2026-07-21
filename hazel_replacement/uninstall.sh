#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONFIG_DIR="$HOME/.config/sharktopus"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.sharktopus.plist"
PLIST_PATH="$LAUNCHD_DIR/$PLIST_NAME"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Sharktopus - Uninstallation Script                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}→ Stopping service...${NC}"
if launchctl list 2>/dev/null | grep -q "com.user.sharktopus"; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Service stopped${NC}"
else
    echo -e "${YELLOW}  → Service was not running${NC}"
fi

echo -e "${YELLOW}→ Removing launchd configuration...${NC}"
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo -e "${GREEN}  ✓ Removed $PLIST_PATH${NC}"
else
    echo -e "${YELLOW}  → Plist file not found${NC}"
fi

echo -e "${YELLOW}→ Removing symlinks...${NC}"
rm -f /usr/local/bin/sharktopus 2>/dev/null || true
rm -f /usr/local/bin/sp 2>/dev/null || true
echo -e "${GREEN}  ✓ Removed /usr/local/bin/sharktopus and /usr/local/bin/sp${NC}"

echo -e "${YELLOW}→ Uninstalling uv tool...${NC}"
if command -v uv &> /dev/null; then
    uv tool uninstall sharktopus 2>/dev/null || true
    echo -e "${GREEN}  ✓ Uninstalled via uv${NC}"
fi

echo
echo -e "${YELLOW}Do you want to remove configuration and logs? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}  ✓ Removed $CONFIG_DIR${NC}"
    fi
else
    echo -e "${YELLOW}  → Keeping configuration at $CONFIG_DIR${NC}"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               Uninstallation Complete!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "Sharktopus has been removed."
echo -e "Your watched files have NOT been modified."
echo
