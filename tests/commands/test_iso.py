#!/usr/bin/env python3

from commands.iso import ISOCommands


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
        self.iso = {
            "id": 15,
            "name": "ubuntu-22.04-amd64.iso",
            "description": "Ubuntu 22.04 LTS",
            "type": "public",
            "architecture": "x86",
            "deprecated": None,
        }
        self.server = {
            "id": 42,
            "name": "web-01",
            "status": "running",
            "iso": None,
        }
        self.attach_calls = []
        self.detach_calls = []

    def list_isos(self):
        return [self.iso]

    def get_iso_by_id(self, iso_id):
        return self.iso if iso_id == 15 else None

    def get_server_by_id(self, server_id):
        return self.server if server_id == 42 else None

    def attach_iso_to_server(self, server_id, iso_id):
        self.attach_calls.append((server_id, iso_id))
        return True

    def detach_iso_from_server(self, server_id):
        self.detach_calls.append(server_id)
        return True


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return ISOCommands(c), h, c


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_isos()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Name" in headers
    assert "Type" in headers
    assert "Architecture" in headers
    assert title == "Available ISOs"
    assert rows[0][1] == "ubuntu-22.04-amd64.iso"
    assert rows[0][2] == "public"


def test_list_empty(capsys):
    cmd, h, _ = build()

    class Empty:
        def list_isos(self): return []
    cmd.hetzner = Empty()
    cmd.list_isos()
    assert "No ISOs" in capsys.readouterr().out


# --- info ---

def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.iso_info(["15"])
    out = capsys.readouterr().out
    assert "ubuntu-22.04-amd64.iso" in out
    assert "Ubuntu 22.04 LTS" in out
    assert "x86" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.iso_info([])
    assert "Missing ISO ID" in capsys.readouterr().out


def test_show_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.iso_info(["abc"])
    assert "Invalid ISO ID" in capsys.readouterr().out


# --- attach ---

def test_attach_iso(capsys):
    cmd, h, _ = build()
    cmd.attach_iso(["15", "42"])
    assert h.attach_calls == [(42, 15)]
    assert "successfully" in capsys.readouterr().out


def test_attach_missing_args(capsys):
    cmd, _, _ = build()
    cmd.attach_iso(["15"])
    assert "Missing arguments" in capsys.readouterr().out


def test_attach_invalid_ids(capsys):
    cmd, _, _ = build()
    cmd.attach_iso(["abc", "42"])
    assert "Invalid ID" in capsys.readouterr().out


def test_attach_iso_not_found(capsys):
    cmd, h, _ = build()
    cmd.attach_iso(["99", "42"])
    # get_iso_by_id returns None, method returns early
    assert h.attach_calls == []


def test_attach_server_not_found(capsys):
    cmd, h, _ = build()
    cmd.attach_iso(["15", "99"])
    assert h.attach_calls == []


# --- detach ---

def test_detach_iso(capsys):
    cmd, h, _ = build()
    h.server["iso"] = {"id": 15, "name": "ubuntu-22.04-amd64.iso"}
    cmd.detach_iso(["42"])
    assert h.detach_calls == [42]
    assert "successfully" in capsys.readouterr().out


def test_detach_no_iso_attached(capsys):
    cmd, h, _ = build()
    h.server["iso"] = None
    cmd.detach_iso(["42"])
    out = capsys.readouterr().out
    assert "No ISO" in out
    assert h.detach_calls == []


def test_detach_missing_id(capsys):
    cmd, _, _ = build()
    cmd.detach_iso([])
    assert "Missing server ID" in capsys.readouterr().out


def test_detach_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.detach_iso(["abc"])
    assert "Invalid server ID" in capsys.readouterr().out


# --- unknown subcommand ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing iso subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown iso subcommand" in capsys.readouterr().out
