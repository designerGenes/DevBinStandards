#!/usr/bin/env bash
# Capture from Pi camera and push H264 to local RTMP server
# Lower bitrate for memory-constrained Pi Zero 2 W

set -euo pipefail

# Conservative defaults to reduce CPU on Pi Zero 2 W
WIDTH=${WIDTH:-960}
HEIGHT=${HEIGHT:-540}
FPS=${FPS:-10}
BITRATE=${BITRATE:-1500000}
RTMP_URL=${RTMP_URL:-rtmp://127.0.0.1:1935/camera}

# Run the capture pipeline once and let systemd handle restarts on failure.
# Software rotate 90° clockwise with ffmpeg (decode -> transpose -> re-encode)
# Scale to capture target size and use a lightweight encoding configuration.

echo "Starting capture at ${WIDTH}x${HEIGHT}@${FPS}fps bitrate=${BITRATE}..."

# Build AWB options
if [ "$AWBMODE" = "auto" ]; then
    AWB_OPT="--awb auto"
else
    AWB_OPT="--awbgains $AWBGAINS"
fi

# Handle rotation natively in rpicam-vid if possible
# Note: rpicam-vid --rotation supports 0 and 180 on all sensors.
# 90/270 might not be supported in hardware on all setups, but is still better handled there if allowed.
# If ROTATION is not set, default to 0.
ROTATION=${ROTATION:-0}

# rpicam-vid command with native H.264 encoding (hardware accelerated)
# Piped to ffmpeg for FLV encapsulation only (copy codec) to minimize CPU usage
rpicam-vid -t 0 --width "$WIDTH" --height "$HEIGHT" --framerate "$FPS" \
    --bitrate "$BITRATE" --inline --nopreview --shutter "$SHUTTER" --gain "$GAIN" \
    $AWB_OPT --ev "$EV" --metering "$METERING" --saturation "$SATURATION" \
    --denoise "$DENOISE" --brightness "$BRIGHTNESS" --contrast "$CONTRAST" \
    --rotation "$ROTATION" -o - \
    | ffmpeg -nostdin -f h264 -i - \
        -c:v copy \
        -f flv "$RTMP_URL"

# If ffmpeg exits the script will exit; systemd will restart the service according to the unit file.

