#!/usr/bin/env python3

import requests

from lib.api import HetznerCloudManager


class DummyResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def test_make_request_unsupported_method_returns_400():
    manager = HetznerCloudManager("token")

    status_code, response = manager._make_request("PATCH", "servers")
    assert status_code == 400
    assert "Unsupported method" in response["error"]["message"]


def test_make_request_handles_request_exception(monkeypatch):
    manager = HetznerCloudManager("token")

    def fail_get(*args, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "get", fail_get)

    status_code, response = manager._make_request("GET", "servers")
    assert status_code == 500
    assert "Request failed" in response["error"]["message"]


def test_make_request_returns_json_for_200(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: DummyResponse(200, text='{"servers": []}', payload={"servers": []}))

    status_code, response = manager._make_request("GET", "servers")
    assert status_code == 200
    assert response == {"servers": []}


def test_make_request_sets_timeout_on_every_method(monkeypatch):
    from utils.constants import REQUEST_TIMEOUT

    manager = HetznerCloudManager("token")
    captured = {}

    def capture(name):
        def fake(*args, **kwargs):
            captured[name] = kwargs.get("timeout")
            return DummyResponse(200, text="{}", payload={})
        return fake

    monkeypatch.setattr(requests, "get", capture("GET"))
    monkeypatch.setattr(requests, "post", capture("POST"))
    monkeypatch.setattr(requests, "put", capture("PUT"))
    monkeypatch.setattr(requests, "delete", capture("DELETE"))

    for method in ("GET", "POST", "PUT", "DELETE"):
        manager._make_request(method, "servers")
        assert captured[method] == REQUEST_TIMEOUT, method


def test_get_all_pages_follows_pagination(monkeypatch):
    manager = HetznerCloudManager("token")
    calls = []

    def fake_request(method, endpoint, data=None):
        calls.append(endpoint)
        if "page=2" in endpoint:
            return 200, {"servers": [{"id": 2}], "meta": {"pagination": {"next_page": None}}}
        return 200, {"servers": [{"id": 1}], "meta": {"pagination": {"next_page": 2}}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    status_code, response = manager._get_all_pages("servers", "servers")
    assert status_code == 200
    assert response == {"servers": [{"id": 1}, {"id": 2}]}
    assert calls == ["servers", "servers?page=2"]


def test_get_all_pages_keeps_existing_query_params(monkeypatch):
    manager = HetznerCloudManager("token")
    calls = []

    def fake_request(method, endpoint, data=None):
        calls.append(endpoint)
        if "page=" in endpoint:
            return 200, {"images": [], "meta": {"pagination": {"next_page": None}}}
        return 200, {"images": [], "meta": {"pagination": {"next_page": 2}}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    manager._get_all_pages("images?type=snapshot", "images")
    assert calls == ["images?type=snapshot", "images?type=snapshot&page=2"]


def test_get_all_pages_propagates_errors(monkeypatch):
    manager = HetznerCloudManager("token")
    monkeypatch.setattr(
        manager,
        "_make_request",
        lambda method, endpoint, data=None: (500, {"error": {"message": "x"}}),
    )

    status_code, response = manager._get_all_pages("servers", "servers")
    assert status_code == 500
    assert "error" in response


def test_list_servers_merges_all_pages(monkeypatch):
    manager = HetznerCloudManager("token")

    def fake_request(method, endpoint, data=None):
        if "page=2" in endpoint:
            return 200, {"servers": [{"id": 2}], "meta": {"pagination": {"next_page": None}}}
        return 200, {"servers": [{"id": 1}], "meta": {"pagination": {"next_page": 2}}}

    monkeypatch.setattr(manager, "_make_request", fake_request)

    assert manager.list_servers() == [{"id": 1}, {"id": 2}]


def test_make_request_retries_on_429(monkeypatch):
    import lib.api as api_module

    manager = HetznerCloudManager("token")
    attempts = []
    sleeps = []

    def fake_get(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            limited = DummyResponse(429, text="limit", payload={"error": {"message": "rate limit exceeded"}})
            limited.headers = {"Retry-After": "1"}
            return limited
        return DummyResponse(200, text='{"servers": []}', payload={"servers": []})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(api_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    status_code, response = manager._make_request("GET", "servers")
    assert status_code == 200
    assert len(attempts) == 3
    assert sleeps == [1, 1]


def test_make_request_gives_up_after_max_429_retries(monkeypatch):
    import lib.api as api_module
    from utils.constants import RATE_LIMIT_MAX_RETRIES

    manager = HetznerCloudManager("token")
    attempts = []

    def always_limited(*args, **kwargs):
        attempts.append(1)
        limited = DummyResponse(429, text="limit", payload={"error": {"message": "rate limit exceeded"}})
        limited.headers = {}
        return limited

    monkeypatch.setattr(requests, "get", always_limited)
    monkeypatch.setattr(api_module.time, "sleep", lambda seconds: None)

    status_code, response = manager._make_request("GET", "servers")
    assert status_code == 429
    assert len(attempts) == RATE_LIMIT_MAX_RETRIES + 1
