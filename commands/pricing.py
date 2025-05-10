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
            print("Missing pricing subcommand. Use 'pricing list|calculate'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_pricing()
        elif subcommand == "calculate":
            self.calculate_costs()
        else:
            print(f"Unknown pricing subcommand: {subcommand}")
    
    def list_pricing(self):
        """Show pricing table for all resources"""
        pricing = self.hetzner.get_pricing()
        if not pricing:
            print("Could not retrieve pricing information.")
            return
            
        print("\nHetzner Cloud Pricing Table:")
        print(self.console.horizontal_line("="))
        
        # Server-Preise anzeigen
        server_types = pricing.get("server_types", [])
        if server_types:
            print("\nServer Types:")
            print(f"{'Type':<10} {'Cores':<6} {'Memory':<8} {'Disk':<8} {'Monthly':<10} {'Hourly'}")
            print("-" * 60)
            
            # Nach Gruppen sortieren
            server_groups = {}
            for st in server_types:
                name = st.get("name", "").upper()
                # Gruppieren nach Präfix (CX, CPX, CCX, CAX)
                prefix = ''.join([c for c in name if c.isalpha()])
                if prefix not in server_groups:
                    server_groups[prefix] = []
                server_groups[prefix].append(st)
            
            # Nach Gruppen anzeigen
            for prefix in sorted(server_groups.keys()):
                group = server_groups[prefix]
                # Innerhalb der Gruppe nach Speicher sortieren
                group.sort(key=lambda x: x.get("memory", 0))
                
                for st in group:
                    name = st.get("name", "N/A")
                    cores = st.get("cores", "N/A")
                    memory = f"{st.get('memory', 0)} GB"
                    disk = f"{st.get('disk', 0)} GB"
                    
                    # Preise extrahieren und sicherstellen, dass es sich um Zahlen handelt
                    try:
                        prices = st.get("prices", [{}])[0]
                        # Stelle sicher, dass monthly ein float ist
                        price_monthly_obj = prices.get("price_monthly", {})
                        if isinstance(price_monthly_obj, dict):
                            monthly = float(price_monthly_obj.get("gross", 0))
                        else:
                            monthly = float(price_monthly_obj) if price_monthly_obj else 0.0
                        
                        # Stelle sicher, dass hourly ein float ist
                        price_hourly_obj = prices.get("price_hourly", {})
                        if isinstance(price_hourly_obj, dict):
                            hourly = float(price_hourly_obj.get("gross", 0))
                        else:
                            hourly = float(price_hourly_obj) if price_hourly_obj else 0.0
                        
                        print(f"{name:<10} {cores:<6} {memory:<8} {disk:<8} {monthly:>8.2f} € {hourly:>6.4f} €")
                    except (ValueError, TypeError) as e:
                        if self.console.debug:
                            print(f"Warning: Price formatting error for {name}: {e}")
                        print(f"{name:<10} {cores:<6} {memory:<8} {disk:<8} {'N/A':>8} {'N/A':>11}")
                
                # Leerzeile zwischen Gruppen
                print()
                
        # Volume-Preise anzeigen
        volume = pricing.get("volume", {})
        if volume:
            print("\nVolumes:")
            try:
                prices = volume.get("prices", [{}])[0]
                
                # Stelle sicher, dass es sich um Zahlen handelt
                price_monthly_obj = prices.get("price_monthly", {})
                if isinstance(price_monthly_obj, dict):
                    monthly_per_gb = float(price_monthly_obj.get("gross", 0))
                else:
                    monthly_per_gb = float(price_monthly_obj) if price_monthly_obj else 0.0
                
                price_hourly_obj = prices.get("price_hourly", {})
                if isinstance(price_hourly_obj, dict):
                    hourly_per_gb = float(price_hourly_obj.get("gross", 0))
                else:
                    hourly_per_gb = float(price_hourly_obj) if price_hourly_obj else 0.0
                
                print(f"Per GB: {monthly_per_gb:.2f} €/month ({hourly_per_gb:.6f} €/hour)")
                
                # Beispiele für verschiedene Größen
                print("\nExamples:")
                for size in [10, 50, 100, 250, 500, 1000]:
                    print(f"{size} GB: {size * monthly_per_gb:.2f} €/month")
            except (ValueError, TypeError) as e:
                if self.console.debug:
                    print(f"Warning: Volume price formatting error: {e}")
                print("Price information not available")
                
        # Floating IP-Preise anzeigen
        floating_ip = pricing.get("floating_ip", {})
        if floating_ip:
            print("\nFloating IPs:")
            try:
                prices = floating_ip.get("prices", [{}])[0]
                
                # Stelle sicher, dass es sich um Zahlen handelt
                price_monthly_obj = prices.get("price_monthly", {})
                if isinstance(price_monthly_obj, dict):
                    monthly = float(price_monthly_obj.get("gross", 0))
                else:
                    monthly = float(price_monthly_obj) if price_monthly_obj else 0.0
                
                price_hourly_obj = prices.get("price_hourly", {})
                if isinstance(price_hourly_obj, dict):
                    hourly = float(price_hourly_obj.get("gross", 0))
                else:
                    hourly = float(price_hourly_obj) if price_hourly_obj else 0.0
                
                print(f"Per IP: {monthly:.2f} €/month ({hourly:.6f} €/hour)")
            except (ValueError, TypeError) as e:
                if self.console.debug:
                    print(f"Warning: Floating IP price formatting error: {e}")
                print("Price information not available")
            
        # Load Balancer-Preise anzeigen
        lb_types = pricing.get("load_balancer_types", [])
        if lb_types:
            print("\nLoad Balancer Types:")
            print(f"{'Type':<10} {'Monthly':<10} {'Hourly'}")
            print("-" * 35)
            
            for lb in lb_types:
                name = lb.get("name", "N/A")
                try:
                    prices = lb.get("prices", [{}])[0]
                    
                    # Stelle sicher, dass es sich um Zahlen handelt
                    price_monthly_obj = prices.get("price_monthly", {})
                    if isinstance(price_monthly_obj, dict):
                        monthly = float(price_monthly_obj.get("gross", 0))
                    else:
                        monthly = float(price_monthly_obj) if price_monthly_obj else 0.0
                    
                    price_hourly_obj = prices.get("price_hourly", {})
                    if isinstance(price_hourly_obj, dict):
                        hourly = float(price_hourly_obj.get("gross", 0))
                    else:
                        hourly = float(price_hourly_obj) if price_hourly_obj else 0.0
                    
                    print(f"{name:<10} {monthly:>8.2f} € {hourly:>6.6f} €")
                except (ValueError, TypeError) as e:
                    if self.console.debug:
                        print(f"Warning: Load balancer price formatting error for {name}: {e}")
                    print(f"{name:<10} {'N/A':>8} {'N/A':>11}")
    
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
