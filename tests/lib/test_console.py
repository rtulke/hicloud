#!/usr/bin/env python3

import pytest

import lib.console as console_module
from lib.console import InteractiveConsole


class DummyHetzner:
    project_name = "test-project"


@pytest.fixture
def console(monkeypatch, tmp_path):
    monkeypatch.setattr(console_module, "HISTORY_DIR", str(tmp_path / "hist"))
    monkeypatch.setattr(InteractiveConsole, "_setup_readline", lambda self: None)
    return InteractiveConsole(DummyHetzner())


# --- registry ---

def test_every_command_has_a_handler(console):
    for name, entry in console.commands.items():
        assert callable(entry.get("handler")), f"missing handler for '{name}'"


def test_server_is_alias_for_vm(console):
    assert console.commands["server"]["alias_of"] == "vm"
    assert console.commands["server"]["subcommands"] is console.commands["vm"]["subcommands"]
    assert console.commands["server"]["handler"] == console.commands["vm"]["handler"]


def test_loadbalancer_is_alias_for_lb(console):
    assert console.commands["loadbalancer"]["alias_of"] == "lb"
    assert console.commands["loadbalancer"]["subcommands"] is console.commands["lb"]["subcommands"]
    assert console.commands["loadbalancer"]["handler"] == console.commands["lb"]["handler"]


def test_help_groups_cover_all_public_commands(console):
    grouped = {name for _, names in InteractiveConsole.HELP_GROUPS for name in names}
    special = {"help", "exit", "quit", "q", "clear", "reset", "history"}
    aliases = {name for name, entry in console.commands.items() if entry.get("alias_of")}
    missing = set(console.commands) - grouped - special - aliases
    assert not missing, f"commands missing from HELP_GROUPS: {missing}"


# --- dispatch ---

def test_dispatch_routes_to_registered_handler(console):
    calls = []
    console.commands["vm"]["handler"] = lambda args: calls.append(args)
    console._dispatch(["vm", "list"])
    assert calls == [["list"]]


def test_dispatch_passes_empty_args_without_subcommand(console):
    calls = []
    console.commands["vm"]["handler"] = lambda args: calls.append(args)
    console._dispatch(["vm"])
    assert calls == [[]]


def test_dispatch_is_case_insensitive(console):
    calls = []
    console.commands["vm"]["handler"] = lambda args: calls.append(args)
    console._dispatch(["VM", "list"])
    assert calls == [["list"]]


def test_dispatch_unknown_command_prints_tip(console, capsys):
    console._dispatch(["nonsense"])
    out = capsys.readouterr().out
    assert "Unknown command" in out
    assert "help" in out


def test_exit_commands_stop_the_loop(console):
    for cmd in ("exit", "quit", "q"):
        console.running = True
        console._dispatch([cmd])
        assert console.running is False, cmd


def test_history_dispatch_routes_display_and_clear(console, monkeypatch):
    called = {}
    monkeypatch.setattr(console, "_display_history", lambda: called.setdefault("display", True))
    monkeypatch.setattr(console, "_clean_history", lambda: called.setdefault("clean", True))
    console._dispatch(["history"])
    console._dispatch(["history", "clear"])
    assert called == {"display": True, "clean": True}


# --- generated help ---

def test_general_help_lists_commands_from_registry(console, capsys):
    console.show_help()
    out = capsys.readouterr().out
    for expected in (
        "vm list",
        "firewall rules",
        "lb service",
        "floating-ip assign",
        "config validate",
        "exit, quit, q",
    ):
        assert expected in out, expected


def test_detailed_help_for_single_command(console, capsys):
    console.show_help("vm")
    out = capsys.readouterr().out
    assert "vm list" in out
    assert "vm create" in out
