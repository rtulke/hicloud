#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_volumes_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"volumes": [{"id": 1}]}))

    assert manager.list_volumes() == [{"id": 1}]


def test_list_volumes_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_volumes() == []


def test_get_volume_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"volume": {"id": 10}}))
    assert manager.get_volume_by_id(10) == {"id": 10}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_volume_by_id(10) == {}


def test_create_volume_success_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 1}, "volume": {"id": 10}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    result = manager.create_volume("vol", 20, location="nbg1", server_id=5, format_volume="ext4", labels={"env": "dev"})
    assert result == {"id": 10}
    assert captured["endpoint"] == "volumes"
    assert captured["data"]["name"] == "vol"
    assert captured["data"]["size"] == 20
    assert captured["data"]["location"] == "nbg1"
    assert captured["data"]["server"] == 5
    assert captured["data"]["format"] == "ext4"
    assert captured["data"]["labels"] == {"env": "dev"}


def test_create_volume_failure_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "bad"}}))

    assert manager.create_volume("vol", 20) == {}


def test_delete_volume_success_and_failure(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))
    assert manager.delete_volume(1) is True

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "x"}}))
    assert manager.delete_volume(1) is False


def test_attach_volume_success_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 2}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.attach_volume(1, 2, automount=True) is True
    assert captured["endpoint"] == "volumes/1/actions/attach"
    assert captured["data"] == {"server": 2, "automount": True}


def test_detach_resize_protection_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 3}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.detach_volume(1) is True
    assert manager.resize_volume(1, 50) is True
    assert manager.change_volume_protection(1, delete=True) is True
