#!/usr/bin/env python3
# commands/location.py - Location and Datacenter commands for hicloud

from typing import List

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

        print("\nAvailable Locations:")
        print(f"{'ID':<10} {'Name':<15} {'City':<20} {'Country':<15} {'Network Zone':<15}")
        print("-" * 75)

        # Sort locations by name
        for location in sorted(locations, key=lambda x: x.get('name', '')):
            loc_id = location.get('id', 'N/A')
            name = location.get('name', 'N/A')
            city = location.get('city', 'N/A')
            country = location.get('country', 'N/A')
            network_zone = location.get('network_zone', 'N/A')

            print(f"{loc_id:<10} {name:<15} {city:<20} {country:<15} {network_zone:<15}")

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
        else:
            print(f"Unknown datacenter subcommand: {subcommand}")

    def list_datacenters(self):
        """List all available datacenters"""
        datacenters = self.hetzner.list_datacenters()

        if not datacenters:
            print("No datacenters found")
            return

        print("\nAvailable Datacenters:")
        print(f"{'ID':<10} {'Name':<20} {'Description':<40} {'Location':<15}")
        print("-" * 85)

        # Sort datacenters by name
        for dc in sorted(datacenters, key=lambda x: x.get('name', '')):
            dc_id = dc.get('id', 'N/A')
            name = dc.get('name', 'N/A')
            description = dc.get('description', 'N/A')
            location_name = dc.get('location', {}).get('name', 'N/A')

            # Truncate description if too long
            if len(description) > 40:
                description = description[:37] + "..."

            print(f"{dc_id:<10} {name:<20} {description:<40} {location_name:<15}")

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
