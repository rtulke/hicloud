#!/usr/bin/env python3

from commands.loadbalancer import LoadBalancerCommands


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
        self.load_balancer = {
            "id": 10,
            "name": "lb-main",
            "load_balancer_type": {"name": "lb11"},
            "location": {"name": "nbg1"},
            "network_zone": "eu-central",
            "algorithm": {"type": "round_robin"},
            "public_net": {"ipv4": {"ip": "1.2.3.4"}, "ipv6": {"ip": "2001:db8::/64"}},
            "targets": [{"type": "server", "server": {"id": 1}, "use_private_ip": False}],
            "services": [{"protocol": "tcp", "listen_port": 80, "destination_port": 8080}],
            "labels": {},
        }
        self.created_calls = []
        self.add_target_calls = []
        self.remove_target_calls = []
        self.delete_calls = []
        self.add_service_calls = []
        self.delete_service_calls = []
        self.update_service_calls = []
        self.algorithm_calls = []

    def list_load_balancers(self):
        return [self.load_balancer]

    def get_load_balancer_by_id(self, lb_id):
        if lb_id == 10:
            return self.load_balancer
        return {}

    def list_load_balancer_types(self):
        return [{"name": "lb11"}, {"name": "lb21"}]

    def list_locations(self):
        return [{"name": "nbg1", "description": "Nuremberg"}, {"name": "hel1", "description": "Helsinki"}]

    def create_load_balancer(self, **kwargs):
        self.created_calls.append(kwargs)
        return {"id": 11, "name": kwargs.get("name"), "location": {"name": kwargs.get("location")}}

    def add_load_balancer_target(self, lb_id, target):
        self.add_target_calls.append((lb_id, target))
        return True

    def remove_load_balancer_target(self, lb_id, target):
        self.remove_target_calls.append((lb_id, target))
        return True

    def delete_load_balancer(self, lb_id):
        self.delete_calls.append(lb_id)
        return True

    def add_lb_service(self, lb_id, service):
        self.add_service_calls.append((lb_id, service))
        return True

    def delete_lb_service(self, lb_id, listen_port):
        self.delete_service_calls.append((lb_id, listen_port))
        return True

    def update_lb_service(self, lb_id, service):
        self.update_service_calls.append((lb_id, service))
        return True

    def change_lb_algorithm(self, lb_id, algorithm):
        self.algorithm_calls.append((lb_id, algorithm))
        return True

    def get_server_by_id(self, server_id):
        if server_id in {1, 2}:
            return {"id": server_id, "name": f"srv-{server_id}"}
        return {}


def build_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return LoadBalancerCommands(console), hetzner, console


def test_list_load_balancers_writes_table():
    commands, _, console = build_commands()
    commands.list_load_balancers()

    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Type" in headers
    assert rows[0][0] == 10
    assert title == "Load Balancers"


def test_create_load_balancer_interactive(monkeypatch):
    commands, hetzner, _ = build_commands()
    answers = iter(["lb-new", "1", "1", "", "n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.create_load_balancer()

    assert len(hetzner.created_calls) == 1
    payload = hetzner.created_calls[0]
    assert payload["name"] == "lb-new"
    assert payload["load_balancer_type"] == "lb11"
    assert payload["location"] == "nbg1"
    assert payload["public_interface"] is True


def test_targets_add_label(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.manage_targets(["10", "add", "label", "env=prod"])

    assert len(hetzner.add_target_calls) == 1
    lb_id, target = hetzner.add_target_calls[0]
    assert lb_id == 10
    assert target == {"type": "label_selector", "label_selector": {"selector": "env=prod"}}


def test_targets_add_server_missing_rejected():
    commands, hetzner, _ = build_commands()

    commands.manage_targets(["10", "add", "server", "99"])

    assert hetzner.add_target_calls == []


def test_targets_remove_server(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.manage_targets(["10", "remove", "server", "1"])

    assert len(hetzner.remove_target_calls) == 1
    lb_id, target = hetzner.remove_target_calls[0]
    assert lb_id == 10
    assert target == {"type": "server", "server": {"id": 1}}


def test_delete_load_balancer(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.delete_load_balancer(["10"])

    assert hetzner.delete_calls == [10]


def test_service_list_shows_services(capsys):
    commands, _, _ = build_commands()
    commands.manage_services(["10", "list"])

    output = capsys.readouterr().out
    assert "tcp" in output
    assert "80" in output


def test_service_add_wizard(monkeypatch):
    commands, hetzner, _ = build_commands()
    # protocol=tcp, listen_port=443, dest_port=4430, health check: y then defaults, no sticky
    answers = iter(["tcp", "443", "4430", "y", "tcp", "", "15", "10", "3", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.manage_services(["10", "add"])

    assert len(hetzner.add_service_calls) == 1
    lb_id, service = hetzner.add_service_calls[0]
    assert lb_id == 10
    assert service["protocol"] == "tcp"
    assert service["listen_port"] == 443
    assert service["destination_port"] == 4430
    assert "health_check" in service


def test_service_add_cancelled(monkeypatch):
    commands, hetzner, _ = build_commands()
    # protocol, listen, dest, skip health check, cancel confirm
    answers = iter(["tcp", "443", "4430", "n", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.manage_services(["10", "add"])

    assert hetzner.add_service_calls == []


def test_service_delete(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.manage_services(["10", "delete", "80"])

    assert hetzner.delete_service_calls == [(10, 80)]


def test_service_delete_cancelled(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "n")

    commands.manage_services(["10", "delete", "80"])

    assert hetzner.delete_service_calls == []


def test_service_update_wizard(monkeypatch):
    commands, hetzner, _ = build_commands()
    # keep protocol, keep dest_port, skip health check update, confirm
    answers = iter(["", "", "n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.manage_services(["10", "update", "80"])

    assert len(hetzner.update_service_calls) == 1
    lb_id, service = hetzner.update_service_calls[0]
    assert lb_id == 10
    assert service["listen_port"] == 80


def test_service_update_nonexistent_port(capsys):
    commands, hetzner, _ = build_commands()

    commands.manage_services(["10", "update", "9999"])

    output = capsys.readouterr().out
    assert "No service found" in output
    assert hetzner.update_service_calls == []


def test_algorithm_change(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.change_algorithm(["10", "least_connections"])

    assert hetzner.algorithm_calls == [(10, "least_connections")]


def test_algorithm_invalid_rejected(capsys):
    commands, hetzner, _ = build_commands()

    commands.change_algorithm(["10", "bad_algo"])

    output = capsys.readouterr().out
    assert "Invalid algorithm" in output
    assert hetzner.algorithm_calls == []


def test_algorithm_already_set(capsys):
    commands, hetzner, _ = build_commands()

    # lb already uses round_robin (from DummyHetzner fixture)
    commands.change_algorithm(["10", "round_robin"])

    output = capsys.readouterr().out
    assert "already uses" in output
    assert hetzner.algorithm_calls == []
