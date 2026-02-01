# Quick Reference Guide

## Prerequisites

1. **Ansible installed on control machine (your Mac)**:
   ```bash
   brew install ansible
   ```

2. **SSH access to target devices**:
   - SSH key configured: `~/.ssh/id_westbankbankrupt`
   - SSH access to devices working: `ssh jadennation@<device-ip>`

3. **Python3 on target devices** (usually pre-installed on Raspberry Pi OS):
   ```bash
   sudo apt update && sudo apt install -y python3
   ```

## Configuration

### 1. Edit Inventory File

Edit [inventory.ini](inventory.ini) with your device details:

```ini
[raspberry_pi_5]
rpi5.local ansible_user=jadennation

[raspberry_pi_zero_2w]
rpizero1.local ansible_user=jadennation
```

You can use:
- Hostnames (e.g., `rpi5.local`)
- IP addresses (e.g., `192.168.1.100`)
- Tailscale names (e.g., `rpizero1.tailscale-name.ts.net`)

### 2. Test Connection

```bash
cd /Users/jadennation/DEV/bin/ansible
ansible all -i inventory.ini -m ping
```

Expected output:
```
rpi5.local | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## Running the Playbook

### Full Setup (All Hosts)

```bash
ansible-playbook -i inventory.ini playbook.yml
```

### Specific Host Group

```bash
# Only Raspberry Pi 5 devices
ansible-playbook -i inventory.ini playbook.yml --limit raspberry_pi_5

# Only Raspberry Pi Zero 2W devices
ansible-playbook -i inventory.ini playbook.yml --limit raspberry_pi_zero_2w
```

### Single Host

```bash
ansible-playbook -i inventory.ini playbook.yml --limit rpi5.local
```

### Dry Run (Check Mode)

See what would change without applying:

```bash
ansible-playbook -i inventory.ini playbook.yml --check --diff
```

### Using Makefile

```bash
make ping         # Test connectivity
make check        # Dry run
make setup        # Full setup
make test-rpi5    # Setup Pi 5 only
make test-zero    # Setup Zero 2W only
```

## What Gets Installed

| Category | Component | Version |
|----------|-----------|---------|
| Editor | Neovim | 0.10.4 |
| Shell | Zsh | Latest |
| Container | Docker + Compose | Latest |
| Language | Golang | 1.23.4 |
| Language | Python 3 | System |
| Package Mgr | UV (Python) | Latest |
| VPN | Tailscale | Latest |
| CLI Tools | gh, tree, ripgrep, bat, fzf, htop, fd | Latest |
| Remote Dev | VS Code Server | Latest |
| Note Taking | skate (Go) | Latest |

## Post-Setup Tasks

### 1. Activate Tailscale

SSH into device and run:
```bash
sudo tailscale up
```

### 2. Start VS Code Tunnel

```bash
code tunnel
```

Follow prompts to authenticate with GitHub.

### 3. Configure GitHub CLI

```bash
gh auth login
```

### 4. Docker Group (Reboot Required)

The user is added to the docker group, but you need to log out/in or reboot:
```bash
sudo reboot
```

After reboot, test:
```bash
docker ps
```

## Troubleshooting

### SSH Key Issues

```bash
# Add key to agent
ssh-add ~/.ssh/id_westbankbankrupt

# Test SSH connection
ssh -i ~/.ssh/id_westbankbankrupt jadennation@rpi5.local
```

### Python Interpreter Not Found

```bash
# SSH into device and install Python 3
ssh jadennation@rpi5.local
sudo apt update && sudo apt install -y python3
```

### Permission Denied (sudo)

Ensure your user has sudo privileges on the target device:
```bash
sudo usermod -aG sudo jadennation
```

### Task Fails: File Not Found

Some config files are optional. Check that these exist locally:
- `~/DEV/bin/aliases.zsh`
- `~/DEV/bin/colors.zsh`
- `~/DEV/bin/constants.zsh`
- `~/DEV/bin/functions.zsh`
- `~/DEV/bin/custom_path.zsh`
- `~/DEV/bin/autoload_environment.zsh`

Tasks using these files have `ignore_errors: yes` so they won't fail the entire playbook.

## Customization

### Change Versions

Edit [playbook.yml](playbook.yml):

```yaml
vars:
  go_version: "1.23.4"      # Update Go version
  nvim_version: "0.10.4"    # Update Neovim version
```

### Skip Specific Tasks

Comment out the task import in [playbook.yml](playbook.yml):

```yaml
# - name: Setup Docker
#   include_tasks: tasks/setup_docker.yml
```

### Add Custom Tasks

1. Create `tasks/your_custom_task.yml`
2. Add to [playbook.yml](playbook.yml):
   ```yaml
   - name: Your custom task
     include_tasks: tasks/your_custom_task.yml
   ```

## Useful Commands

```bash
# List all hosts
ansible all -i inventory.ini --list-hosts

# Run ad-hoc command on all hosts
ansible all -i inventory.ini -a "uptime"

# Check disk space on all hosts
ansible all -i inventory.ini -a "df -h"

# Reboot all hosts
ansible all -i inventory.ini -b -a "reboot"

# Update packages on all hosts
ansible all -i inventory.ini -b -m apt -a "upgrade=dist update_cache=yes"
```

## Files Structure

```
ansible/
├── playbook.yml              # Main playbook
├── inventory.ini             # Your devices (edit this!)
├── ansible.cfg               # Ansible configuration
├── Makefile                  # Helper commands
├── README.md                 # Full documentation
├── QUICK_START.md            # This file
├── tasks/                    # Individual task modules
│   ├── install_packages.yml
│   ├── setup_docker.yml
│   ├── setup_golang.yml
│   ├── setup_neovim.yml
│   ├── setup_python.yml
│   ├── setup_ssh_keys.yml
│   ├── setup_tailscale.yml
│   ├── setup_vscode_server.yml
│   ├── setup_zsh.yml
│   └── copy_config_files.yml
├── files/
│   └── remote_zshrc          # Zsh config for remote
└── templates/
    └── vscode-tunnel.service.j2
```
