#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_images_no_filter(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"images": [{"id": 1, "type": "snapshot"}]}),
    )

    result = manager.list_images()
    assert result == [{"id": 1, "type": "snapshot"}]


def test_list_images_with_type_filter(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 200, {"images": [{"id": 2, "type": "backup"}]}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.list_images(image_type="backup")
    assert result == [{"id": 2, "type": "backup"}]
    assert "type=backup" in captured["endpoint"]


def test_list_images_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (500, {"error": {"message": "server error"}}),
    )

    assert manager.list_images() == []


def test_get_image_by_id_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (200, {"image": {"id": 42, "type": "snapshot"}}),
    )

    result = manager.get_image_by_id(42)
    assert result == {"id": 42, "type": "snapshot"}


def test_get_image_by_id_not_found(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.get_image_by_id(99) == {}


def test_delete_image_success(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (204, {}),
    )

    assert manager.delete_image(42) is True


def test_delete_image_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (403, {"error": {"message": "forbidden"}}),
    )

    assert manager.delete_image(42) is False


def test_update_image_success(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["data"] = data
        return 200, {"image": {"id": 42, "description": "new desc"}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.update_image(42, description="new desc", labels={"env": "test"})
    assert result == {"id": 42, "description": "new desc"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "images/42"
    assert captured["data"]["description"] == "new desc"
    assert captured["data"]["labels"] == {"env": "test"}


def test_update_image_only_description(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["data"] = data
        return 200, {"image": {"id": 42}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    manager.update_image(42, description="only desc")
    assert "description" in captured["data"]
    assert "labels" not in captured["data"]


def test_update_image_failure(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}),
    )

    assert manager.update_image(99, description="x") == {}
