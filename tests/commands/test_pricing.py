#!/usr/bin/env python3

from commands.pricing import PricingCommands


class DummyConsole:
    def __init__(self, hetzner):
        self.hetzner = hetzner
        self.tables = []
        self.debug = False

    def print_table(self, headers, rows, title=None):
        self.tables.append((headers, rows, title))

    def horizontal_line(self, char="="):
        return char * 60


SAMPLE_PRICING = {
    "server_types": [
        {
            "id": 1,
            "name": "cx22",
            "prices": [
                {
                    "location": "nbg1",
                    "price_hourly": {"gross": "0.0077"},
                    "price_monthly": {"gross": "4.15"},
                }
            ],
        }
    ],
    "load_balancer_types": [],
    "volumes": {"price_per_gb_month": {"gross": "0.0476"}},
    "floating_ips": [
        {
            "type": "ipv4",
            "prices": [{"location": "nbg1", "price_monthly": {"gross": "1.19"}}],
        }
    ],
    "primary_ips": [],
    "traffic": {"price_per_tb": {"gross": "1.19"}},
}


class DummyHetzner:
    def __init__(self):
        self.project_name = "test-project"
        self.servers = [
            {"id": 1, "name": "web-01", "server_type": {"id": 1, "name": "cx22"}, "datacenter": {"location": {"name": "nbg1"}}}
        ]
        self.volumes = [{"id": 5, "name": "data-vol", "size": 50}]
        self.floating_ips = [{"id": 10, "name": "fip-1", "type": "ipv4"}]
        self.load_balancers = []

    def calculate_project_costs(self):
        return {
            "servers": {"count": len(self.servers), "cost": len(self.servers) * 4.15},
            "volumes": {"count": len(self.volumes), "cost": len(self.volumes) * 2.38},
            "floating_ips": {"count": len(self.floating_ips), "cost": len(self.floating_ips) * 1.19},
            "total": len(self.servers) * 4.15 + len(self.volumes) * 2.38 + len(self.floating_ips) * 1.19,
        }

    def get_pricing(self):
        return SAMPLE_PRICING

    def list_server_types(self):
        return [{"id": 1, "name": "cx22", "cores": 2, "memory": 4, "disk": 40}]

    def list_servers(self):
        return self.servers

    def list_volumes(self):
        return self.volumes

    def list_floating_ips(self):
        return self.floating_ips

    def list_load_balancers(self):
        return self.load_balancers

    def list_primary_ips(self):
        return []


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return PricingCommands(c), h, c


# --- list ---

def test_list_all_produces_tables():
    cmd, _, console = build()
    cmd.list_pricing("all")
    titles = [t for _, _, t in console.tables]
    assert any("Server" in (t or "") for t in titles)


def test_list_server_category():
    cmd, _, console = build()
    cmd.list_pricing("server")
    titles = [t for _, _, t in console.tables]
    assert any("Server" in (t or "") for t in titles)


def test_list_invalid_category(capsys):
    cmd, _, _ = build()
    cmd.list_pricing("unknown")
    assert "Unknown pricing category" in capsys.readouterr().out


def test_list_no_pricing_data(capsys):
    cmd, h, _ = build()
    h.get_pricing = lambda: None
    cmd.list_pricing("all")
    assert "Could not retrieve" in capsys.readouterr().out


# --- calculate ---

def test_calculate_shows_output(capsys):
    cmd, _, _ = build()
    cmd.calculate_costs()
    out = capsys.readouterr().out
    # At minimum a summary section should appear
    assert out.strip() != ""


def test_calculate_empty_project(capsys):
    cmd, h, _ = build()
    h.servers = []
    h.volumes = []
    h.floating_ips = []
    cmd.calculate_costs()
    out = capsys.readouterr().out
    assert out.strip() != ""


# --- handle_command ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing pricing subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown pricing subcommand" in capsys.readouterr().out
