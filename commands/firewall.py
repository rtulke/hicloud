#!/usr/bin/env python3
# commands/firewall.py - Firewall-related commands for hicloud

import ipaddress
from typing import Dict, List, Optional, Set, Tuple


class FirewallCommands:
    """Firewall-related commands for Interactive Console."""

    def __init__(self, console):
        """Initialize with reference to the console."""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle firewall-related commands."""
        if not args:
            print("Missing firewall subcommand. Use 'firewall list|info|create|update|delete|rules|apply|remove'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_firewalls()
        elif subcommand == "info":
            self.show_firewall_info(args[1:])
        elif subcommand == "create":
            self.create_firewall()
        elif subcommand == "update":
            self.update_firewall(args[1:])
        elif subcommand == "delete":
            self.delete_firewall(args[1:])
        elif subcommand == "rules":
            self.configure_rules(args[1:])
        elif subcommand == "apply":
            self.apply_to_resources(args[1:])
        elif subcommand == "remove":
            self.remove_from_resources(args[1:])
        else:
            print(f"Unknown firewall subcommand: {subcommand}")

    def list_firewalls(self):
        """List all firewalls."""
        firewalls = self.hetzner.list_firewalls()
        if not firewalls:
            print("No firewalls found")
            return

        headers = ["ID", "Name", "Rules", "Applied To", "Created"]
        rows = []

        for firewall in sorted(firewalls, key=lambda x: x.get("name", "").lower()):
            created = firewall.get("created", "N/A")
            if created != "N/A":
                created = created.split("T")[0]

            rules_count = len(firewall.get("rules", []))
            applied_count = len(firewall.get("applied_to", []))
            rows.append([
                firewall.get("id", "N/A"),
                firewall.get("name", "N/A"),
                rules_count,
                applied_count,
                created,
            ])

        self.console.print_table(headers, rows, "Firewalls")

    def show_firewall_info(self, args: List[str]):
        """Show detailed firewall information."""
        firewall = self._resolve_firewall_from_args(args, "firewall info <id>")
        if not firewall:
            return

        firewall_id = firewall.get("id", "N/A")
        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Firewall Information: \033[1;32m{firewall.get('name')}\033[0m (ID: {firewall_id})")
        print(f"{self.console.horizontal_line('=')}")

        created = firewall.get("created", "N/A")
        if created != "N/A":
            created_date = created.split("T")[0]
            created_time = created.split("T")[1].split("+")[0] if "+" in created else created.split("T")[1].split("Z")[0]
            print(f"Created: {created_date} {created_time}")

        self._print_rules(firewall.get("rules", []))
        self._print_applied_resources(firewall.get("applied_to", []))

        labels = firewall.get("labels", {})
        if labels:
            print("\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")
        else:
            print("\nLabels: None")

        print(f"{self.console.horizontal_line('-')}")

    def create_firewall(self):
        """Create a new firewall."""
        print("Create a new Firewall:")

        name = input("Firewall Name: ").strip()
        if not name:
            print("Firewall name is required")
            return

        rules: Optional[List[Dict]] = None
        add_rules = input("\nAdd rules now? [Y/n]: ").strip().lower()
        if add_rules in ["", "y", "yes"]:
            rules = self._prompt_for_rules()

        apply_to = self._prompt_for_apply_resources()
        if apply_to is None:
            return

        labels = self._prompt_for_labels()
        if labels == {}:
            labels = None

        print("\nFirewall Creation Summary:")
        print(f"  Name: {name}")
        print(f"  Rules: {len(rules) if rules is not None else 0}")
        print(f"  Apply To: {len(apply_to) if apply_to else 0} target(s)")
        if labels:
            print(f"  Labels: {labels}")

        confirm = input("\nCreate this firewall? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print("Creating firewall...")
        firewall = self.hetzner.create_firewall(
            name=name,
            rules=rules,
            apply_to=apply_to,
            labels=labels,
        )

        if firewall:
            print("\nFirewall created successfully!")
            print(f"ID: {firewall.get('id')}")
            print(f"Name: {firewall.get('name')}")
        else:
            print("Failed to create firewall")

    def update_firewall(self, args: List[str]):
        """Update firewall metadata (name and/or labels)."""
        firewall = self._resolve_firewall_from_args(args, "firewall update <id>")
        if not firewall:
            return

        firewall_id = firewall.get("id")
        print(f"\nUpdating Firewall: \033[1;32m{firewall.get('name')}\033[0m (ID: {firewall_id})")
        print(f"{self.console.horizontal_line('-')}")

        new_name = None
        name_input = input(f"New name (leave empty to keep '{firewall.get('name')}'): ").strip()
        if name_input:
            new_name = name_input

        new_labels = None
        update_labels_input = input("\nUpdate labels? [y/N]: ").strip().lower()
        if update_labels_input == "y":
            current_labels = firewall.get("labels", {})
            if current_labels:
                print("\nCurrent labels:")
                for key, value in current_labels.items():
                    print(f"  {key}: {value}")

            print("\nEnter new labels (this will replace all existing labels):")
            new_labels = self._prompt_for_labels(ask_first=False)

        if new_name is None and new_labels is None:
            print("\nNo changes made.")
            return

        print("\nUpdate Summary:")
        if new_name is not None:
            print(f"  Name: {firewall.get('name')} -> {new_name}")
        if new_labels is not None:
            print(f"  Labels: {len(new_labels)} labels")

        confirm = input("\nApply these changes? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Updating firewall {firewall_id}...")
        updated = self.hetzner.update_firewall(firewall_id, name=new_name, labels=new_labels)
        if updated:
            print(f"Firewall {firewall_id} updated successfully")
        else:
            print(f"Failed to update firewall {firewall_id}")

    def delete_firewall(self, args: List[str]):
        """Delete a firewall by ID."""
        firewall = self._resolve_firewall_from_args(args, "firewall delete <id>")
        if not firewall:
            return

        firewall_id = firewall.get("id")
        applied_count = len(firewall.get("applied_to", []))
        if applied_count > 0:
            print(f"Warning: This firewall is currently applied to {applied_count} resource(s).")

        confirm = input(
            f"Are you sure you want to delete firewall '{firewall.get('name')}' (ID: {firewall_id})? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Deleting firewall {firewall_id}...")
        if self.hetzner.delete_firewall(firewall_id):
            print(f"Firewall {firewall_id} deleted successfully")
        else:
            print(f"Failed to delete firewall {firewall_id}")

    def configure_rules(self, args: List[str]):
        """Manage firewall rules."""
        if not args:
            print("Missing rule action. Use 'firewall rules list|add|remove|set <id> [index[,index...]]'")
            print("Compatibility: 'firewall rules <id>' still works as 'set'")
            return

        action = "set"
        remaining = args
        candidate = args[0].lower()
        if candidate in {"list", "add", "remove", "set"}:
            action = candidate
            remaining = args[1:]

        if action == "list":
            self.list_rules(remaining)
        elif action == "add":
            self.add_rules(remaining)
        elif action == "remove":
            self.remove_rules(remaining)
        else:
            self.set_rules(remaining)

    def list_rules(self, args: List[str]):
        """List firewall rules."""
        firewall = self._resolve_firewall_from_args(args, "firewall rules list <id>")
        if not firewall:
            return

        print(f"\nFirewall Rules: \033[1;32m{firewall.get('name')}\033[0m (ID: {firewall.get('id')})")
        self._print_rules(firewall.get("rules", []))

    def add_rules(self, args: List[str]):
        """Append new rules to a firewall."""
        firewall = self._resolve_firewall_from_args(args, "firewall rules add <id>")
        if not firewall:
            return

        existing_rules = firewall.get("rules", [])
        print(f"\nAdding rules to firewall '{firewall.get('name')}' (ID: {firewall.get('id')})")
        print(f"Current rule count: {len(existing_rules)}")

        new_rules = self._prompt_for_rules()
        if not new_rules:
            print("No rules added. Operation cancelled.")
            return

        combined_rules = list(existing_rules) + new_rules
        print("\nRule Update Summary:")
        print(f"  Existing rules: {len(existing_rules)}")
        print(f"  Rules to add: {len(new_rules)}")
        print(f"  Resulting rules: {len(combined_rules)}")

        confirm = input("\nApply these rule changes? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        firewall_id = firewall.get("id")
        print(f"Updating rules for firewall {firewall_id}...")
        if self.hetzner.set_firewall_rules(firewall_id, combined_rules):
            print(f"Firewall {firewall_id} rules updated successfully")
        else:
            print(f"Failed to update rules for firewall {firewall_id}")

    def remove_rules(self, args: List[str]):
        """Remove rules by 1-based index."""
        if len(args) < 2:
            print("Missing parameters. Use 'firewall rules remove <id> <index[,index...]>'")
            return

        firewall = self._resolve_firewall_from_args([args[0]], "firewall rules remove <id> <index[,index...]>")
        if not firewall:
            return

        rules = firewall.get("rules", [])
        if not rules:
            print("Firewall has no rules to remove.")
            return

        indexes = self._parse_rule_indexes(args[1], len(rules))
        if not indexes:
            print("Invalid rule indexes. Use 1-based indexes like '1' or '1,3,5'.")
            return

        remaining_rules = [rule for index, rule in enumerate(rules, start=1) if index not in indexes]
        print("\nRule Removal Summary:")
        print(f"  Existing rules: {len(rules)}")
        print(f"  Removing indexes: {', '.join(str(i) for i in sorted(indexes))}")
        print(f"  Resulting rules: {len(remaining_rules)}")

        confirm = input("\nApply these rule changes? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        firewall_id = firewall.get("id")
        print(f"Updating rules for firewall {firewall_id}...")
        if self.hetzner.set_firewall_rules(firewall_id, remaining_rules):
            print(f"Firewall {firewall_id} rules updated successfully")
        else:
            print(f"Failed to update rules for firewall {firewall_id}")

    def set_rules(self, args: List[str]):
        """Replace all firewall rules with a new set."""
        firewall = self._resolve_firewall_from_args(args, "firewall rules set <id>")
        if not firewall:
            return

        firewall_id = firewall.get("id")
        existing_rules = firewall.get("rules", [])
        print(f"\nReplacing rules for firewall '{firewall.get('name')}' (ID: {firewall_id})")
        print(f"Current rule count: {len(existing_rules)}")
        print("All existing rules will be replaced.")

        rules = self._prompt_for_rules()
        print("\nRule Update Summary:")
        print(f"  Existing rules: {len(existing_rules)}")
        print(f"  New rules: {len(rules)}")

        confirm = input("\nApply these rule changes? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Updating rules for firewall {firewall_id}...")
        if self.hetzner.set_firewall_rules(firewall_id, rules):
            print(f"Firewall {firewall_id} rules updated successfully")
        else:
            print(f"Failed to update rules for firewall {firewall_id}")

    def apply_to_resources(self, args: List[str]):
        """Apply firewall to server IDs or label selector targets."""
        if len(args) < 2:
            print("Missing parameters. Use 'firewall apply <firewall_id> <server_id[,server_id...]>'")
            print("Alternative: 'firewall apply <firewall_id> server <ids>' or 'firewall apply <firewall_id> label <selector>'")
            return

        firewall = self._resolve_firewall_from_args([args[0]], "firewall apply <firewall_id> ...")
        if not firewall:
            return

        parsed = self._parse_resource_target(args[1:])
        if parsed is None:
            return

        resources, target_text = parsed
        firewall_id = firewall.get("id")

        confirm = input(
            f"Apply firewall '{firewall.get('name')}' (ID: {firewall_id}) to {target_text}? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Applying firewall {firewall_id}...")
        if self.hetzner.apply_firewall_to_resources(firewall_id, resources):
            print(f"Firewall {firewall_id} applied successfully")
        else:
            print(f"Failed to apply firewall {firewall_id}")

    def remove_from_resources(self, args: List[str]):
        """Remove firewall from server IDs or label selector targets."""
        if len(args) < 2:
            print("Missing parameters. Use 'firewall remove <firewall_id> <server_id[,server_id...]>'")
            print("Alternative: 'firewall remove <firewall_id> server <ids>' or 'firewall remove <firewall_id> label <selector>'")
            return

        firewall = self._resolve_firewall_from_args([args[0]], "firewall remove <firewall_id> ...")
        if not firewall:
            return

        parsed = self._parse_resource_target(args[1:])
        if parsed is None:
            return

        resources, target_text = parsed
        firewall_id = firewall.get("id")

        confirm = input(
            f"Remove firewall '{firewall.get('name')}' (ID: {firewall_id}) from {target_text}? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Removing firewall {firewall_id} from target(s)...")
        if self.hetzner.remove_firewall_from_resources(firewall_id, resources):
            print(f"Firewall {firewall_id} removed successfully")
        else:
            print(f"Failed to remove firewall {firewall_id}")

    def _prompt_for_rules(self) -> List[Dict]:
        """Interactively collect firewall rules."""
        print("\nAdd firewall rules. Press Enter on direction to finish.")
        print("Example inbound rule: direction=in, protocol=tcp, port=22, source_ips=0.0.0.0/0,::/0")

        rules: List[Dict] = []

        while True:
            direction = input("\nDirection [in/out] (Enter to finish): ").strip().lower()
            if not direction:
                break
            if direction not in ["in", "out"]:
                print("Direction must be 'in' or 'out'")
                continue

            protocol = input("Protocol [tcp/udp/icmp/gre/esp]: ").strip().lower()
            if protocol not in ["tcp", "udp", "icmp", "gre", "esp"]:
                print("Protocol must be one of: tcp, udp, icmp, gre, esp")
                continue

            rule: Dict[str, object] = {
                "direction": direction,
                "protocol": protocol,
            }

            if protocol in ["tcp", "udp"]:
                port = input("Port or range (e.g. 22, 80, 8000-8100): ").strip()
                if not self._validate_port_spec(port):
                    print("Invalid port specification. Use single port 1-65535 or range (e.g. 80-443).")
                    continue
                rule["port"] = port

            default_ips = "0.0.0.0/0,::/0"
            if direction == "in":
                ip_input = input(f"Source IPs (comma-separated, default: {default_ips}): ").strip()
                ips = ["0.0.0.0/0", "::/0"] if not ip_input else self._parse_ip_list(ip_input)
                if not ips:
                    print("Invalid source IP list. Use valid IP/CIDR entries, e.g. 10.0.0.0/8,2001:db8::/32")
                    continue
                rule["source_ips"] = ips
            else:
                ip_input = input(f"Destination IPs (comma-separated, default: {default_ips}): ").strip()
                ips = ["0.0.0.0/0", "::/0"] if not ip_input else self._parse_ip_list(ip_input)
                if not ips:
                    print("Invalid destination IP list. Use valid IP/CIDR entries, e.g. 10.0.0.0/8,2001:db8::/32")
                    continue
                rule["destination_ips"] = ips

            description = input("Description (optional): ").strip()
            if description:
                rule["description"] = description

            rules.append(rule)
            print("Rule added.")

        return rules

    def _prompt_for_labels(self, ask_first: bool = True) -> Dict[str, str]:
        """Interactively collect key/value labels."""
        labels: Dict[str, str] = {}
        if ask_first:
            add_labels = input("\nAdd labels? [y/N]: ").strip().lower()
            if add_labels != "y":
                return labels

        while True:
            key = input("Label key (or press Enter to finish): ").strip()
            if not key:
                break
            value = input(f"Label value for '{key}': ").strip()
            labels[key] = value

        return labels

    def _prompt_for_apply_resources(self) -> Optional[List[Dict]]:
        """Interactively choose optional initial apply targets."""
        add_targets = input("\nApply firewall to resources now? [y/N]: ").strip().lower()
        if add_targets != "y":
            return None

        target_type = input("Target type [server/label] (default: server): ").strip().lower() or "server"
        if target_type == "label":
            selector = input("Label selector (e.g. env=prod): ").strip()
            if not selector:
                print("Label selector cannot be empty.")
                return None
            return [{"type": "label_selector", "label_selector": {"selector": selector}}]

        if target_type != "server":
            print("Invalid target type. Use 'server' or 'label'.")
            return None

        server_ids = self._prompt_for_server_ids()
        if server_ids is None:
            return None
        if not server_ids:
            return []

        return self._build_server_resources(server_ids)

    def _prompt_for_server_ids(self) -> Optional[List[int]]:
        """Display available servers and return selected IDs."""
        servers = self.hetzner.list_servers()
        if not servers:
            print("No servers available.")
            return []

        print("\nAvailable Servers:")
        for server in sorted(servers, key=lambda x: x.get("name", "").lower()):
            print(f"  - {server.get('id')}: {server.get('name')} ({server.get('status', 'unknown')})")

        raw = input("Server IDs (comma-separated, leave empty for none): ").strip()
        if not raw:
            return []

        server_ids = self._parse_server_ids(raw)
        if not server_ids:
            print("Invalid server list. Expected comma-separated integers like '1,2,3'.")
            return None

        return server_ids

    def _parse_resource_target(self, args: List[str]) -> Optional[Tuple[List[Dict], str]]:
        """
        Parse resource target args for apply/remove.
        Supported:
        - <server_ids>
        - server <server_ids>
        - label <selector>
        """
        if not args:
            print("Missing target resource.")
            return None

        mode = "server"
        target_value = args[0].strip()
        if args[0].lower() in {"server", "label"}:
            mode = args[0].lower()
            if len(args) < 2:
                print(f"Missing target value after '{mode}'.")
                return None
            target_value = " ".join(args[1:]).strip()

        if mode == "label":
            if not target_value:
                print("Label selector cannot be empty.")
                return None
            resources = [{"type": "label_selector", "label_selector": {"selector": target_value}}]
            return resources, f"label selector '{target_value}'"

        server_ids = self._parse_server_ids(target_value)
        if not server_ids:
            print("Invalid server ID list. Use comma-separated integers like '1,2,3'.")
            return None

        missing_ids = self._find_missing_server_ids(server_ids)
        if missing_ids:
            missing = ", ".join(str(server_id) for server_id in missing_ids)
            print(f"Unknown server ID(s): {missing}")
            return None

        resources = self._build_server_resources(server_ids)
        return resources, f"{len(server_ids)} server(s)"

    def _parse_ip_list(self, raw: str) -> List[str]:
        """Parse and validate comma-separated IP/CIDR values."""
        result: List[str] = []
        for item in raw.split(","):
            value = item.strip()
            if not value:
                continue
            try:
                ipaddress.ip_network(value, strict=False)
            except ValueError:
                return []
            result.append(value)
        return result

    def _parse_server_ids(self, raw: str) -> List[int]:
        """Parse comma-separated server IDs and remove duplicates."""
        server_ids: List[int] = []
        seen: Set[int] = set()

        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                server_id = int(token)
            except ValueError:
                return []

            if server_id not in seen:
                seen.add(server_id)
                server_ids.append(server_id)

        return server_ids

    def _parse_rule_indexes(self, raw: str, max_index: int) -> Set[int]:
        """Parse 1-based rule indexes from comma-separated input."""
        indexes: Set[int] = set()
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                index = int(token)
            except ValueError:
                return set()
            if index < 1 or index > max_index:
                return set()
            indexes.add(index)
        return indexes

    def _find_missing_server_ids(self, server_ids: List[int]) -> List[int]:
        """Return server IDs that do not exist in the current project."""
        servers = self.hetzner.list_servers()
        existing_ids = {int(server.get("id")) for server in servers if server.get("id") is not None}
        return [server_id for server_id in server_ids if server_id not in existing_ids]

    def _resolve_firewall_from_args(self, args: List[str], usage: str) -> Dict:
        """Resolve firewall from first arg with standard validation and messaging."""
        if not args:
            print(f"Missing firewall ID. Use '{usage}'")
            return {}

        try:
            firewall_id = int(args[0])
        except ValueError:
            print("Invalid firewall ID. Must be an integer.")
            return {}

        return self.hetzner.get_firewall_by_id(firewall_id)

    def _validate_port_spec(self, port: str) -> bool:
        """Validate single port or inclusive port range."""
        if not port:
            return False

        if "-" in port:
            left, right = port.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                return False
            start = int(left)
            end = int(right)
            return 1 <= start <= end <= 65535

        if not port.isdigit():
            return False
        value = int(port)
        return 1 <= value <= 65535

    def _build_server_resources(self, server_ids: List[int]) -> List[Dict]:
        """Build Hetzner firewall resource objects for server IDs."""
        return [{"type": "server", "server": {"id": server_id}} for server_id in server_ids]

    def _print_rules(self, rules: List[Dict]) -> None:
        """Render firewall rules in a compact human-readable form."""
        if not rules:
            print("\nRules: None")
            return

        print(f"\nRules ({len(rules)}):")
        for index, rule in enumerate(rules, start=1):
            direction = rule.get("direction", "N/A")
            protocol = rule.get("protocol", "N/A")
            port = rule.get("port", "-")
            src_ips = ",".join(rule.get("source_ips", [])) if rule.get("source_ips") else "-"
            dst_ips = ",".join(rule.get("destination_ips", [])) if rule.get("destination_ips") else "-"
            description = rule.get("description", "")

            print(f"  {index}. {direction} {protocol} port={port}")
            if src_ips != "-":
                print(f"     source_ips: {src_ips}")
            if dst_ips != "-":
                print(f"     destination_ips: {dst_ips}")
            if description:
                print(f"     description: {description}")

    def _print_applied_resources(self, applied_to: List[Dict]) -> None:
        """Render attached firewall resources."""
        if not applied_to:
            print("\nApplied To: None")
            return

        print(f"\nApplied To ({len(applied_to)}):")
        for resource in applied_to:
            resource_type = resource.get("type", "unknown")
            if resource_type == "server":
                server_id = resource.get("server", {}).get("id", "N/A")
                print(f"  - Server ID: {server_id}")
            elif resource_type == "label_selector":
                selector = resource.get("label_selector", {}).get("selector", "N/A")
                print(f"  - Label selector: {selector}")
            else:
                print(f"  - {resource}")
