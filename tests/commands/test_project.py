#!/usr/bin/env python3

import os
import pytest
from commands.project import ProjectCommands


class DummyConsole:
    def __init__(self, hetzner):
        self.hetzner = hetzner
        self.tables = []

    def print_table(self, headers, rows, title=None):
        self.tables.append((headers, rows, title))

    def horizontal_line(self, char="="):
        return char * 60


class DummyHetzner:
    def __init__(self):
        self.project_name = "default"
        self.headers = {"Authorization": "Bearer test-token-xyz"}

    def list_servers(self):
        return [
            {"id": 1, "name": "web-01", "status": "running", "server_type": {"name": "cx22"}},
        ]

    def list_snapshots(self):
        return [
            {"id": 10, "description": "snap-a", "created": "2024-03-01T12:00:00Z"},
        ]

    def list_ssh_keys(self):
        return [{"id": 7, "name": "my-key"}]

    def list_backups(self):
        return []

    def _make_request(self, method, path, data=None):
        return 200, {"datacenters": [{"name": "nbg1-dc3"}]}


def build(tmp_path=None, config_content=None):
    h = DummyHetzner()
    c = DummyConsole(h)
    return ProjectCommands(c), h, c


# --- show_resources ---

def test_show_resources_builds_tables():
    cmd, _, console = build()
    cmd.show_resources()
    titles = [t for _, _, t in console.tables]
    assert any("Virtual Machines" in (t or "") for t in titles)
    assert any("Snapshots" in (t or "") for t in titles)
    assert any("SSH Keys" in (t or "") for t in titles)


def test_show_resources_empty_project(capsys):
    cmd, h, console = build()
    h.list_servers = lambda: []
    h.list_snapshots = lambda: []
    h.list_ssh_keys = lambda: []
    h.list_backups = lambda: []
    cmd.show_resources()
    out = capsys.readouterr().out
    assert "0" in out


# --- list_projects ---

def test_list_projects_no_config(monkeypatch, capsys):
    cmd, _, _ = build()
    monkeypatch.setattr("commands.project.DEFAULT_CONFIG_PATH", "/nonexistent/.hicloud.toml")
    cmd.list_projects()
    assert "No configuration file" in capsys.readouterr().out


def test_list_projects_shows_sections(monkeypatch, tmp_path):
    config_file = tmp_path / ".hicloud.toml"
    config_file.write_text(
        "[default]\napi_token = \"abc\"\nproject_name = \"Default\"\n"
        "[prod]\napi_token = \"xyz\"\nproject_name = \"Production\"\n"
    )
    config_file.chmod(0o600)

    monkeypatch.setattr("commands.project.DEFAULT_CONFIG_PATH", str(config_file))
    cmd, _, console = build()
    cmd.list_projects()
    assert len(console.tables) == 1
    _, rows, _ = console.tables[0]
    project_keys = [r[0] for r in rows]
    assert "default" in project_keys
    assert "prod" in project_keys


# --- switch_project ---

def test_switch_project_missing_arg(capsys):
    cmd, _, _ = build()
    cmd.switch_project([])
    assert "Missing project name" in capsys.readouterr().out


def test_switch_project_no_config(monkeypatch, capsys):
    cmd, _, _ = build()
    monkeypatch.setattr("commands.project.DEFAULT_CONFIG_PATH", "/nonexistent/.hicloud.toml")
    cmd.switch_project(["prod"])
    assert "No configuration file" in capsys.readouterr().out


def test_switch_project_not_found(monkeypatch, tmp_path, capsys):
    config_file = tmp_path / ".hicloud.toml"
    config_file.write_text("[default]\napi_token = \"abc\"\nproject_name = \"Default\"\n")
    config_file.chmod(0o600)

    monkeypatch.setattr("commands.project.DEFAULT_CONFIG_PATH", str(config_file))
    cmd, _, _ = build()
    cmd.switch_project(["nonexistent"])
    out = capsys.readouterr().out
    assert "not found" in out


# --- show_info ---

def test_show_info_outputs_project_name(capsys):
    cmd, _, _ = build()
    cmd.show_info()
    out = capsys.readouterr().out
    assert "default" in out


def test_show_info_shows_server_count(capsys):
    cmd, _, _ = build()
    cmd.show_info()
    out = capsys.readouterr().out
    assert "1" in out  # 1 server


# --- handle_command ---

def test_handle_no_subcommand():
    # no subcommand → calls show_resources (no crash)
    cmd, _, console = build()
    cmd.handle_command([])
    assert len(console.tables) >= 1  # show_resources produces tables


def test_handle_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown project subcommand" in capsys.readouterr().out
