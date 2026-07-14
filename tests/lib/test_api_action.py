#!/usr/bin/env python3

from lib.api import HetznerCloudManager


# Das globale GET /actions ist seit 2025-01-30 entfernt (410 Gone);
# list_actions aggregiert deshalb ueber die Ressourcen-Action-Endpoints.

def test_list_actions_aggregates_resource_endpoints(monkeypatch):
    manager = HetznerCloudManager("token")
    calls = []

    def fake_request(method, endpoint, data=None):
        calls.append(endpoint)
        if endpoint.startswith("servers/actions"):
            return 200, {"actions": [{"id": 1, "command": "start_server"}]}
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 1, "command": "start_server"}]
    assert "servers/actions" in calls
    assert "floating_ips/actions" in calls
    assert "actions" not in calls  # der entfernte Global-Endpoint darf nicht mehr aufgerufen werden


def test_list_actions_with_status_filter(monkeypatch):
    manager = HetznerCloudManager("token")
    calls = []

    def fake_request(method, endpoint, data=None):
        calls.append(endpoint)
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    manager.list_actions("running")
    assert calls
    assert all(endpoint.endswith("?status=running") for endpoint in calls)


def test_list_actions_deduplicates_across_sources(monkeypatch):
    manager = HetznerCloudManager("token")

    def fake_request(method, endpoint, data=None):
        # Dieselbe Action taucht bei zwei Ressourcen auf
        if endpoint.startswith(("servers/actions", "volumes/actions")):
            return 200, {"actions": [{"id": 42, "command": "attach_volume"}]}
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 42, "command": "attach_volume"}]


def test_list_actions_follows_pagination_per_source(monkeypatch):
    manager = HetznerCloudManager("token")

    def fake_request(method, endpoint, data=None):
        if endpoint.startswith("servers/actions"):
            if "page=2" in endpoint:
                return 200, {"actions": [{"id": 2}], "meta": {"pagination": {"next_page": None}}}
            return 200, {"actions": [{"id": 1}], "meta": {"pagination": {"next_page": 2}}}
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 1}, {"id": 2}]


def test_list_actions_reports_failed_sources(monkeypatch, capsys):
    manager = HetznerCloudManager("token")

    def fake_request(method, endpoint, data=None):
        if endpoint.startswith("servers/actions"):
            return 500, {"error": {"message": "boom"}}
        if endpoint.startswith("volumes/actions"):
            return 200, {"actions": [{"id": 3}]}
        return 200, {"actions": []}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_actions() == [{"id": 3}]
    assert "could not list actions for: servers" in capsys.readouterr().out


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
