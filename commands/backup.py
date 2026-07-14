#!/usr/bin/env python3
# commands/backup.py - Backup-related commands for hicloud

from typing import List

from commands.base import BaseCommands
from utils.formatting import format_size

class BackupCommands(BaseCommands):
    """Backup-related commands for Interactive Console"""

    label = "backup"
    usage = "backup list|enable|disable|delete"

    def _build_actions(self):
        return {
            "list": self.list_backups,
            "enable": self.enable_backup,
            "disable": self.disable_backup,
            "delete": self.delete_backup,
        }
    
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
        
        headers = ["ID", "Name", "Created", "Size", "Server ID"]

        for server_name in sorted(backup_groups.keys()):
            group_backups = backup_groups[server_name]
            group_backups.sort(key=lambda x: x.get("image_size", 0), reverse=True)

            rows = []
            for backup in group_backups:
                server_id = backup.get("created_from", {}).get("id", "N/A")
                desc = f"{server_name} backup" if server_name != "Unknown" else backup.get("description", "N/A")
                rows.append([backup["id"], desc, backup["created"][:19], format_size(backup.get("image_size", 0)), server_id])

            self.console.print_table(headers, rows, server_name)
    
    def enable_backup(self, args: List[str]):
        """Enable automatic backups for a VM"""
        vm_id = self.parse_id(args, "VM ID", "backup enable <id> [WINDOW]")
        if vm_id is None:
            return
            
        server = self.hetzner.get_server_by_id(vm_id)

        if not server:
            # Fehlermeldung kommt bereits aus dem API-Layer
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
        vm_id = self.parse_id(args, "VM ID", "backup disable <id>")
        if vm_id is None:
            return
            
        server = self.hetzner.get_server_by_id(vm_id)

        if not server:
            # Fehlermeldung kommt bereits aus dem API-Layer
            return
            
        print(f"Disabling automatic backups for VM '{server.get('name')}' (ID: {vm_id})...")
        if self.hetzner.disable_server_backups(vm_id):
            print(f"Automatic backups disabled successfully for VM {vm_id}")
        else:
            print(f"Failed to disable automatic backups for VM {vm_id}")
    
    def delete_backup(self, args: List[str]):
        """Delete a backup by ID"""
        backup_id = self.parse_id(args, "backup ID", "backup delete <id>")
        if backup_id is None:
            return

        if not self.confirm(f"Are you sure you want to delete backup {backup_id}?"):
            return
            
        print(f"Deleting backup {backup_id}...")
        if self.hetzner.delete_backup(backup_id):
            print(f"Backup {backup_id} deleted successfully")
        else:
            print(f"Failed to delete backup {backup_id}")
