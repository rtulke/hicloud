#!/usr/bin/env python3
# commands/network.py - Network-related commands for hicloud

from typing import List

class NetworkCommands:
    """Network-related commands for Interactive Console"""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle network-related commands"""
        if not args:
            print("Missing network subcommand. Use 'network list|info|create|update|delete|attach|detach|subnet|protect'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_networks()
        elif subcommand == "info":
            self.show_network_info(args[1:])
        elif subcommand == "create":
            self.create_network()
        elif subcommand == "update":
            self.update_network(args[1:])
        elif subcommand == "delete":
            self.delete_network(args[1:])
        elif subcommand == "attach":
            self.attach_server(args[1:])
        elif subcommand == "detach":
            self.detach_server(args[1:])
        elif subcommand == "subnet":
            self.manage_subnet(args[1:])
        elif subcommand == "protect":
            self.protect_network(args[1:])
        else:
            print(f"Unknown network subcommand: {subcommand}")

    def list_networks(self):
        """List all networks"""
        networks = self.hetzner.list_networks()

        if not networks:
            print("No networks found")
            return

        # Prepare data for table
        headers = ["ID", "Name", "IP Range", "Subnets", "Servers", "Protection"]
        rows = []

        for network in sorted(networks, key=lambda x: x.get('name', '').lower()):
            network_id = network.get('id', 'N/A')
            name = network.get('name', 'N/A')
            ip_range = network.get('ip_range', 'N/A')

            # Count subnets
            subnets = network.get('subnets', [])
            subnet_count = len(subnets)

            # Count servers
            servers = network.get('servers', [])
            server_count = len(servers)

            # Protection status
            protection = network.get('protection', {})
            delete_protected = "Yes" if protection.get('delete', False) else "No"

            rows.append([network_id, name, ip_range, subnet_count, server_count, delete_protected])

        # Print table with dynamic column widths
        self.console.print_table(headers, rows, "Networks")

    def show_network_info(self, args: List[str]):
        """Show detailed information about a network"""
        if not args:
            print("Missing network ID. Use 'network info <id>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        network = self.hetzner.get_network_by_id(network_id)

        if not network:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Network Information: \033[1;32m{network.get('name')}\033[0m (ID: {network_id})")
        print(f"{self.console.horizontal_line('=')}")

        # Basic information
        print(f"IP Range:    {network.get('ip_range', 'N/A')}")

        created = network.get('created', 'N/A')
        if created != 'N/A':
            created_date = created.split('T')[0]
            created_time = created.split('T')[1].split('+')[0] if '+' in created else created.split('T')[1].split('Z')[0]
            print(f"Created:     {created_date} {created_time}")

        # Subnets
        subnets = network.get('subnets', [])
        if subnets:
            print(f"\nSubnets ({len(subnets)}):")
            for subnet in subnets:
                zone = subnet.get('network_zone', 'N/A')
                ip_range = subnet.get('ip_range', 'N/A')
                gateway = subnet.get('gateway', 'N/A')
                subnet_type = subnet.get('type', 'N/A')
                print(f"  - {ip_range} (Zone: {zone}, Gateway: {gateway}, Type: {subnet_type})")
        else:
            print("\nSubnets: None")

        # Routes
        routes = network.get('routes', [])
        if routes:
            print(f"\nRoutes ({len(routes)}):")
            for route in routes:
                destination = route.get('destination', 'N/A')
                gateway = route.get('gateway', 'N/A')
                print(f"  - {destination} via {gateway}")

        # Attached servers
        servers = network.get('servers', [])
        if servers:
            print(f"\nAttached Servers ({len(servers)}):")
            for server_id in servers:
                server = self.hetzner.get_server_by_id(server_id)
                if server:
                    # Find the IP address in this network
                    private_nets = server.get('private_net', [])
                    ip_addr = "N/A"
                    for pnet in private_nets:
                        if pnet.get('network') == network_id:
                            ip_addr = pnet.get('ip', 'N/A')
                            break
                    print(f"  - {server.get('name')} (ID: {server_id}, IP: {ip_addr})")
                else:
                    print(f"  - Server ID: {server_id}")
        else:
            print("\nAttached Servers: None")

        # Labels
        labels = network.get('labels', {})
        if labels:
            print("\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")
        else:
            print("\nLabels: None")

        # Protection
        protection = network.get('protection', {})
        delete_protected = "Enabled" if protection.get('delete', False) else "Disabled"
        print(f"\nProtection:")
        print(f"  Delete Protection: {delete_protected}")

        print(f"{self.console.horizontal_line('-')}")

    def create_network(self):
        """Create a new network (interactive)"""
        print("Create a new Network:")

        # Get name
        name = input("Network Name: ").strip()
        if not name:
            print("Network name is required")
            return

        # Get IP range
        print("\nIP Range (e.g., 10.0.0.0/16):")
        print("  Private IP ranges:")
        print("    - 10.0.0.0/8     (10.0.0.0 - 10.255.255.255)")
        print("    - 172.16.0.0/12  (172.16.0.0 - 172.31.255.255)")
        print("    - 192.168.0.0/16 (192.168.0.0 - 192.168.255.255)")
        ip_range = input("IP Range: ").strip()

        if not ip_range:
            print("IP range is required")
            return

        # Validate IP range format (basic check)
        if '/' not in ip_range:
            print("Invalid IP range format. Must be CIDR notation (e.g., 10.0.0.0/16)")
            return

        # Optional: Create subnets
        subnets = []
        add_subnets = input("\nAdd subnets now? [y/N]: ").strip().lower()

        if add_subnets == 'y':
            # Get available network zones
            print("\nAvailable Network Zones:")
            locations = self.hetzner.list_locations()
            zones = set()
            for loc in locations:
                zone = loc.get('network_zone')
                if zone:
                    zones.add(zone)

            for i, zone in enumerate(sorted(zones), 1):
                print(f"  {i}. {zone}")

            while True:
                zone_input = input("\nNetwork Zone (or press Enter to finish): ").strip()
                if not zone_input:
                    break

                if zone_input not in zones:
                    print(f"Invalid zone. Must be one of: {', '.join(sorted(zones))}")
                    continue

                subnet_range = input(f"Subnet IP Range for {zone_input}: ").strip()
                if not subnet_range or '/' not in subnet_range:
                    print("Invalid subnet range")
                    continue

                subnet_type = input("Subnet Type [cloud/server/vswitch] (default: cloud): ").strip() or "cloud"

                subnets.append({
                    "network_zone": zone_input,
                    "ip_range": subnet_range,
                    "type": subnet_type
                })
                print(f"Subnet added: {subnet_range} in {zone_input}")

        # Optional labels
        labels = {}
        add_labels = input("\nAdd labels? [y/N]: ").strip().lower()
        if add_labels == 'y':
            while True:
                key = input("Label key (or press Enter to finish): ").strip()
                if not key:
                    break
                value = input(f"Label value for '{key}': ").strip()
                labels[key] = value

        # Summary
        print("\nNetwork Creation Summary:")
        print(f"  Name:     {name}")
        print(f"  IP Range: {ip_range}")
        if subnets:
            print(f"  Subnets:  {len(subnets)} subnet(s)")
            for subnet in subnets:
                print(f"    - {subnet['ip_range']} ({subnet['network_zone']})")
        if labels:
            print(f"  Labels:   {labels}")

        confirm = input("\nCreate this network? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print("Creating network...")

        # Create network
        network = self.hetzner.create_network(
            name=name,
            ip_range=ip_range,
            subnets=subnets if subnets else None,
            labels=labels if labels else None
        )

        if network:
            print(f"\nNetwork created successfully!")
            print(f"ID:       {network.get('id')}")
            print(f"Name:     {network.get('name')}")
            print(f"IP Range: {network.get('ip_range')}")
        else:
            print(f"Failed to create network")

    def update_network(self, args: List[str]):
        """Update network metadata (name and/or labels)"""
        if not args:
            print("Missing network ID. Use 'network update <id>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        # Get current network info
        network = self.hetzner.get_network_by_id(network_id)

        if not network:
            return

        print(f"\nUpdating Network: \033[1;32m{network.get('name')}\033[0m (ID: {network_id})")
        print(f"{self.console.horizontal_line('-')}")

        # Update name
        new_name = None
        name_input = input(f"New name (leave empty to keep '{network.get('name')}'): ").strip()
        if name_input:
            new_name = name_input

        # Update labels
        update_labels_input = input("\nUpdate labels? [y/N]: ").strip().lower()
        new_labels = None

        if update_labels_input == 'y':
            # Show current labels
            current_labels = network.get('labels', {})
            if current_labels:
                print("\nCurrent labels:")
                for k, v in current_labels.items():
                    print(f"  {k}: {v}")

            print("\nEnter new labels (this will replace all existing labels):")
            new_labels = {}
            while True:
                label_key = input("Label key (or press Enter to finish): ").strip()
                if not label_key:
                    break
                label_value = input(f"Label value for '{label_key}': ").strip()
                new_labels[label_key] = label_value

        # Check if any updates were made
        if new_name is None and new_labels is None:
            print("\nNo changes made.")
            return

        # Summary
        print("\nUpdate Summary:")
        if new_name:
            print(f"  Name: {network.get('name')} → {new_name}")
        if new_labels is not None:
            print(f"  Labels: {len(new_labels)} labels")

        confirm = input("\nApply these changes? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Updating network {network_id}...")

        # Update network
        updated_network = self.hetzner.update_network(
            network_id=network_id,
            name=new_name,
            labels=new_labels
        )

        if updated_network:
            print(f"Network {network_id} updated successfully")
            if new_name:
                print(f"  New name: {updated_network.get('name')}")
            if new_labels is not None:
                print(f"  Labels updated: {len(updated_network.get('labels', {}))} labels")
        else:
            print(f"Failed to update network {network_id}")

    def delete_network(self, args: List[str]):
        """Delete a network by ID"""
        if not args:
            print("Missing network ID. Use 'network delete <id>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        network = self.hetzner.get_network_by_id(network_id)

        if not network:
            return

        # Check if network has attached servers
        servers = network.get('servers', [])
        if servers:
            print(f"WARNING: Network '{network.get('name')}' has {len(servers)} attached server(s).")
            print("You must detach all servers before deletion.")
            print("\nAttached servers:")
            for server_id in servers:
                server = self.hetzner.get_server_by_id(server_id)
                if server:
                    print(f"  - {server.get('name')} (ID: {server_id})")
            print("\nUse 'network detach <network_id> <server_id>' to detach servers.")
            return

        confirm = input(f"Are you sure you want to delete network '{network.get('name')}' (ID: {network_id})? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Deleting network {network_id}...")
        if self.hetzner.delete_network(network_id):
            print(f"Network {network_id} deleted successfully")
        else:
            print(f"Failed to delete network {network_id}")

    def attach_server(self, args: List[str]):
        """Attach a server to a network"""
        if len(args) < 2:
            print("Missing parameters. Use 'network attach <network_id> <server_id> [ip]'")
            return

        try:
            network_id = int(args[0])
            server_id = int(args[1])
        except ValueError:
            print("Invalid ID format. Both network ID and server ID must be integers.")
            return

        # Optional IP address
        ip = args[2] if len(args) > 2 else None

        # Get network details
        network = self.hetzner.get_network_by_id(network_id)
        if not network:
            return

        # Get server details
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        # Check if server is already attached
        servers = network.get('servers', [])
        if server_id in servers:
            print(f"Server '{server.get('name')}' is already attached to network '{network.get('name')}'")
            return

        print(f"Attaching server '{server.get('name')}' to network '{network.get('name')}'...")
        if ip:
            print(f"Assigning IP: {ip}")

        if self.hetzner.attach_server_to_network(network_id, server_id, ip):
            print(f"Server {server_id} successfully attached to network {network_id}")
        else:
            print(f"Failed to attach server {server_id} to network {network_id}")

    def detach_server(self, args: List[str]):
        """Detach a server from a network"""
        if len(args) < 2:
            print("Missing parameters. Use 'network detach <network_id> <server_id>'")
            return

        try:
            network_id = int(args[0])
            server_id = int(args[1])
        except ValueError:
            print("Invalid ID format. Both network ID and server ID must be integers.")
            return

        # Get network details
        network = self.hetzner.get_network_by_id(network_id)
        if not network:
            return

        # Get server details
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            return

        # Check if server is attached
        servers = network.get('servers', [])
        if server_id not in servers:
            print(f"Server '{server.get('name')}' is not attached to network '{network.get('name')}'")
            return

        confirm = input(f"Detach server '{server.get('name')}' from network '{network.get('name')}'? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Detaching server {server_id} from network {network_id}...")
        if self.hetzner.detach_server_from_network(network_id, server_id):
            print(f"Server {server_id} successfully detached from network {network_id}")
        else:
            print(f"Failed to detach server {server_id} from network {network_id}")

    def manage_subnet(self, args: List[str]):
        """Manage subnets (add/delete)"""
        if not args:
            print("Missing subnet action. Use 'network subnet add|delete <network_id> ...'")
            return

        action = args[0].lower()

        if action == "add":
            self.add_subnet(args[1:])
        elif action == "delete":
            self.delete_subnet(args[1:])
        else:
            print(f"Unknown subnet action: {action}")
            print("Use 'network subnet add' or 'network subnet delete'")

    def add_subnet(self, args: List[str]):
        """Add a subnet to a network"""
        if not args:
            print("Missing network ID. Use 'network subnet add <network_id>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        network = self.hetzner.get_network_by_id(network_id)
        if not network:
            return

        print(f"\nAdding subnet to network: \033[1;32m{network.get('name')}\033[0m")
        print(f"Network IP Range: {network.get('ip_range')}")

        # Get available network zones
        print("\nAvailable Network Zones:")
        locations = self.hetzner.list_locations()
        zones = set()
        for loc in locations:
            zone = loc.get('network_zone')
            if zone:
                zones.add(zone)

        for i, zone in enumerate(sorted(zones), 1):
            print(f"  {i}. {zone}")

        zone_input = input("\nNetwork Zone: ").strip()
        if zone_input not in zones:
            print(f"Invalid zone. Must be one of: {', '.join(sorted(zones))}")
            return

        subnet_range = input("Subnet IP Range (must be within network range): ").strip()
        if not subnet_range or '/' not in subnet_range:
            print("Invalid subnet range")
            return

        subnet_type = input("Subnet Type [cloud/server/vswitch] (default: cloud): ").strip() or "cloud"

        confirm = input(f"\nAdd subnet {subnet_range} to network? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Adding subnet to network {network_id}...")
        result = self.hetzner.add_subnet_to_network(network_id, zone_input, subnet_range, subnet_type)

        if result:
            print(f"Subnet {subnet_range} added successfully to network {network_id}")
        else:
            print(f"Failed to add subnet to network {network_id}")

    def delete_subnet(self, args: List[str]):
        """Delete a subnet from a network"""
        if len(args) < 2:
            print("Missing parameters. Use 'network subnet delete <network_id> <ip_range>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        ip_range = args[1]

        network = self.hetzner.get_network_by_id(network_id)
        if not network:
            return

        # Check if subnet exists
        subnets = network.get('subnets', [])
        subnet_found = False
        for subnet in subnets:
            if subnet.get('ip_range') == ip_range:
                subnet_found = True
                break

        if not subnet_found:
            print(f"Subnet {ip_range} not found in network '{network.get('name')}'")
            return

        confirm = input(f"Delete subnet {ip_range} from network '{network.get('name')}'? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"Deleting subnet from network {network_id}...")
        if self.hetzner.delete_subnet_from_network(network_id, ip_range):
            print(f"Subnet {ip_range} deleted successfully from network {network_id}")
        else:
            print(f"Failed to delete subnet from network {network_id}")

    def protect_network(self, args: List[str]):
        """Enable or disable network protection"""
        if len(args) < 2:
            print("Missing parameters. Use 'network protect <id> <enable|disable>'")
            return

        try:
            network_id = int(args[0])
        except ValueError:
            print("Invalid network ID. Must be an integer.")
            return

        action = args[1].lower()
        if action not in ['enable', 'disable']:
            print("Action must be 'enable' or 'disable'")
            return

        enable_protection = (action == 'enable')

        # Get network details
        network = self.hetzner.get_network_by_id(network_id)
        if not network:
            return

        action_text = "enable" if enable_protection else "disable"
        confirm = input(f"{action_text.capitalize()} delete protection for network '{network.get('name')}'? [y/N]: ")

        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print(f"{action_text.capitalize()}ing protection for network {network_id}...")
        result = self.hetzner.change_network_protection(network_id, delete=enable_protection)

        if result:
            print(f"Delete protection {action}d for network {network_id}")
        else:
            print(f"Failed to {action} protection for network {network_id}")
