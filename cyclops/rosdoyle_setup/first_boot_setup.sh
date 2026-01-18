#!/bin/bash
# First-boot setup script for rosdoyle security camera
# This script should be run as root after first boot

set -e

HOSTNAME="rosdoyle"
USERNAME="jadennation"
HOME_DIR="/home/$USERNAME"

echo "=========================================="
echo "  rosdoyle Security Camera Setup"
echo "=========================================="

# Set hostname
echo "Setting hostname to $HOSTNAME..."
hostnamectl set-hostname "$HOSTNAME"
echo "127.0.1.1       $HOSTNAME" >> /etc/hosts

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y \
    zsh \
    git \
    vim \
    htop \
    tmux \
    curl \
    wget \
    ffmpeg \
    python3-pip \
    python3-venv \
    libcamera-apps \
    rpicam-apps \
    v4l-utils \
    v4l2loopback-dkms

# Install Tailscale
echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

# Create media user for mediamtx
echo "Creating media user..."
useradd -r -s /usr/sbin/nologin -M media 2>/dev/null || true

# Create node_exporter user
echo "Creating node_exporter user..."
useradd -r -s /usr/sbin/nologin -M node_exporter 2>/dev/null || true

# Download and install MediaMTX
echo "Installing MediaMTX..."
MEDIAMTX_VERSION="1.15.6"
MEDIAMTX_ARCH="arm64v8"
cd /tmp
wget -q "https://github.com/bluenviron/mediamtx/releases/download/v${MEDIAMTX_VERSION}/mediamtx_v${MEDIAMTX_VERSION}_linux_${MEDIAMTX_ARCH}.tar.gz"
tar -xzf "mediamtx_v${MEDIAMTX_VERSION}_linux_${MEDIAMTX_ARCH}.tar.gz"
mv mediamtx /usr/local/bin/
chmod +x /usr/local/bin/mediamtx
rm -f "mediamtx_v${MEDIAMTX_VERSION}_linux_${MEDIAMTX_ARCH}.tar.gz" mediamtx.yml LICENSE

# Download and install Node Exporter
echo "Installing Node Exporter..."
NODE_EXPORTER_VERSION="1.9.1"
cd /tmp
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-arm64.tar.gz"
tar -xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-arm64.tar.gz"
mv "node_exporter-${NODE_EXPORTER_VERSION}.linux-arm64/node_exporter" /usr/local/bin/
chmod +x /usr/local/bin/node_exporter
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-arm64" "node_exporter-${NODE_EXPORTER_VERSION}.linux-arm64.tar.gz"

# Set zsh as default shell for user
echo "Setting zsh as default shell..."
chsh -s /usr/bin/zsh "$USERNAME"

# Add user to required groups
echo "Adding user to required groups..."
usermod -aG video,audio,gpio,i2c,spi,dialout,plugdev,input,render,netdev "$USERNAME"

# Configure swap
echo "Configuring swap..."
sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
systemctl restart dphys-swapfile

# Copy configuration files from boot partition
echo "Copying configuration files..."
BOOT_SETUP="/boot/firmware/setup_files"

if [ -d "$BOOT_SETUP" ]; then
    # MediaMTX config
    cp "$BOOT_SETUP/mediamtx.yml" /etc/mediamtx.yml
    
    # Camera capture script
    cp "$BOOT_SETUP/pi_camera_capture.sh" /usr/local/bin/
    chmod +x /usr/local/bin/pi_camera_capture.sh
    
    # Systemd services
    cp "$BOOT_SETUP/mediamtx.service" /etc/systemd/system/
    cp "$BOOT_SETUP/pi_camera_capture.service" /etc/systemd/system/
    cp "$BOOT_SETUP/node_exporter.service" /etc/systemd/system/
    cp "$BOOT_SETUP/crash-recovery.service" /etc/systemd/system/
    
    # Enable services
    systemctl daemon-reload
    systemctl enable mediamtx.service
    systemctl enable pi_camera_capture.service
    systemctl enable node_exporter.service
    systemctl enable crash-recovery.service
fi

# Setup DEV/bin structure
echo "Setting up DEV/bin..."
mkdir -p "$HOME_DIR/dev/bin"
chown -R "$USERNAME:$USERNAME" "$HOME_DIR/dev"

# Clone DevBinStandards repo
echo "Cloning DevBinStandards..."
sudo -u "$USERNAME" git clone https://github.com/designerGenes/DevBinStandards.git "$HOME_DIR/dev/bin" 2>/dev/null || true

# Setup SSH authorized keys
echo "Setting up SSH keys..."
mkdir -p "$HOME_DIR/.ssh"
chmod 700 "$HOME_DIR/.ssh"
if [ -f "$BOOT_SETUP/authorized_keys" ]; then
    cp "$BOOT_SETUP/authorized_keys" "$HOME_DIR/.ssh/"
fi
chmod 600 "$HOME_DIR/.ssh/authorized_keys" 2>/dev/null || true
chown -R "$USERNAME:$USERNAME" "$HOME_DIR/.ssh"

# Copy zshrc
if [ -f "$BOOT_SETUP/zshrc" ]; then
    cp "$BOOT_SETUP/zshrc" "$HOME_DIR/.zshrc"
    chown "$USERNAME:$USERNAME" "$HOME_DIR/.zshrc"
fi

# Setup zsh completions
mkdir -p "$HOME_DIR/.zsh"
sudo -u "$USERNAME" git clone https://github.com/zsh-users/zsh-completions.git "$HOME_DIR/.zsh/zsh-completions" 2>/dev/null || true
sudo -u "$USERNAME" git clone https://github.com/zsh-users/zsh-autosuggestions.git "$HOME_DIR/.zsh/zsh-autosuggestions" 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Reboot: sudo reboot"
echo "2. Connect to Tailscale: sudo tailscale up"
echo "3. Start camera services: sudo systemctl start mediamtx pi_camera_capture"
echo ""
echo "Stream URLs after setup:"
echo "  RTSP: rtsp://<ip>:8554/camera"
echo "  HLS:  http://<ip>:8888/camera"
echo ""
