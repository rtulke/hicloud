#!/usr/bin/env python3
# commands/snapshot.py - Snapshot-related commands for hicloud

from typing import List
from utils.formatting import format_size

class SnapshotCommands:
    """Snapshot-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle snapshot-related commands"""
        if not args:
            print("Missing snapshot subcommand. Use 'snapshot list|create|delete|rebuild'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_snapshots(args[1:])
        elif subcommand == "create":
            self.create_snapshot(args[1:])
        elif subcommand == "delete":
            self.delete_snapshot(args[1:])
        elif subcommand == "rebuild":
            self.rebuild_snapshot(args[1:])
        else:
            print(f"Unknown snapshot subcommand: {subcommand}")
    
    def list_snapshots(self, args: List[str]):
        """List snapshots, optionally filtered by VM ID"""
        vm_id = None
        if args:
            try:
                vm_id = int(args[0])
            except ValueError:
                print("Invalid VM ID. Must be an integer.")
                return
                
        snapshots = self.hetzner.list_snapshots(vm_id)
        if not snapshots:
            print("No snapshots found")
            return
            
        # Gruppiere Snapshots nach Server-Namen
        snapshot_groups = {}
        for snapshot in snapshots:
            server_name = snapshot.get("created_from", {}).get("name", "Unknown")
            if server_name not in snapshot_groups:
                snapshot_groups[server_name] = []
            snapshot_groups[server_name].append(snapshot)
        
        headers = ["ID", "Name", "Created", "Size", "Server ID"]

        for server_name in sorted(snapshot_groups.keys()):
            group_snapshots = snapshot_groups[server_name]
            group_snapshots.sort(key=lambda x: x.get("image_size", 0), reverse=True)

            rows = []
            for snapshot in group_snapshots:
                server_id = snapshot.get("created_from", {}).get("id", "N/A")
                desc = snapshot.get("description", "N/A")
                if desc == "N/A" and server_name != "Unknown":
                    desc = f"{server_name} snapshot"
                rows.append([snapshot["id"], desc, snapshot["created"][:19], format_size(snapshot.get("image_size", 0)), server_id])

            self.console.print_table(headers, rows, server_name)
    
    def create_snapshot(self, args: List[str]):
        """Create a snapshot for a VM"""
        if not args:
            print("Missing VM ID. Use 'snapshot create <id>'")
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
            
        print(f"Creating snapshot for VM '{server.get('name')}' (ID: {vm_id})...")
        snapshot = self.hetzner.create_snapshot(vm_id)
        
        if snapshot:
            print(f"Snapshot created successfully with ID {snapshot['id']}")
        else:
            print("Failed to create snapshot")
    
    def delete_snapshot(self, args: List[str]):
        """Delete a snapshot by ID or all snapshots for a VM"""
        if not args:
            print("Missing snapshot ID or 'all'. Use 'snapshot delete <id>' or 'snapshot delete all <id>'")
            return
            
        if args[0].lower() == "all":
            # Delete all snapshots for a VM
            if len(args) < 2:
                print("Missing VM ID. Use 'snapshot delete all <id>'")
                return
                
            try:
                vm_id = int(args[1])
            except ValueError:
                print("Invalid VM ID. Must be an integer.")
                return
                
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            confirm = input(f"Are you sure you want to delete ALL snapshots for VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return
                
            snapshots = self.hetzner.list_snapshots(vm_id)
            if not snapshots:
                print("No snapshots found for this VM")
                return
                
            success_count = 0
            fail_count = 0
            
            for snapshot in snapshots:
                print(f"Deleting snapshot {snapshot['id']}...", end="")
                if self.hetzner.delete_snapshot(snapshot['id']):
                    print(" OK")
                    success_count += 1
                else:
                    print(" FAILED")
                    fail_count += 1
                    
            print(f"Deleted {success_count} snapshots, {fail_count} failed")
            
        else:
            # Delete a specific snapshot
            try:
                snapshot_id = int(args[0])
            except ValueError:
                print("Invalid snapshot ID. Must be an integer.")
                return
                
            confirm = input(f"Are you sure you want to delete snapshot {snapshot_id}? [y/N]: ")
            
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return
                
            if self.hetzner.delete_snapshot(snapshot_id):
                print(f"Snapshot {snapshot_id} deleted successfully")
            else:
                print(f"Failed to delete snapshot {snapshot_id}")
    
    def rebuild_snapshot(self, args: List[str]):
        """Rebuild a server from a snapshot"""
        if len(args) < 2:
            print("Missing snapshot ID and server ID. Use 'snapshot rebuild <snapshot_id> <server_id>'")
            return
            
        try:
            snapshot_id = int(args[0])
            server_id = int(args[1])
        except ValueError:
            print("Invalid ID format. Both snapshot ID and server ID must be integers.")
            return
            
        # Get server and snapshot details for confirmation
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            print(f"Server with ID {server_id} not found")
            return
            
        # Check if the snapshot exists
        snapshots = self.hetzner.list_snapshots()
        snapshot = next((s for s in snapshots if s.get('id') == snapshot_id), None)
        
        if not snapshot:
            print(f"Snapshot with ID {snapshot_id} not found")
            return
            
        snapshot_name = snapshot.get('description', f'Snapshot {snapshot_id}')
        
        # Warning message
        print("\n\033[1;31mWARNING!\033[0m")
        print(f"Rebuilding server '{server.get('name')}' will delete all data on the server!")
        print("This action is irreversible.")
        print(f"The server will be rebuilt using snapshot '{snapshot_name}'")
        
        confirm = input(f"Are you sure you want to rebuild server '{server.get('name')}' (ID: {server_id})? Type 'rebuild' to confirm: ")
        
        if confirm.lower() != 'rebuild':
            print("Operation cancelled")
            return
            
        print(f"Rebuilding server '{server.get('name')}' (ID: {server_id}) from snapshot {snapshot_id}...")
        
        if self.hetzner.rebuild_server_from_snapshot(server_id, snapshot_id):
            print(f"Server {server_id} successfully rebuilt from snapshot {snapshot_id}")
        else:
            print(f"Failed to rebuild server from snapshot")
