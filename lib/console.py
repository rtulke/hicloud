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
            "project": {
                "help": "Project commands: list, switch <n>, resources",
                "subcommands": {
                    "list": {"help": "List all available projects"},
                    "switch": {"help": "Switch to a different project: project switch <n>"},
                    "resources": {"help": "Show all resources in the current project"}
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
                "help": "SSH key commands: list, delete <id>",
                "subcommands": {
                    "list": {"help": "List all SSH keys"},
                    "delete": {"help": "Delete an SSH key: keys delete <id>"}
                }
            },
            "info": {"help": "Show current project information"},
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
            if state < len(matches):
                return matches[state]
            else:
                return None
        elif len(parts) == 1 and not line.endswith(' '):  # Erster Teil, noch nicht abgeschlossen
            # Nur Hauptbefehle vervollständigen, die mit dem Text beginnen
            cmd_part = parts[0]
            matches = [cmd for cmd in self.commands.keys() if cmd.startswith(cmd_part)]
            
            # Wenn wir genau eine Übereinstimmung haben, füge ein Leerzeichen hinzu
            if len(matches) == 1:
                return matches[0] + ' ' if state == 0 else None
                
            # Wenn wir mehrere Übereinstimmungen haben
            elif len(matches) > 1:
                # Finde gemeinsames Präfix (wenn vorhanden)
                if state == 0:
                    # Prüfe, ob es ein längeres gemeinsames Präfix gibt
                    if text != "":  # Nur wenn etwas eingegeben wurde
                        common_prefix = self._get_common_prefix(matches)
                        if common_prefix and len(common_prefix) > len(cmd_part):
                            return common_prefix
                    # Zeige die möglichen Matches an
                    print("\n\033[90mMatching commands: " + ", ".join(matches) + "\033[0m")
                    print("\nhicloud> " + line, end="", flush=True)
                
                # Gib die Matches je nach state zurück
                if state < len(matches):
                    return matches[state]
                else:
                    return None
            else:
                return None
                
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
                    return matches[0] + ' ' if state == 0 else None
                
                # Wenn wir mehrere Übereinstimmungen haben
                elif len(matches) > 1:
                    # Finde gemeinsames Präfix (wenn vorhanden)
                    if state == 0:
                        # Prüfe, ob es ein längeres gemeinsames Präfix gibt
                        if curr_part != "":  # Nur wenn etwas eingegeben wurde
                            common_prefix = self._get_common_prefix(matches)
                            if common_prefix and len(common_prefix) > len(curr_part):
                                return common_prefix
                        # Zeige die möglichen Matches an
                        print("\n\033[90mMatching subcommands: " + ", ".join(matches) + "\033[0m")
                        print("\nhicloud> " + line, end="", flush=True)
                    
                    # Gib den Match zurück je nach state
                    if state < len(matches):
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
                elif main_cmd == "pricing":
                    self.pricing_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "project":
                    self.project_commands.handle_command(parts[1:] if len(parts) > 1 else [])
                elif main_cmd == "info":
                    self.project_commands.show_info()
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

  vm commands:
    vm list                           - list all vms
    vm info <id>                      - show detailed information about a vm
    vm create                         - create a new vm (interactive)
    vm start <id>                     - start a vm
    vm stop <id>                      - stop a vm
    vm delete <id>                    - delete a vm by id
    
  snapshot commands:
    snapshot list                     - list all snapshots or for specific vm
    snapshot create                   - create a snapshot for a vm
    snapshot delete <id>              - delete a snapshot by id
    snapshot delete all               - delete all snapshots for a vm
    snapshot rebuild <id> <sv>        - rebuild a server from a snapshot
    
  backup commands:
    backup list                       - list all backups or for specific vm
    backup enable <id> [window]       - enable automatic backups for a vm
    backup disable <id>               - disable automatic backups for a vm
    backup delete <id>                - delete a backup by id
    
  monitoring commands:
    metrics list <id>                 - list available metrics for a server
    metrics cpu <id> [--hours=24]     - show cpu utilization metrics
    metrics traffic <id> [--days=7]   - show network traffic metrics
    
  project commands:
    project list                      - list all available projects
    project switch <n>                - switch to a different project
    project resources                 - show all resources in the current project
    info                              - show current project information
    
  pricing commands:
    pricing list                      - show pricing table for all resources
    pricing calculate                 - calculate monthly costs for current resources
    
  general commands:
    keys list                         - list all ssh keys
    keys delete <id>                  - delete an ssh key by id
    history                           - show command history
    history clear                     - clear command history
    clear, reset                      - clear screen
    help                              - show this help message
    exit, quit, q                     - exit the program
"""
        print(help_text)
