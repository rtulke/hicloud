#!/usr/bin/env python3
# commands/loadbalancer.py - Load balancer-related commands for hicloud

from typing import Dict, List, Optional, Tuple


class LoadBalancerCommands:
    """Load balancer-related commands for Interactive Console."""

    def __init__(self, console):
        """Initialize with reference to the console."""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle load balancer-related commands."""
        if not args:
            print("Missing lb subcommand. Use 'lb list|info|create|delete|targets|service|algorithm'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_load_balancers()
        elif subcommand == "info":
            self.show_load_balancer_info(args[1:])
        elif subcommand == "create":
            self.create_load_balancer()
        elif subcommand == "delete":
            self.delete_load_balancer(args[1:])
        elif subcommand == "targets":
            self.manage_targets(args[1:])
        elif subcommand == "service":
            self.manage_services(args[1:])
        elif subcommand == "algorithm":
            self.change_algorithm(args[1:])
        else:
            print(f"Unknown lb subcommand: {subcommand}")

    def list_load_balancers(self):
        """List all load balancers."""
        load_balancers = self.hetzner.list_load_balancers()
        if not load_balancers:
            print("No load balancers found")
            return

        headers = ["ID", "Name", "Type", "Location", "Targets", "Services", "IPv4"]
        rows = []

        for lb in sorted(load_balancers, key=lambda x: x.get("name", "").lower()):
            lb_id = lb.get("id", "N/A")
            name = lb.get("name", "N/A")
            lb_type = lb.get("load_balancer_type", {}).get("name", "N/A")
            location = lb.get("location", {}).get("name", "N/A")
            target_count = len(lb.get("targets", []))
            service_count = len(lb.get("services", []))
            ipv4 = lb.get("public_net", {}).get("ipv4", {}).get("ip", "-")

            rows.append([lb_id, name, lb_type, location, target_count, service_count, ipv4])

        self.console.print_table(headers, rows, "Load Balancers")

    def show_load_balancer_info(self, args: List[str]):
        """Show detailed information about a load balancer."""
        lb = self._resolve_lb_from_args(args, "lb info <id>")
        if not lb:
            return

        lb_id = lb.get("id")
        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Load Balancer Information: \033[1;32m{lb.get('name')}\033[0m (ID: {lb_id})")
        print(f"{self.console.horizontal_line('=')}")

        lb_type = lb.get("load_balancer_type", {})
        print(f"Type:        {lb_type.get('name', 'N/A')}")
        print(f"Algorithm:   {lb.get('algorithm', {}).get('type', 'N/A')}")
        print(f"Location:    {lb.get('location', {}).get('name', 'N/A')}")
        print(f"Network Zone:{lb.get('network_zone', 'N/A')}")

        public_net = lb.get("public_net", {})
        print("\nPublic Network:")
        print(f"  IPv4: {public_net.get('ipv4', {}).get('ip', '-')}")
        print(f"  IPv6: {public_net.get('ipv6', {}).get('ip', '-')}")

        self._print_targets(lb.get("targets", []))
        self._print_services(lb.get("services", []))

        labels = lb.get("labels", {})
        if labels:
            print("\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")
        else:
            print("\nLabels: None")

        print(f"{self.console.horizontal_line('-')}")

    def create_load_balancer(self):
        """Create a new load balancer."""
        print("Create a new Load Balancer:")

        name = input("Load Balancer Name: ").strip()
        if not name:
            print("Load balancer name is required")
            return

        lb_types = self.hetzner.list_load_balancer_types()
        if not lb_types:
            print("No load balancer types available")
            return

        print("\nAvailable Load Balancer Types:")
        for index, lb_type in enumerate(lb_types, start=1):
            print(f"  {index}. {lb_type.get('name', 'N/A')}")

        type_choice = input("Select type (number or name): ").strip()
        type_name = self._resolve_type_choice(lb_types, type_choice)
        if not type_name:
            print("Invalid load balancer type selection.")
            return

        locations = self.hetzner.list_locations()
        if not locations:
            print("No locations available")
            return

        print("\nAvailable Locations:")
        for index, location in enumerate(locations, start=1):
            print(f"  {index}. {location.get('name', 'N/A')} ({location.get('description', 'N/A')})")

        location_choice = input("Select location (number or name): ").strip()
        location_name = self._resolve_location_choice(locations, location_choice)
        if not location_name:
            print("Invalid location selection.")
            return

        public_interface_input = input("Enable public interface? [Y/n]: ").strip().lower()
        public_interface = public_interface_input not in {"n", "no"}

        labels = self._prompt_for_labels()
        if labels == {}:
            labels = None

        print("\nLoad Balancer Creation Summary:")
        print(f"  Name:             {name}")
        print(f"  Type:             {type_name}")
        print(f"  Location:         {location_name}")
        print(f"  Public Interface: {'enabled' if public_interface else 'disabled'}")
        if labels:
            print(f"  Labels:           {labels}")

        confirm = input("\nCreate this load balancer? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print("Creating load balancer...")
        lb = self.hetzner.create_load_balancer(
            name=name,
            load_balancer_type=type_name,
            location=location_name,
            labels=labels,
            public_interface=public_interface,
        )

        if lb:
            print("\nLoad balancer created successfully!")
            print(f"ID:       {lb.get('id')}")
            print(f"Name:     {lb.get('name')}")
            print(f"Location: {lb.get('location', {}).get('name', location_name)}")
        else:
            print("Failed to create load balancer")

    def delete_load_balancer(self, args: List[str]):
        """Delete a load balancer by ID."""
        lb = self._resolve_lb_from_args(args, "lb delete <id>")
        if not lb:
            return

        lb_id = lb.get("id")
        confirm = input(f"Are you sure you want to delete load balancer '{lb.get('name')}' (ID: {lb_id})? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        print(f"Deleting load balancer {lb_id}...")
        if self.hetzner.delete_load_balancer(lb_id):
            print(f"Load balancer {lb_id} deleted successfully")
        else:
            print(f"Failed to delete load balancer {lb_id}")

    def manage_targets(self, args: List[str]):
        """Manage load balancer targets."""
        if len(args) < 2:
            print("Missing parameters. Use 'lb targets <lb_id> list|add|remove ...'")
            print("Examples:")
            print("  lb targets <lb_id> list")
            print("  lb targets <lb_id> add server <server_id> [private]")
            print("  lb targets <lb_id> add label <selector>")
            print("  lb targets <lb_id> remove server <server_id>")
            print("  lb targets <lb_id> remove label <selector>")
            return

        lb = self._resolve_lb_from_args([args[0]], "lb targets <lb_id> ...")
        if not lb:
            return

        lb_id = lb.get("id")
        action = args[1].lower()

        if action == "list":
            self._print_targets(lb.get("targets", []), title=f"Targets for '{lb.get('name')}'")
            return

        if action not in {"add", "remove"}:
            print("Invalid target action. Use 'list', 'add' or 'remove'.")
            return

        if len(args) < 4:
            print("Missing target type/value.")
            return

        target_type = args[2].lower()
        target_value = " ".join(args[3:]).strip()

        target = self._build_target(target_type, target_value, action == "add")
        if target is None:
            return

        target_label = self._target_to_label(target)
        confirm = input(
            f"{action.capitalize()} target {target_label} {'to' if action == 'add' else 'from'} load balancer '{lb.get('name')}' (ID: {lb_id})? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        if action == "add":
            print(f"Adding target to load balancer {lb_id}...")
            ok = self.hetzner.add_load_balancer_target(lb_id, target)
        else:
            print(f"Removing target from load balancer {lb_id}...")
            ok = self.hetzner.remove_load_balancer_target(lb_id, target)

        if ok:
            print(f"Target {action} operation completed successfully")
        else:
            print(f"Failed to {action} target")

    def manage_services(self, args: List[str]):
        """Manage load balancer services."""
        if len(args) < 2:
            print("Missing parameters. Use 'lb service <lb_id> list|add|delete'")
            print("Examples:")
            print("  lb service <lb_id> list")
            print("  lb service <lb_id> add")
            print("  lb service <lb_id> delete <listen_port>")
            return

        lb = self._resolve_lb_from_args([args[0]], "lb service <lb_id> list|add|delete")
        if not lb:
            return

        lb_id = lb.get("id")
        action = args[1].lower()

        if action == "list":
            self._print_services(lb.get("services", []))
            return

        if action == "add":
            self._add_service_wizard(lb_id, lb.get("name", str(lb_id)))
            return

        if action == "update":
            if len(args) < 3:
                print("Missing listen port. Use 'lb service <lb_id> update <listen_port>'")
                return
            try:
                listen_port = int(args[2])
            except ValueError:
                print("Invalid listen port. Must be an integer.")
                return
            self._update_service_wizard(lb_id, lb.get("name", str(lb_id)), listen_port, lb.get("services", []))
            return

        if action == "delete":
            if len(args) < 3:
                print("Missing listen port. Use 'lb service <lb_id> delete <listen_port>'")
                return
            try:
                listen_port = int(args[2])
            except ValueError:
                print("Invalid listen port. Must be an integer.")
                return

            confirm = input(
                f"Delete service on port {listen_port} from load balancer '{lb.get('name')}' (ID: {lb_id})? [y/N]: "
            ).strip().lower()
            if confirm != "y":
                print("Operation cancelled")
                return

            if self.hetzner.delete_lb_service(lb_id, listen_port):
                print(f"Service on port {listen_port} deleted from load balancer {lb_id}")
            else:
                print(f"Failed to delete service on port {listen_port}")
            return

        print(f"Unknown service action '{action}'. Use list|add|delete")

    def _add_service_wizard(self, lb_id: int, lb_name: str):
        """Interactive wizard to add a new service to a load balancer."""
        print(f"Adding service to load balancer '{lb_name}' (ID: {lb_id}):")

        # Protocol
        while True:
            protocol = input("Protocol [tcp/http/https] (default: tcp): ").strip().lower() or "tcp"
            if protocol in ("tcp", "http", "https"):
                break
            print("Invalid protocol. Use tcp, http, or https.")

        # Listen port
        while True:
            try:
                listen_port = int(input("Listen port (1-65535): ").strip())
                if 1 <= listen_port <= 65535:
                    break
                print("Port must be between 1 and 65535.")
            except ValueError:
                print("Invalid port. Must be an integer.")

        # Destination port
        while True:
            try:
                destination_port = int(input("Destination port (1-65535): ").strip())
                if 1 <= destination_port <= 65535:
                    break
                print("Port must be between 1 and 65535.")
            except ValueError:
                print("Invalid port. Must be an integer.")

        # Health check
        service: Dict = {
            "protocol": protocol,
            "listen_port": listen_port,
            "destination_port": destination_port,
        }

        add_hc = input("Configure health check? [Y/n]: ").strip().lower()
        if add_hc not in ("n", "no"):
            hc_protocol = input("Health check protocol [tcp/http] (default: tcp): ").strip().lower() or "tcp"
            if hc_protocol not in ("tcp", "http"):
                hc_protocol = "tcp"

            try:
                hc_port = int(input(f"Health check port (default: {destination_port}): ").strip() or destination_port)
            except ValueError:
                hc_port = destination_port

            try:
                hc_interval = int(input("Check interval in seconds (default: 15): ").strip() or 15)
            except ValueError:
                hc_interval = 15

            try:
                hc_timeout = int(input("Timeout in seconds (default: 10): ").strip() or 10)
            except ValueError:
                hc_timeout = 10

            try:
                hc_retries = int(input("Retries (default: 3): ").strip() or 3)
            except ValueError:
                hc_retries = 3

            health_check: Dict = {
                "protocol": hc_protocol,
                "port": hc_port,
                "interval": hc_interval,
                "timeout": hc_timeout,
                "retries": hc_retries,
            }
            service["health_check"] = health_check

        # Sticky sessions (only for http/https)
        if protocol in ("http", "https"):
            sticky = input("Enable sticky sessions? [y/N]: ").strip().lower()
            if sticky == "y":
                cookie_name = input("Cookie name (default: SERVERID): ").strip() or "SERVERID"
                service["stickiness"] = {
                    "enabled": True,
                    "cookie_name": cookie_name,
                }

        print("\nService Summary:")
        print(f"  Protocol:         {protocol}")
        print(f"  Listen Port:      {listen_port}")
        print(f"  Destination Port: {destination_port}")
        if "health_check" in service:
            hc = service["health_check"]
            print(f"  Health Check:     {hc['protocol']}:{hc['port']} every {hc['interval']}s, timeout {hc['timeout']}s, retries {hc['retries']}")
        if "stickiness" in service:
            print(f"  Sticky Sessions:  enabled (cookie: {service['stickiness']['cookie_name']})")

        confirm = input("\nAdd this service? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        if self.hetzner.add_lb_service(lb_id, service):
            print(f"Service added to load balancer {lb_id} successfully")
        else:
            print(f"Failed to add service to load balancer {lb_id}")

    def _update_service_wizard(self, lb_id: int, lb_name: str, listen_port: int, existing_services: List[Dict]):
        """Interactive wizard to update an existing service on a load balancer."""
        current = next((s for s in existing_services if s.get("listen_port") == listen_port), None)
        if not current:
            print(f"No service found on listen port {listen_port} for load balancer '{lb_name}'.")
            return

        print(f"Updating service (port {listen_port}) on load balancer '{lb_name}' (ID: {lb_id}):")
        print("Press Enter to keep the current value.\n")

        cur_protocol = current.get("protocol", "tcp")
        protocol_input = input(f"Protocol [tcp/http/https] (current: {cur_protocol}): ").strip().lower()
        protocol = protocol_input if protocol_input in ("tcp", "http", "https") else cur_protocol

        cur_dest = current.get("destination_port", listen_port)
        dest_input = input(f"Destination port (current: {cur_dest}): ").strip()
        try:
            destination_port = int(dest_input) if dest_input else cur_dest
        except ValueError:
            destination_port = cur_dest

        service: Dict = {
            "listen_port": listen_port,
            "protocol": protocol,
            "destination_port": destination_port,
        }

        update_hc = input("Update health check? [y/N]: ").strip().lower()
        if update_hc == "y":
            cur_hc = current.get("health_check", {})
            cur_hc_proto = cur_hc.get("protocol", "tcp")
            hc_proto_input = input(f"Health check protocol [tcp/http] (current: {cur_hc_proto}): ").strip().lower()
            hc_protocol = hc_proto_input if hc_proto_input in ("tcp", "http") else cur_hc_proto

            cur_hc_port = cur_hc.get("port", destination_port)
            hc_port_input = input(f"Health check port (current: {cur_hc_port}): ").strip()
            try:
                hc_port = int(hc_port_input) if hc_port_input else cur_hc_port
            except ValueError:
                hc_port = cur_hc_port

            cur_interval = cur_hc.get("interval", 15)
            interval_input = input(f"Check interval seconds (current: {cur_interval}): ").strip()
            try:
                hc_interval = int(interval_input) if interval_input else cur_interval
            except ValueError:
                hc_interval = cur_interval

            cur_timeout = cur_hc.get("timeout", 10)
            timeout_input = input(f"Timeout seconds (current: {cur_timeout}): ").strip()
            try:
                hc_timeout = int(timeout_input) if timeout_input else cur_timeout
            except ValueError:
                hc_timeout = cur_timeout

            cur_retries = cur_hc.get("retries", 3)
            retries_input = input(f"Retries (current: {cur_retries}): ").strip()
            try:
                hc_retries = int(retries_input) if retries_input else cur_retries
            except ValueError:
                hc_retries = cur_retries

            service["health_check"] = {
                "protocol": hc_protocol,
                "port": hc_port,
                "interval": hc_interval,
                "timeout": hc_timeout,
                "retries": hc_retries,
            }

        confirm = input(f"\nUpdate service on port {listen_port}? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        if self.hetzner.update_lb_service(lb_id, service):
            print(f"Service on port {listen_port} updated successfully")
        else:
            print(f"Failed to update service on port {listen_port}")

    def change_algorithm(self, args: List[str]):
        """Change the load balancing algorithm."""
        if len(args) < 2:
            print("Missing parameters. Use 'lb algorithm <lb_id> <round_robin|least_connections>'")
            return

        lb = self._resolve_lb_from_args([args[0]], "lb algorithm <lb_id> <algorithm>")
        if not lb:
            return

        lb_id = lb.get("id")
        algorithm = args[1].lower()

        if algorithm not in ("round_robin", "least_connections"):
            print(f"Invalid algorithm '{algorithm}'. Use 'round_robin' or 'least_connections'.")
            return

        current = lb.get("algorithm", {}).get("type", "N/A")
        if current == algorithm:
            print(f"Load balancer '{lb.get('name')}' already uses '{algorithm}'.")
            return

        confirm = input(
            f"Change algorithm for '{lb.get('name')}' (ID: {lb_id}) from '{current}' to '{algorithm}'? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        if self.hetzner.change_lb_algorithm(lb_id, algorithm):
            print(f"Algorithm for load balancer {lb_id} changed to '{algorithm}'")
        else:
            print(f"Failed to change algorithm for load balancer {lb_id}")

    def _resolve_lb_from_args(self, args: List[str], usage: str) -> Dict:
        """Resolve load balancer by first arg with standard validation."""
        if not args:
            print(f"Missing load balancer ID. Use '{usage}'")
            return {}

        try:
            lb_id = int(args[0])
        except ValueError:
            print("Invalid load balancer ID. Must be an integer.")
            return {}

        return self.hetzner.get_load_balancer_by_id(lb_id)

    def _resolve_type_choice(self, lb_types: List[Dict], choice: str) -> Optional[str]:
        """Resolve user type choice by number or exact name."""
        if not choice:
            return None

        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(lb_types):
                return lb_types[index].get("name")
            return None

        for lb_type in lb_types:
            if lb_type.get("name", "").lower() == choice.lower():
                return lb_type.get("name")
        return None

    def _resolve_location_choice(self, locations: List[Dict], choice: str) -> Optional[str]:
        """Resolve user location choice by number or exact name."""
        if not choice:
            return None

        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(locations):
                return locations[index].get("name")
            return None

        for location in locations:
            if location.get("name", "").lower() == choice.lower():
                return location.get("name")
        return None

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

    def _build_target(self, target_type: str, value: str, add_mode: bool) -> Optional[Dict]:
        """Build load balancer target object for API calls."""
        if target_type == "server":
            tokens = value.split()
            if not tokens:
                print("Missing server ID.")
                return None
            try:
                server_id = int(tokens[0])
            except ValueError:
                print("Invalid server ID. Must be an integer.")
                return None

            server = self.hetzner.get_server_by_id(server_id)
            if not server:
                print(f"Server with ID {server_id} not found")
                return None

            target = {
                "type": "server",
                "server": {"id": server_id},
            }

            if add_mode:
                use_private_ip = len(tokens) > 1 and tokens[1].lower() in {"private", "--private", "true", "yes", "y"}
                target["use_private_ip"] = use_private_ip

            return target

        if target_type == "label":
            selector = value.strip()
            if not selector:
                print("Label selector cannot be empty.")
                return None
            return {
                "type": "label_selector",
                "label_selector": {"selector": selector},
            }

        print("Invalid target type. Use 'server' or 'label'.")
        return None

    def _target_to_label(self, target: Dict) -> str:
        """Build human-friendly target string."""
        target_type = target.get("type")
        if target_type == "server":
            server_id = target.get("server", {}).get("id", "N/A")
            private = target.get("use_private_ip", False)
            suffix = " (private-ip)" if private else ""
            return f"server:{server_id}{suffix}"
        if target_type == "label_selector":
            selector = target.get("label_selector", {}).get("selector", "N/A")
            return f"label:{selector}"
        return str(target)

    def _print_targets(self, targets: List[Dict], title: str = "Targets"):
        """Render targets."""
        if not targets:
            print(f"\n{title}: None")
            return

        print(f"\n{title} ({len(targets)}):")
        for target in targets:
            target_type = target.get("type", "unknown")
            if target_type == "server":
                server_id = target.get("server", {}).get("id", "N/A")
                use_private_ip = target.get("use_private_ip", False)
                private_text = "yes" if use_private_ip else "no"
                print(f"  - server:{server_id} (use_private_ip={private_text})")
            elif target_type == "label_selector":
                selector = target.get("label_selector", {}).get("selector", "N/A")
                print(f"  - label:{selector}")
            else:
                print(f"  - {target}")

    def _print_services(self, services: List[Dict]):
        """Render services."""
        if not services:
            print("\nServices: None")
            return

        print(f"\nServices ({len(services)}):")
        for service in services:
            listen_port = service.get("listen_port", "N/A")
            destination_port = service.get("destination_port", "N/A")
            protocol = service.get("protocol", "N/A")
            print(f"  - {protocol} {listen_port} -> {destination_port}")
