#!/bin/zsh

get_rpi_temp() {
  # Bail out silently if vcgencmd isn't available
  command -v vcgencmd >/dev/null 2>&1 || return

  # Extract Celsius reading (e.g. 42.7)
  local c
  c=$(vcgencmd measure_temp 2>/dev/null | sed -E "s/temp=([0-9.]+)'C/\1/") || return

  # Convert to Fahrenheit with awk (no extra deps) and format to one decimal
  local f
  f=$(awk "BEGIN {printf \"%.1f\", ($c * 9 / 5) + 32}")

  # Output without a newline so PS1 stays tidy
  printf "%s°F/%s°C" "$f" "$c"
}

manbat() {
  man "$@" | col -bx | bat --paging=always --language=man
}

cdp() {
  if [[ -f "$1" ]]; then
    cd "$(dirname "$1")" || return 1
  elif [[ -d "$1" ]]; then
    cd "$1" || return 1
  fi
}

addAlias() {
  # Ensure an argument was provided
  if [ -z "$1" ]; then
    echo "Usage: addAlias key=value"
    return 1
  fi

  # Extract key and value (split on the first '=')
  local pair="$1"
  local key="${pair%%=*}"
  local value="${pair#*=}"

  # Strip any surrounding quotes on value (will re-add)
  value="${value%\"}"
  value="${value#\"}"

  local alias_line="alias $key=\"$value\""

  echo "$alias_line" >>"$HOME/DEV/bin/aliases.zsh"

  # Quietly re-source the file (no output)
  source "$HOME/DEV/bin/aliases.zsh" >/dev/null 2>&1

  echo "Alias '$key' added and reloaded."
}

gitQuick() {
  local msg="${1:-Quick commit}"
  git add .
  git commit -m "$msg"
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  echo "Quick commit made on branch $branch"
}

gb() {
  # Get current branch name
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

  if [[ -z "$branch" ]]; then
    # Only show error if not in raw mode
    if [[ "$1" != "-r" && "$1" != "--raw" ]]; then
      echo "Not in a git repository."
    fi
    return 1
  fi

  # Check for raw flag
  if [[ "$1" == "-r" || "$1" == "--raw" ]]; then
    echo "$branch"
    return 0
  fi

  # Define gentle, visually consistent colors
  local colors
  colors=(
    '%F{81}'   # teal-ish
    '%F{111}'  # soft violet
    '%F{180}'  # tan
    '%F{67}'   # steel blue
    '%F{109}'  # muted turquoise
    '%F{181}'  # pale peach
    '%F{146}'  # lilac
  )
  local reset='%f'

  # Split branch by "/"
  local parts
  IFS='/' parts=("${(@s:/:)branch}")

  local output=""
  local i=1
  for part in "${parts[@]}"; do
    local color="${colors[((i-1)%${#colors[@]}+1)]}"
    output+="${color}${part}${reset}"
    ((i++))

    if (( i <= ${#parts[@]} + 0 )); then
      output+="${reset}/"
    fi
  done

  print -P "$output"
}


register_script() {
    SCRIPT_PATH="$1"
    # Check for input
    if [[ -z "$SCRIPT_PATH" || ! -f "$SCRIPT_PATH" ]]; then
      echo "❌ Error: Please provide a valid .sh file path."
      exit 1
    fi

    # Expand full path
    FULL_PATH="$(realpath "$SCRIPT_PATH")"

    # Make script executable
    chmod +x "$FULL_PATH"
    echo "✅ Made executable: $FULL_PATH"

    # Define target
    ZSHRC="$HOME/.zshrc"
    SOURCE_LINE="source $FULL_PATH"

    # Check if already present
    if grep -Fxq "$SOURCE_LINE" "$ZSHRC"; then
      echo "ℹ️ Already sourced in $ZSHRC"
    else
      # Insert at the top
      sed -i.bak "1s|^|$SOURCE_LINE\n|" "$ZSHRC"
      echo "✅ Added to the top of $ZSHRC"
    fi
}

# Functions from funcs.sh that don't conflict
pwdc() {
  # Get current directory
  local dry 
  dry=$(pwd)

  # Define gentle, visually consistent colors
  local colors
  colors=(
    '%F{81}'   # teal-ish
    '%F{111}'  # soft violet
    '%F{180}'  # tan
    '%F{67}'   # steel blue
    '%F{109}'  # muted turquoise
    '%F{181}'  # pale peach
    '%F{146}'  # lilac
  )
  local reset='%f'

  # Split directory part by "/"
  local parts
  IFS='/' parts=("${(@s:/:)dry}")

  local output=""
  local i=1
  for part in "${parts[@]}"; do
    local color="${colors[((i-1)%${#colors[@]}+1)]}"
    output+="${color}${part}${reset}"
    ((i++))
    if (( i <= ${#parts[@]} + 0 )); then
      output+="${reset}/"
    fi
  done

  print -P "$output"
}

rezsh() {
  echo "reloaded ZSH"
  exec zsh
}

print_colors() {
  echo "Defined Colors:"
  local var val name
  for var in ${(k)parameters}; do
    if [[ "$var" == FG_* ]]; then
      val="${(P)var}"
      name="${var#FG_}"
      print -P "${val}${(l:20:: :)name} → Sample text${RESET}"
    fi
  done
}

gpN() {
  # function saves current git branch and creates a remote branch to track the local branch, using the same name
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [[ -z "$branch" ]]; then
    echo "Not in a git repository."
    return 1
  fi
  git push -u origin "$branch" && echo "Remote branch '$branch' created and tracking set."
}

# Lazy Load Conda
# Only adds Conda to PATH when you type 'conda' or 'mamba'
conda() {
    echo "Initializing Conda..."
    
    # 1. Source the official Miniforge activation scripts
    # This replaces the messy hook code you saw earlier
    if [ -f "/Users/jadennation/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/Users/jadennation/miniforge3/etc/profile.d/conda.sh"
    fi

    if [ -f "/Users/jadennation/miniforge3/etc/profile.d/mamba.sh" ]; then
        . "/Users/jadennation/miniforge3/etc/profile.d/mamba.sh"
    fi

    # 2. Unset these temporary functions so the real commands take over
    unset -f conda
    unset -f mamba

    # 3. Run the command you actually typed
    conda "$@"
}

# Optional: Make 'mamba' trigger the same loading
mamba() {
    conda "$@"
}
