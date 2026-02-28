#!/usr/bin/env python3

from commands.volume import VolumeCommands


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
        self.volume = {
            "id": 5,
            "name": "data-vol",
            "size": 50,
            "status": "available",
            "server": None,
            "location": {"name": "nbg1", "city": "Nuremberg", "country": "DE"},
            "format": "xfs",
            "protection": {"delete": False},
            "labels": {},
            "created": "2024-01-10T08:00:00Z",
            "linux_device": "/dev/sdb",
        }
        self.server = {"id": 42, "name": "web-01", "status": "running"}
        self.attach_calls = []
        self.detach_calls = []
        self.delete_calls = []
        self.resize_calls = []
        self.protect_calls = []

    def list_volumes(self):
        return [self.volume]

    def get_volume_by_id(self, vol_id):
        return self.volume if vol_id == 5 else None

    def get_server_by_id(self, server_id):
        return self.server if server_id == 42 else None

    def delete_volume(self, vol_id):
        self.delete_calls.append(vol_id)
        return True

    def attach_volume(self, vol_id, server_id, automount=False):
        self.attach_calls.append((vol_id, server_id, automount))
        return True

    def detach_volume(self, vol_id):
        self.detach_calls.append(vol_id)
        return True

    def resize_volume(self, vol_id, new_size):
        self.resize_calls.append((vol_id, new_size))
        return True

    def change_volume_protection(self, vol_id, delete):
        self.protect_calls.append((vol_id, delete))
        return True


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return VolumeCommands(c), h, c


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_volumes()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Name" in headers
    assert "Size" in headers
    assert title == "Volumes"
    assert rows[0][1] == "data-vol"


def test_list_empty(capsys):
    cmd, h, _ = build()

    class Empty:
        def list_volumes(self): return []
    cmd.hetzner = Empty()
    cmd.list_volumes()
    assert "No volumes" in capsys.readouterr().out


# --- info ---

def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_volume_info(["5"])
    out = capsys.readouterr().out
    assert "data-vol" in out
    assert "50" in out
    assert "Nuremberg" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_volume_info([])
    assert "Missing volume ID" in capsys.readouterr().out


def test_show_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_volume_info(["abc"])
    assert "Invalid volume ID" in capsys.readouterr().out


# --- delete ---

def test_delete_unattached_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_volume(["5"])
    assert h.delete_calls == [5]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_volume(["5"])
    assert h.delete_calls == []


def test_delete_attached_offers_detach_then_delete(monkeypatch):
    cmd, h, _ = build()
    h.volume["server"] = 42
    # first input: "y" (detach), second input: "y" (delete confirm)
    answers = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.delete_volume(["5"])
    assert h.detach_calls == [5]
    assert h.delete_calls == [5]


def test_delete_attached_cancel_detach(monkeypatch, capsys):
    cmd, h, _ = build()
    h.volume["server"] = 42
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_volume(["5"])
    out = capsys.readouterr().out
    assert "cancelled" in out
    assert h.delete_calls == []


def test_delete_missing_id(capsys):
    cmd, _, _ = build()
    cmd.delete_volume([])
    assert "Missing volume ID" in capsys.readouterr().out


# --- attach ---

def test_attach_volume(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")  # no automount
    cmd.attach_volume(["5", "42"])
    assert (5, 42, False) in h.attach_calls


def test_attach_already_attached(capsys):
    cmd, h, _ = build()
    h.volume["server"] = 42
    cmd.attach_volume(["5", "42"])
    out = capsys.readouterr().out
    assert "already attached" in out
    assert h.attach_calls == []


def test_attach_missing_args(capsys):
    cmd, _, _ = build()
    cmd.attach_volume(["5"])
    assert "Missing parameters" in capsys.readouterr().out


# --- detach ---

def test_detach_volume_confirmed(monkeypatch):
    cmd, h, _ = build()
    h.volume["server"] = 42
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.detach_volume(["5"])
    assert h.detach_calls == [5]


def test_detach_volume_cancelled(monkeypatch):
    cmd, h, _ = build()
    h.volume["server"] = 42
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.detach_volume(["5"])
    assert h.detach_calls == []


def test_detach_not_attached(capsys):
    cmd, h, _ = build()
    h.volume["server"] = None
    cmd.detach_volume(["5"])
    assert "not attached" in capsys.readouterr().out


def test_detach_missing_id(capsys):
    cmd, _, _ = build()
    cmd.detach_volume([])
    assert "Missing volume ID" in capsys.readouterr().out


# --- resize ---

def test_resize_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.resize_volume(["5", "100"])
    assert h.resize_calls == [(5, 100)]


def test_resize_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.resize_volume(["5", "100"])
    assert h.resize_calls == []


def test_resize_smaller_blocked(capsys):
    cmd, h, _ = build()
    h.volume["size"] = 50
    cmd.resize_volume(["5", "20"])
    out = capsys.readouterr().out
    assert "larger than current" in out
    assert h.resize_calls == []


def test_resize_below_minimum(capsys):
    cmd, h, _ = build()
    cmd.resize_volume(["5", "5"])
    out = capsys.readouterr().out
    assert "10 GB" in out
    assert h.resize_calls == []


def test_resize_missing_args(capsys):
    cmd, _, _ = build()
    cmd.resize_volume(["5"])
    assert "Missing parameters" in capsys.readouterr().out


# --- protect ---

def test_protect_enable(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.protect_volume(["5", "enable"])
    assert h.protect_calls == [(5, True)]


def test_protect_disable(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.protect_volume(["5", "disable"])
    assert h.protect_calls == [(5, False)]


def test_protect_invalid_action(capsys):
    cmd, h, _ = build()
    cmd.protect_volume(["5", "maybe"])
    assert "enable" in capsys.readouterr().out
    assert h.protect_calls == []


def test_protect_missing_args(capsys):
    cmd, _, _ = build()
    cmd.protect_volume(["5"])
    assert "Missing parameters" in capsys.readouterr().out
