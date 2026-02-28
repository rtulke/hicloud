#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_get_pricing_success_and_error(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"pricing": {"x": 1}}))
    assert manager.get_pricing() == {"x": 1}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))
    assert manager.get_pricing() == {}


def test_calculate_project_costs_returns_empty_when_no_pricing(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "get_pricing", lambda: {})

    assert manager.calculate_project_costs() == {}


def test_calculate_project_costs_happy_path(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(
        manager,
        "get_pricing",
        lambda: {
            "server_types": [{"id": 1, "prices": [{"price_monthly": {"gross": "4.0"}}]}],
            "volume": {"price_per_gb_month": {"gross": "0.05"}},
            "floating_ip": {"price_monthly": {"gross": "1.0"}},
            "load_balancer_types": [{"id": 10, "prices": [{"price_monthly": {"gross": "5.0"}}]}],
        },
    )

    monkeypatch.setattr(manager, "list_servers", lambda: [{"id": 1, "server_type": {"id": 1}}])

    def fake_request(method, endpoint, data=None):
        if endpoint == "volumes":
            return 200, {"volumes": [{"id": 1, "size": 20}]}
        if endpoint == "floating_ips":
            return 200, {"floating_ips": [{"id": 1}, {"id": 2}]}
        if endpoint == "load_balancers":
            return 200, {"load_balancers": [{"id": 1, "load_balancer_type": {"id": 10}}]}
        return 500, {}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    result = manager.calculate_project_costs()
    assert result["servers"]["count"] == 1
    assert result["servers"]["cost"] == 4.0
    assert result["volumes"]["count"] == 1
    assert result["volumes"]["cost"] == 1.0
    assert result["floating_ips"]["count"] == 2
    assert result["floating_ips"]["cost"] == 2.0
    assert result["load_balancers"]["count"] == 1
    assert result["load_balancers"]["cost"] == 5.0
    assert result["total"] == 12.0
