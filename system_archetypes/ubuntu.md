## Things our basic ubuntu system archetype provides

- Zsh as the default shell
- Kubernetes tools: kubectl, k9s, helm
- Docker and docker-compose
- Git and Git LFS
- Golang
- Node.js and npm
- Python 3 and pip.  UV for managing multiple python versions and dependencies
- Neovim with LunarVim configuration
- headless
- RG, fd, bat, exa, htop, jq, and other useful cli tools
- ssh setup with public key authentication
- wifi setup
- UFW firewall setup
- Basic system hardening
- User setup with sudo privileges
- Need to pull the aliases/functions/etc from github designerGenes/DevBinStandards.git repo 
- our .zshrc should source those files so we adopt the custom functions and aliases such as rezsh, reA, vimZ, etc
