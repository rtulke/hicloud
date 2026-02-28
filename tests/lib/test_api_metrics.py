#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_get_server_metrics_builds_endpoint(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_request(method, endpoint, data=None):
        captured["endpoint"] = endpoint
        return 200, {"metrics": {"time_series": {}}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.get_server_metrics(10, "cpu", "2026-02-27T00:00:00Z", "2026-02-28T00:00:00Z", step="60")
    assert result == {"time_series": {}}
    assert "servers/10/metrics?" in captured["endpoint"]
    assert "type=cpu" in captured["endpoint"]
    assert "step=60" in captured["endpoint"]


def test_get_server_metrics_error_returns_empty(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))

    assert manager.get_server_metrics(10, "cpu", "a", "b") == {}


def test_get_cpu_metrics_uses_reasonable_step(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_get(server_id, metric_type, start, end, step=None):
        captured["step"] = step
        return {"ok": True}

    monkeypatch.setattr(manager, "get_server_metrics", fake_get)

    assert manager.get_cpu_metrics(1, hours=5) == {"ok": True}
    assert captured["step"] == "60"

    assert manager.get_cpu_metrics(1, hours=24) == {"ok": True}
    assert captured["step"] == "300"


def test_get_network_metrics_step_changes_with_days(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_get(server_id, metric_type, start, end, step=None):
        captured["step"] = step
        return {"ok": True}

    monkeypatch.setattr(manager, "get_server_metrics", fake_get)

    assert manager.get_network_metrics(1, days=1) == {"ok": True}
    assert captured["step"] == "300"

    assert manager.get_network_metrics(1, days=7) == {"ok": True}
    assert captured["step"] == "3600"

    assert manager.get_network_metrics(1, days=10) == {"ok": True}
    assert captured["step"] == "86400"


def test_get_disk_metrics_uses_fixed_step(monkeypatch):
    manager = HetznerCloudManager("token")
    captured = {}

    def fake_get(server_id, metric_type, start, end, step=None):
        captured["step"] = step
        return {"ok": True}

    monkeypatch.setattr(manager, "get_server_metrics", fake_get)

    assert manager.get_disk_metrics(1, days=3) == {"ok": True}
    assert captured["step"] == "60"


def test_get_available_metrics_is_static_list():
    manager = HetznerCloudManager("token")
    assert manager.get_available_metrics(1) == ["cpu", "disk", "network"]
