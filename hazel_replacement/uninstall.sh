#!/bin/bash
#
# Hazel Replacement - Uninstallation Script
# ==========================================
# This script removes the Hazel Replacement service.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
CONFIG_DIR="$HOME/.hazel_replacement"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.hazel-replacement.plist"
PLIST_PATH="$LAUNCHD_DIR/$PLIST_NAME"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Hazel Replacement - Uninstallation Script            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Stop the service
echo -e "${YELLOW}→ Stopping service...${NC}"
if launchctl list | grep -q "com.user.hazel-replacement"; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Service stopped${NC}"
else
    echo -e "${YELLOW}  → Service was not running${NC}"
fi

# Remove plist
echo -e "${YELLOW}→ Removing launchd configuration...${NC}"
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo -e "${GREEN}  ✓ Removed $PLIST_PATH${NC}"
else
    echo -e "${YELLOW}  → Plist file not found${NC}"
fi

# Ask about config removal
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
echo -e "The service has been removed."
echo -e "Your watched files in ~/Downloads/drive have NOT been modified."
echo
