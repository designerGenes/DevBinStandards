#!/bin/bash

# Crash Detector - Monitors system accessibility and responsiveness
# Detects potential crashes by checking various system indicators

LOG_FILE="/var/log/crash_detector.log"
STATE_FILE="/tmp/crash_detector_state"
LAST_BOOT_FILE="/tmp/last_boot_time"

# Logging function
log_event() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [CRASH_DETECTOR] $1" | sudo tee -a "$LOG_FILE"
}

# Get current boot time
CURRENT_BOOT=$(stat -c %Y /proc/1)

# Check if this is first run after boot
if [ ! -f "$LAST_BOOT_FILE" ] || [ "$(cat "$LAST_BOOT_FILE" 2>/dev/null)" != "$CURRENT_BOOT" ]; then
    echo "$CURRENT_BOOT" > "$LAST_BOOT_FILE"
    
    # Check if this was an unexpected reboot
    if [ -f "$STATE_FILE" ]; then
        LAST_STATE=$(cat "$STATE_FILE")
        if [ "$LAST_STATE" != "clean_shutdown" ]; then
            log_event "CRASH DETECTED: System rebooted without clean shutdown (last state: $LAST_STATE)"
            log_event "Boot time: $(date -d "@$CURRENT_BOOT")"
            
            # Log hardware info for troubleshooting
            log_event "Hardware info at boot:"
            if command -v vcgencmd >/dev/null 2>&1; then
                log_event "  Temperature: $(vcgencmd measure_temp)"
                log_event "  Throttling: $(vcgencmd get_throttled)"
                log_event "  Memory split: $(vcgencmd get_mem arm) / $(vcgencmd get_mem gpu)"
            fi
            log_event "  Memory: $(free -h | grep Mem)"
            log_event "  Uptime: $(uptime)"
        fi
    fi
    
    echo "boot_detected" > "$STATE_FILE"
fi

# Update state to show we're running
echo "running" > "$STATE_FILE"

# Test system responsiveness
RESPONSIVENESS_TESTS=(
    "ls /proc"
    "ps aux"
    "free"
    "df /"
)

FAILED_TESTS=0
for test in "${RESPONSIVENESS_TESTS[@]}"; do
    if ! timeout 10 $test >/dev/null 2>&1; then
        log_event "RESPONSIVENESS FAILURE: Command '$test' failed or timed out"
        ((FAILED_TESTS++))
    fi
done

if [ "$FAILED_TESTS" -gt 2 ]; then
    log_event "CRITICAL: Multiple responsiveness tests failed ($FAILED_TESTS/${#RESPONSIVENESS_TESTS[@]})"
    echo "unresponsive" > "$STATE_FILE"
fi

# Check for kernel messages indicating problems
if dmesg | tail -20 | grep -i "panic\|oops\|segfault\|killed\|oom" | grep "$(date +%b\ %d)" >/dev/null 2>&1; then
    log_event "WARNING: Recent kernel messages indicate system issues"
    dmesg | tail -20 | grep -i "panic\|oops\|segfault\|killed\|oom" | while read -r line; do
        log_event "  KERNEL: $line"
    done
fi

# Check for signs of filesystem corruption
if [ -f /forcefsck ] || [ -f /.autofsck ]; then
    log_event "WARNING: Filesystem check indicators present"
fi

# Update state file with clean status if we made it this far
echo "healthy" > "$STATE_FILE"
