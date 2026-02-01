# Ansible Playbooks for Linux Device Setup

This directory contains Ansible playbooks for setting up base configuration on Linux devices (Raspberry Pi 5, Raspberry Pi Zero 2 W, and other Debian-based SBCs).

## Requirements

See [FEATURES/00.md](FEATURES/00.md) for the complete list of requirements and features.

## Directory Structure

```
ansible/
├── playbook.yml              # Main playbook
├── inventory.ini             # Inventory file (configure your hosts here)
├── tasks/                    # Modular task files
│   ├── install_packages.yml
│   ├── copy_config_files.yml
│   ├── setup_zsh.yml
│   ├── setup_neovim.yml
│   ├── setup_docker.yml
│   ├── setup_golang.yml
│   ├── setup_tailscale.yml
│   ├── setup_python.yml
│   ├── setup_vscode_server.yml
│   └── setup_ssh_keys.yml
└── files/
    ├── remote_zshrc          # Zsh config for remote devices
    └── init.lua              # (Optional) Neovim config
```

## Quick Start

### 1. Configure Inventory

Edit `inventory.ini` to add your devices:

```ini
[raspberry_pi_5]
rpi5.local ansible_user=jadennation

[raspberry_pi_zero_2w]
rpizero1.local ansible_user=jadennation
rpizero2.local ansible_user=jadennation
```

### 2. Test Connection

```bash
ansible all -i inventory.ini -m ping
```

### 3. Run the Playbook

Run the full setup on all hosts:

```bash
ansible-playbook -i inventory.ini playbook.yml
```

Run on specific hosts or groups:

```bash
ansible-playbook -i inventory.ini playbook.yml --limit raspberry_pi_5
ansible-playbook -i inventory.ini playbook.yml --limit rpizero1.local
```

### 4. Run Specific Tasks

You can use tags to run specific parts of the playbook. While tags aren't currently defined in the playbook, you can run individual task files by importing them separately.

## What Gets Installed

### System Packages
- **Core utilities**: curl, wget, git, build-essential
- **Terminal tools**: tree, ripgrep, bat, fzf, htop, fd-find
- **Development**: Python 3, Zsh, GitHub CLI (gh)

### Applications
- **Neovim** (v0.10.4) with Lua config, Treesitter, and lazy.nvim
- **Docker** (latest) with compose plugin
- **Golang** (v1.23.4) and `skate` CLI
- **Tailscale** VPN client
- **VS Code Server** for remote tunneling
- **UV** Python package manager

### Configuration Files Copied
- Zsh configuration files (aliases, functions, colors, constants, custom_path)
- Modified `.zshrc` for remote devices
- SSH authorized keys
- Neovim init.lua (if provided)

## Variables

You can customize versions and paths by modifying variables in `playbook.yml`:

```yaml
vars:
  go_version: "1.23.4"
  nvim_version: "0.10.4"
  user_home: "/home/{{ ansible_user }}"
  target_user: "{{ ansible_user }}"
```

## Post-Installation

### Tailscale Setup
After installation, connect to Tailscale:
```bash
sudo tailscale up
```

### VS Code Tunnel
To start a VS Code tunnel:
```bash
code tunnel
```

### Docker
User is added to docker group, but you'll need to log out and back in for group membership to take effect.

## Troubleshooting

### SSH Connection Issues
- Ensure your SSH key is added: `ssh-add ~/.ssh/id_westbankbankrupt`
- Test direct SSH: `ssh jadennation@rpizero1.local`

### Ansible Python Interpreter
If you get Python interpreter errors, ensure Python 3 is installed on the remote device:
```bash
ssh user@host "sudo apt update && sudo apt install -y python3"
```

### File Not Found Errors
Some config files are copied with `ignore_errors: yes`. If they don't exist locally, they'll be skipped without failing the playbook.

## Development

To add new tasks:
1. Create a new file in `tasks/` directory
2. Import it in `playbook.yml` using `import_tasks`

## License

This is internal tooling for personal use.
