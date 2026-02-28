#!/usr/bin/env python3

from commands.backup import BackupCommands


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
        self.backups = [
            {
                "id": 20,
                "description": "backup-a",
                "created": "2024-03-01T12:00:00Z",
                "image_size": 8.0,
                "created_from": {"id": 1, "name": "server-a"},
            },
            {
                "id": 21,
                "description": "backup-b",
                "created": "2024-03-02T08:00:00Z",
                "image_size": 4.5,
                "created_from": {"id": 2, "name": "server-b"},
            },
        ]
        self.server = {"id": 1, "name": "server-a", "status": "running"}
        self.enable_calls = []
        self.disable_calls = []
        self.delete_calls = []
        self.list_vm_id_calls = []

    def list_backups(self, vm_id=None):
        self.list_vm_id_calls.append(vm_id)
        if vm_id is not None:
            return [b for b in self.backups if b["created_from"]["id"] == vm_id]
        return self.backups

    def get_server_by_id(self, server_id):
        return self.server if server_id == 1 else None

    def enable_server_backups(self, server_id, window=None):
        self.enable_calls.append((server_id, window))
        return True

    def disable_server_backups(self, server_id):
        self.disable_calls.append(server_id)
        return True

    def delete_backup(self, backup_id):
        self.delete_calls.append(backup_id)
        return True


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return BackupCommands(c), h, c


# --- list ---

def test_list_groups_by_server():
    cmd, _, console = build()
    cmd.list_backups([])
    assert len(console.tables) == 2
    titles = [t for _, _, t in console.tables]
    assert "server-a" in titles
    assert "server-b" in titles


def test_list_filtered_by_vm():
    cmd, h, console = build()
    cmd.list_backups(["1"])
    assert h.list_vm_id_calls[-1] == 1
    assert len(console.tables) == 1
    _, rows, title = console.tables[0]
    assert title == "server-a"
    assert rows[0][0] == 20


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.backups = []
    cmd.list_backups([])
    assert "No backups" in capsys.readouterr().out


def test_list_invalid_vm_id(capsys):
    cmd, _, _ = build()
    cmd.list_backups(["abc"])
    assert "Invalid VM ID" in capsys.readouterr().out


# --- enable ---

def test_enable_backup():
    cmd, h, _ = build()
    cmd.enable_backup(["1"])
    assert h.enable_calls == [(1, None)]


def test_enable_backup_with_valid_window():
    cmd, h, _ = build()
    cmd.enable_backup(["1", "22-02"])
    assert h.enable_calls == [(1, "22-02")]


def test_enable_backup_invalid_window(capsys):
    cmd, h, _ = build()
    cmd.enable_backup(["1", "99-99"])
    assert "Invalid backup window" in capsys.readouterr().out
    assert h.enable_calls == []


def test_enable_backup_missing_id(capsys):
    cmd, _, _ = build()
    cmd.enable_backup([])
    assert "Missing VM ID" in capsys.readouterr().out


def test_enable_backup_server_not_found(capsys):
    cmd, _, _ = build()
    cmd.enable_backup(["99"])
    assert "not found" in capsys.readouterr().out


# --- disable ---

def test_disable_backup():
    cmd, h, _ = build()
    cmd.disable_backup(["1"])
    assert h.disable_calls == [1]


def test_disable_backup_missing_id(capsys):
    cmd, _, _ = build()
    cmd.disable_backup([])
    assert "Missing VM ID" in capsys.readouterr().out


# --- delete ---

def test_delete_backup_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_backup(["20"])
    assert h.delete_calls == [20]


def test_delete_backup_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_backup(["20"])
    assert h.delete_calls == []


def test_delete_backup_missing_id(capsys):
    cmd, _, _ = build()
    cmd.delete_backup([])
    assert "Missing backup ID" in capsys.readouterr().out


def test_delete_backup_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.delete_backup(["abc"])
    assert "Invalid backup ID" in capsys.readouterr().out
