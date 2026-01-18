export CLICOLOR_FORCE=1
export HOMEBREW_NO_ENV_HINTS=1
export GIT_ASKPASS="$HOME/.git-tools/git-askpass-helper.sh"
export TREE_IGNORABLES="-I 'node_modules' -I 'venv' -I '.git' -I '.github' -I '.python_packages' -I 'Pods'"
export AZURE_DEV_COLLECT_TELEMETRY="no"

# Regex patterns
export REGEX_PHONE='\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
export REGEX_EMAIL='\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
export REGEX_URL='\bhttps?://[^\s]+\b'
export REGEX_IP='\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
