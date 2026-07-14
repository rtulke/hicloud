#!/usr/bin/env python3
# commands/action.py - Action-related commands for hicloud

from typing import Dict, List

from commands.base import BaseCommands


class ActionCommands(BaseCommands):
    """Action-related commands for Interactive Console.

    Note: the Hetzner Cloud API has no endpoint to cancel actions, so this
    module intentionally only offers listing and inspection.
    """

    label = "action"
    usage = "action list [running|success|error] | action info <id>"

    def _build_actions(self):
        return {
            "list": self.list_actions,
            "info": self.show_action_info,
        }

    def list_actions(self, args: List[str]):
        """List actions, optionally filtered by status."""
        status = None
        if args:
            status = args[0].lower()
            if status not in ("running", "success", "error"):
                print("Unknown status filter. Use 'action list [running|success|error]'")
                return

        actions = self.hetzner.list_actions(status)
        if not actions:
            print(f"No actions found (status: {status or 'any'})")
            return

        headers = ["ID", "Command", "Status", "Progress", "Started", "Finished", "Resources"]
        rows = []
        for action in sorted(actions, key=lambda x: x.get("id", 0), reverse=True):
            rows.append([
                action.get("id", "N/A"),
                action.get("command", "N/A"),
                action.get("status", "N/A"),
                f"{action.get('progress', 0)}%",
                self._format_time(action.get("started")),
                self._format_time(action.get("finished")),
                self._format_resources(action.get("resources", [])),
            ])

        title = f"Actions ({status})" if status else "Actions"
        self.console.print_table(headers, rows, title)

    def show_action_info(self, args: List[str]):
        """Show detailed information about an action."""
        action_id = self.parse_id(args, "action ID", "action info <id>")
        if action_id is None:
            return

        action = self.hetzner.get_action_by_id(action_id)
        if not action:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Action: \033[1;32m{action.get('command', 'N/A')}\033[0m (ID: {action.get('id')})")
        print(f"{self.console.horizontal_line('=')}")
        print(f"Status:    {action.get('status', 'N/A')}")
        print(f"Progress:  {action.get('progress', 0)}%")
        print(f"Started:   {self._format_time(action.get('started'))}")
        print(f"Finished:  {self._format_time(action.get('finished'))}")

        resources = action.get("resources", [])
        if resources:
            print("\nResources:")
            for resource in resources:
                print(f"  - {resource.get('type', 'N/A')}: {resource.get('id', 'N/A')}")

        error = action.get("error")
        if error:
            print("\nError:")
            print(f"  Code:    {error.get('code', 'N/A')}")
            print(f"  Message: {error.get('message', 'N/A')}")

        print(f"{self.console.horizontal_line('-')}")

    @staticmethod
    def _format_time(value) -> str:
        """Compact ISO timestamp rendering ('-' when unset)."""
        if not value:
            return "-"
        return str(value).replace("T", " ")[:19]

    @staticmethod
    def _format_resources(resources: List[Dict]) -> str:
        """Render affected resources as 'type:id' pairs."""
        if not resources:
            return "-"
        return ", ".join(f"{r.get('type', '?')}:{r.get('id', '?')}" for r in resources)
