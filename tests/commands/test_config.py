#!/usr/bin/env python3

import os
import stat
import tempfile

from commands.config import ConfigCommands


class DummyHetzner:
    def __init__(self):
        self.project_name = "test-project"
        self.api_token = "abc123xyzabc123xyzabc123xyzabc123xyz"


class DummyConsole:
    def __init__(self):
        self.hetzner = DummyHetzner()


def build_commands():
    return ConfigCommands(DummyConsole())


# ---------- validate tests ----------

def test_validate_missing_file(capsys):
    commands = build_commands()
    commands.validate_config(["/nonexistent/path/config.toml"])

    output = capsys.readouterr().out
    assert "not found" in output.lower() or "ERROR" in output
    assert "FAILED" in output


def test_validate_valid_config(tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    config.write_text('[default]\napi_token = "' + "A" * 64 + '"\nproject_name = "MyProject"\n')
    os.chmod(config, stat.S_IRUSR | stat.S_IWUSR)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "OK" in output
    assert "FAILED" not in output


def test_validate_insecure_permissions(monkeypatch, tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    config.write_text('[default]\napi_token = "' + "A" * 64 + '"\nproject_name = "MyProject"\n')
    os.chmod(config, 0o644)

    monkeypatch.setattr("commands.config.ConfigManager.check_file_permissions", lambda path: False)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "WARNING" in output
    assert "permissions" in output.lower()


def test_validate_missing_api_token(tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    config.write_text('[default]\nproject_name = "MyProject"\n')
    os.chmod(config, stat.S_IRUSR | stat.S_IWUSR)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "api_token" in output
    assert "FAILED" in output


def test_validate_missing_project_name(tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    config.write_text('[default]\napi_token = "' + "A" * 64 + '"\n')
    os.chmod(config, stat.S_IRUSR | stat.S_IWUSR)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "project_name" in output
    assert "FAILED" in output


def test_validate_suspicious_token(tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    config.write_text('[default]\napi_token = "short"\nproject_name = "X"\n')
    os.chmod(config, stat.S_IRUSR | stat.S_IWUSR)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "WARNING" in output


def test_validate_multiple_sections(tmp_path, capsys):
    config = tmp_path / "hicloud.toml"
    token = "A" * 64
    config.write_text(
        f'[proj1]\napi_token = "{token}"\nproject_name = "P1"\n\n'
        f'[proj2]\napi_token = "{token}"\nproject_name = "P2"\n'
    )
    os.chmod(config, stat.S_IRUSR | stat.S_IWUSR)

    commands = build_commands()
    commands.validate_config([str(config)])

    output = capsys.readouterr().out
    assert "OK" in output
    assert "FAILED" not in output


# ---------- info tests ----------

def test_info_shows_project_and_token(capsys):
    commands = build_commands()
    commands.show_config_info()

    output = capsys.readouterr().out
    assert "test-project" in output
    assert "abc123" in output


def test_is_valid_token():
    commands = build_commands()
    assert commands._is_valid_token("A" * 64) is True
    assert commands._is_valid_token("short") is False
    assert commands._is_valid_token("A" * 64 + " spaces") is False
    assert commands._is_valid_token(123) is False
