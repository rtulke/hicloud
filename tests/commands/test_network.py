#!/usr/bin/env python3

from commands.network import NetworkCommands


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
        self.network = {
            "id": 10,
            "name": "private-net",
            "ip_range": "10.0.0.0/16",
            "subnets": [{"network_zone": "eu-central", "ip_range": "10.0.1.0/24", "gateway": "10.0.1.1", "type": "cloud"}],
            "routes": [],
            "servers": [],
            "labels": {},
            "protection": {"delete": False},
            "created": "2024-01-01T00:00:00Z",
        }
        self.server = {"id": 42, "name": "web-01", "status": "running", "private_net": []}
        self.attach_calls = []
        self.detach_calls = []
        self.delete_calls = []
        self.update_calls = []
        self.protect_calls = []

    def list_networks(self):
        return [self.network]

    def get_network_by_id(self, net_id):
        return self.network if net_id == 10 else None

    def get_server_by_id(self, server_id):
        return self.server if server_id == 42 else None

    def delete_network(self, net_id):
        self.delete_calls.append(net_id)
        return True

    def attach_server_to_network(self, net_id, server_id, ip=None):
        self.attach_calls.append((net_id, server_id, ip))
        return True

    def detach_server_from_network(self, net_id, server_id):
        self.detach_calls.append((net_id, server_id))
        return True

    def update_network(self, network_id, name=None, labels=None):
        self.update_calls.append((network_id, name, labels))
        return {"id": network_id, "name": name or self.network["name"], "labels": labels or {}}

    def change_network_protection(self, net_id, delete):
        self.protect_calls.append((net_id, delete))
        return True

    def list_locations(self):
        return [{"name": "nbg1", "network_zone": "eu-central"}]


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return NetworkCommands(c), h, c


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_networks()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Name" in headers
    assert "IP Range" in headers
    assert title == "Networks"
    assert rows[0][1] == "private-net"
    assert rows[0][2] == "10.0.0.0/16"


def test_list_empty(capsys):
    cmd, h, _ = build()

    class Empty:
        def list_networks(self): return []
    cmd.hetzner = Empty()
    cmd.list_networks()
    assert "No networks" in capsys.readouterr().out


# --- info ---

def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_network_info(["10"])
    out = capsys.readouterr().out
    assert "private-net" in out
    assert "10.0.0.0/16" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_network_info([])
    assert "Missing network ID" in capsys.readouterr().out


def test_show_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_network_info(["abc"])
    assert "Invalid network ID" in capsys.readouterr().out


# --- delete ---

def test_delete_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_network(["10"])
    assert h.delete_calls == [10]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_network(["10"])
    assert h.delete_calls == []


def test_delete_blocked_if_servers_attached(capsys):
    cmd, h, _ = build()
    h.network["servers"] = [42]
    cmd.delete_network(["10"])
    out = capsys.readouterr().out
    assert "must detach" in out.lower() or "detach" in out.lower()
    assert h.delete_calls == []


def test_delete_missing_id(capsys):
    cmd, _, _ = build()
    cmd.delete_network([])
    assert "Missing network ID" in capsys.readouterr().out


# --- attach ---

def test_attach_server():
    cmd, h, _ = build()
    cmd.attach_server(["10", "42"])
    assert h.attach_calls == [(10, 42, None)]


def test_attach_server_with_ip():
    cmd, h, _ = build()
    cmd.attach_server(["10", "42", "10.0.1.5"])
    assert h.attach_calls == [(10, 42, "10.0.1.5")]


def test_attach_already_attached(capsys):
    cmd, h, _ = build()
    h.network["servers"] = [42]
    cmd.attach_server(["10", "42"])
    out = capsys.readouterr().out
    assert "already attached" in out
    assert h.attach_calls == []


def test_attach_missing_args(capsys):
    cmd, _, _ = build()
    cmd.attach_server(["10"])
    assert "Missing parameters" in capsys.readouterr().out


# --- detach ---

def test_detach_server(monkeypatch):
    cmd, h, _ = build()
    h.network["servers"] = [42]
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.detach_server(["10", "42"])
    assert h.detach_calls == [(10, 42)]


def test_detach_missing_args(capsys):
    cmd, _, _ = build()
    cmd.detach_server(["10"])
    assert "Missing parameters" in capsys.readouterr().out


# --- protect ---

def test_protect_enable(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.protect_network(["10", "enable"])
    assert h.protect_calls == [(10, True)]


def test_protect_disable(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.protect_network(["10", "disable"])
    assert h.protect_calls == [(10, False)]


def test_protect_invalid_action(capsys):
    cmd, h, _ = build()
    cmd.protect_network(["10", "maybe"])
    assert "enable" in capsys.readouterr().out.lower()
    assert h.protect_calls == []


# --- unknown subcommand ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing network subcommand" in capsys.readouterr().out
