#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_snapshots_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"images": [{"id": 1}, {"id": 2}]}),
    )

    assert manager.list_snapshots() == [{"id": 1}, {"id": 2}]


def test_list_snapshots_filtered(monkeypatch):
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

    assert manager.list_snapshots(server_id=20) == [{"id": 2, "created_from": {"id": 20}}]


def test_list_snapshots_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_snapshots() == []


def test_create_snapshot_returns_newest(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 91}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)
    monkeypatch.setattr(
        manager,
        "list_snapshots",
        lambda server_id=None: [
            {"id": 100, "created": "2024-01-01T10:00:00+00:00"},
            {"id": 101, "created": "2024-01-02T10:00:00+00:00"},
        ],
    )

    result = manager.create_snapshot(10, "snap")
    assert result == {"id": 101, "created": "2024-01-02T10:00:00+00:00"}


def test_create_snapshot_failure_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (400, {"error": {"message": "bad"}}))

    assert manager.create_snapshot(10) == {}


def test_delete_snapshot_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_snapshot(1) is True


def test_delete_snapshot_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "forbidden"}}))

    assert manager.delete_snapshot(1) is False


def test_rebuild_server_from_snapshot_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 55}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: action_id == 55)

    assert manager.rebuild_server_from_snapshot(11, 99) is True
    assert captured["endpoint"] == "servers/11/actions/rebuild"
    assert captured["data"] == {"image": "99"}


def test_rebuild_server_from_snapshot_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "x"}}))

    assert manager.rebuild_server_from_snapshot(11, 99) is False
