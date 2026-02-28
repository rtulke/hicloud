#!/usr/bin/env python3

from lib.api import HetznerCloudManager


def test_project_related_list_servers(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"servers": [{"id": 1}]}))

    assert manager.list_servers() == [{"id": 1}]


def test_project_related_list_snapshots(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"images": [{"id": 1}]}))

    assert manager.list_snapshots() == [{"id": 1}]


def test_project_related_list_backups(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"images": [{"id": 2}]}))

    assert manager.list_backups() == [{"id": 2}]


def test_project_related_list_ssh_keys(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(manager, "_make_request", lambda method, endpoint, data=None: (200, {"ssh_keys": [{"id": 3}]}))

    assert manager.list_ssh_keys() == [{"id": 3}]
