#!/usr/bin/env python3
# lib/api.py - Hetzner Cloud API Manager

import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from utils.constants import API_BASE_URL


class HetznerCloudManager:
    """Manages interactions with Hetzner Cloud API"""
    
    def __init__(self, api_token: str, project_name: str = "default", debug: bool = False):
        self.api_token = api_token
        self.project_name = project_name
        self.debug = debug
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Tuple[int, Dict]:
        """Make an API request to Hetzner Cloud"""
        url = f"{API_BASE_URL}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return 400, {"error": f"Unsupported method: {method}"}
                
            if response.status_code in [200, 201, 202, 204]:
                try:
                    if response.status_code == 204 or not response.text:
                        return response.status_code, {}
                    return response.status_code, response.json()
                except json.JSONDecodeError:
                    return response.status_code, {}
            else:
                error_msg = f"API request failed: {response.text}"
                
                if self.debug:
                    print(error_msg)
                    
                try:
                    return response.status_code, response.json()
                except json.JSONDecodeError:
                    return response.status_code, {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            if self.debug:
                print(error_msg)
            return 500, {"error": error_msg}
    
    # Metrics Management Functions
    def get_server_metrics(self, server_id: int, type: str, start: str, end: str, step: Optional[str] = None) -> Dict:
        """
        Gets metrics for a server
        
        type: Must be one of 'cpu', 'disk', 'network'
        start: ISO 8601 date string for start time
        end: ISO 8601 date string for end time
        step: Optional step size in seconds (e.g. '60' for minute intervals)
        """
        params = {
            "type": type,
            "start": start,
            "end": end
        }
        
        if step:
            params["step"] = step
            
        endpoint = f"servers/{server_id}/metrics"
        
        # API erfordert GET-Parameter
        query_params = "&".join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"{endpoint}?{query_params}"
        
        status_code, response = self._make_request("GET", endpoint)
        
        if status_code != 200:
            print(f"Error getting metrics: {response.get('error', 'Unknown error')}")
            return {}
            
        return response.get("metrics", {})
    
    def get_cpu_metrics(self, server_id: int, hours: int = 24) -> Dict:
        """Gets CPU metrics for a server for the specified number of hours"""
        # Berechne Start- und Endzeitpunkt basierend auf Stunden
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # Für längere Zeiträume größere Schritte verwenden
        step = "60" if hours <= 6 else "300" if hours <= 48 else "3600"
        
        return self.get_server_metrics(server_id, "cpu", start_time, end_time, step)
    
    def get_network_metrics(self, server_id: int, days: int = 7) -> Dict:
        """Gets network metrics for a server for the specified number of days"""
        # Berechne Start- und Endzeitpunkt basierend auf Tagen
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Für längere Zeiträume größere Schritte verwenden
        step = "300" if days <= 1 else "3600" if days <= 7 else "86400"
        
        return self.get_server_metrics(server_id, "network", start_time, end_time, step)
    
    def get_disk_metrics(self, server_id: int, days: int = 1) -> Dict:
        """Gets disk metrics for a server for the specified number of days"""
        # Berechne Start- und Endzeitpunkt basierend auf Tagen
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Feste Schrittweite für Festplattenmetriken
        step = "60"
        
        return self.get_server_metrics(server_id, "disk", start_time, end_time, step)
    
    def get_available_metrics(self, server_id: int) -> List[str]:
        """Returns a list of available metric types for a server"""
        # API bietet keine direkte Möglichkeit, verfügbare Metriken abzurufen
        # Daher geben wir die unterstützten Typen zurück
        return ["cpu", "disk", "network"]
    
    # Pricing Functions
    def get_pricing(self) -> Dict:
        """Gets the current pricing information"""
        status_code, response = self._make_request("GET", "pricing")
        
        if status_code != 200:
            print(f"Error getting pricing information: {response.get('error', 'Unknown error')}")
            return {}
            
        return response.get("pricing", {})
    
    def calculate_project_costs(self) -> Dict:
        """Calculates the estimated monthly costs for all resources in the project"""
        # Preisdaten abrufen
        pricing = self.get_pricing()
        if not pricing:
            return {}
            
        result = {
            "servers": {"count": 0, "cost": 0.0},
            "volumes": {"count": 0, "cost": 0.0},
            "floating_ips": {"count": 0, "cost": 0.0},
            "load_balancers": {"count": 0, "cost": 0.0},
            "total": 0.0
        }
        
        # Server-Kosten berechnen
        servers = self.list_servers()
        server_prices = pricing.get("server_types", [])
        
        # Server-Preise nach ID indizieren
        server_price_map = {}
        for price_info in server_prices:
            try:
                server_id = price_info.get("id")
                price_data = price_info.get("prices", [{}])[0].get("price_monthly", {})
                
                if isinstance(price_data, dict):
                    price = float(price_data.get("gross", 0))
                else:
                    price = float(price_data) if price_data else 0.0
                    
                server_price_map[server_id] = price
            except (ValueError, TypeError) as e:
                if self.debug:
                    print(f"Warning: Error parsing server price data: {e}")
        
        for server in servers:
            server_type_id = server.get("server_type", {}).get("id")
            if server_type_id in server_price_map:
                result["servers"]["count"] += 1
                monthly_price = server_price_map[server_type_id]
                result["servers"]["cost"] += monthly_price
        
        # Volumes Kosten berechnen
        try:
            status_code, volumes_response = self._make_request("GET", "volumes")
            if status_code == 200:
                volumes = volumes_response.get("volumes", [])
                
                price_data = pricing.get("volume", {}).get("prices", [{}])[0].get("price_monthly", {})
                if isinstance(price_data, dict):
                    volume_price_per_gb = float(price_data.get("gross", 0))
                else:
                    volume_price_per_gb = float(price_data) if price_data else 0.0
                
                for volume in volumes:
                    result["volumes"]["count"] += 1
                    size_gb = float(volume.get("size", 0))
                    result["volumes"]["cost"] += size_gb * volume_price_per_gb
        except Exception as e:
            if self.debug:
                print(f"Warning: Error calculating volume costs: {e}")
        
        # Floating IPs berechnen
        try:
            status_code, ips_response = self._make_request("GET", "floating_ips")
            if status_code == 200:
                ips = ips_response.get("floating_ips", [])
                
                price_data = pricing.get("floating_ip", {}).get("prices", [{}])[0].get("price_monthly", {})
                if isinstance(price_data, dict):
                    ip_price = float(price_data.get("gross", 0))
                else:
                    ip_price = float(price_data) if price_data else 0.0
                
                result["floating_ips"]["count"] = len(ips)
                result["floating_ips"]["cost"] = len(ips) * ip_price
        except Exception as e:
            if self.debug:
                print(f"Warning: Error calculating floating IP costs: {e}")
        
        # Load Balancer berechnen
        try:
            status_code, lb_response = self._make_request("GET", "load_balancers")
            if status_code == 200:
                lbs = lb_response.get("load_balancers", [])
                lb_types = pricing.get("load_balancer_types", [])
                
                # LB-Preise nach ID indizieren
                lb_price_map = {}
                for lb_type in lb_types:
                    try:
                        lb_id = lb_type.get("id")
                        price_data = lb_type.get("prices", [{}])[0].get("price_monthly", {})
                        
                        if isinstance(price_data, dict):
                            price = float(price_data.get("gross", 0))
                        else:
                            price = float(price_data) if price_data else 0.0
                            
                        lb_price_map[lb_id] = price
                    except (ValueError, TypeError) as e:
                        if self.debug:
                            print(f"Warning: Error parsing load balancer price data: {e}")
                
                for lb in lbs:
                    result["load_balancers"]["count"] += 1
                    lb_type_id = lb.get("load_balancer_type", {}).get("id")
                    if lb_type_id in lb_price_map:
                        result["load_balancers"]["cost"] += lb_price_map[lb_type_id]
        except Exception as e:
            if self.debug:
                print(f"Warning: Error calculating load balancer costs: {e}")
        
        # Gesamtkosten berechnen
        result["total"] = (
            result["servers"]["cost"] +
            result["volumes"]["cost"] +
            result["floating_ips"]["cost"] +
            result["load_balancers"]["cost"]
        )
        
        return result
    
    def rebuild_server_from_snapshot(self, server_id: int, snapshot_id: int) -> bool:
        """Rebuild a server from a snapshot"""
        data = {
            "image": str(snapshot_id)
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/rebuild", data
        )
        
        if status_code != 201:
            print(f"Error rebuilding server: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server rebuild to complete...")
            return self._wait_for_action(action_id)
            
        return True
    
    # SSH Key Management Functions
    def list_ssh_keys(self) -> List[Dict]:
        """List all SSH keys in the project"""
        status_code, response = self._make_request("GET", "ssh_keys")
        
        if status_code != 200:
            print(f"Error listing SSH keys: {response.get('error', 'Unknown error')}")
            return []
            
        return response.get("ssh_keys", [])
    
    def get_ssh_key_by_id(self, key_id: int) -> Dict:
        """Get SSH key by ID"""
        status_code, response = self._make_request("GET", f"ssh_keys/{key_id}")
        
        if status_code != 200:
            if not self.debug:
                # In user mode no technical details
                print(f"SSH key with ID {key_id} not found")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting SSH key: {error_message}")
            return {}
            
        return response.get("ssh_key", {})
    
    def delete_ssh_key(self, key_id: int) -> bool:
        """Delete an SSH key by ID"""
        status_code, response = self._make_request("DELETE", f"ssh_keys/{key_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                # In user mode no technical details
                print(f"Failed to delete SSH key {key_id}")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting SSH key: {error_message}")
            return False

        return True

    def create_ssh_key(self, name: str, public_key: str, labels: Dict = None) -> Dict:
        """Create/upload a new SSH key"""
        data = {
            "name": name,
            "public_key": public_key
        }

        if labels:
            data["labels"] = labels

        status_code, response = self._make_request("POST", "ssh_keys", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to create SSH key '{name}'")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error creating SSH key: {error_message}")
            return {}

        return response.get("ssh_key", {})

    def update_ssh_key(self, key_id: int, name: str = None, labels: Dict = None) -> Dict:
        """Update SSH key metadata (name and/or labels)"""
        data = {}

        if name is not None:
            data["name"] = name

        if labels is not None:
            data["labels"] = labels

        if not data:
            print("No updates provided")
            return {}

        status_code, response = self._make_request("PUT", f"ssh_keys/{key_id}", data)

        if status_code != 200:
            if not self.debug:
                print(f"Failed to update SSH key {key_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error updating SSH key: {error_message}")
            return {}

        return response.get("ssh_key", {})

    # Backup Management Functions
    def list_backups(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all backups, optionally filtered by server ID"""
        status_code, response = self._make_request("GET", "images?type=backup")
        
        if status_code != 200:
            print(f"Error listing backups: {response.get('error', 'Unknown error')}")
            return []
        
        backups = response.get("images", [])
        
        # Filter by server ID if provided
        if server_id:
            return [b for b in backups if b.get("created_from", {}).get("id") == server_id]
        return backups
    
    def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup by ID"""
        status_code, response = self._make_request("DELETE", f"images/{backup_id}")
        
        if status_code not in [200, 204]:
            if not self.debug:
                # In user mode no technical details
                print(f"Failed to delete backup {backup_id}")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting backup: {error_message}")
            return False
            
        return True
    
    def enable_server_backups(self, server_id: int, backup_window: Optional[str] = None) -> bool:
        """Enable automated backups for a server"""
        data = {}
        if backup_window:
            data["backup_window"] = backup_window
            
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/enable_backup", data
        )
        
        if status_code != 201:
            print(f"Error enabling backups: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for backup enablement to complete...")
            return self._wait_for_action(action_id)
            
        return True
    
    def disable_server_backups(self, server_id: int) -> bool:
        """Disable automated backups for a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/disable_backup", {}
        )
        
        if status_code != 201:
            print(f"Error disabling backups: {response.get('error', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for backup disablement to complete...")
            return self._wait_for_action(action_id)
            
        return True
    
    # VM Management Functions

    def resize_server(self, server_id: int, server_type: str) -> bool:
        """Change the server type of a server"""
        data = {
            "server_type": server_type,
            "upgrade_disk": True  # Vergrößere auch die Festplatte, wenn möglich
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/change_type", data
        )
        
        if status_code != 201:
            print(f"Error resizing server: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for resize operation to complete...")
            return self._wait_for_action(action_id)
            
        return True

    def rename_server(self, server_id: int, name: str) -> bool:
        """Rename a server"""
        data = {
            "name": name
        }
        
        status_code, response = self._make_request(
            "PUT", f"servers/{server_id}", data
        )
        
        if status_code != 200:
            print(f"Error renaming server: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
            
        return True

    def enable_rescue_mode(self, server_id: int, rescue_type: str = "linux64") -> Dict:
        """
        Enable rescue mode for a server
        
        rescue_type can be one of:
        - linux64 (default)
        - linux32
        - freebsd64
        """
        data = {
            "type": rescue_type
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/enable_rescue", data
        )
        
        if status_code != 201:
            print(f"Error enabling rescue mode: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for rescue mode enablement to complete...")
            if not self._wait_for_action(action_id):
                return {}
                
        # Return the root password
        return {
            "root_password": response.get("root_password", "")
        }

    def reset_server_password(self, server_id: int) -> Dict:
        """Reset the root password of a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/reset_password", {}
        )
        
        if status_code != 201:
            print(f"Error resetting password: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for password reset to complete...")
            if not self._wait_for_action(action_id):
                return {}
                
        # Return the root password
        return {
            "root_password": response.get("root_password", "")
        }

    def reboot_server(self, server_id: int) -> bool:
        """Reboot a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/reboot", {}
        )
        
        if status_code != 201:
            print(f"Error rebooting server: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server to reboot...")
            return self._wait_for_action(action_id)
            
        return True

    def create_image(self, server_id: int, description: str = "") -> Dict:
        """Create a custom image from a server"""
        data = {
            "description": description,
            "type": "snapshot"  # Immer als Snapshot erstellen
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/create_image", data
        )
        
        if status_code != 201:
            print(f"Error creating image: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for image creation to complete...")
            if not self._wait_for_action(action_id):
                return {}
                
        # Return the image details
        return response.get("image", {})
    
    
    
    def list_servers(self) -> List[Dict]:
        """List all servers in the project"""
        status_code, response = self._make_request("GET", "servers")
        
        if status_code != 200:
            print(f"Error listing servers: {response.get('error', 'Unknown error')}")
            return []
            
        return response.get("servers", [])
    
    def create_server(self, name: str, server_type: str, image: str, 
                     location: str = "nbg1", ssh_keys: List[int] = None,
                     ipv4: bool = True, ipv6: bool = True, 
                     auto_password: bool = False) -> Dict:
        """Create a new server"""
        data = {
            "name": name,
            "server_type": server_type,
            "image": image,
            "location": location,
            "public_net": {
                "enable_ipv4": ipv4,
                "enable_ipv6": ipv6
            }
        }
        
        if ssh_keys:
            data["ssh_keys"] = ssh_keys
            
        # Die standard API-Verhaltensweise ist: Wenn kein root_password gesetzt ist,
        # wird keines generiert AUSSER wenn 'start_after_create' true ist oder nicht spezifiziert ist
        # Wir setzen dies explizit, um je nach Benutzerauswahl ein Passwort zu forcieren oder nicht
        if auto_password:
            data["start_after_create"] = True
        else:
            data["start_after_create"] = False
            
        status_code, response = self._make_request("POST", "servers", data)
        
        if status_code != 201:
            print(f"Error creating server: {response.get('error', 'Unknown error')}")
            return {}
            
        return response.get("server", {})
    
    def delete_server(self, server_id: int) -> bool:
        """Delete a server by ID"""
        status_code, response = self._make_request("DELETE", f"servers/{server_id}")
        
        if status_code not in [200, 204]:
            if not self.debug:
                # In user mode no technical details
                print(f"Failed to delete server {server_id}")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting server: {error_message}")
            return False
            
        return True
    
    def start_server(self, server_id: int) -> bool:
        """Start a server by ID"""
        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/poweron", {})
        
        if status_code != 201:
            if not self.debug:
                # In user mode no technical details
                print(f"Failed to start server {server_id}")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error starting server: {error_message}")
            return False
            
        # Wait for action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server to start...")
            return self._wait_for_action(action_id)
            
        return True
    
    def stop_server(self, server_id: int) -> bool:
        """Stop a server by ID"""
        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/shutdown", {})
        
        if status_code != 201:
            # Try poweroff if shutdown fails
            print("Trying graceful shutdown...")
            status_code, response = self._make_request("POST", f"servers/{server_id}/actions/poweroff", {})
            
            if status_code != 201:
                if not self.debug:
                    # In user mode no technical details
                    print(f"Failed to stop server {server_id}")
                else:
                    # In debug mode show technical error
                    error_message = response.get('error', {}).get('message', 'Unknown error')
                    print(f"Error stopping server: {error_message}")
                return False
        
        # Wait for action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for server to stop...")
            return self._wait_for_action(action_id)
            
        return True
    
    def get_server_by_name(self, name: str) -> Dict:
        """Get server by name"""
        servers = self.list_servers()
        for server in servers:
            if server["name"] == name:
                return server
        return {}
        
    def get_server_by_id(self, server_id: int) -> Dict:
        """Get server details by ID"""
        status_code, response = self._make_request("GET", f"servers/{server_id}")
        
        if status_code != 200:
            if not self.debug:
                # In user mode no technical details
                print(f"VM with ID {server_id} not found")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting server: {error_message}")
            return {}
            
        return response.get("server", {})
    
    # Snapshot Management Functions
    def list_snapshots(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all snapshots, optionally filtered by server ID"""
        status_code, response = self._make_request("GET", "images?type=snapshot")
        
        if status_code != 200:
            print(f"Error listing snapshots: {response.get('error', 'Unknown error')}")
            return []
        
        snapshots = response.get("images", [])
        
        # Filter by server ID if provided
        if server_id:
            return [s for s in snapshots if s.get("created_from", {}).get("id") == server_id]
        return snapshots
    
    def create_snapshot(self, server_id: int, description: Optional[str] = None) -> Dict:
        """Create a snapshot of a server"""
        if not description:
            description = f"Backup from {datetime.now().strftime('%Y-%m-%d-%H%M')}"
            
        data = {
            "description": description,
            "type": "snapshot"
        }
        
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/create_image", data
        )
        
        if status_code != 201:
            print(f"Error creating snapshot: {response.get('error', 'Unknown error')}")
            return {}
            
        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for snapshot creation to complete...")
            self._wait_for_action(action_id)
            
        # Get the newly created snapshot details
        snapshots = self.list_snapshots(server_id)
        if snapshots:
            # Find the newest snapshot for this server
            newest = max(snapshots, key=lambda x: x.get("created"))
            return newest
            
        return {}
    
    def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete a snapshot by ID"""
        status_code, response = self._make_request("DELETE", f"images/{snapshot_id}")
        
        if status_code not in [200, 204]:
            if not self.debug:
                # In user mode no technical details
                print(f"Failed to delete snapshot {snapshot_id}")
            else:
                # In debug mode show technical error
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting snapshot: {error_message}")
            return False
            
        return True
    
    def _wait_for_action(self, action_id: int, timeout: int = 300) -> bool:
        """Wait for an action to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_code, response = self._make_request("GET", f"actions/{action_id}")

            if status_code != 200:
                print(f"Error checking action status: {response.get('error', 'Unknown error')}")
                return False

            status = response.get("action", {}).get("status")
            if status == "success":
                return True
            elif status == "error":
                print(f"Action failed: {response.get('action', {}).get('error', {}).get('message', 'Unknown error')}")
                return False

            print(".", end="", flush=True)
            time.sleep(5)

        print(f"\nTimeout waiting for action {action_id} to complete")
        return False

    # Volume Management Functions
    def list_volumes(self) -> List[Dict]:
        """List all volumes in the project"""
        status_code, response = self._make_request("GET", "volumes")

        if status_code != 200:
            print(f"Error listing volumes: {response.get('error', 'Unknown error')}")
            return []

        return response.get("volumes", [])

    def get_volume_by_id(self, volume_id: int) -> Dict:
        """Get volume details by ID"""
        status_code, response = self._make_request("GET", f"volumes/{volume_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Volume with ID {volume_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting volume: {error_message}")
            return {}

        return response.get("volume", {})

    def create_volume(self, name: str, size: int, location: str = None,
                     server_id: int = None, format_volume: str = None,
                     labels: Dict = None) -> Dict:
        """
        Create a new volume

        Args:
            name: Volume name
            size: Volume size in GB (minimum 10)
            location: Location name (e.g. 'nbg1') - required if server_id not provided
            server_id: Server ID to attach to (optional)
            format_volume: Filesystem format ('xfs' or 'ext4') - only if server_id provided
            labels: Optional labels as dict
        """
        data = {
            "name": name,
            "size": size
        }

        if location:
            data["location"] = location

        if server_id:
            data["server"] = server_id

        if format_volume:
            data["format"] = format_volume

        if labels:
            data["labels"] = labels

        status_code, response = self._make_request("POST", "volumes", data)

        if status_code != 201:
            print(f"Error creating volume: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}

        # Wait for the action to complete if there is one
        action = response.get("action")
        if action:
            action_id = action.get("id")
            if action_id:
                print("Waiting for volume creation to complete...")
                if not self._wait_for_action(action_id):
                    return {}

        return response.get("volume", {})

    def delete_volume(self, volume_id: int) -> bool:
        """Delete a volume by ID"""
        status_code, response = self._make_request("DELETE", f"volumes/{volume_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                print(f"Failed to delete volume {volume_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting volume: {error_message}")
            return False

        return True

    def attach_volume(self, volume_id: int, server_id: int, automount: bool = False) -> bool:
        """Attach a volume to a server"""
        data = {
            "server": server_id,
            "automount": automount
        }

        status_code, response = self._make_request(
            "POST", f"volumes/{volume_id}/actions/attach", data
        )

        if status_code != 201:
            print(f"Error attaching volume: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for volume attachment to complete...")
            return self._wait_for_action(action_id)

        return True

    def detach_volume(self, volume_id: int) -> bool:
        """Detach a volume from its server"""
        status_code, response = self._make_request(
            "POST", f"volumes/{volume_id}/actions/detach", {}
        )

        if status_code != 201:
            print(f"Error detaching volume: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for volume detachment to complete...")
            return self._wait_for_action(action_id)

        return True

    def resize_volume(self, volume_id: int, size: int) -> bool:
        """
        Resize a volume

        Args:
            volume_id: Volume ID
            size: New size in GB (must be larger than current size)
        """
        data = {
            "size": size
        }

        status_code, response = self._make_request(
            "POST", f"volumes/{volume_id}/actions/resize", data
        )

        if status_code != 201:
            print(f"Error resizing volume: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for volume resize to complete...")
            return self._wait_for_action(action_id)

        return True

    def change_volume_protection(self, volume_id: int, delete: bool = None) -> bool:
        """
        Change volume protection settings

        Args:
            volume_id: Volume ID
            delete: Enable/disable delete protection
        """
        data = {}

        if delete is not None:
            data["delete"] = delete

        status_code, response = self._make_request(
            "POST", f"volumes/{volume_id}/actions/change_protection", data
        )

        if status_code != 201:
            print(f"Error changing volume protection: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for protection change to complete...")
            return self._wait_for_action(action_id)

        return True

    # ISO Management Functions
    def list_isos(self) -> List[Dict]:
        """List all available ISOs"""
        status_code, response = self._make_request("GET", "isos")

        if status_code != 200:
            print(f"Error listing ISOs: {response.get('error', 'Unknown error')}")
            return []

        return response.get("isos", [])

    def get_iso_by_id(self, iso_id: int) -> Dict:
        """Get ISO details by ID"""
        status_code, response = self._make_request("GET", f"isos/{iso_id}")

        if status_code != 200:
            if not self.debug:
                print(f"ISO with ID {iso_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting ISO: {error_message}")
            return {}

        return response.get("iso", {})

    def attach_iso_to_server(self, server_id: int, iso_id: int) -> bool:
        """Attach an ISO to a server"""
        data = {
            "iso": iso_id
        }

        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/attach_iso", data
        )

        if status_code != 201:
            print(f"Error attaching ISO: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for ISO attachment to complete...")
            return self._wait_for_action(action_id)

        return True

    def detach_iso_from_server(self, server_id: int) -> bool:
        """Detach the ISO from a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/detach_iso", {}
        )

        if status_code != 201:
            print(f"Error detaching ISO: {response.get('error', {}).get('message', 'Unknown error')}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            print("Waiting for ISO detachment to complete...")
            return self._wait_for_action(action_id)

        return True

    # Location & Datacenter Functions
    def list_locations(self) -> List[Dict]:
        """List all available locations"""
        status_code, response = self._make_request("GET", "locations")

        if status_code != 200:
            print(f"Error listing locations: {response.get('error', 'Unknown error')}")
            return []

        return response.get("locations", [])

    def get_location_by_id(self, location_id: int) -> Dict:
        """Get location details by ID"""
        status_code, response = self._make_request("GET", f"locations/{location_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Location with ID {location_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting location: {error_message}")
            return {}

        return response.get("location", {})

    def list_datacenters(self) -> List[Dict]:
        """List all available datacenters"""
        status_code, response = self._make_request("GET", "datacenters")

        if status_code != 200:
            print(f"Error listing datacenters: {response.get('error', 'Unknown error')}")
            return []

        return response.get("datacenters", [])

    def get_datacenter_by_id(self, datacenter_id: int) -> Dict:
        """Get datacenter details by ID"""
        status_code, response = self._make_request("GET", f"datacenters/{datacenter_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Datacenter with ID {datacenter_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting datacenter: {error_message}")
            return {}

        return response.get("datacenter", {})
