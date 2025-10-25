#!/usr/bin/env python3
# commands/keys.py - SSH key-related commands for hicloud

import os
import re
from typing import List

class KeysCommands:
    """SSH key-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle SSH key-related commands"""
        if not args:
            print("Missing keys subcommand. Use 'keys list|info|create|update|delete'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_keys()
        elif subcommand == "info":
            self.show_key_info(args[1:])
        elif subcommand == "create":
            self.create_key(args[1:])
        elif subcommand == "update":
            self.update_key(args[1:])
        elif subcommand == "delete":
            self.delete_key(args[1:])
        else:
            print(f"Unknown keys subcommand: {subcommand}")
    
    def list_keys(self):
        """List all SSH keys"""
        ssh_keys = self.hetzner.list_ssh_keys()

        if not ssh_keys:
            print("No SSH keys found")
            return

        # Prepare data for table
        headers = ["ID", "Name", "Fingerprint", "Created"]
        rows = []

        # Sort keys alphabetically by name
        for key in sorted(ssh_keys, key=lambda x: x.get('name', '').lower()):
            fingerprint = key.get('fingerprint', 'N/A')
            created = key.get('created', 'N/A')

            # Format the creation date if it exists
            if created != 'N/A':
                created = created.split('T')[0]

            rows.append([key['id'], key['name'], fingerprint, created])

        # Print table with dynamic column widths
        self.console.print_table(headers, rows, "SSH Keys")
    
    def delete_key(self, args: List[str]):
        """Delete SSH key by ID"""
        if not args:
            print("Missing SSH key ID. Use 'keys delete <id>'")
            return
            
        try:
            key_id = int(args[0])
        except ValueError:
            print("Invalid key ID. Must be an integer.")
            return
            
        key = self.hetzner.get_ssh_key_by_id(key_id)
        
        if not key:
            # Die Fehlermeldung wird bereits in get_ssh_key_by_id ausgegeben
            return
            
        confirm = input(f"Are you sure you want to delete SSH key '{key.get('name')}' (ID: {key_id})? [y/N]: ")
        
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        print(f"Deleting SSH key {key_id}...")
        if self.hetzner.delete_ssh_key(key_id):
            print(f"SSH key {key_id} deleted successfully")
        else:
            print(f"Failed to delete SSH key {key_id}")

    def show_key_info(self, args: List[str]):
        """Show detailed information about an SSH key"""
        if not args:
            print("Missing SSH key ID. Use 'keys info <id>'")
            return

        try:
            key_id = int(args[0])
        except ValueError:
            print("Invalid key ID. Must be an integer.")
            return

        key = self.hetzner.get_ssh_key_by_id(key_id)

        if not key:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"SSH Key Information: \033[1;32m{key.get('name')}\033[0m (ID: {key_id})")
        print(f"{self.console.horizontal_line('=')}")

        # Basic information
        print(f"Fingerprint: {key.get('fingerprint', 'N/A')}")

        created = key.get('created', 'N/A')
        if created != 'N/A':
            created_date = created.split('T')[0]
            created_time = created.split('T')[1].split('+')[0] if '+' in created else created.split('T')[1].split('Z')[0]
            print(f"Created:     {created_date} {created_time}")

        # Extract key type from public key
        public_key = key.get('public_key', '')
        if public_key:
            key_type = public_key.split()[0] if public_key else 'N/A'
            print(f"Key Type:    {key_type}")

        # Labels
        labels = key.get('labels', {})
        if labels:
            print("\nLabels:")
            for label_key, label_value in labels.items():
                print(f"  {label_key}: {label_value}")
        else:
            print("\nLabels: None")

        # Public Key (truncated for display)
        if public_key:
            # Show first 50 and last 20 characters
            if len(public_key) > 80:
                key_display = f"{public_key[:50]}...{public_key[-20:]}"
            else:
                key_display = public_key
            print(f"\nPublic Key: {key_display}")

        # Check which servers use this key
        print("\nUsed by servers:")
        servers = self.hetzner.list_servers()
        servers_using_key = []
        for server in servers:
            server_keys = server.get('ssh_keys', [])
            if key_id in server_keys:
                servers_using_key.append(server)

        if servers_using_key:
            for server in servers_using_key:
                print(f"  - {server.get('name')} (ID: {server.get('id')})")
        else:
            print("  No servers currently using this key")

        print(f"{self.console.horizontal_line('-')}")

    def create_key(self, args: List[str]):
        """Create/upload a new SSH key"""
        print("Create a new SSH Key:")

        # Get name
        if args and not args[0].startswith('--'):
            name = args[0]
            print(f"Name: {name}")
        else:
            name = input("SSH Key Name: ").strip()
            if not name:
                print("Key name is required")
                return

        # Get public key (from file or direct input)
        public_key = None
        key_file = None

        # Check if file path was provided as argument
        if len(args) > 1:
            key_file = args[1]
        else:
            key_input = input("Public Key (paste key or file path): ").strip()

            # Check if it's a file path
            if key_input.startswith('~'):
                key_input = os.path.expanduser(key_input)

            if os.path.isfile(key_input):
                key_file = key_input
            elif key_input.startswith('ssh-'):
                public_key = key_input
            else:
                print("Invalid input. Must be a valid SSH public key or file path.")
                return

        # Read from file if provided
        if key_file:
            try:
                with open(key_file, 'r') as f:
                    public_key = f.read().strip()
                print(f"Loaded key from: {key_file}")
            except Exception as e:
                print(f"Error reading file: {str(e)}")
                return

        # Validate key format
        if not self._validate_ssh_key(public_key):
            print("Invalid SSH public key format.")
            print("Key must start with ssh-rsa, ssh-ed25519, ecdsa-sha2-nistp256, or ecdsa-sha2-nistp384")
            return

        # Optional labels
        labels = {}
        add_labels = input("\nAdd labels? [y/N]: ").strip().lower()
        if add_labels == 'y':
            while True:
                key = input("Label key (or press Enter to finish): ").strip()
                if not key:
                    break
                value = input(f"Label value for '{key}': ").strip()
                labels[key] = value

        # Summary
        print("\nSSH Key Creation Summary:")
        print(f"  Name: {name}")
        print(f"  Key Type: {public_key.split()[0] if public_key else 'Unknown'}")
        if labels:
            print(f"  Labels: {labels}")

        confirm = input("\nCreate this SSH key? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print("Creating SSH key...")

        # Create key
        key = self.hetzner.create_ssh_key(
            name=name,
            public_key=public_key,
            labels=labels if labels else None
        )

        if key:
            print(f"\nSSH key created successfully!")
            print(f"ID:          {key.get('id')}")
            print(f"Name:        {key.get('name')}")
            print(f"Fingerprint: {key.get('fingerprint')}")
        else:
            print(f"Failed to create SSH key")

    def update_key(self, args: List[str]):
        """Update SSH key metadata (name and/or labels)"""
        if not args:
            print("Missing SSH key ID. Use 'keys update <id>'")
            return

        try:
            key_id = int(args[0])
        except ValueError:
            print("Invalid key ID. Must be an integer.")
            return

        # Get current key info
        key = self.hetzner.get_ssh_key_by_id(key_id)

        if not key:
            return

        print(f"\nUpdating SSH Key: \033[1;32m{key.get('name')}\033[0m (ID: {key_id})")
        print(f"{self.console.horizontal_line('-')}")

        # Update name
        new_name = None
        name_input = input(f"New name (leave empty to keep '{key.get('name')}'): ").strip()
        if name_input:
            new_name = name_input

        # Update labels
        update_labels_input = input("\nUpdate labels? [y/N]: ").strip().lower()
        new_labels = None

        if update_labels_input == 'y':
            # Show current labels
            current_labels = key.get('labels', {})
            if current_labels:
                print("\nCurrent labels:")
                for k, v in current_labels.items():
                    print(f"  {k}: {v}")

            print("\nEnter new labels (this will replace all existing labels):")
            new_labels = {}
            while True:
                label_key = input("Label key (or press Enter to finish): ").strip()
                if not label_key:
                    break
                label_value = input(f"Label value for '{label_key}': ").strip()
                new_labels[label_key] = label_value

        # Check if any updates were made
        if new_name is None and new_labels is None:
            print("\nNo changes made.")
            return

        # Summary
        print("\nUpdate Summary:")
        if new_name:
            print(f"  Name: {key.get('name')} → {new_name}")
        if new_labels is not None:
            print(f"  Labels: {len(new_labels)} labels")

        confirm = input("\nApply these changes? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Updating SSH key {key_id}...")

        # Update key
        updated_key = self.hetzner.update_ssh_key(
            key_id=key_id,
            name=new_name,
            labels=new_labels
        )

        if updated_key:
            print(f"SSH key {key_id} updated successfully")
            if new_name:
                print(f"  New name: {updated_key.get('name')}")
            if new_labels is not None:
                print(f"  Labels updated: {len(updated_key.get('labels', {}))} labels")
        else:
            print(f"Failed to update SSH key {key_id}")

    def _validate_ssh_key(self, public_key: str) -> bool:
        """Validate SSH public key format"""
        if not public_key:
            return False

        # Check if key starts with valid key type
        valid_key_types = [
            'ssh-rsa',
            'ssh-ed25519',
            'ecdsa-sha2-nistp256',
            'ecdsa-sha2-nistp384',
            'ecdsa-sha2-nistp521'
        ]

        return any(public_key.startswith(key_type) for key_type in valid_key_types)
