#!/usr/bin/env python3

from commands.primary_ip import PrimaryIPCommands


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
        self.pip = {
            "id": 20,
            "name": "my-pip",
            "ip": "10.0.0.1",
            "type": "ipv4",
            "datacenter": {"name": "nbg1-dc3", "location": {"name": "nbg1"}},
            "assignee_id": None,
            "assignee_type": "server",
            "auto_delete": False,
            "protection": {"delete": False},
            "blocked": False,
            "created": "2024-01-01T00:00:00Z",
            "dns_ptr": [],
            "labels": {},
        }
        self.datacenters = [{"name": "nbg1-dc3", "location": {"name": "nbg1"}}]
        self.assign_calls = []
        self.unassign_calls = []
        self.delete_calls = []
        self.update_calls = []
        self.dns_calls = []
        self.protect_calls = []
        self.create_calls = []

    def list_primary_ips(self):
        return [self.pip]

    def get_primary_ip_by_id(self, pip_id):
        return self.pip if pip_id == 20 else {}

    def create_primary_ip(self, **kwargs):
        self.create_calls.append(kwargs)
        return {"id": 21, "ip": "10.0.0.2"}

    def update_primary_ip(self, pip_id, **kwargs):
        self.update_calls.append((pip_id, kwargs))
        return {"id": pip_id}

    def delete_primary_ip(self, pip_id):
        self.delete_calls.append(pip_id)
        return True

    def assign_primary_ip(self, pip_id, server_id):
        self.assign_calls.append((pip_id, server_id))
        return True

    def unassign_primary_ip(self, pip_id):
        self.unassign_calls.append(pip_id)
        return True

    def change_primary_ip_dns_ptr(self, pip_id, ip, dns_ptr=None):
        self.dns_calls.append((pip_id, ip, dns_ptr))
        return True

    def change_primary_ip_protection(self, pip_id, delete):
        self.protect_calls.append((pip_id, delete))
        return True

    def list_datacenters(self):
        return self.datacenters


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return PrimaryIPCommands(c), h, c


def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_primary_ips()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "IP" in headers
    assert rows[0][2] == "10.0.0.1"
    assert title == "Primary IPs"


def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_info(["20"])
    out = capsys.readouterr().out
    assert "my-pip" in out
    assert "10.0.0.1" in out
    assert "nbg1-dc3" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_info([])
    assert "Missing ID" in capsys.readouterr().out


def test_assign(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.assign_primary_ip(["20", "42"])
    assert h.assign_calls == [(20, 42)]


def test_assign_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.assign_primary_ip(["20", "42"])
    assert h.assign_calls == []


def test_unassign_when_assigned(monkeypatch):
    cmd, h, _ = build()
    h.pip["assignee_id"] = 42
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.unassign_primary_ip(["20"])
    assert h.unassign_calls == [20]


def test_unassign_when_not_assigned(capsys):
    cmd, h, _ = build()
    h.pip["assignee_id"] = None
    cmd.unassign_primary_ip(["20"])
    assert "not assigned" in capsys.readouterr().out
    assert h.unassign_calls == []


def test_delete_unassigned(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_primary_ip(["20"])
    assert h.delete_calls == [20]


def test_delete_blocks_if_assigned(capsys):
    cmd, h, _ = build()
    h.pip["assignee_id"] = 99
    cmd.delete_primary_ip(["20"])
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "Unassign" in out
    assert h.delete_calls == []


def test_delete_blocks_if_protected(capsys):
    cmd, h, _ = build()
    h.pip["protection"] = {"delete": True}
    cmd.delete_primary_ip(["20"])
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert h.delete_calls == []


def test_delete_warns_auto_delete_disabled(monkeypatch, capsys):
    cmd, h, _ = build()
    h.pip["auto_delete"] = False
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_primary_ip(["20"])
    out = capsys.readouterr().out
    assert "auto_delete" in out
    assert h.delete_calls == [20]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_primary_ip(["20"])
    assert h.delete_calls == []


def test_dns_set(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.change_dns_ptr(["20", "10.0.0.1", "host.example.com"])
    assert h.dns_calls == [(20, "10.0.0.1", "host.example.com")]


def test_dns_reset(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.change_dns_ptr(["20", "10.0.0.1", "reset"])
    assert h.dns_calls == [(20, "10.0.0.1", None)]


def test_protect_enable():
    cmd, h, _ = build()
    cmd.change_protection(["20", "enable"])
    assert h.protect_calls == [(20, True)]


def test_protect_disable():
    cmd, h, _ = build()
    cmd.change_protection(["20", "disable"])
    assert h.protect_calls == [(20, False)]


def test_update(monkeypatch):
    cmd, h, _ = build()
    answers = iter(["new-name", "yes", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.update_primary_ip(["20"])
    assert len(h.update_calls) == 1
    pip_id, kwargs = h.update_calls[0]
    assert pip_id == 20
    assert kwargs["name"] == "new-name"
    assert kwargs["auto_delete"] is True


def test_update_no_changes(monkeypatch, capsys):
    cmd, h, _ = build()
    answers = iter(["", "", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.update_primary_ip(["20"])
    assert "No changes" in capsys.readouterr().out
    assert h.update_calls == []


def test_create_wizard(monkeypatch):
    cmd, h, _ = build()
    # type, name, no server → datacenter 1, no auto_delete, no labels, confirm
    answers = iter(["ipv4", "pip-new", "", "1", "n", "n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.create_primary_ip()
    assert len(h.create_calls) == 1
    assert h.create_calls[0]["ip_type"] == "ipv4"
    assert h.create_calls[0]["name"] == "pip-new"
    assert h.create_calls[0]["datacenter"] == "nbg1-dc3"
    assert h.create_calls[0]["auto_delete"] is False
