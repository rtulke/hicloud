#!/usr/bin/env python3

from commands.image import ImageCommands


class DummyConsole:
    def __init__(self, hetzner):
        self.hetzner = hetzner
        self.tables = []
        self.vm_commands = _DummyVMCommands()

    def print_table(self, headers, rows, title=None):
        self.tables.append((headers, rows, title))

    def horizontal_line(self, char="="):
        return char * 60


class _DummyVMCommands:
    def __init__(self):
        self.import_calls = []

    def import_image_from_url(self, args):
        self.import_calls.append(args)


class DummyHetzner:
    def __init__(self):
        self.snapshot = {
            "id": 42,
            "type": "snapshot",
            "description": "my-snapshot",
            "name": None,
            "status": "available",
            "architecture": "x86",
            "os_flavor": "ubuntu",
            "os_version": "22.04",
            "image_size": 2.5,
            "created": "2024-01-01T00:00:00Z",
            "created_from": {"id": 1, "name": "app-1"},
            "labels": {"env": "test"},
        }
        self.delete_calls = []
        self.update_calls = []

    def list_images(self, image_type=None):
        return [self.snapshot]

    def get_image_by_id(self, image_id):
        if image_id == 42:
            return self.snapshot
        return {}

    def delete_image(self, image_id):
        self.delete_calls.append(image_id)
        return True

    def update_image(self, image_id, description=None, labels=None):
        self.update_calls.append({"id": image_id, "description": description, "labels": labels})
        return {"id": image_id, "description": description}


def build_commands():
    hetzner = DummyHetzner()
    console = DummyConsole(hetzner)
    return ImageCommands(console), hetzner, console


def test_list_images_builds_table():
    commands, _, console = build_commands()
    commands.list_images([])

    assert len(console.tables) == 1
    headers, rows, title = console.tables[0]
    assert "ID" in headers
    assert rows[0][0] == 42
    assert "snapshot" in title


def test_list_images_all_type():
    commands, _, console = build_commands()
    commands.list_images(["all"])

    assert len(console.tables) == 1
    _, _, title = console.tables[0]
    assert "all" in title


def test_list_images_invalid_type(capsys):
    commands, _, console = build_commands()
    commands.list_images(["unknown"])

    output = capsys.readouterr().out
    assert "Unknown image type" in output
    assert console.tables == []


def test_show_image_info(capsys):
    commands, _, _ = build_commands()
    commands.show_image_info(["42"])

    output = capsys.readouterr().out
    assert "my-snapshot" in output
    assert "ubuntu" in output
    assert "x86" in output


def test_show_image_info_missing_id(capsys):
    commands, _, _ = build_commands()
    commands.show_image_info([])

    output = capsys.readouterr().out
    assert "Missing image ID" in output


def test_show_image_info_not_found(capsys):
    commands, _, _ = build_commands()
    commands.show_image_info(["999"])

    output = capsys.readouterr().out
    # get_image_by_id returns {} for unknown ID — no crash
    assert "Image" not in output or "999" not in output


def test_delete_image_confirmed(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "y")

    commands.delete_image(["42"])

    assert hetzner.delete_calls == [42]


def test_delete_image_cancelled(monkeypatch):
    commands, hetzner, _ = build_commands()
    monkeypatch.setattr("builtins.input", lambda _: "n")

    commands.delete_image(["42"])

    assert hetzner.delete_calls == []


def test_delete_image_wrong_type(capsys):
    commands, hetzner, _ = build_commands()
    # Change fixture to a system image
    hetzner.snapshot["type"] = "system"

    commands.delete_image(["42"])

    output = capsys.readouterr().out
    assert "system" in output
    assert hetzner.delete_calls == []


def test_update_image_description(monkeypatch):
    commands, hetzner, _ = build_commands()
    # new description, skip labels, no label update
    answers = iter(["new description", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.update_image(["42"])

    assert len(hetzner.update_calls) == 1
    call = hetzner.update_calls[0]
    assert call["id"] == 42
    assert call["description"] == "new description"
    assert call["labels"] is None


def test_update_image_no_changes(monkeypatch, capsys):
    commands, hetzner, _ = build_commands()
    # blank description (keep), no label update
    answers = iter(["", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    commands.update_image(["42"])

    output = capsys.readouterr().out
    assert "No changes" in output
    assert hetzner.update_calls == []


def test_update_image_missing_id(capsys):
    commands, _, _ = build_commands()
    commands.update_image([])

    output = capsys.readouterr().out
    assert "Missing image ID" in output


def test_import_delegates_to_vm_commands():
    commands, _, console = build_commands()
    commands.handle_command(["import", "https://example.com/img.raw"])

    assert console.vm_commands.import_calls == [["https://example.com/img.raw"]]
