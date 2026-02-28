#!/usr/bin/env python3
# commands/location.py - Location, Datacenter, and ServerType commands for hicloud

from typing import List, Optional

class LocationCommands:
    """Location and Datacenter-related commands for Interactive Console"""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle location-related commands"""
        if not args:
            print("Missing location subcommand. Use 'location list|info'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_locations()
        elif subcommand == "info":
            self.location_info(args[1:])
        else:
            print(f"Unknown location subcommand: {subcommand}")

    def list_locations(self):
        """List all available locations"""
        locations = self.hetzner.list_locations()

        if not locations:
            print("No locations found")
            return

        # Prepare data for table
        headers = ["ID", "Name", "City", "Country", "Network Zone"]
        rows = []

        # Sort locations by ID for predictable ordering
        for location in sorted(locations, key=lambda x: x.get('id', 0)):
            loc_id = location.get('id', 'N/A')
            name = location.get('name', 'N/A')
            city = location.get('city', 'N/A')
            country = location.get('country', 'N/A')
            network_zone = location.get('network_zone', 'N/A')

            rows.append([loc_id, name, city, country, network_zone])

        # Print table with dynamic column widths
        self.console.print_table(headers, rows, "Available Locations")

    def location_info(self, args: List[str]):
        """Show detailed information about a location"""
        if not args:
            print("Missing location ID. Use 'location info <id>'")
            return

        try:
            location_id = int(args[0])
        except ValueError:
            print("Invalid location ID. Must be an integer.")
            return

        location = self.hetzner.get_location_by_id(location_id)

        if not location:
            # Error message is already printed in get_location_by_id
            return

        print(f"\nLocation Details:")
        print(f"  ID:            {location.get('id', 'N/A')}")
        print(f"  Name:          {location.get('name', 'N/A')}")
        print(f"  Description:   {location.get('description', 'N/A')}")
        print(f"  City:          {location.get('city', 'N/A')}")
        print(f"  Country:       {location.get('country', 'N/A')}")
        print(f"  Network Zone:  {location.get('network_zone', 'N/A')}")
        print(f"  Latitude:      {location.get('latitude', 'N/A')}")
        print(f"  Longitude:     {location.get('longitude', 'N/A')}")


class DatacenterCommands:
    """Datacenter-related commands for Interactive Console"""

    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle datacenter-related commands"""
        if not args:
            print("Missing datacenter subcommand. Use 'datacenter list|info'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_datacenters()
        elif subcommand == "info":
            self.datacenter_info(args[1:])
        elif subcommand == "resources":
            self.datacenter_resources(args[1:])
        else:
            print(f"Unknown datacenter subcommand: {subcommand}")

    def list_datacenters(self):
        """List all available datacenters"""
        datacenters = self.hetzner.list_datacenters()

        if not datacenters:
            print("No datacenters found")
            return

        # Prepare data for table
        headers = ["ID", "Name", "Description", "Location"]
        rows = []

        # Sort datacenters by ID for predictable ordering
        for dc in sorted(datacenters, key=lambda x: x.get('id', 0)):
            dc_id = dc.get('id', 'N/A')
            name = dc.get('name', 'N/A')
            description = dc.get('description', 'N/A')
            location_name = dc.get('location', {}).get('name', 'N/A')

            rows.append([dc_id, name, description, location_name])

        # Print table with dynamic column widths
        self.console.print_table(headers, rows, "Available Datacenters")

    def datacenter_info(self, args: List[str]):
        """Show detailed information about a datacenter"""
        if not args:
            print("Missing datacenter ID. Use 'datacenter info <id>'")
            return

        try:
            datacenter_id = int(args[0])
        except ValueError:
            print("Invalid datacenter ID. Must be an integer.")
            return

        datacenter = self.hetzner.get_datacenter_by_id(datacenter_id)

        if not datacenter:
            # Error message is already printed in get_datacenter_by_id
            return

        print(f"\nDatacenter Details:")
        print(f"  ID:            {datacenter.get('id', 'N/A')}")
        print(f"  Name:          {datacenter.get('name', 'N/A')}")
        print(f"  Description:   {datacenter.get('description', 'N/A')}")

        location = datacenter.get('location', {})
        if location:
            print(f"\n  Location:")
            print(f"    Name:        {location.get('name', 'N/A')}")
            print(f"    City:        {location.get('city', 'N/A')}")
            print(f"    Country:     {location.get('country', 'N/A')}")
            print(f"    Network Zone: {location.get('network_zone', 'N/A')}")

        # Show supported types
        server_types = datacenter.get('server_types', {})
        if server_types:
            supported = server_types.get('supported', [])
            available = server_types.get('available', [])

            if supported:
                print(f"\n  Supported Server Types: {len(supported)} types")
            if available:
                print(f"  Available Server Types: {len(available)} types")

        # Show network zones
        network_zones = datacenter.get('network_zones', [])
        if network_zones:
            print(f"\n  Network Zones: {', '.join(network_zones)}")

    def datacenter_resources(self, args: List[str]):
        """Show resource counts per datacenter (optional filter by ID or location name)"""
        datacenters = self.hetzner.list_datacenters()
        if not datacenters:
            print("No datacenters found")
            return

        filter_token = args[0].lower() if args else None

        # Build lookup maps
        dc_map = {}
        location_to_dc_ids = {}
        selected_ids = set()

        for dc in datacenters:
            dc_id = dc.get("id")
            location = dc.get("location", {})
            location_id = location.get("id")
            location_name = location.get("name", "").lower()
            city = location.get("city", "").lower()

            dc_map[dc_id] = {
                "name": dc.get("name", "N/A"),
                "location": location.get("name", "N/A"),
                "location_id": location_id,
                "city": location.get("city", "N/A"),
                "servers": 0,
                "volumes": 0,
                "floating_ips": 0,
                "load_balancers": 0,
                "server_ids": [],
                "volume_ids": [],
                "floating_ip_ids": [],
                "load_balancer_ids": [],
            }

            if location_id is not None:
                location_to_dc_ids.setdefault(location_id, set()).add(dc_id)

            if filter_token:
                if str(dc_id) == filter_token or dc.get("name", "").lower() == filter_token:
                    selected_ids.add(dc_id)
                elif location_name == filter_token or city == filter_token:
                    selected_ids.add(dc_id)

        if filter_token and not selected_ids:
            print(f"No datacenter found matching '{filter_token}'")
            return

        target_ids = selected_ids if selected_ids else set(dc_map.keys())

        # Collect resources
        servers = self.hetzner.list_servers()
        for server in servers:
            dc_id = server.get("datacenter", {}).get("id")
            if dc_id in target_ids:
                info = dc_map.get(dc_id)
                info["servers"] += 1
                info["server_ids"].append(str(server.get("id")))

        # Volumes (grouped by location -> datacenter)
        volumes = self.hetzner.list_volumes()
        for volume in volumes:
            loc_id = volume.get("location", {}).get("id")
            if loc_id in location_to_dc_ids:
                for dc_id in location_to_dc_ids[loc_id]:
                    if dc_id in target_ids:
                        info = dc_map.get(dc_id)
                        info["volumes"] += 1
                        info["volume_ids"].append(str(volume.get("id")))

        # Floating IPs (home_location)
        status_code, fip_resp = self.hetzner._make_request("GET", "floating_ips")
        if status_code == 200:
            for fip in fip_resp.get("floating_ips", []):
                loc_id = fip.get("home_location", {}).get("id")
                if loc_id in location_to_dc_ids:
                    for dc_id in location_to_dc_ids[loc_id]:
                        if dc_id in target_ids:
                            info = dc_map.get(dc_id)
                            info["floating_ips"] += 1
                            info["floating_ip_ids"].append(str(fip.get("id")))

        # Load balancers
        status_code, lb_resp = self.hetzner._make_request("GET", "load_balancers")
        if status_code == 200:
            for lb in lb_resp.get("load_balancers", []):
                loc_id = lb.get("location", {}).get("id")
                if loc_id in location_to_dc_ids:
                    for dc_id in location_to_dc_ids[loc_id]:
                        if dc_id in target_ids:
                            info = dc_map.get(dc_id)
                            info["load_balancers"] += 1
                            info["load_balancer_ids"].append(str(lb.get("id")))

        # Build table
        headers = ["ID", "Name", "Location", "Servers", "Volumes", "Floating IPs", "Load Balancers"]
        rows = []
        for dc_id in sorted(target_ids):
            info = dc_map[dc_id]
            rows.append([
                dc_id,
                info["name"],
                info["location"],
                info["servers"],
                info["volumes"],
                info["floating_ips"],
                info["load_balancers"],
            ])

        self.console.print_table(headers, rows, "Datacenter Resources")

        # Detailed lists if a single DC was requested
        if len(target_ids) == 1:
            dc_id = next(iter(target_ids))
            info = dc_map[dc_id]
            print("\nDetails:")
            print(f"  Servers:        {', '.join(info['server_ids']) if info['server_ids'] else '-'}")
            print(f"  Volumes:        {', '.join(info['volume_ids']) if info['volume_ids'] else '-'}")
            print(f"  Floating IPs:   {', '.join(info['floating_ip_ids']) if info['floating_ip_ids'] else '-'}")
            print(f"  Load Balancers: {', '.join(info['load_balancer_ids']) if info['load_balancer_ids'] else '-'}")


class ServerTypeCommands:
    """Server type commands for Interactive Console."""

    def __init__(self, console):
        """Initialize with reference to the console."""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle server-type commands."""
        if not args:
            print("Missing server-type subcommand. Use 'server-type list|info'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_server_types(args[1:])
        elif subcommand == "info":
            self.show_server_type_info(args[1:])
        else:
            print(f"Unknown server-type subcommand: {subcommand}")

    def list_server_types(self, args: List[str]):
        """List all available server types, optionally filtered by location."""
        location_filter: Optional[str] = args[0].lower() if args else None

        server_types = self.hetzner.list_server_types()
        if not server_types:
            print("No server types found")
            return

        # Group by architecture
        groups = {}
        for st in server_types:
            arch = st.get("architecture", "x86")
            groups.setdefault(arch, []).append(st)

        for arch in sorted(groups.keys()):
            types = groups[arch]
            types.sort(key=lambda x: x.get("name", ""))

            headers = ["Name", "Cores", "Memory (GB)", "Disk (GB)", "Disk Type", "Hourly €", "Monthly €"]
            rows = []

            for st in types:
                name = st.get("name", "N/A")
                cores = st.get("cores", "N/A")
                memory = st.get("memory", "N/A")
                disk = st.get("disk", "N/A")
                disk_type = st.get("storage_type", "N/A")

                # Find price for the requested location (or first available)
                hourly = "-"
                monthly = "-"
                prices = st.get("prices", [])
                if prices:
                    price_entry = None
                    if location_filter:
                        for p in prices:
                            if p.get("location", "").lower() == location_filter:
                                price_entry = p
                                break
                    if price_entry is None:
                        price_entry = prices[0]

                    if price_entry:
                        ph = price_entry.get("price_hourly", {})
                        pm = price_entry.get("price_monthly", {})
                        hourly = ph.get("gross", ph.get("net", "-")) if isinstance(ph, dict) else str(ph)
                        monthly = pm.get("gross", pm.get("net", "-")) if isinstance(pm, dict) else str(pm)
                        try:
                            hourly = f"{float(hourly):.4f}"
                        except (ValueError, TypeError):
                            pass
                        try:
                            monthly = f"{float(monthly):.2f}"
                        except (ValueError, TypeError):
                            pass

                rows.append([name, cores, memory, disk, disk_type, hourly, monthly])

            title = f"Server Types — {arch.upper()}"
            if location_filter:
                title += f" (location: {location_filter})"
            self.console.print_table(headers, rows, title)

    def show_server_type_info(self, args: List[str]):
        """Show detailed information about a server type by name or ID."""
        if not args:
            print("Missing server type name or ID. Use 'server-type info <name|id>'")
            return

        identifier = args[0]
        server_types = self.hetzner.list_server_types()
        if not server_types:
            print("Could not retrieve server types")
            return

        # Resolve by name or numeric ID
        match = None
        try:
            numeric_id = int(identifier)
            for st in server_types:
                if st.get("id") == numeric_id:
                    match = st
                    break
        except ValueError:
            for st in server_types:
                if st.get("name", "").lower() == identifier.lower():
                    match = st
                    break

        if not match:
            print(f"Server type '{identifier}' not found")
            return

        print(f"\n{self.console.horizontal_line('=')}")
        print(f"Server Type: \033[1;32m{match.get('name', 'N/A')}\033[0m (ID: {match.get('id', 'N/A')})")
        print(f"{self.console.horizontal_line('=')}")
        print(f"Description:   {match.get('description', 'N/A')}")
        print(f"Architecture:  {match.get('architecture', 'N/A')}")
        print(f"Cores:         {match.get('cores', 'N/A')}")
        print(f"Memory:        {match.get('memory', 'N/A')} GB")
        print(f"Disk:          {match.get('disk', 'N/A')} GB ({match.get('storage_type', 'N/A')})")
        print(f"CPU Type:      {match.get('cpu_type', 'N/A')}")

        prices = match.get("prices", [])
        if prices:
            print("\nPricing by Location:")
            for p in prices:
                loc = p.get("location", "N/A")
                ph = p.get("price_hourly", {})
                pm = p.get("price_monthly", {})
                h_val = ph.get("gross", ph.get("net", "-")) if isinstance(ph, dict) else str(ph)
                m_val = pm.get("gross", pm.get("net", "-")) if isinstance(pm, dict) else str(pm)
                try:
                    h_val = f"€{float(h_val):.4f}/hr"
                except (ValueError, TypeError):
                    h_val = "-"
                try:
                    m_val = f"€{float(m_val):.2f}/mo"
                except (ValueError, TypeError):
                    m_val = "-"
                print(f"  {loc:<12} {h_val}  {m_val}")

        print(f"{self.console.horizontal_line('-')}")
