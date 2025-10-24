#!/usr/bin/env python3
# commands/iso.py - ISO-related commands for hicloud

from typing import List
from utils.formatting import format_size

class ISOCommands:
    """ISO-related commands for Interactive Console"""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle ISO-related commands"""
        if not args:
            print("Missing iso subcommand. Use 'iso list|info|attach|detach'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_isos()
        elif subcommand == "info":
            self.iso_info(args[1:])
        elif subcommand == "attach":
            self.attach_iso(args[1:])
        elif subcommand == "detach":
            self.detach_iso(args[1:])
        else:
            print(f"Unknown iso subcommand: {subcommand}")

    def list_isos(self):
        """List all available ISOs"""
        isos = self.hetzner.list_isos()

        if not isos:
            print("No ISOs found")
            return

        print("\nAvailable ISOs:")
        print(f"{'ID':<10} {'Name':<50} {'Type':<15} {'Architecture':<15}")
        print("-" * 90)

        # Sort ISOs by name
        for iso in sorted(isos, key=lambda x: x.get('name', '').lower()):
            iso_id = iso.get('id', 'N/A')
            name = iso.get('name', 'N/A')
            iso_type = iso.get('type', 'N/A')
            architecture = iso.get('architecture', 'N/A')

            print(f"{iso_id:<10} {name:<50} {iso_type:<15} {architecture:<15}")

    def iso_info(self, args: List[str]):
        """Show detailed information about an ISO"""
        if not args:
            print("Missing ISO ID. Use 'iso info <id>'")
            return

        try:
            iso_id = int(args[0])
        except ValueError:
            print("Invalid ISO ID. Must be an integer.")
            return

        iso = self.hetzner.get_iso_by_id(iso_id)

        if not iso:
            # Error message is already printed in get_iso_by_id
            return

        print(f"\nISO Details:")
        print(f"  ID:           {iso.get('id', 'N/A')}")
        print(f"  Name:         {iso.get('name', 'N/A')}")
        print(f"  Description:  {iso.get('description', 'N/A')}")
        print(f"  Type:         {iso.get('type', 'N/A')}")
        print(f"  Architecture: {iso.get('architecture', 'N/A')}")

        # Show deprecation info if available
        if iso.get('deprecated'):
            deprecation = iso.get('deprecated')
            print(f"  Deprecated:   {deprecation}")

    def attach_iso(self, args: List[str]):
        """Attach an ISO to a server"""
        if len(args) < 2:
            print("Missing arguments. Use 'iso attach <iso_id> <server_id>'")
            return

        try:
            iso_id = int(args[0])
            server_id = int(args[1])
        except ValueError:
            print("Invalid ID. Both ISO ID and Server ID must be integers.")
            return

        # Verify ISO exists
        iso = self.hetzner.get_iso_by_id(iso_id)
        if not iso:
            return

        # Verify server exists
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        print(f"Attaching ISO '{iso.get('name')}' to server '{server.get('name')}'...")
        if self.hetzner.attach_iso_to_server(server_id, iso_id):
            print(f"ISO attached successfully")
        else:
            print(f"Failed to attach ISO")

    def detach_iso(self, args: List[str]):
        """Detach an ISO from a server"""
        if not args:
            print("Missing server ID. Use 'iso detach <server_id>'")
            return

        try:
            server_id = int(args[0])
        except ValueError:
            print("Invalid server ID. Must be an integer.")
            return

        # Verify server exists
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        # Check if an ISO is attached
        if not server.get('iso'):
            print(f"No ISO is attached to server '{server.get('name')}'")
            return

        iso_name = server.get('iso', {}).get('name', 'Unknown')
        print(f"Detaching ISO '{iso_name}' from server '{server.get('name')}'...")
        if self.hetzner.detach_iso_from_server(server_id):
            print(f"ISO detached successfully")
        else:
            print(f"Failed to detach ISO")
