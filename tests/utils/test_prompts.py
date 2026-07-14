#!/usr/bin/env python3

from utils.prompts import prompt_choice, prompt_int


def _feed(monkeypatch, answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _: next(it))


# --- prompt_choice ---

def test_choice_accepts_valid_value(monkeypatch):
    _feed(monkeypatch, ["tcp"])
    assert prompt_choice("? ", ["tcp", "http"]) == "tcp"


def test_choice_normalizes_case(monkeypatch):
    _feed(monkeypatch, ["TCP"])
    assert prompt_choice("? ", ["tcp", "http"]) == "tcp"


def test_choice_empty_returns_default(monkeypatch):
    _feed(monkeypatch, [""])
    assert prompt_choice("? ", ["tcp", "http"], default="tcp") == "tcp"


def test_choice_reprompts_on_invalid(monkeypatch, capsys):
    _feed(monkeypatch, ["bogus", "http"])
    assert prompt_choice("? ", ["tcp", "http"], default="tcp") == "http"
    assert "Invalid input" in capsys.readouterr().out


def test_choice_without_default_reprompts_on_empty(monkeypatch):
    _feed(monkeypatch, ["", "tcp"])
    assert prompt_choice("? ", ["tcp", "http"]) == "tcp"


# --- prompt_int ---

def test_int_accepts_valid_value(monkeypatch):
    _feed(monkeypatch, ["443"])
    assert prompt_int("? ") == 443


def test_int_empty_returns_default(monkeypatch):
    _feed(monkeypatch, [""])
    assert prompt_int("? ", default=8080) == 8080


def test_int_reprompts_on_non_integer(monkeypatch, capsys):
    _feed(monkeypatch, ["15o", "150"])
    assert prompt_int("? ", default=15) == 150
    assert "Invalid input" in capsys.readouterr().out


def test_int_enforces_range(monkeypatch, capsys):
    _feed(monkeypatch, ["0", "70000", "443"])
    assert prompt_int("? ", min_value=1, max_value=65535) == 443
    out = capsys.readouterr().out
    assert "at least 1" in out
    assert "at most 65535" in out


def test_int_without_default_reprompts_on_empty(monkeypatch):
    _feed(monkeypatch, ["", "5"])
    assert prompt_int("? ") == 5
