# Prefer Zsh's native path array handling to auto-deduplicate
typeset -U path

# Go environment variables
export GOPATH="$HOME/go"
export GOBIN="$GOPATH/bin"

# Linux-specific paths
path=(
  # Local user binaries
  $HOME/.local/bin
  $HOME/DEV/bin
  $HOME/bin

  # Go
  $GOBIN
  $HOME/.local/opt/go/bin

  # Node.js (webi installed)
  $HOME/.local/opt/node/bin

  # Cargo/Rust
  $HOME/.cargo/bin

  # System paths
  /usr/local/bin
  /usr/local/sbin
  /usr/bin
  /bin
  /usr/sbin
  /sbin

  # Keep existing path entries
  $path
)

export PATH
