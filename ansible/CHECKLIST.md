# Pre-Deployment Checklist

## Before Running Playbooks

### Local Machine (Control Node)
- [ ] Ansible installed: `brew install ansible`
- [ ] SSH key exists: `ls ~/.ssh/id_westbankbankrupt`
- [ ] SSH key added to agent: `ssh-add ~/.ssh/id_westbankbankrupt`
- [ ] Can access target devices: `ssh jadennation@<device-ip>`

### Target Devices (Remote Nodes)
- [ ] Raspberry Pi OS (64-bit) or Debian-based OS installed
- [ ] Python 3 installed: `ssh user@device "python3 --version"`
- [ ] SSH access configured
- [ ] User has sudo privileges: `ssh user@device "sudo whoami"`
- [ ] Device connected to network
- [ ] Device has internet access

### Configuration
- [ ] Edit `inventory.ini` with actual device IPs/hostnames
- [ ] Verify config files exist locally:
  - [ ] `~/DEV/bin/aliases.zsh`
  - [ ] `~/DEV/bin/colors.zsh`
  - [ ] `~/DEV/bin/constants.zsh`
  - [ ] `~/DEV/bin/functions.zsh`
  - [ ] `~/DEV/bin/custom_path.zsh`
  - [ ] `~/DEV/bin/autoload_environment.zsh`

## Testing Steps

### 1. Syntax Check (if Ansible installed locally)
```bash
cd /Users/jadennation/DEV/bin/ansible
ansible-playbook playbook.yml --syntax-check
```

### 2. Inventory Verification
```bash
ansible all -i inventory.ini --list-hosts
```

Expected output should list your devices.

### 3. Connectivity Test
```bash
ansible all -i inventory.ini -m ping
```

Expected: All devices respond with "pong"

### 4. Dry Run
```bash
ansible-playbook -i inventory.ini playbook.yml --check --diff
```

Review what would change. No actual changes made.

### 5. Single Host Test (Recommended First)
```bash
# Test on one device first
ansible-playbook -i inventory.ini playbook.yml --limit <single-host>
```

### 6. Full Deployment
```bash
# If single host test successful, run on all
ansible-playbook -i inventory.ini playbook.yml
```

## Post-Deployment Verification

### On Each Target Device

#### 1. Zsh Installation
```bash
ssh user@device
echo $SHELL  # Should be /bin/zsh
which zsh    # Should show /bin/zsh
```

#### 2. Neovim Installation
```bash
nvim --version  # Should show v0.10.4
```

#### 3. Docker Installation
```bash
docker --version          # Should show Docker version
docker compose version    # Should show Compose version
docker ps                 # Should work without sudo (after reboot)
```

#### 4. Golang Installation
```bash
go version               # Should show go1.23.4
which skate              # Should show ~/go/bin/skate
skate --help             # Should show help
```

#### 5. Python/UV Installation
```bash
python3 --version        # Should show Python 3.x
uv --version            # Should show UV version
```

#### 6. Tailscale Installation
```bash
tailscale version       # Should show version
sudo tailscale status   # Should show "not running" or connected
```

#### 7. GitHub CLI Installation
```bash
gh --version            # Should show gh version
```

#### 8. Terminal Utilities
```bash
tree --version
rg --version           # ripgrep
batcat --version       # bat (installed as batcat on Debian)
fzf --version
htop --version
fdfind --version       # fd (installed as fdfind on Debian)
```

#### 9. VS Code Server
```bash
ls -la ~/.vscode-cli/code  # Should exist
```

#### 10. Config Files
```bash
ls -la ~/dev/bin/          # Should contain .zsh files
cat ~/.zshrc               # Should show remote zshrc content
cat ~/.config/nvim/init.lua  # Should exist
```

#### 11. PATH Check
```bash
echo $PATH
# Should include:
# - /usr/local/go/bin
# - ~/go/bin
# - ~/.cargo/bin
# - ~/.vscode-cli
```

## Common Issues & Solutions

### Issue: "Python interpreter not found"
**Solution**: 
```bash
ssh user@device "sudo apt update && sudo apt install -y python3"
```

### Issue: "Permission denied" for Docker
**Solution**: 
```bash
# Reboot the device or re-login
ssh user@device "sudo reboot"
# Wait 30 seconds, then test again
```

### Issue: "SSH connection refused"
**Solution**:
```bash
# Verify SSH service running on device
ssh user@device "sudo systemctl status ssh"

# Restart if needed
ssh user@device "sudo systemctl restart ssh"
```

### Issue: Config files not copied
**Solution**: 
These tasks have `ignore_errors: yes`. Verify files exist locally:
```bash
ls -la ~/DEV/bin/*.zsh
```

### Issue: Download timeouts
**Solution**: 
Large files (Go, Neovim) may timeout on slow connections. Increase timeout in task files or download manually first.

### Issue: Architecture mismatch
**Solution**: 
Playbook detects architecture automatically. Verify with:
```bash
ansible all -i inventory.ini -m setup -a "filter=ansible_architecture"
```

## Performance Benchmarks

Typical run times (varies by network speed):

- **Full fresh install**: 15-25 minutes per device
- **Idempotent re-run**: 2-5 minutes per device
- **Single task update**: 30 seconds - 2 minutes

## Rollback Plan

If something goes wrong:

1. **Re-flash SD card** (nuclear option)
2. **Uninstall specific packages**:
   ```bash
   sudo apt remove docker-ce docker-ce-cli containerd.io
   sudo apt autoremove
   ```
3. **Restore backed-up configs** (if you made backups)
4. **Re-run specific task modules**:
   ```bash
   ansible-playbook -i inventory.ini playbook.yml --tags <tag-name>
   ```

## Success Criteria

✅ Playbook completes without errors
✅ All expected packages installed and working
✅ Zsh is default shell with working config
✅ Can connect via VS Code tunnel
✅ Docker commands work without sudo (after reboot)
✅ Neovim opens with plugins loaded
✅ All PATH additions work correctly

## Sign-Off

- [ ] Tested on at least one device
- [ ] All critical services verified
- [ ] Documentation reviewed and accurate
- [ ] Inventory file configured for production
- [ ] Ready for deployment to all devices

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Devices Configured**: _________________

**Issues Encountered**: _________________

**Notes**: _________________
