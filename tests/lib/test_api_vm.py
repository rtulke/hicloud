#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_servers_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"servers": [{"id": 1}]}))

    assert manager.list_servers() == [{"id": 1}]


def test_list_servers_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.list_servers() == []


def test_create_server_payload_start_after_create(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["data"] = data
        return 201, {"server": {"id": 10}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.create_server("vm1", "cx11", "ubuntu", auto_password=True)
    assert result == {"id": 10}
    assert captured["data"]["start_after_create"] is True

    result = manager.create_server("vm2", "cx11", "ubuntu", auto_password=False)
    assert result == {"id": 10}
    assert captured["data"]["start_after_create"] is False


def test_delete_server_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (204, {}))

    assert manager.delete_server(1) is True


def test_delete_server_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (403, {"error": {"message": "x"}}))

    assert manager.delete_server(1) is False


def test_start_server_success_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 1}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: action_id == 1)

    assert manager.start_server(5) is True


def test_stop_server_falls_back_to_poweroff(monkeypatch):
    manager = HetznerCloudManager("token")
    calls = []

    def fake_request(method, endpoint, data=None):
        calls.append(endpoint)
        if endpoint.endswith("/shutdown"):
            return 400, {"error": {"message": "nope"}}
        return 201, {"action": {"id": 2}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.stop_server(5) is True
    assert calls == ["servers/5/actions/shutdown", "servers/5/actions/poweroff"]


def test_stop_server_failure_when_both_fail(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.stop_server(5) is False


def test_get_server_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"server": {"id": 9}}))
    assert manager.get_server_by_id(9) == {"id": 9}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_server_by_id(9) == {}


def test_get_server_by_name(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "list_servers", lambda: [{"name": "a", "id": 1}, {"name": "b", "id": 2}])

    assert manager.get_server_by_name("b") == {"name": "b", "id": 2}
    assert manager.get_server_by_name("x") == {}


def test_resize_server_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 201, {"action": {"id": 8}}

    monkeypatch.setattr(manager, "_make_request", fake_request)
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.resize_server(1, "cx22") is True
    assert captured["endpoint"] == "servers/1/actions/change_type"
    assert captured["data"]["server_type"] == "cx22"
    assert captured["data"]["upgrade_disk"] is True


def test_rename_server_success_and_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {}))
    assert manager.rename_server(1, "new") is True

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "x"}}))
    assert manager.rename_server(1, "new") is False


def test_reboot_server_waits(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (201, {"action": {"id": 10}}))
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.reboot_server(1) is True


def test_enable_rescue_mode_returns_root_password(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 11}, "root_password": "secret"}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.enable_rescue_mode(1) == {"root_password": "secret"}


def test_enable_rescue_mode_wait_failure_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 11}, "root_password": "secret"}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: False)

    assert manager.enable_rescue_mode(1) == {}


def test_reset_server_password_returns_root_password(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 12}, "root_password": "pw"}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.reset_server_password(1) == {"root_password": "pw"}


def test_create_image_waits_and_returns_image(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 13}, "image": {"id": 77}}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.create_image(1, "desc") == {"id": 77}


def test_import_image_from_url_success_image(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (202, {"action": {"id": 14}, "image": {"id": 88}}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.import_image_from_url("img", "https://example.com/a.raw") == {"id": 88}


def test_import_image_from_url_success_image_id(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (201, {"action": {"id": 15}, "image_id": 99}),
    )
    monkeypatch.setattr(manager, "_wait_for_action", lambda action_id, timeout=300, message=None: True)

    assert manager.import_image_from_url("img", "https://example.com/a.raw") == {"id": 99}


def test_import_image_from_url_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (422, {"error": {"message": "bad"}}))

    assert manager.import_image_from_url("img", "https://example.com/a.raw") == {}
