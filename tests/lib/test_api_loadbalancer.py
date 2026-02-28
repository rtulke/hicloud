#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_load_balancer_types_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"load_balancer_types": [{"name": "lb11"}]}),
    )

    assert manager.list_load_balancer_types() == [{"name": "lb11"}]


def test_list_load_balancers_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"load_balancers": [{"id": 1}]}),
    )

    assert manager.list_load_balancers() == [{"id": 1}]


def test_get_load_balancer_by_id_not_found(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.get_load_balancer_by_id(99) == {}


def test_create_load_balancer_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"load_balancer": {"id": 10, "name": "lb-main"}, "action": {"id": 111}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    result = manager.create_load_balancer(
        name="lb-main",
        load_balancer_type="lb11",
        location="nbg1",
        labels={"env": "prod"},
        public_interface=False,
    )

    assert result == {"id": 10, "name": "lb-main"}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "load_balancers"
    assert captured["data"]["name"] == "lb-main"
    assert captured["data"]["load_balancer_type"] == "lb11"
    assert captured["data"]["location"] == "nbg1"
    assert captured["data"]["labels"] == {"env": "prod"}
    assert captured["data"]["public_interface"] is False


def test_delete_load_balancer_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_load_balancer(10) is True


def test_add_load_balancer_target_waits_for_actions(monkeypatch):
    manager = HetznerCloudManager("token")
    waited = []

    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"actions": [{"id": 21}, {"id": 22}]}),
    )

    def fake_wait(action_id, timeout=300, message=None):
        waited.append(action_id)
        return True

    monkeypatch.setattr(manager, "_wait_for_action", fake_wait)

    ok = manager.add_load_balancer_target(10, {"type": "server", "server": {"id": 1}})
    assert ok is True
    assert waited == [21, 22]


def test_remove_load_balancer_target_waits_for_action(monkeypatch):
    manager = HetznerCloudManager("token")
    waited = []

    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (202, {"action": {"id": 31}}),
    )

    def fake_wait(action_id, timeout=300, message=None):
        waited.append(action_id)
        return True

    monkeypatch.setattr(manager, "_wait_for_action", fake_wait)

    ok = manager.remove_load_balancer_target(10, {"type": "label_selector", "label_selector": {"selector": "env=prod"}})
    assert ok is True
    assert waited == [31]


def test_add_lb_service_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 50}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    service = {"protocol": "tcp", "listen_port": 80, "destination_port": 8080}
    ok = manager.add_lb_service(10, service)

    assert ok is True
    assert captured["method"] == "POST"
    assert "add_service" in captured["endpoint"]
    assert captured["data"] == service


def test_add_lb_service_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (422, {"error": {"message": "conflict"}}),
    )

    assert manager.add_lb_service(10, {"listen_port": 80}) is False


def test_delete_lb_service_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["data"] = data
        return 201, {"action": {"id": 51}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    ok = manager.delete_lb_service(10, 80)

    assert ok is True
    assert captured["data"] == {"listen_port": 80}


def test_update_lb_service_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 52}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    service = {"listen_port": 80, "protocol": "http", "destination_port": 8080}
    ok = manager.update_lb_service(10, service)

    assert ok is True
    assert "update_service" in captured["endpoint"]
    assert captured["data"] == service


def test_change_lb_algorithm_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 53}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    ok = manager.change_lb_algorithm(10, "least_connections")

    assert ok is True
    assert "change_algorithm" in captured["endpoint"]
    assert captured["data"] == {"type": "least_connections"}


def test_change_lb_algorithm_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (422, {"error": {"message": "invalid"}}),
    )

    assert manager.change_lb_algorithm(10, "invalid_algo") is False
