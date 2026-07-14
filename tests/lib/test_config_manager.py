#!/usr/bin/env python3

import os

from lib.config import ConfigManager


def _write_config(tmp_path, mode):
    path = tmp_path / "hicloud.toml"
    path.write_text('[default]\napi_token = "abc"\nproject_name = "default"\n')
    os.chmod(path, mode)
    return str(path)


def test_permissions_600_accepted(tmp_path):
    path = _write_config(tmp_path, 0o600)
    assert ConfigManager.check_file_permissions(path) is True


def test_permissions_400_accepted(tmp_path):
    path = _write_config(tmp_path, 0o400)
    assert ConfigManager.check_file_permissions(path) is True


def test_permissions_group_or_world_readable_rejected(tmp_path):
    # These all passed the old check because it only masked the user bits.
    for mode in (0o644, 0o664, 0o666, 0o604, 0o640):
        path = _write_config(tmp_path, mode)
        assert ConfigManager.check_file_permissions(path) is False, oct(mode)


def test_permissions_user_executable_rejected(tmp_path):
    path = _write_config(tmp_path, 0o700)
    assert ConfigManager.check_file_permissions(path) is False


def test_permissions_missing_file_rejected(tmp_path):
    assert ConfigManager.check_file_permissions(str(tmp_path / "nope.toml")) is False


def test_load_config_reads_secure_file(tmp_path):
    path = _write_config(tmp_path, 0o600)
    config = ConfigManager.load_config(path)
    assert config["default"]["api_token"] == "abc"


def test_load_config_refuses_insecure_file(tmp_path, capsys):
    path = _write_config(tmp_path, 0o644)
    config = ConfigManager.load_config(path)
    assert config == {}
    assert "Insecure permissions" in capsys.readouterr().out


def test_generate_config_sets_secure_permissions(tmp_path):
    path = str(tmp_path / "generated.toml")
    assert ConfigManager.generate_config(path) is True
    assert ConfigManager.check_file_permissions(path) is True
