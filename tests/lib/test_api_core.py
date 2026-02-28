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
