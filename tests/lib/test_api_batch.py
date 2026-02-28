#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_batch_related_get_server_by_id(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"server": {"id": 1}}))

    assert manager.get_server_by_id(1) == {"id": 1}


def test_batch_related_start_stop_server(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 11}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.start_server(1) is True
    assert manager.stop_server(1) is True


def test_batch_related_delete_server(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_server(1) is True


def test_batch_related_create_snapshot(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 22}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)
    monkeypatch.setattr(manager, "list_snapshots", lambda server_id=None: [{"id": 9, "created": "2026-02-28T01:00:00+00:00"}])

    assert manager.create_snapshot(1) == {"id": 9, "created": "2026-02-28T01:00:00+00:00"}
