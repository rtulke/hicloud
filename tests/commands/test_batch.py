#!/usr/bin/env python3

from commands.batch import BatchCommands


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
        self.servers = {
            1: {"id": 1, "name": "web-01", "status": "off"},
            2: {"id": 2, "name": "web-02", "status": "off"},
            3: {"id": 3, "name": "web-03", "status": "running"},
        }
        self.start_calls = []
        self.stop_calls = []
        self.delete_calls = []
        self.snapshot_calls = []

    def get_server_by_id(self, server_id):
        return self.servers.get(server_id)

    def start_server(self, server_id):
        self.start_calls.append(server_id)
        return True

    def stop_server(self, server_id):
        self.stop_calls.append(server_id)
        return True

    def delete_server(self, server_id):
        self.delete_calls.append(server_id)
        return True

    def create_snapshot(self, server_id, description=None):
        self.snapshot_calls.append(server_id)
        return {"id": 99}


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return BatchCommands(c), h, c


# --- _parse_ids ---

def test_parse_comma_separated_ids(capsys):
    cmd, h, _ = build()
    monkeypatch_input_y = lambda _: "y"
    # Direct test via batch_start which calls _parse_ids
    ids = cmd._parse_ids(["1,2"])
    assert ids == [1, 2]


def test_parse_space_separated_ids():
    cmd, _, _ = build()
    ids = cmd._parse_ids(["1", "2", "3"])
    assert ids == [1, 2, 3]


def test_parse_invalid_id_skips(capsys):
    cmd, _, _ = build()
    ids = cmd._parse_ids(["1,abc,3"])
    capsys.readouterr()
    assert 1 in ids
    assert 3 in ids
    # "abc" produces an error message but does not raise
    assert len(ids) == 2


def test_parse_missing_ids(capsys):
    cmd, _, _ = build()
    ids = cmd._parse_ids([])
    assert ids == []
    assert "Missing server IDs" in capsys.readouterr().out


# --- batch start ---

def test_batch_start_skips_running(monkeypatch, capsys):
    cmd, h, _ = build()
    # server 3 is already running
    answers = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.batch_start(["1,3"])
    out = capsys.readouterr().out
    assert "already running" in out
    assert h.start_calls == [1]  # only server 1 started


def test_batch_start_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.batch_start(["1,2"])
    assert h.start_calls == []


def test_batch_start_not_found(monkeypatch, capsys):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.batch_start(["1,99"])
    out = capsys.readouterr().out
    assert "not found" in out.lower() or "Warning" in out
    assert h.start_calls == [1]


def test_batch_start_no_ids(capsys):
    cmd, _, _ = build()
    cmd.batch_start([])
    assert "Missing server IDs" in capsys.readouterr().out


# --- batch stop ---

def test_batch_stop_skips_off(monkeypatch, capsys):
    cmd, h, _ = build()
    # servers 1 and 2 are "off"
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.batch_stop(["3,1"])
    out = capsys.readouterr().out
    assert "already stopped" in out
    assert h.stop_calls == [3]


def test_batch_stop_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.batch_stop(["3"])
    assert h.stop_calls == []


# --- batch delete ---

def test_batch_delete_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "delete")
    cmd.batch_delete(["1,2"])
    assert 1 in h.delete_calls
    assert 2 in h.delete_calls


def test_batch_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.batch_delete(["1,2"])
    assert h.delete_calls == []


def test_batch_delete_wrong_confirmation(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    cmd.batch_delete(["1"])
    assert h.delete_calls == []


# --- batch snapshot ---

def test_batch_snapshot_confirmed(monkeypatch):
    cmd, h, _ = build()
    answers = iter(["batch snap", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.batch_snapshot(["1,2"])
    assert 1 in h.snapshot_calls
    assert 2 in h.snapshot_calls


def test_batch_snapshot_cancelled(monkeypatch):
    cmd, h, _ = build()
    answers = iter(["", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.batch_snapshot(["1"])
    assert h.snapshot_calls == []


# --- handle_command ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing batch subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown batch subcommand" in capsys.readouterr().out
