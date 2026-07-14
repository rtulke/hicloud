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


def _series(values):
    """Build a Hetzner-style time series: [timestamp, "value"] pairs."""
    return {"values": [[1700000000 + i * 60, str(v)] for i, v in enumerate(values)]}


class DummyHetzner:
    def __init__(self):
        self.server = {"id": 1, "name": "web-01", "status": "running"}
        self.cpu_metrics = {
            "step": 60,
            "time_series": {"cpu": _series([50.0, 60.0, 45.0, 70.0])},
        }
        self.traffic_metrics = {
            "step": 60,
            "time_series": {
                "network.0.bandwidth.in": _series([1024, 2048]),
                "network.0.bandwidth.out": _series([512, 1024]),
                "network.0.pps.in": _series([10, 20]),
                "network.0.pps.out": _series([5, 8]),
            },
        }
        self.disk_metrics = {
            "step": 60,
            "time_series": {
                "disk.0.bandwidth.read": _series([100, 200]),
                "disk.0.bandwidth.write": _series([50, 80]),
                "disk.0.iops.read": _series([12, 20]),
                "disk.0.iops.write": _series([3, 4]),
            },
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


# --- parsing of the real Hetzner response format ---

def test_cpu_parses_timestamp_value_pairs(capsys):
    cmd, _, _ = build()
    cmd.show_cpu_metrics(["1"])
    out = capsys.readouterr().out
    # avg of 50/60/45/70 = 56.25, min 45, max 70
    assert "56.2% (avg)" in out
    assert "Min: 45.0%" in out
    assert "Max: 70.0%" in out


def test_cpu_empty_series_reports_no_data(capsys):
    cmd, h, _ = build()
    h.cpu_metrics = {"step": 60, "time_series": {"cpu": {"values": []}}}
    cmd.show_cpu_metrics(["1"])
    assert "No CPU metrics data available" in capsys.readouterr().out


def test_traffic_totals_use_step(capsys):
    cmd, _, _ = build()
    cmd.show_traffic_metrics(["1"])
    out = capsys.readouterr().out
    # (1024+2048) bytes/s * 60s = 184320 bytes = 180.00 KB
    assert "Total received: 180.00 KB" in out
    # (512+1024) bytes/s * 60s = 92160 bytes = 90.00 KB
    assert "Total sent:     90.00 KB" in out
    # avg pps: in (10+20)/2 = 15.0, out (5+8)/2 = 6.5
    assert "Received: 15.0 pps" in out
    assert "Sent:     6.5 pps" in out


def test_disk_totals_and_iops(capsys):
    cmd, _, _ = build()
    cmd.show_disk_metrics(["1"])
    out = capsys.readouterr().out
    # (100+200) bytes/s * 60s = 18000 bytes = 17.58 KB
    assert "Total read:  17.58 KB" in out
    # avg iops read (12+20)/2 = 16.0, max 20
    assert "Avg read:  16.0 IOPS" in out
    assert "Max read:  20.0 IOPS" in out


def test_disk_empty_series_reports_no_data(capsys):
    cmd, h, _ = build()
    h.disk_metrics = {"step": 60, "time_series": {}}
    cmd.show_disk_metrics(["1"])
    assert "No disk metrics data available" in capsys.readouterr().out


# --- no subcommand ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing metrics subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown metrics subcommand" in capsys.readouterr().out
