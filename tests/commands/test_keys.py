#!/usr/bin/env python3

from commands.keys import KeysCommands


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
        self.key = {
            "id": 7,
            "name": "my-key",
            "fingerprint": "ab:cd:ef:12:34",
            "public_key": "ssh-ed25519 AAAAC3Nza test@host",
            "labels": {},
            "created": "2024-02-01T12:00:00+00:00",
        }
        self.delete_calls = []
        self.create_calls = []
        self.update_calls = []

    def list_ssh_keys(self):
        return [self.key]

    def get_ssh_key_by_id(self, key_id):
        return self.key if key_id == 7 else None

    def list_servers(self):
        return []

    def delete_ssh_key(self, key_id):
        self.delete_calls.append(key_id)
        return True

    def create_ssh_key(self, name, public_key, labels=None):
        self.create_calls.append({"name": name, "public_key": public_key, "labels": labels})
        return {"id": 8, "name": name}

    def update_ssh_key(self, key_id, name=None, labels=None):
        self.update_calls.append((key_id, {"name": name, "labels": labels}))
        return {"id": key_id, "name": name}


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return KeysCommands(c), h, c


# --- list ---

def test_list_builds_table():
    cmd, _, console = build()
    cmd.list_keys()
    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "Name" in headers
    assert "Fingerprint" in headers
    assert title == "SSH Keys"
    assert rows[0][1] == "my-key"
    assert rows[0][2] == "ab:cd:ef:12:34"


def test_list_empty(capsys):
    cmd, h, _ = build()

    class Empty:
        def list_ssh_keys(self): return []
    cmd.hetzner = Empty()
    cmd.list_keys()
    assert "No SSH keys" in capsys.readouterr().out


# --- info ---

def test_show_info(capsys):
    cmd, _, _ = build()
    cmd.show_key_info(["7"])
    out = capsys.readouterr().out
    assert "my-key" in out
    assert "ab:cd:ef:12:34" in out
    assert "ssh-ed25519" in out


def test_show_info_missing_id(capsys):
    cmd, _, _ = build()
    cmd.show_key_info([])
    assert "Missing SSH key ID" in capsys.readouterr().out


def test_show_info_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.show_key_info(["abc"])
    assert "Invalid key ID" in capsys.readouterr().out


# --- create ---

def test_create_from_file(monkeypatch, tmp_path):
    pub_key_file = tmp_path / "id_ed25519.pub"
    pub_key_file.write_text("ssh-ed25519 AAAAC3Nza test@host")

    cmd, h, _ = build()
    answers = iter(["n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cmd.create_key(["mykey", str(pub_key_file)])
    assert len(h.create_calls) == 1
    assert h.create_calls[0]["name"] == "mykey"
    assert "ssh-ed25519" in h.create_calls[0]["public_key"]


def test_create_invalid_key_format(monkeypatch, capsys, tmp_path):
    bad_key_file = tmp_path / "bad.pub"
    bad_key_file.write_text("not-a-valid-key")

    cmd, _, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.create_key(["mykey", str(bad_key_file)])
    assert "Invalid SSH public key" in capsys.readouterr().out


# --- delete ---

def test_delete_confirmed(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    cmd.delete_key(["7"])
    assert h.delete_calls == [7]


def test_delete_cancelled(monkeypatch):
    cmd, h, _ = build()
    monkeypatch.setattr("builtins.input", lambda _: "n")
    cmd.delete_key(["7"])
    assert h.delete_calls == []


def test_delete_missing_id(capsys):
    cmd, _, _ = build()
    cmd.delete_key([])
    assert "Missing SSH key ID" in capsys.readouterr().out


def test_delete_invalid_id(capsys):
    cmd, _, _ = build()
    cmd.delete_key(["abc"])
    assert "Invalid key ID" in capsys.readouterr().out


def test_delete_not_found(capsys):
    cmd, _, _ = build()
    cmd.delete_key(["99"])
    # get_ssh_key_by_id returns None → silent return (error printed inside API)
    out = capsys.readouterr().out
    assert "delete" not in out.lower() or "not found" in out.lower()


# --- unknown subcommand ---

def test_no_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command([])
    assert "Missing keys subcommand" in capsys.readouterr().out


def test_unknown_subcommand(capsys):
    cmd, _, _ = build()
    cmd.handle_command(["foobar"])
    assert "Unknown keys subcommand" in capsys.readouterr().out
