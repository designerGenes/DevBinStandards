#!/bin/bash

# Get screen dimensions
screen_dimensions=$(osascript -e 'tell application "Finder" to get bounds of window of desktop')
screen_width=$(echo "$screen_dimensions" | cut -d ',' -f 3 | xargs)
screen_height=$(echo "$screen_dimensions" | cut -d ',' -f 4 | xargs)

# Check for a --random flag
randomize=false
only_ghostty=false

for arg in "$@"; do
  case $arg in
    --random)
      randomize=true
      shift
      ;;
    --only-ghostty)
      only_ghostty=true
      shift
      ;;
    *)
      # Unknown option or positional argument
      shift
      ;;
  esac
done

echo "Screen width: $screen_width"
echo "Screen height: $screen_height"

# List of target applications
all_apps=("Google Chrome" "VLC" "Google Photos" "Ghostty" "iTerm")
running_apps=()

# Find which applications are running
if [ "$only_ghostty" = true ]; then
  if osascript -e "application \"Ghostty\" is running" | grep -q "true"; then
    running_apps+=("Ghostty")
  fi
else
  for app_name in "${all_apps[@]}"; do
    # pgrep is not reliable for GUI apps, using osascript is better
    if osascript -e "application \"$app_name\" is running" | grep -q "true"; then
      running_apps+=("$app_name")
    fi
  done
fi

# If no relevant apps are running, exit
if [ ${#running_apps[@]} -eq 0 ]; then
  echo "No target applications are running."
  exit 0
fi

# Calculate the width for each window based on running apps
num_apps=${#running_apps[@]}
window_width=$((screen_width / num_apps))
x_position=0

# Randomize the order if the flag was passed
if [ "$randomize" = true ]; then
  echo "Randomizing window order..."
  # Use awk/sort for a portable shuffle, as shuf is not on macOS
  running_apps=($(printf "%s\n" "${running_apps[@]}" | awk 'BEGIN{srand();}{print rand() "\t" $0}' | sort -n | cut -f2-))
fi

echo "Resizing running applications: ${running_apps[*]}"

# Loop through the running applications and resize their windows
for app_name in "${running_apps[@]}"; do
  echo "Processing $app_name: x_pos=$x_position, width=$window_width"
  
  # Use UI scripting for Ghostty as a fallback
  if [ "$app_name" == "Ghostty" ]; then
    osascript -e "
      tell application \"System Events\"
        tell process \"$app_name\"
          set frontmost to true
          try
            set position of front window to {$x_position, 0}
            set size of front window to {$window_width, $screen_height}
          on error msg
            log \"Could not resize Ghostty with UI scripting: \" & msg
          end try
        end tell
      end tell
    "
  else
    # Standard handling for other apps
osascript -e "
      tell application \"$app_name\"
        activate
        try
          if (count of windows) > 0 then
            set bounds of window 1 to {$x_position, 0, $x_position + $window_width, $screen_height}
          end if
        on error msg
          -- Fallback for apps that don't like 'window 1'
          try
            set bounds of front window to {$x_position, 0, $x_position + $window_width, $screen_height}
          on error msg2
            log \"Could not resize \" & \"$app_name\" & \": \" & msg2
          end try
        end try
      end tell
    "
  fi
  
  x_position=$((x_position + window_width))
done

