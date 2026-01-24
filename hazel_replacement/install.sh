#!/bin/bash
#
# Hazel Replacement - Installation Script
# ========================================
# This script installs the Hazel Replacement service to run at login.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.hazel_replacement"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="com.user.hazel-replacement.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/com.user.hazel-replacement.plist.template"
PLIST_DEST="$LAUNCHD_DIR/$PLIST_NAME"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Hazel Replacement - Installation Script              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Check for Python 3
echo -e "${YELLOW}→ Checking for Python 3...${NC}"
if command -v python3 &> /dev/null; then
    SYSTEM_PYTHON=$(which python3)
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}  ✓ Found: $PYTHON_VERSION at $SYSTEM_PYTHON${NC}"
else
    echo -e "${RED}  ✗ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

# Setup virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_PATH="$VENV_DIR/bin/python3"

echo -e "${YELLOW}→ Setting up virtual environment...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}  ✓ Created virtual environment${NC}"
else
    echo -e "${GREEN}  ✓ Virtual environment exists${NC}"
fi

# Install dependencies in venv
echo -e "${YELLOW}→ Installing Python dependencies...${NC}"
"$VENV_DIR/bin/pip" install --quiet watchdog PyYAML xattr
echo -e "${GREEN}  ✓ Dependencies installed${NC}"

# Create config directory
echo -e "${YELLOW}→ Setting up configuration...${NC}"
mkdir -p "$CONFIG_DIR"

# Copy config if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cp "$SCRIPT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"
    echo -e "${GREEN}  ✓ Config installed to $CONFIG_DIR/config.yaml${NC}"
else
    echo -e "${YELLOW}  → Existing config found, keeping it${NC}"
fi

# Create watch directories from config
echo -e "${YELLOW}→ Creating watch directories...${NC}"
WATCH_DIR="$HOME/Downloads/drive"
mkdir -p "$WATCH_DIR"
mkdir -p "$WATCH_DIR/vid"
mkdir -p "$WATCH_DIR/img"
mkdir -p "$WATCH_DIR/tmp"
echo -e "${GREEN}  ✓ Created $WATCH_DIR and subdirectories${NC}"

# Stop existing service if running
echo -e "${YELLOW}→ Checking for existing service...${NC}"
if launchctl list | grep -q "com.user.hazel-replacement"; then
    echo -e "${YELLOW}  → Stopping existing service...${NC}"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Stopped existing service${NC}"
fi

# Create LaunchAgents directory if needed
mkdir -p "$LAUNCHD_DIR"

# Generate plist from template
echo -e "${YELLOW}→ Installing launchd service...${NC}"

if [ -f "$PLIST_TEMPLATE" ]; then
    sed -e "s|__PYTHON_PATH__|$PYTHON_PATH|g" \
        -e "s|__INSTALL_PATH__|$SCRIPT_DIR|g" \
        -e "s|__HOME__|$HOME|g" \
        "$PLIST_TEMPLATE" > "$PLIST_DEST"
    
    # Set correct permissions
    chmod 644 "$PLIST_DEST"
    echo -e "${GREEN}  ✓ Installed plist to $PLIST_DEST${NC}"
else
    echo -e "${RED}  ✗ Template not found: $PLIST_TEMPLATE${NC}"
    exit 1
fi

# Load the service
echo -e "${YELLOW}→ Starting service...${NC}"
launchctl load "$PLIST_DEST"

# Verify service is running
sleep 2
if launchctl list | grep -q "com.user.hazel-replacement"; then
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
echo -e "${BLUE}Watch Directory:${NC} $WATCH_DIR"
echo -e "${BLUE}Config File:${NC}     $CONFIG_DIR/config.yaml"
echo -e "${BLUE}Log File:${NC}        $CONFIG_DIR/hazel.log"
echo
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Check status:     launchctl list | grep hazel"
echo -e "  View logs:        tail -f $CONFIG_DIR/hazel.log"
echo -e "  Stop service:     launchctl unload $PLIST_DEST"
echo -e "  Start service:    launchctl load $PLIST_DEST"
echo -e "  Uninstall:        ./uninstall.sh"
echo
