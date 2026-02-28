#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_floating_ips_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (200, {"floating_ips": [{"id": 1, "ip": "1.2.3.4"}]}))
    assert manager.list_floating_ips() == [{"id": 1, "ip": "1.2.3.4"}]


def test_list_floating_ips_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (500, {"error": {"message": "server error"}}))
    assert manager.list_floating_ips() == []


def test_get_floating_ip_by_id_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (200, {"floating_ip": {"id": 5, "ip": "5.5.5.5"}}))
    assert manager.get_floating_ip_by_id(5) == {"id": 5, "ip": "5.5.5.5"}


def test_get_floating_ip_by_id_not_found(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_floating_ip_by_id(99) == {}


def test_create_floating_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"method": m, "endpoint": e, "data": d})
        return 201, {"floating_ip": {"id": 10, "ip": "9.9.9.9"}}

    monkeypatch.setattr(manager, "_make_request", fake)
    result = manager.create_floating_ip("ipv4", "my-fip", home_location="nbg1",
                                        description="test", labels={"env": "prod"})
    assert result == {"id": 10, "ip": "9.9.9.9"}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "floating_ips"
    assert captured["data"]["type"] == "ipv4"
    assert captured["data"]["name"] == "my-fip"
    assert captured["data"]["home_location"] == "nbg1"


def test_create_floating_ip_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (422, {"error": {"message": "conflict"}}))
    assert manager.create_floating_ip("ipv4", "x") == {}


def test_update_floating_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"method": m, "endpoint": e, "data": d})
        return 200, {"floating_ip": {"id": 10, "name": "new-name"}}

    monkeypatch.setattr(manager, "_make_request", fake)
    result = manager.update_floating_ip(10, name="new-name", labels={"x": "y"})
    assert result == {"id": 10, "name": "new-name"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "floating_ips/10"
    assert captured["data"]["name"] == "new-name"


def test_delete_floating_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (204, {}))
    assert manager.delete_floating_ip(10) is True


def test_delete_floating_ip_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (403, {"error": {"message": "forbidden"}}))
    assert manager.delete_floating_ip(10) is False


def test_assign_floating_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured.update({"endpoint": e, "data": d})
        return 201, {"action": {"id": 50}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.assign_floating_ip(10, 42) is True
    assert "assign" in captured["endpoint"]
    assert captured["data"]["server"] == 42


def test_unassign_floating_ip_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request",
        lambda m, e, d=None: (201, {"action": {"id": 51}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.unassign_floating_ip(10) is True


def test_change_floating_ip_dns_ptr(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured["data"] = d
        return 201, {"action": {"id": 52}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.change_floating_ip_dns_ptr(10, "1.2.3.4", "host.example.com") is True
    assert captured["data"] == {"ip": "1.2.3.4", "dns_ptr": "host.example.com"}


def test_change_floating_ip_dns_ptr_reset(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured["data"] = d
        return 201, {"action": {"id": 53}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.change_floating_ip_dns_ptr(10, "1.2.3.4") is True
    assert captured["data"]["dns_ptr"] is None


def test_change_floating_ip_protection(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake(m, e, d=None):
        captured["data"] = d
        return 201, {"action": {"id": 54}}

    monkeypatch.setattr(manager, "_make_request", fake)
    monkeypatch.setattr(manager, "_wait_for_action", lambda *a, **kw: True)
    assert manager.change_floating_ip_protection(10, True) is True
    assert captured["data"] == {"delete": True}
