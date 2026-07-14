#!/usr/bin/env python3
# commands/loadbalancer.py - Load balancer-related commands for hicloud

from typing import Dict, List, Optional, Tuple

from commands.base import BaseCommands
from utils.prompts import prompt_choice, prompt_int


class LoadBalancerCommands(BaseCommands):
    """Load balancer-related commands for Interactive Console."""

    label = "lb"
    usage = "lb list|info|create|delete|targets|service|algorithm"

    def _build_actions(self):
        return {
            "list": lambda args: self.list_load_balancers(),
            "info": self.show_load_balancer_info,
            "create": lambda args: self.create_load_balancer(),
            "delete": self.delete_load_balancer,
            "targets": self.manage_targets,
            "service": self.manage_services,
            "algorithm": self.change_algorithm,
        }

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

        labels = self.prompt_labels()
        if labels == {}:
            labels = None

        print("\nLoad Balancer Creation Summary:")
        print(f"  Name:             {name}")
        print(f"  Type:             {type_name}")
        print(f"  Location:         {location_name}")
        print(f"  Public Interface: {'enabled' if public_interface else 'disabled'}")
        if labels:
            print(f"  Labels:           {labels}")

        if not self.confirm("\nCreate this load balancer?"):
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
        if not self.confirm(f"Are you sure you want to delete load balancer '{lb.get('name')}' (ID: {lb_id})?"):
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
        if not self.confirm(
            f"{action.capitalize()} target {target_label} {'to' if action == 'add' else 'from'} load balancer '{lb.get('name')}' (ID: {lb_id})?"
        ):
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
            print("Missing parameters. Use 'lb service <lb_id> list|add|update|delete'")
            print("Examples:")
            print("  lb service <lb_id> list")
            print("  lb service <lb_id> add")
            print("  lb service <lb_id> update <listen_port>")
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

            if not self.confirm(f"Delete service on port {listen_port} from load balancer '{lb.get('name')}' (ID: {lb_id})?"):
                return

            if self.hetzner.delete_lb_service(lb_id, listen_port):
                print(f"Service on port {listen_port} deleted from load balancer {lb_id}")
            else:
                print(f"Failed to delete service on port {listen_port}")
            return

        print(f"Unknown service action '{action}'. Use list|add|update|delete")

    def _add_service_wizard(self, lb_id: int, lb_name: str):
        """Interactive wizard to add a new service to a load balancer."""
        print(f"Adding service to load balancer '{lb_name}' (ID: {lb_id}):")

        protocol = prompt_choice("Protocol [tcp/http/https] (default: tcp): ", ["tcp", "http", "https"], default="tcp")
        listen_port = prompt_int("Listen port (1-65535): ", min_value=1, max_value=65535)
        destination_port = prompt_int("Destination port (1-65535): ", min_value=1, max_value=65535)

        # Health check
        service: Dict = {
            "protocol": protocol,
            "listen_port": listen_port,
            "destination_port": destination_port,
        }

        add_hc = input("Configure health check? [Y/n]: ").strip().lower()
        if add_hc not in ("n", "no"):
            hc_protocol = prompt_choice("Health check protocol [tcp/http] (default: tcp): ", ["tcp", "http"], default="tcp")
            hc_port = prompt_int(f"Health check port (default: {destination_port}): ",
                                 default=destination_port, min_value=1, max_value=65535)
            hc_interval = prompt_int("Check interval in seconds (default: 15): ", default=15, min_value=1)
            hc_timeout = prompt_int("Timeout in seconds (default: 10): ", default=10, min_value=1)
            hc_retries = prompt_int("Retries (default: 3): ", default=3, min_value=1)

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

        if not self.confirm("\nAdd this service?"):
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
        protocol = prompt_choice(f"Protocol [tcp/http/https] (current: {cur_protocol}): ",
                                 ["tcp", "http", "https"], default=cur_protocol)

        cur_dest = current.get("destination_port", listen_port)
        destination_port = prompt_int(f"Destination port (current: {cur_dest}): ",
                                      default=cur_dest, min_value=1, max_value=65535)

        service: Dict = {
            "listen_port": listen_port,
            "protocol": protocol,
            "destination_port": destination_port,
        }

        update_hc = input("Update health check? [y/N]: ").strip().lower()
        if update_hc == "y":
            cur_hc = current.get("health_check", {})
            cur_hc_proto = cur_hc.get("protocol", "tcp")
            hc_protocol = prompt_choice(f"Health check protocol [tcp/http] (current: {cur_hc_proto}): ",
                                        ["tcp", "http"], default=cur_hc_proto)

            cur_hc_port = cur_hc.get("port", destination_port)
            hc_port = prompt_int(f"Health check port (current: {cur_hc_port}): ",
                                 default=cur_hc_port, min_value=1, max_value=65535)

            cur_interval = cur_hc.get("interval", 15)
            hc_interval = prompt_int(f"Check interval seconds (current: {cur_interval}): ",
                                     default=cur_interval, min_value=1)

            cur_timeout = cur_hc.get("timeout", 10)
            hc_timeout = prompt_int(f"Timeout seconds (current: {cur_timeout}): ",
                                    default=cur_timeout, min_value=1)

            cur_retries = cur_hc.get("retries", 3)
            hc_retries = prompt_int(f"Retries (current: {cur_retries}): ",
                                    default=cur_retries, min_value=1)

            service["health_check"] = {
                "protocol": hc_protocol,
                "port": hc_port,
                "interval": hc_interval,
                "timeout": hc_timeout,
                "retries": hc_retries,
            }

        if not self.confirm(f"\nUpdate service on port {listen_port}?"):
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

        if not self.confirm(f"Change algorithm for '{lb.get('name')}' (ID: {lb_id}) from '{current}' to '{algorithm}'?"):
            return

        if self.hetzner.change_lb_algorithm(lb_id, algorithm):
            print(f"Algorithm for load balancer {lb_id} changed to '{algorithm}'")
        else:
            print(f"Failed to change algorithm for load balancer {lb_id}")

    def _resolve_lb_from_args(self, args: List[str], usage: str) -> Dict:
        """Resolve load balancer by first arg with standard validation."""
        lb_id = self.parse_id(args, "load balancer ID", usage)
        if lb_id is None:
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
                # Fehlermeldung kommt bereits aus dem API-Layer
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
