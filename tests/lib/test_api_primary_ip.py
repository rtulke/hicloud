#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_primary_ips_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (200, {"primary_ips": [{"id": 1, "ip": "10.0.0.1"}]}))
    assert manager.list_primary_ips() == [{"id": 1, "ip": "10.0.0.1"}]


def test_list_primary_ips_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (500, {"error": {"message": "error"}}))
    assert manager.list_primary_ips() == []


def test_get_primary_ip_by_id_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (200, {"primary_ip": {"id": 7, "ip": "10.0.0.7"}}))
    assert manager.get_primary_ip_by_id(7) == {"id": 7, "ip": "10.0.0.7"}


def test_get_primary_ip_by_id_not_found(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_primary_ip_by_id(99) == {}


def test_create_primary_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"method": m, "endpoint": e, "data": d})
        return 201, {"primary_ip": {"id": 20, "ip": "10.0.1.1"}}

    monkeypatch.setattr(manager, "_make_request", fake)
    result = manager.create_primary_ip("ipv4", "my-pip", datacenter="nbg1-dc3",
                                       auto_delete=True, labels={"k": "v"})
    assert result == {"id": 20, "ip": "10.0.1.1"}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "primary_ips"
    assert captured["data"]["type"] == "ipv4"
    assert captured["data"]["name"] == "my-pip"
    assert captured["data"]["datacenter"] == "nbg1-dc3"
    assert captured["data"]["auto_delete"] is True
    assert captured["data"]["assignee_type"] == "server"


def test_create_primary_ip_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (422, {"error": {"message": "conflict"}}))
    assert manager.create_primary_ip("ipv4", "x") == {}


def test_update_primary_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"method": m, "endpoint": e, "data": d})
        return 200, {"primary_ip": {"id": 20, "name": "renamed"}}

    monkeypatch.setattr(manager, "_make_request", fake)
    result = manager.update_primary_ip(20, name="renamed", auto_delete=False)
    assert result == {"id": 20, "name": "renamed"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "primary_ips/20"
    assert captured["data"]["name"] == "renamed"
    assert captured["data"]["auto_delete"] is False


def test_delete_primary_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (204, {}))
    assert manager.delete_primary_ip(20) is True


def test_delete_primary_ip_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (409, {"error": {"message": "still assigned"}}))
    assert manager.delete_primary_ip(20) is False


def test_assign_primary_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"endpoint": e, "data": d})
        return 201, {"action": {"id": 60}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.assign_primary_ip(20, 42) is True
    assert "assign" in captured["endpoint"]
    assert captured["data"]["assignee_id"] == 42
    assert captured["data"]["assignee_type"] == "server"


def test_unassign_primary_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (201, {"action": {"id": 61}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.unassign_primary_ip(20) is True


def test_change_primary_ip_dns_ptr(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured["data"] = d
        return 201, {"action": {"id": 62}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.change_primary_ip_dns_ptr(20, "10.0.0.1", "host.example.com") is True
    assert captured["data"] == {"ip": "10.0.0.1", "dns_ptr": "host.example.com"}


def test_change_primary_ip_protection(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured["data"] = d
        return 201, {"action": {"id": 63}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.change_primary_ip_protection(20, False) is True
    assert captured["data"] == {"delete": False}
