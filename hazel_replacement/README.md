# Hazel Replacement

A macOS service that automatically organizes files based on configurable rules. This is a lightweight, open-source alternative to the popular Hazel app.

## Features

- **Automatic File Organization**: Watch directories and automatically move files based on rules
- **File Type Detection**: Route files to different directories based on extension (video, image, audio, etc.)
- **Download Source Detection**: Read macOS extended attributes to determine where files were downloaded from
- **Domain-Based Routing**: Redirect files from specific domains (social media, etc.) to a separate directory
- **Launch at Login**: Runs as a background service via launchd
- **Configurable via YAML**: Easy-to-edit configuration file

## Quick Start

### Installation

```bash
cd /path/to/hazel_replacement
chmod +x install.sh
./install.sh
```

This will:
1. Check for Python 3 and install dependencies
2. Create the configuration directory at `~/.hazel_replacement/`
3. Create the watch directory structure at `~/Downloads/drive/`
4. Install and start the launchd service

### Manual Run (for testing)

```bash
python3 hazel_service.py run
```

## Configuration

The configuration file is located at `~/.hazel_replacement/config.yaml` after installation.

### Example Configuration

```yaml
settings:
  log_level: INFO
  log_file: ~/.hazel_replacement/hazel.log

watch_rules:
  - name: "Downloads Drive Organizer"
    watch_directory: "~/Downloads/drive"
    enabled: true
    
    # Files from these domains go to /tmp
    redirect_domains:
      - "facebook.com"
      - "instagram.com"
      - "tiktok.com"
    
    # File type rules
    type_rules:
      video:
        extensions:
          - .mp4
          - .mkv
          - .mov
        destination: "vid"
      
      image:
        extensions:
          - .jpg
          - .png
          - .gif
        destination: "img"
    
    redirect_destination: "tmp"
```

### How Rules Work

1. **Domain Redirect (Highest Priority)**: If a file was downloaded from a URL matching any pattern in `redirect_domains`, it goes to the `redirect_destination` directory.

2. **Type Rules (Second Priority)**: If no domain match, files are routed based on their extension to the corresponding destination.

3. **No Match**: Files that don't match any rule are left in place.

## Directory Structure

After installation, the following directories are created:

```
~/Downloads/drive/
├── vid/    # Video files (.mp4, .mkv, .mov, etc.)
├── img/    # Image files (.jpg, .png, .gif, etc.)
└── tmp/    # Files from redirect domains
```

## Commands

### Check Status
```bash
# Check if service is running
launchctl list | grep hazel

# Or use the built-in command
python3 hazel_service.py status
```

### View Logs
```bash
tail -f ~/.hazel_replacement/hazel.log
```

### Stop Service
```bash
launchctl unload ~/Library/LaunchAgents/com.user.hazel-replacement.plist
```

### Start Service
```bash
launchctl load ~/Library/LaunchAgents/com.user.hazel-replacement.plist
```

### Uninstall
```bash
./uninstall.sh
```

## How Download Source Detection Works

When you download a file via Safari, Chrome, or other browsers, macOS stores the source URL in extended attributes:

- `com.apple.metadata:kMDItemWhereFroms` - Contains the download URL(s)

This service reads these attributes to determine where files came from, enabling domain-based routing.

## Adding Custom Rules

Edit `~/.hazel_replacement/config.yaml` to add more rules:

### Add More File Types

```yaml
type_rules:
  audio:
    extensions:
      - .mp3
      - .wav
      - .flac
      - .m4a
    destination: "audio"
  
  documents:
    extensions:
      - .pdf
      - .doc
      - .docx
    destination: "docs"
```

### Add More Redirect Domains

```yaml
redirect_domains:
  - "facebook.com"
  - "instagram.com"
  - "reddit.com"
  - "imgur.com"
```

### Watch Multiple Directories

```yaml
watch_rules:
  - name: "Downloads Organizer"
    watch_directory: "~/Downloads"
    enabled: true
    # ... rules ...
  
  - name: "Desktop Cleanup"
    watch_directory: "~/Desktop"
    enabled: true
    # ... rules ...
```

## Troubleshooting

### Service Not Starting

1. Check logs: `tail -100 ~/.hazel_replacement/stderr.log`
2. Verify Python path: `which python3`
3. Check plist: `cat ~/Library/LaunchAgents/com.user.hazel-replacement.plist`

### Files Not Moving

1. Ensure the watch directory exists: `ls ~/Downloads/drive`
2. Check permissions on destination directories
3. View service logs: `tail -f ~/.hazel_replacement/hazel.log`

### Domain Detection Not Working

Domain detection only works for files downloaded via browsers that set the `kMDItemWhereFroms` extended attribute. Files moved/copied from other locations won't have this metadata.

Check if a file has download metadata:
```bash
xattr -p com.apple.metadata:kMDItemWhereFroms /path/to/file
```

## Requirements

- macOS 10.15+
- Python 3.8+
- Dependencies: watchdog, PyYAML, xattr

## License

MIT License
