#!/usr/bin/env python3
# commands/config.py - Config validation and info commands for hicloud

import os
import re
import stat
import toml
from typing import List

from lib.config import ConfigManager
from utils.constants import DEFAULT_CONFIG_PATH


class ConfigCommands:
    """Config management commands for Interactive Console."""

    def __init__(self, console):
        """Initialize with reference to the console."""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle config-related commands."""
        if not args:
            print("Missing config subcommand. Use 'config validate|info'")
            return

        subcommand = args[0].lower()

        if subcommand == "validate":
            self.validate_config(args[1:])
        elif subcommand == "info":
            self.show_config_info()
        else:
            print(f"Unknown config subcommand: {subcommand}")

    def validate_config(self, args: List[str]):
        """Validate the config file: existence, permissions, required fields, token format."""
        config_path = args[0] if args else DEFAULT_CONFIG_PATH

        errors = []
        warnings = []

        print(f"Validating config: {config_path}")

        # 1. File existence
        if not os.path.exists(config_path):
            print(f"\n  ERROR: Config file not found: {config_path}")
            print("\nResult: FAILED (1 error)")
            return

        # 2. File permissions (must be 600)
        has_correct_perms = ConfigManager.check_file_permissions(config_path)
        if not has_correct_perms:
            file_mode = os.stat(config_path).st_mode
            octal = oct(file_mode & 0o777)
            warnings.append(f"Insecure file permissions {octal} — expected 0o600. Run: chmod 600 {config_path}")

        # 3. Parse TOML
        try:
            data = toml.load(config_path)
        except Exception as e:
            errors.append(f"TOML parse error: {e}")
            self._print_result(errors, warnings)
            return

        if not data:
            warnings.append("Config file is empty — no project sections defined")
            self._print_result(errors, warnings)
            return

        # 4. Validate sections
        for section_name, section in data.items():
            if not isinstance(section, dict):
                errors.append(f"[{section_name}] is not a table/dict")
                continue

            if "api_token" not in section:
                errors.append(f"[{section_name}] missing required field: api_token")
            else:
                token = section["api_token"]
                if not self._is_valid_token(token):
                    warnings.append(f"[{section_name}] api_token format looks suspicious (should be ~64 chars, alphanumeric)")

            if "project_name" not in section:
                errors.append(f"[{section_name}] missing required field: project_name")

        self._print_result(errors, warnings)

    def _is_valid_token(self, token: str) -> bool:
        """Basic sanity check for a Hetzner API token."""
        if not isinstance(token, str):
            return False
        if len(token) < 32 or len(token) > 128:
            return False
        if not re.match(r'^[A-Za-z0-9_\-]+$', token):
            return False
        return True

    def _print_result(self, errors: List[str], warnings: List[str]):
        """Print validation summary."""
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  WARNING: {w}")

        if errors:
            print("\nErrors:")
            for e in errors:
                print(f"  ERROR: {e}")
            print(f"\nResult: FAILED ({len(errors)} error(s), {len(warnings)} warning(s))")
        else:
            print(f"\nResult: OK ({len(warnings)} warning(s))")

    def show_config_info(self):
        """Show active config path, project sections, and current session info."""
        print(f"Config Path:     {DEFAULT_CONFIG_PATH}")

        exists = os.path.exists(DEFAULT_CONFIG_PATH)
        print(f"File Exists:     {'yes' if exists else 'no'}")

        if exists:
            has_correct_perms = ConfigManager.check_file_permissions(DEFAULT_CONFIG_PATH)
            file_mode = os.stat(DEFAULT_CONFIG_PATH).st_mode
            octal = oct(file_mode & 0o777)
            perm_label = f"{octal} ({'OK' if has_correct_perms else 'WARNING: should be 0o600'})"
            print(f"Permissions:     {perm_label}")

            try:
                data = toml.load(DEFAULT_CONFIG_PATH)
                sections = list(data.keys())
                print(f"Projects ({len(sections)}):   {', '.join(sections) if sections else '(none)'}")
            except Exception as e:
                print(f"Parse Error:     {e}")

        print(f"\nActive Project:  {self.hetzner.project_name}")
        token_preview = self.hetzner.api_token[:8] + "..." if self.hetzner.api_token else "(none)"
        print(f"API Token:       {token_preview}")
