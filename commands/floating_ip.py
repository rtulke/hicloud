#!/usr/bin/env python3
# commands/floating_ip.py - Floating IP commands for hicloud

from typing import List


class FloatingIPCommands:
    """Floating IP management commands for Interactive Console."""

    def __init__(self, console):
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        if not args:
            print("Missing floating-ip subcommand. Use 'floating-ip list|info|create|update|delete|assign|unassign|dns|protect'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_floating_ips()
        elif subcommand == "info":
            self.show_info(args[1:])
        elif subcommand == "create":
            self.create_floating_ip()
        elif subcommand == "update":
            self.update_floating_ip(args[1:])
        elif subcommand == "delete":
            self.delete_floating_ip(args[1:])
        elif subcommand == "assign":
            self.assign_floating_ip(args[1:])
        elif subcommand == "unassign":
            self.unassign_floating_ip(args[1:])
        elif subcommand == "dns":
            self.change_dns_ptr(args[1:])
        elif subcommand == "protect":
            self.change_protection(args[1:])
        else:
            print(f"Unknown floating-ip subcommand: {subcommand}")

    # ------------------------------------------------------------------ list

    def list_floating_ips(self):
        fips = self.hetzner.list_floating_ips()
        if not fips:
            print("No floating IPs found")
            return

        headers = ["ID", "Name", "IP", "Type", "Location", "Assigned To", "Protected"]
        rows = []
        for fip in sorted(fips, key=lambda x: x.get("id", 0)):
            fip_id   = fip.get("id", "N/A")
            name     = fip.get("name", "N/A")
            ip       = fip.get("ip", "N/A")
            ip_type  = fip.get("type", "N/A")
            location = fip.get("home_location", {}).get("name", "N/A")
            server   = fip.get("server")
            assigned = f"server:{server}" if server else "-"
            protected = "yes" if fip.get("protection", {}).get("delete") else "no"
            rows.append([fip_id, name, ip, ip_type, location, assigned, protected])

        self.console.print_table(headers, rows, "Floating IPs")

    # ------------------------------------------------------------------ info

    def show_info(self, args: List[str]):
        fip = self._resolve(args, "floating-ip info <id>")
        if not fip:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Floating IP: \033[1;32m{fip.get('name', 'N/A')}\033[0m (ID: {fip.get('id')})")
        print(f"{self.console.horizontal_line('=')}")
        print(f"IP:          {fip.get('ip', 'N/A')}")
        print(f"Type:        {fip.get('type', 'N/A')}")
        print(f"Location:    {fip.get('home_location', {}).get('name', 'N/A')}")
        server = fip.get("server")
        print(f"Assigned To: {'server:' + str(server) if server else '-'}")
        print(f"Description: {fip.get('description') or '-'}")
        print(f"Protected:   {'yes' if fip.get('protection', {}).get('delete') else 'no'}")
        print(f"Blocked:     {'yes' if fip.get('blocked') else 'no'}")
        print(f"Created:     {fip.get('created', 'N/A')}")

        dns_ptrs = fip.get("dns_ptr", [])
        if dns_ptrs:
            print("\nReverse DNS:")
            for entry in dns_ptrs:
                print(f"  {entry.get('ip')} → {entry.get('dns_ptr')}")

        labels = fip.get("labels", {})
        if labels:
            print("\nLabels:")
            for k, v in labels.items():
                print(f"  {k}: {v}")

        print(f"{self.console.horizontal_line('-')}")

    # ----------------------------------------------------------------- create

    def create_floating_ip(self):
        print("Create a new Floating IP:")

        while True:
            ip_type = input("Type [ipv4/ipv6] (default: ipv4): ").strip().lower() or "ipv4"
            if ip_type in ("ipv4", "ipv6"):
                break
            print("Invalid type. Use 'ipv4' or 'ipv6'.")

        name = input("Name: ").strip()
        if not name:
            print("Name is required.")
            return

        description = input("Description (optional): ").strip() or None

        # Location or server
        server_input = input("Assign to server ID (or leave blank to choose a location): ").strip()
        server_id = None
        home_location = None
        if server_input:
            try:
                server_id = int(server_input)
            except ValueError:
                print("Invalid server ID.")
                return
        else:
            locations = self.hetzner.list_locations()
            if not locations:
                print("No locations available.")
                return
            print("\nAvailable locations:")
            for i, loc in enumerate(locations, 1):
                print(f"  {i}. {loc.get('name')} ({loc.get('city', '')})")
            choice = input("Select location (number or name): ").strip()
            home_location = self._resolve_location(locations, choice)
            if not home_location:
                print("Invalid location selection.")
                return

        labels = self._prompt_labels()

        print("\nSummary:")
        print(f"  Type:        {ip_type}")
        print(f"  Name:        {name}")
        if description:
            print(f"  Description: {description}")
        if server_id:
            print(f"  Server:      {server_id}")
        else:
            print(f"  Location:    {home_location}")

        if input("\nCreate floating IP? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        fip = self.hetzner.create_floating_ip(
            ip_type=ip_type, name=name, home_location=home_location,
            server=server_id, description=description,
            labels=labels if labels else None,
        )
        if fip:
            print(f"\nFloating IP created: {fip.get('ip')} (ID: {fip.get('id')})")
        else:
            print("Failed to create floating IP")

    # ----------------------------------------------------------------- update

    def update_floating_ip(self, args: List[str]):
        fip = self._resolve(args, "floating-ip update <id>")
        if not fip:
            return

        fip_id = fip.get("id")
        print(f"Updating floating IP '{fip.get('name')}' (ID: {fip_id})")
        print("Press Enter to keep current value.\n")

        cur_name = fip.get("name", "")
        new_name = input(f"Name [{cur_name}]: ").strip() or None

        cur_desc = fip.get("description") or ""
        new_desc_raw = input(f"Description [{cur_desc}]: ").strip()
        new_desc = new_desc_raw if new_desc_raw else None

        new_labels = None
        if input("Update labels? [y/N]: ").strip().lower() == "y":
            new_labels = self._prompt_labels(ask_first=False)

        if new_name is None and new_desc is None and new_labels is None:
            print("No changes. Skipping.")
            return

        result = self.hetzner.update_floating_ip(fip_id, name=new_name, description=new_desc, labels=new_labels)
        if result:
            print(f"Floating IP {fip_id} updated successfully")
        else:
            print(f"Failed to update floating IP {fip_id}")

    # ----------------------------------------------------------------- delete

    def delete_floating_ip(self, args: List[str]):
        fip = self._resolve(args, "floating-ip delete <id>")
        if not fip:
            return

        fip_id = fip.get("id")

        # IP Deletion Guard (ID 28)
        if fip.get("server"):
            print(f"ERROR: Floating IP '{fip.get('name')}' (ID: {fip_id}) is currently assigned to server {fip['server']}.")
            print("Unassign it first:  floating-ip unassign " + str(fip_id))
            return

        if fip.get("protection", {}).get("delete"):
            print(f"ERROR: Floating IP '{fip.get('name')}' is delete-protected. Disable protection first:")
            print("  floating-ip protect " + str(fip_id) + " disable")
            return

        if input(f"Delete floating IP '{fip.get('name')}' ({fip.get('ip')})? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.delete_floating_ip(fip_id):
            print(f"Floating IP {fip_id} deleted")
        else:
            print(f"Failed to delete floating IP {fip_id}")

    # ----------------------------------------------------------------- assign

    def assign_floating_ip(self, args: List[str]):
        if len(args) < 2:
            print("Usage: floating-ip assign <fip_id> <server_id>")
            return
        fip = self._resolve([args[0]], "floating-ip assign <fip_id> <server_id>")
        if not fip:
            return
        try:
            server_id = int(args[1])
        except ValueError:
            print("Invalid server ID.")
            return

        fip_id = fip.get("id")
        if input(f"Assign floating IP '{fip.get('name')}' ({fip.get('ip')}) to server {server_id}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.assign_floating_ip(fip_id, server_id):
            print(f"Floating IP {fip_id} assigned to server {server_id}")
        else:
            print(f"Failed to assign floating IP {fip_id}")

    # --------------------------------------------------------------- unassign

    def unassign_floating_ip(self, args: List[str]):
        fip = self._resolve(args, "floating-ip unassign <id>")
        if not fip:
            return

        fip_id = fip.get("id")
        if not fip.get("server"):
            print(f"Floating IP '{fip.get('name')}' is not assigned to any server.")
            return

        if input(f"Unassign floating IP '{fip.get('name')}' from server {fip['server']}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.unassign_floating_ip(fip_id):
            print(f"Floating IP {fip_id} unassigned")
        else:
            print(f"Failed to unassign floating IP {fip_id}")

    # -------------------------------------------------------------------- dns

    def change_dns_ptr(self, args: List[str]):
        if len(args) < 2:
            print("Usage: floating-ip dns <id> <ip> [<ptr>]")
            print("  Omit <ptr> or pass 'reset' to remove the reverse DNS entry.")
            return
        fip = self._resolve([args[0]], "floating-ip dns <id> <ip> [<ptr>]")
        if not fip:
            return

        ip = args[1]
        dns_ptr = args[2] if len(args) >= 3 and args[2].lower() != "reset" else None
        fip_id = fip.get("id")

        action = f"→ {dns_ptr}" if dns_ptr else "(reset)"
        if input(f"Set rDNS for {ip} {action} on floating IP {fip_id}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.change_floating_ip_dns_ptr(fip_id, ip, dns_ptr):
            print(f"rDNS updated for floating IP {fip_id}")
        else:
            print(f"Failed to update rDNS for floating IP {fip_id}")

    # ----------------------------------------------------------------- protect

    def change_protection(self, args: List[str]):
        if len(args) < 2:
            print("Usage: floating-ip protect <id> <enable|disable>")
            return
        fip = self._resolve([args[0]], "floating-ip protect <id> <enable|disable>")
        if not fip:
            return

        action = args[1].lower()
        if action not in ("enable", "disable"):
            print("Use 'enable' or 'disable'.")
            return

        delete_protection = action == "enable"
        fip_id = fip.get("id")

        if self.hetzner.change_floating_ip_protection(fip_id, delete_protection):
            print(f"Delete protection {action}d for floating IP {fip_id}")
        else:
            print(f"Failed to change protection for floating IP {fip_id}")

    # ------------------------------------------------------------ helpers

    def _resolve(self, args: List[str], usage: str):
        if not args:
            print(f"Missing ID. Use '{usage}'")
            return None
        try:
            fip_id = int(args[0])
        except ValueError:
            print("Invalid ID. Must be an integer.")
            return None
        fip = self.hetzner.get_floating_ip_by_id(fip_id)
        return fip if fip else None

    def _resolve_location(self, locations, choice: str):
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(locations):
                return locations[idx].get("name")
            return None
        for loc in locations:
            if loc.get("name", "").lower() == choice.lower():
                return loc.get("name")
        return None

    def _prompt_labels(self, ask_first: bool = True):
        labels = {}
        if ask_first and input("Add labels? [y/N]: ").strip().lower() != "y":
            return labels
        while True:
            key = input("Label key (Enter to finish): ").strip()
            if not key:
                break
            labels[key] = input(f"Value for '{key}': ").strip()
        return labels
