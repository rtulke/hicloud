#!/usr/bin/env python3
# lib/api.py - Hetzner Cloud API Manager

import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from utils.constants import API_BASE_URL
from utils.spinner import DotsSpinner


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
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return 400, {"error": {"message": f"Unsupported method: {method}"}}
                
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
                    return response.status_code, {"error": {"message": error_msg}}
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            if self.debug:
                print(error_msg)
            return 500, {"error": {"message": error_msg}}
    
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
        # Hetzner API erwartet ISO 8601 mit Timezone (Z für UTC)
        end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Für längere Zeiträume größere Schritte verwenden
        step = "60" if hours <= 6 else "300" if hours <= 48 else "3600"

        return self.get_server_metrics(server_id, "cpu", start_time, end_time, step)

    def get_network_metrics(self, server_id: int, days: int = 7) -> Dict:
        """Gets network metrics for a server for the specified number of days"""
        # Berechne Start- und Endzeitpunkt basierend auf Tagen
        # Hetzner API erwartet ISO 8601 mit Timezone (Z für UTC)
        end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Für längere Zeiträume größere Schritte verwenden
        step = "300" if days <= 1 else "3600" if days <= 7 else "86400"

        return self.get_server_metrics(server_id, "network", start_time, end_time, step)

    def get_disk_metrics(self, server_id: int, days: int = 1) -> Dict:
        """Gets disk metrics for a server for the specified number of days"""
        # Berechne Start- und Endzeitpunkt basierend auf Tagen
        # Hetzner API erwartet ISO 8601 mit Timezone (Z für UTC)
        end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

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
            error_message = response.get("error", {}).get("message", "Unknown error")
            print(f"Error getting pricing information: {error_message}")
            return {}
            
        return response.get("pricing", {})

    def list_server_types(self) -> List[Dict]:
        """Return all server types with their specifications"""
        status_code, response = self._make_request("GET", "server_types")

        if status_code != 200:
            if self.debug:
                error_message = response.get("error", {}).get("message", "Unknown error")
                print(f"Error listing server types: {error_message}")
            return []

        return response.get("server_types", [])
    
    def calculate_project_costs(self) -> Dict:
        """Calculates the estimated monthly costs for all resources in the project"""
        # Preisdaten abrufen
        pricing = self.get_pricing()
        if not pricing:
            return {}

        def _price_value(value: Any) -> float:
            """Normalize price objects (gross/net or raw) to float."""
            if isinstance(value, dict):
                return float(value.get("gross") or value.get("net") or 0)
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
            
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
                price_entries = price_info.get("prices", [])
                if not price_entries:
                    continue
                price = _price_value(price_entries[0].get("price_monthly", {}))
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
                
                volume_pricing = pricing.get("volume", {})
                volume_price_per_gb = _price_value(
                    volume_pricing.get("price_per_gb_month", volume_pricing.get("price_monthly", {}))
                )
                if volume_price_per_gb == 0 and volume_pricing.get("prices"):
                    volume_price_per_gb = _price_value(volume_pricing.get("prices", [{}])[0].get("price_monthly", {}))
                
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
                
                floating_pricing = pricing.get("floating_ip", {})
                ip_price = _price_value(floating_pricing.get("price_monthly", {}))
                if ip_price == 0 and floating_pricing.get("prices"):
                    ip_price = _price_value(floating_pricing.get("prices", [{}])[0].get("price_monthly", {}))
                
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
                        prices = lb_type.get("prices", [])
                        if not prices:
                            continue
                        price = _price_value(prices[0].get("price_monthly", {}))
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
            return self._wait_for_action(
                action_id,
                message="Waiting for server rebuild to complete..."
            )
            
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
            return self._wait_for_action(
                action_id,
                message="Waiting for backup enablement to complete..."
            )
            
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
            return self._wait_for_action(
                action_id,
                message="Waiting for backup disablement to complete..."
            )
            
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
            return self._wait_for_action(
                action_id,
                message="Waiting for resize operation to complete..."
            )
            
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
            if not self._wait_for_action(
                action_id,
                message="Waiting for rescue mode enablement to complete..."
            ):
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
            if not self._wait_for_action(
                action_id,
                message="Waiting for password reset to complete..."
            ):
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
            return self._wait_for_action(
                action_id,
                message="Waiting for server to reboot..."
            )
            
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
            if not self._wait_for_action(
                action_id,
                message="Waiting for image creation to complete..."
            ):
                return {}
                
        # Return the image details
        return response.get("image", {})

    def import_image_from_url(
        self,
        name: str,
        image_url: str,
        architecture: str = "x86",
        description: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Dict:
        """Import a custom image hosted at a remote HTTP(S) URL."""
        payload: Dict[str, Any] = {
            "type": "system",
            "name": name,
            "architecture": architecture,
            "url": image_url
        }

        if description:
            payload["description"] = description
        if labels:
            payload["labels"] = labels

        status_code, response = self._make_request("POST", "images/actions/import", payload)

        if status_code not in [201, 202]:
            error_message = response.get("error", {}).get("message", "Unknown error")
            print(f"Error importing image: {error_message}")
            return {}

        action_id = response.get("action", {}).get("id")
        if action_id:
            if not self._wait_for_action(
                action_id,
                message="Importing image from remote URL..."
            ):
                return {}

        image = response.get("image")
        if image:
            return image

        image_id = response.get("image_id")
        if image_id:
            return {"id": image_id}

        return {}

    
    
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
            return self._wait_for_action(
                action_id,
                message="Waiting for server to start..."
            )
            
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
            return self._wait_for_action(
                action_id,
                message="Waiting for server to stop..."
            )
            
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
            self._wait_for_action(
                action_id,
                message="Waiting for snapshot creation to complete..."
            )
            
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
    
    def _wait_for_action(self, action_id: int, timeout: int = 300, message: Optional[str] = None) -> bool:
        """Wait for an action to complete while rendering a spinner."""
        start_time = time.time()
        spinner = DotsSpinner(message).start() if message else None

        while time.time() - start_time < timeout:
            status_code, response = self._make_request("GET", f"actions/{action_id}")

            if status_code != 200:
                if spinner:
                    spinner.stop(False)
                print(f"Error checking action status: {response.get('error', 'Unknown error')}")
                return False

            status = response.get("action", {}).get("status")
            if status == "success":
                if spinner:
                    spinner.stop(True)
                return True
            if status == "error":
                if spinner:
                    spinner.stop(False)
                print(f"Action failed: {response.get('action', {}).get('error', {}).get('message', 'Unknown error')}")
                return False

            time.sleep(5)

        if spinner:
            spinner.stop(False)
        print(f"Timeout waiting for action {action_id} to complete")
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
                if not self._wait_for_action(
                    action_id,
                    message="Waiting for volume creation to complete..."
                ):
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
            return self._wait_for_action(
                action_id,
                message="Waiting for volume attachment to complete..."
            )

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
            return self._wait_for_action(
                action_id,
                message="Waiting for volume detachment to complete..."
            )

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
            return self._wait_for_action(
                action_id,
                message="Waiting for volume resize to complete..."
            )

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
            return self._wait_for_action(
                action_id,
                message="Waiting for protection change to complete..."
            )

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
            return self._wait_for_action(
                action_id,
                message="Waiting for ISO attachment to complete..."
            )

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
            return self._wait_for_action(
                action_id,
                message="Waiting for ISO detachment to complete..."
            )

        return True

    # Network Management Functions
    def list_networks(self) -> List[Dict]:
        """List all networks in the project"""
        status_code, response = self._make_request("GET", "networks")

        if status_code != 200:
            print(f"Error listing networks: {response.get('error', 'Unknown error')}")
            return []

        return response.get("networks", [])

    def get_network_by_id(self, network_id: int) -> Dict:
        """Get network by ID"""
        status_code, response = self._make_request("GET", f"networks/{network_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Network with ID {network_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting network: {error_message}")
            return {}

        return response.get("network", {})

    def create_network(self, name: str, ip_range: str, subnets: List[Dict] = None, labels: Dict = None) -> Dict:
        """Create a new network"""
        data = {
            "name": name,
            "ip_range": ip_range
        }

        if subnets:
            data["subnets"] = subnets

        if labels:
            data["labels"] = labels

        status_code, response = self._make_request("POST", "networks", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to create network '{name}'")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error creating network: {error_message}")
            return {}

        return response.get("network", {})

    def delete_network(self, network_id: int) -> bool:
        """Delete a network by ID"""
        status_code, response = self._make_request("DELETE", f"networks/{network_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                print(f"Failed to delete network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting network: {error_message}")
            return False

        return True

    def update_network(self, network_id: int, name: str = None, labels: Dict = None) -> Dict:
        """Update network metadata (name and/or labels)"""
        data = {}

        if name is not None:
            data["name"] = name

        if labels is not None:
            data["labels"] = labels

        if not data:
            print("No updates provided")
            return {}

        status_code, response = self._make_request("PUT", f"networks/{network_id}", data)

        if status_code != 200:
            if not self.debug:
                print(f"Failed to update network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error updating network: {error_message}")
            return {}

        return response.get("network", {})

    def attach_server_to_network(self, network_id: int, server_id: int, ip: str = None, alias_ips: List[str] = None) -> bool:
        """Attach a server to a network"""
        data = {
            "network": network_id
        }

        if ip:
            data["ip"] = ip

        if alias_ips:
            data["alias_ips"] = alias_ips

        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/attach_to_network", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to attach server {server_id} to network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error attaching to network: {error_message}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            return self._wait_for_action(
                action_id,
                message="Waiting for network attachment to complete..."
            )

        return True

    def detach_server_from_network(self, network_id: int, server_id: int) -> bool:
        """Detach a server from a network"""
        data = {
            "network": network_id
        }

        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/detach_from_network", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to detach server {server_id} from network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error detaching from network: {error_message}")
            return False

        # Wait for the action to complete
        action_id = response.get("action", {}).get("id")
        if action_id:
            return self._wait_for_action(
                action_id,
                message="Waiting for network detachment to complete..."
            )

        return True

    def add_subnet_to_network(self, network_id: int, network_zone: str, ip_range: str, type: str = "cloud") -> Dict:
        """Add a subnet to a network"""
        data = {
            "network_zone": network_zone,
            "ip_range": ip_range,
            "type": type
        }

        status_code, response = self._make_request("POST", f"networks/{network_id}/actions/add_subnet", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to add subnet to network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error adding subnet: {error_message}")
            return {}

        return response.get("network", {})

    def delete_subnet_from_network(self, network_id: int, ip_range: str) -> bool:
        """Delete a subnet from a network"""
        data = {
            "ip_range": ip_range
        }

        status_code, response = self._make_request("POST", f"networks/{network_id}/actions/delete_subnet", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to delete subnet from network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting subnet: {error_message}")
            return False

        return True

    def change_network_protection(self, network_id: int, delete: bool = None) -> Dict:
        """Change network protection settings"""
        data = {}

        if delete is not None:
            data["delete"] = delete

        if not data:
            print("No protection changes provided")
            return {}

        status_code, response = self._make_request("POST", f"networks/{network_id}/actions/change_protection", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to change protection for network {network_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error changing protection: {error_message}")
            return {}

        return response.get("network", {})

    # Load Balancer Management Functions
    def list_load_balancer_types(self) -> List[Dict]:
        """List all available load balancer types."""
        status_code, response = self._make_request("GET", "load_balancer_types")

        if status_code != 200:
            print(f"Error listing load balancer types: {response.get('error', 'Unknown error')}")
            return []

        return response.get("load_balancer_types", [])

    def list_load_balancers(self) -> List[Dict]:
        """List all load balancers in the project."""
        status_code, response = self._make_request("GET", "load_balancers")

        if status_code != 200:
            print(f"Error listing load balancers: {response.get('error', 'Unknown error')}")
            return []

        return response.get("load_balancers", [])

    def get_load_balancer_by_id(self, load_balancer_id: int) -> Dict:
        """Get load balancer details by ID."""
        status_code, response = self._make_request("GET", f"load_balancers/{load_balancer_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Load balancer with ID {load_balancer_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting load balancer: {error_message}")
            return {}

        return response.get("load_balancer", {})

    def create_load_balancer(
        self,
        name: str,
        load_balancer_type: str,
        location: Optional[str] = None,
        network_zone: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        public_interface: bool = True
    ) -> Dict:
        """Create a new load balancer."""
        data: Dict[str, Any] = {
            "name": name,
            "load_balancer_type": load_balancer_type,
            "public_interface": public_interface,
        }

        if location:
            data["location"] = location
        elif network_zone:
            data["network_zone"] = network_zone

        if labels:
            data["labels"] = labels

        status_code, response = self._make_request("POST", "load_balancers", data)

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to create load balancer '{name}'")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error creating load balancer: {error_message}")
            return {}

        if not self._wait_for_actions(response, "Waiting for load balancer creation to complete..."):
            return {}

        return response.get("load_balancer", {})

    def delete_load_balancer(self, load_balancer_id: int) -> bool:
        """Delete a load balancer by ID."""
        status_code, response = self._make_request("DELETE", f"load_balancers/{load_balancer_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                print(f"Failed to delete load balancer {load_balancer_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting load balancer: {error_message}")
            return False

        return True

    def add_load_balancer_target(self, load_balancer_id: int, target: Dict) -> bool:
        """Add a target to a load balancer."""
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{load_balancer_id}/actions/add_target",
            target
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to add target to load balancer {load_balancer_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error adding load balancer target: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for target attachment to complete...")

    def remove_load_balancer_target(self, load_balancer_id: int, target: Dict) -> bool:
        """Remove a target from a load balancer."""
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{load_balancer_id}/actions/remove_target",
            target
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to remove target from load balancer {load_balancer_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error removing load balancer target: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for target removal to complete...")

    # Firewall Management Functions
    def _wait_for_actions(self, response: Dict, message: str) -> bool:
        """Wait for one or more actions contained in an API response."""
        action_ids: List[int] = []

        action = response.get("action", {})
        if isinstance(action, dict) and action.get("id"):
            action_ids.append(action["id"])

        for item in response.get("actions", []) or []:
            if isinstance(item, dict) and item.get("id"):
                action_ids.append(item["id"])

        if not action_ids:
            return True

        for index, action_id in enumerate(action_ids, start=1):
            wait_message = message
            if len(action_ids) > 1:
                wait_message = f"{message} ({index}/{len(action_ids)})"
            if not self._wait_for_action(action_id, message=wait_message):
                return False

        return True

    def list_firewalls(self) -> List[Dict]:
        """List all firewalls in the project."""
        status_code, response = self._make_request("GET", "firewalls")

        if status_code != 200:
            print(f"Error listing firewalls: {response.get('error', 'Unknown error')}")
            return []

        return response.get("firewalls", [])

    def get_firewall_by_id(self, firewall_id: int) -> Dict:
        """Get firewall details by ID."""
        status_code, response = self._make_request("GET", f"firewalls/{firewall_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Firewall with ID {firewall_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting firewall: {error_message}")
            return {}

        return response.get("firewall", {})

    def create_firewall(
        self,
        name: str,
        rules: Optional[List[Dict]] = None,
        apply_to: Optional[List[Dict]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict:
        """Create a new firewall."""
        data: Dict[str, Any] = {"name": name}

        if rules is not None:
            data["rules"] = rules
        if apply_to:
            data["apply_to"] = apply_to
        if labels:
            data["labels"] = labels

        status_code, response = self._make_request("POST", "firewalls", data)

        if status_code != 201:
            if not self.debug:
                print(f"Failed to create firewall '{name}'")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error creating firewall: {error_message}")
            return {}

        return response.get("firewall", {})

    def update_firewall(self, firewall_id: int, name: Optional[str] = None, labels: Optional[Dict[str, str]] = None) -> Dict:
        """Update firewall metadata (name and/or labels)."""
        data: Dict[str, Any] = {}

        if name is not None:
            data["name"] = name
        if labels is not None:
            data["labels"] = labels

        if not data:
            print("No updates provided")
            return {}

        status_code, response = self._make_request("PUT", f"firewalls/{firewall_id}", data)

        if status_code != 200:
            if not self.debug:
                print(f"Failed to update firewall {firewall_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error updating firewall: {error_message}")
            return {}

        return response.get("firewall", {})

    def delete_firewall(self, firewall_id: int) -> bool:
        """Delete a firewall by ID."""
        status_code, response = self._make_request("DELETE", f"firewalls/{firewall_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                print(f"Failed to delete firewall {firewall_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting firewall: {error_message}")
            return False

        return True

    def set_firewall_rules(self, firewall_id: int, rules: List[Dict]) -> bool:
        """Replace firewall rules."""
        data = {"rules": rules}
        status_code, response = self._make_request("POST", f"firewalls/{firewall_id}/actions/set_rules", data)

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to update rules for firewall {firewall_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error setting firewall rules: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for firewall rule update to complete...")

    def apply_firewall_to_resources(self, firewall_id: int, resources: List[Dict]) -> bool:
        """Apply firewall to resources."""
        data = {"apply_to": resources}
        status_code, response = self._make_request(
            "POST",
            f"firewalls/{firewall_id}/actions/apply_to_resources",
            data
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to apply firewall {firewall_id} to resources")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error applying firewall to resources: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for firewall apply operation to complete...")

    def remove_firewall_from_resources(self, firewall_id: int, resources: List[Dict]) -> bool:
        """Remove firewall from resources."""
        data = {"remove_from": resources}
        status_code, response = self._make_request(
            "POST",
            f"firewalls/{firewall_id}/actions/remove_from_resources",
            data
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to remove firewall {firewall_id} from resources")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error removing firewall from resources: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for firewall removal to complete...")

    # Floating IP Management Functions
    def list_floating_ips(self) -> List[Dict]:
        """List all Floating IPs"""
        status_code, response = self._make_request("GET", "floating_ips")
        if status_code != 200:
            print(f"Error listing floating IPs: {response.get('error', 'Unknown error')}")
            return []
        return response.get("floating_ips", [])

    def get_floating_ip_by_id(self, fip_id: int) -> Dict:
        """Get a Floating IP by ID"""
        status_code, response = self._make_request("GET", f"floating_ips/{fip_id}")
        if status_code != 200:
            if not self.debug:
                print(f"Floating IP with ID {fip_id} not found")
            else:
                print(f"Error getting floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("floating_ip", {})

    def create_floating_ip(self, ip_type: str, name: str, home_location: str = None,
                           server: int = None, description: str = None, labels: Dict = None) -> Dict:
        """Create a new Floating IP"""
        data: Dict = {"type": ip_type, "name": name}
        if home_location:
            data["home_location"] = home_location
        if server:
            data["server"] = server
        if description:
            data["description"] = description
        if labels:
            data["labels"] = labels
        status_code, response = self._make_request("POST", "floating_ips", data)
        if status_code not in (200, 201):
            if not self.debug:
                print(f"Failed to create floating IP '{name}'")
            else:
                print(f"Error creating floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("floating_ip", {})

    def update_floating_ip(self, fip_id: int, name: str = None,
                           description: str = None, labels: Dict = None) -> Dict:
        """Update Floating IP metadata"""
        data: Dict = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if labels is not None:
            data["labels"] = labels
        status_code, response = self._make_request("PUT", f"floating_ips/{fip_id}", data)
        if status_code != 200:
            if not self.debug:
                print(f"Failed to update floating IP {fip_id}")
            else:
                print(f"Error updating floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("floating_ip", {})

    def delete_floating_ip(self, fip_id: int) -> bool:
        """Delete a Floating IP (must be unassigned)"""
        status_code, response = self._make_request("DELETE", f"floating_ips/{fip_id}")
        if status_code not in (200, 204):
            if not self.debug:
                print(f"Failed to delete floating IP {fip_id}")
            else:
                print(f"Error deleting floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return True

    def assign_floating_ip(self, fip_id: int, server_id: int) -> bool:
        """Assign a Floating IP to a server"""
        status_code, response = self._make_request(
            "POST", f"floating_ips/{fip_id}/actions/assign", {"server": server_id}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to assign floating IP {fip_id} to server {server_id}")
            else:
                print(f"Error assigning floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for floating IP assignment...")

    def unassign_floating_ip(self, fip_id: int) -> bool:
        """Unassign a Floating IP from its current server"""
        status_code, response = self._make_request(
            "POST", f"floating_ips/{fip_id}/actions/unassign", {}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to unassign floating IP {fip_id}")
            else:
                print(f"Error unassigning floating IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for floating IP unassignment...")

    def change_floating_ip_dns_ptr(self, fip_id: int, ip: str, dns_ptr: str = None) -> bool:
        """Set or reset reverse DNS for a Floating IP"""
        status_code, response = self._make_request(
            "POST", f"floating_ips/{fip_id}/actions/change_dns_ptr", {"ip": ip, "dns_ptr": dns_ptr}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to update rDNS for floating IP {fip_id}")
            else:
                print(f"Error updating rDNS: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for rDNS update...")

    def change_floating_ip_protection(self, fip_id: int, delete: bool) -> bool:
        """Enable or disable delete protection for a Floating IP"""
        status_code, response = self._make_request(
            "POST", f"floating_ips/{fip_id}/actions/change_protection", {"delete": delete}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to change protection for floating IP {fip_id}")
            else:
                print(f"Error changing protection: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for protection change...")

    # Primary IP Management Functions
    def list_primary_ips(self) -> List[Dict]:
        """List all Primary IPs"""
        status_code, response = self._make_request("GET", "primary_ips")
        if status_code != 200:
            print(f"Error listing primary IPs: {response.get('error', 'Unknown error')}")
            return []
        return response.get("primary_ips", [])

    def get_primary_ip_by_id(self, pip_id: int) -> Dict:
        """Get a Primary IP by ID"""
        status_code, response = self._make_request("GET", f"primary_ips/{pip_id}")
        if status_code != 200:
            if not self.debug:
                print(f"Primary IP with ID {pip_id} not found")
            else:
                print(f"Error getting primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("primary_ip", {})

    def create_primary_ip(self, ip_type: str, name: str, assignee_type: str = "server",
                          datacenter: str = None, assignee_id: int = None,
                          auto_delete: bool = False, labels: Dict = None) -> Dict:
        """Create a new Primary IP"""
        data: Dict = {"type": ip_type, "name": name, "assignee_type": assignee_type,
                      "auto_delete": auto_delete}
        if datacenter:
            data["datacenter"] = datacenter
        if assignee_id:
            data["assignee_id"] = assignee_id
        if labels:
            data["labels"] = labels
        status_code, response = self._make_request("POST", "primary_ips", data)
        if status_code not in (200, 201):
            if not self.debug:
                print(f"Failed to create primary IP '{name}'")
            else:
                print(f"Error creating primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("primary_ip", {})

    def update_primary_ip(self, pip_id: int, name: str = None,
                          auto_delete: bool = None, labels: Dict = None) -> Dict:
        """Update Primary IP metadata"""
        data: Dict = {}
        if name is not None:
            data["name"] = name
        if auto_delete is not None:
            data["auto_delete"] = auto_delete
        if labels is not None:
            data["labels"] = labels
        status_code, response = self._make_request("PUT", f"primary_ips/{pip_id}", data)
        if status_code != 200:
            if not self.debug:
                print(f"Failed to update primary IP {pip_id}")
            else:
                print(f"Error updating primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return {}
        return response.get("primary_ip", {})

    def delete_primary_ip(self, pip_id: int) -> bool:
        """Delete a Primary IP (must be unassigned first)"""
        status_code, response = self._make_request("DELETE", f"primary_ips/{pip_id}")
        if status_code not in (200, 204):
            if not self.debug:
                print(f"Failed to delete primary IP {pip_id}")
            else:
                print(f"Error deleting primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return True

    def assign_primary_ip(self, pip_id: int, server_id: int) -> bool:
        """Assign a Primary IP to a server"""
        status_code, response = self._make_request(
            "POST", f"primary_ips/{pip_id}/actions/assign",
            {"assignee_id": server_id, "assignee_type": "server"}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to assign primary IP {pip_id} to server {server_id}")
            else:
                print(f"Error assigning primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for primary IP assignment...")

    def unassign_primary_ip(self, pip_id: int) -> bool:
        """Unassign a Primary IP from its current server"""
        status_code, response = self._make_request(
            "POST", f"primary_ips/{pip_id}/actions/unassign", {}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to unassign primary IP {pip_id}")
            else:
                print(f"Error unassigning primary IP: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for primary IP unassignment...")

    def change_primary_ip_dns_ptr(self, pip_id: int, ip: str, dns_ptr: str = None) -> bool:
        """Set or reset reverse DNS for a Primary IP"""
        status_code, response = self._make_request(
            "POST", f"primary_ips/{pip_id}/actions/change_dns_ptr", {"ip": ip, "dns_ptr": dns_ptr}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to update rDNS for primary IP {pip_id}")
            else:
                print(f"Error updating rDNS: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for rDNS update...")

    def change_primary_ip_protection(self, pip_id: int, delete: bool) -> bool:
        """Enable or disable delete protection for a Primary IP"""
        status_code, response = self._make_request(
            "POST", f"primary_ips/{pip_id}/actions/change_protection", {"delete": delete}
        )
        if status_code not in (200, 201, 202):
            if not self.debug:
                print(f"Failed to change protection for primary IP {pip_id}")
            else:
                print(f"Error changing protection: {response.get('error', {}).get('message', 'Unknown error')}")
            return False
        return self._wait_for_actions(response, "Waiting for protection change...")

    # Image Management Functions
    def list_images(self, image_type: str = None) -> List[Dict]:
        """List images, optionally filtered by type (snapshot, backup, system, app)"""
        endpoint = "images"
        if image_type:
            endpoint = f"images?type={image_type}"
        status_code, response = self._make_request("GET", endpoint)

        if status_code != 200:
            print(f"Error listing images: {response.get('error', 'Unknown error')}")
            return []

        return response.get("images", [])

    def get_image_by_id(self, image_id: int) -> Dict:
        """Get image details by ID"""
        status_code, response = self._make_request("GET", f"images/{image_id}")

        if status_code != 200:
            if not self.debug:
                print(f"Image with ID {image_id} not found")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error getting image: {error_message}")
            return {}

        return response.get("image", {})

    def delete_image(self, image_id: int) -> bool:
        """Delete an image (only custom images can be deleted)"""
        status_code, response = self._make_request("DELETE", f"images/{image_id}")

        if status_code not in [200, 204]:
            if not self.debug:
                print(f"Failed to delete image {image_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting image: {error_message}")
            return False

        return True

    def update_image(self, image_id: int, description: str = None, labels: Dict = None) -> Dict:
        """Update image metadata (description and/or labels)"""
        data: Dict = {}
        if description is not None:
            data["description"] = description
        if labels is not None:
            data["labels"] = labels

        status_code, response = self._make_request("PUT", f"images/{image_id}", data)

        if status_code != 200:
            if not self.debug:
                print(f"Failed to update image {image_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error updating image: {error_message}")
            return {}

        return response.get("image", {})

    # Load Balancer Service & Algorithm Functions
    def add_lb_service(self, lb_id: int, service: Dict) -> bool:
        """Add a service to a load balancer"""
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{lb_id}/actions/add_service",
            service,
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to add service to load balancer {lb_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error adding lb service: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for service add to complete...")

    def delete_lb_service(self, lb_id: int, listen_port: int) -> bool:
        """Delete a service from a load balancer by listen port"""
        data = {"listen_port": listen_port}
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{lb_id}/actions/delete_service",
            data,
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to delete service (port {listen_port}) from load balancer {lb_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error deleting lb service: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for service deletion to complete...")

    def update_lb_service(self, lb_id: int, service: Dict) -> bool:
        """Update a service on a load balancer"""
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{lb_id}/actions/update_service",
            service,
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to update service on load balancer {lb_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error updating lb service: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for service update to complete...")

    def change_lb_algorithm(self, lb_id: int, algorithm: str) -> bool:
        """Change the algorithm of a load balancer (round_robin or least_connections)"""
        data = {"type": algorithm}
        status_code, response = self._make_request(
            "POST",
            f"load_balancers/{lb_id}/actions/change_algorithm",
            data,
        )

        if status_code not in [200, 201, 202]:
            if not self.debug:
                print(f"Failed to change algorithm for load balancer {lb_id}")
            else:
                error_message = response.get('error', {}).get('message', 'Unknown error')
                print(f"Error changing lb algorithm: {error_message}")
            return False

        return self._wait_for_actions(response, "Waiting for algorithm change to complete...")

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
