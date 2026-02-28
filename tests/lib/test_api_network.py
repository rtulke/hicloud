#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_networks_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"networks": [{"id": 1}]}))

    assert manager.list_networks() == [{"id": 1}]


def test_list_networks_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_networks() == []


def test_get_network_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"network": {"id": 10}}))
    assert manager.get_network_by_id(10) == {"id": 10}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_network_by_id(10) == {}


def test_create_network_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"network": {"id": 1, "name": "n1"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.create_network("n1", "10.0.0.0/16", subnets=[{"type": "cloud", "network_zone": "eu-central", "ip_range": "10.0.1.0/24"}], labels={"env": "dev"})
    assert result == {"id": 1, "name": "n1"}
    assert captured["endpoint"] == "networks"
    assert captured["data"]["name"] == "n1"


def test_delete_network_success_and_failure(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))
    assert manager.delete_network(1) is True

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "x"}}))
    assert manager.delete_network(1) is False


def test_update_network_success_and_no_updates(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 200, {"network": {"id": 1, "name": "new"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.update_network(1, name="new", labels={"team": "core"})
    assert result == {"id": 1, "name": "new"}
    assert captured["endpoint"] == "networks/1"

    assert manager.update_network(1) == {}


def test_attach_and_detach_server_to_network_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 77}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.attach_server_to_network(2, 10, ip="10.0.1.5", alias_ips=["10.0.1.6"]) is True
    assert manager.detach_server_from_network(2, 10) is True


def test_add_and_delete_subnet(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"network": {"id": 3}}))
    assert manager.add_subnet_to_network(3, "eu-central", "10.0.2.0/24") == {"id": 3}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {}))
    assert manager.delete_subnet_from_network(3, "10.0.2.0/24") is True


def test_change_network_protection(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"network": {"id": 3}}))
    assert manager.change_network_protection(3, delete=True) == {"id": 3}

    assert manager.change_network_protection(3) == {}
