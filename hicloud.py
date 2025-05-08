#!/usr/bin/env python3
# hicloud.py - Hetzner Cloud CLI Tool
# License: MIT

import os
import sys
import argparse
import json
import stat
import requests
import time
import toml
import getpass
import readline
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Constants
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.hicloud.toml")
HISTORY_DIR = os.path.expanduser("~/.tmp/hicloud")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history")
HISTORY_MAX_LINES = 1000
API_BASE_URL = "https://api.hetzner.cloud/v1"
VERSION = "1.0.0"

class HetznerCloudManager:
    """Manages interactions with Hetzner Cloud API"""
    
    def __init__(self, api_token: str, project_name: str = "default"):
        self.api_token = api_token
        self.project_name = project_name
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Tuple[int, Dict]:
        """Make an API request to Hetzner Cloud"""
        url = f"{API_BASE_URL}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return 400, {"error": f"Unsupported method: {method}"}
                
            if response.status_code in [200, 201, 202, 204]:
                try:
                    if response.status_code == 204 or not response.text:
                        return response.status_code, {}
                    return response.status_code, response.json()
                except json.JSONDecodeError:
                    return response.status_code, {}
            else:
                return response.status_code, {"error": f"API request failed: {response.text}"}
        except requests.exceptions.RequestException as e:
            return 500, {"error": f"Request failed: {str(e)}"}
    
    # Backup Management Functions
    def list_backups(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all backups, optionally filtered by server ID"""
        status_code, response = self._make_request("GET", "images?type=backup")
        
        if status_code != 200:
            print(f"Error listing backups: {response.get('error', 'Unknown error')}")
            return []
        
        backups = response.get("images", [])
        
        # Filter by server ID if provided
        if server_id:
            return [b for b in backups if b.get("created_from", {}).get("id") == server_id]
        return backups
    
    def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup by ID"""
        status_code, response = self._make_request("DELETE", f"images/{backup_id}")
        
        if status_code not in [200, 204]:
            print(f"Error deleting backup: {response.get('error', 'Unknown error')}")
            return False
            
        return True
    
    def enable_server_backups(self, server_id: int, backup_window: Optional[str] = None) -> bool:
        """Enable automated backups for a server"""
        data = {}
        if backup_window:
            data["backup_window"] = backup_window
            
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/enable_backup", data
        )
        
        if status_code != 201:
            print(f"Error enabling backups: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for backup enablement to complete...")
            return self._wait_for_action(action_id)
            
        return True
    
    def disable_server_backups(self, server_id: int) -> bool:
        """Disable automated backups for a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/disable_backup", {}
        )
        
        if status_code != 201:
            print(f"Error disabling backups: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for backup disablement to complete...")
            return self._wait_for_action(action_id)
            
        return True
    
    # VM Management Functions
    def list_servers(self) -> List[Dict]:
        """List all servers in the project"""
        status_code, response = self._make_request("GET", "servers")
        
        if status_code != 200:
            print(f"Error listing servers: {response.get('error', 'Unknown error')}")
            return []
            
        return response.get("servers", [])
    
    def create_server(self, name: str, server_type: str, image: str, 
                     location: str = "nbg1", ssh_keys: List[int] = None,
                     ipv4: bool = True, ipv6: bool = True, 
                     auto_password: bool = False) -> Dict:
        """Create a new server"""
        data = {
            "name": name,
            "server_type": server_type,
            "image": image,
            "location": location,
            "public_net": {
                "enable_ipv4": ipv4,
                "enable_ipv6": ipv6
            }
        }
        
        if ssh_keys:
            data["ssh_keys"] = ssh_keys
            
        # Die standard API-Verhaltensweise ist: Wenn kein root_password gesetzt ist,
        # wird keines generiert AUSSER wenn 'start_after_create' true ist oder nicht spezifiziert ist
        # Wir setzen dies explizit, um je nach Benutzerauswahl ein Passwort zu forcieren oder nicht
        if auto_password:
            data["start_after_create"] = True
        else:
            data["start_after_create"] = False
            
        status_code, response = self._make_request("POST", "servers", data)
        
        if status_code != 201:
            print(f"Error creating server: {response.get('error', 'Unknown error')}")
            return {}
            
        return response.get("server", {})
    
    def delete_server(self, server_id: int) -> bool:
        """Delete a server by ID"""
        status_code, response = self._make_request("DELETE", f"servers/{server_id}")
        
        if status_code not in [200, 204]:
            print(f"Error deleting server: {response.get('error', 'Unknown error')}")
            return False
            
        return True
    
    def start_server(self, server_id: int) -> bool:
        """Start a server by ID"""
        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/poweron", {})
        
        if status_code != 201:
            print(f"Error starting server: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server to start...")
            return self._wait_for_action(action_id)
            
        return True
    
    def stop_server(self, server_id: int) -> bool:
        """Stop a server by ID"""
        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/shutdown", {})
        
        if status_code != 201:
            # Try poweroff if shutdown fails
            print("Trying graceful shutdown...")
            status_code, response = self._make_request("POST", f"servers/{server_id}/actions/poweroff", {})
            
            if status_code != 201:
                print(f"Error stopping server: {response.get('error', 'Unknown error')}")
                return False
        
        # Wait for action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server to stop...")
            return self._wait_for_action(action_id)
            
        return True
    
    def get_server_by_name(self, name: str) -> Dict:
        """Get server by name"""
        servers = self.list_servers()
        for server in servers:
            if server["name"] == name:
                return server
        return {}
        
    def get_server_by_id(self, server_id: int) -> Dict:
        """Get server details by ID"""
        status_code, response = self._make_request("GET", f"servers/{server_id}")
        
        if status_code != 200:
            print(f"Error getting server: {response.get('error', 'Unknown error')}")
            return {}
            
        return response.get("server", {})
    
    # Snapshot Management Functions
    def list_snapshots(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all snapshots, optionally filtered by server ID"""
        status_code, response = self._make_request("GET", "images?type=snapshot")
        
        if status_code != 200:
            print(f"Error listing snapshots: {response.get('error', 'Unknown error')}")
            return []
        
        snapshots = response.get("images", [])
        
        # Filter by server ID if provided
        if server_id:
            return [s for s in snapshots if s.get("created_from", {}).get("id") == server_id]
        return snapshots
    
    def create_snapshot(self, server_id: int, description: Optional[str] = None) -> Dict:
        """Create a snapshot of a server"""
        if not description:
            description = f"Backup from {datetime.now().strftime('%Y-%m-%d-%H%M')}"
            
        data = {
            "description": description,
            "type": "snapshot"
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/create_image", data
        )
        
        if status_code != 201:
            print(f"Error creating snapshot: {response.get('error', 'Unknown error')}")
            return {}
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for snapshot creation to complete...")
            self._wait_for_action(action_id)
            
        # Get the newly created snapshot details
        snapshots = self.list_snapshots(server_id)
        if snapshots:
            # Find the newest snapshot for this server
            newest = max(snapshots, key=lambda x: x.get("created"))
            return newest
            
        return {}
    
    def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete a snapshot by ID"""
        status_code, response = self._make_request("DELETE", f"images/{snapshot_id}")
        
        if status_code not in [200, 204]:
            print(f"Error deleting snapshot: {response.get('error', 'Unknown error')}")
            return False
            
        return True
    
    def _wait_for_action(self, action_id: int, timeout: int = 300) -> bool:
        """Wait for an action to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_code, response = self._make_request("GET", f"actions/{action_id}")
            
            if status_code != 200:
                print(f"Error checking action status: {response.get('error', 'Unknown error')}")
                return False
                
            status = response.get("action", {}).get("status")
            if status == "success":
                return True
            elif status == "error":
                print(f"Action failed: {response.get('action', {}).get('error', {}).get('message', 'Unknown error')}")
                return False
                
            print(".", end="", flush=True)
            time.sleep(5)
            
        print(f"\nTimeout waiting for action {action_id} to complete")
        return False


class ConfigManager:
    """Manages configuration loading and generation"""
    
    @staticmethod
    def check_file_permissions(config_path: str) -> bool:
        """Check if the config file has 600 permissions"""
        if not os.path.exists(config_path):
            return False
            
        file_mode = os.stat(config_path).st_mode
        return (file_mode & stat.S_IRWXU) == stat.S_IRUSR | stat.S_IWUSR
    
    @staticmethod
    def load_config(config_path: str) -> Dict:
        """Load configuration from a TOML file"""
        if not os.path.exists(config_path):
            print(f"Configuration file not found: {config_path}")
            return {}
            
        # Check file permissions (must be 600)
        if not ConfigManager.check_file_permissions(config_path):
            print(f"WARNING: Insecure permissions on {config_path}")
            print("Please change permissions to 600 (chmod 600 filename)")
            print("Configuration file was not loaded for security reasons")
            return {}
            
        try:
            return toml.load(config_path)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            return {}
    
    @staticmethod
    def generate_config(output_path: str) -> bool:
        """Generate a sample configuration file"""
        sample_config = {
            "default": {
                "api_token": "your_api_token_here",
                "project_name": "default"
            },
            "project1": {
                "api_token": "project1_api_token",
                "project_name": "Production"
            },
            "project2": {
                "api_token": "project2_api_token",
                "project_name": "Development"
            }
        }
        
        try:
            with open(output_path, 'w') as f:
                toml.dump(sample_config, f)
                
            # Set permissions to 600
            os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR)
            print(f"Sample configuration generated at {output_path} with secure permissions")
            return True
        except Exception as e:
            print(f"Error generating configuration: {str(e)}")
            return False


class InteractiveConsole:
    """Interactive console for hicloud"""
    
    def __init__(self, hetzner: HetznerCloudManager):
        self.hetzner = hetzner
        self.running = True
        self.history = []
        
        # Stelle sicher, dass das History-Verzeichnis existiert
        if not os.path.exists(HISTORY_DIR):
            try:
                os.makedirs(HISTORY_DIR, exist_ok=True)
                print(f"Created history directory: {HISTORY_DIR}")
            except Exception as e:
                print(f"Warning: Could not create history directory: {str(e)}")
        
        # Konfiguriere readline für History-Unterstützung
        self._setup_readline()
    
    def _setup_readline(self):
        """Setup readline with history and tab completion support"""
        # Readline-Konfiguration für verschiedene Betriebssysteme
        if platform.system() == 'Windows':
            # Windows-spezifische Konfiguration
            try:
                import pyreadline3
            except ImportError:
                print("Warning: pyreadline3 not installed. Tab completion may not work correctly.")
                print("Try: pip install pyreadline3")
        else:
            # Unix/Mac Konfiguration
            try:
                if platform.system() == 'Darwin':  # macOS
                    # macOS-spezifische Readline-Bindung
                    readline.parse_and_bind("bind ^I rl_complete")
                else:
                    # Linux und andere Unix-Systeme
                    readline.parse_and_bind("tab: complete")
            except Exception as e:
                print(f"Warning: Could not configure readline: {str(e)}")
        
        # Setze den Custom Completer
        try:
            readline.set_completer(self._command_completer)
            readline.set_completer_delims(' \t\n;')
        except Exception as e:
            print(f"Warning: Could not setup tab completion: {str(e)}")
        
        # History aus Datei laden, falls vorhanden
        try:
            if os.path.exists(HISTORY_FILE):
                readline.read_history_file(HISTORY_FILE)
                # Historie auf maximale Zeilenanzahl begrenzen
                history_len = readline.get_current_history_length()
                if history_len > HISTORY_MAX_LINES:
                    # Historie nur behalten wenn wir sie neu schreiben können
                    for i in range(history_len - HISTORY_MAX_LINES):
                        readline.remove_history_item(0)
                    # Datei mit begrenzter Historie neu schreiben
                    readline.write_history_file(HISTORY_FILE)
        except Exception as e:
            print(f"Warning: Could not load command history: {str(e)}")
            
        # Command completion einrichten
        self.commands = {
            "vm": {
                "help": "VM commands: list, info <id>, create, start <id>, stop <id>, delete <id>",
                "subcommands": {
                    "list": {"help": "List all VMs"},
                    "info": {"help": "Show detailed information about a VM: vm info <id>"},
                    "create": {"help": "Create a new VM (interactive)"},
                    "start": {"help": "Start a VM: vm start <id>"},
                    "stop": {"help": "Stop a VM: vm stop <id>"},
                    "delete": {"help": "Delete a VM: vm delete <id>"}
                }
            },
            "snapshot": {
                "help": "Snapshot commands: list, create, delete <id>, delete all",
                "subcommands": {
                    "list": {"help": "List all snapshots or for specific VM"},
                    "create": {"help": "Create a snapshot for a VM"},
                    "delete": {"help": "Delete a snapshot: snapshot delete <id>"},
                    "all": {"help": "Delete all snapshots for a VM: snapshot delete all"}
                }
            },
            "backup": {
                "help": "Backup commands: list, enable <id> [WINDOW], disable <id>, delete <id>",
                "subcommands": {
                    "list": {"help": "List all backups or for specific VM"},
                    "enable": {"help": "Enable automatic backups for a VM: backup enable <id> [WINDOW]"},
                    "disable": {"help": "Disable automatic backups for a VM: backup disable <id>"},
                    "delete": {"help": "Delete a backup: backup delete <id>"}
                }
            },
            "project": {"help": "Show current project information"},
            "info": {"help": "Show current project information"},
            "history": {
                "help": "Command history: history, history clear",
                "subcommands": {
                    "clear": {"help": "Clear command history"}
                }
            },
            "clear": {"help": "Clear screen"},
            "help": {"help": "Show help information"},
            "exit": {"help": "Exit the program"},
            "quit": {"help": "Exit the program"},
            "q": {"help": "Exit the program"}
        }
        
        # Setze den Completer
        readline.set_completer(self._command_completer)
        
    def _command_completer(self, text, state):
        """Custom command completer for tab completion"""
        buffer = readline.get_line_buffer()
        line = buffer.lstrip()
        
        # Zeige alle verfügbaren Befehle als erste Übereinstimmung, wenn der Zustand 0 ist
        if state == 0 and not text and not line:
            print("\n\033[90mAvailable commands: " + ", ".join(sorted(self.commands.keys())) + "\033[0m")
            print("\nhicloud> ", end="", flush=True)
            return None
        
        # Teile die Eingabe in Wörter auf
        parts = line.split()
        
        # Bestimme den Kontext (Haupt- oder Unterbefehl)
        if not parts:  # Leere Zeile
            matches = sorted(self.commands.keys())
        elif len(parts) == 1 and not line.endswith(' '):  # Erster Teil, noch nicht abgeschlossen
            # Nur Hauptbefehle vervollständigen, die mit dem Text beginnen
            cmd_part = parts[0]
            matches = [cmd for cmd in self.commands.keys() if cmd.startswith(cmd_part)]
            
            # Wenn wir genau eine Übereinstimmung haben, füge ein Leerzeichen hinzu
            if len(matches) == 1:
                matches = [matches[0] + ' ']
                
            # Wenn wir mehrere Übereinstimmungen haben und es der erste Aufruf ist, zeige die an
            elif len(matches) > 1 and state == 0:
                print("\n\033[90mMatching commands: " + ", ".join(matches) + "\033[0m")
                print("\nhicloud> " + line, end="", flush=True)
                
        elif len(parts) == 1 and line.endswith(' '):  # Erster Teil abgeschlossen, zweiter Teil beginnt
            # Wenn der Hauptbefehl bekannt ist, zeige die Unterbefehle an
            cmd = parts[0]
            
            if cmd in self.commands and 'subcommands' in self.commands[cmd]:
                if state == 0:  # Nur beim ersten Aufruf die Hilfe anzeigen
                    # Zeige Hilfe für den Hauptbefehl über dem Prompt
                    print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
                    print("\nhicloud> " + line, end="", flush=True)
                    
                # Liste der möglichen Unterbefehle
                subcmds = sorted(self.commands[cmd]['subcommands'].keys())
                if state < len(subcmds):
                    return subcmds[state]
                else:
                    return None
            else:
                return None
                
        elif len(parts) >= 2 and not line.endswith(' '):  # Zweiter Teil oder höher, unvollständig
            # Wir vervollständigen möglicherweise einen Unterbefehl
            cmd = parts[0]
            curr_part = parts[-1]  # Der aktuelle Teil, den wir vervollständigen
            
            # Wenn der zweite Teil ein "delete" ist und wir bei "all" sein könnten (für snapshot delete all)
            if len(parts) == 2 and cmd == "snapshot" and parts[1] == "delete":
                if state == 0:
                    # Zeige Hilfe für 'delete' Unterbefehl
                    print(f"\n\033[90m{self.commands[cmd]['subcommands']['delete']['help']}\033[0m")
                    print("\nhicloud> " + line, end="", flush=True)
                return "all " if state == 0 else None
                
            # Normaler Fall: Unterbefehlvervollständigung
            if cmd in self.commands and 'subcommands' in self.commands[cmd]:
                # Finde passende Unterbefehle
                matches = [subcmd for subcmd in self.commands[cmd]['subcommands'].keys() 
                          if subcmd.startswith(curr_part)]
                
                # Wenn genau ein Match, füge Leerzeichen an
                if len(matches) == 1:
                    matches = [matches[0] + ' ']
                
                # Wenn wir mehrere Übereinstimmungen haben und es der erste Aufruf ist, zeige sie an
                if len(matches) > 1 and state == 0:
                    print("\n\033[90mMatching subcommands: " + ", ".join(matches) + "\033[0m")
                    print("\nhicloud> " + line, end="", flush=True)
                
                # Return the match at the given state position
                if state < len(matches):
                    # Wir müssen hier den relativen Teil gegen den vollständigen Befehl austauschen
                    full_line = line[:-len(curr_part)] + matches[state]
                    # Nur den nicht bereits eingegebenen Teil zurückgeben
                    return matches[state]
                else:
                    return None
            else:
                return None
                
        # Wenn wir hier ankommen, haben wir keine Übereinstimmungen
        return None
        
    def _show_command_help(self, cmd):
        """Zeigt Hilfe für einen Hauptbefehl an"""
        if cmd in self.commands and 'help' in self.commands[cmd]:
            # Zeige die Hilfe über dem Prompt
            print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
            print("\nhicloud> ", end="", flush=True)
            
    def _show_subcommand_help(self, cmd, subcmd):
        """Zeigt Hilfe für einen Unterbefehl an"""
        if cmd in self.commands and 'subcommands' in self.commands[cmd]:
            if subcmd in self.commands[cmd]['subcommands'] and 'help' in self.commands[cmd]['subcommands'][subcmd]:
                print(f"\n\033[90m{self.commands[cmd]['subcommands'][subcmd]['help']}\033[0m")
                print("\nhicloud> ", end="", flush=True)
    
    def _save_history(self):
        """Save command history to file"""
        try:
            readline.write_history_file(HISTORY_FILE)
        except Exception as e:
            print(f"Warning: Could not save command history: {str(e)}")
            
    def _clean_history(self):
        """Clean command history"""
        try:
            # Lösche alle Einträge aus der readline-History
            hist_len = readline.get_current_history_length()
            for i in range(hist_len):
                readline.remove_history_item(0)
                
            # Leere History-Datei schreiben
            readline.write_history_file(HISTORY_FILE)
            print("Command history cleared")
        except Exception as e:
            print(f"Error clearing history: {str(e)}")
    
    def _display_history(self):
        """Display command history"""
        try:
            hist_len = readline.get_current_history_length()
            print("\nCommand History:")
            print("-" * 60)
            
            # History-Einträge abrufen (ohne den aktuellen 'history' Befehl)
            for i in range(1, hist_len):
                # Index beginnt bei 1, nicht bei 0
                item = readline.get_history_item(i)
                if item:
                    print(f"{i:4d}  {item}")
            print("-" * 60)
        except Exception as e:
            print(f"Error displaying history: {str(e)}")
    
    def _clear_screen(self):
        """Clear the terminal screen"""
        # OS-unabhängiges Löschen des Bildschirms
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")
    
    def _display_welcome_screen(self):
        """Display the welcome screen"""
        print(f"\n{'='*60}")
        print(f"hicloud - Hetzner Interactive Console v{VERSION}")
        print(f"{'='*60}")
        print(f"Active Project: \033[1;32m{self.hetzner.project_name}\033[0m")
        print(f"API Endpoint: {API_BASE_URL}")
        
        # Versuche, Projektinformationen abzurufen
        try:
            status_code, response = self.hetzner._make_request("GET", "datacenters")
            if status_code == 200:
                datacenter_count = len(response.get("datacenters", []))
                print(f"Connection Status: \033[1;32mConnected\033[0m ({datacenter_count} datacenters available)")
            else:
                print(f"Connection Status: \033[1;31mError\033[0m (HTTP {status_code})")
                print(f"API Response: {response.get('error', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Connection Status: \033[1;31mError\033[0m")
            print(f"Error: {str(e)}")
            
        print(f"{'-'*60}")
        print("Type 'help' for available commands, 'exit' to quit")
    
    def start(self):
        """Start the interactive console"""
        # Zeige Willkommensbildschirm
        self._display_welcome_screen()
        
        while self.running:
            try:
                command = input("\nhicloud> ").strip()
                if not command:
                    continue
                    
                parts = command.split()
                main_cmd = parts[0].lower()
                
                if main_cmd in ["exit", "quit", "q"]:
                    self.running = False
                elif main_cmd == "help":
                    self.show_help()
                elif main_cmd == "clear":
                    self._clear_screen()
                    self._display_welcome_screen()
                elif main_cmd == "snapshot":
                    self.handle_snapshot_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "backup":
                    self.handle_backup_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "vm" or main_cmd == "server":
                    print("VM commands available: list, info, create, start, stop, delete")
                    self.handle_vm_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "project" or main_cmd == "info":
                    self.show_project_info()
                elif main_cmd == "history":
                    if len(parts) > 1 and parts[1].lower() == "clear":
                        self._clean_history()
                    else:
                        self._display_history()
                else:
                    print(f"Unknown command: {main_cmd}")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # Beim Beenden die Historie speichern
        self._save_history()    
    def show_help(self):
        """Show help information"""
        help_text = """
Available commands:

  VM Commands:
    vm list                      - List all VMs
    vm info <id>                 - Show detailed information about a VM
    vm create                    - Create a new VM (interactive)
    vm start <id>                - Start a VM
    vm stop <id>                 - Stop a VM
    vm delete <id>               - Delete a VM by ID
    
  Snapshot Commands:
    snapshot list                - List all snapshots or for specific VM
    snapshot create              - Create a snapshot for a VM
    snapshot delete <id>         - Delete a snapshot by ID
    snapshot delete all          - Delete all snapshots for a VM
    
  Backup Commands:
    backup list                  - List all backups or for specific VM
    backup enable <id> [WINDOW]  - Enable automatic backups for a VM
    backup disable <id>          - Disable automatic backups for a VM
    backup delete <id>           - Delete a backup by ID
    
  General Commands:
    project, info                - Show current project information
    history                      - Show command history
    history clear                - Clear command history
    clear                        - Clear screen
    help                         - Show this help message
    exit, quit, q                - Exit the program
"""
        print(help_text)
    
    def handle_snapshot_command(self, args: List[str]):
        """Handle snapshot-related commands"""
        if not args:
            print("Missing snapshot subcommand. Use 'snapshot list|create|delete'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            # List snapshots, optionally filtered by VM ID
            vm_id = int(args[1]) if len(args) > 1 else None
            
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
            
            print("\nSnapshots:")
            print(f"{'ID':<10} {'Name':<50} {'Created':<20} {'Size':<12} {'Server ID':<15}")
            print("-" * 107)
            
            # Sortiere die Server-Namen alphabetisch
            for server_name in sorted(snapshot_groups.keys()):
                group_snapshots = snapshot_groups[server_name]
                
                # Sortiere Snapshots innerhalb der Gruppe nach Größe (absteigend)
                group_snapshots.sort(key=lambda x: x.get("image_size", 0), reverse=True)
                
                for snapshot in group_snapshots:
                    server_id = snapshot.get("created_from", {}).get("id", "N/A")
                    desc = snapshot.get("description", "N/A")
                    if desc == "N/A" and server_name != "Unknown":
                        desc = f"{server_name} snapshot"
                    
                    # Formatiere Größe
                    size_gb = snapshot.get("image_size", 0)
                    formatted_size = self._format_size(size_gb)
                    
                    print(f"{snapshot['id']:<10} {desc:<50} {snapshot['created'][:19]:<20} {formatted_size:<12} {server_id:<15}")
                
                # Füge eine Leerzeile zwischen den Gruppen ein
                print()
                
        elif subcommand == "create":
            # Create a snapshot for a VM
            if len(args) < 2:
                print("Missing VM ID. Use 'snapshot create VM_ID'")
                return
                
            vm_id = int(args[1])
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
                
        elif subcommand == "delete":
            # Delete a snapshot by ID or all snapshots for a VM
            if len(args) < 2:
                print("Missing snapshot ID or 'all'. Use 'snapshot delete ID' or 'snapshot delete all VM_ID'")
                return
                
            if args[1].lower() == "all":
                # Delete all snapshots for a VM
                if len(args) < 3:
                    print("Missing VM ID. Use 'snapshot delete all VM_ID'")
                    return
                    
                vm_id = int(args[2])
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
                snapshot_id = int(args[1])
                confirm = input(f"Are you sure you want to delete snapshot {snapshot_id}? [y/N]: ")
                
                if confirm.lower() != 'y':
                    print("Operation cancelled")
                    return
                    
                if self.hetzner.delete_snapshot(snapshot_id):
                    print(f"Snapshot {snapshot_id} deleted successfully")
                else:
                    print(f"Failed to delete snapshot {snapshot_id}")
        else:
            print(f"Unknown snapshot subcommand: {subcommand}")
    
    def _format_size(self, size_gb: float) -> str:
        """Format size in GB or MB with 2 decimal places"""
        if size_gb >= 1:
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_gb * 1024:.2f} MB"
    
    def handle_backup_command(self, args: List[str]):
        """Handle backup-related commands"""
        if not args:
            print("Missing backup subcommand. Use 'backup list|enable|disable|delete'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            # List backups, optionally filtered by VM ID
            vm_id = int(args[1]) if len(args) > 1 else None
            
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
                    formatted_size = self._format_size(size_gb)
                    
                    print(f"{backup['id']:<10} {desc:<50} {backup['created'][:19]:<20} {formatted_size:<12} {server_id:<15}")
                
                # Füge eine Leerzeile zwischen den Gruppen ein
                print()
        
        elif subcommand == "enable":
            # Enable automatic backups for a VM
            if len(args) < 2:
                print("Missing VM ID. Use 'backup enable VM_ID [WINDOW]'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
            
            # Optional backup window parameter
            backup_window = args[2] if len(args) > 2 else None
            if backup_window and backup_window not in ["22-02", "02-06", "06-10", "10-14", "14-18", "18-22"]:
                print("Invalid backup window. Must be one of: 22-02, 02-06, 06-10, 10-14, 14-18, 18-22")
                return
                
            print(f"Enabling automatic backups for VM '{server.get('name')}' (ID: {vm_id})...")
            if self.hetzner.enable_server_backups(vm_id, backup_window):
                print(f"Automatic backups enabled successfully for VM {vm_id}")
            else:
                print(f"Failed to enable automatic backups for VM {vm_id}")
        
        elif subcommand == "disable":
            # Disable automatic backups for a VM
            if len(args) < 2:
                print("Missing VM ID. Use 'backup disable VM_ID'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            print(f"Disabling automatic backups for VM '{server.get('name')}' (ID: {vm_id})...")
            if self.hetzner.disable_server_backups(vm_id):
                print(f"Automatic backups disabled successfully for VM {vm_id}")
            else:
                print(f"Failed to disable automatic backups for VM {vm_id}")
        
        elif subcommand == "delete":
            # Delete a backup by ID
            if len(args) < 2:
                print("Missing backup ID. Use 'backup delete ID'")
                return
                
            backup_id = int(args[1])
            
            confirm = input(f"Are you sure you want to delete backup {backup_id}? [y/N]: ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return
                
            print(f"Deleting backup {backup_id}...")
            if self.hetzner.delete_backup(backup_id):
                print(f"Backup {backup_id} deleted successfully")
            else:
                print(f"Failed to delete backup {backup_id}")
        
        else:
            print(f"Unknown backup subcommand: {subcommand}")
    
    def handle_vm_command(self, args: List[str]):
        """Handle VM-related commands"""
        if not args:
            print("Missing VM subcommand. Use 'vm list|create|delete'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            # List all VMs
            servers = self.hetzner.list_servers()
            
            if not servers:
                print("No VMs found")
                return
                
            print("\nVirtual Machines:")
            print(f"{'ID':<10} {'Name':<30} {'Status':<10} {'Type':<15} {'IP':<15} {'Location':<10}")
            print("-" * 90)
            
            for server in servers:
                ip = server.get("public_net", {}).get("ipv4", {}).get("ip", "N/A")
                print(f"{server['id']:<10} {server['name']:<30} {server['status']:<10} {server['server_type']['name']:<15} {ip:<15} {server['datacenter']['location']['name']:<10}")
                
        elif subcommand == "info":
            # Show detailed information about a specific VM
            if len(args) < 2:
                print("Missing VM ID. Use 'vm info ID'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            print(f"\n{'='*60}")
            print(f"VM Information: \033[1;32m{server.get('name')}\033[0m (ID: {vm_id})")
            print(f"{'='*60}")
            
            # Grundlegende Informationen
            status = server.get('status', 'unknown')
            status_color = "\033[1;32m" if status == "running" else "\033[1;31m" if status == "off" else "\033[1;33m"
            print(f"Status: {status_color}{status}\033[0m")
            created = server.get('created', 'unknown')
            if created != 'unknown':
                created_date = created.split('T')[0]
                created_time = created.split('T')[1].split('+')[0] if '+' in created else created.split('T')[1].split('Z')[0]
                print(f"Created: {created_date} {created_time}")
            
            # Hardware-Informationen
            print("\nHardware:")
            server_type = server.get('server_type', {})
            print(f"  Type: {server_type.get('name', 'N/A')}")
            print(f"  CPU Cores: {server_type.get('cores', 'N/A')}")
            print(f"  Memory: {server_type.get('memory', 'N/A')} GB")
            print(f"  Disk: {server_type.get('disk', 'N/A')} GB")
            
            # Standort-Informationen
            print("\nLocation:")
            datacenter = server.get('datacenter', {})
            location = datacenter.get('location', {})
            print(f"  Datacenter: {datacenter.get('name', 'N/A')}")
            print(f"  City: {location.get('city', 'N/A')}")
            print(f"  Country: {location.get('country', 'N/A')}")
            
            # Netzwerkinformationen
            print("\nNetwork:")
            public_net = server.get('public_net', {})
            ipv4 = public_net.get('ipv4', {})
            ipv6 = public_net.get('ipv6', {})
            print(f"  IPv4: {ipv4.get('ip', 'N/A')}")
            print(f"  IPv6: {ipv6.get('ip', 'N/A')}")
            
            # DNS-Einträge
            dns_ptr = []
            for entry in public_net.get('dns_ptr', []):
                dns_ptr.append(f"{entry.get('ip', 'N/A')} -> {entry.get('dns_ptr', 'N/A')}")
            if dns_ptr:
                print("\nDNS Reverse Records:")
                for entry in dns_ptr:
                    print(f"  {entry}")
            
            # Volumes
            try:
                status_code, volumes_response = self.hetzner._make_request("GET", f"servers/{vm_id}/volumes")
                if status_code == 200:
                    volumes = volumes_response.get('volumes', [])
                    if volumes:
                        print("\nAttached Volumes:")
                        for vol in volumes:
                            print(f"  {vol.get('name', 'N/A')} ({vol.get('size', 'N/A')} GB)")
            except Exception:
                pass
            
            # Backup-Status
            backup_window = server.get('backup_window', 'disabled')
            if backup_window != 'disabled':
                print(f"\nBackup: Enabled (Window: {backup_window})")
            else:
                print("\nBackup: Disabled")
            
            # Image-Informationen
            print("\nImage Information:")
            image = server.get('image', {})
            print(f"  OS: {image.get('name', 'N/A')}")
            print(f"  Description: {image.get('description', 'N/A')}")
            
            # Protection-Informationen
            protection = server.get('protection', {})
            if protection:
                delete_protection = "Enabled" if protection.get('delete', False) else "Disabled"
                rebuild_protection = "Enabled" if protection.get('rebuild', False) else "Disabled"
                print("\nProtection:")
                print(f"  Delete Protection: {delete_protection}")
                print(f"  Rebuild Protection: {rebuild_protection}")
            
            # Preisberechnung (wenn verfügbar)
            try:
                status_code, pricing = self.hetzner._make_request("GET", "pricing")
                if status_code == 200:
                    server_prices = pricing.get('pricing', {}).get('server_types', [])
                    for price in server_prices:
                        if price.get('id') == server_type.get('id'):
                            price_monthly = price.get('prices', [{}])[0].get('price_monthly', {}).get('gross', 'N/A')
                            price_hourly = price.get('prices', [{}])[0].get('price_hourly', {}).get('gross', 'N/A')
                            if price_monthly != 'N/A' or price_hourly != 'N/A':
                                print("\nPricing:")
                                if price_monthly != 'N/A':
                                    print(f"  Monthly: {price_monthly} €")
                                if price_hourly != 'N/A':
                                    print(f"  Hourly: {price_hourly} €")
            except Exception:
                pass
                
            print(f"{'-'*60}")
                
        if subcommand == "create":
            print("Create a new VM:")
            name = input("Name: ")
            if not name:
                print("Name is required")
                return
                
            # Get available server types
            status_code, response = self.hetzner._make_request("GET", "server_types")
            if status_code != 200:
                print("Failed to get server types")
                return
                
            server_types = response.get("server_types", [])
            
            # Gruppiere nach Servertyp-Präfixen (unabhängig von Groß-/Kleinschreibung)
            server_type_groups = {
                "CAX": {"name": "ARM64 (shared vCPU)", "types": []},
                "CCX": {"name": "x86 AMD (dedicated vCPU)", "types": []},
                "CPX": {"name": "x86 AMD (shared vCPU)", "types": []},
                "CX": {"name": "x86 Intel (shared vCPU)", "types": []}
            }
            
            # Andere Typen
            other_types = []
            
            # Sortiere Server-Typen nach Gruppen (unabhängig von Groß-/Kleinschreibung)
            for st in server_types:
                st_name = st.get("name", "").upper()  # Konvertiere zu Großbuchstaben für Vergleich
                for prefix in server_type_groups.keys():
                    if st_name.startswith(prefix):
                        server_type_groups[prefix]["types"].append(st)
                        break
                else:
                    other_types.append(st)
            
            # Zeige Server-Typen nach Gruppe an
            print("\nAvailable Server Types:")
            print("-" * 80)
            
            type_options = []
            option_index = 1
            
            for prefix, group in server_type_groups.items():
                if group["types"]:
                    print(f"\n{group['name']}:")
                    for st in sorted(group["types"], key=lambda x: x.get("memory", 0)):
                        cores = st.get("cores", "N/A")
                        memory = st.get("memory", "N/A")
                        disk = st.get("disk", "N/A")
                        price_info = ""
                        try:
                            # Hetzner Preise sind in € pro Monat
                            price = float(st.get("prices", [{}])[0].get("price_monthly", {}).get("gross", 0))
                            if price > 0:
                                price_info = f", {price:.2f}€/mo"
                        except:
                            pass
                        
                        print(f"{option_index}. {st['name']} (Cores: {cores}, Memory: {memory} GB, Disk: {disk} GB{price_info})")
                        type_options.append(st)
                        option_index += 1
            
            # Andere Typen, falls vorhanden
            if other_types:
                print("\nOther Types:")
                for st in other_types:
                    cores = st.get("cores", "N/A")
                    memory = st.get("memory", "N/A")
                    disk = st.get("disk", "N/A")
                    print(f"{option_index}. {st['name']} (Cores: {cores}, Memory: {memory} GB, Disk: {disk} GB)")
                    type_options.append(st)
                    option_index += 1
                
            type_choice = input("\nSelect server type (number): ")
            try:
                type_index = int(type_choice) - 1
                if type_index < 0 or type_index >= len(type_options):
                    print("Invalid selection")
                    return
                server_type = type_options[type_index]["name"]
            except ValueError:
                print("Invalid input")
                return
                
            # Get available images
            status_code, response = self.hetzner._make_request("GET", "images?type=system")
            if status_code != 200:
                print("Failed to get images")
                return
                
            images = response.get("images", [])
            system_images = [img for img in images if img.get("type") == "system"]
            
            print("\nAvailable Images:")
            for i, img in enumerate(system_images):
                print(f"{i+1}. {img['name']} ({img['description']})")
                
            image_choice = input("\nSelect image (number): ")
            try:
                image_index = int(image_choice) - 1
                if image_index < 0 or image_index >= len(system_images):
                    print("Invalid selection")
                    return
                image = system_images[image_index]["name"]
            except ValueError:
                print("Invalid input")
                return
                
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
                
            # Get SSH keys
            status_code, response = self.hetzner._make_request("GET", "ssh_keys")
            ssh_keys = []
            
            if status_code == 200:
                available_keys = response.get("ssh_keys", [])
                if available_keys:
                    print("\nAvailable SSH Keys:")
                    for i, key in enumerate(available_keys):
                        print(f"{i+1}. {key['name']}")
                        
                    keys_choice = input("\nSelect SSH keys (comma-separated numbers or 'none'): ")
                    if keys_choice.lower() != "none":
                        try:
                            key_indices = [int(idx.strip()) - 1 for idx in keys_choice.split(",")]
                            ssh_keys = [available_keys[idx]["id"] for idx in key_indices if 0 <= idx < len(available_keys)]
                        except ValueError:
                            print("Invalid input, proceeding without SSH keys")
            
            # IP-Version auswählen
            print("\nIP Version:")
            print("1. IPv4 only")
            print("2. IPv6 only")
            print("3. Both IPv4 and IPv6 (default)")
            
            ip_choice = input("\nSelect IP version (number, default: 3): ").strip()
            
            ipv4 = True
            ipv6 = True
            
            if ip_choice == "1":
                ipv6 = False
            elif ip_choice == "2":
                ipv4 = False
            elif ip_choice != "" and ip_choice != "3":
                print("Invalid selection, using both IPv4 and IPv6")
            
            # Option für Root-Passwort
            generate_password = input("\nDo you want to set a root password? [y/N]: ").strip().lower()
            use_auto_password = generate_password == 'y'
            
            # Final confirmation
            print("\nVM Creation Summary:")
            print(f"  Name: {name}")
            print(f"  Type: {server_type}")
            print(f"  Image: {image}")
            print(f"  Location: {location}")
            print(f"  SSH Keys: {', '.join(str(k) for k in ssh_keys) if ssh_keys else 'None'}")
            print(f"  Network: {'IPv4' if ipv4 else ''}{' and ' if ipv4 and ipv6 else ''}{'IPv6' if ipv6 else ''}")
            print(f"  Root Password: {'Auto-generated' if use_auto_password else 'None'}")
            
            confirm = input("\nCreate this VM? [y/N]: ")
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return
                
            print("Creating VM...")
            
            # Bereite die Daten für die API vor
            data = {
                "name": name,
                "server_type": server_type,
                "image": image,
                "location": location,
                "public_net": {
                    "enable_ipv4": ipv4,
                    "enable_ipv6": ipv6
                }
            }
            
            if ssh_keys:
                data["ssh_keys"] = ssh_keys
                
            # Die standard API-Verhaltensweise ist: Wenn kein root_password gesetzt ist,
            # wird keines generiert AUSSER wenn 'start_after_create' true ist oder nicht spezifiziert ist
            # Wir setzen dies explizit, um je nach Benutzerauswahl ein Passwort zu forcieren oder nicht
            if use_auto_password:
                data["start_after_create"] = True
            else:
                data["start_after_create"] = False
                
            # Direkte API-Anfrage durchführen
            status_code, response = self.hetzner._make_request("POST", "servers", data)
            
            if status_code == 201:
                server = response.get("server", {})
                print(f"\nVM created successfully!")
                print(f"ID: {server.get('id')}")
                print(f"Name: {server.get('name')}")
                print(f"Status: {server.get('status')}")
                
                # IP-Adressen anzeigen
                public_net = server.get("public_net", {})
                if ipv4:
                    ipv4_info = public_net.get("ipv4", {})
                    print(f"IPv4: {ipv4_info.get('ip', 'N/A')}")
                if ipv6:
                    ipv6_info = public_net.get("ipv6", {})
                    print(f"IPv6: {ipv6_info.get('ip', 'N/A')}")
                
                # Root-Passwort anzeigen, wenn generiert
                if use_auto_password:
                    root_pass = response.get("root_password")
                    if root_pass:
                        print(f"\nROOT PASSWORD: {root_pass}")
                        print("IMPORTANT: Save this password now, it won't be shown again!")
                    else:
                        print("\nNo root password was generated by the API. You may need to reset it manually.")
            else:
                print(f"Failed to create VM: {response.get('error', {}).get('message', 'Unknown error')}")
                
        elif subcommand == "delete":
            # Delete a VM by ID
            if len(args) < 2:
                print("Missing VM ID. Use 'vm delete ID'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            confirm = input(f"Are you sure you want to delete VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
            
            if confirm.lower() != 'y':
                print("Operation cancelled")
                return
                
            print(f"Deleting VM {vm_id}...")
            if self.hetzner.delete_server(vm_id):
                print(f"VM {vm_id} deleted successfully")
            else:
                print(f"Failed to delete VM {vm_id}")
                
        elif subcommand == "start":
            # Start a VM by ID
            if len(args) < 2:
                print("Missing VM ID. Use 'vm start ID'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            if server.get("status") == "running":
                print(f"VM '{server.get('name')}' is already running")
                return
                
            print(f"Starting VM '{server.get('name')}' (ID: {vm_id})...")
            if self.hetzner.start_server(vm_id):
                print(f"VM {vm_id} started successfully")
            else:
                print(f"Failed to start VM {vm_id}")
                
        elif subcommand == "stop":
            # Stop a VM by ID
            if len(args) < 2:
                print("Missing VM ID. Use 'vm stop ID'")
                return
                
            vm_id = int(args[1])
            server = self.hetzner.get_server_by_id(vm_id)
            
            if not server:
                print(f"VM with ID {vm_id} not found")
                return
                
            if server.get("status") == "off":
                print(f"VM '{server.get('name')}' is already stopped")
                return
                
            print(f"Stopping VM '{server.get('name')}' (ID: {vm_id})...")
            if self.hetzner.stop_server(vm_id):
                print(f"VM {vm_id} stopped successfully")
            else:
                print(f"Failed to stop VM {vm_id}")
                
        else:
            print(f"Unknown VM subcommand: {subcommand}")
            
    def show_project_info(self):
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
                print(f"API Endpoint: {API_BASE_URL}")
                
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
                        print(f"    - {dc['name']} ({dc['location']['name']})")
                
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


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Hetzner Cloud CLI Tool")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--gen-config", help="Generate a sample configuration file")
    parser.add_argument("--project", help="Project to use from config file", default="default")
    parser.add_argument("--token", help="API token (overrides config file)")
    parser.add_argument("--version", action="version", version=f"hicloud v{VERSION}")
    
    args = parser.parse_args()
    
    # Ensure history directory exists
    if not os.path.exists(HISTORY_DIR):
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create history directory: {str(e)}")
    
    # Handle config generation
    if args.gen_config:
        ConfigManager.generate_config(args.gen_config)
        return 0
        
    # Load configuration
    config_path = args.config if args.config else DEFAULT_CONFIG_PATH
    config = {}
    
    if os.path.exists(config_path):
        config = ConfigManager.load_config(config_path)
        
    # Get API token
    api_token = None
    project_name = "default"
    
    if args.token:
        api_token = args.token
    elif args.project in config:
        api_token = config[args.project].get("api_token")
        project_name = config[args.project].get("project_name", args.project)
    elif "default" in config:
        api_token = config["default"].get("api_token")
        project_name = config["default"].get("project_name", "default")
        
    if not api_token:
        if not os.path.exists(config_path):
            print(f"No configuration file found at {config_path}")
            print(f"Generate one with: hicloud.py --gen-config {config_path}")
            print("Or provide an API token: hicloud.py --token YOUR_API_TOKEN")
        else:
            print(f"No API token found for project '{args.project}'")
        return 1
        
    # Create Hetzner Cloud manager
    hetzner = HetznerCloudManager(api_token, project_name)
    
    # Start interactive console
    console = InteractiveConsole(hetzner)
    console.start()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
