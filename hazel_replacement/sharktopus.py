#!/usr/bin/env python3
"""
Sharktopus - Automatic File Organization Service
==================================================
A macOS service that watches folders and automatically organizes files
based on configurable rules. Successor to Hazel Replacement.
"""

import os
import sys
import json
import time
import shutil
import fnmatch
import logging
import subprocess
import threading
import uuid
import xattr
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent


CONFIG_DIR = Path.home() / ".config" / "sharktopus"
RULES_FILE = CONFIG_DIR / "rules.json"
LEGACY_CONFIG_DIR = Path.home() / ".hazel_replacement"
LEGACY_CONFIG_FILE = LEGACY_CONFIG_DIR / "config.yaml"
LOG_FILE = CONFIG_DIR / "sharktopus.log"
PID_FILE = CONFIG_DIR / "sharktopus.pid"


class ActionType(str, Enum):
    MOVE = "move"
    RUN = "run"


DEFAULT_SENIORITY = 1


@dataclass
class Rule:
    id: str
    name: str
    pattern: str
    action: str
    enabled: bool = True
    destination: Optional[str] = None
    command: Optional[str] = None
    seniority: int = DEFAULT_SENIORITY

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "action": self.action,
            "enabled": self.enabled,
            "seniority": self.seniority,
        }
        if self.destination is not None:
            d["destination"] = self.destination
        if self.command is not None:
            d["command"] = self.command
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            id=data["id"],
            name=data["name"],
            pattern=data["pattern"],
            action=data["action"],
            enabled=data.get("enabled", True),
            destination=data.get("destination"),
            command=data.get("command"),
            seniority=int(data.get("seniority", DEFAULT_SENIORITY)),
        )


@dataclass
class TypeRule:
    name: str
    extensions: List[str]
    destination: str
    seniority: int = DEFAULT_SENIORITY


@dataclass
class DomainRule:
    name: str
    domain: str
    extensions: List[str]
    destination: str
    seniority: int = DEFAULT_SENIORITY


@dataclass
class WatchRule:
    name: str
    watch_directory: Path
    enabled: bool
    redirect_domains: List[str]
    domain_rules: List[DomainRule]
    type_rules: List[TypeRule]
    redirect_destination: str
    source_directories: List[str]


@dataclass
class RulesConfig:
    enabled: bool = True
    rules: List[Rule] = field(default_factory=list)
    watch_rules: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=lambda: {
        "log_level": "INFO",
        "log_file": str(LOG_FILE),
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "settings": self.settings,
            "rules": [r.to_dict() for r in self.rules],
            "watch_rules": self.watch_rules,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RulesConfig":
        rules = [Rule.from_dict(r) for r in data.get("rules", [])]
        return cls(
            enabled=data.get("enabled", True),
            rules=rules,
            watch_rules=data.get("watch_rules", []),
            settings=data.get("settings", {
                "log_level": "INFO",
                "log_file": str(LOG_FILE),
            }),
        )


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger("Sharktopus")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

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


def load_rules_config() -> RulesConfig:
    if not RULES_FILE.exists():
        return RulesConfig()
    with open(RULES_FILE, 'r') as f:
        data = json.load(f)
    return RulesConfig.from_dict(data)


def save_rules_config(config: RulesConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(RULES_FILE, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)


def migrate_legacy_config() -> RulesConfig:
    config = RulesConfig()

    if LEGACY_CONFIG_FILE.exists():
        with open(LEGACY_CONFIG_FILE, 'r') as f:
            legacy = yaml.safe_load(f)

        if legacy:
            config.settings = legacy.get("settings", config.settings)
            config.watch_rules = legacy.get("watch_rules", [])

    save_rules_config(config)
    return config


def parse_watch_rules(watch_rules_data: List[Dict[str, Any]]) -> List[WatchRule]:
    rules = []

    for rule_config in watch_rules_data:
        if not rule_config.get('enabled', True):
            continue

        type_rules = []
        for type_name, type_config in rule_config.get('type_rules', {}).items():
            type_rules.append(TypeRule(
                name=type_name,
                extensions=[ext.lower() for ext in type_config.get('extensions', [])],
                destination=type_config.get('destination', type_name),
                seniority=int(type_config.get('seniority', DEFAULT_SENIORITY)),
            ))

        domain_rules = []
        for dr_name, dr_config in rule_config.get('domain_rules', {}).items():
            domain_rules.append(DomainRule(
                name=dr_name,
                domain=dr_config.get('domain', ''),
                extensions=[ext.lower() for ext in dr_config.get('extensions', [])],
                destination=dr_config.get('destination', ''),
                seniority=int(dr_config.get('seniority', DEFAULT_SENIORITY)),
            ))

        watch_dir = Path(os.path.expanduser(rule_config['watch_directory']))
        source_dirs = rule_config.get('source_directories', ['.'])

        rules.append(WatchRule(
            name=rule_config['name'],
            watch_directory=watch_dir,
            enabled=rule_config.get('enabled', True),
            redirect_domains=rule_config.get('redirect_domains', []),
            domain_rules=domain_rules,
            type_rules=type_rules,
            redirect_destination=rule_config.get('redirect_destination', 'tmp'),
            source_directories=source_dirs
        ))

    return rules


def get_download_source(file_path: Path) -> Optional[str]:
    try:
        attrs = xattr.xattr(str(file_path))
        where_from_key = 'com.apple.metadata:kMDItemWhereFroms'

        if where_from_key in attrs:
            import plistlib
            data = attrs[where_from_key]
            urls = plistlib.loads(data)

            if urls and len(urls) > 0:
                return urls[0]

        return None
    except Exception:
        return None


def extract_domain(url: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def matches_redirect_domain(url: str, redirect_domains: List[str]) -> bool:
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


def get_file_extension(file_path: Path) -> str:
    return file_path.suffix.lower()


def find_matching_type_rule(file_path: Path, type_rules: List[TypeRule]) -> Optional[TypeRule]:
    ext = get_file_extension(file_path)

    for rule in type_rules:
        if ext in rule.extensions:
            return rule

    return None


def ensure_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def generate_unique_filename(destination: Path, original_name: str) -> Path:
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
    try:
        if not file_path.exists():
            return False

        size1 = file_path.stat().st_size
        time.sleep(wait_time)

        if not file_path.exists():
            return False

        size2 = file_path.stat().st_size

        return size1 == size2
    except Exception:
        return False


def matches_cli_rule(file_path: Path, rule: Rule) -> bool:
    filename = file_path.name
    pattern = rule.pattern

    if fnmatch.fnmatch(filename, pattern):
        return True

    if pattern.startswith("*."):
        suffix = pattern[1:]
        if filename.endswith(suffix):
            return True

    return False


def execute_cli_rule(file_path: Path, rule: Rule, logger: logging.Logger) -> None:
    if rule.action == ActionType.MOVE:
        if rule.destination:
            dest_path = Path(os.path.expanduser(rule.destination))
            move_file(file_path, dest_path, logger)
        else:
            logger.warning(f"Rule '{rule.name}' has action 'move' but no destination")

    elif rule.action == ActionType.RUN:
        if rule.command:
            cmd = rule.command
            if "__FILE__" in cmd:
                cmd = cmd.replace("__FILE__", str(file_path))
            else:
                cmd = f"{cmd} {file_path}"

            logger.info(f"Running command: {cmd}")
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=300
                )
                if result.returncode != 0:
                    logger.error(f"Command failed ({result.returncode}): {result.stderr}")
                else:
                    logger.info(f"Command succeeded: {result.stdout.strip()}")
            except subprocess.TimeoutExpired:
                logger.error(f"Command timed out: {cmd}")
            except Exception as e:
                logger.error(f"Command error: {e}")
        else:
            logger.warning(f"Rule '{rule.name}' has action 'run' but no command")


@dataclass
class Candidate:
    """A rule that matched a file, normalized across CLI/Domain/Type rule kinds."""
    kind: str  # "cli" | "domain" | "type"
    seniority: int
    name: str
    destination: Optional[Path] = None
    command: Optional[str] = None
    action: Optional[str] = None  # "move" | "run"  (set for cli candidates)
    rule: Optional[Any] = None  # original rule object, for execution by existing helpers

    def tie_breaker(self) -> int:
        # Order of preference when seniority is tied: cli > domain > type
        return {"cli": 0, "domain": 1, "type": 2}.get(self.kind, 99)


def execute_candidate(file_path: Path, candidate: Candidate, logger: logging.Logger) -> None:
    if candidate.kind == "cli" and candidate.rule is not None:
        execute_cli_rule(file_path, candidate.rule, logger)
    elif candidate.destination is not None:
        move_file(file_path, candidate.destination, logger)
    else:
        logger.warning(f"Candidate '{candidate.name}' has no executable action")


def select_winner(candidates: List[Candidate], logger: logging.Logger) -> Optional[Candidate]:
    if not candidates:
        return None
    return max(candidates, key=lambda c: (c.seniority, -c.tie_breaker()))


def collect_watch_candidates(
    file_path: Path,
    watch_rule: WatchRule,
    logger: logging.Logger,
) -> List[Candidate]:
    candidates: List[Candidate] = []

    download_url = get_download_source(file_path)
    if download_url:
        domain = extract_domain(download_url)
        domain_lower = domain.lower() if domain else ""
        ext = get_file_extension(file_path)

        for dr in watch_rule.domain_rules:
            if dr.domain.lower() in domain_lower:
                if not dr.extensions or ext in dr.extensions:
                    dest_path = Path(os.path.expanduser(dr.destination))
                    if not dest_path.is_absolute():
                        dest_dir = watch_rule.watch_directory / dest_path
                    else:
                        dest_dir = dest_path
                    candidates.append(Candidate(
                        kind="domain",
                        seniority=dr.seniority,
                        name=f"{watch_rule.name} / {dr.name}",
                        destination=dest_dir,
                    ))

        if matches_redirect_domain(download_url, watch_rule.redirect_domains):
            dest_dir = watch_rule.watch_directory / watch_rule.redirect_destination
            candidates.append(Candidate(
                kind="domain",
                seniority=DEFAULT_SENIORITY,
                name=f"{watch_rule.name} / redirect",
                destination=dest_dir,
            ))

    type_rule = find_matching_type_rule(file_path, watch_rule.type_rules)
    if type_rule:
        dest_path = Path(os.path.expanduser(type_rule.destination))
        if not dest_path.is_absolute():
            dest_dir = watch_rule.watch_directory / dest_path
        else:
            dest_dir = dest_path
        candidates.append(Candidate(
            kind="type",
            seniority=type_rule.seniority,
            name=f"{watch_rule.name} / {type_rule.name}",
            destination=dest_dir,
        ))

    return candidates


def process_file(file_path: Path, cli_rules: List[Rule], watch_rule: Optional[WatchRule],
                 logger: logging.Logger) -> None:
    if file_path.is_dir():
        return

    if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
        return

    if file_path.name in ['.DS_Store', 'Thumbs.db', '.localized']:
        return

    if not is_file_ready(file_path):
        logger.debug(f"File not ready yet: {file_path.name}")
        return

    logger.debug(f"Processing: {file_path.name}")

    candidates: List[Candidate] = []

    for rule in cli_rules:
        if not rule.enabled:
            continue
        if matches_cli_rule(file_path, rule):
            dest: Optional[Path] = None
            if rule.action == ActionType.MOVE and rule.destination:
                dest = Path(os.path.expanduser(rule.destination))
            candidates.append(Candidate(
                kind="cli",
                seniority=rule.seniority,
                name=rule.name,
                destination=dest,
                command=rule.command,
                action=rule.action,
                rule=rule,
            ))

    if watch_rule is not None:
        candidates.extend(collect_watch_candidates(file_path, watch_rule, logger))

    if not candidates:
        logger.debug(f"No matching rule for: {file_path.name}")
        return

    winner = select_winner(candidates, logger)
    if winner is None:
        return

    if len(candidates) > 1:
        losing = [c for c in candidates if c is not winner]
        logger.info(
            f"Seniority winner ({winner.name}, s={winner.seniority}) "
            f"overrode: {', '.join(f'{c.name} (s={c.seniority})' for c in losing)}"
        )
    else:
        logger.info(f"Rule match ({winner.name}): {file_path.name}")

    execute_candidate(file_path, winner, logger)


class RuntimeState:
    """Shared mutable state between the service and event-handler threads.

    The service polls rules.json for changes and updates this object in-place;
    event handlers read from it on every file event so that `sp toggle` and
    `sp add-rule` take effect without restarting the service.
    """
    def __init__(self, enabled: bool, cli_rules: List["Rule"]):
        self.enabled = enabled
        self.cli_rules = cli_rules
        self._lock = threading.Lock()

    def snapshot(self) -> tuple:
        with self._lock:
            return self.enabled, list(self.cli_rules)

    def update(self, enabled: bool, cli_rules: List["Rule"]) -> None:
        with self._lock:
            self.enabled = enabled
            self.cli_rules = cli_rules


class SharktopusEventHandler(FileSystemEventHandler):
    def __init__(self, watch_rule: Optional[WatchRule], state: RuntimeState,
                 logger: logging.Logger, source_directories: Optional[List[str]] = None,
                 watch_directory: Optional[Path] = None):
        super().__init__()
        self.watch_rule = watch_rule
        self.state = state
        self.logger = logger
        self.source_directories = source_directories or ['.']
        self.watch_directory = watch_directory

    def _should_process(self, event) -> bool:
        if event.is_directory:
            return False

        file_path = Path(event.dest_path if hasattr(event, 'dest_path') and event.dest_path else event.src_path)

        if self.watch_directory is None:
            return True

        file_parent = file_path.parent
        for src_dir in self.source_directories:
            if src_dir == '.':
                allowed_path = self.watch_directory
            else:
                allowed_path = self.watch_directory / src_dir
            if file_parent == allowed_path:
                return True

        return False

    def on_created(self, event: FileCreatedEvent) -> None:
        if not self._should_process(event):
            return

        file_path = Path(event.src_path)
        self.logger.debug(f"File created: {file_path.name}")

        enabled, cli_rules = self.state.snapshot()
        if not enabled:
            self.logger.debug(f"Service asleep — skipping: {file_path.name}")
            return

        time.sleep(1)
        process_file(file_path, cli_rules, self.watch_rule, self.logger)

    def on_moved(self, event: FileMovedEvent) -> None:
        if not self._should_process(event):
            return

        file_path = Path(event.dest_path)
        self.logger.debug(f"File moved in: {file_path.name}")

        enabled, cli_rules = self.state.snapshot()
        if not enabled:
            self.logger.debug(f"Service asleep — skipping: {file_path.name}")
            return

        time.sleep(0.5)
        process_file(file_path, cli_rules, self.watch_rule, self.logger)


class SharktopusService:
    POLL_INTERVAL = 2  # seconds between config-reload checks

    def __init__(self, config: Optional[RulesConfig] = None):
        if config is None:
            config = load_rules_config()
        self.config = config

        settings = self.config.settings
        log_level = settings.get('log_level', 'INFO')
        log_file_path = settings.get('log_file')

        if log_file_path:
            log_file = Path(os.path.expanduser(log_file_path))
        else:
            log_file = LOG_FILE

        self.logger = setup_logging(log_level, log_file)
        self.watch_rules = parse_watch_rules(self.config.watch_rules)
        self.observers: List[Observer] = []
        self.running = False
        self._config_mtime: float = 0.0
        self._poller_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        enabled_cli_rules = [r for r in self.config.rules if r.enabled]
        self.state = RuntimeState(enabled=self.config.enabled, cli_rules=enabled_cli_rules)

    def _setup_directories(self) -> None:
        for rule in self.watch_rules:
            ensure_directory(rule.watch_directory)
            ensure_directory(rule.watch_directory / rule.redirect_destination)

            for domain_rule in rule.domain_rules:
                dest_path = Path(os.path.expanduser(domain_rule.destination))
                if not dest_path.is_absolute():
                    ensure_directory(rule.watch_directory / dest_path)
                else:
                    ensure_directory(dest_path)

            for type_rule in rule.type_rules:
                dest_path = Path(os.path.expanduser(type_rule.destination))
                if not dest_path.is_absolute():
                    ensure_directory(rule.watch_directory / dest_path)
                else:
                    ensure_directory(dest_path)

        for cli_rule in self.config.rules:
            if cli_rule.enabled and cli_rule.action == ActionType.MOVE and cli_rule.destination:
                dest_path = Path(os.path.expanduser(cli_rule.destination))
                ensure_directory(dest_path)

    def _process_existing_files(self) -> None:
        if not self.state.enabled:
            self.logger.info("Service asleep — skipping existing-file processing")
            return

        self.logger.info("Processing existing files...")

        enabled, cli_rules = self.state.snapshot()

        for rule in self.watch_rules:
            if not rule.watch_directory.exists():
                continue

            for src_dir in rule.source_directories:
                if src_dir == '.':
                    scan_dir = rule.watch_directory
                else:
                    scan_dir = rule.watch_directory / src_dir

                if not scan_dir.exists():
                    continue

                for file_path in scan_dir.iterdir():
                    if file_path.is_file():
                        process_file(file_path, cli_rules, rule, self.logger)

    def _reload_config_if_changed(self) -> bool:
        """Re-read rules.json if its mtime changed. Returns True if reloaded."""
        try:
            if not RULES_FILE.exists():
                return False
            mtime = RULES_FILE.stat().st_mtime
            if mtime == self._config_mtime:
                return False
            self._config_mtime = mtime
        except OSError:
            return False

        try:
            new_config = load_rules_config()
        except Exception as e:
            self.logger.warning(f"Config reload failed (keeping old state): {e}")
            return False

        was_enabled = self.state.enabled
        new_cli_rules = [r for r in new_config.rules if r.enabled]
        self.state.update(enabled=new_config.enabled, cli_rules=new_cli_rules)

        if was_enabled and not new_config.enabled:
            self.logger.info("Service entering sleep mode (enabled=false)")
        elif not was_enabled and new_config.enabled:
            self.logger.info("Service waking up (enabled=true)")

        self.logger.info(
            f"Config reloaded: enabled={new_config.enabled}, "
            f"{len(new_cli_rules)} active CLI rules"
        )
        return True

    def _config_poller(self) -> None:
        while not self._stop_event.is_set():
            self._reload_config_if_changed()
            self._stop_event.wait(self.POLL_INTERVAL)

    def start(self) -> None:
        self.logger.info("=" * 60)
        self.logger.info("Sharktopus Service Starting")
        self.logger.info("=" * 60)

        if RULES_FILE.exists():
            self._config_mtime = RULES_FILE.stat().st_mtime

        self._setup_directories()

        if self.state.enabled:
            self._process_existing_files()
        else:
            self.logger.info("Starting in sleep mode (enabled=false)")

        for rule in self.watch_rules:
            self.logger.info(f"Watching: {rule.watch_directory} ({rule.name})")

            event_handler = SharktopusEventHandler(
                watch_rule=rule,
                state=self.state,
                logger=self.logger,
                source_directories=rule.source_directories,
                watch_directory=rule.watch_directory,
            )
            observer = Observer()
            observer.schedule(event_handler, str(rule.watch_directory), recursive=True)
            observer.start()
            self.observers.append(observer)

        if not self.watch_rules:
            watch_dir = Path.home() / "Downloads"
            self.logger.info(f"No watch rules found. Watching default: {watch_dir}")

            event_handler = SharktopusEventHandler(
                watch_rule=None,
                state=self.state,
                logger=self.logger,
                watch_directory=watch_dir,
            )
            observer = Observer()
            observer.schedule(event_handler, str(watch_dir), recursive=True)
            observer.start()
            self.observers.append(observer)

        self._poller_thread = threading.Thread(target=self._config_poller, daemon=True)
        self._poller_thread.start()

        self.running = True
        self.logger.info(f"Service started with {len(self.config.rules)} CLI rules, "
                        f"{len(self.watch_rules)} watch rules")

        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

    def stop(self) -> None:
        self.logger.info("Stopping service...")
        self.running = False
        self._stop_event.set()

        if self._poller_thread and self._poller_thread.is_alive():
            self._poller_thread.join(timeout=5)

        for observer in self.observers:
            observer.stop()
            observer.join()

        self.observers.clear()

        if PID_FILE.exists():
            PID_FILE.unlink()

        self.logger.info("Service stopped")

    def run(self) -> None:
        self.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop()


def generate_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def pattern_extensions(pattern: str) -> List[str]:
    """Extract literal extensions a glob pattern can match. Returns [] for '*'."""
    if pattern == "*" or pattern == "*.*":
        return []
    if pattern.startswith("*."):
        return [pattern[1:].lower()]
    return [pattern.lower()]


def patterns_overlap(a: str, b: str) -> bool:
    """Conservative overlap check: True if any filename can match both patterns."""
    a_exts = pattern_extensions(a)
    b_exts = pattern_extensions(b)
    if not a_exts or not b_exts:
        return True
    return bool(set(a_exts) & set(b_exts))


def detect_conflicts(new_rule: Rule, config: RulesConfig) -> List[Dict[str, Any]]:
    """Return conflict descriptions for new_rule vs existing rules.

    Each returned dict has: description (str), loses (bool) — True if the new
    rule would be shadowed by this existing rule at its current seniority.
    """
    conflicts: List[Dict[str, Any]] = []
    new_exts = set(pattern_extensions(new_rule.pattern))

    for existing in config.rules:
        if not existing.enabled or existing.name == new_rule.name:
            continue
        if patterns_overlap(new_rule.pattern, existing.pattern):
            new_loses = existing.seniority >= new_rule.seniority
            winner = existing if new_loses else new_rule
            loser = new_rule if new_loses else existing
            conflicts.append({
                "loses": new_loses,
                "description": (
                    f"  - CLI rule '{existing.name}' (id={existing.id}, pattern='{existing.pattern}', "
                    f"seniority={existing.seniority}) — winner: '{winner.name}' (s={winner.seniority}); "
                    f"'{loser.name}' will be shadowed"
                ),
            })

    for wr_config in config.watch_rules:
        if not wr_config.get("enabled", True):
            continue
        wr_name = wr_config.get("name", "?")

        for tr_name, tr in wr_config.get("type_rules", {}).items():
            tr_exts = {e.lower() for e in tr.get("extensions", [])}
            tr_sen = int(tr.get("seniority", DEFAULT_SENIORITY))
            overlap = (not new_exts) or bool(new_exts & tr_exts)
            if not overlap:
                continue
            new_loses = tr_sen > new_rule.seniority
            if new_loses:
                desc = (
                    f"  - Watch type rule '{wr_name}/{tr_name}' (extensions={sorted(tr_exts)}, "
                    f"seniority={tr_sen}) — watch rule wins (s={tr_sen} > {new_rule.seniority}); "
                    f"new rule will be shadowed for these extensions"
                )
            else:
                desc = (
                    f"  - Watch type rule '{wr_name}/{tr_name}' (extensions={sorted(tr_exts)}, "
                    f"seniority={tr_sen}) — new rule wins (s={new_rule.seniority} >= {tr_sen}); "
                    f"this type rule will be shadowed for overlapping files"
                )
            conflicts.append({"loses": new_loses, "description": desc})

        for dr_name, dr in wr_config.get("domain_rules", {}).items():
            dr_exts = {e.lower() for e in dr.get("extensions", [])}
            dr_sen = int(dr.get("seniority", DEFAULT_SENIORITY))
            overlap = (not new_exts) or (not dr_exts) or bool(new_exts & dr_exts)
            if not overlap:
                continue
            new_loses = dr_sen > new_rule.seniority
            if new_loses:
                desc = (
                    f"  - Watch domain rule '{wr_name}/{dr_name}' (domain='{dr.get('domain')}', "
                    f"seniority={dr_sen}) — watch rule wins (s={dr_sen} > {new_rule.seniority}); "
                    f"new rule will be shadowed for files from this domain"
                )
            else:
                desc = (
                    f"  - Watch domain rule '{wr_name}/{dr_name}' (domain='{dr.get('domain')}', "
                    f"seniority={dr_sen}) — new rule wins (s={new_rule.seniority} >= {dr_sen}); "
                    f"this domain rule will be shadowed for overlapping extensions"
                )
            conflicts.append({"loses": new_loses, "description": desc})

    return conflicts


def suggest_seniority(new_rule: Rule, config: RulesConfig) -> Optional[int]:
    """If the new rule would lose to an existing rule, suggest next-higher seniority."""
    max_existing = 0
    found_loss = False
    new_exts = set(pattern_extensions(new_rule.pattern))

    for existing in config.rules:
        if not existing.enabled or existing.name == new_rule.name:
            continue
        if patterns_overlap(new_rule.pattern, existing.pattern) and existing.seniority >= new_rule.seniority:
            found_loss = True
            max_existing = max(max_existing, existing.seniority)

    for wr_config in config.watch_rules:
        if not wr_config.get("enabled", True):
            continue
        for tr in wr_config.get("type_rules", {}).values():
            tr_exts = {e.lower() for e in tr.get("extensions", [])}
            tr_sen = int(tr.get("seniority", DEFAULT_SENIORITY))
            if ((not new_exts) or bool(new_exts & tr_exts)) and tr_sen >= new_rule.seniority:
                found_loss = True
                max_existing = max(max_existing, tr_sen)
        for dr in wr_config.get("domain_rules", {}).values():
            dr_exts = {e.lower() for e in dr.get("extensions", [])}
            dr_sen = int(dr.get("seniority", DEFAULT_SENIORITY))
            overlap = (not new_exts) or (not dr_exts) or bool(new_exts & dr_exts)
            if overlap and dr_sen >= new_rule.seniority:
                found_loss = True
                max_existing = max(max_existing, dr_sen)

    if found_loss:
        return max_existing + 1
    return None


def cmd_add_rule(args) -> None:
    config = load_rules_config()

    for existing in config.rules:
        if existing.name == args.name:
            print(f"Error: Rule with name '{args.name}' already exists (id: {existing.id})")
            sys.exit(1)

    seniority = args.seniority if args.seniority is not None else DEFAULT_SENIORITY

    rule = Rule(
        id=generate_id(),
        name=args.name,
        pattern=args.pattern,
        action=args.action,
        enabled=True,
        destination=args.destination,
        command=args.command,
        seniority=seniority,
    )

    if rule.action == ActionType.MOVE and not rule.destination:
        print("Error: --destination is required for action 'move'")
        sys.exit(1)

    conflicts = detect_conflicts(rule, config)
    suggested = suggest_seniority(rule, config)
    any_loses = any(c["loses"] for c in conflicts)

    if conflicts:
        print(f"Warning: new rule '{rule.name}' conflicts with existing rules:")
        for c in conflicts:
            print(c["description"])
        if suggested is not None:
            print(f"Suggestion: re-run with --seniority {suggested} to make '{rule.name}' win "
                  f"all conflicts (current seniority={seniority}).")
        if any_loses and not args.force:
            print("New rule would be shadowed. Use --force to add anyway.")
            sys.exit(1)

    config.rules.append(rule)
    save_rules_config(config)
    print(f"Added rule '{rule.name}' (id: {rule.id}, seniority={rule.seniority})")


def cmd_remove_rule(args) -> None:
    config = load_rules_config()

    if args.id:
        config.rules = [r for r in config.rules if r.id != args.id]
    elif args.name:
        config.rules = [r for r in config.rules if r.name != args.name]
    else:
        print("Error: --name or --id is required")
        sys.exit(1)

    save_rules_config(config)
    print("Rule removed")


def cmd_toggle_rule(args) -> None:
    config = load_rules_config()

    target = None
    for rule in config.rules:
        if rule.name == args.name:
            target = rule
            break

    if target is None:
        print(f"Error: Rule '{args.name}' not found")
        sys.exit(1)

    if args.enable:
        target.enabled = True
    elif args.disable:
        target.enabled = False
    else:
        target.enabled = not target.enabled

    save_rules_config(config)
    state = "enabled" if target.enabled else "disabled"
    print(f"Rule '{target.name}' is now {state}")


def cmd_list_rules(args) -> None:
    config = load_rules_config()
    watch_rules = parse_watch_rules(config.watch_rules)

    rows: List[Dict[str, str]] = []

    cli_rules = config.rules
    if args.enabled:
        cli_rules = [r for r in cli_rules if r.enabled]
    if args.pattern:
        cli_rules = [r for r in cli_rules if fnmatch.fnmatch(r.pattern, args.pattern) or r.pattern == args.pattern]

    for rule in cli_rules:
        details = ""
        if rule.action == ActionType.MOVE and rule.destination:
            details = f"-> {rule.destination}"
        elif rule.action == ActionType.RUN and rule.command:
            details = f"$ {rule.command}"
        rows.append({
            "id": rule.id,
            "kind": "cli",
            "name": rule.name,
            "pattern": rule.pattern,
            "action": rule.action,
            "enabled": "Yes" if rule.enabled else "No",
            "seniority": str(rule.seniority),
            "details": details,
        })

    for wr in watch_rules:
        wr_enabled = "Yes" if wr.enabled else "No"
        if args.enabled and not wr.enabled:
            continue

        for dr in wr.domain_rules:
            exts = ",".join(dr.extensions) if dr.extensions else "*"
            if args.pattern and not (fnmatch.fnmatch(f"*{exts}", args.pattern)):
                continue
            rows.append({
                "id": "-",
                "kind": "domain",
                "name": f"{wr.name} / {dr.name}",
                "pattern": f"{dr.domain}:{exts}",
                "action": "move",
                "enabled": wr_enabled,
                "seniority": str(dr.seniority),
                "details": f"-> {dr.destination}",
            })

        for tr in wr.type_rules:
            exts = ",".join(tr.extensions)
            if args.pattern and not (fnmatch.fnmatch(f"*{exts}", args.pattern) or
                                     any(fnmatch.fnmatch(e, args.pattern) for e in tr.extensions)):
                continue
            rows.append({
                "id": "-",
                "kind": "type",
                "name": f"{wr.name} / {tr.name}",
                "pattern": exts,
                "action": "move",
                "enabled": wr_enabled,
                "seniority": str(tr.seniority),
                "details": f"-> {tr.destination}",
            })

    if not rows:
        print("No rules found")
        return

    global_state = "ENABLED" if config.enabled else "DISABLED"
    print(f"Sharktopus: {global_state}")
    header = f"{'ID':<10} {'Kind':<8} {'Name':<40} {'Pattern':<28} {'Action':<8} {'Enabled':<8} {'Sen':<5} Details"
    print(header)
    print("-" * len(header))

    for row in rows:
        print(f"{row['id']:<10} {row['kind']:<8} {row['name']:<40} {row['pattern']:<28} "
              f"{row['action']:<8} {row['enabled']:<8} {row['seniority']:<5} {row['details']}")


def cmd_toggle(args) -> None:
    config = load_rules_config()

    if args.enable:
        config.enabled = True
    elif args.disable:
        config.enabled = False
    else:
        config.enabled = not config.enabled

    save_rules_config(config)
    state = "enabled" if config.enabled else "disabled"
    print(f"Sharktopus is now {state}")


def cmd_rules(args) -> None:
    if not RULES_FILE.exists():
        save_rules_config(RulesConfig())

    editor = os.environ.get("EDITOR", "code")
    try:
        subprocess.run([editor, str(RULES_FILE)])
    except FileNotFoundError:
        subprocess.run(["open", str(RULES_FILE)])


def cmd_status(args) -> None:
    config = load_rules_config()
    global_state = "ENABLED" if config.enabled else "DISABLED"

    if PID_FILE.exists():
        pid = PID_FILE.read_text().strip()
        try:
            os.kill(int(pid), 0)
            print(f"Sharktopus is running (PID: {pid}) [{global_state}]")
        except OSError:
            print(f"Sharktopus is not running (stale PID file) [{global_state}]")
            PID_FILE.unlink()
    else:
        print(f"Sharktopus is not running [{global_state}]")

    print(f"  CLI rules: {len(config.rules)}")
    print(f"  Watch rules: {len(config.watch_rules)}")
    print(f"  Config: {RULES_FILE}")


def cmd_run(args) -> None:
    config = load_rules_config()
    service = SharktopusService(config)
    service.run()


def cmd_migrate(args) -> None:
    if not LEGACY_CONFIG_FILE.exists():
        print("No legacy config found to migrate")
        return

    config = migrate_legacy_config()
    print(f"Migrated legacy config to {RULES_FILE}")
    print(f"  Watch rules: {len(config.watch_rules)}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="sharktopus",
        description="Sharktopus - Automatic File Organization Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    p_add = subparsers.add_parser("add-rule", help="Add a new rule")
    p_add.add_argument("--name", required=True, help="Rule name")
    p_add.add_argument("--pattern", required=True, help="File pattern (glob)")
    p_add.add_argument("--action", required=True, choices=["move", "run"], help="Action type")
    p_add.add_argument("--destination", help="Destination directory (for move)")
    p_add.add_argument("--command", help="Command to run (for run)")
    p_add.add_argument("--seniority", type=int, default=None,
                      help="Seniority (higher wins conflicts). Default: 1")
    p_add.add_argument("--force", action="store_true",
                      help="Add rule even if it conflicts with existing rules")

    p_remove = subparsers.add_parser("remove-rule", help="Remove a rule")
    p_remove.add_argument("--name", help="Rule name")
    p_remove.add_argument("--id", help="Rule ID")

    p_toggle_rule = subparsers.add_parser("toggle-rule", help="Toggle a rule on/off")
    p_toggle_rule.add_argument("--name", required=True, help="Rule name")
    p_toggle_rule.add_argument("--enable", action="store_true", help="Enable the rule")
    p_toggle_rule.add_argument("--disable", action="store_true", help="Disable the rule")

    p_list = subparsers.add_parser("list-rules", help="List all rules")
    p_list.add_argument("--enabled", action="store_true", help="Show only enabled rules")
    p_list.add_argument("--pattern", help="Filter by pattern")

    p_toggle = subparsers.add_parser("toggle", help="Toggle Sharktopus on/off globally")
    p_toggle.add_argument("--enable", action="store_true", help="Enable globally")
    p_toggle.add_argument("--disable", action="store_true", help="Disable globally")

    subparsers.add_parser("rules", help="Open rules config in editor")
    subparsers.add_parser("status", help="Show service status")
    subparsers.add_parser("run", help="Run the service")
    subparsers.add_parser("migrate", help="Migrate legacy config")

    args = parser.parse_args()

    if not RULES_FILE.exists() and LEGACY_CONFIG_FILE.exists():
        migrate_legacy_config()

    if args.subcommand is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "add-rule": cmd_add_rule,
        "remove-rule": cmd_remove_rule,
        "toggle-rule": cmd_toggle_rule,
        "list-rules": cmd_list_rules,
        "toggle": cmd_toggle,
        "rules": cmd_rules,
        "status": cmd_status,
        "run": cmd_run,
        "migrate": cmd_migrate,
    }

    handler = commands.get(args.subcommand)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
