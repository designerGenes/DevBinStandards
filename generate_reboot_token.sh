#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE=/etc/pi_reboot_token

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo or as root"
  exit 1
fi

# generate token
TOKEN=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')

# write token to file with strict perms
printf "%s\n" "$TOKEN" > "$TOKEN_FILE"
# Allow the 'jadennation' service user to read the token
chown root:jadennation "$TOKEN_FILE"
chmod 640 "$TOKEN_FILE"

# Add sudoers entry for controlled reboot/shutdown commands
SUDO_FILE=/etc/sudoers.d/camera_reboot
cat > "$SUDO_FILE" <<EOF
# Allow the pi camera UI user to run shutdown/reboot without password
jadennation ALL=(root) NOPASSWD: /sbin/shutdown, /sbin/reboot
EOF
chmod 440 "$SUDO_FILE"

echo "Token written to $TOKEN_FILE"
echo "Token value: $TOKEN"

echo "Done. Keep the token secret. Use it as: Authorization: Bearer $TOKEN"