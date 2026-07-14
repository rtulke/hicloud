#!/usr/bin/env python3

import re

import utils.formatting as formatting


ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _plain_lines(output):
    return [ANSI_PATTERN.sub("", line) for line in output.splitlines()]


# --- truncate_cell ---

def test_truncate_cell_short_text_unchanged():
    assert formatting.truncate_cell("abc", 10) == "abc"


def test_truncate_cell_exact_width_unchanged():
    assert formatting.truncate_cell("abcdef", 6) == "abcdef"


def test_truncate_cell_long_text_gets_ellipsis():
    result = formatting.truncate_cell("abcdefghij", 6)
    assert result == "abcde…"
    assert len(result) == 6


def test_truncate_cell_tiny_width():
    assert formatting.truncate_cell("abcdef", 1) == "a"
    assert formatting.truncate_cell("abcdef", 0) == ""


# --- create_table_layout ---

def test_layout_sizes_columns_to_content(monkeypatch):
    monkeypatch.setattr(formatting, "get_terminal_width", lambda: 200)
    layout = formatting.create_table_layout(["ID", "Name"], [[1, "server-one"]])
    # content width + default padding of 2
    assert layout["column_widths"] == [len("ID") + 2, len("server-one") + 2]
    assert layout["padding"] == 2


def test_layout_scales_down_for_narrow_terminal(monkeypatch):
    monkeypatch.setattr(formatting, "get_terminal_width", lambda: 40)
    layout = formatting.create_table_layout(["ID", "Name"], [[1, "x" * 100]])
    assert layout["total_width"] <= 40


# --- print_table ---

def test_print_table_no_rows(capsys):
    formatting.print_table(["ID"], [], title="Empty")
    out = capsys.readouterr().out
    assert "No data found" in out


def test_print_table_pads_short_rows(monkeypatch, capsys):
    monkeypatch.setattr(formatting, "get_terminal_width", lambda: 200)
    formatting.print_table(["ID", "Name", "Status"], [[1, "web"]])
    # must not raise; missing cells are padded with empty strings
    out = capsys.readouterr().out
    assert "web" in out


def test_print_table_truncates_overwide_cells(monkeypatch, capsys):
    monkeypatch.setattr(formatting, "get_terminal_width", lambda: 40)
    formatting.print_table(["ID", "Name"], [[1, "x" * 100]])
    lines = _plain_lines(capsys.readouterr().out)
    assert any("…" in line for line in lines)
    for line in lines:
        assert len(line) <= 40, line
