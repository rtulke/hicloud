#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_placement_groups_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 200, {"placement_groups": [{"id": 1, "name": "pg"}]}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_placement_groups() == [{"id": 1, "name": "pg"}]
    assert captured["endpoint"] == "placement_groups"


def test_list_placement_groups_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}),
    )

    assert manager.list_placement_groups() == []


def test_get_placement_group_by_id_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"placement_group": {"id": 5}}),
    )

    assert manager.get_placement_group_by_id(5) == {"id": 5}


def test_get_placement_group_by_id_not_found(monkeypatch, capsys):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.get_placement_group_by_id(5) == {}
    assert "Placement group with ID 5 not found" in capsys.readouterr().out


def test_create_placement_group_payload(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"placement_group": {"id": 6, "name": "pg-new"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.create_placement_group("pg-new", labels={"env": "prod"})
    assert result == {"id": 6, "name": "pg-new"}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "placement_groups"
    assert captured["data"] == {"name": "pg-new", "type": "spread", "labels": {"env": "prod"}}


def test_create_placement_group_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (422, {"error": {"message": "invalid"}}),
    )

    assert manager.create_placement_group("pg") == {}


def test_update_placement_group_requires_changes(monkeypatch, capsys):
    manager = HetznerCloudManager("token")
    calls = []
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: calls.append(endpoint) or (200, {}),
    )

    assert manager.update_placement_group(5) == {}
    assert "No updates provided" in capsys.readouterr().out
    assert calls == []


def test_delete_placement_group(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_placement_group(5) is True


def test_add_server_waits_for_action(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 3}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.add_server_to_placement_group(7, 5) is True
    assert captured["endpoint"] == "servers/7/actions/add_to_placement_group"
    assert captured["data"] == {"placement_group": 5}


def test_remove_server_waits_for_action(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 201, {"action": {"id": 4}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.remove_server_from_placement_group(7) is True
    assert captured["endpoint"] == "servers/7/actions/remove_from_placement_group"
