#!/usr/bin/env python3

from commands.location import ServerTypeCommands


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

    def list_server_types(self):
        return self.server_types


def build_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return ServerTypeCommands(console), hetzner, console


def test_list_server_types_grouped_by_arch():
    commands, _, console = build_commands()
    commands.list_server_types([])

    # Should produce one table per architecture (x86, arm)
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
