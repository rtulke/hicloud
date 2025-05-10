#!/usr/bin/env python3
# commands/backup.py - Backup-related commands for hicloud

from typing import List
from utils.formatting import format_size

class BackupCommands:
    """Backup-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle backup-related commands"""
        if not args:
            print("Missing backup subcommand. Use 'backup list|enable|disable|delete'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_backups(args[1:])
        elif subcommand == "enable":
            self.enable_backup(args[1:])
        elif subcommand == "disable":
            self.disable_backup(args[1:])
        elif subcommand == "delete":
            self.delete_backup(args[1:])
        else:
            print(f"Unknown backup subcommand: {subcommand}")
    
    def list_backups(self, args: List[str]):
        """List backups, optionally filtered by VM ID"""
        vm_id = None
        if args:
            try:
                vm_id = int(args[0])
            except ValueError:
                print("Invalid VM ID. Must be an integer.")
                return
                
        backups = self.hetzner.list_backups(vm_id)
        if not backups:
            print("No backups found")
            return
            
        # Gruppiere Backups nach Server-Namen
        backup_groups = {}
        for backup in backups:
            server_name = backup.get("created_from", {}).get("name", "Unknown")
            if server_name not in backup_groups:
                backup_groups[server_name] = []
            backup_groups[server_name].append(backup)
        
        print("\nBackups:")
        print(f"{'ID':<10} {'Name':<50} {'Created':<20} {'Size':<12} {'Server ID':<15}")
        print("-" * 107)
        
        # Sortiere die Server-Namen alphabetisch
        for server_name in sorted(backup_groups.keys()):
            group_backups = backup_groups[server_name]
            
            # Sortiere Backups innerhalb der Gruppe nach Größe (absteigend)
            group_backups.sort(key=lambda x: x.get("image_size", 0), reverse=True)
            
            for backup in group_backups:
                server_id = backup.get("created_from", {}).get("id", "N/A")
                desc = f"{server_name} backup" if server_name != "Unknown" else backup.get("description", "N/A")
                
                # Formatiere Größe
                size_gb = backup.get("image_size", 0)
                formatted_size = format_size(size_gb)
                
                print(f"{backup['id']:<10} {desc:<50} {backup['created'][:19]:<20} {formatted_size:<12} {server_id:<15}")
            
            # Füge eine Leerzeile zwischen den Gruppen ein
            print()
    
    def enable_backup(self, args: List[str]):
        """Enable automatic backups for a VM"""
        if not args:
            print("Missing VM ID. Use 'backup enable <id> [WINDOW]'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            print(f"VM with ID {vm_id} not found")
            return
        
        # Optional backup window parameter
        backup_window = args[1] if len(args) > 1 else None
        if backup_window and backup_window not in ["22-02", "02-06", "06-10", "10-14", "14-18", "18-22"]:
            print("Invalid backup window. Must be one of: 22-02, 02-06, 06-10, 10-14, 14-18, 18-22")
            return
            
        print(f"Enabling automatic backups for VM '{server.get('name')}' (ID: {vm_id})...")
        if self.hetzner.enable_server_backups(vm_id, backup_window):
            print(f"Automatic backups enabled successfully for VM {vm_id}")
        else:
            print(f"Failed to enable automatic backups for VM {vm_id}")
    
    def disable_backup(self, args: List[str]):
        """Disable automatic backups for a VM"""
        if not args:
            print("Missing VM ID. Use 'backup disable <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            print(f"VM with ID {vm_id} not found")
            return
            
        print(f"Disabling automatic backups for VM '{server.get('name')}' (ID: {vm_id})...")
        if self.hetzner.disable_server_backups(vm_id):
            print(f"Automatic backups disabled successfully for VM {vm_id}")
        else:
            print(f"Failed to disable automatic backups for VM {vm_id}")
    
    def delete_backup(self, args: List[str]):
        """Delete a backup by ID"""
        if not args:
            print("Missing backup ID. Use 'backup delete <id>'")
            return
            
        try:
            backup_id = int(args[0])
        except ValueError:
            print("Invalid backup ID. Must be an integer.")
            return
            
        confirm = input(f"Are you sure you want to delete backup {backup_id}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        print(f"Deleting backup {backup_id}...")
        if self.hetzner.delete_backup(backup_id):
            print(f"Backup {backup_id} deleted successfully")
        else:
            print(f"Failed to delete backup {backup_id}")
