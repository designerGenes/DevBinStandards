loadenv() {
  if [[ -f .env ]]; then
    while IFS='=' read -r key value; do
      # skip comments and empty lines
      [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
      export "$key"="${value%\"}"
    done <.env
    echo "Loaded environment variables from .env"
  else
    echo ".env file not found in current directory"
  fi
}

# Mask: first 4 chars ... last 2 (handles very short safely)
_mask_api_value() {
  local s="$1" n=${#1}
  if ((n <= 3)); then
    # too short — show first then ellipsis
    echo "${s:0:1}...${s: -1}"
  elif ((n <= 6)); then
    echo "${s:0:2}...${s: -1}"
  else
    echo "${s:0:4}...${s: -2}"
  fi
}

# Resolve special values: REF:path:key or DEFER_PARENT
_resolve_env_value() {
  local key="$1"
  local val="$2"
  if [[ "$val" == \\* ]]; then
    # escaped, remove \
    val="${val:1}"
    echo "$val"
  elif [[ "$val" == REF:* ]]; then
    local ref="${val#REF:}"
    local path="${ref%%:*}"
    local refkey="${ref#*:}"
    if [[ "$path" != /* || "$path" != $HOME* ]]; then
      print -P "${FG_RED}Invalid path: $path${RESET}" >&2
      return 1
    fi
    if [[ ! -f "$path" ]]; then
      print -P "${FG_RED}Referenced .env not found: $path${RESET}" >&2
      return 1
    fi
    local resolved=""
    while IFS= read -r line || [[ -n "$line" ]]; do
      if [[ $line == $refkey=* ]]; then
        resolved="${line#*=}"
        break
      fi
    done < "$path"
    if [[ -z "$resolved" ]]; then
      print -P "${FG_RED}Key $refkey not found in $path${RESET}" >&2
      return 1
    fi
    # strip quotes
    resolved="${resolved%\"}"
    resolved="${resolved#\"}"
    resolved="${resolved%\'}"
    resolved="${resolved#\'}"
    echo "$resolved"
  elif [[ "$val" == DEFER_PARENT ]]; then
    local dir="$PWD"
    local depth=0
    while [[ "$dir" != "/" && "$dir" != "$HOME" && $depth -lt 5 ]]; do
      dir="$(dirname "$dir")"
      if [[ -f "$dir/.env" ]]; then
        local resolved=""
        while IFS= read -r line || [[ -n "$line" ]]; do
          if [[ $line == $key=* ]]; then
            resolved="${line#*=}"
            break
          fi
        done < "$dir/.env"
        if [[ -n "$resolved" ]]; then
          resolved="${resolved%\"}"
          resolved="${resolved#\"}"
          resolved="${resolved%\'}"
          resolved="${resolved#\'}"
          echo "$resolved"
          return 0
        fi
      fi
      ((depth++))
    done
    print -P "${FG_RED}Key $key not found in parent directories${RESET}" >&2
    return 1
  else
    echo "$val"
  fi
}

# Load .env into current shell; print only NEW/CHANGED keys (colorized via colors.zsh)
loadenv_verbose_masked() {
  local file="${1:-.env}"
  [[ -f "$file" ]] || return 0

  local line key val cur masked show

  # Parse simple KEY=VAL / export KEY=VAL; supports single/double quotes; not multiline
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    line="${line#export }"

    key="${line%%=*}"
    val="${line#*=}"

    # trim whitespace
    key="${key//[[:space:]]/}"
    val="${val#[[:space:]]}"

    # strip matching quotes
    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" == \'*\' && "$val" == *\' ]]; then
      val="${val:1:${#val}-2}"
    fi

    # resolve special values
    local resolved_val="$(_resolve_env_value "$key" "$val")" || continue

    # value before change
    eval "cur=\${$key}"

    if [[ "$cur" != "$resolved_val" ]]; then
      export "$key=$resolved_val"

      # Secret-ish keys: contains PRIVATE or API_KEY or APIKEY
      if [[ "$key" == *PRIVATE* || "$key" == *API_KEY* || "$key" == *APIKEY* ]]; then
        masked="$(_mask_api_value "$resolved_val")"
        # key yellow, value white
        print -P "loaded ${FG_SUNSET_ORANGE}${key}${RESET}=${FG_WHITE}${masked}${RESET}"
      else
        # key green, value white
        # print -P "loaded ${FG_LIME_GREEN}${key}${RESET}=${FG_WHITE}${resolved_val}${RESET}"
        print -P "loaded ${FG_LIME_GREEN}${key}${RESET}"
      fi
    fi
  done <"$file"
}

# Auto-load on directory change if a .env exists
_env_try_load_on_cd() {
  [[ -f .env ]] && loadenv_verbose_masked .env
}

autoload -Uz add-zsh-hook
add-zsh-hook chpwd _env_try_load_on_cd
# Also run once at shell start for the current dir
_env_try_load_on_cd
# ---------------------------------------------------------------
