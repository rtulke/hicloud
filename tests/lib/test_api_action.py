#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_actions_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 200, {"actions": [{"id": 1, "command": "create_server"}]}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 1, "command": "create_server"}]
    assert captured["endpoint"] == "actions"


def test_list_actions_with_status_filter(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    manager.list_actions("running")
    assert captured["endpoint"] == "actions?status=running"


def test_list_actions_follows_pagination(monkeypatch):
    manager = HetznerCloudManager("token")

    def fake_request(method, endpoint, data=None):
        if "page=2" in endpoint:
            return 200, {"actions": [{"id": 2}], "meta": {"pagination": {"next_page": None}}}
        return 200, {"actions": [{"id": 1}], "meta": {"pagination": {"next_page": 2}}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 1}, {"id": 2}]


def test_list_actions_error_returns_empty(monkeypatch, capsys):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (500, {"error": {"message": "boom"}}),
    )

    assert manager.list_actions() == []
    assert "Error listing actions: boom" in capsys.readouterr().out


def test_get_action_by_id_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"action": {"id": 9, "status": "success"}}),
    )

    assert manager.get_action_by_id(9) == {"id": 9, "status": "success"}


def test_get_action_by_id_not_found(monkeypatch, capsys):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.get_action_by_id(9) == {}
    assert "Action with ID 9 not found" in capsys.readouterr().out
