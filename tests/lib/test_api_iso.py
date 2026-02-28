#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_isos_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"isos": [{"id": 1}]}))

    assert manager.list_isos() == [{"id": 1}]


def test_list_isos_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_isos() == []


def test_get_iso_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"iso": {"id": 7}}))
    assert manager.get_iso_by_id(7) == {"id": 7}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_iso_by_id(7) == {}


def test_attach_iso_to_server_success_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 1}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.attach_iso_to_server(42, 10) is True
    assert captured["endpoint"] == "servers/42/actions/attach_iso"
    assert captured["data"] == {"iso": 10}


def test_detach_iso_from_server_success_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 2}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.detach_iso_from_server(42) is True
