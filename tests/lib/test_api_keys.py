#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_ssh_keys_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"ssh_keys": [{"id": 1}]}))

    assert manager.list_ssh_keys() == [{"id": 1}]


def test_list_ssh_keys_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_ssh_keys() == []


def test_get_ssh_key_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"ssh_key": {"id": 9}}))
    assert manager.get_ssh_key_by_id(9) == {"id": 9}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_ssh_key_by_id(9) == {}


def test_create_ssh_key_success_and_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"ssh_key": {"id": 3, "name": "k"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    assert manager.create_ssh_key("k", "ssh-ed25519 AAA", labels={"env": "dev"}) == {"id": 3, "name": "k"}
    assert captured["endpoint"] == "ssh_keys"
    assert captured["data"]["labels"] == {"env": "dev"}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "bad"}}))
    assert manager.create_ssh_key("k", "ssh-ed25519 AAA") == {}


def test_update_ssh_key_success_failure_and_no_updates(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"ssh_key": {"id": 3, "name": "new"}}))
    assert manager.update_ssh_key(3, name="new", labels={"x": "y"}) == {"id": 3, "name": "new"}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))
    assert manager.update_ssh_key(3, name="new") == {}

    assert manager.update_ssh_key(3) == {}


def test_delete_ssh_key_success_and_failure(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))
    assert manager.delete_ssh_key(3) is True

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "x"}}))
    assert manager.delete_ssh_key(3) is False
