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


# --- readline fallback ---

def test_console_starts_without_readline(monkeypatch, tmp_path, capsys):
    """Windows without pyreadline3: the console must come up with a hint,
    not die on the module import."""
    monkeypatch.setattr(console_module, "HISTORY_DIR", str(tmp_path / "hist"))
    monkeypatch.setattr(console_module, "readline", None)
    monkeypatch.setattr(console_module.platform, "system", lambda: "Windows")

    console = InteractiveConsole(DummyHetzner())

    out = capsys.readouterr().out
    assert "readline is not available" in out
    assert "pip install pyreadline3" in out
    assert console.commands  # registry still built


def test_history_commands_degrade_without_readline(console, monkeypatch, capsys):
    monkeypatch.setattr(console_module, "readline", None)

    console._save_history()          # must stay silent, nothing to save
    console._clean_history()
    console._display_history()

    out = capsys.readouterr().out
    assert out.count("Command history is not available") == 2
    assert "Warning" not in out


# --- tab completion ---

class CompletionHetzner(DummyHetzner):
    def list_servers(self):
        return [{"id": 101}, {"id": 102}, {"id": 2000}]

    def list_volumes(self):
        return [{"id": 7}]


@pytest.fixture
def completer(monkeypatch, tmp_path):
    """Drives _command_completer the way readline does: the buffer comes from
    get_line_buffer(), `text` is the word under the cursor, state 0."""
    from types import SimpleNamespace
    monkeypatch.setattr(console_module, "HISTORY_DIR", str(tmp_path / "hist"))
    monkeypatch.setattr(InteractiveConsole, "_setup_readline", lambda self: None)
    console = InteractiveConsole(CompletionHetzner())
    state = {"buffer": ""}
    monkeypatch.setattr(console_module, "readline", SimpleNamespace(get_line_buffer=lambda: state["buffer"]))

    def complete(buffer):
        state["buffer"] = buffer
        text = "" if buffer.endswith(" ") or not buffer else buffer.split()[-1]
        return console._command_completer(text, 0)

    return complete


def test_complete_unique_main_command_adds_space(completer):
    assert completer("vo") == "volume "


def test_complete_main_command_is_case_insensitive(completer):
    assert completer("VO") == "volume "


def test_complete_main_command_extends_to_common_prefix(completer, capsys):
    assert completer("ser") == "server"
    assert "server, server-type" in capsys.readouterr().out


def test_complete_subcommand_adds_space_even_when_already_complete(completer):
    assert completer("vm li") == "list "
    assert completer("vm list") == "list "
    assert completer("VM li") == "list "
    assert completer("server li") == "list "


def test_complete_subcommand_lists_alternatives(completer, capsys):
    assert completer("vm re") is None
    out = capsys.readouterr().out
    assert "Matching subcommands:" in out
    for sub in ("reboot", "rename", "rescue", "reset-password", "resize"):
        assert sub in out
    assert "VM commands:" not in out  # the full overview is noise here


def test_complete_after_command_shows_overview_and_keeps_buffer(completer, capsys):
    assert completer("vm ") is None
    out = capsys.readouterr().out
    assert "VM commands:" in out
    # the redrawn prompt must show what was typed, not an empty line
    assert out.rstrip().endswith("vm")


def test_complete_argument_values(completer, capsys):
    assert completer("vm info 2") == "2000 "
    assert completer("vm info 1") == "10"          # common prefix of 101, 102
    assert completer("volume info ") == "7 "        # single candidate fills in
    assert completer("vm info 5") is None
    assert "No server_id starting with '5'" in capsys.readouterr().out


def test_complete_free_form_argument_shows_usage(completer, capsys):
    assert completer("vm rename 101 ") is None
    assert "vm rename <id> <new_name>" in capsys.readouterr().out


def test_complete_subcommand_without_arguments_shows_its_help(completer, capsys):
    assert completer("vm create ") is None
    assert "Create a new VM" in capsys.readouterr().out


def test_complete_literal_arguments(completer):
    assert completer("firewall rules a") == "add "


def test_prompt_hides_colour_codes_from_readline(completer, monkeypatch, tmp_path):
    monkeypatch.setattr(console_module, "HISTORY_DIR", str(tmp_path / "hist2"))
    console = InteractiveConsole(DummyHetzner())
    # every escape sequence readline gets is wrapped in \001 ... \002
    import re
    stripped = re.sub(r"\001\x1b\[[0-9;]*m\002", "", console.prompt_string)
    assert "\x1b" not in stripped
    assert stripped == "hicloud> "
    # no newline inside the prompt (libedit counts it as a column)
    assert not console.prompt_string.startswith("\n")
    # the plain label used for print() carries no readline markers
    assert "\001" not in console.prompt_label
