#!/usr/bin/env python3
"""Tests for Sharktopus CLI and rule management."""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import sharktopus
from sharktopus import (
    Rule,
    RulesConfig,
    ActionType,
    generate_id,
    load_rules_config,
    save_rules_config,
    matches_cli_rule,
    execute_cli_rule,
    parse_watch_rules,
    cmd_add_rule,
    cmd_remove_rule,
    cmd_toggle_rule,
    cmd_list_rules,
    cmd_toggle,
    cmd_status,
    migrate_legacy_config,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / "config" / "sharktopus"
    config_dir.mkdir(parents=True)
    rules_file = config_dir / "rules.json"

    with patch.object(sharktopus, "CONFIG_DIR", config_dir), \
         patch.object(sharktopus, "RULES_FILE", rules_file):
        yield config_dir, rules_file


@pytest.fixture
def sample_config(temp_config_dir):
    config_dir, rules_file = temp_config_dir
    config = RulesConfig(
        enabled=True,
        rules=[
            Rule(id="ABC123", name="move soupified", pattern="*.soup.md",
                 action="move", enabled=True, destination="/tmp/soup"),
            Rule(id="DEF456", name="auto-desoupify", pattern="*.soup.md",
                 action="run", enabled=False, command="soupify -d"),
        ],
        watch_rules=[],
        settings={"log_level": "INFO", "log_file": str(config_dir / "test.log")},
    )
    save_rules_config(config)
    return config


class TestRule:
    def test_to_dict_move(self):
        rule = Rule(id="A1B2C3", name="test", pattern="*.txt",
                    action="move", destination="/tmp")
        d = rule.to_dict()
        assert d["id"] == "A1B2C3"
        assert d["name"] == "test"
        assert d["pattern"] == "*.txt"
        assert d["action"] == "move"
        assert d["destination"] == "/tmp"
        assert "command" not in d

    def test_to_dict_run(self):
        rule = Rule(id="X1Y2Z3", name="test", pattern="*.md",
                    action="run", command="echo hello")
        d = rule.to_dict()
        assert d["command"] == "echo hello"
        assert "destination" not in d

    def test_from_dict(self):
        data = {
            "id": "TEST123",
            "name": "my rule",
            "pattern": "*.py",
            "action": "move",
            "enabled": False,
            "destination": "/tmp/py",
        }
        rule = Rule.from_dict(data)
        assert rule.id == "TEST123"
        assert rule.name == "my rule"
        assert rule.enabled is False
        assert rule.destination == "/tmp/py"

    def test_roundtrip(self):
        original = Rule(id="RT001", name="roundtrip", pattern="*.json",
                       action="run", enabled=True, command="cat")
        restored = Rule.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.pattern == original.pattern
        assert restored.action == original.action
        assert restored.command == original.command


class TestRulesConfig:
    def test_empty_config(self):
        config = RulesConfig()
        assert config.enabled is True
        assert config.rules == []
        assert config.watch_rules == []

    def test_to_dict(self):
        config = RulesConfig(
            enabled=False,
            rules=[Rule(id="A1", name="r1", pattern="*.txt", action="move", destination="/tmp")],
        )
        d = config.to_dict()
        assert d["enabled"] is False
        assert len(d["rules"]) == 1
        assert d["rules"][0]["name"] == "r1"

    def test_from_dict(self):
        data = {
            "enabled": False,
            "rules": [
                {"id": "B2", "name": "r2", "pattern": "*.md", "action": "run", "command": "echo"}
            ],
            "watch_rules": [{"name": "watch1", "watch_directory": "~/Downloads"}],
            "settings": {"log_level": "DEBUG"},
        }
        config = RulesConfig.from_dict(data)
        assert config.enabled is False
        assert len(config.rules) == 1
        assert config.rules[0].command == "echo"
        assert len(config.watch_rules) == 1
        assert config.settings["log_level"] == "DEBUG"

    def test_roundtrip(self, sample_config):
        loaded = load_rules_config()
        assert loaded.enabled == sample_config.enabled
        assert len(loaded.rules) == len(sample_config.rules)
        assert loaded.rules[0].name == sample_config.rules[0].name


class TestSaveLoadConfig:
    def test_save_and_load(self, temp_config_dir):
        config = RulesConfig(
            enabled=True,
            rules=[Rule(id="SL01", name="test", pattern="*.txt", action="move", destination="/tmp")],
        )
        save_rules_config(config)

        loaded = load_rules_config()
        assert len(loaded.rules) == 1
        assert loaded.rules[0].id == "SL01"

    def test_load_nonexistent(self, temp_config_dir):
        config = load_rules_config()
        assert config.enabled is True
        assert config.rules == []


class TestMatchesCliRule:
    def test_glob_match(self):
        rule = Rule(id="M1", name="test", pattern="*.soup.md", action="move", destination="/tmp")
        assert matches_cli_rule(Path("/some/path/file.soup.md"), rule) is True

    def test_glob_no_match(self):
        rule = Rule(id="M2", name="test", pattern="*.soup.md", action="move", destination="/tmp")
        assert matches_cli_rule(Path("/some/path/file.txt"), rule) is False

    def test_suffix_match(self):
        rule = Rule(id="M3", name="test", pattern="*.soup.md", action="move", destination="/tmp")
        assert matches_cli_rule(Path("/path/to/deeply.nested.soup.md"), rule) is True

    def test_wildcard_all(self):
        rule = Rule(id="M4", name="test", pattern="*", action="move", destination="/tmp")
        assert matches_cli_rule(Path("/path/to/anything.txt"), rule) is True

    def test_specific_extension(self):
        rule = Rule(id="M5", name="test", pattern="*.py", action="run", command="python")
        assert matches_cli_rule(Path("script.py"), rule) is True
        assert matches_cli_rule(Path("script.js"), rule) is False


class TestExecuteCliRule:
    def test_move_rule(self, tmp_path):
        src_file = tmp_path / "test.soup.md"
        src_file.write_text("test content")
        dest_dir = tmp_path / "dest"

        rule = Rule(id="E1", name="move test", pattern="*.soup.md",
                    action="move", destination=str(dest_dir))
        logger = MagicMock()

        execute_cli_rule(src_file, rule, logger)

        assert not src_file.exists()
        assert (dest_dir / "test.soup.md").exists()

    def test_run_rule_with_file_placeholder(self, tmp_path):
        src_file = tmp_path / "test.soup.md"
        src_file.write_text("test content")
        output_file = tmp_path / "output.txt"

        rule = Rule(id="E2", name="run test", pattern="*.soup.md",
                    action="run", command=f"echo __FILE__ > {output_file}")
        logger = MagicMock()

        execute_cli_rule(src_file, rule, logger)

        assert output_file.exists()
        content = output_file.read_text().strip()
        assert str(src_file) in content

    def test_run_rule_without_placeholder(self, tmp_path):
        src_file = tmp_path / "test.soup.md"
        src_file.write_text("test content")
        output_file = tmp_path / "output.txt"

        rule = Rule(id="E3", name="run test", pattern="*.soup.md",
                    action="run", command=f"echo")
        logger = MagicMock()

        execute_cli_rule(src_file, rule, logger)
        logger.info.assert_called()

    def test_move_no_destination(self, tmp_path):
        src_file = tmp_path / "test.txt"
        src_file.write_text("test")

        rule = Rule(id="E4", name="bad move", pattern="*.txt", action="move")
        logger = MagicMock()

        execute_cli_rule(src_file, rule, logger)
        logger.warning.assert_called_once()


class TestCmdAddRule:
    def _make_args(self, **overrides):
        args = MagicMock()
        args.name = "new move rule"
        args.pattern = "*.txt"
        args.action = "move"
        args.destination = "/tmp/txt"
        args.command = None
        args.seniority = None
        args.force = False
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def test_add_move_rule(self, sample_config, capsys):
        args = self._make_args()

        cmd_add_rule(args)

        captured = capsys.readouterr()
        assert "Added rule" in captured.out

        config = load_rules_config()
        assert len(config.rules) == 3
        assert config.rules[2].name == "new move rule"

    def test_add_run_rule(self, sample_config, capsys):
        args = self._make_args(
            name="new run rule",
            pattern="*.py",
            action="run",
            destination=None,
            command="python",
        )

        cmd_add_rule(args)

        config = load_rules_config()
        assert len(config.rules) == 3
        assert config.rules[2].command == "python"

    def test_add_duplicate_name(self, sample_config, capsys):
        args = self._make_args(name="move soupified")

        with pytest.raises(SystemExit):
            cmd_add_rule(args)

    def test_add_move_without_destination(self, sample_config, capsys):
        args = self._make_args(name="bad rule", destination=None)

        with pytest.raises(SystemExit):
            cmd_add_rule(args)

    def test_add_conflicting_rule_without_force_fails(self, sample_config, capsys):
        # sample_config has 'move soupified' with pattern *.soup.md, seniority 1
        args = self._make_args(
            name="another soup rule",
            pattern="*.soup.md",
            destination="/tmp/other",
        )

        with pytest.raises(SystemExit):
            cmd_add_rule(args)

        captured = capsys.readouterr()
        assert "conflicts" in captured.out
        assert "Suggestion" in captured.out

    def test_add_winning_conflict_proceeds_without_force(self, sample_config, capsys):
        # New rule at seniority 5 beats existing *.soup.md rule at seniority 1
        args = self._make_args(
            name="winning soup rule",
            pattern="*.soup.md",
            destination="/tmp/winner",
            seniority=5,
        )

        cmd_add_rule(args)

        captured = capsys.readouterr()
        assert "conflicts" in captured.out  # still warns
        assert "Added rule" in captured.out  # but proceeds
        config = load_rules_config()
        assert len(config.rules) == 3

    def test_add_conflicting_rule_with_force(self, sample_config, capsys):
        args = self._make_args(
            name="another soup rule",
            pattern="*.soup.md",
            destination="/tmp/other",
            force=True,
        )

        cmd_add_rule(args)

        captured = capsys.readouterr()
        assert "Added rule" in captured.out
        config = load_rules_config()
        assert len(config.rules) == 3

    def test_add_with_explicit_seniority(self, sample_config, capsys):
        args = self._make_args(seniority=5)

        cmd_add_rule(args)

        config = load_rules_config()
        assert config.rules[2].seniority == 5

    def test_suggest_seniority_for_loss(self, sample_config):
        # sample_config has *.soup.md rule at seniority 1; new rule at 1 loses tie
        new_rule = Rule(id="X", name="new", pattern="*.soup.md", action="move",
                        destination="/tmp/x", seniority=1)
        config = load_rules_config()
        suggested = sharktopus.suggest_seniority(new_rule, config)
        assert suggested == 2


class TestCmdRemoveRule:
    def test_remove_by_name(self, sample_config, capsys):
        args = MagicMock()
        args.name = "move soupified"
        args.id = None

        cmd_remove_rule(args)

        config = load_rules_config()
        assert len(config.rules) == 1
        assert config.rules[0].name == "auto-desoupify"

    def test_remove_by_id(self, sample_config, capsys):
        args = MagicMock()
        args.name = None
        args.id = "DEF456"

        cmd_remove_rule(args)

        config = load_rules_config()
        assert len(config.rules) == 1
        assert config.rules[0].id == "ABC123"

    def test_remove_no_args(self, sample_config, capsys):
        args = MagicMock()
        args.name = None
        args.id = None

        with pytest.raises(SystemExit):
            cmd_remove_rule(args)


class TestCmdToggleRule:
    def test_toggle_on(self, sample_config, capsys):
        args = MagicMock()
        args.name = "auto-desoupify"
        args.enable = True
        args.disable = False

        cmd_toggle_rule(args)

        config = load_rules_config()
        rule = [r for r in config.rules if r.name == "auto-desoupify"][0]
        assert rule.enabled is True

    def test_toggle_off(self, sample_config, capsys):
        args = MagicMock()
        args.name = "move soupified"
        args.enable = False
        args.disable = True

        cmd_toggle_rule(args)

        config = load_rules_config()
        rule = [r for r in config.rules if r.name == "move soupified"][0]
        assert rule.enabled is False

    def test_toggle_flip(self, sample_config, capsys):
        args = MagicMock()
        args.name = "move soupified"
        args.enable = False
        args.disable = False

        cmd_toggle_rule(args)

        config = load_rules_config()
        rule = [r for r in config.rules if r.name == "move soupified"][0]
        assert rule.enabled is False

    def test_toggle_not_found(self, sample_config, capsys):
        args = MagicMock()
        args.name = "nonexistent"
        args.enable = False
        args.disable = False

        with pytest.raises(SystemExit):
            cmd_toggle_rule(args)


class TestCmdListRules:
    def test_list_all(self, sample_config, capsys):
        args = MagicMock()
        args.enabled = False
        args.pattern = None

        cmd_list_rules(args)

        captured = capsys.readouterr()
        assert "move soupified" in captured.out
        assert "auto-desoupify" in captured.out

    def test_list_enabled_only(self, sample_config, capsys):
        args = MagicMock()
        args.enabled = True
        args.pattern = None

        cmd_list_rules(args)

        captured = capsys.readouterr()
        assert "move soupified" in captured.out
        assert "auto-desoupify" not in captured.out

    def test_list_by_pattern(self, sample_config, capsys):
        args = MagicMock()
        args.enabled = False
        args.pattern = "*.soup.md"

        cmd_list_rules(args)

        captured = capsys.readouterr()
        assert "move soupified" in captured.out
        assert "auto-desoupify" in captured.out

    def test_list_empty(self, temp_config_dir, capsys):
        args = MagicMock()
        args.enabled = False
        args.pattern = None

        cmd_list_rules(args)

        captured = capsys.readouterr()
        assert "No rules found" in captured.out


class TestCmdToggle:
    def test_toggle_global_off(self, sample_config, capsys):
        args = MagicMock()
        args.enable = False
        args.disable = True

        cmd_toggle(args)

        config = load_rules_config()
        assert config.enabled is False

    def test_toggle_global_on(self, sample_config, capsys):
        config = load_rules_config()
        config.enabled = False
        save_rules_config(config)

        args = MagicMock()
        args.enable = True
        args.disable = False

        cmd_toggle(args)

        config = load_rules_config()
        assert config.enabled is True

    def test_toggle_global_flip(self, sample_config, capsys):
        args = MagicMock()
        args.enable = False
        args.disable = False

        cmd_toggle(args)

        config = load_rules_config()
        assert config.enabled is False


class TestCmdStatus:
    def test_status_not_running(self, sample_config, capsys):
        args = MagicMock()

        with patch.object(sharktopus, "PID_FILE", Path("/nonexistent/pid")):
            cmd_status(args)

        captured = capsys.readouterr()
        assert "not running" in captured.out


class TestMigrateLegacyConfig:
    def test_migrate(self, tmp_path):
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        legacy_file = legacy_dir / "config.yaml"
        legacy_file.write_text("""
settings:
  log_level: DEBUG
watch_rules:
  - name: "Test Watcher"
    watch_directory: "~/Downloads"
    enabled: true
    type_rules:
      video:
        extensions: [".mp4"]
        destination: "vid"
    redirect_destination: "tmp"
""")

        config_dir = tmp_path / "config" / "sharktopus"
        config_dir.mkdir(parents=True)
        rules_file = config_dir / "rules.json"

        with patch.object(sharktopus, "LEGACY_CONFIG_FILE", legacy_file), \
             patch.object(sharktopus, "CONFIG_DIR", config_dir), \
             patch.object(sharktopus, "RULES_FILE", rules_file):
            config = migrate_legacy_config()

        assert len(config.watch_rules) == 1
        assert config.settings["log_level"] == "DEBUG"
        assert rules_file.exists()

    def test_migrate_no_legacy(self, tmp_path):
        config_dir = tmp_path / "config" / "sharktopus"
        config_dir.mkdir(parents=True)
        rules_file = config_dir / "rules.json"

        with patch.object(sharktopus, "LEGACY_CONFIG_FILE", Path("/nonexistent")), \
             patch.object(sharktopus, "CONFIG_DIR", config_dir), \
             patch.object(sharktopus, "RULES_FILE", rules_file):
            config = migrate_legacy_config()

        assert config.watch_rules == []


class TestGenerateId:
    def test_format(self):
        id1 = generate_id()
        assert len(id1) == 8
        assert id1.isalnum()
        assert id1 == id1.upper()

    def test_uniqueness(self):
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestParseWatchRules:
    def test_parse_basic(self):
        data = [
            {
                "name": "Test",
                "watch_directory": "~/Downloads",
                "enabled": True,
                "type_rules": {
                    "video": {
                        "extensions": [".mp4", ".mkv"],
                        "destination": "vid",
                    }
                },
                "redirect_destination": "tmp",
            }
        ]
        rules = parse_watch_rules(data)
        assert len(rules) == 1
        assert rules[0].name == "Test"
        assert len(rules[0].type_rules) == 1
        assert rules[0].type_rules[0].name == "video"

    def test_skip_disabled(self):
        data = [
            {
                "name": "Disabled",
                "watch_directory": "~/Downloads",
                "enabled": False,
                "type_rules": {},
                "redirect_destination": "tmp",
            }
        ]
        rules = parse_watch_rules(data)
        assert len(rules) == 0

    def test_domain_rules(self):
        data = [
            {
                "name": "With Domains",
                "watch_directory": "~/Downloads",
                "enabled": True,
                "redirect_domains": ["facebook.com"],
                "domain_rules": {
                    "claude": {
                        "domain": "claude.ai",
                        "extensions": [".md"],
                        "destination": "~/output",
                    }
                },
                "type_rules": {},
                "redirect_destination": "tmp",
            }
        ]
        rules = parse_watch_rules(data)
        assert len(rules) == 1
        assert len(rules[0].domain_rules) == 1
        assert rules[0].domain_rules[0].domain == "claude.ai"
        assert rules[0].redirect_domains == ["facebook.com"]
