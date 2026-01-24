#!/bin/zsh

# -----------------------------------------------------------------------------
# Agnostic Ripgrep Formatting Templates
# Focus: Layout, Legibility, and Data Extraction
# -----------------------------------------------------------------------------

# Helper: Render Zsh color codes (%F{...}) from stdin
_expand_colors() {
  while IFS= read -r line; do
    print -P "$line"
  done
}

# Usage: rg_tree "pattern" [path]
# Group matches by file with a bold, distinct header.
# Good for scanning which files are most affected.
rg_tree() {
  local pattern="$1"
  shift
  local target="${1:-.}"
  
  print -P "${FG_TEAL}Mapping matches for: ${FG_WHITE}${pattern}${RESET}"
  
  # --heading: Group by file
  # --line-number: Show lines
  # --color: Force color for piping
  # We pipe through _expand_colors because we inject %F codes via sed
  rg --heading --line-number --color=always --smart-case "$pattern" "$target" \
    | sed "s/^/${FG_WARM_GRAY}│ ${RESET}/" \
    | _expand_colors
}

# Usage: rg_context "pattern" [lines_of_context] [path]
# Shows matches with context blocks and visible separators.
# Default context: 3 lines.
rg_context() {
  local pattern="$1"
  local ctx="${2:-3}"
  local target="${3:-.}"

  print -P "${FG_SOFT_VIOLET}Contextual search (${ctx} lines): ${FG_WHITE}${pattern}${RESET}"

  rg --context "$ctx" --line-number --color=always --smart-case \
     --heading --context-separator "────" \
     "$pattern" "$target"
}

# Usage: rg_extract "pattern" [path]
# Returns ONLY the matching text, sorted and unique.
# Great for: extracting specific IDs, keys, or values.
rg_extract() {
  local pattern="$1"
  local target="${2:-.}"

  print -P "${FG_SKY_BLUE}Extracting unique values: ${FG_WHITE}${pattern}${RESET}"

  # -o: Only match
  # -N: No line number
  # --no-filename: Don't print filename
  rg -o --no-filename --no-line-number --smart-case "$pattern" "$target" \
    | sort \
    | uniq \
    | while read -r line; do
        print -P "${FG_LIME_GREEN}➜ ${FG_WHITE}${line}${RESET}"
      done
}

# Usage: rg_table "pattern" [path]
# Formats results as an aligned table: FILE | LINE | CONTENT
# Requires 'column' command.
rg_table() {
  local pattern="$1"
  local target="${2:-.}"

  print -P "${FG_TAN}Tabular view for: ${FG_WHITE}${pattern}${RESET}"

  # Output format: file:line:content
  # We use sed to replace the first two colons with pipes for 'column' to process
  rg --line-number --no-heading --color=always --smart-case "$pattern" "$target" \
    | sed 's/:/ | /' \
    | sed 's/:/ | /' \
    | column -t -s '|' \
    | head -n 100 # Safety limit for table rendering
    
  echo # newline
  print -P "${FG_WARM_GRAY}(Showing top 100 matches)${RESET}"
}

# Usage: rg_stats "pattern" [path]
# Shows a leaderboard of files with the most matches.
rg_stats() {
  local pattern="$1"
  local target="${2:-.}"

  print -P "${FG_ROSE}Hit count statistics for: ${FG_WHITE}${pattern}${RESET}"

  rg -c --smart-case "$pattern" "$target" \
    | sort -t: -k2 -nr \
    | awk -F: -v color="${FG_ROSE}" -v reset="${RESET}" \
      '{ printf "%s%4s hits%s │ %s\n", color, $2, reset, $1 }' \
    | _expand_colors
}

# Usage: rg_help
# Lists available ripgrep templates.
rg_help() {
  print -P "${FG_TEAL}Ripgrep Formatting Templates:${RESET}"
  print -P "  ${FG_LIME_GREEN}rg_tree${RESET}    'pat' [path] - Grouped by file (tree view)"
  print -P "  ${FG_LIME_GREEN}rg_context${RESET} 'pat' [N]    - Block view with N lines context"
  print -P "  ${FG_LIME_GREEN}rg_extract${RESET} 'pat' [path] - Unique value extractor (sorted)"
  print -P "  ${FG_LIME_GREEN}rg_table${RESET}   'pat' [path] - Aligned tabular output"
  print -P "  ${FG_LIME_GREEN}rg_stats${RESET}   'pat' [path] - Hit count leaderboard per file"
}
