#!/usr/bin/env python3
import os
import time
import signal
import sys
from picamera2 import Picamera2
from picamera2.outputs import FfmpegOutput
from picamera2.encoders import H264Encoder
import libcamera
from libcamera import Transform

# Configuration from Environment
WIDTH = int(os.environ.get("WIDTH", 960))
HEIGHT = int(os.environ.get("HEIGHT", 540))
FPS = int(os.environ.get("FPS", 10))
BITRATE = int(os.environ.get("BITRATE", 1500000))
RTMP_URL = os.environ.get("RTMP_URL", "rtmp://127.0.0.1:1935/camera")
ROTATION = int(os.environ.get("ROTATION", 0))

# Image Controls
AE_METERING = os.environ.get("AE_METERING", "Matrix")
AE_EXPOSURE = os.environ.get("AE_EXPOSURE", "Normal")
BRIGHTNESS = float(os.environ.get("BRIGHTNESS", 0.0))
CONTRAST = float(os.environ.get("CONTRAST", 1.0))
SHARPNESS = float(os.environ.get("SHARPNESS", 1.0))

def main():
    print(f"Starting Picamera2 capture: {WIDTH}x{HEIGHT} @ {FPS}fps, {BITRATE} bps -> {RTMP_URL}")
    print(f"Rotation: {ROTATION}")
    print(f"Controls: Metering={AE_METERING}, Exposure={AE_EXPOSURE}, Bright={BRIGHTNESS}, Contrast={CONTRAST}")

    picam2 = Picamera2()

    # Configure Transform
    transform = Transform()
    if ROTATION == 2:
        transform = Transform(hflip=True, vflip=True)
    elif ROTATION == 1 or ROTATION == 3:
        print("Warning: 90/270 degree rotation not supported by hardware. Using 0.")

    # Control Mapping
    # Access controls via libcamera.controls
    metering_map = {
        "Matrix": libcamera.controls.AeMeteringModeEnum.Matrix,
        "Spot": libcamera.controls.AeMeteringModeEnum.Spot,
        "CentreWeighted": libcamera.controls.AeMeteringModeEnum.CentreWeighted,
        "Custom": libcamera.controls.AeMeteringModeEnum.Custom
    }
    exposure_map = {
        "Normal": libcamera.controls.AeExposureModeEnum.Normal,
        "Short": libcamera.controls.AeExposureModeEnum.Short,
        "Long": libcamera.controls.AeExposureModeEnum.Long,
        "Custom": libcamera.controls.AeExposureModeEnum.Custom
    }

    controls = {
        "FrameRate": FPS,
        "AeMeteringMode": metering_map.get(AE_METERING, libcamera.controls.AeMeteringModeEnum.Matrix),
        "AeExposureMode": exposure_map.get(AE_EXPOSURE, libcamera.controls.AeExposureModeEnum.Normal),
        "Brightness": BRIGHTNESS,
        "Contrast": CONTRAST,
        "Sharpness": SHARPNESS
    }

    # Configure video
    config = picam2.create_video_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "YUV420"},
        controls=controls,
        transform=transform
    )
    
    picam2.configure(config)
    picam2.start()

    # Encoder
    # bitrate in bps
    # iperiod: Keyframe interval. For HLS 2s segments, we want I-frame every 2s.
    encoder = H264Encoder(bitrate=BITRATE, iperiod=FPS*2)

    # Output
    output = FfmpegOutput(f"-f flv {RTMP_URL}")

    print("Starting recording...")
    picam2.start_recording(encoder, output)

    # Wait for signal
    stop_event = False
    def signal_handler(sig, frame):
        nonlocal stop_event
        print("Signal received, stopping...")
        stop_event = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        while not stop_event:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Stopping recording...")
        picam2.stop_recording()
        picam2.stop()
        print("Exited.")

if __name__ == "__main__":
    main()
