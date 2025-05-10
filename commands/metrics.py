#!/usr/bin/env python3
# commands/metrics.py - Metrics-related commands for hicloud

from typing import List

class MetricsCommands:
    """Metrics-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle metrics-related commands"""
        if not args:
            print("Missing metrics subcommand. Use 'metrics list|cpu|traffic'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_metrics(args[1:])
        elif subcommand == "cpu":
            self.show_cpu_metrics(args[1:])
        elif subcommand == "traffic":
            self.show_traffic_metrics(args[1:])
        else:
            print(f"Unknown metrics subcommand: {subcommand}")
    
    def list_metrics(self, args: List[str]):
        """Show available metrics for a server"""
        if not args:
            print("Missing server ID. Use 'metrics list <id>'")
            return
            
        try:
            server_id = int(args[0])
        except ValueError:
            print("Invalid server ID. Must be an integer.")
            return
            
        # Überprüfe, ob der Server existiert
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            print(f"Server with ID {server_id} not found")
            return
            
        metrics = self.hetzner.get_available_metrics(server_id)
        print(f"\nAvailable metrics for server '{server.get('name')}' (ID: {server_id}):")
        print("-" * 60)
        
        for metric in metrics:
            if metric == "cpu":
                print(f"cpu      - CPU utilization over time")
            elif metric == "disk":
                print(f"disk     - Disk read/write operations")
            elif metric == "network":
                print(f"traffic  - Network traffic (in/out)")
                
        print("\nUse 'metrics <type> <id>' to view specific metrics.")
    
    def show_cpu_metrics(self, args: List[str]):
        """Show CPU metrics for a server"""
        if not args:
            print("Missing server ID. Use 'metrics cpu <id> [--hours=24]'")
            return
            
        try:
            server_id = int(args[0])
        except ValueError:
            print("Invalid server ID. Must be an integer.")
            return
            
        # Parse options
        hours = 24  # Default
        for arg in args[1:]:
            if arg.startswith("--hours="):
                try:
                    hours = int(arg.split("=")[1])
                except (ValueError, IndexError):
                    print("Invalid hours value. Must be an integer.")
                    return
        
        # Überprüfe, ob der Server existiert
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            print(f"Server with ID {server_id} not found")
            return
            
        print(f"\nCPU metrics for server '{server.get('name')}' (ID: {server_id}) over the last {hours} hours:")
        print("-" * 80)
        
        metrics = self.hetzner.get_cpu_metrics(server_id, hours)
        if not metrics:
            print("No CPU metrics available for this server.")
            return
            
        # Metriken auswerten und anzeigen
        try:
            # Zeitpunkte und CPU-Werte extrahieren
            timestamps = metrics.get("time_series", {}).get("values", [])
            cpu_values = metrics.get("time_series", {}).get("values", [])
            
            if not timestamps or not cpu_values:
                print("No CPU metrics data available.")
                return
                
            # Einfache ASCII-Grafik erstellen
            print("\nCPU Utilization (%):")
            print("  0%  10%  20%  30%  40%  50%  60%  70%  80%  90% 100%")
            print("  |    |    |    |    |    |    |    |    |    |    |")
            
            # Berechne Durchschnitt, Min und Max
            cpu_values_float = []
            for value in cpu_values:
                try:
                    if value is not None:
                        cpu_values_float.append(float(value))
                except (ValueError, TypeError):
                    pass
                    
            if cpu_values_float:
                avg_cpu = sum(cpu_values_float) / len(cpu_values_float)
                max_cpu = max(cpu_values_float)
                min_cpu = min(cpu_values_float)
                
                # ASCII-Balken für Durchschnitt
                bar_length = int(avg_cpu / 100 * 51)  # 51 Zeichen für 0-100%
                bar = "=" * bar_length
                print(f"  {bar}> {avg_cpu:.1f}% (avg)")
                
                # Min/Max-Werte anzeigen
                print(f"\nMin: {min_cpu:.1f}%, Max: {max_cpu:.1f}%")
            else:
                print("  No data available")
                
        except Exception as e:
            print(f"Error processing CPU metrics: {str(e)}")
    
    def show_traffic_metrics(self, args: List[str]):
        """Show network traffic metrics for a server"""
        if not args:
            print("Missing server ID. Use 'metrics traffic <id> [--days=7]'")
            return
            
        try:
            server_id = int(args[0])
        except ValueError:
            print("Invalid server ID. Must be an integer.")
            return
            
        # Parse options
        days = 7  # Default
        for arg in args[1:]:
            if arg.startswith("--days="):
                try:
                    days = int(arg.split("=")[1])
                except (ValueError, IndexError):
                    print("Invalid days value. Must be an integer.")
                    return
        
        # Überprüfe, ob der Server existiert
        server = self.hetzner.get_server_by_id(server_id)
        if not server:
            print(f"Server with ID {server_id} not found")
            return
            
        print(f"\nNetwork traffic for server '{server.get('name')}' (ID: {server_id}) over the last {days} days:")
        print("-" * 80)
        
        metrics = self.hetzner.get_network_metrics(server_id, days)
        if not metrics:
            print("No network metrics available for this server.")
            return
            
        # Metriken auswerten und anzeigen
        try:
            # Netzwerkdaten extrahieren
            timestamps = metrics.get("time_series", {}).get("values", [])
            network_rx = metrics.get("metrics", {}).get("network", {}).get("pps", {}).get("rx", {}).get("values", [])
            network_tx = metrics.get("metrics", {}).get("network", {}).get("pps", {}).get("tx", {}).get("values", [])
            
            if not timestamps or not network_rx or not network_tx:
                print("No network metrics data available.")
                return
                
            # Berechne Gesamttraffic
            rx_values = [float(v) if v is not None else 0 for v in network_rx]
            tx_values = [float(v) if v is not None else 0 for v in network_tx]
            
            total_rx = sum(rx_values)
            total_tx = sum(tx_values)
            
            # In MB/GB umrechnen
            if total_rx > 1024*1024:
                rx_str = f"{total_rx/(1024*1024):.2f} GB"
            else:
                rx_str = f"{total_rx/1024:.2f} MB"
                
            if total_tx > 1024*1024:
                tx_str = f"{total_tx/(1024*1024):.2f} GB"
            else:
                tx_str = f"{total_tx/1024:.2f} MB"
                
            print(f"Total received: {rx_str}")
            print(f"Total sent:     {tx_str}")
            
            # Durchschnittliche Paket-Rate berechnen
            avg_rx_pps = sum(rx_values) / len(rx_values)
            avg_tx_pps = sum(tx_values) / len(tx_values)
            
            print(f"\nAverage packet rate:")
            print(f"Received: {avg_rx_pps:.1f} pps")
            print(f"Sent:     {avg_tx_pps:.1f} pps")
            
        except Exception as e:
            print(f"Error processing network metrics: {str(e)}")
