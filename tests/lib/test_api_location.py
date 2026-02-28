#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_list_locations_success_and_error(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"locations": [{"id": 1}]}))
    assert manager.list_locations() == [{"id": 1}]

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))
    assert manager.list_locations() == []


def test_get_location_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"location": {"id": 1}}))
    assert manager.get_location_by_id(1) == {"id": 1}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_location_by_id(1) == {}


def test_list_datacenters_success_and_error(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"datacenters": [{"id": 1}]}))
    assert manager.list_datacenters() == [{"id": 1}]

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))
    assert manager.list_datacenters() == []


def test_get_datacenter_by_id_success_and_not_found(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"datacenter": {"id": 2}}))
    assert manager.get_datacenter_by_id(2) == {"id": 2}

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (404, {"error": {"message": "not found"}}))
    assert manager.get_datacenter_by_id(2) == {}


def test_list_server_types_success_and_error(monkeypatch):
    manager = HetznerCloudManager("token")

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"server_types": [{"id": 1, "name": "cx11"}]}))
    assert manager.list_server_types() == [{"id": 1, "name": "cx11"}]

    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}))
    assert manager.list_server_types() == []
