#!/usr/bin/env python3
# commands/placement_group.py - Placement group commands for hicloud

from typing import List

from commands.base import BaseCommands


class PlacementGroupCommands(BaseCommands):
    """Placement group management commands for Interactive Console."""

    label = "placement-group"
    usage = "placement-group list|info|create|update|delete|add|remove"

    def _build_actions(self):
        return {
            "list": lambda args: self.list_groups(),
            "info": self.show_group_info,
            "create": lambda args: self.create_group(),
            "update": self.update_group,
            "delete": self.delete_group,
            "add": self.add_server,
            "remove": self.remove_server,
        }

    # ------------------------------------------------------------------ list

    def list_groups(self):
        """List all placement groups."""
        groups = self.hetzner.list_placement_groups()
        if not groups:
            print("No placement groups found")
            return

        headers = ["ID", "Name", "Type", "Servers", "Created"]
        rows = []
        for group in sorted(groups, key=lambda x: x.get("name", "").lower()):
            created = group.get("created", "N/A")
            if created != "N/A":
                created = created.split("T")[0]
            rows.append([
                group.get("id", "N/A"),
                group.get("name", "N/A"),
                group.get("type", "N/A"),
                len(group.get("servers", [])),
                created,
            ])

        self.console.print_table(headers, rows, "Placement Groups")

    # ------------------------------------------------------------------ info

    def show_group_info(self, args: List[str]):
        """Show detailed information about a placement group."""
        group = self._resolve(args, "placement-group info <id>")
        if not group:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Placement Group: \033[1;32m{group.get('name', 'N/A')}\033[0m (ID: {group.get('id')})")
        print(f"{self.console.horizontal_line('=')}")
        print(f"Type:    {group.get('type', 'N/A')}")
        print(f"Created: {group.get('created', 'N/A')}")

        servers = group.get("servers", [])
        if servers:
            print(f"\nServers ({len(servers)}):")
            for server_id in servers:
                print(f"  - Server ID: {server_id}")
        else:
            print("\nServers: None")

        labels = group.get("labels", {})
        if labels:
            print("\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")

        print(f"{self.console.horizontal_line('-')}")

    # ----------------------------------------------------------------- create

    def create_group(self):
        """Create a new placement group (interactive)."""
        print("Create a new Placement Group:")

        name = input("Placement Group Name: ").strip()
        if not name:
            print("Placement group name is required")
            return

        # Hetzner bietet derzeit nur den Typ 'spread' an
        print("Type: spread (only type offered by the Hetzner API)")

        labels = self.prompt_labels()

        print("\nPlacement Group Creation Summary:")
        print(f"  Name: {name}")
        print("  Type: spread")
        if labels:
            print(f"  Labels: {labels}")

        if not self.confirm("\nCreate this placement group?"):
            return

        group = self.hetzner.create_placement_group(name, "spread", labels if labels else None)
        if group:
            print("\nPlacement group created successfully!")
            print(f"ID:   {group.get('id')}")
            print(f"Name: {group.get('name')}")
        else:
            print("Failed to create placement group")

    # ----------------------------------------------------------------- update

    def update_group(self, args: List[str]):
        """Update placement group metadata (name and/or labels)."""
        group = self._resolve(args, "placement-group update <id>")
        if not group:
            return

        group_id = group.get("id")
        print(f"\nUpdating Placement Group: \033[1;32m{group.get('name')}\033[0m (ID: {group_id})")
        print(f"{self.console.horizontal_line('-')}")

        new_name = input(f"New name (leave empty to keep '{group.get('name')}'): ").strip() or None

        new_labels = None
        if input("\nUpdate labels? [y/N]: ").strip().lower() == "y":
            current_labels = group.get("labels", {})
            if current_labels:
                print("\nCurrent labels:")
                for key, value in current_labels.items():
                    print(f"  {key}: {value}")
            print("\nEnter new labels (this will replace all existing labels):")
            new_labels = self.prompt_labels(ask_first=False)

        if new_name is None and new_labels is None:
            print("\nNo changes made.")
            return

        if not self.confirm("\nApply these changes?"):
            return

        updated = self.hetzner.update_placement_group(group_id, name=new_name, labels=new_labels)
        if updated:
            print(f"Placement group {group_id} updated successfully")
        else:
            print(f"Failed to update placement group {group_id}")

    # ----------------------------------------------------------------- delete

    def delete_group(self, args: List[str]):
        """Delete a placement group by ID."""
        group = self._resolve(args, "placement-group delete <id>")
        if not group:
            return

        group_id = group.get("id")
        servers = group.get("servers", [])
        if servers:
            print(f"ERROR: Placement group '{group.get('name')}' still contains {len(servers)} server(s).")
            print("Remove them first:  placement-group remove <server_id>")
            return

        if not self.confirm(f"Are you sure you want to delete placement group '{group.get('name')}' (ID: {group_id})?"):
            return

        if self.hetzner.delete_placement_group(group_id):
            print(f"Placement group {group_id} deleted successfully")
        else:
            print(f"Failed to delete placement group {group_id}")

    # -------------------------------------------------------------------- add

    def add_server(self, args: List[str]):
        """Add a server to a placement group (server must be powered off)."""
        if len(args) < 2:
            print("Missing parameters. Use 'placement-group add <id> <server_id>'")
            return

        group = self._resolve([args[0]], "placement-group add <id> <server_id>")
        if not group:
            return

        server_id = self.parse_id(args[1:], "server ID", "placement-group add <id> <server_id>")
        if server_id is None:
            return

        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        if server.get("placement_group"):
            current = server["placement_group"]
            print(f"ERROR: Server '{server.get('name')}' is already in placement group "
                  f"'{current.get('name')}' (ID: {current.get('id')}).")
            print(f"Remove it first:  placement-group remove {server_id}")
            return

        if server.get("status") == "running":
            print(f"ERROR: Server '{server.get('name')}' is running. Adding a server to a "
                  "placement group requires it to be powered off.")
            print(f"Stop it first:  vm stop {server_id}")
            return

        group_id = group.get("id")
        if not self.confirm(f"Add server '{server.get('name')}' (ID: {server_id}) to placement group "
                            f"'{group.get('name')}' (ID: {group_id})?"):
            return

        if self.hetzner.add_server_to_placement_group(server_id, group_id):
            print(f"Server {server_id} added to placement group {group_id}")
        else:
            print(f"Failed to add server {server_id} to placement group {group_id}")

    # ----------------------------------------------------------------- remove

    def remove_server(self, args: List[str]):
        """Remove a server from its placement group."""
        server_id = self.parse_id(args, "server ID", "placement-group remove <server_id>")
        if server_id is None:
            return

        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        group = server.get("placement_group")
        if not group:
            print(f"Server '{server.get('name')}' is not in any placement group.")
            return

        if not self.confirm(f"Remove server '{server.get('name')}' (ID: {server_id}) from placement group "
                            f"'{group.get('name')}' (ID: {group.get('id')})?"):
            return

        if self.hetzner.remove_server_from_placement_group(server_id):
            print(f"Server {server_id} removed from its placement group")
        else:
            print(f"Failed to remove server {server_id} from its placement group")

    # ------------------------------------------------------------ helpers

    def _resolve(self, args: List[str], usage: str):
        group_id = self.parse_id(args, "placement group ID", usage)
        if group_id is None:
            return None
        group = self.hetzner.get_placement_group_by_id(group_id)
        return group if group else None
