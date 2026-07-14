#!/usr/bin/env python3
# commands/base.py - Shared base class for command handlers

from typing import Callable, Dict, List, Optional


class BaseCommands:
    """Common dispatch and input-parsing helpers for command handlers.

    Subclasses set `label` (the casing used in Missing/Unknown messages,
    e.g. "VM" or "iso"), `usage` (the subcommand summary shown when no
    subcommand is given) and implement `_build_actions()` returning a
    mapping of subcommand name to a callable taking the remaining args.
    """

    label = "command"
    usage = ""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
        self.actions: Dict[str, Callable[[List[str]], None]] = self._build_actions()

    def _build_actions(self) -> Dict[str, Callable[[List[str]], None]]:
        raise NotImplementedError

    def handle_command(self, args: List[str]):
        """Dispatch to the subcommand handler registered in _build_actions()."""
        if not args:
            print(f"Missing {self.label} subcommand. Use '{self.usage}'")
            return

        action = self.actions.get(args[0].lower())
        if action is None:
            print(f"Unknown {self.label} subcommand: {args[0].lower()}")
            return

        action(args[1:])

    @staticmethod
    def parse_id(args: List[str], label: str, usage: str) -> Optional[int]:
        """Parse the leading argument as an integer ID with standard messages."""
        if not args:
            print(f"Missing {label}. Use '{usage}'")
            return None
        try:
            return int(args[0])
        except ValueError:
            print(f"Invalid {label}. Must be an integer.")
            return None

    @staticmethod
    def confirm(question: str) -> bool:
        """Standard [y/N] confirmation; prints 'Operation cancelled' on decline."""
        if input(f"{question} [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return False
        return True

    @staticmethod
    def prompt_labels(ask_first: bool = True) -> Dict[str, str]:
        """Interactively collect key/value labels."""
        labels: Dict[str, str] = {}
        if ask_first:
            if input("\nAdd labels? [y/N]: ").strip().lower() != "y":
                return labels
        while True:
            key = input("Label key (or press Enter to finish): ").strip()
            if not key:
                break
            labels[key] = input(f"Label value for '{key}': ").strip()
        return labels
