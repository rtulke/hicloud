#!/usr/bin/env python3

from commands.location import DatacenterCommands, LocationCommands, ServerTypeCommands


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
        self.locations = [
            {
                "id": 2,
                "name": "fsn1",
                "description": "Falkenstein",
                "city": "Falkenstein",
                "country": "DE",
                "network_zone": "eu-central",
                "latitude": 50.0,
                "longitude": 12.3,
            },
            {
                "id": 1,
                "name": "nbg1",
                "description": "Nuremberg",
                "city": "Nuremberg",
                "country": "DE",
                "network_zone": "eu-central",
                "latitude": 49.4,
                "longitude": 11.1,
            },
        ]
        self.datacenters = [
            {
                "id": 2,
                "name": "fsn1-dc14",
                "description": "Falkenstein DC 14",
                "location": {
                    "id": 2,
                    "name": "fsn1",
                    "city": "Falkenstein",
                    "country": "DE",
                    "network_zone": "eu-central",
                },
                "server_types": {"supported": [11, 12], "available": [11]},
                "network_zones": ["eu-central"],
            },
            {
                "id": 1,
                "name": "nbg1-dc3",
                "description": "Nuremberg DC 3",
                "location": {
                    "id": 1,
                    "name": "nbg1",
                    "city": "Nuremberg",
                    "country": "DE",
                    "network_zone": "eu-central",
                },
                "server_types": {"supported": [21, 22], "available": [21, 22]},
                "network_zones": ["eu-central"],
            },
        ]
        self.servers = [
            {"id": 11, "datacenter": {"id": 1}},
            {"id": 12, "datacenter": {"id": 1}},
            {"id": 21, "datacenter": {"id": 2}},
        ]
        self.volumes = [
            {"id": 201, "location": {"id": 1}},
            {"id": 202, "location": {"id": 2}},
            {"id": 203, "location": {"id": 1}},
        ]
        self.floating_ips = [
            {"id": 301, "home_location": {"id": 1}},
        ]
        self.load_balancers = [
            {"id": 401, "location": {"id": 1}},
            {"id": 402, "location": {"id": 2}},
        ]
        self.server_types = [
            {
                "id": 1,
                "name": "cx11",
                "description": "CX11",
                "architecture": "x86",
                "cores": 1,
                "memory": 2.0,
                "disk": 20,
                "storage_type": "local",
                "cpu_type": "shared",
                "prices": [
                    {
                        "location": "nbg1",
                        "price_hourly": {"gross": "0.0060", "net": "0.0050"},
                        "price_monthly": {"gross": "3.29", "net": "2.77"},
                    }
                ],
            },
            {
                "id": 2,
                "name": "cax11",
                "description": "CAX11",
                "architecture": "arm",
                "cores": 2,
                "memory": 4.0,
                "disk": 40,
                "storage_type": "local",
                "cpu_type": "shared",
                "prices": [
                    {
                        "location": "fsn1",
                        "price_hourly": {"gross": "0.0080", "net": "0.0067"},
                        "price_monthly": {"gross": "4.59", "net": "3.86"},
                    }
                ],
            },
        ]

    def list_locations(self):
        return self.locations

    def get_location_by_id(self, location_id):
        for location in self.locations:
            if location.get("id") == location_id:
                return location
        return None

    def list_datacenters(self):
        return self.datacenters

    def get_datacenter_by_id(self, datacenter_id):
        for datacenter in self.datacenters:
            if datacenter.get("id") == datacenter_id:
                return datacenter
        return None

    def list_servers(self):
        return self.servers

    def list_volumes(self):
        return self.volumes

    def _make_request(self, method, endpoint):
        if method == "GET" and endpoint == "floating_ips":
            return 200, {"floating_ips": self.floating_ips}
        if method == "GET" and endpoint == "load_balancers":
            return 200, {"load_balancers": self.load_balancers}
        return 500, {}

    def list_server_types(self):
        return self.server_types


def build_location_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return LocationCommands(console), hetzner, console


def build_datacenter_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return DatacenterCommands(console), hetzner, console


def build_server_type_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return ServerTypeCommands(console), hetzner, console


def build_commands():
    return build_server_type_commands()


def test_location_list_builds_table():
    commands, _, console = build_location_commands()
    commands.list_locations()

    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert headers == ["ID", "Name", "City", "Country", "Network Zone"]
    assert [row[0] for row in rows] == [1, 2]
    assert title == "Available Locations"


def test_location_list_empty(capsys):
    commands, hetzner, _ = build_location_commands()
    hetzner.locations = []
    commands.list_locations()

    output = capsys.readouterr().out
    assert "No locations found" in output


def test_location_info_shows_details(capsys):
    commands, _, _ = build_location_commands()
    commands.location_info(["1"])

    output = capsys.readouterr().out
    assert "Location Details" in output
    assert "nbg1" in output
    assert "Nuremberg" in output
    assert "Latitude" in output


def test_location_info_missing_id(capsys):
    commands, _, _ = build_location_commands()
    commands.location_info([])

    output = capsys.readouterr().out
    assert "Missing location ID" in output


def test_location_info_invalid_id(capsys):
    commands, _, _ = build_location_commands()
    commands.location_info(["abc"])

    output = capsys.readouterr().out
    assert "Invalid location ID" in output


def test_location_handle_no_subcommand(capsys):
    commands, _, _ = build_location_commands()
    commands.handle_command([])

    output = capsys.readouterr().out
    assert "Missing location subcommand" in output


def test_location_handle_unknown_subcommand(capsys):
    commands, _, _ = build_location_commands()
    commands.handle_command(["foobar"])

    output = capsys.readouterr().out
    assert "Unknown location subcommand" in output


def test_list_datacenters_builds_table():
    commands, _, console = build_datacenter_commands()
    commands.list_datacenters()

    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert headers == ["ID", "Name", "Description", "Location"]
    assert [row[0] for row in rows] == [1, 2]
    assert title == "Available Datacenters"


def test_list_datacenters_empty(capsys):
    commands, hetzner, _ = build_datacenter_commands()
    hetzner.datacenters = []
    commands.list_datacenters()

    output = capsys.readouterr().out
    assert "No datacenters found" in output


def test_datacenter_info_shows_details(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.datacenter_info(["1"])

    output = capsys.readouterr().out
    assert "Datacenter Details" in output
    assert "nbg1-dc3" in output
    assert "Nuremberg" in output
    assert "Supported Server Types: 2 types" in output
    assert "Network Zones: eu-central" in output


def test_datacenter_info_missing_id(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.datacenter_info([])

    output = capsys.readouterr().out
    assert "Missing datacenter ID" in output


def test_datacenter_info_invalid_id(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.datacenter_info(["abc"])

    output = capsys.readouterr().out
    assert "Invalid datacenter ID" in output


def test_datacenter_handle_no_subcommand(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.handle_command([])

    output = capsys.readouterr().out
    assert "Missing datacenter subcommand" in output


def test_datacenter_handle_unknown_subcommand(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.handle_command(["foobar"])

    output = capsys.readouterr().out
    assert "Unknown datacenter subcommand" in output


def test_datacenter_resources_builds_aggregated_table():
    commands, _, console = build_datacenter_commands()
    commands.datacenter_resources([])

    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert headers == ["ID", "Name", "Location", "Servers", "Volumes", "Floating IPs", "Load Balancers"]
    assert title == "Datacenter Resources"
    assert rows[0] == [1, "nbg1-dc3", "nbg1", 2, 2, 1, 1]
    assert rows[1] == [2, "fsn1-dc14", "fsn1", 1, 1, 0, 1]


def test_datacenter_resources_single_dc_shows_details(capsys):
    commands, _, console = build_datacenter_commands()
    commands.datacenter_resources(["1"])

    assert len(console.tables) == 1
    _, rows, _ = console.tables[0]
    assert rows == [[1, "nbg1-dc3", "nbg1", 2, 2, 1, 1]]

    output = capsys.readouterr().out
    assert "Details:" in output
    assert "Servers:        11, 12" in output
    assert "Volumes:        201, 203" in output
    assert "Floating IPs:   301" in output
    assert "Load Balancers: 401" in output


def test_datacenter_resources_filter_by_location():
    commands, _, console = build_datacenter_commands()
    commands.datacenter_resources(["fsn1"])

    assert len(console.tables) == 1
    _, rows, _ = console.tables[0]
    assert rows == [[2, "fsn1-dc14", "fsn1", 1, 1, 0, 1]]


def test_datacenter_resources_filter_not_found(capsys):
    commands, _, _ = build_datacenter_commands()
    commands.datacenter_resources(["nowhere"])

    output = capsys.readouterr().out
    assert "No datacenter found matching" in output


def test_datacenter_resources_no_datacenters(capsys):
    commands, hetzner, _ = build_datacenter_commands()
    hetzner.datacenters = []
    commands.datacenter_resources([])

    output = capsys.readouterr().out
    assert "No datacenters found" in output


def test_list_server_types_grouped_by_arch():
    commands, _, console = build_commands()
    commands.list_server_types([])

    assert len(console.tables) == 2
    titles = [t for _, _, t in console.tables]
    assert any("X86" in t.upper() for t in titles)
    assert any("ARM" in t.upper() for t in titles)


def test_list_server_types_with_location_filter():
    commands, _, console = build_commands()
    commands.list_server_types(["nbg1"])

    assert len(console.tables) == 2
    titles = [t for _, _, t in console.tables]
    assert any("nbg1" in t for t in titles)


def test_list_server_types_empty(capsys):
    commands, hetzner, _ = build_commands()
    hetzner.server_types = []
    commands.list_server_types([])

    output = capsys.readouterr().out
    assert "No server types" in output


def test_list_server_types_rows_contain_data():
    commands, _, console = build_commands()
    commands.list_server_types([])

    all_rows = []
    for _, rows, _ in console.tables:
        all_rows.extend(rows)

    names = [row[0] for row in all_rows]
    assert "cx11" in names
    assert "cax11" in names


def test_show_server_type_info_by_name(capsys):
    commands, _, _ = build_commands()
    commands.show_server_type_info(["cx11"])

    output = capsys.readouterr().out
    assert "cx11" in output
    assert "x86" in output
    assert "CX11" in output


def test_show_server_type_info_by_id(capsys):
    commands, _, _ = build_commands()
    commands.show_server_type_info(["2"])

    output = capsys.readouterr().out
    assert "cax11" in output
    assert "arm" in output


def test_show_server_type_info_not_found(capsys):
    commands, _, _ = build_commands()
    commands.show_server_type_info(["cx999"])

    output = capsys.readouterr().out
    assert "not found" in output


def test_show_server_type_info_missing_arg(capsys):
    commands, _, _ = build_commands()
    commands.show_server_type_info([])

    output = capsys.readouterr().out
    assert "Missing" in output


def test_show_server_type_info_shows_pricing(capsys):
    commands, _, _ = build_commands()
    commands.show_server_type_info(["cx11"])

    output = capsys.readouterr().out
    assert "nbg1" in output
    assert "€" in output
