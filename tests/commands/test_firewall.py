#!/usr/bin/env python3

from commands.firewall import FirewallCommands


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
        self.firewall = {
            "id": 10,
            "name": "fw-main",
            "rules": [
                {"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0", "::/0"]},
                {"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ["0.0.0.0/0", "::/0"]},
                {"direction": "out", "protocol": "tcp", "port": "53", "destination_ips": ["0.0.0.0/0", "::/0"]},
            ],
            "applied_to": [],
            "labels": {},
        }
        self.set_rules_calls = []
        self.apply_calls = []
        self.remove_calls = []

    def get_firewall_by_id(self, firewall_id):
        if firewall_id == 10:
            return self.firewall
        return {}

    def set_firewall_rules(self, firewall_id, rules):
        self.set_rules_calls.append((firewall_id, rules))
        return True

    def apply_firewall_to_resources(self, firewall_id, resources):
        self.apply_calls.append((firewall_id, resources))
        return True

    def remove_firewall_from_resources(self, firewall_id, resources):
        self.remove_calls.append((firewall_id, resources))
        return True

    def list_servers(self):
        return [
            {"id": 1, "name": "app-1", "status": "running"},
            {"id": 2, "name": "app-2", "status": "off"},
        ]


def build_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return FirewallCommands(console), hetzner


def test_parse_ip_list_validation():
    commands, _ = build_commands()
    assert commands._parse_ip_list("10.0.0.0/8,::/0") == ["10.0.0.0/8", "::/0"]
    assert commands._parse_ip_list("bad-cidr") == []


def test_validate_port_spec():
    commands, _ = build_commands()
    assert commands._validate_port_spec("22")
    assert commands._validate_port_spec("1000-2000")
    assert not commands._validate_port_spec("0")
    assert not commands._validate_port_spec("2000-1000")
    assert not commands._validate_port_spec("abc")


def test_apply_to_label_selector(monkeypatch):
    commands, hetzner = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.apply_to_resources(["10", "label", "env=prod"])

    assert len(hetzner.apply_calls) == 1
    firewall_id, resources = hetzner.apply_calls[0]
    assert firewall_id == 10
    assert resources == [{"type": "label_selector", "label_selector": {"selector": "env=prod"}}]


def test_apply_unknown_server_id_stops(capsys):
    commands, hetzner = build_commands()

    commands.apply_to_resources(["10", "1,3"])

    output = capsys.readouterr().out
    assert "Unknown server ID(s): 3" in output
    assert hetzner.apply_calls == []


def test_remove_rules_by_index(monkeypatch):
    commands, hetzner = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.remove_rules(["10", "2,3"])

    assert len(hetzner.set_rules_calls) == 1
    firewall_id, rules = hetzner.set_rules_calls[0]
    assert firewall_id == 10
    assert len(rules) == 1
    assert rules[0]["port"] == "22"


def test_add_rules_appends_existing(monkeypatch):
    commands, hetzner = build_commands()
    monkeypatch.setattr(commands, "_prompt_for_rules", lambda: [{"direction": "in", "protocol": "udp", "port": "53", "source_ips": ["0.0.0.0/0"]}])
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.add_rules(["10"])

    assert len(hetzner.set_rules_calls) == 1
    firewall_id, rules = hetzner.set_rules_calls[0]
    assert firewall_id == 10
    assert len(rules) == 4
    assert rules[-1]["protocol"] == "udp"
