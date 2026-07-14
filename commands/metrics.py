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
            print("Missing metrics subcommand. Use 'metrics list|cpu|traffic|disk'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_metrics(args[1:])
        elif subcommand == "cpu":
            self.show_cpu_metrics(args[1:])
        elif subcommand == "traffic":
            self.show_traffic_metrics(args[1:])
        elif subcommand == "disk":
            self.show_disk_metrics(args[1:])
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

        # Hetzner liefert [timestamp, "wert"]-Paare pro Serie
        cpu_values = self._series_values(metrics, "cpu")
        if not cpu_values:
            print("No CPU metrics data available.")
            return

        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        min_cpu = min(cpu_values)

        # Einfache ASCII-Grafik erstellen
        print("\nCPU Utilization (%):")
        print("  0%  10%  20%  30%  40%  50%  60%  70%  80%  90% 100%")
        print("  |    |    |    |    |    |    |    |    |    |    |")

        # ASCII-Balken für Durchschnitt (>100% möglich bei mehreren Cores, daher kappen)
        bar_length = min(int(avg_cpu / 100 * 51), 51)
        bar = "=" * bar_length
        print(f"  {bar}> {avg_cpu:.1f}% (avg)")

        print(f"\nMin: {min_cpu:.1f}%, Max: {max_cpu:.1f}%")
    
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

        step = float(metrics.get("step") or 0)
        bw_in = self._series_values(metrics, "network.0.bandwidth.in")
        bw_out = self._series_values(metrics, "network.0.bandwidth.out")
        pps_in = self._series_values(metrics, "network.0.pps.in")
        pps_out = self._series_values(metrics, "network.0.pps.out")

        if not (bw_in or bw_out or pps_in or pps_out):
            print("No network metrics data available.")
            return

        if bw_in or bw_out:
            # Bandwidth-Samples sind Bytes/s; Gesamtvolumen = Summe * Schrittweite
            print(f"Total received: {self._format_bytes(sum(bw_in) * step)}")
            print(f"Total sent:     {self._format_bytes(sum(bw_out) * step)}")
            if bw_in:
                print(f"\nAverage bandwidth in:  {self._format_bytes(sum(bw_in) / len(bw_in))}/s")
            if bw_out:
                print(f"Average bandwidth out: {self._format_bytes(sum(bw_out) / len(bw_out))}/s")

        if pps_in or pps_out:
            print("\nAverage packet rate:")
            if pps_in:
                print(f"Received: {sum(pps_in) / len(pps_in):.1f} pps")
            if pps_out:
                print(f"Sent:     {sum(pps_out) / len(pps_out):.1f} pps")

    def show_disk_metrics(self, args: List[str]):
        """Show disk I/O metrics for a server"""
        if not args:
            print("Missing server ID. Use 'metrics disk <id> [--days=1]'")
            return

        try:
            server_id = int(args[0])
        except ValueError:
            print("Invalid server ID. Must be an integer.")
            return

        # Parse options
        days = 1  # Default
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

        print(f"\nDisk I/O metrics for server '{server.get('name')}' (ID: {server_id}) over the last {days} day(s):")
        print("-" * 80)

        metrics = self.hetzner.get_disk_metrics(server_id, days)
        if not metrics:
            print("No disk metrics available for this server.")
            return

        step = float(metrics.get("step") or 0)
        read_bw = self._series_values(metrics, "disk.0.bandwidth.read")
        write_bw = self._series_values(metrics, "disk.0.bandwidth.write")
        read_iops = self._series_values(metrics, "disk.0.iops.read")
        write_iops = self._series_values(metrics, "disk.0.iops.write")

        if not (read_bw or write_bw or read_iops or write_iops):
            print("No disk metrics data available.")
            return

        if read_bw or write_bw:
            # Bandwidth-Samples sind Bytes/s; Gesamtvolumen = Summe * Schrittweite
            print("Disk Bandwidth:")
            print(f"  Total read:  {self._format_bytes(sum(read_bw) * step)}")
            print(f"  Total write: {self._format_bytes(sum(write_bw) * step)}")
            if read_bw:
                print(f"\n  Avg read:  {self._format_bytes(sum(read_bw) / len(read_bw))}/s")
            if write_bw:
                print(f"  Avg write: {self._format_bytes(sum(write_bw) / len(write_bw))}/s")

        if read_iops or write_iops:
            print("\nDisk IOPS (Operations per second):")
            if read_iops:
                print(f"  Avg read:  {sum(read_iops) / len(read_iops):.1f} IOPS")
            if write_iops:
                print(f"  Avg write: {sum(write_iops) / len(write_iops):.1f} IOPS")
            if read_iops:
                print(f"\n  Max read:  {max(read_iops):.1f} IOPS")
            if write_iops:
                print(f"  Max write: {max(write_iops):.1f} IOPS")

    def _series_values(self, metrics: dict, series_name: str) -> List[float]:
        """
        Extract numeric values from a Hetzner metrics time series.

        The API returns metrics as {"time_series": {"<name>": {"values":
        [[timestamp, "value"], ...]}}} with values encoded as strings.
        """
        raw = metrics.get("time_series", {}).get(series_name, {}).get("values", [])
        values = []
        for entry in raw:
            try:
                values.append(float(entry[1]))
            except (TypeError, ValueError, IndexError):
                continue
        return values

    @staticmethod
    def _format_bytes(value: float) -> str:
        """Format a byte count with a human-readable unit."""
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024
        return f"{value:.2f} TB"
