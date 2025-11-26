#!/usr/bin/env python3
# commands/pricing.py - Pricing-related commands for hicloud

from typing import List

class PricingCommands:
    """Pricing-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle pricing-related commands"""
        if not args:
            print("Missing pricing subcommand. Use 'pricing list [server|backup|loadbalancer|storage|network|all] [location]' or 'pricing calculate'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            category = args[1].lower() if len(args) > 1 else "all"
            location = args[2].lower() if len(args) > 2 else None
            self.list_pricing(category, location)
        elif subcommand == "calculate":
            self.calculate_costs()
        else:
            print(f"Unknown pricing subcommand: {subcommand}")
    
    def list_pricing(self, category: str = "all", location_filter: str = None):
        """Show pricing table for all resources or a specific category"""
        valid_categories = {"all", "server", "backup", "loadbalancer", "storage", "network"}
        if category not in valid_categories:
            print("Unknown pricing category. Use 'pricing list [server|backup|loadbalancer|storage|network|all] [location]'")
            return
        derived_used = False

        pricing = self.hetzner.get_pricing()
        if not pricing:
            print("Could not retrieve pricing information.")
            return

        def _price_value(value):
            """Normalize Hetzner price objects to float gross/net values."""
            if isinstance(value, dict):
                return float(value.get("gross") or value.get("net") or 0)
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        def _extract_price(entry):
            """Pull monthly/hourly/location from a price entry."""
            monthly = _price_value(entry.get("price_monthly", {}))
            hourly = _price_value(entry.get("price_hourly", {}))
            location = (entry.get("location", "-") or "-")

            derived = False
            if hourly == 0 and monthly:
                hourly = monthly / 730  # derive hourly if missing
                derived = True

            return monthly, hourly, location, derived

        print("\nHetzner Cloud Pricing:")

        # Server types table
        server_types = pricing.get("server_types", [])
        server_specs = {st.get("id"): st for st in self.hetzner.list_server_types()}
        if server_types and category in {"all", "server", "backup"}:
            server_rows = []
            backup_rows = []
            for st in sorted(server_types, key=lambda x: x.get("id", 0)):
                prices = st.get("prices", [])
                spec = server_specs.get(st.get("id"), {})
                cores = spec.get("cores", st.get("cores", "N/A"))
                memory = spec.get("memory", st.get("memory", "N/A"))
                disk = spec.get("disk", st.get("disk", "N/A"))

                for price_entry in prices:
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    server_rows.append([
                        st.get("name", "N/A"),
                        price_entry.get("location", location) or "-",
                        cores,
                        memory,
                        disk,
                        f"{hourly:.4f}{' *' if derived else ''}",
                        f"{monthly:.2f}"
                    ])

                    backup_rows.append([
                        st.get("name", "N/A"),
                        price_entry.get("location", location) or "-",
                        f"{(hourly if not derived else monthly / 730) * 0.2:.4f}",
                        f"{monthly * 0.2:.2f}"
                    ])

            server_rows.sort(key=lambda row: (row[0], row[1]))
            if category in {"all", "server"}:
                headers = ["Type", "Location", "Cores", "Memory (GB)", "Disk (GB)", "Hourly (€)", "Monthly (€)"]
                self.console.print_table(headers, server_rows, "Server Types")

            if backup_rows and category in {"all", "backup"}:
                backup_rows.sort(key=lambda row: (row[0], row[1]))
                backup_headers = ["Type", "Location", "Backup Hourly (€)", "Backup Monthly (€)"]
                self.console.print_table(backup_headers, backup_rows, "Backups (20% of server price)")

        # Load balancer types table
        lb_types = pricing.get("load_balancer_types", [])
        if lb_types and category in {"all", "loadbalancer"}:
            lb_rows = []
            for lb in sorted(lb_types, key=lambda x: x.get("id", 0)):
                for price_entry in lb.get("prices", []):
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    lb_rows.append([
                        lb.get("name", "N/A"),
                        price_entry.get("location", location) or "-",
                        f"{hourly:.4f}{' *' if derived else ''}",
                        f"{monthly:.2f}",
                    ])

            lb_rows.sort(key=lambda row: (row[0], row[-1]))
            headers = ["Type", "Location", "Hourly (€)", "Monthly (€)"]
            self.console.print_table(headers, lb_rows, "Load Balancer Types")

        # Other recurring resources (volume + floating IP) table
        other_rows = []

        volume = pricing.get("volume", {})
        if volume:
            prices = volume.get("prices", [])
            if prices:
                for price_entry in prices:
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    other_rows.append(["Volume", f"per GB ({price_entry.get('location','-')})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])
            else:
                monthly = _price_value(volume.get("price_per_gb_month", volume.get("price_monthly", {})))
                hourly = _price_value(volume.get("price_per_gb_hour", volume.get("price_hourly", {})))
                derived = hourly == 0 and monthly
                if derived:
                    hourly = monthly / 730
                    derived_used = True
                loc_label = location_filter if location_filter else "-"
                other_rows.append(["Volume", f"per GB ({loc_label})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])

        snapshot_pricing = pricing.get("snapshot", pricing.get("snapshots", {}))
        if snapshot_pricing:
            prices = snapshot_pricing.get("prices", [])
            if prices:
                for price_entry in prices:
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    other_rows.append(["Snapshot", f"per GB ({price_entry.get('location','-')})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])
            else:
                monthly = _price_value(snapshot_pricing.get("price_per_gb_month", snapshot_pricing.get("price_monthly", {})))
                hourly = _price_value(snapshot_pricing.get("price_per_gb_hour", snapshot_pricing.get("price_hourly", {})))
                derived = hourly == 0 and monthly
                if derived:
                    hourly = monthly / 730
                    derived_used = True
                loc_label = location_filter if location_filter else "-"
                other_rows.append(["Snapshot", f"per GB ({loc_label})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])

        traffic_pricing = pricing.get("traffic", {})
        if traffic_pricing:
            prices = traffic_pricing.get("prices", [])
            if prices:
                for price_entry in prices:
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    unit = price_entry.get("unit", "per TB")
                    other_rows.append(["Traffic", f"{unit} ({price_entry.get('location','-')})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])
            else:
                monthly = _price_value(traffic_pricing.get("price_per_tb_month", traffic_pricing.get("price_monthly", {})))
                hourly = _price_value(traffic_pricing.get("price_per_tb_hour", traffic_pricing.get("price_hourly", {})))
                derived = hourly == 0 and monthly
                if derived:
                    hourly = monthly / 730
                    derived_used = True
                loc_label = location_filter if location_filter else "-"
                other_rows.append(["Traffic", f"per TB ({loc_label})", f"{monthly:.4f}", f"{hourly:.6f}{' *' if derived else ''}"])

        floating_ip = pricing.get("floating_ip", {})
        if floating_ip:
            prices = floating_ip.get("prices", [])
            if prices:
                for price_entry in prices:
                    monthly, hourly, location, derived = _extract_price(price_entry)
                    if location_filter and location_filter != location.lower():
                        continue
                    if derived:
                        derived_used = True
                    other_rows.append(["Floating IP", f"per IP ({price_entry.get('location','-')})", f"{monthly:.2f}", f"{hourly:.6f}{' *' if derived else ''}"])
            else:
                monthly = _price_value(floating_ip.get("price_monthly", {}))
                hourly = _price_value(floating_ip.get("price_hourly", {}))
                derived = hourly == 0 and monthly
                if derived:
                    hourly = monthly / 730
                    derived_used = True
                loc_label = location_filter if location_filter else "-"
                other_rows.append(["Floating IP", f"per IP ({loc_label})", f"{monthly:.2f}", f"{hourly:.6f}{' *' if derived else ''}"])

        if other_rows and category in {"all", "storage", "network"}:
            # Split storage vs network display
            storage_rows = [row for row in other_rows if row[0] in {"Volume", "Snapshot"}]
            network_rows = [row for row in other_rows if row[0] in {"Floating IP", "Traffic"}]

            if category in {"all", "storage"} and storage_rows:
                storage_rows.sort(key=lambda row: (row[0], row[1]))
                # Swap order: Hourly before Monthly
                swapped_storage_rows = []
                for res, unit, monthly, hourly in storage_rows:
                    swapped_storage_rows.append([res, unit, hourly, monthly])
                headers = ["Resource", "Unit", "Hourly (€)", "Monthly (€)"]
                self.console.print_table(headers, swapped_storage_rows, "Storage")

            if category in {"all", "network"} and network_rows:
                network_rows.sort(key=lambda row: (row[0], row[1]))
                swapped_network_rows = []
                for res, unit, monthly, hourly in network_rows:
                    swapped_network_rows.append([res, unit, hourly, monthly])
                headers = ["Resource", "Unit", "Hourly (€)", "Monthly (€)"]
                self.console.print_table(headers, swapped_network_rows, "Network")

        if derived_used:
            print("\n* Hourly derived from monthly/730 (API does not provide hourly for this item)")
    
    def calculate_costs(self):
        """Calculate estimated monthly costs for current resources"""
        print("\nCalculating project costs...")
        costs = self.hetzner.calculate_project_costs()
        
        if not costs:
            print("Could not calculate project costs.")
            return
            
        print(f"\nEstimated Monthly Costs for Project '{self.hetzner.project_name}':")
        print(self.console.horizontal_line("="))
        
        print(f"\n{'Resource Type':<20} {'Count':<10} {'Cost'}")
        print("-" * 45)
        
        # Einzelne Ressourcentypen anzeigen
        for resource, data in costs.items():
            if resource != "total":  # "total" separat behandeln
                count = data.get("count", 0)
                try:
                    # Stelle sicher, dass cost ein float ist
                    cost = float(data.get("cost", 0))
                    print(f"{resource.capitalize():<20} {count:<10} {cost:>8.2f} €")
                except (ValueError, TypeError):
                    print(f"{resource.capitalize():<20} {count:<10} {'N/A':>8}")
        
        print("-" * 45)
        
        # Gesamtkosten anzeigen
        try:
            total = float(costs.get("total", 0))
            print(f"{'Total':<20} {'':<10} {total:>8.2f} €")
            
            # Jährliche Kosten und Durchschnitt pro Tag
            yearly = total * 12
            daily = total / 30
            
            print(f"\nYearly cost:  {yearly:.2f} €")
            print(f"Daily average: {daily:.2f} €")
        except (ValueError, TypeError) as e:
            if self.console.debug:
                print(f"Warning: Total cost calculation error: {e}")
            print(f"{'Total':<20} {'':<10} {'N/A':>8}")
