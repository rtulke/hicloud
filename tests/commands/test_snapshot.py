#!/usr/bin/env python3

from commands.snapshot import SnapshotCommands


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
        self.snapshots = [
            {
                "id": 10,
                "description": "snap-a",
                "created": "2024-03-01T12:00:00Z",
                "image_size": 5.5,
                "created_from": {"id": 1, "name": "server-a"},
            },
            {
                "id": 11,
                "description": "snap-b",
                "created": "2024-03-02T08:00:00Z",
                "image_size": 3.2,
                "created_from": {"id": 2, "name": "server-b"},
            },
        ]
        self.server = {"id": 1, "name": "server-a", "status": "running"}
        self.create_calls = []
        self.delete_calls = []
        self.rebuild_calls = []

    def list_snapshots(self, vm_id=None):
        if vm_id is not None:
            return [s for s in self.snapshots if s["created_from"]["id"] == vm_id]
        return self.snapshots

    def get_server_by_id(self, server_id):
        return self.server if server_id == 1 else None

    def create_snapshot(self, vm_id, description=None):
        self.create_calls.append(vm_id)
        return {"id": 99}

    def delete_snapshot(self, snap_id):
        self.delete_calls.append(snap_id)
        return True

    def rebuild_server_from_snapshot(self, server_id, snapshot_id):
        self.rebuild_calls.append((server_id, snapshot_id))
        return True


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return SnapshotCommands(c), h, c


# --- list ---

def test_list_groups_by_server():
    cmd, _, console = build()
    cmd.list_snapshots([])
    # one table per server group
    assert len(console.tables) == 2
    titles = [t for _, _, t in console.tables]
    assert "server-a" in titles
    assert "server-b" in titles


def test_list_filtered_by_vm():
    cmd, h, console = build()
    cmd.list_snapshots(["1"])
    assert len(console.tables) == 1
    _, rows, title = console.tables[0]
    assert title == "server-a"
    assert len(rows) == 1
    assert rows[0][0] == 10


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.snapshots = []
    cmd.list_snapshots([])
    assert "No snapshots" in capsys.readouterr().out


def test_list_invalid_vm_id(capsys):
    cmd, _, _ = build()
    cmd.list_snapshots(["abc"])
    assert "Invalid VM ID" in capsys.readouterr().out


# --- create ---

def test_create_snapshot():
    cmd, h, _ = build()
    cmd.create_snapshot(["1"])
    assert h.create_calls == [1]


def test_create_missing_id(capsys):
    cmd, _, _ = build()
    cmd.create_snapshot([])
    assert "Missing VM ID" in capsys.readouterr().out


def test_create_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.create_snapshot(["abc"])
    assert "Invalid VM ID" in capsys.readouterr().out


def test_create_server_not_found(capsys):
    cmd, _, _ = build()
    cmd.create_snapshot(["99"])
    assert "not found" in capsys.readouterr().out


# --- delete single ---

def test_delete_single_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_snapshot(["10"])
    assert h.delete_calls == [10]


def test_delete_single_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_snapshot(["10"])
    assert h.delete_calls == []


def test_delete_missing_arg(capsys):
    cmd, _, _ = build()
    cmd.delete_snapshot([])
    assert "Missing" in capsys.readouterr().out


# --- delete all ---

def test_delete_all_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_snapshot(["all", "1"])
    assert 10 in h.delete_calls


def test_delete_all_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_snapshot(["all", "1"])
    assert h.delete_calls == []


def test_delete_all_missing_vm_id(capsys):
    cmd, _, _ = build()
    cmd.delete_snapshot(["all"])
    assert "Missing VM ID" in capsys.readouterr().out


def test_delete_all_no_snapshots(monkeypatch, capsys):
    cmd, h, _ = build()
    h.snapshots = []
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_snapshot(["all", "1"])
    assert "No snapshots" in capsys.readouterr().out


# --- rebuild ---

def test_rebuild_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "rebuild")
    cmd.rebuild_snapshot(["10", "1"])
    assert h.rebuild_calls == [(1, 10)]


def test_rebuild_wrong_confirmation(monkeypatch, capsys):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    cmd.rebuild_snapshot(["10", "1"])
    out = capsys.readouterr().out
    assert "cancelled" in out
    assert h.rebuild_calls == []


def test_rebuild_missing_args(capsys):
    cmd, _, _ = build()
    cmd.rebuild_snapshot(["10"])
    assert "Missing" in capsys.readouterr().out


def test_rebuild_snapshot_not_found(capsys):
    cmd, _, _ = build()
    cmd.rebuild_snapshot(["999", "1"])
    assert "not found" in capsys.readouterr().out
