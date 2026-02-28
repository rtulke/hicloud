#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_backups_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"images": [{"id": 1}, {"id": 2}]}),
    )

    assert manager.list_backups() == [{"id": 1}, {"id": 2}]


def test_list_backups_filtered_by_server_id(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (
            200,
            {
                "images": [
                    {"id": 1, "created_from": {"id": 10}},
                    {"id": 2, "created_from": {"id": 20}},
                ]
            },
        ),
    )

    assert manager.list_backups(server_id=10) == [{"id": 1, "created_from": {"id": 10}}]


def test_list_backups_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_backups() == []


def test_delete_backup_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_backup(123) is True


def test_delete_backup_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "forbidden"}}))

    assert manager.delete_backup(123) is False


def test_enable_server_backups_with_window_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 77}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: action_id == 77)

    assert manager.enable_server_backups(10, "22-02") is True
    assert captured["endpoint"] == "servers/10/actions/enable_backup"
    assert captured["data"] == {"backup_window": "22-02"}


def test_enable_server_backups_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "invalid"}}))

    assert manager.enable_server_backups(10) is False


def test_disable_server_backups_waits(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 88}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: action_id == 88)

    assert manager.disable_server_backups(10) is True


def test_disable_server_backups_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.disable_server_backups(10) is False
