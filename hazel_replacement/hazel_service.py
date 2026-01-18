#!/usr/bin/env python3
"""
Hazel Replacement - Automatic File Organization Service
========================================================
A macOS service that watches folders and automatically organizes files
based on configurable rules (file type, download source, etc.)
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import xattr
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent


# =============================================================================
# Configuration
# =============================================================================

CONFIG_DIR = Path.home() / ".hazel_replacement"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEFAULT_CONFIG_FILE = Path(__file__).parent / "config.yaml"
LOG_FILE = CONFIG_DIR / "hazel.log"
PID_FILE = CONFIG_DIR / "hazel.pid"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TypeRule:
    """Represents a file type rule."""
    name: str
    extensions: List[str]
    destination: str


@dataclass
class WatchRule:
    """Represents a watch directory rule."""
    name: str
    watch_directory: Path
    enabled: bool
    redirect_domains: List[str]
    type_rules: List[TypeRule]
    redirect_destination: str
    source_directories: List[str]  # Relative paths where files are picked up from


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """Configure logging for the service."""
    logger = logging.getLogger("HazelReplacement")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


# =============================================================================
# Configuration Loading
# =============================================================================

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        # Check user config first, then fall back to default
        if CONFIG_FILE.exists():
            config_path = CONFIG_FILE
        elif DEFAULT_CONFIG_FILE.exists():
            config_path = DEFAULT_CONFIG_FILE
        else:
            raise FileNotFoundError(f"No configuration file found at {CONFIG_FILE} or {DEFAULT_CONFIG_FILE}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def parse_watch_rules(config: Dict[str, Any]) -> List[WatchRule]:
    """Parse watch rules from configuration."""
    rules = []
    
    for rule_config in config.get('watch_rules', []):
        if not rule_config.get('enabled', True):
            continue
        
        # Parse type rules
        type_rules = []
        for type_name, type_config in rule_config.get('type_rules', {}).items():
            type_rules.append(TypeRule(
                name=type_name,
                extensions=[ext.lower() for ext in type_config.get('extensions', [])],
                destination=type_config.get('destination', type_name)
            ))
        
        # Expand ~ in path
        watch_dir = Path(os.path.expanduser(rule_config['watch_directory']))
        
        # Parse source directories (default to just root)
        source_dirs = rule_config.get('source_directories', ['.'])
        
        rules.append(WatchRule(
            name=rule_config['name'],
            watch_directory=watch_dir,
            enabled=rule_config.get('enabled', True),
            redirect_domains=rule_config.get('redirect_domains', []),
            type_rules=type_rules,
            redirect_destination=rule_config.get('redirect_destination', 'tmp'),
            source_directories=source_dirs
        ))
    
    return rules


# =============================================================================
# Download Source Detection
# =============================================================================

def get_download_source(file_path: Path) -> Optional[str]:
    """
    Extract the download source URL from macOS extended attributes.
    
    macOS stores download information in the 'com.apple.metadata:kMDItemWhereFroms'
    extended attribute when files are downloaded via Safari, Chrome, etc.
    """
    try:
        attrs = xattr.xattr(str(file_path))
        
        # Check for the "where from" attribute (contains download URL)
        where_from_key = 'com.apple.metadata:kMDItemWhereFroms'
        
        if where_from_key in attrs:
            import plistlib
            data = attrs[where_from_key]
            urls = plistlib.loads(data)
            
            if urls and len(urls) > 0:
                return urls[0]  # First URL is typically the direct download source
        
        return None
    except Exception:
        return None


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def matches_redirect_domain(url: str, redirect_domains: List[str]) -> bool:
    """
    Check if the download URL matches any redirect domain pattern.
    Supports partial matching (e.g., 'facebook' matches 'www.facebook.com').
    """
    if not url:
        return False
    
    domain = extract_domain(url)
    if not domain:
        return False
    
    domain_lower = domain.lower()
    
    for pattern in redirect_domains:
        pattern_lower = pattern.lower()
        if pattern_lower in domain_lower:
            return True
    
    return False


# =============================================================================
# File Organization
# =============================================================================

def get_file_extension(file_path: Path) -> str:
    """Get lowercase file extension including the dot."""
    return file_path.suffix.lower()


def find_matching_type_rule(file_path: Path, type_rules: List[TypeRule]) -> Optional[TypeRule]:
    """Find a type rule that matches the file extension."""
    ext = get_file_extension(file_path)
    
    for rule in type_rules:
        if ext in rule.extensions:
            return rule
    
    return None


def ensure_directory(directory: Path) -> None:
    """Ensure a directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)


def generate_unique_filename(destination: Path, original_name: str) -> Path:
    """
    Generate a unique filename if the destination already has a file with that name.
    Appends _1, _2, etc. before the extension.
    """
    dest_file = destination / original_name
    
    if not dest_file.exists():
        return dest_file
    
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        dest_file = destination / new_name
        if not dest_file.exists():
            return dest_file
        counter += 1


def move_file(source: Path, destination_dir: Path, logger: logging.Logger) -> bool:
    """
    Move a file to the destination directory.
    Returns True on success, False on failure.
    """
    try:
        ensure_directory(destination_dir)
        dest_file = generate_unique_filename(destination_dir, source.name)
        
        shutil.move(str(source), str(dest_file))
        logger.info(f"Moved: {source.name} -> {dest_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to move {source}: {e}")
        return False


def is_file_ready(file_path: Path, wait_time: float = 0.5) -> bool:
    """
    Check if a file is ready (not still being written).
    Compares file size at two points in time.
    """
    try:
        if not file_path.exists():
            return False
        
        size1 = file_path.stat().st_size
        time.sleep(wait_time)
        
        if not file_path.exists():
            return False
        
        size2 = file_path.stat().st_size
        
        # File is ready if size is stable (allow 0-byte files too)
        return size1 == size2
    except Exception:
        return False


def process_file(file_path: Path, rule: WatchRule, logger: logging.Logger) -> None:
    """Process a single file according to the watch rule."""
    
    # Skip directories
    if file_path.is_dir():
        return
    
    # Skip hidden files and temp files
    if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
        return
    
    # Skip .DS_Store and similar
    if file_path.name in ['.DS_Store', 'Thumbs.db', '.localized']:
        return
    
    # Wait for file to be fully written
    if not is_file_ready(file_path):
        logger.debug(f"File not ready yet: {file_path.name}")
        return
    
    logger.debug(f"Processing: {file_path.name}")
    
    # Check download source for domain redirect
    download_url = get_download_source(file_path)
    
    if download_url and matches_redirect_domain(download_url, rule.redirect_domains):
        domain = extract_domain(download_url)
        logger.info(f"Domain redirect match ({domain}): {file_path.name}")
        dest_dir = rule.watch_directory / rule.redirect_destination
        move_file(file_path, dest_dir, logger)
        return
    
    # Check file type rules
    type_rule = find_matching_type_rule(file_path, rule.type_rules)
    
    if type_rule:
        logger.info(f"Type match ({type_rule.name}): {file_path.name}")
        dest_dir = rule.watch_directory / type_rule.destination
        move_file(file_path, dest_dir, logger)
        return
    
    logger.debug(f"No matching rule for: {file_path.name}")


# =============================================================================
# File System Event Handler
# =============================================================================

class HazelEventHandler(FileSystemEventHandler):
    """Handles file system events for automatic file organization."""
    
    def __init__(self, rule: WatchRule, logger: logging.Logger):
        super().__init__()
        self.rule = rule
        self.logger = logger
        self.processing_queue: Dict[str, float] = {}
        self.debounce_seconds = 2.0  # Wait 2 seconds before processing
    
    def _should_process(self, event) -> bool:
        """Determine if the event should be processed."""
        # Only process files, not directories
        if event.is_directory:
            return False
        
        # Get the file path
        file_path = Path(event.dest_path if hasattr(event, 'dest_path') and event.dest_path else event.src_path)
        
        # Check if file is in one of the allowed source directories
        file_parent = file_path.parent
        allowed = False
        for src_dir in self.rule.source_directories:
            if src_dir == '.':
                allowed_path = self.rule.watch_directory
            else:
                allowed_path = self.rule.watch_directory / src_dir
            if file_parent == allowed_path:
                allowed = True
                break
        
        if not allowed:
            return False
        
        return True
    
    def _queue_for_processing(self, file_path: Path) -> None:
        """Queue a file for processing with debouncing."""
        self.processing_queue[str(file_path)] = time.time()
    
    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if not self._should_process(event):
            return
        
        file_path = Path(event.src_path)
        self.logger.debug(f"File created: {file_path.name}")
        
        # Process with a small delay to ensure file is fully written
        time.sleep(1)
        process_file(file_path, self.rule, self.logger)
    
    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle file move events (files moved INTO the watched directory)."""
        if not self._should_process(event):
            return
        
        file_path = Path(event.dest_path)
        self.logger.debug(f"File moved in: {file_path.name}")
        
        time.sleep(0.5)
        process_file(file_path, self.rule, self.logger)


# =============================================================================
# Service Management
# =============================================================================

class HazelService:
    """Main service class that manages file watching."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.rules = parse_watch_rules(self.config)
        
        # Setup logging
        settings = self.config.get('settings', {})
        log_level = settings.get('log_level', 'INFO')
        log_file_path = settings.get('log_file')
        
        if log_file_path:
            log_file = Path(os.path.expanduser(log_file_path))
        else:
            log_file = LOG_FILE
        
        self.logger = setup_logging(log_level, log_file)
        
        self.observers: List[Observer] = []
        self.running = False
    
    def _setup_directories(self) -> None:
        """Ensure all watch directories and subdirectories exist."""
        for rule in self.rules:
            # Create watch directory
            ensure_directory(rule.watch_directory)
            
            # Create redirect destination
            ensure_directory(rule.watch_directory / rule.redirect_destination)
            
            # Create type rule destinations
            for type_rule in rule.type_rules:
                ensure_directory(rule.watch_directory / type_rule.destination)
    
    def _process_existing_files(self) -> None:
        """Process any existing files in watch directories on startup."""
        self.logger.info("Processing existing files...")
        
        for rule in self.rules:
            if not rule.watch_directory.exists():
                continue
            
            # Process files in each source directory
            for src_dir in rule.source_directories:
                if src_dir == '.':
                    scan_dir = rule.watch_directory
                else:
                    scan_dir = rule.watch_directory / src_dir
                
                if not scan_dir.exists():
                    continue
                
                for file_path in scan_dir.iterdir():
                    if file_path.is_file():
                        process_file(file_path, rule, self.logger)
    
    def start(self) -> None:
        """Start the file watching service."""
        self.logger.info("=" * 60)
        self.logger.info("Hazel Replacement Service Starting")
        self.logger.info("=" * 60)
        
        # Setup directories
        self._setup_directories()
        
        # Process existing files
        self._process_existing_files()
        
        # Setup observers for each rule
        for rule in self.rules:
            self.logger.info(f"Watching: {rule.watch_directory} ({rule.name})")
            
            event_handler = HazelEventHandler(rule, self.logger)
            observer = Observer()
            observer.schedule(event_handler, str(rule.watch_directory), recursive=True)
            observer.start()
            self.observers.append(observer)
        
        self.running = True
        self.logger.info("Service started successfully")
        
        # Write PID file
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
    
    def stop(self) -> None:
        """Stop the file watching service."""
        self.logger.info("Stopping service...")
        self.running = False
        
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.observers.clear()
        
        # Remove PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        
        self.logger.info("Service stopped")
    
    def run(self) -> None:
        """Run the service (blocking)."""
        self.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()


# =============================================================================
# CLI Commands
# =============================================================================

def print_status() -> None:
    """Print service status."""
    if PID_FILE.exists():
        pid = PID_FILE.read_text().strip()
        # Check if process is actually running
        try:
            os.kill(int(pid), 0)
            print(f"✅ Hazel Replacement is running (PID: {pid})")
        except OSError:
            print("⚠️  PID file exists but process is not running")
            PID_FILE.unlink()
    else:
        print("❌ Hazel Replacement is not running")


def print_config() -> None:
    """Print current configuration."""
    try:
        config = load_config()
        rules = parse_watch_rules(config)
        
        print("\n📁 Hazel Replacement Configuration")
        print("=" * 50)
        
        for rule in rules:
            print(f"\n📂 {rule.name}")
            print(f"   Watch: {rule.watch_directory}")
            print(f"   Redirect domains: {', '.join(rule.redirect_domains[:3])}...")
            print(f"   Redirect to: {rule.redirect_destination}/")
            print("   Type rules:")
            for tr in rule.type_rules:
                print(f"     - {tr.name}: {tr.destination}/")
    except Exception as e:
        print(f"Error loading config: {e}")


def install_config() -> None:
    """Copy default config to user config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_FILE.exists():
        backup = CONFIG_FILE.with_suffix('.yaml.bak')
        shutil.copy(CONFIG_FILE, backup)
        print(f"Backed up existing config to {backup}")
    
    shutil.copy(DEFAULT_CONFIG_FILE, CONFIG_FILE)
    print(f"Installed config to {CONFIG_FILE}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Hazel Replacement - Automatic File Organization Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run the service (foreground)
  %(prog)s status             Check if service is running
  %(prog)s config             Show current configuration
  %(prog)s install-config     Install default config to ~/.hazel_replacement/
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='run',
        choices=['run', 'status', 'config', 'install-config'],
        help='Command to execute (default: run)'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=Path,
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print_status()
    elif args.command == 'config':
        print_config()
    elif args.command == 'install-config':
        install_config()
    elif args.command == 'run':
        service = HazelService(args.config)
        service.run()


if __name__ == '__main__':
    main()
