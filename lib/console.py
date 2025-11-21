#!/usr/bin/env python3
# lib/console.py - Interactive console manager for hicloud

import os
import platform
import readline
import sys
import time
import toml
from contextlib import contextmanager

from typing import Dict, List, Optional
from utils.constants import (
    HISTORY_DIR,
    HISTORY_FILE,
    HISTORY_MAX_LINES,
    VERSION,
    DEFAULT_CONFIG_PATH,
)
from lib.config import ConfigManager
# Korrekte Imports für die Formatierungsfunktionen
from utils.formatting import get_terminal_width as _get_terminal_width
from utils.formatting import horizontal_line as _horizontal_line
from utils.formatting import print_table as _print_table
from utils.colors import PROMPT_TEXT_COLOR, PROMPT_ARROW_COLOR, ANSI_RESET

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
from commands.network import NetworkCommands


class _LeadingNewlineWriter:
    """Normalize leading/trailing whitespace around a command response."""

    def __init__(self, stream):
        self.stream = stream
        self.leading = True
        self.pending_newlines = ""

    def write(self, data):
        if not data:
            return

        chunk = data

        if self.leading:
            chunk = chunk.lstrip("\n")
            if chunk:
                self.stream.write("\n")
                self.leading = False
            else:
                return

        if not chunk:
            return

        if self.pending_newlines:
            chunk = self.pending_newlines + chunk
            self.pending_newlines = ""

        trailing_len = len(chunk) - len(chunk.rstrip("\n"))
        body = chunk[:-trailing_len] if trailing_len else chunk

        if body:
            self.stream.write(body)

        if trailing_len:
            self.pending_newlines = "\n" * trailing_len

    def finalize(self):
        if self.pending_newlines:
            self.stream.write("\n")
            self.pending_newlines = ""
        elif not self.leading:
            self.stream.write("\n")
        else:
            self.stream.write("\n")
        self.stream.flush()

    def flush(self):
        self.stream.flush()

    def isatty(self):
        return hasattr(self.stream, "isatty") and self.stream.isatty()

class InteractiveConsole:
    """Interactive console for hicloud"""
    
    def __init__(self, hetzner, debug=False):
        """Initialize the interactive console with a Hetzner Cloud manager"""
        self.hetzner = hetzner
        self.debug = debug
        self.running = True
        self.history = []
        self._completion_cache = {}
        self.prompt_label = f"{PROMPT_TEXT_COLOR}hicloud{ANSI_RESET}{PROMPT_ARROW_COLOR}>{ANSI_RESET}"
        self.prompt_string = f"\n{self.prompt_label} "
        
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
        self.network_commands = NetworkCommands(self)
        
        # Konfiguriere readline für History-Unterstützung
        self._setup_readline()
        
    def _print_prompt_with_line(self, line: str = "") -> None:
        """Render the colored prompt optionally followed by existing buffer contents"""
        print(f"\n{self.prompt_label} {line}", end="", flush=True)

    @contextmanager
    def _command_output(self):
        """Ensure every command response starts with exactly one blank line."""
        original_stdout = sys.stdout
        wrapper = _LeadingNewlineWriter(original_stdout)
        try:
            sys.stdout = wrapper
            yield
        finally:
            sys.stdout = original_stdout
            wrapper.finalize()
        
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
                doc = (readline.__doc__ or "").lower()
                is_libedit = "libedit" in doc

                if is_libedit or platform.system() == 'Darwin':
                    # macOS/libedit bindings
                    readline.parse_and_bind("bind ^I rl_complete")
                    libedit_bindings = [
                        '"\\e[5~": ed-prev-history',
                        '"\\e[6~": ed-next-history',
                        '"\\e[5;2~": ed-prev-history',
                        '"\\e[6;2~": ed-next-history',
                        '"\\e[5;5~": ed-prev-history',
                        '"\\e[6;5~": ed-next-history',
                        '"\\e[5;6~": ed-prev-history',
                        '"\\e[6;6~": ed-next-history',
                    ]
                    for binding in libedit_bindings:
                        try:
                            readline.parse_and_bind(binding)
                        except Exception:
                            continue
                else:
                    # Linux and other GNU readline environments
                    readline.parse_and_bind("tab: complete")
                    bindings = [
                        '"\\e[5~": previous-history',
                        '"\\e[6~": next-history',
                        '"\\e[5;2~": previous-history',
                        '"\\e[6;2~": next-history',
                        '"\\e[5;5~": previous-history',
                        '"\\e[6;5~": next-history',
                        '"\\e[5;6~": previous-history',
                        '"\\e[6;6~": next-history',
                    ]
                    for binding in bindings:
                        try:
                            readline.parse_and_bind(binding)
                        except Exception:
                            continue
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
                    "info": {
                        "help": "Show detailed information about a VM: vm info <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "create": {"help": "Create a new VM (interactive)"},
                    "start": {
                        "help": "Start a VM: vm start <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "stop": {
                        "help": "Stop a VM: vm stop <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "delete": {
                        "help": "Delete a VM: vm delete <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "resize": {
                        "help": "Change server type: vm resize <id> <new_type>",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids"},
                            {"name": "server_type"},
                        ],
                    },
                    "rename": {
                        "help": "Rename a VM: vm rename <id> <new_name>",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids"},
                            {"name": "new_name"},
                        ],
                    },
                    "rescue": {
                        "help": "Enable rescue mode: vm rescue <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "reset-password": {
                        "help": "Reset root password: vm reset-password <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "image": {
                        "help": "Create custom image: vm image <id> <n>",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids"},
                            {"name": "description"},
                        ],
                    }
                }
            },
            "snapshot": {
                "help": "Snapshot commands: list, create, delete <id>, delete all, rebuild <id>",
                "subcommands": {
                    "list": {
                        "help": "List all snapshots or for specific VM",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids", "optional": True}
                        ],
                    },
                    "create": {
                        "help": "Create a snapshot for a VM",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "delete": {
                        "help": "Delete a snapshot: snapshot delete <id>",
                        "arguments": [{"name": "snapshot_id", "provider": "snapshot_ids"}],
                    },
                    "all": {"help": "Delete all snapshots for a VM: snapshot delete all"},
                    "rebuild": {
                        "help": "Rebuild a server from a snapshot: snapshot rebuild <id> <server_id>",
                        "arguments": [
                            {"name": "snapshot_id", "provider": "snapshot_ids"},
                            {"name": "server_id", "provider": "server_ids"},
                        ],
                    }
                }
            },
            "backup": {
                "help": "Backup commands: list, enable <id> [WINDOW], disable <id>, delete <id>",
                "subcommands": {
                    "list": {
                        "help": "List all backups or for specific VM",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids", "optional": True}
                        ],
                    },
                    "enable": {
                        "help": "Enable automatic backups for a VM: backup enable <id> [WINDOW]",
                        "arguments": [
                            {"name": "server_id", "provider": "server_ids"},
                            {
                                "name": "window",
                                "provider": "backup_windows",
                                "optional": True,
                            },
                        ],
                    },
                    "disable": {
                        "help": "Disable automatic backups for a VM: backup disable <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "delete": {
                        "help": "Delete a backup: backup delete <id>",
                        "arguments": [{"name": "backup_id", "provider": "backup_ids"}],
                    }
                }
            },
            "metrics": {
                "help": "Metrics commands: list <id>, cpu <id> [--hours=24], traffic <id> [--days=7], disk <id> [--days=1]",
                "subcommands": {
                    "list": {
                        "help": "List available metrics for a server: metrics list <id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "cpu": {
                        "help": "Show CPU utilization metrics: metrics cpu <id> [--hours=24]",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "traffic": {
                        "help": "Show network traffic metrics: metrics traffic <id> [--days=7]",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    },
                    "disk": {
                        "help": "Show disk I/O metrics: metrics disk <id> [--days=1]",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    }
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
                    "switch": {
                        "help": "Switch to a different project: project switch <n>",
                        "arguments": [{"name": "project_name", "provider": "project_names"}],
                    },
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
                    "info": {
                        "help": "Show detailed information about an SSH key: keys info <id>",
                        "arguments": [{"name": "ssh_key_id", "provider": "ssh_key_ids"}],
                    },
                    "create": {"help": "Create/upload a new SSH key: keys create [name] [file]"},
                    "update": {
                        "help": "Update SSH key metadata: keys update <id>",
                        "arguments": [{"name": "ssh_key_id", "provider": "ssh_key_ids"}],
                    },
                    "delete": {
                        "help": "Delete an SSH key: keys delete <id>",
                        "arguments": [{"name": "ssh_key_id", "provider": "ssh_key_ids"}],
                    }
                }
            },
            "volume": {
                "help": "Volume commands: list, info <id>, create, delete <id>, attach <vid> <sid>, detach <id>, resize <id> <size>, protect <id> <enable|disable>",
                "subcommands": {
                    "list": {"help": "List all volumes"},
                    "info": {
                        "help": "Show detailed information about a volume: volume info <id>",
                        "arguments": [{"name": "volume_id", "provider": "volume_ids"}],
                    },
                    "create": {"help": "Create a new volume (interactive)"},
                    "delete": {
                        "help": "Delete a volume: volume delete <id>",
                        "arguments": [{"name": "volume_id", "provider": "volume_ids"}],
                    },
                    "attach": {
                        "help": "Attach volume to server: volume attach <volume_id> <server_id>",
                        "arguments": [
                            {"name": "volume_id", "provider": "volume_ids"},
                            {"name": "server_id", "provider": "server_ids"},
                        ],
                    },
                    "detach": {
                        "help": "Detach volume from server: volume detach <id>",
                        "arguments": [{"name": "volume_id", "provider": "volume_ids"}],
                    },
                    "resize": {
                        "help": "Resize a volume: volume resize <id> <new_size_gb>",
                        "arguments": [{"name": "volume_id", "provider": "volume_ids"}],
                    },
                    "protect": {
                        "help": "Enable/disable volume protection: volume protect <id> <enable|disable>",
                        "arguments": [{"name": "volume_id", "provider": "volume_ids"}],
                    }
                }
            },
            "network": {
                "help": "Network commands: list, info <id>, create, update <id>, delete <id>, attach <nid> <sid>, detach <nid> <sid>, subnet add|delete, protect <id> <enable|disable>",
                "subcommands": {
                    "list": {"help": "List all networks"},
                    "info": {
                        "help": "Show detailed information about a network: network info <id>",
                        "arguments": [{"name": "network_id", "provider": "network_ids"}],
                    },
                    "create": {"help": "Create a new network (interactive)"},
                    "update": {
                        "help": "Update network metadata: network update <id>",
                        "arguments": [{"name": "network_id", "provider": "network_ids"}],
                    },
                    "delete": {
                        "help": "Delete a network: network delete <id>",
                        "arguments": [{"name": "network_id", "provider": "network_ids"}],
                    },
                    "attach": {
                        "help": "Attach server to network: network attach <network_id> <server_id> [ip]",
                        "arguments": [
                            {"name": "network_id", "provider": "network_ids"},
                            {"name": "server_id", "provider": "server_ids"},
                        ],
                    },
                    "detach": {
                        "help": "Detach server from network: network detach <network_id> <server_id>",
                        "arguments": [
                            {"name": "network_id", "provider": "network_ids"},
                            {"name": "server_id", "provider": "server_ids"},
                        ],
                    },
                    "subnet": {"help": "Manage subnets: network subnet add|delete <network_id> ..."},
                    "protect": {
                        "help": "Enable/disable network protection: network protect <id> <enable|disable>",
                        "arguments": [{"name": "network_id", "provider": "network_ids"}],
                    }
                }
            },
            "iso": {
                "help": "ISO commands: list, info <id>, attach <iso_id> <server_id>, detach <server_id>",
                "subcommands": {
                    "list": {"help": "List all available ISOs"},
                    "info": {
                        "help": "Show detailed information about an ISO: iso info <id>",
                        "arguments": [{"name": "iso_id", "provider": "iso_ids"}],
                    },
                    "attach": {
                        "help": "Attach ISO to server: iso attach <iso_id> <server_id>",
                        "arguments": [
                            {"name": "iso_id", "provider": "iso_ids"},
                            {"name": "server_id", "provider": "server_ids"},
                        ],
                    },
                    "detach": {
                        "help": "Detach ISO from server: iso detach <server_id>",
                        "arguments": [{"name": "server_id", "provider": "server_ids"}],
                    }
                }
            },
            "location": {
                "help": "Location commands: list, info <id>",
                "subcommands": {
                    "list": {"help": "List all available locations"},
                    "info": {
                        "help": "Show detailed information about a location: location info <id>",
                        "arguments": [{"name": "location_id", "provider": "location_ids"}],
                    }
                }
            },
            "datacenter": {
                "help": "Datacenter commands: list, info <id>",
                "subcommands": {
                    "list": {"help": "List all available datacenters"},
                    "info": {
                        "help": "Show detailed information about a datacenter: datacenter info <id>",
                        "arguments": [{"name": "datacenter_id", "provider": "datacenter_ids"}],
                    }
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
            "help": {
                "help": "Show help information",
                "arguments": [
                    {"name": "command", "provider": "commands", "optional": True}
                ],
            },
            "exit": {"help": "Exit the program"},
            "quit": {"help": "Exit the program"},
            "q": {"help": "Exit the program"}
        }
        
        self.argument_providers = {
            "commands": self._get_command_names,
            "server_ids": self._get_server_ids,
            "snapshot_ids": self._get_snapshot_ids,
            "backup_ids": self._get_backup_ids,
            "volume_ids": self._get_volume_ids,
            "network_ids": self._get_network_ids,
            "iso_ids": self._get_iso_ids,
            "ssh_key_ids": self._get_ssh_key_ids,
            "location_ids": self._get_location_ids,
            "datacenter_ids": self._get_datacenter_ids,
            "project_names": self._get_project_names,
            "backup_windows": self._get_backup_windows,
        }
    
    def _get_cached_values(self, key: str, fetcher, ttl: int = 10) -> List[str]:
        """Return cached completion values for a provider"""
        entry = self._completion_cache.get(key)
        now = time.time()
        if entry and now - entry["timestamp"] < ttl:
            return entry["values"]
        
        try:
            values = fetcher()
        except Exception:
            values = []
        if not isinstance(values, list):
            values = list(values or [])
        self._completion_cache[key] = {"timestamp": now, "values": values}
        return values
    
    def _get_argument_values(self, provider_key: str) -> List[str]:
        """Resolve argument suggestions for a provider"""
        provider = self.argument_providers.get(provider_key)
        if not provider:
            return []
        try:
            return provider()
        except Exception:
            return []
    
    def _get_command_names(self) -> List[str]:
        """Return sorted list of top-level commands"""
        return sorted(self.commands.keys())
    
    def _get_server_ids(self) -> List[str]:
        return self._get_cached_values(
            "server_ids",
            lambda: [str(server.get("id")) for server in self.hetzner.list_servers()],
        )
    
    def _get_snapshot_ids(self) -> List[str]:
        return self._get_cached_values(
            "snapshot_ids",
            lambda: [str(snapshot.get("id")) for snapshot in self.hetzner.list_snapshots()],
        )
    
    def _get_backup_ids(self) -> List[str]:
        return self._get_cached_values(
            "backup_ids",
            lambda: [str(backup.get("id")) for backup in self.hetzner.list_backups()],
        )
    
    def _get_volume_ids(self) -> List[str]:
        return self._get_cached_values(
            "volume_ids",
            lambda: [str(volume.get("id")) for volume in self.hetzner.list_volumes()],
        )
    
    def _get_network_ids(self) -> List[str]:
        return self._get_cached_values(
            "network_ids",
            lambda: [str(network.get("id")) for network in self.hetzner.list_networks()],
        )
    
    def _get_iso_ids(self) -> List[str]:
        return self._get_cached_values(
            "iso_ids",
            lambda: [str(iso.get("id")) for iso in self.hetzner.list_isos()],
        )
    
    def _get_ssh_key_ids(self) -> List[str]:
        return self._get_cached_values(
            "ssh_key_ids",
            lambda: [str(key.get("id")) for key in self.hetzner.list_ssh_keys()],
        )
    
    def _get_location_ids(self) -> List[str]:
        return self._get_cached_values(
            "location_ids",
            lambda: [str(loc.get("id")) for loc in self.hetzner.list_locations()],
        )
    
    def _get_datacenter_ids(self) -> List[str]:
        return self._get_cached_values(
            "datacenter_ids",
            lambda: [str(dc.get("id")) for dc in self.hetzner.list_datacenters()],
        )
    
    def _get_project_names(self) -> List[str]:
        if not os.path.exists(DEFAULT_CONFIG_PATH):
            return []
        if not ConfigManager.check_file_permissions(DEFAULT_CONFIG_PATH):
            return []
        try:
            data = toml.load(DEFAULT_CONFIG_PATH)
            return sorted(data.keys())
        except Exception:
            return []
    
    def _get_backup_windows(self) -> List[str]:
        return ["22-02", "02-06", "06-10", "10-14", "14-18", "18-22"]
    
    def _command_completer(self, text, state):
        """Context-aware command completer built from command metadata"""
        buffer = readline.get_line_buffer()
        line = buffer.lstrip()
        ends_with_space = line.endswith(" ")
        
        if state > 0:
            return None
        
        parts = line.split()
        if not parts:
            return self._complete_main_command(text, line)
        
        if len(parts) == 1 and not ends_with_space:
            return self._complete_main_command(text, line)
        
        cmd_name = parts[0]
        cmd_info = self.commands.get(cmd_name)
        if not cmd_info:
            return None
        
        subcommands = cmd_info.get("subcommands")
        if subcommands:
            if len(parts) == 1 and ends_with_space:
                self._show_command_help(cmd_name)
                return None
            
            if len(parts) == 2 and not ends_with_space:
                return self._complete_subcommand(cmd_name, text, line)
            
            if len(parts) >= 2:
                subcmd_name = parts[1]
                if subcmd_name not in subcommands:
                    return self._complete_subcommand(cmd_name, text, line)
                
                if len(parts) == 2 and ends_with_space and not subcommands[subcmd_name].get("arguments"):
                    return None
                
                return self._complete_arguments(cmd_name, subcmd_name, parts, text, line, ends_with_space)
        
        # Commands without subcommands but with arguments
        if cmd_info.get("arguments"):
            return self._complete_arguments(cmd_name, None, parts, text, line, ends_with_space)
        
        return None
    
    def _complete_main_command(self, prefix: str, line: str) -> Optional[str]:
        commands = self._get_command_names()
        if not prefix:
            print("\n\033[90mAvailable commands: " + ", ".join(commands) + "\033[0m")
            self._print_prompt_with_line(line)
            return None
        
        matches = [cmd for cmd in commands if cmd.startswith(prefix)]
        if len(matches) == 1:
            return matches[0] + " "
        if matches:
            print("\n\033[90mMatching commands: " + ", ".join(matches) + "\033[0m")
            self._print_prompt_with_line(line)
            common = self._get_common_prefix(matches)
            if common and len(common) > len(prefix):
                return common
        return None
    
    def _complete_subcommand(self, cmd_name: str, prefix: str, line: str) -> Optional[str]:
        subcommands = self.commands.get(cmd_name, {}).get("subcommands", {})
        if not subcommands:
            return None
        
        matches = [sub for sub in subcommands.keys() if sub.startswith(prefix)]
        print(f"\n\033[90m{self.commands[cmd_name]['help']}\033[0m")
        self._print_prompt_with_line(line)
        
        if len(matches) == 1:
            return matches[0]
        if matches:
            common = self._get_common_prefix(matches)
            if common and len(common) > len(prefix):
                return common
        return None
    
    def _complete_arguments(
        self,
        cmd_name: str,
        subcmd_name: Optional[str],
        parts: List[str],
        text: str,
        line: str,
        ends_with_space: bool,
    ) -> Optional[str]:
        if subcmd_name:
            arg_specs = (
                self.commands.get(cmd_name, {})
                .get("subcommands", {})
                .get(subcmd_name, {})
                .get("arguments", [])
            )
        else:
            arg_specs = self.commands.get(cmd_name, {}).get("arguments", [])
        
        if not arg_specs:
            return None
        
        consumed_tokens = 1 + (1 if subcmd_name else 0)
        arg_index = len(parts) - consumed_tokens
        if not ends_with_space:
            arg_index -= 1
        if arg_index < 0:
            return None
        if arg_index >= len(arg_specs):
            spec = arg_specs[-1]
            if not spec.get("variadic"):
                return None
        else:
            spec = arg_specs[arg_index]
        
        values = set()
        provider_key = spec.get("provider")
        if provider_key:
            values.update(self._get_argument_values(provider_key))
        if spec.get("choices"):
            values.update(spec["choices"])
        if spec.get("literals"):
            values.update(spec["literals"])
        
        values = sorted([val for val in values if isinstance(val, str) and val])
        if not values:
            return None
        
        prefix = "" if ends_with_space else text
        matches = [val for val in values if val.startswith(prefix)]
        
        if len(matches) == 1:
            return matches[0] + " "
        
        label = spec.get("name", "value")
        if matches:
            preview = ", ".join(matches[:8])
            if len(matches) > 8:
                preview += ", ..."
            print(f"\n\033[90mMatching {label}: {preview}\033[0m")
        else:
            preview = ", ".join(values[:8])
            if len(values) > 8:
                preview += ", ..."
            print(f"\n\033[90m{label} options: {preview}\033[0m")
        self._print_prompt_with_line(line)
        return None
    
    def _show_command_help(self, cmd):
        """Zeigt Hilfe für einen Hauptbefehl an"""
        if cmd in self.commands and 'help' in self.commands[cmd]:
            # Zeige die Hilfe über dem Prompt
            print(f"\n\033[90m{self.commands[cmd]['help']}\033[0m")
            self._print_prompt_with_line()
            
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
                self._print_prompt_with_line()
    
    def _show_detailed_help(self, cmd_name: str):
        """Renders a detailed help section for a specific command"""
        cmd_info = self.commands.get(cmd_name)
        if not cmd_info:
            print(f"No help available for '{cmd_name}'.")
            return

        header = cmd_info.get('help', f"{cmd_name} commands")
        print(f"\n  {header}")

        subcommands = cmd_info.get('subcommands')
        if not subcommands:
            return

        command_names = [f"{cmd_name} {name}" for name in subcommands.keys()]
        max_len = max(len(name) for name in command_names) if command_names else len(cmd_name)

        for sub_name, meta in subcommands.items():
            label = f"{cmd_name} {sub_name}"
            description = meta.get('help', 'No description provided')
            print(f"    {label:<{max_len}}  - {description}")
    
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
                command = input(self.prompt_string).strip()
                if not command:
                    continue
                    
                with self._command_output():
                    parts = command.split()
                    main_cmd = parts[0].lower()
                    
                    if main_cmd in ["exit", "quit", "q"]:
                        self.running = False
                    elif main_cmd == "help":
                        if len(parts) > 1:
                            self.show_help(parts[1])
                        else:
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
                    elif main_cmd == "network":
                        self.network_commands.handle_command(parts[1:] if len(parts) > 1 else [])
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
                        print(f"Unknown command: {main_cmd}. Tip: type 'help' to list all available commands.")
                    
            except EOFError:
                print("\nExiting on Ctrl-D")
                self.running = False
            except KeyboardInterrupt:
                print("\nOperation cancelled")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # Beim Beenden die Historie speichern
        self._save_history()
    
    def show_help(self, command: str = None):
        """Show help information"""
        if command:
            self._show_detailed_help(command.lower())
            return

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
    metrics disk <id> [--days=1]      - Show disk I/O metrics

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

  Network Commands:
    network list                      - List all private networks
    network info <id>                 - Show detailed information about a network
    network create                    - Create a new private network (interactive)
    network update <id>               - Update network metadata (name, labels)
    network delete <id>               - Delete a network by ID
    network attach <nid> <sid> [ip]   - Attach server to network
    network detach <nid> <sid>        - Detach server from network
    network subnet add <id>           - Add a subnet to network
    network subnet delete <id> <ip>   - Remove a subnet from network
    network protect <id> <e|d>        - Enable/disable network protection

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
    help [command]                    - Show general or command-specific help
    exit, quit, q, Ctrl-D             - Exit the program
"""
        print(help_text)
