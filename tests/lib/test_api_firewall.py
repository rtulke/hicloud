#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_firewalls_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"firewalls": [{"id": 1}]}))

    assert manager.list_firewalls() == [{"id": 1}]


def test_get_firewall_by_id_not_found(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.get_firewall_by_id(99) == {}


def test_create_firewall_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"firewall": {"id": 10, "name": "fw"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    result = manager.create_firewall(
        "fw",
        rules=[{"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0"]}],
        apply_to=[{"type": "server", "server": {"id": 1}}],
        labels={"env": "test"},
    )

    assert result == {"id": 10, "name": "fw"}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "firewalls"
    assert captured["data"]["name"] == "fw"
    assert "rules" in captured["data"]
    assert "apply_to" in captured["data"]
    assert captured["data"]["labels"] == {"env": "test"}


def test_update_firewall_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 200, {"firewall": {"id": 10, "name": "fw-new"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    result = manager.update_firewall(10, name="fw-new", labels={"team": "core"})

    assert result == {"id": 10, "name": "fw-new"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "firewalls/10"
    assert captured["data"] == {"name": "fw-new", "labels": {"team": "core"}}


def test_delete_firewall_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_firewall(10) is True


def test_set_firewall_rules_waits_for_all_actions(monkeypatch):
    manager = HetznerCloudManager("token")
    waited = []

    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"actions": [{"id": 101}, {"id": 102}]}),
    )

    def fake_wait(action_id, timeout=300, message=None):
        waited.append(action_id)
        return True

    monkeypatch.setattr(manager, "_wait_for_action", fake_wait)

    ok = manager.set_firewall_rules(10, [{"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0"]}])
    assert ok is True
    assert waited == [101, 102]


def test_apply_firewall_to_resources_waits_for_action(monkeypatch):
    manager = HetznerCloudManager("token")
    waited = []

    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 201}}),
    )

    def fake_wait(action_id, timeout=300, message=None):
        waited.append(action_id)
        return True

    monkeypatch.setattr(manager, "_wait_for_action", fake_wait)

    ok = manager.apply_firewall_to_resources(10, [{"type": "server", "server": {"id": 1}}])
    assert ok is True
    assert waited == [201]


def test_remove_firewall_from_resources_waits_for_action(monkeypatch):
    manager = HetznerCloudManager("token")
    waited = []

    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (202, {"action": {"id": 301}}),
    )

    def fake_wait(action_id, timeout=300, message=None):
        waited.append(action_id)
        return True

    monkeypatch.setattr(manager, "_wait_for_action", fake_wait)

    ok = manager.remove_firewall_from_resources(10, [{"type": "label_selector", "label_selector": {"selector": "env=prod"}}])
    assert ok is True
    assert waited == [301]
