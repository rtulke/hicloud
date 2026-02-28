#!/usr/bin/env python3

from commands.vm import VMCommands


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
        self.server = {
            "id": 1,
            "name": "web-01",
            "status": "running",
            "server_type": {"id": 1, "name": "cx22", "cores": 2, "memory": 4, "disk": 40},
            "public_net": {
                "ipv4": {"ip": "1.2.3.4"},
                "ipv6": {"ip": "2001:db8::1"},
                "dns_ptr": [],
            },
            "datacenter": {
                "name": "nbg1-dc3",
                "location": {"name": "nbg1", "city": "Nuremberg", "country": "DE"},
            },
            "image": {"name": "ubuntu-22.04", "description": "Ubuntu 22.04"},
            "backup_window": None,
            "protection": {"delete": False, "rebuild": False},
            "created": "2024-01-15T10:00:00+00:00",
            "ssh_keys": [],
        }
        self.start_calls = []
        self.stop_calls = []
        self.reboot_calls = []
        self.delete_calls = []
        self.rename_calls = []
        self.resize_calls = []

    def list_servers(self):
        return [self.server]

    def get_server_by_id(self, server_id):
        return self.server if server_id == 1 else None

    def start_server(self, server_id):
        self.start_calls.append(server_id)
        return True

    def stop_server(self, server_id):
        self.stop_calls.append(server_id)
        return True

    def reboot_server(self, server_id):
        self.reboot_calls.append(server_id)
        return True

    def delete_server(self, server_id):
        self.delete_calls.append(server_id)
        return True

    def rename_server(self, server_id, new_name):
        self.rename_calls.append((server_id, new_name))
        return True

    def resize_server(self, server_id, new_type):
        self.resize_calls.append((server_id, new_type))
        return True

    def _make_request(self, method, path, data=None):
        # Return empty pricing/volumes so show_vm_info doesn't crash
        if "pricing" in path:
            return 200, {"pricing": {"server_types": []}}
        if "volumes" in path:
            return 200, {"volumes": []}
        return 404, {}


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return VMCommands(c), h, c


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_vms()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Server Name" in headers
    assert "IP" in headers
    assert title == "Virtual Machines"
    assert rows[0][1] == "web-01"
    assert rows[0][4] == "1.2.3.4"


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.server = None

    class EmptyHetzner:
        def list_servers(self): return []
    cmd.hetzner = EmptyHetzner()
    cmd.list_vms()
    assert "No VMs" in capsys.readouterr().out


# --- info ---

def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_vm_info(["1"])
    out = capsys.readouterr().out
    assert "web-01" in out
    assert "1.2.3.4" in out
    assert "Nuremberg" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_vm_info([])
    assert "Missing VM ID" in capsys.readouterr().out


def test_show_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_vm_info(["abc"])
    assert "Invalid VM ID" in capsys.readouterr().out


# --- start ---

def test_start_vm(monkeypatch):
    cmd, h, _ = build()
    h.server["status"] = "off"
    cmd.start_vm(["1"])
    assert h.start_calls == [1]


def test_start_already_running(capsys):
    cmd, h, _ = build()
    h.server["status"] = "running"
    cmd.start_vm(["1"])
    assert "already running" in capsys.readouterr().out
    assert h.start_calls == []


def test_start_missing_id(capsys):
    cmd, _, _ = build()
    cmd.start_vm([])
    assert "Missing VM ID" in capsys.readouterr().out


# --- stop ---

def test_stop_vm():
    cmd, h, _ = build()
    h.server["status"] = "running"
    cmd.stop_vm(["1"])
    assert h.stop_calls == [1]


def test_stop_already_off(capsys):
    cmd, h, _ = build()
    h.server["status"] = "off"
    cmd.stop_vm(["1"])
    assert "already stopped" in capsys.readouterr().out
    assert h.stop_calls == []


def test_stop_missing_id(capsys):
    cmd, _, _ = build()
    cmd.stop_vm([])
    assert "Missing VM ID" in capsys.readouterr().out


# --- reboot ---

def test_reboot_vm():
    cmd, h, _ = build()
    h.server["status"] = "running"
    cmd.reboot_vm(["1"])
    assert h.reboot_calls == [1]


def test_reboot_blocked_if_off(capsys):
    cmd, h, _ = build()
    h.server["status"] = "off"
    cmd.reboot_vm(["1"])
    out = capsys.readouterr().out
    assert "vm start" in out
    assert h.reboot_calls == []


def test_reboot_missing_id(capsys):
    cmd, _, _ = build()
    cmd.reboot_vm([])
    assert "Missing VM ID" in capsys.readouterr().out


# --- delete ---

def test_delete_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_vm(["1"])
    assert h.delete_calls == [1]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_vm(["1"])
    assert h.delete_calls == []


def test_delete_missing_id(capsys):
    cmd, _, _ = build()
    cmd.delete_vm([])
    assert "Missing VM ID" in capsys.readouterr().out


# --- rename ---

def test_rename_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.rename_vm(["1", "new-name"])
    assert h.rename_calls == [(1, "new-name")]


def test_rename_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.rename_vm(["1", "new-name"])
    assert h.rename_calls == []


def test_rename_missing_args(capsys):
    cmd, _, _ = build()
    cmd.rename_vm(["1"])
    assert "Missing parameters" in capsys.readouterr().out


# --- unknown subcommand ---

def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown VM subcommand" in capsys.readouterr().out


def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing VM subcommand" in capsys.readouterr().out
