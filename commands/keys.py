#!/usr/bin/env python3
# commands/keys.py - SSH key-related commands for hicloud

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
            print("Missing keys subcommand. Use 'keys list|delete'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_keys()
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
            
        print("\nSSH Keys:")
        print(f"{'ID':<10} {'Name':<30} {'Fingerprint':<50} {'Created':<20}")
        print("-" * 110)
        
        # Sort keys alphabetically by name
        for key in sorted(ssh_keys, key=lambda x: x.get('name', '').lower()):
            fingerprint = key.get('fingerprint', 'N/A')
            created = key.get('created', 'N/A')
            
            # Format the creation date if it exists
            if created != 'N/A':
                created = created.split('T')[0]
                
            print(f"{key['id']:<10} {key['name']:<30} {fingerprint:<50} {created:<20}")
    
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
