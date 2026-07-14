#!/usr/bin/env python3

from commands.action import ActionCommands


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
        self.actions = [
            {
                "id": 42,
                "command": "create_server",
                "status": "running",
                "progress": 50,
                "started": "2026-07-14T10:00:00+00:00",
                "finished": None,
                "resources": [{"type": "server", "id": 7}],
            },
            {
                "id": 41,
                "command": "delete_server",
                "status": "error",
                "progress": 100,
                "started": "2026-07-14T09:00:00+00:00",
                "finished": "2026-07-14T09:00:05+00:00",
                "resources": [{"type": "server", "id": 6}],
                "error": {"code": "server_error", "message": "boom"},
            },
        ]
        self.list_calls = []

    def list_actions(self, status=None):
        self.list_calls.append(status)
        if status:
            return [a for a in self.actions if a["status"] == status]
        return self.actions

    def get_action_by_id(self, action_id):
        for action in self.actions:
            if action["id"] == action_id:
                return action
        # mirrors the real API layer, which prints the not-found message itself
        print(f"Action with ID {action_id} not found")
        return {}


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return ActionCommands(c), h, c


# --- list ---

def test_list_builds_table_newest_first():
    cmd, h, console = build()
    cmd.list_actions([])
    assert h.list_calls == [None]
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Command" in headers
    assert title == "Actions"
    assert rows[0][0] == 42  # sorted by ID, newest first
    assert rows[1][0] == 41


def test_list_with_status_filter():
    cmd, h, console = build()
    cmd.list_actions(["running"])
    assert h.list_calls == ["running"]
    _, rows, title = console.tables[0]
    assert title == "Actions (running)"
    assert len(rows) == 1


def test_list_invalid_status(capsys):
    cmd, h, _ = build()
    cmd.list_actions(["bogus"])
    assert "Unknown status filter" in capsys.readouterr().out
    assert h.list_calls == []


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.actions = []
    cmd.list_actions([])
    assert "No actions found" in capsys.readouterr().out


def test_list_renders_resources_and_progress():
    cmd, _, console = build()
    cmd.list_actions([])
    _, rows, _ = console.tables[0]
    assert rows[0][3] == "50%"
    assert rows[0][6] == "server:7"
    assert rows[0][5] == "-"  # not finished yet


# --- info ---

def test_info_shows_details(capsys):
    cmd, _, _ = build()
    cmd.show_action_info(["42"])
    out = capsys.readouterr().out
    assert "create_server" in out
    assert "running" in out
    assert "server: 7" in out


def test_info_shows_error_block(capsys):
    cmd, _, _ = build()
    cmd.show_action_info(["41"])
    out = capsys.readouterr().out
    assert "server_error" in out
    assert "boom" in out


def test_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_action_info([])
    assert "Missing action ID" in capsys.readouterr().out


def test_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_action_info(["abc"])
    assert "Invalid action ID" in capsys.readouterr().out


def test_info_not_found(capsys):
    cmd, _, _ = build()
    cmd.show_action_info(["99"])
    assert "not found" in capsys.readouterr().out


# --- dispatch ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing action subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown action subcommand" in capsys.readouterr().out
