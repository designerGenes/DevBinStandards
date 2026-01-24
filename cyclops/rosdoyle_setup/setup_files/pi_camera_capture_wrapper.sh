#!/usr/bin/env bash
set -euo pipefail

# Configuration
CONF=/etc/pi_camera_capture.conf
if [ -f "$CONF" ]; then source "$CONF"; fi

# Export variables for the Python script
export WIDTH=${WIDTH:-640}
export HEIGHT=${HEIGHT:-360}
export FPS=${FPS:-5}
export BITRATE=${BITRATE:-700000}
export RTMP_URL=${RTMP_URL:-rtmp://127.0.0.1:1935/camera}
export ROTATION=${ROTATION:-0}

# New Controls for Low Light / Tuning
export AE_METERING=${AE_METERING:-Matrix}
export AE_EXPOSURE=${AE_EXPOSURE:-Normal}
export BRIGHTNESS=${BRIGHTNESS:-0.0}
export CONTRAST=${CONTRAST:-1.0}
export SHARPNESS=${SHARPNESS:-1.0}

LOG=/var/log/pi_camera_picamera2.log

# Ensure log is writable
mkdir -p "$(dirname "$LOG")"
touch "$LOG"

echo "$(date) Wrapper starting..." >> $LOG

while true; do
    echo "$(date) Launching pi_camera_capture.py" >> $LOG
    /usr/bin/python3 -u /usr/local/bin/pi_camera_capture.py >> $LOG 2>&1
    EXIT_CODE=$?
    echo "$(date) pi_camera_capture.py exited with code $EXIT_CODE" >> $LOG
    
    # Prevent tight loop on immediate failure
    sleep 3
done