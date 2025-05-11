#!/usr/bin/env python3
# commands/project.py - Project-related commands for hicloud

import os
import sys
from typing import List

from utils.constants import DEFAULT_CONFIG_PATH
from lib.config import ConfigManager

class ProjectCommands:
    """Project-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle project-related commands"""
        if not args:
            # Wenn kein Unterbefehl angegeben, zeige die Projektinformationen an
            self.show_resources()
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_projects()
        elif subcommand == "switch":
            self.switch_project(args[1:])
        elif subcommand == "resources":
            self.show_resources()
        elif subcommand == "info":
            self.show_info()
        else:
            # Bei unbekannten Unterbefehlen standardmäßig Projektinformationen anzeigen
            print(f"Unknown project subcommand: {subcommand}")
            print("Available subcommands: list, switch, resources, info")
            print("Use 'help' for more information")
            return
    
    def list_projects(self):
        """List available projects"""
        config_path = DEFAULT_CONFIG_PATH
        if not os.path.exists(config_path):
            print(f"No configuration file found at {config_path}")
            print(f"Generate one with: hicloud.py --gen-config {config_path}")
            return
            
        config = ConfigManager.load_config(config_path)
        if not config:
            print("No projects found in configuration file.")
            return
            
        # Daten für die Tabelle vorbereiten
        headers = ["Project", "Name", "Current"]
        rows = []
        
        for project_key, project_data in config.items():
            project_name = project_data.get("project_name", project_key)
            is_current = "✓" if project_key == self.hetzner.project_name else ""
            rows.append([project_key, project_name, is_current])
            
        # Tabelle drucken
        self.console.print_table(headers, rows, "Available projects")
        
        print("\nUse 'project switch <project>' to change the active project.")
    
    def switch_project(self, args: List[str]):
        """Switch to a different project"""
        if not args:
            print("Missing project name. Use 'project switch <n>'")
            return
            
        project_name = args[0]
        config_path = DEFAULT_CONFIG_PATH
        
        if not os.path.exists(config_path):
            print(f"No configuration file found at {config_path}")
            return
            
        config = ConfigManager.load_config(config_path)
        if not config:
            print("No projects found in configuration file.")
            return
            
        if project_name not in config:
            print(f"Project '{project_name}' not found in configuration.")
            print("Available projects:")
            for proj in config.keys():
                print(f"  - {proj}")
            return
            
        # Projekt wechseln durch Neustart mit --project Parameter
        print(f"Switching to project '{project_name}'...")
        
        # Aktuelle Kommandozeile bauen
        cmd = [sys.executable]  # Python-Interpreter
        cmd.append(os.path.abspath(sys.argv[0]))  # Skriptpfad
        cmd.append("--project")
        cmd.append(project_name)
        
        # Führe das Skript mit neuem Projekt neu aus
        print(f"Restarting hicloud with project '{project_name}'...")
        os.execv(sys.executable, cmd)
    
    def show_resources(self):
        """Show all resources in the current project"""
        print(f"\nResources in project '{self.hetzner.project_name}':")
        print(self.console.horizontal_line('='))
        
        # Server auflisten
        servers = self.hetzner.list_servers()
        
        # VM-Tabelle
        if servers:
            headers = ["ID", "Name", "Status", "Type"]
            rows = [[server['id'], server['name'], server['status'], server['server_type']['name']] for server in servers]
            self.console.print_table(headers, rows, f"Virtual Machines: {len(servers)}")
        else:
            print(f"\nVirtual Machines: 0")
                
        # Snapshots auflisten
        snapshots = self.hetzner.list_snapshots()
        
        # Snapshots-Tabelle
        if snapshots:
            headers = ["ID", "Description", "Created"]
            rows = []
            for snapshot in snapshots:
                desc = snapshot.get("description", f"Snapshot {snapshot['id']}")
                created = snapshot['created'][:19] if 'created' in snapshot else "N/A"
                rows.append([snapshot['id'], desc, created])
            
            self.console.print_table(headers, rows, f"Snapshots: {len(snapshots)}")
        else:
            print(f"\nSnapshots: 0")
                
        # SSH-Keys auflisten
        ssh_keys = self.hetzner.list_ssh_keys()
        
        # SSH-Keys-Tabelle
        if ssh_keys:
            headers = ["ID", "Name"]
            rows = [[key['id'], key['name']] for key in ssh_keys]
            self.console.print_table(headers, rows, f"SSH Keys: {len(ssh_keys)}")
        else:
            print(f"\nSSH Keys: 0")
                
        # Backups auflisten
        backups = self.hetzner.list_backups()
        
        # Backups-Tabelle
        if backups:
            headers = ["ID", "Description", "Created"]
            rows = []
            for backup in backups:
                desc = backup.get("description", f"Backup {backup['id']}")
                created = backup['created'][:19] if 'created' in backup else "N/A"
                rows.append([backup['id'], desc, created])
            
            self.console.print_table(headers, rows, f"Backups: {len(backups)}")
        else:
            print(f"\nBackups: 0")
    
    def show_info(self):
        """Show detailed information about the current project"""
        print(f"\n{'='*60}")
        print(f"Project Information: \033[1;32m{self.hetzner.project_name}\033[0m")
        print(f"{'='*60}")

        # API-Verbindungsstatus prüfen mit einem gültigen Endpunkt
        try:
            # Statt des leeren Endpunkts einen gültigen API-Endpunkt verwenden
            status_code, response = self.hetzner._make_request("GET", "datacenters")
            if status_code == 200:
                print(f"Connection Status: \033[1;32mConnected\033[0m")
                print(f"API Endpoint: {self.hetzner.headers['Authorization'][:10]}...")

                # Server zählen
                servers = self.hetzner.list_servers()
                server_count = len(servers)
                running_servers = sum(1 for s in servers if s.get("status") == "running")

                # Snapshots zählen
                snapshots = self.hetzner.list_snapshots()
                snapshot_count = len(snapshots)

                # Ressourcen anzeigen
                print(f"\nResources:")
                print(f"  VMs: {server_count} total, {running_servers} running")
                print(f"  Snapshots: {snapshot_count}")

                # Datacenters anzeigen            
                datacenters = response.get("datacenters", [])
                if datacenters:
                    datacenter_count = len(datacenters)
                    print(f"  Datacenters: {datacenter_count}")
                    print("  Available Locations:")
                    for dc in datacenters:
                        location = dc.get('location', {})
                        location_name = location.get('name', 'N/A')
                        location_city = location.get('city', location.get('description', 'N/A'))
                        location_country = location.get('country', 'N/A')
                        print(f"    - {dc['name']} ({location_name}): {location_city}, {location_country}")
                        
                    # Verbundene Netzwerke zählen
                try:
                    status_code, networks = self.hetzner._make_request("GET", "networks")
                    if status_code == 200:
                        network_count = len(networks.get("networks", []))
                        print(f"  Networks: {network_count}")
                except Exception:
                    pass

                # Verfügbare SSH-Schlüssel zählen
                try:
                    status_code, ssh_keys = self.hetzner._make_request("GET", "ssh_keys")
                    if status_code == 200:
                        ssh_key_count = len(ssh_keys.get("ssh_keys", []))
                        print(f"  SSH Keys: {ssh_key_count}")
                except Exception:
                    pass

            else:
                print(f"Connection Status: \033[1;31mError\033[0m (HTTP {status_code})")
                print(f"Could not connect to API. Response: {response.get('error', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Connection Status: \033[1;31mError\033[0m")
            print(f"Error: {str(e)}")

        print(f"{'-'*60}")
