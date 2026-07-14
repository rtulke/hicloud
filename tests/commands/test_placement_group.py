#!/usr/bin/env python3

from commands.placement_group import PlacementGroupCommands


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
        self.group = {
            "id": 5,
            "name": "spread-a",
            "type": "spread",
            "created": "2026-07-01T10:00:00+00:00",
            "servers": [],
            "labels": {"env": "prod"},
        }
        self.server = {"id": 7, "name": "web-01", "status": "off", "placement_group": None}
        self.create_calls = []
        self.update_calls = []
        self.delete_calls = []
        self.add_calls = []
        self.remove_calls = []

    def list_placement_groups(self):
        return [self.group]

    def get_placement_group_by_id(self, group_id):
        if group_id == 5:
            return self.group
        # mirrors the real API layer, which prints the not-found message itself
        print(f"Placement group with ID {group_id} not found")
        return {}

    def get_server_by_id(self, server_id):
        if server_id == 7:
            return self.server
        print(f"VM with ID {server_id} not found")
        return None

    def create_placement_group(self, name, group_type="spread", labels=None):
        self.create_calls.append((name, group_type, labels))
        return {"id": 6, "name": name}

    def update_placement_group(self, group_id, name=None, labels=None):
        self.update_calls.append((group_id, name, labels))
        return {"id": group_id}

    def delete_placement_group(self, group_id):
        self.delete_calls.append(group_id)
        return True

    def add_server_to_placement_group(self, server_id, group_id):
        self.add_calls.append((server_id, group_id))
        return True

    def remove_server_from_placement_group(self, server_id):
        self.remove_calls.append(server_id)
        return True


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return PlacementGroupCommands(c), h, c


def _feed(monkeypatch, answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _: next(it))


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_groups()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Type" in headers
    assert title == "Placement Groups"
    assert rows[0][0] == 5
    assert rows[0][2] == "spread"


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.group = None
    h.list_placement_groups = lambda: []
    cmd.list_groups()
    assert "No placement groups found" in capsys.readouterr().out


# --- info ---

def test_info_shows_details(capsys):
    cmd, _, _ = build()
    cmd.show_group_info(["5"])
    out = capsys.readouterr().out
    assert "spread-a" in out
    assert "env: prod" in out
    assert "Servers: None" in out


def test_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_group_info([])
    assert "Missing placement group ID" in capsys.readouterr().out


def test_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_group_info(["abc"])
    assert "Invalid placement group ID" in capsys.readouterr().out


# --- create ---

def test_create_confirmed(monkeypatch):
    cmd, h, _ = build()
    _feed(monkeypatch, ["pg-1", "n", "y"])  # name, no labels, confirm
    cmd.create_group()
    assert h.create_calls == [("pg-1", "spread", None)]


def test_create_cancelled(monkeypatch):
    cmd, h, _ = build()
    _feed(monkeypatch, ["pg-1", "n", "n"])
    cmd.create_group()
    assert h.create_calls == []


def test_create_requires_name(monkeypatch, capsys):
    cmd, h, _ = build()
    _feed(monkeypatch, [""])
    cmd.create_group()
    assert "name is required" in capsys.readouterr().out
    assert h.create_calls == []


# --- update ---

def test_update_no_changes(monkeypatch, capsys):
    cmd, h, _ = build()
    _feed(monkeypatch, ["", "n"])  # keep name, no label update
    cmd.update_group(["5"])
    assert "No changes made" in capsys.readouterr().out
    assert h.update_calls == []


def test_update_name_confirmed(monkeypatch):
    cmd, h, _ = build()
    _feed(monkeypatch, ["new-name", "n", "y"])  # new name, no labels, confirm
    cmd.update_group(["5"])
    assert h.update_calls == [(5, "new-name", None)]


# --- delete ---

def test_delete_blocked_when_servers_present(capsys):
    cmd, h, _ = build()
    h.group["servers"] = [1, 2]
    cmd.delete_group(["5"])
    out = capsys.readouterr().out
    assert "still contains" in out
    assert h.delete_calls == []


def test_delete_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_group(["5"])
    assert h.delete_calls == [5]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_group(["5"])
    assert h.delete_calls == []


# --- add ---

def test_add_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.add_server(["5", "7"])
    assert h.add_calls == [(7, 5)]


def test_add_blocked_when_running(capsys):
    cmd, h, _ = build()
    h.server["status"] = "running"
    cmd.add_server(["5", "7"])
    out = capsys.readouterr().out
    assert "powered off" in out
    assert "vm stop 7" in out
    assert h.add_calls == []


def test_add_blocked_when_already_in_group(capsys):
    cmd, h, _ = build()
    h.server["placement_group"] = {"id": 9, "name": "other"}
    cmd.add_server(["5", "7"])
    out = capsys.readouterr().out
    assert "already in placement group" in out
    assert h.add_calls == []


# --- remove ---

def test_remove_not_in_group(capsys):
    cmd, h, _ = build()
    cmd.remove_server(["7"])
    assert "not in any placement group" in capsys.readouterr().out
    assert h.remove_calls == []


def test_remove_confirmed(monkeypatch):
    cmd, h, _ = build()
    h.server["placement_group"] = {"id": 5, "name": "spread-a"}
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.remove_server(["7"])
    assert h.remove_calls == [7]
