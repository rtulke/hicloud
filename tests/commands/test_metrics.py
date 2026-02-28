#!/usr/bin/env python3

from commands.metrics import MetricsCommands


class DummyConsole:
    def __init__(self, hetzner):
        self.hetzner = hetzner
        self.tables = []

    def print_table(self, headers, rows, title=None):
        self.tables.append((headers, rows, title))

    def horizontal_line(self, char="="):
        return char * 60


class DummyHetzner:
    def __init__(self):
        self.server = {"id": 1, "name": "web-01", "status": "running"}
        self.cpu_metrics = {
            "time_series": {"values": [50.0, 60.0, 45.0, 70.0]}
        }
        self.traffic_metrics = {
            "time_series": {
                "network_in": {"values": [1024, 2048]},
                "network_out": {"values": [512, 1024]},
            }
        }
        self.disk_metrics = {
            "time_series": {
                "disk_read": {"values": [100, 200]},
                "disk_write": {"values": [50, 80]},
            }
        }
        self.cpu_calls = []
        self.traffic_calls = []
        self.disk_calls = []

    def get_server_by_id(self, server_id):
        return self.server if server_id == 1 else None

    def get_available_metrics(self, server_id):
        return ["cpu", "disk", "network"]

    def get_cpu_metrics(self, server_id, hours=24):
        self.cpu_calls.append((server_id, hours))
        return self.cpu_metrics

    def get_network_metrics(self, server_id, days=7):
        self.traffic_calls.append((server_id, days))
        return self.traffic_metrics

    def get_disk_metrics(self, server_id, days=1):
        self.disk_calls.append((server_id, days))
        return self.disk_metrics


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return MetricsCommands(c), h, c


# --- list metrics ---

def test_list_metrics_shows_available(capsys):
    cmd, _, _ = build()
    cmd.list_metrics(["1"])
    out = capsys.readouterr().out
    assert "cpu" in out
    assert "web-01" in out


def test_list_metrics_missing_id(capsys):
    cmd, _, _ = build()
    cmd.list_metrics([])
    assert "Missing server ID" in capsys.readouterr().out


def test_list_metrics_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.list_metrics(["abc"])
    assert "Invalid server ID" in capsys.readouterr().out


def test_list_metrics_server_not_found(capsys):
    cmd, _, _ = build()
    cmd.list_metrics(["99"])
    assert "not found" in capsys.readouterr().out


# --- cpu ---

def test_cpu_default_hours(capsys):
    cmd, h, _ = build()
    cmd.show_cpu_metrics(["1"])
    out = capsys.readouterr().out
    assert "CPU" in out
    assert h.cpu_calls == [(1, 24)]


def test_cpu_custom_hours(capsys):
    cmd, h, _ = build()
    cmd.show_cpu_metrics(["1", "--hours=48"])
    out = capsys.readouterr().out
    assert "48 hours" in out
    assert h.cpu_calls == [(1, 48)]


def test_cpu_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_cpu_metrics([])
    assert "Missing server ID" in capsys.readouterr().out


def test_cpu_server_not_found(capsys):
    cmd, _, _ = build()
    cmd.show_cpu_metrics(["99"])
    assert "not found" in capsys.readouterr().out


def test_cpu_shows_min_max(capsys):
    cmd, h, _ = build()
    cmd.show_cpu_metrics(["1"])
    out = capsys.readouterr().out
    assert "Min" in out
    assert "Max" in out


# --- traffic ---

def test_traffic_default_days(capsys):
    cmd, h, _ = build()
    cmd.show_traffic_metrics(["1"])
    capsys.readouterr()
    assert h.traffic_calls == [(1, 7)]


def test_traffic_custom_days():
    cmd, h, _ = build()
    cmd.show_traffic_metrics(["1", "--days=14"])
    assert h.traffic_calls == [(1, 14)]


def test_traffic_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_traffic_metrics([])
    assert "Missing server ID" in capsys.readouterr().out


# --- disk ---

def test_disk_default_days():
    cmd, h, _ = build()
    cmd.show_disk_metrics(["1"])
    assert h.disk_calls == [(1, 1)]


def test_disk_custom_days():
    cmd, h, _ = build()
    cmd.show_disk_metrics(["1", "--days=3"])
    assert h.disk_calls == [(1, 3)]


def test_disk_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_disk_metrics([])
    assert "Missing server ID" in capsys.readouterr().out


# --- no subcommand ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing metrics subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown metrics subcommand" in capsys.readouterr().out
