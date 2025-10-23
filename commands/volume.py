#!/usr/bin/env python3
# commands/volume.py - Volume-related commands for hicloud

from typing import List
from utils.formatting import format_size

class VolumeCommands:
    """Volume-related commands for Interactive Console"""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle volume-related commands"""
        if not args:
            print("Missing volume subcommand. Use 'volume list|info|create|delete|attach|detach|resize|protect'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_volumes()
        elif subcommand == "info":
            self.show_volume_info(args[1:])
        elif subcommand == "create":
            self.create_volume()
        elif subcommand == "delete":
            self.delete_volume(args[1:])
        elif subcommand == "attach":
            self.attach_volume(args[1:])
        elif subcommand == "detach":
            self.detach_volume(args[1:])
        elif subcommand == "resize":
            self.resize_volume(args[1:])
        elif subcommand == "protect":
            self.protect_volume(args[1:])
        else:
            print(f"Unknown volume subcommand: {subcommand}")

    def list_volumes(self):
        """List all volumes"""
        volumes = self.hetzner.list_volumes()

        if not volumes:
            print("No volumes found")
            return

        # Daten für die Tabelle vorbereiten
        headers = ["ID", "Name", "Size", "Status", "Server", "Location", "Format", "Protection"]
        rows = []

        for volume in volumes:
            volume_id = volume.get('id', 'N/A')
            name = volume.get('name', 'N/A')
            size = volume.get('size', 0)
            formatted_size = f"{size} GB"
            status = volume.get('status', 'N/A')

            # Server-Information
            server_id = volume.get('server')
            if server_id:
                server = self.hetzner.get_server_by_id(server_id)
                server_name = server.get('name', f'ID:{server_id}') if server else f'ID:{server_id}'
            else:
                server_name = "detached"

            # Location
            location = volume.get('location', {}).get('name', 'N/A')

            # Format
            volume_format = volume.get('format', 'N/A')
            if not volume_format:
                volume_format = 'N/A'

            # Protection
            protection = volume.get('protection', {})
            delete_protected = "Yes" if protection.get('delete', False) else "No"

            rows.append([
                volume_id,
                name,
                formatted_size,
                status,
                server_name,
                location,
                volume_format,
                delete_protected
            ])

        # Tabelle drucken
        self.console.print_table(headers, rows, "Volumes")

    def show_volume_info(self, args: List[str]):
        """Show detailed information about a specific volume"""
        if not args:
            print("Missing volume ID. Use 'volume info <id>'")
            return

        try:
            volume_id = int(args[0])
        except ValueError:
            print("Invalid volume ID. Must be an integer.")
            return

        volume = self.hetzner.get_volume_by_id(volume_id)

        if not volume:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Volume Information: \033[1;32m{volume.get('name')}\033[0m (ID: {volume_id})")
        print(f"{self.console.horizontal_line('=')}")

        # Grundlegende Informationen
        status = volume.get('status', 'unknown')
        status_color = "\033[1;32m" if status == "available" else "\033[1;33m"
        print(f"Status: {status_color}{status}\033[0m")

        created = volume.get('created', 'unknown')
        if created != 'unknown':
            created_date = created.split('T')[0]
            created_time = created.split('T')[1].split('+')[0] if '+' in created else created.split('T')[1].split('Z')[0]
            print(f"Created: {created_date} {created_time}")

        # Size Information
        size = volume.get('size', 0)
        print(f"\nSize: {size} GB")

        # Location
        location = volume.get('location', {})
        print(f"\nLocation:")
        print(f"  Name: {location.get('name', 'N/A')}")
        print(f"  City: {location.get('city', 'N/A')}")
        print(f"  Country: {location.get('country', 'N/A')}")

        # Server attachment
        server_id = volume.get('server')
        if server_id:
            server = self.hetzner.get_server_by_id(server_id)
            if server:
                print(f"\nAttached to Server:")
                print(f"  ID: {server_id}")
                print(f"  Name: {server.get('name', 'N/A')}")
                print(f"  Device: {volume.get('linux_device', 'N/A')}")
        else:
            print(f"\nAttached to Server: Not attached")

        # Format
        volume_format = volume.get('format')
        if volume_format:
            print(f"\nFilesystem: {volume_format}")

        # Protection
        protection = volume.get('protection', {})
        delete_protected = "Enabled" if protection.get('delete', False) else "Disabled"
        print(f"\nProtection:")
        print(f"  Delete Protection: {delete_protected}")

        # Labels
        labels = volume.get('labels', {})
        if labels:
            print(f"\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")

        print(f"{self.console.horizontal_line('-')}")

    def create_volume(self):
        """Create a new volume (interactive)"""
        print("Create a new Volume:")
        name = input("Volume Name: ")
        if not name:
            print("Volume name is required")
            return

        # Get size
        size_input = input("Size in GB (minimum 10): ")
        try:
            size = int(size_input)
            if size < 10:
                print("Minimum volume size is 10 GB")
                return
        except ValueError:
            print("Invalid size. Must be an integer.")
            return

        # Option 1: Create standalone volume
        # Option 2: Create and attach to server
        print("\nCreation Options:")
        print("1. Create standalone volume (not attached)")
        print("2. Create and attach to a server")

        option = input("\nSelect option (1 or 2): ").strip()

        server_id = None
        format_volume = None
        location = None

        if option == "2":
            # Get list of servers
            servers = self.hetzner.list_servers()
            if not servers:
                print("No servers available. Creating standalone volume.")
                option = "1"
            else:
                print("\nAvailable Servers:")
                for i, server in enumerate(servers):
                    print(f"{i+1}. {server['name']} (ID: {server['id']}) - {server.get('datacenter', {}).get('location', {}).get('name', 'N/A')}")

                server_choice = input("\nSelect server (number): ")
                try:
                    server_index = int(server_choice) - 1
                    if server_index < 0 or server_index >= len(servers):
                        print("Invalid selection")
                        return
                    server_id = servers[server_index]['id']

                    # Ask for filesystem format
                    print("\nFilesystem Format:")
                    print("1. xfs (recommended)")
                    print("2. ext4")
                    print("3. None (format manually later)")

                    format_choice = input("\nSelect format (1, 2, or 3): ").strip()
                    if format_choice == "1":
                        format_volume = "xfs"
                    elif format_choice == "2":
                        format_volume = "ext4"

                except ValueError:
                    print("Invalid input")
                    return

        if option == "1" or server_id is None:
            # Get available locations
            status_code, response = self.hetzner._make_request("GET", "locations")
            if status_code != 200:
                print("Failed to get locations")
                return

            locations = response.get("locations", [])
            print("\nAvailable Locations:")
            for i, loc in enumerate(locations):
                print(f"{i+1}. {loc['name']} ({loc['description']})")

            location_choice = input("\nSelect location (number): ")
            try:
                location_index = int(location_choice) - 1
                if location_index < 0 or location_index >= len(locations):
                    print("Invalid selection")
                    return
                location = locations[location_index]["name"]
            except ValueError:
                print("Invalid input")
                return

        # Optional labels
        labels = {}
        add_labels = input("\nDo you want to add labels? [y/N]: ").strip().lower()
        if add_labels == 'y':
            while True:
                key = input("Label key (or press Enter to finish): ").strip()
                if not key:
                    break
                value = input(f"Label value for '{key}': ").strip()
                labels[key] = value

        # Final confirmation
        print("\nVolume Creation Summary:")
        print(f"  Name: {name}")
        print(f"  Size: {size} GB")
        if server_id:
            print(f"  Attach to Server: ID {server_id}")
            if format_volume:
                print(f"  Format: {format_volume}")
        else:
            print(f"  Location: {location}")
        if labels:
            print(f"  Labels: {labels}")

        confirm = input("\nCreate this volume? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print("Creating volume...")

        # Volume erstellen
        volume = self.hetzner.create_volume(
            name=name,
            size=size,
            location=location,
            server_id=server_id,
            format_volume=format_volume,
            labels=labels if labels else None
        )

        if volume:
            print(f"\nVolume created successfully!")
            print(f"ID: {volume.get('id')}")
            print(f"Name: {volume.get('name')}")
            print(f"Size: {volume.get('size')} GB")
            print(f"Status: {volume.get('status')}")
            if server_id:
                print(f"Attached to Server: ID {server_id}")
                print(f"Linux Device: {volume.get('linux_device', 'N/A')}")
        else:
            print(f"Failed to create volume")

    def delete_volume(self, args: List[str]):
        """Delete a volume by ID"""
        if not args:
            print("Missing volume ID. Use 'volume delete <id>'")
            return

        try:
            volume_id = int(args[0])
        except ValueError:
            print("Invalid volume ID. Must be an integer.")
            return

        volume = self.hetzner.get_volume_by_id(volume_id)

        if not volume:
            return

        # Check if volume is attached
        if volume.get('server'):
            print(f"WARNING: Volume '{volume.get('name')}' is currently attached to a server.")
            print("You must detach it first before deletion.")
            detach_now = input("Do you want to detach it now? [y/N]: ")
            if detach_now.lower() == 'y':
                print(f"Detaching volume {volume_id}...")
                if not self.hetzner.detach_volume(volume_id):
                    print("Failed to detach volume. Cannot delete.")
                    return
            else:
                print("Operation cancelled")
                return

        confirm = input(f"Are you sure you want to delete volume '{volume.get('name')}' (ID: {volume_id})? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Deleting volume {volume_id}...")
        if self.hetzner.delete_volume(volume_id):
            print(f"Volume {volume_id} deleted successfully")
        else:
            print(f"Failed to delete volume {volume_id}")

    def attach_volume(self, args: List[str]):
        """Attach a volume to a server"""
        if len(args) < 2:
            print("Missing parameters. Use 'volume attach <volume_id> <server_id>'")
            return

        try:
            volume_id = int(args[0])
            server_id = int(args[1])
        except ValueError:
            print("Invalid ID format. Both volume ID and server ID must be integers.")
            return

        # Get volume details
        volume = self.hetzner.get_volume_by_id(volume_id)
        if not volume:
            return

        # Check if already attached
        if volume.get('server'):
            current_server = volume.get('server')
            print(f"Volume '{volume.get('name')}' is already attached to server ID {current_server}")
            return

        # Get server details
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        # Ask about automount
        automount = input("Enable automount? [y/N]: ").strip().lower() == 'y'

        print(f"Attaching volume '{volume.get('name')}' to server '{server.get('name')}'...")
        if self.hetzner.attach_volume(volume_id, server_id, automount):
            print(f"Volume {volume_id} successfully attached to server {server_id}")

            # Show device path
            updated_volume = self.hetzner.get_volume_by_id(volume_id)
            if updated_volume:
                device = updated_volume.get('linux_device', 'N/A')
                print(f"Linux device: {device}")
        else:
            print(f"Failed to attach volume {volume_id}")

    def detach_volume(self, args: List[str]):
        """Detach a volume from its server"""
        if not args:
            print("Missing volume ID. Use 'volume detach <id>'")
            return

        try:
            volume_id = int(args[0])
        except ValueError:
            print("Invalid volume ID. Must be an integer.")
            return

        # Get volume details
        volume = self.hetzner.get_volume_by_id(volume_id)
        if not volume:
            return

        # Check if attached
        if not volume.get('server'):
            print(f"Volume '{volume.get('name')}' is not attached to any server")
            return

        server_id = volume.get('server')
        server = self.hetzner.get_server_by_id(server_id)
        server_name = server.get('name', f'ID:{server_id}') if server else f'ID:{server_id}'

        print(f"WARNING: Make sure the volume is properly unmounted on the server before detaching!")
        confirm = input(f"Detach volume '{volume.get('name')}' from server '{server_name}'? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Detaching volume {volume_id}...")
        if self.hetzner.detach_volume(volume_id):
            print(f"Volume {volume_id} successfully detached")
        else:
            print(f"Failed to detach volume {volume_id}")

    def resize_volume(self, args: List[str]):
        """Resize a volume"""
        if len(args) < 2:
            print("Missing parameters. Use 'volume resize <id> <new_size_gb>'")
            return

        try:
            volume_id = int(args[0])
            new_size = int(args[1])
        except ValueError:
            print("Invalid format. Both volume ID and size must be integers.")
            return

        if new_size < 10:
            print("Minimum volume size is 10 GB")
            return

        # Get volume details
        volume = self.hetzner.get_volume_by_id(volume_id)
        if not volume:
            return

        current_size = volume.get('size', 0)

        if new_size <= current_size:
            print(f"New size ({new_size} GB) must be larger than current size ({current_size} GB)")
            print("Volumes can only be increased in size, not decreased.")
            return

        print(f"\nWARNING:")
        print(f"You are about to resize volume '{volume.get('name')}' from {current_size} GB to {new_size} GB")
        print("After resizing, you need to extend the filesystem manually on the server.")

        if volume.get('server'):
            print("\nThe volume is currently attached to a server.")
            print("It's recommended to unmount the volume before resizing.")

        confirm = input(f"\nResize volume '{volume.get('name')}' to {new_size} GB? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Resizing volume {volume_id} to {new_size} GB...")
        if self.hetzner.resize_volume(volume_id, new_size):
            print(f"Volume {volume_id} successfully resized to {new_size} GB")
            print("\nDon't forget to extend the filesystem on your server:")
            print("  For ext4: resize2fs /dev/sdX")
            print("  For xfs: xfs_growfs /mount/point")
        else:
            print(f"Failed to resize volume {volume_id}")

    def protect_volume(self, args: List[str]):
        """Enable or disable volume protection"""
        if len(args) < 2:
            print("Missing parameters. Use 'volume protect <id> <enable|disable>'")
            return

        try:
            volume_id = int(args[0])
        except ValueError:
            print("Invalid volume ID. Must be an integer.")
            return

        action = args[1].lower()
        if action not in ['enable', 'disable']:
            print("Action must be 'enable' or 'disable'")
            return

        enable_protection = (action == 'enable')

        # Get volume details
        volume = self.hetzner.get_volume_by_id(volume_id)
        if not volume:
            return

        action_text = "enable" if enable_protection else "disable"
        confirm = input(f"{action_text.capitalize()} delete protection for volume '{volume.get('name')}'? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"{action_text.capitalize()}ing protection for volume {volume_id}...")
        if self.hetzner.change_volume_protection(volume_id, delete=enable_protection):
            print(f"Delete protection {action}d for volume {volume_id}")
        else:
            print(f"Failed to {action} protection for volume {volume_id}")
