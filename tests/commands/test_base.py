#!/usr/bin/env python3

from commands.base import BaseCommands


class DummyConsole:
    def __init__(self):
        self.hetzner = object()


class ToyCommands(BaseCommands):
    label = "toy"
    usage = "toy list|info <id>"

    def __init__(self, console):
        self.calls = []
        super().__init__(console)

    def _build_actions(self):
        return {
            "list": lambda args: self.calls.append(("list", args)),
            "info": lambda args: self.calls.append(("info", args)),
        }


def build():
    return ToyCommands(DummyConsole())


# --- dispatch ---

def test_missing_subcommand_shows_usage(capsys):
    build().handle_command([])
    out = capsys.readouterr().out
    assert "Missing toy subcommand" in out
    assert "toy list|info <id>" in out


def test_unknown_subcommand(capsys):
    build().handle_command(["bogus"])
    assert "Unknown toy subcommand: bogus" in capsys.readouterr().out


def test_dispatch_routes_with_remaining_args():
    cmd = build()
    cmd.handle_command(["info", "42", "extra"])
    assert cmd.calls == [("info", ["42", "extra"])]


def test_dispatch_lowercases_subcommand():
    cmd = build()
    cmd.handle_command(["LIST"])
    assert cmd.calls == [("list", [])]


# --- parse_id ---

def test_parse_id_missing(capsys):
    assert BaseCommands.parse_id([], "VM ID", "vm info <id>") is None
    assert "Missing VM ID. Use 'vm info <id>'" in capsys.readouterr().out


def test_parse_id_invalid(capsys):
    assert BaseCommands.parse_id(["abc"], "VM ID", "vm info <id>") is None
    assert "Invalid VM ID. Must be an integer." in capsys.readouterr().out


def test_parse_id_valid():
    assert BaseCommands.parse_id(["42"], "VM ID", "vm info <id>") == 42


# --- confirm ---

def test_confirm_accepts_y(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert BaseCommands.confirm("Delete?") is True


def test_confirm_declines_and_prints_cancelled(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert BaseCommands.confirm("Delete?") is False
    assert "Operation cancelled" in capsys.readouterr().out


# --- prompt_labels ---

def test_prompt_labels_declined(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert BaseCommands.prompt_labels() == {}


def test_prompt_labels_collects_pairs(monkeypatch):
    answers = iter(["y", "env", "prod", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert BaseCommands.prompt_labels() == {"env": "prod"}
