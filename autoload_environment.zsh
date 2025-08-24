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

    # value before change
    eval "cur=\${$key}"

    if [[ "$cur" != "$val" ]]; then
      export "$key=$val"

      # Secret-ish keys: contains PRIVATE or API_KEY or APIKEY
      if [[ "$key" == *PRIVATE* || "$key" == *API_KEY* || "$key" == *APIKEY* ]]; then
        masked="$(_mask_api_value "$val")"
        # key yellow, value white
        print -P "loaded ${FG_SUNSET_ORANGE}${key}${RESET}=${FG_WHITE}${masked}${RESET}"
      else
        # key green, value white
        print -P "loaded ${FG_LIME_GREEN}${key}${RESET}=${FG_WHITE}${val}${RESET}"
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
