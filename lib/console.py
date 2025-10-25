#!/usr/bin/env python3
# lib/console.py - Interactive console manager for hicloud

import os
import platform
import readline

from typing import Dict, List
from utils.constants import HISTORY_DIR, HISTORY_FILE, HISTORY_MAX_LINES, VERSION
# Korrekte Imports für die Formatierungsfunktionen
from utils.formatting import get_terminal_width as _get_terminal_width
from utils.formatting import horizontal_line as _horizontal_line
from utils.formatting import print_table as _print_table

from commands.vm import VMCommands
from commands.snapshot import SnapshotCommands
from commands.backup import BackupCommands
from commands.metrics import MetricsCommands
from commands.project import ProjectCommands
from commands.pricing import PricingCommands
from commands.keys import KeysCommands
from commands.batch import BatchCommands
from commands.volume import VolumeCommands
from commands.iso import ISOCommands
from commands.location import LocationCommands, DatacenterCommands

class InteractiveConsole:
    """Interactive console for hicloud"""
    
    def __init__(self, hetzner, debug=False):
        """Initialize the interactive console with a Hetzner Cloud manager"""
        self.hetzner = hetzner
        self.debug = debug
        self.running = True
        self.history = []
        
        # Stelle sicher, dass das History-Verzeichnis existiert
        if not os.path.exists(HISTORY_DIR):
            try:
                os.makedirs(HISTORY_DIR, exist_ok=True)
                print(f"Created history directory: {HISTORY_DIR}")
            except Exception as e:
                print(f"Warning: Could not create history directory: {str(e)}")
        
        # Initialisiere Befehlsklassen
        self.vm_commands = VMCommands(self)
        self.snapshot_commands = SnapshotCommands(self)
        self.backup_commands = BackupCommands(self)
        self.metrics_commands = MetricsCommands(self)
        self.project_commands = ProjectCommands(self)
        self.pricing_commands = PricingCommands(self)
        self.keys_commands = KeysCommands(self)
        self.batch_commands = BatchCommands(self)
        self.volume_commands = VolumeCommands(self)
        self.iso_commands = ISOCommands(self)
        self.location_commands = LocationCommands(self)
        self.datacenter_commands = DatacenterCommands(self)
        
        # Konfiguriere readline für History-Unterstützung
        self._setup_readline()
        
    # Formatierungsfunktionen als Methodenwrapper
    def get_terminal_width(self):
        """Wrapper für die globale get_terminal_width Funktion"""
        return _get_terminal_width()
        
    def horizontal_line(self, char="="):
        """Wrapper für die globale horizontal_line Funktion"""
        return _horizontal_line(char)
        
    def print_table(self, headers, rows, title=None):
        """Wrapper für die globale print_table Funktion"""
        _print_table(headers, rows, title)
    
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
        
        # Tab-Vervollständigung deaktivieren (wir übernehmen die manuelle Steuerung)
        # Diese Einstellung verhindert das Standardverhalten von readline,
        # alle Vervollständigungen anzuzeigen, wenn zweimal Tab gedrückt wird
        try:
            readline.set_completion_display_matches_hook(lambda *args: None)
        except:
            pass  # Ignorieren, wenn nicht unterstützt
        
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
                "help": "VM commands: list, info <id>, create, start <id>, stop <id>, delete <id>, resize <id> <type>, rename <id> <n>, rescue <id>, reset-password <id>, image <id> <n>",
                "subcommands": {
                    "list": {"help": "List all VMs"},
                    "info": {"help": "Show detailed information about a VM: vm info <id>"},
                    "create": {"help": "Create a new VM (interactive)"},
                    "start": {"help": "Start a VM: vm start <id>"},
                    "stop": {"help": "Stop a VM: vm stop <id>"},
                    "delete": {"help": "Delete a VM: vm delete <id>"},
                    "resize": {"help": "Change server type: vm resize <id> <new_type>"},
                    "rename": {"help": "Rename a VM: vm rename <id> <new_name>"},
                    "rescue": {"help": "Enable rescue mode: vm rescue <id>"},
                    "reset-password": {"help": "Reset root password: vm reset-password <id>"},
                    "image": {"help": "Create custom image: vm image <id> <n>"}
                }
            },
            "snapshot": {
                "help": "Snapshot commands: list, create, delete <id>, delete all, rebuild <id>",
                "subcommands": {
                    "list": {"help": "List all snapshots or for specific VM"},
                    "create": {"help": "Create a snapshot for a VM"},
                    "delete": {"help": "Delete a snapshot: snapshot delete <id>"},
                    "all": {"help": "Delete all snapshots for a VM: snapshot delete all"},
                    "rebuild": {"help": "Rebuild a server from a snapshot: snapshot rebuild <id> <server_id>"}
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
            "metrics": {
                "help": "Metrics commands: list <id>, cpu <id> [--hours=24], traffic <id> [--days=7]",
                "subcommands": {
                    "list": {"help": "List available metrics for a server: metrics list <id>"},
                    "cpu": {"help": "Show CPU utilization metrics: metrics cpu <id> [--hours=24]"},
                    "traffic": {"help": "Show network traffic metrics: metrics traffic <id> [--days=7]"}
                }
            },
            "batch": {
                "help": "Batch commands: start <id1,id2,id3...>, stop <id1,id2,id3...>, delete <id1,id2,id3...>, snapshot <id1,id2,id3...>",
                "subcommands": {
                    "start": {"help": "Start multiple servers: batch start <id1,id2,id3...>"},
                    "stop": {"help": "Stop multiple servers: batch stop <id1,id2,id3...>"},
                    "delete": {"help": "Delete multiple servers: batch delete <id1,id2,id3...>"},
                    "snapshot": {"help": "Create snapshots for multiple servers: batch snapshot <id1,id2,id3...>"}
                }
            },
            "project": {
                "help": "Project commands: list, switch <n>, resources, info",
                "subcommands": {
                    "list": {"help": "List all available projects"},
                    "switch": {"help": "Switch to a different project: project switch <n>"},
                    "resources": {"help": "Show all resources in the current project"},
                    "info": {"help": "Show detailed information about the current project"}
                }
            },
            "pricing": {
                "help": "Pricing commands: list, calculate",
                "subcommands": {
                    "list": {"help": "Show pricing table for all resources"},
                    "calculate": {"help": "Calculate estimated monthly costs for current resources"}
                }
            },
            "keys": {
                "help": "SSH key commands: list, info <id>, create, update <id>, delete <id>",
                "subcommands": {
                    "list": {"help": "List all SSH keys"},
                    "info": {"help": "Show detailed information about an SSH key: keys info <id>"},
                    "create": {"help": "Create/upload a new SSH key: keys create [name] [file]"},
                    "update": {"help": "Update SSH key metadata: keys update <id>"},
                    "delete": {"help": "Delete an SSH key: keys delete <id>"}
                }
            },
            "volume": {
                "help": "Volume commands: list, info <id>, create, delete <id>, attach <vid> <sid>, detach <id>, resize <id> <size>, protect <id> <enable|disable>",
                "subcommands": {
                    "list": {"help": "List all volumes"},
                    "info": {"help": "Show detailed information about a volume: volume info <id>"},
                    "create": {"help": "Create a new volume (interactive)"},
                    "delete": {"help": "Delete a volume: volume delete <id>"},
                    "attach": {"help": "Attach volume to server: volume attach <volume_id> <server_id>"},
                    "detach": {"help": "Detach volume from server: volume detach <id>"},
                    "resize": {"help": "Resize a volume: volume resize <id> <new_size_gb>"},
                    "protect": {"help": "Enable/disable volume protection: volume protect <id> <enable|disable>"}
                }
            },
            "iso": {
                "help": "ISO commands: list, info <id>, attach <iso_id> <server_id>, detach <server_id>",
                "subcommands": {
                    "list": {"help": "List all available ISOs"},
                    "info": {"help": "Show detailed information about an ISO: iso info <id>"},
                    "attach": {"help": "Attach ISO to server: iso attach <iso_id> <server_id>"},
                    "detach": {"help": "Detach ISO from server: iso detach <server_id>"}
                }
            },
            "location": {
                "help": "Location commands: list, info <id>",
                "subcommands": {
                    "list": {"help": "List all available locations"},
                    "info": {"help": "Show detailed information about a location: location info <id>"}
                }
            },
            "datacenter": {
                "help": "Datacenter commands: list, info <id>",
                "subcommands": {
                    "list": {"help": "List all available datacenters"},
                    "info": {"help": "Show detailed information about a datacenter: datacenter info <id>"}
                }
            },
            "history": {
                "help": "Command history: history, history clear",
                "subcommands": {
                    "clear": {"help": "Clear command history"}
                }
            },
            "clear": {"help": "Clear screen"},
            "reset": {"help": "Clear screen (alias for 'clear')"},
            "help": {"help": "Show help information"},
            "exit": {"help": "Exit the program"},
            "quit": {"help": "Exit the program"},
            "q": {"help": "Exit the program"}
        }
    
    def _command_completer(self, text, state):
        """Vereinfachter Command Completer"""
        buffer = readline.get_line_buffer()
        line = buffer.lstrip()
        
        # Wenn wir das zweite Mal Tab drücken (state > 0), nix tun
        if state > 0:
            return None
                
        # Teile die Eingabe in Wörter auf
        parts = line.split()
        
        if not parts:
            # Zeige die Liste der Hauptbefehle an
            print("\n\033[90mAvailable commands: " + ", ".join(sorted(self.commands.keys())) + "\033[0m")
            print("\nhicloud> " + line, end="", flush=True)
            return None
        
        # Hauptbefehl
        cmd = parts[0]
        
        # Hauptbefehl vervollständigen
        if len(parts) == 1 and not line.endswith(' '):
            matches = [c for c in self.commands.keys() if c.startswith(cmd)]
            if len(matches) == 1:
                # Nur ein passender Befehl - vollständiger Befehl + Leerzeichen
                return matches[0] + ' '
            elif len(matches) > 0:
                # Mehrere Treffer - zeige den Hilfetext an
                print("\n\033[90mMatching commands: " + ", ".join(matches) + "\033[0m")
                print("\nhicloud> " + line, end="", flush=True)
                
                # Gemeinsames Präfix finden
                common = self._get_common_prefix(matches)
                if common and len(common) > len(cmd):
                    return common
            return None
        
        # Unterbefehl vervollständigen
        if cmd in self.commands:
            # Zeige den Hilfetext für den Hauptbefehl an
            if len(parts) == 1 and line.endswith(' '):
                print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
                print("\nhicloud> " + line, end="", flush=True)
                return None
            
            # Unterbefehl-Vervollständigung    
            if 'subcommands' in self.commands[cmd] and len(parts) >= 2:
                # Hier ist text der zu vervollständigende Teil, nicht parts[-1]
                # Es kann unterschiedlich sein, wenn der Benutzer mehrere Teile hat
                subcmd_part = text
                
                # Zeige den Hilfetext für den Hauptbefehl an
                print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
                print("\nhicloud> " + line, end="", flush=True)
                
                # Passende Unterbefehle finden
                matches = [sc for sc in self.commands[cmd]['subcommands'] 
                        if sc.startswith(subcmd_part)]
                        
                if len(matches) == 1:
                    # Für readline muss die Rückgabe genau dem zu ersetzenden Text entsprechen
                    # Daher geben wir den kompletten Treffer zurück, nicht nur den Rest
                    return matches[0]
                
                # Gemeinsames Präfix finden
                if len(matches) > 1:
                    common = self._get_common_prefix(matches)
                    if common and len(common) > len(subcmd_part):
                        # Gleiches gilt hier: vollständiges gemeinsames Präfix zurückgeben
                        return common
                        
        return None
    
    def _show_command_help(self, cmd):
        """Zeigt Hilfe für einen Hauptbefehl an"""
        if cmd in self.commands and 'help' in self.commands[cmd]:
            # Zeige die Hilfe über dem Prompt
            print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
            print("\nhicloud> ", end="", flush=True)
            
    def _get_common_prefix(self, strings):
        """Findet das gemeinsame Präfix aller Strings in der Liste"""
        if not strings:
            return ""
        if len(strings) == 1:
            return strings[0]
            
        prefix = strings[0]
        for s in strings[1:]:
            i = 0
            while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
                i += 1
            prefix = prefix[:i]
            if not prefix:
                break
        
        return prefix
    
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
            print(self.horizontal_line('-'))
            
            # History-Einträge abrufen (ohne den aktuellen 'history' Befehl)
            for i in range(1, hist_len):
                # Index beginnt bei 1, nicht bei 0
                item = readline.get_history_item(i)
                if item:
                    print(f"{i:4d}  {item}")
            print(self.horizontal_line('-'))
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
        width = self.get_terminal_width()
        
        print(f"\n{self.horizontal_line('=')}")
        
        # Zentrieren des Titels
        title = f"hicloud Interactive Console v{VERSION}"
        padding = (width - len(title)) // 2
        print(" " * padding + title)
        
        print(f"{self.horizontal_line('=')}")
        print(f"Active Project: \033[1;32m{self.hetzner.project_name}\033[0m")
        
        # Debug-Modus anzeigen, wenn aktiviert
        if self.debug:
            print(f"Debug Mode: \033[1;33mEnabled\033[0m")
        
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
            
        print(f"{self.horizontal_line('-')}")
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
                elif main_cmd in ["clear", "reset"]:
                    self._clear_screen()
                    self._display_welcome_screen()
                elif main_cmd == "snapshot":
                    self.snapshot_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "backup":
                    self.backup_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "vm" or main_cmd == "server":
                    self.vm_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "keys":
                    self.keys_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "metrics":
                    self.metrics_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "batch":
                    self.batch_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "pricing":
                    self.pricing_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "project":
                    self.project_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "volume":
                    self.volume_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "iso":
                    self.iso_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "location":
                    self.location_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "datacenter":
                    self.datacenter_commands.handle_command(parts[1:] if len(parts) > 1 else [])
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
    vm list                           - List all VMs
    vm info <id>                      - Show detailed information about a VM
    vm create                         - Create a new VM (interactive)
    vm start <id>                     - Start a VM
    vm stop <id>                      - Stop a VM
    vm delete <id>                    - Delete a VM by ID
    vm resize <id> <type>             - Change server type
    vm rename <id> <name>             - Rename a VM
    vm rescue <id>                    - Enable rescue mode
    vm reset-password <id>            - Reset root password
    vm image <id> <name>              - Create custom image from VM
    
  Snapshot Commands:
    snapshot list                     - List all snapshots or for specific VM
    snapshot create                   - Create a snapshot for a VM
    snapshot delete <id>              - Delete a snapshot by ID
    snapshot delete all               - Delete all snapshots for a VM
    snapshot rebuild <id> <sv>        - Rebuild a server from a snapshot
    
  Backup Commands:
    backup list                       - List all backups or for specific VM
    backup enable <id> [WINDOW]       - Enable automatic backups for a VM
    backup disable <id>               - Disable automatic backups for a VM
    backup delete <id>                - Delete a backup by ID
    
  Monitoring Commands:
    metrics list <id>                 - List available metrics for a server
    metrics cpu <id> [--hours=24]     - Show CPU utilization metrics
    metrics traffic <id> [--days=7]   - Show network traffic metrics

  Batch Commands:
    batch start <id1,id2,id3...>      - Start multiple servers
    batch stop <id1,id2,id3...>       - Stop multiple servers
    batch delete <id1,id2,id3...>     - Delete multiple servers
    batch snapshot <id1,id2,id3...>   - Create snapshots for multiple servers

  Project Commands:
    project list                      - List all available projects
    project switch <n>                - Switch to a different project
    project resources                 - Show all resources in the current project
    project info                      - Show current project information
    
  Pricing Commands:
    pricing list                      - Show pricing table for all resources
    pricing calculate                 - Calculate monthly costs for current resources

  Volume Commands:
    volume list                       - List all volumes
    volume info <id>                  - Show detailed information about a volume
    volume create                     - Create a new volume (interactive)
    volume delete <id>                - Delete a volume by ID
    volume attach <vid> <sid>         - Attach volume to server
    volume detach <id>                - Detach volume from server
    volume resize <id> <size>         - Resize a volume (increase only)
    volume protect <id> <e|d>         - Enable/disable volume protection

  ISO Commands:
    iso list                          - List all available ISOs
    iso info <id>                     - Show detailed information about an ISO
    iso attach <iso_id> <server_id>   - Attach ISO to server
    iso detach <server_id>            - Detach ISO from server

  Location & Datacenter Commands:
    location list                     - List all available locations
    location info <id>                - Show detailed information about a location
    datacenter list                   - List all available datacenters
    datacenter info <id>              - Show detailed information about a datacenter

  General Commands:
    keys list                         - List all SSH keys
    keys info <id>                    - Show detailed information about an SSH key
    keys create [name] [file]         - Create/upload a new SSH key
    keys update <id>                  - Update SSH key metadata (name, labels)
    keys delete <id>                  - Delete an SSH key by ID
    history                           - Show command history
    history clear                     - Clear command history
    clear, reset                      - Clear screen
    help                              - Show this help message
    exit, quit, q                     - Exit the program
"""
        print(help_text)
