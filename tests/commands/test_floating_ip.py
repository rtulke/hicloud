#!/usr/bin/env python3

from commands.floating_ip import FloatingIPCommands


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
        self.fip = {
            "id": 10,
            "name": "my-fip",
            "ip": "1.2.3.4",
            "type": "ipv4",
            "home_location": {"name": "nbg1"},
            "server": None,
            "description": "test fip",
            "protection": {"delete": False},
            "blocked": False,
            "created": "2024-01-01T00:00:00Z",
            "dns_ptr": [],
            "labels": {},
        }
        self.locations = [{"name": "nbg1", "city": "Nuremberg"}]
        self.assign_calls = []
        self.unassign_calls = []
        self.delete_calls = []
        self.update_calls = []
        self.dns_calls = []
        self.protect_calls = []
        self.create_calls = []

    def list_floating_ips(self):
        return [self.fip]

    def get_floating_ip_by_id(self, fip_id):
        return self.fip if fip_id == 10 else {}

    def create_floating_ip(self, **kwargs):
        self.create_calls.append(kwargs)
        return {"id": 11, "ip": "2.2.2.2"}

    def update_floating_ip(self, fip_id, **kwargs):
        self.update_calls.append((fip_id, kwargs))
        return {"id": fip_id}

    def delete_floating_ip(self, fip_id):
        self.delete_calls.append(fip_id)
        return True

    def assign_floating_ip(self, fip_id, server_id):
        self.assign_calls.append((fip_id, server_id))
        return True

    def unassign_floating_ip(self, fip_id):
        self.unassign_calls.append(fip_id)
        return True

    def change_floating_ip_dns_ptr(self, fip_id, ip, dns_ptr=None):
        self.dns_calls.append((fip_id, ip, dns_ptr))
        return True

    def change_floating_ip_protection(self, fip_id, delete):
        self.protect_calls.append((fip_id, delete))
        return True

    def list_locations(self):
        return self.locations


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return FloatingIPCommands(c), h, c


def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_floating_ips()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "IP" in headers
    assert rows[0][2] == "1.2.3.4"
    assert title == "Floating IPs"


def test_list_empty(capsys):
    cmd, h, _ = build()
    h.fip = None

    class Empty:
        def list_floating_ips(self): return []
    cmd.hetzner = Empty()
    cmd.list_floating_ips()
    assert "No floating IPs" in capsys.readouterr().out


def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_info(["10"])
    out = capsys.readouterr().out
    assert "my-fip" in out
    assert "1.2.3.4" in out
    assert "nbg1" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_info([])
    assert "Missing ID" in capsys.readouterr().out


def test_assign(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.assign_floating_ip(["10", "42"])
    assert h.assign_calls == [(10, 42)]


def test_assign_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.assign_floating_ip(["10", "42"])
    assert h.assign_calls == []


def test_assign_missing_server_id(capsys):
    cmd, h, _ = build()
    cmd.assign_floating_ip(["10"])
    assert "Usage" in capsys.readouterr().out
    assert h.assign_calls == []


def test_unassign_when_assigned(monkeypatch):
    cmd, h, _ = build()
    h.fip["server"] = 42
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.unassign_floating_ip(["10"])
    assert h.unassign_calls == [10]


def test_unassign_when_not_assigned(capsys):
    cmd, h, _ = build()
    h.fip["server"] = None
    cmd.unassign_floating_ip(["10"])
    assert "not assigned" in capsys.readouterr().out
    assert h.unassign_calls == []


def test_delete_unassigned(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_floating_ip(["10"])
    assert h.delete_calls == [10]


def test_delete_blocks_if_assigned(capsys):
    cmd, h, _ = build()
    h.fip["server"] = 99
    cmd.delete_floating_ip(["10"])
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "Unassign" in out
    assert h.delete_calls == []


def test_delete_blocks_if_protected(capsys):
    cmd, h, _ = build()
    h.fip["protection"] = {"delete": True}
    cmd.delete_floating_ip(["10"])
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "protection" in out.lower()
    assert h.delete_calls == []


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_floating_ip(["10"])
    assert h.delete_calls == []


def test_dns_set(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.change_dns_ptr(["10", "1.2.3.4", "host.example.com"])
    assert h.dns_calls == [(10, "1.2.3.4", "host.example.com")]


def test_dns_reset(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.change_dns_ptr(["10", "1.2.3.4", "reset"])
    assert h.dns_calls == [(10, "1.2.3.4", None)]


def test_dns_missing_args(capsys):
    cmd, _, _ = build()
    cmd.change_dns_ptr(["10"])
    assert "Usage" in capsys.readouterr().out


def test_protect_enable():
    cmd, h, _ = build()
    cmd.change_protection(["10", "enable"])
    assert h.protect_calls == [(10, True)]


def test_protect_disable():
    cmd, h, _ = build()
    cmd.change_protection(["10", "disable"])
    assert h.protect_calls == [(10, False)]


def test_protect_invalid_action(capsys):
    cmd, h, _ = build()
    cmd.change_protection(["10", "maybe"])
    assert "enable" in capsys.readouterr().out
    assert h.protect_calls == []


def test_update(monkeypatch):
    cmd, h, _ = build()
    answers = iter(["new-name", "new desc", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.update_floating_ip(["10"])
    assert len(h.update_calls) == 1
    fip_id, kwargs = h.update_calls[0]
    assert fip_id == 10
    assert kwargs["name"] == "new-name"


def test_update_no_changes(monkeypatch, capsys):
    cmd, h, _ = build()
    answers = iter(["", "", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.update_floating_ip(["10"])
    assert "No changes" in capsys.readouterr().out
    assert h.update_calls == []


def test_create_wizard(monkeypatch):
    cmd, h, _ = build()
    # type, name, description, no server → location 1, no labels, confirm
    answers = iter(["ipv4", "fip-new", "desc", "", "1", "n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.create_floating_ip()
    assert len(h.create_calls) == 1
    assert h.create_calls[0]["ip_type"] == "ipv4"
    assert h.create_calls[0]["name"] == "fip-new"
    assert h.create_calls[0]["home_location"] == "nbg1"
