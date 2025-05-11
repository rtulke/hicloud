#!/usr/bin/env python3
# commands/batch.py - Batch operations for multiple servers

from typing import List

class BatchCommands:
    """Batch operations for multiple servers in Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle batch operation commands"""
        if not args:
            print("Missing batch subcommand. Use 'batch start|stop|delete|snapshot <id1,id2,id3...>'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "start":
            self.batch_start(args[1:])
        elif subcommand == "stop":
            self.batch_stop(args[1:])
        elif subcommand == "delete":
            self.batch_delete(args[1:])
        elif subcommand == "snapshot":
            self.batch_snapshot(args[1:])
        else:
            print(f"Unknown batch subcommand: {subcommand}")
    
    def _parse_ids(self, args):
        """Parse comma-separated server IDs from arguments"""
        if not args:
            print("Missing server IDs. Use 'batch SUBCOMMAND <id1,id2,id3...>'")
            return []
            
        # IDs können entweder als einzelnes Argument mit Kommas oder als separate Argumente übergeben werden
        if len(args) == 1 and ',' in args[0]:
            id_strings = args[0].split(',')
        else:
            id_strings = args
            
        server_ids = []
        for id_str in id_strings:
            try:
                server_id = int(id_str.strip())
                server_ids.append(server_id)
            except ValueError:
                print(f"Invalid server ID: {id_str} (must be an integer)")
                
        return server_ids
    
    def batch_start(self, args: List[str]):
        """Start multiple servers by ID"""
        server_ids = self._parse_ids(args)
        if not server_ids:
            return
            
        # Sammle Server-Details für die Bestätigungsabfrage
        servers_to_start = []
        servers_already_running = []
        servers_not_found = []
        
        for server_id in server_ids:
            server = self.hetzner.get_server_by_id(server_id)
            if not server:
                servers_not_found.append(server_id)
                continue
                
            if server.get("status") == "running":
                servers_already_running.append(server)
            else:
                servers_to_start.append(server)
        
        # Zeige gefundene/nicht gefundene Server an
        if servers_not_found:
            print(f"Warning: The following server IDs were not found: {', '.join(str(id) for id in servers_not_found)}")
            
        if servers_already_running:
            print("The following servers are already running and will be skipped:")
            for server in servers_already_running:
                print(f"  - {server.get('name')} (ID: {server.get('id')})")
        
        if not servers_to_start:
            print("No servers to start.")
            return
            
        # Bestätigungsabfrage
        print("\nThe following servers will be started:")
        for server in servers_to_start:
            print(f"  - {server.get('name')} (ID: {server.get('id')})")
            
        confirm = input(f"\nAre you sure you want to start these {len(servers_to_start)} servers? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Server starten
        success_count = 0
        fail_count = 0
        
        for server in servers_to_start:
            server_id = server.get('id')
            server_name = server.get('name')
            
            print(f"Starting server '{server_name}' (ID: {server_id})...", end="", flush=True)
            if self.hetzner.start_server(server_id):
                print(" OK")
                success_count += 1
            else:
                print(" FAILED")
                fail_count += 1
                
        print(f"\nBatch operation completed: {success_count} servers started successfully, {fail_count} failed")
    
    def batch_stop(self, args: List[str]):
        """Stop multiple servers by ID"""
        server_ids = self._parse_ids(args)
        if not server_ids:
            return
            
        # Sammle Server-Details für die Bestätigungsabfrage
        servers_to_stop = []
        servers_already_stopped = []
        servers_not_found = []
        
        for server_id in server_ids:
            server = self.hetzner.get_server_by_id(server_id)
            if not server:
                servers_not_found.append(server_id)
                continue
                
            if server.get("status") == "off":
                servers_already_stopped.append(server)
            else:
                servers_to_stop.append(server)
        
        # Zeige gefundene/nicht gefundene Server an
        if servers_not_found:
            print(f"Warning: The following server IDs were not found: {', '.join(str(id) for id in servers_not_found)}")
            
        if servers_already_stopped:
            print("The following servers are already stopped and will be skipped:")
            for server in servers_already_stopped:
                print(f"  - {server.get('name')} (ID: {server.get('id')})")
        
        if not servers_to_stop:
            print("No servers to stop.")
            return
            
        # Bestätigungsabfrage
        print("\nThe following servers will be stopped:")
        for server in servers_to_stop:
            print(f"  - {server.get('name')} (ID: {server.get('id')})")
            
        confirm = input(f"\nAre you sure you want to stop these {len(servers_to_stop)} servers? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Server stoppen
        success_count = 0
        fail_count = 0
        
        for server in servers_to_stop:
            server_id = server.get('id')
            server_name = server.get('name')
            
            print(f"Stopping server '{server_name}' (ID: {server_id})...", end="", flush=True)
            if self.hetzner.stop_server(server_id):
                print(" OK")
                success_count += 1
            else:
                print(" FAILED")
                fail_count += 1
                
        print(f"\nBatch operation completed: {success_count} servers stopped successfully, {fail_count} failed")
    
    def batch_delete(self, args: List[str]):
        """Delete multiple servers by ID"""
        server_ids = self._parse_ids(args)
        if not server_ids:
            return
            
        # Sammle Server-Details für die Bestätigungsabfrage
        servers_to_delete = []
        servers_not_found = []
        
        for server_id in server_ids:
            server = self.hetzner.get_server_by_id(server_id)
            if not server:
                servers_not_found.append(server_id)
                continue
                
            servers_to_delete.append(server)
        
        # Zeige gefundene/nicht gefundene Server an
        if servers_not_found:
            print(f"Warning: The following server IDs were not found: {', '.join(str(id) for id in servers_not_found)}")
        
        if not servers_to_delete:
            print("No servers to delete.")
            return
            
        # Bestätigungsabfrage mit besonderer Warnung
        print("\n\033[1;31mWARNING: This operation will PERMANENTLY DELETE the following servers:\033[0m")
        for server in servers_to_delete:
            print(f"  - {server.get('name')} (ID: {server.get('id')})")
            
        confirm = input(f"\nThis action is irreversible! Are you absolutely sure you want to delete these {len(servers_to_delete)} servers? Type 'delete' to confirm: ")
        if confirm.lower() != 'delete':
            print("Operation cancelled")
            return
            
        # Server löschen
        success_count = 0
        fail_count = 0
        
        for server in servers_to_delete:
            server_id = server.get('id')
            server_name = server.get('name')
            
            print(f"Deleting server '{server_name}' (ID: {server_id})...", end="", flush=True)
            if self.hetzner.delete_server(server_id):
                print(" OK")
                success_count += 1
            else:
                print(" FAILED")
                fail_count += 1
                
        print(f"\nBatch operation completed: {success_count} servers deleted successfully, {fail_count} failed")
    
    def batch_snapshot(self, args: List[str]):
        """Create snapshots for multiple servers"""
        server_ids = self._parse_ids(args)
        if not server_ids:
            return
            
        # Sammle Server-Details für die Bestätigungsabfrage
        servers_to_snapshot = []
        servers_not_found = []
        
        for server_id in server_ids:
            server = self.hetzner.get_server_by_id(server_id)
            if not server:
                servers_not_found.append(server_id)
                continue
                
            servers_to_snapshot.append(server)
        
        # Zeige gefundene/nicht gefundene Server an
        if servers_not_found:
            print(f"Warning: The following server IDs were not found: {', '.join(str(id) for id in servers_not_found)}")
        
        if not servers_to_snapshot:
            print("No servers to snapshot.")
            return
            
        # Optionen für Snapshots
        description = input("Enter a description for these snapshots (optional): ")
        
        # Bestätigungsabfrage
        print("\nThe following servers will be snapshotted:")
        for server in servers_to_snapshot:
            print(f"  - {server.get('name')} (ID: {server.get('id')})")
            
        confirm = input(f"\nThis may take some time depending on the server sizes. Continue with creating {len(servers_to_snapshot)} snapshots? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Snapshots erstellen
        success_count = 0
        fail_count = 0
        created_snapshots = []
        
        for server in servers_to_snapshot:
            server_id = server.get('id')
            server_name = server.get('name')
            
            # Beschreibung für jeden Server anpassen
            snapshot_description = description
            if not snapshot_description:
                snapshot_description = f"Batch snapshot of {server_name}"
            
            print(f"Creating snapshot for server '{server_name}' (ID: {server_id})...", end="", flush=True)
            snapshot = self.hetzner.create_snapshot(server_id, snapshot_description)
            
            if snapshot and 'id' in snapshot:
                print(f" OK (ID: {snapshot['id']})")
                success_count += 1
                created_snapshots.append(snapshot)
            else:
                print(" FAILED")
                fail_count += 1
                
        print(f"\nBatch operation completed: {success_count} snapshots created successfully, {fail_count} failed")
        
        # Zeige die erstellten Snapshots an
        if created_snapshots:
            print("\nCreated snapshots:")
            for snapshot in created_snapshots:
                snapshot_id = snapshot.get('id')
                snapshot_desc = snapshot.get('description', f"Snapshot {snapshot_id}")
                print(f"  - {snapshot_desc} (ID: {snapshot_id})")