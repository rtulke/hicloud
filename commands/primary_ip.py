#!/usr/bin/env python3
# commands/primary_ip.py - Primary IP commands for hicloud

from typing import List


class PrimaryIPCommands:
    """Primary IP management commands for Interactive Console."""

    def __init__(self, console):
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        if not args:
            print("Missing primary-ip subcommand. Use 'primary-ip list|info|create|update|delete|assign|unassign|dns|protect'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_primary_ips()
        elif subcommand == "info":
            self.show_info(args[1:])
        elif subcommand == "create":
            self.create_primary_ip()
        elif subcommand == "update":
            self.update_primary_ip(args[1:])
        elif subcommand == "delete":
            self.delete_primary_ip(args[1:])
        elif subcommand == "assign":
            self.assign_primary_ip(args[1:])
        elif subcommand == "unassign":
            self.unassign_primary_ip(args[1:])
        elif subcommand == "dns":
            self.change_dns_ptr(args[1:])
        elif subcommand == "protect":
            self.change_protection(args[1:])
        else:
            print(f"Unknown primary-ip subcommand: {subcommand}")

    # ------------------------------------------------------------------ list

    def list_primary_ips(self):
        pips = self.hetzner.list_primary_ips()
        if not pips:
            print("No primary IPs found")
            return

        headers = ["ID", "Name", "IP", "Type", "Datacenter", "Assigned To", "Auto-Delete", "Protected"]
        rows = []
        for pip in sorted(pips, key=lambda x: x.get("id", 0)):
            pip_id     = pip.get("id", "N/A")
            name       = pip.get("name", "N/A")
            ip         = pip.get("ip", "N/A")
            ip_type    = pip.get("type", "N/A")
            datacenter = pip.get("datacenter", {}).get("name", "N/A")
            assignee   = pip.get("assignee_id")
            assigned   = f"server:{assignee}" if assignee else "-"
            auto_del   = "yes" if pip.get("auto_delete") else "no"
            protected  = "yes" if pip.get("protection", {}).get("delete") else "no"
            rows.append([pip_id, name, ip, ip_type, datacenter, assigned, auto_del, protected])

        self.console.print_table(headers, rows, "Primary IPs")

    # ------------------------------------------------------------------ info

    def show_info(self, args: List[str]):
        pip = self._resolve(args, "primary-ip info <id>")
        if not pip:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Primary IP: \033[1;32m{pip.get('name', 'N/A')}\033[0m (ID: {pip.get('id')})")
        print(f"{self.console.horizontal_line('=')}")
        print(f"IP:          {pip.get('ip', 'N/A')}")
        print(f"Type:        {pip.get('type', 'N/A')}")
        dc = pip.get("datacenter", {})
        print(f"Datacenter:  {dc.get('name', 'N/A')} ({dc.get('location', {}).get('name', 'N/A')})")
        assignee = pip.get("assignee_id")
        print(f"Assigned To: {'server:' + str(assignee) if assignee else '-'}")
        print(f"Auto-Delete: {'yes' if pip.get('auto_delete') else 'no'}")
        print(f"Protected:   {'yes' if pip.get('protection', {}).get('delete') else 'no'}")
        print(f"Blocked:     {'yes' if pip.get('blocked') else 'no'}")
        print(f"Created:     {pip.get('created', 'N/A')}")

        dns_ptrs = pip.get("dns_ptr", [])
        if dns_ptrs:
            print("\nReverse DNS:")
            for entry in dns_ptrs:
                print(f"  {entry.get('ip')} → {entry.get('dns_ptr')}")

        labels = pip.get("labels", {})
        if labels:
            print("\nLabels:")
            for k, v in labels.items():
                print(f"  {k}: {v}")

        print(f"{self.console.horizontal_line('-')}")

    # ----------------------------------------------------------------- create

    def create_primary_ip(self):
        print("Create a new Primary IP:")

        while True:
            ip_type = input("Type [ipv4/ipv6] (default: ipv4): ").strip().lower() or "ipv4"
            if ip_type in ("ipv4", "ipv6"):
                break
            print("Invalid type. Use 'ipv4' or 'ipv6'.")

        name = input("Name: ").strip()
        if not name:
            print("Name is required.")
            return

        # Datacenter or server
        server_input = input("Assign to server ID immediately (or leave blank to choose a datacenter): ").strip()
        assignee_id = None
        datacenter = None
        if server_input:
            try:
                assignee_id = int(server_input)
            except ValueError:
                print("Invalid server ID.")
                return
        else:
            datacenters = self.hetzner.list_datacenters()
            if not datacenters:
                print("No datacenters available.")
                return
            print("\nAvailable datacenters:")
            for i, dc in enumerate(datacenters, 1):
                print(f"  {i}. {dc.get('name')} ({dc.get('location', {}).get('name', '')})")
            choice = input("Select datacenter (number or name): ").strip()
            datacenter = self._resolve_datacenter(datacenters, choice)
            if not datacenter:
                print("Invalid datacenter selection.")
                return

        auto_delete_input = input("Enable auto-delete (delete IP when server is deleted)? [y/N]: ").strip().lower()
        auto_delete = auto_delete_input == "y"

        labels = self._prompt_labels()

        print("\nSummary:")
        print(f"  Type:        {ip_type}")
        print(f"  Name:        {name}")
        if assignee_id:
            print(f"  Server:      {assignee_id}")
        else:
            print(f"  Datacenter:  {datacenter}")
        print(f"  Auto-Delete: {'yes' if auto_delete else 'no'}")

        if input("\nCreate primary IP? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        pip = self.hetzner.create_primary_ip(
            ip_type=ip_type, name=name, assignee_type="server",
            datacenter=datacenter, assignee_id=assignee_id,
            auto_delete=auto_delete, labels=labels if labels else None,
        )
        if pip:
            print(f"\nPrimary IP created: {pip.get('ip')} (ID: {pip.get('id')})")
        else:
            print("Failed to create primary IP")

    # ----------------------------------------------------------------- update

    def update_primary_ip(self, args: List[str]):
        pip = self._resolve(args, "primary-ip update <id>")
        if not pip:
            return

        pip_id = pip.get("id")
        print(f"Updating primary IP '{pip.get('name')}' (ID: {pip_id})")
        print("Press Enter to keep current value.\n")

        cur_name = pip.get("name", "")
        new_name = input(f"Name [{cur_name}]: ").strip() or None

        cur_auto = "yes" if pip.get("auto_delete") else "no"
        auto_raw = input(f"Auto-delete [{cur_auto}] (yes/no): ").strip().lower()
        new_auto = None
        if auto_raw in ("yes", "y"):
            new_auto = True
        elif auto_raw in ("no", "n"):
            new_auto = False

        new_labels = None
        if input("Update labels? [y/N]: ").strip().lower() == "y":
            new_labels = self._prompt_labels(ask_first=False)

        if new_name is None and new_auto is None and new_labels is None:
            print("No changes. Skipping.")
            return

        result = self.hetzner.update_primary_ip(pip_id, name=new_name, auto_delete=new_auto, labels=new_labels)
        if result:
            print(f"Primary IP {pip_id} updated successfully")
        else:
            print(f"Failed to update primary IP {pip_id}")

    # ----------------------------------------------------------------- delete

    def delete_primary_ip(self, args: List[str]):
        pip = self._resolve(args, "primary-ip delete <id>")
        if not pip:
            return

        pip_id = pip.get("id")

        # IP Deletion Guard (ID 28)
        if pip.get("assignee_id"):
            print(f"ERROR: Primary IP '{pip.get('name')}' (ID: {pip_id}) is assigned to server {pip['assignee_id']}.")
            print("Unassign it first:  primary-ip unassign " + str(pip_id))
            return

        if pip.get("protection", {}).get("delete"):
            print(f"ERROR: Primary IP '{pip.get('name')}' is delete-protected. Disable protection first:")
            print("  primary-ip protect " + str(pip_id) + " disable")
            return

        if not pip.get("auto_delete"):
            print(f"NOTE: auto_delete is disabled for this IP — it won't be deleted automatically with its server.")

        if input(f"Delete primary IP '{pip.get('name')}' ({pip.get('ip')})? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.delete_primary_ip(pip_id):
            print(f"Primary IP {pip_id} deleted")
        else:
            print(f"Failed to delete primary IP {pip_id}")

    # ----------------------------------------------------------------- assign

    def assign_primary_ip(self, args: List[str]):
        if len(args) < 2:
            print("Usage: primary-ip assign <pip_id> <server_id>")
            return
        pip = self._resolve([args[0]], "primary-ip assign <pip_id> <server_id>")
        if not pip:
            return
        try:
            server_id = int(args[1])
        except ValueError:
            print("Invalid server ID.")
            return

        pip_id = pip.get("id")
        if input(f"Assign primary IP '{pip.get('name')}' ({pip.get('ip')}) to server {server_id}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.assign_primary_ip(pip_id, server_id):
            print(f"Primary IP {pip_id} assigned to server {server_id}")
        else:
            print(f"Failed to assign primary IP {pip_id}")

    # --------------------------------------------------------------- unassign

    def unassign_primary_ip(self, args: List[str]):
        pip = self._resolve(args, "primary-ip unassign <id>")
        if not pip:
            return

        pip_id = pip.get("id")
        if not pip.get("assignee_id"):
            print(f"Primary IP '{pip.get('name')}' is not assigned to any server.")
            return

        if input(f"Unassign primary IP '{pip.get('name')}' from server {pip['assignee_id']}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.unassign_primary_ip(pip_id):
            print(f"Primary IP {pip_id} unassigned")
        else:
            print(f"Failed to unassign primary IP {pip_id}")

    # -------------------------------------------------------------------- dns

    def change_dns_ptr(self, args: List[str]):
        if len(args) < 2:
            print("Usage: primary-ip dns <id> <ip> [<ptr>]")
            print("  Omit <ptr> or pass 'reset' to remove the reverse DNS entry.")
            return
        pip = self._resolve([args[0]], "primary-ip dns <id> <ip> [<ptr>]")
        if not pip:
            return

        ip = args[1]
        dns_ptr = args[2] if len(args) >= 3 and args[2].lower() != "reset" else None
        pip_id = pip.get("id")

        action = f"→ {dns_ptr}" if dns_ptr else "(reset)"
        if input(f"Set rDNS for {ip} {action} on primary IP {pip_id}? [y/N]: ").strip().lower() != "y":
            print("Operation cancelled")
            return

        if self.hetzner.change_primary_ip_dns_ptr(pip_id, ip, dns_ptr):
            print(f"rDNS updated for primary IP {pip_id}")
        else:
            print(f"Failed to update rDNS for primary IP {pip_id}")

    # ----------------------------------------------------------------- protect

    def change_protection(self, args: List[str]):
        if len(args) < 2:
            print("Usage: primary-ip protect <id> <enable|disable>")
            return
        pip = self._resolve([args[0]], "primary-ip protect <id> <enable|disable>")
        if not pip:
            return

        action = args[1].lower()
        if action not in ("enable", "disable"):
            print("Use 'enable' or 'disable'.")
            return

        pip_id = pip.get("id")
        if self.hetzner.change_primary_ip_protection(pip_id, action == "enable"):
            print(f"Delete protection {action}d for primary IP {pip_id}")
        else:
            print(f"Failed to change protection for primary IP {pip_id}")

    # ------------------------------------------------------------ helpers

    def _resolve(self, args: List[str], usage: str):
        if not args:
            print(f"Missing ID. Use '{usage}'")
            return None
        try:
            pip_id = int(args[0])
        except ValueError:
            print("Invalid ID. Must be an integer.")
            return None
        pip = self.hetzner.get_primary_ip_by_id(pip_id)
        return pip if pip else None

    def _resolve_datacenter(self, datacenters, choice: str):
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(datacenters):
                return datacenters[idx].get("name")
            return None
        for dc in datacenters:
            if dc.get("name", "").lower() == choice.lower():
                return dc.get("name")
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
