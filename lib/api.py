#!/usr/bin/env python3
# lib/api.py - Hetzner Cloud API Manager

import json
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

from utils.constants import API_BASE_URL, RATE_LIMIT_MAX_RETRIES, REQUEST_TIMEOUT
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

    # ------------------------------------------------------------------
    # Core request layer
    # ------------------------------------------------------------------

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Tuple[int, Dict]:
        """Make an API request to Hetzner Cloud"""
        url = f"{API_BASE_URL}/{endpoint}"

        try:
            for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
                if method == "GET":
                    response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)
                elif method == "PUT":
                    response = requests.put(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)
                elif method == "DELETE":
                    response = requests.delete(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
                else:
                    return 400, {"error": {"message": f"Unsupported method: {method}"}}

                if response.status_code != 429 or attempt == RATE_LIMIT_MAX_RETRIES:
                    break

                retry_delay = self._rate_limit_delay(response)
                if self.debug:
                    print(f"Rate limited (429), retrying in {retry_delay}s...")
                time.sleep(retry_delay)

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

    @staticmethod
    def _rate_limit_delay(response) -> int:
        """Seconds to wait after an HTTP 429, from Retry-After if present (1-60s)."""
        try:
            delay = int(response.headers.get("Retry-After", 5))
        except (TypeError, ValueError):
            delay = 5
        return max(1, min(delay, 60))

    def _get_all_pages(self, endpoint: str, key: str) -> Tuple[int, Dict]:
        """
        GET a list endpoint and follow meta.pagination across all pages.

        Returns the same (status_code, response) shape as _make_request,
        with the `key` arrays of all pages merged. The first request uses
        the endpoint unchanged so page numbering stays consistent with the
        API's default page size.
        """
        status_code, response = self._make_request("GET", endpoint)
        if status_code != 200:
            return status_code, response

        items = list(response.get(key, []))
        next_page = response.get("meta", {}).get("pagination", {}).get("next_page")
        separator = "&" if "?" in endpoint else "?"

        while next_page:
            status_code, response = self._make_request("GET", f"{endpoint}{separator}page={next_page}")
            if status_code != 200:
                return status_code, response
            items.extend(response.get(key, []))
            next_page = response.get("meta", {}).get("pagination", {}).get("next_page")

        return 200, {key: items}

    # ------------------------------------------------------------------
    # Error reporting (single convention for the whole API layer)
    # ------------------------------------------------------------------

    @staticmethod
    def _error_message(response: Dict) -> str:
        """Extract the API error message from a response payload."""
        error = response.get("error")
        if isinstance(error, dict):
            return error.get("message", "Unknown error")
        if error:
            return str(error)
        return "Unknown error"

    def _report_error(self, context: str, status_code: int, response: Dict) -> None:
        """
        Render an API error. The API message is always shown — it tells the
        user what to do (e.g. "server is delete protected"). Debug mode only
        adds transport details on top.
        """
        print(f"Error {context}: {self._error_message(response)}")
        if self.debug:
            print(f"  HTTP status: {status_code}")

    # ------------------------------------------------------------------
    # Generic resource operations
    # ------------------------------------------------------------------

    def _get_list(self, endpoint: str, key: str, context: str) -> List[Dict]:
        """GET a paginated list; returns [] and reports on error."""
        status_code, response = self._get_all_pages(endpoint, key)
        if status_code != 200:
            self._report_error(context, status_code, response)
            return []
        return response.get(key, [])

    def _get_resource(self, endpoint: str, key: str, not_found_label: str, context: str) -> Dict:
        """GET a single resource; friendly message on 404, API message otherwise."""
        status_code, response = self._make_request("GET", endpoint)
        if status_code == 404:
            print(f"{not_found_label} not found")
            return {}
        if status_code != 200:
            self._report_error(context, status_code, response)
            return {}
        return response.get(key, {})

    def _create_resource(self, endpoint: str, data: Dict, key: str, context: str,
                         wait_message: Optional[str] = None) -> Dict:
        """POST a new resource; optionally wait for returned actions."""
        status_code, response = self._make_request("POST", endpoint, data)
        if status_code not in (200, 201, 202):
            self._report_error(context, status_code, response)
            return {}
        if wait_message is not None and not self._wait_for_actions(response, wait_message):
            return {}
        return response.get(key, {})

    def _update_resource(self, endpoint: str, data: Dict, key: str, context: str) -> Dict:
        """PUT resource metadata; returns the updated resource or {}."""
        status_code, response = self._make_request("PUT", endpoint, data)
        if status_code != 200:
            self._report_error(context, status_code, response)
            return {}
        return response.get(key, {})

    def _delete_resource(self, endpoint: str, context: str) -> bool:
        """DELETE a resource; returns True on success."""
        status_code, response = self._make_request("DELETE", endpoint)
        if status_code not in (200, 204):
            self._report_error(context, status_code, response)
            return False
        return True

    def _run_action(self, endpoint: str, data: Dict, context: str,
                    wait_message: Optional[str] = None) -> bool:
        """POST an action endpoint; optionally wait for the returned action(s)."""
        status_code, response = self._make_request("POST", endpoint, data)
        if status_code not in (200, 201, 202):
            self._report_error(context, status_code, response)
            return False
        if wait_message is None:
            return True
        return self._wait_for_actions(response, wait_message)

    # ------------------------------------------------------------------
    # Action waiting
    # ------------------------------------------------------------------

    def _wait_for_action(self, action_id: int, timeout: int = 300, message: Optional[str] = None) -> bool:
        """Wait for an action to complete while rendering a spinner."""
        start_time = time.time()
        spinner = DotsSpinner(message).start() if message else None

        while time.time() - start_time < timeout:
            status_code, response = self._make_request("GET", f"actions/{action_id}")

            if status_code != 200:
                if spinner:
                    spinner.stop(False)
                print(f"Error checking action status: {self._error_message(response)}")
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
        print("Note: the action keeps running on Hetzner's side; check the resource state before retrying.")
        return False

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

    # ------------------------------------------------------------------
    # Metrics Management Functions
    # ------------------------------------------------------------------

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

        endpoint = f"servers/{server_id}/metrics?{urlencode(params)}"

        status_code, response = self._make_request("GET", endpoint)

        if status_code != 200:
            self._report_error("getting metrics", status_code, response)
            return {}

        return response.get("metrics", {})

    def get_cpu_metrics(self, server_id: int, hours: int = 24) -> Dict:
        """Gets CPU metrics for a server for the specified number of hours"""
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Für längere Zeiträume größere Schritte verwenden
        step = "60" if hours <= 6 else "300" if hours <= 48 else "3600"

        return self.get_server_metrics(server_id, "cpu", start_time, end_time, step)

    def get_network_metrics(self, server_id: int, days: int = 7) -> Dict:
        """Gets network metrics for a server for the specified number of days"""
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Für längere Zeiträume größere Schritte verwenden
        step = "300" if days <= 1 else "3600" if days <= 7 else "86400"

        return self.get_server_metrics(server_id, "network", start_time, end_time, step)

    def get_disk_metrics(self, server_id: int, days: int = 1) -> Dict:
        """Gets disk metrics for a server for the specified number of days"""
        end_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Feste Schrittweite für Festplattenmetriken
        step = "60"

        return self.get_server_metrics(server_id, "disk", start_time, end_time, step)

    def get_available_metrics(self, server_id: int) -> List[str]:
        """Returns a list of available metric types for a server"""
        # API bietet keine direkte Möglichkeit, verfügbare Metriken abzurufen
        # Daher geben wir die unterstützten Typen zurück
        return ["cpu", "disk", "network"]

    # ------------------------------------------------------------------
    # Pricing Functions
    # ------------------------------------------------------------------

    def get_pricing(self) -> Dict:
        """Gets the current pricing information"""
        status_code, response = self._make_request("GET", "pricing")

        if status_code != 200:
            self._report_error("getting pricing information", status_code, response)
            return {}

        return response.get("pricing", {})

    def list_server_types(self) -> List[Dict]:
        """Return all server types with their specifications"""
        return self._get_list("server_types", "server_types", "listing server types")

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
            status_code, volumes_response = self._get_all_pages("volumes", "volumes")
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
            status_code, ips_response = self._get_all_pages("floating_ips", "floating_ips")
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
            status_code, lb_response = self._get_all_pages("load_balancers", "load_balancers")
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

    # ------------------------------------------------------------------
    # VM Management Functions
    # ------------------------------------------------------------------

    def rebuild_server_from_snapshot(self, server_id: int, snapshot_id: int) -> bool:
        """Rebuild a server from a snapshot"""
        data = {"image": str(snapshot_id)}
        return self._run_action(
            f"servers/{server_id}/actions/rebuild", data,
            f"rebuilding server {server_id}",
            "Waiting for server rebuild to complete..."
        )

    def resize_server(self, server_id: int, server_type: str) -> bool:
        """Change the server type of a server"""
        data = {
            "server_type": server_type,
            "upgrade_disk": True  # Vergrößere auch die Festplatte, wenn möglich
        }
        return self._run_action(
            f"servers/{server_id}/actions/change_type", data,
            f"resizing server {server_id}",
            "Waiting for resize operation to complete..."
        )

    def rename_server(self, server_id: int, name: str) -> bool:
        """Rename a server"""
        status_code, response = self._make_request("PUT", f"servers/{server_id}", {"name": name})
        if status_code != 200:
            self._report_error(f"renaming server {server_id}", status_code, response)
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
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/enable_rescue", {"type": rescue_type}
        )

        if status_code not in (200, 201, 202):
            self._report_error(f"enabling rescue mode for server {server_id}", status_code, response)
            return {}

        if not self._wait_for_actions(response, "Waiting for rescue mode enablement to complete..."):
            return {}

        return {"root_password": response.get("root_password", "")}

    def reset_server_password(self, server_id: int) -> Dict:
        """Reset the root password of a server"""
        status_code, response = self._make_request(
            "POST", f"servers/{server_id}/actions/reset_password", {}
        )

        if status_code not in (200, 201, 202):
            self._report_error(f"resetting password for server {server_id}", status_code, response)
            return {}

        if not self._wait_for_actions(response, "Waiting for password reset to complete..."):
            return {}

        return {"root_password": response.get("root_password", "")}

    def reboot_server(self, server_id: int) -> bool:
        """Reboot a server"""
        return self._run_action(
            f"servers/{server_id}/actions/reboot", {},
            f"rebooting server {server_id}",
            "Waiting for server to reboot..."
        )

    def create_image(self, server_id: int, description: str = "") -> Dict:
        """Create a custom image from a server"""
        data = {
            "description": description,
            "type": "snapshot"  # Immer als Snapshot erstellen
        }
        return self._create_resource(
            f"servers/{server_id}/actions/create_image", data, "image",
            f"creating image from server {server_id}",
            wait_message="Waiting for image creation to complete..."
        )

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

        if status_code not in (200, 201, 202):
            self._report_error(f"importing image '{name}'", status_code, response)
            return {}

        if not self._wait_for_actions(response, "Importing image from remote URL..."):
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
        return self._get_list("servers", "servers", "listing servers")

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
        data["start_after_create"] = bool(auto_password)

        return self._create_resource("servers", data, "server", f"creating server '{name}'")

    def delete_server(self, server_id: int) -> bool:
        """Delete a server by ID"""
        return self._delete_resource(f"servers/{server_id}", f"deleting server {server_id}")

    def start_server(self, server_id: int) -> bool:
        """Start a server by ID"""
        return self._run_action(
            f"servers/{server_id}/actions/poweron", {},
            f"starting server {server_id}",
            "Waiting for server to start..."
        )

    def stop_server(self, server_id: int) -> bool:
        """Stop a server by ID"""
        status_code, response = self._make_request("POST", f"servers/{server_id}/actions/shutdown", {})

        if status_code not in (200, 201, 202):
            # Fallback auf hartes Ausschalten, wenn das graceful Shutdown scheitert
            print("Graceful shutdown failed, forcing power off (unsaved data may be lost)...")
            status_code, response = self._make_request("POST", f"servers/{server_id}/actions/poweroff", {})

            if status_code not in (200, 201, 202):
                self._report_error(f"stopping server {server_id}", status_code, response)
                return False

        return self._wait_for_actions(response, "Waiting for server to stop...")

    def get_server_by_name(self, name: str) -> Dict:
        """Get server by name"""
        servers = self.list_servers()
        for server in servers:
            if server["name"] == name:
                return server
        return {}

    def get_server_by_id(self, server_id: int) -> Dict:
        """Get server details by ID"""
        return self._get_resource(
            f"servers/{server_id}", "server",
            f"VM with ID {server_id}", f"getting server {server_id}"
        )

    # ------------------------------------------------------------------
    # Snapshot Management Functions
    # ------------------------------------------------------------------

    def list_snapshots(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all snapshots, optionally filtered by server ID"""
        snapshots = self._get_list("images?type=snapshot", "images", "listing snapshots")

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

        if status_code not in (200, 201, 202):
            self._report_error(f"creating snapshot for server {server_id}", status_code, response)
            return {}

        # Warten, aber auch bei Timeout weiter versuchen, den Snapshot zu finden
        self._wait_for_actions(response, "Waiting for snapshot creation to complete...")

        # Get the newly created snapshot details
        snapshots = self.list_snapshots(server_id)
        if snapshots:
            # Find the newest snapshot for this server
            newest = max(snapshots, key=lambda x: x.get("created"))
            return newest

        return {}

    def delete_snapshot(self, snapshot_id: int) -> bool:
        """Delete a snapshot by ID"""
        return self._delete_resource(f"images/{snapshot_id}", f"deleting snapshot {snapshot_id}")

    # ------------------------------------------------------------------
    # Backup Management Functions
    # ------------------------------------------------------------------

    def list_backups(self, server_id: Optional[int] = None) -> List[Dict]:
        """List all backups, optionally filtered by server ID"""
        backups = self._get_list("images?type=backup", "images", "listing backups")

        # Filter by server ID if provided
        if server_id:
            return [b for b in backups if b.get("created_from", {}).get("id") == server_id]
        return backups

    def delete_backup(self, backup_id: int) -> bool:
        """Delete a backup by ID"""
        return self._delete_resource(f"images/{backup_id}", f"deleting backup {backup_id}")

    def enable_server_backups(self, server_id: int, backup_window: Optional[str] = None) -> bool:
        """Enable automated backups for a server"""
        data = {}
        if backup_window:
            data["backup_window"] = backup_window

        return self._run_action(
            f"servers/{server_id}/actions/enable_backup", data,
            f"enabling backups for server {server_id}",
            "Waiting for backup enablement to complete..."
        )

    def disable_server_backups(self, server_id: int) -> bool:
        """Disable automated backups for a server"""
        return self._run_action(
            f"servers/{server_id}/actions/disable_backup", {},
            f"disabling backups for server {server_id}",
            "Waiting for backup disablement to complete..."
        )

    # ------------------------------------------------------------------
    # SSH Key Management Functions
    # ------------------------------------------------------------------

    def list_ssh_keys(self) -> List[Dict]:
        """List all SSH keys in the project"""
        return self._get_list("ssh_keys", "ssh_keys", "listing SSH keys")

    def get_ssh_key_by_id(self, key_id: int) -> Dict:
        """Get SSH key by ID"""
        return self._get_resource(
            f"ssh_keys/{key_id}", "ssh_key",
            f"SSH key with ID {key_id}", f"getting SSH key {key_id}"
        )

    def delete_ssh_key(self, key_id: int) -> bool:
        """Delete an SSH key by ID"""
        return self._delete_resource(f"ssh_keys/{key_id}", f"deleting SSH key {key_id}")

    def create_ssh_key(self, name: str, public_key: str, labels: Dict = None) -> Dict:
        """Create/upload a new SSH key"""
        data = {
            "name": name,
            "public_key": public_key
        }

        if labels:
            data["labels"] = labels

        return self._create_resource("ssh_keys", data, "ssh_key", f"creating SSH key '{name}'")

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

        return self._update_resource(f"ssh_keys/{key_id}", data, "ssh_key", f"updating SSH key {key_id}")

    # ------------------------------------------------------------------
    # Volume Management Functions
    # ------------------------------------------------------------------

    def list_volumes(self) -> List[Dict]:
        """List all volumes in the project"""
        return self._get_list("volumes", "volumes", "listing volumes")

    def get_volume_by_id(self, volume_id: int) -> Dict:
        """Get volume details by ID"""
        return self._get_resource(
            f"volumes/{volume_id}", "volume",
            f"Volume with ID {volume_id}", f"getting volume {volume_id}"
        )

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

        return self._create_resource(
            "volumes", data, "volume", f"creating volume '{name}'",
            wait_message="Waiting for volume creation to complete..."
        )

    def delete_volume(self, volume_id: int) -> bool:
        """Delete a volume by ID"""
        return self._delete_resource(f"volumes/{volume_id}", f"deleting volume {volume_id}")

    def attach_volume(self, volume_id: int, server_id: int, automount: bool = False) -> bool:
        """Attach a volume to a server"""
        data = {
            "server": server_id,
            "automount": automount
        }
        return self._run_action(
            f"volumes/{volume_id}/actions/attach", data,
            f"attaching volume {volume_id}",
            "Waiting for volume attachment to complete..."
        )

    def detach_volume(self, volume_id: int) -> bool:
        """Detach a volume from its server"""
        return self._run_action(
            f"volumes/{volume_id}/actions/detach", {},
            f"detaching volume {volume_id}",
            "Waiting for volume detachment to complete..."
        )

    def resize_volume(self, volume_id: int, size: int) -> bool:
        """
        Resize a volume

        Args:
            volume_id: Volume ID
            size: New size in GB (must be larger than current size)
        """
        return self._run_action(
            f"volumes/{volume_id}/actions/resize", {"size": size},
            f"resizing volume {volume_id}",
            "Waiting for volume resize to complete..."
        )

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

        return self._run_action(
            f"volumes/{volume_id}/actions/change_protection", data,
            f"changing protection for volume {volume_id}",
            "Waiting for protection change to complete..."
        )

    # ------------------------------------------------------------------
    # ISO Management Functions
    # ------------------------------------------------------------------

    def list_isos(self) -> List[Dict]:
        """List all available ISOs"""
        return self._get_list("isos", "isos", "listing ISOs")

    def get_iso_by_id(self, iso_id: int) -> Dict:
        """Get ISO details by ID"""
        return self._get_resource(
            f"isos/{iso_id}", "iso",
            f"ISO with ID {iso_id}", f"getting ISO {iso_id}"
        )

    def attach_iso_to_server(self, server_id: int, iso_id: int) -> bool:
        """Attach an ISO to a server"""
        return self._run_action(
            f"servers/{server_id}/actions/attach_iso", {"iso": iso_id},
            f"attaching ISO {iso_id} to server {server_id}",
            "Waiting for ISO attachment to complete..."
        )

    def detach_iso_from_server(self, server_id: int) -> bool:
        """Detach the ISO from a server"""
        return self._run_action(
            f"servers/{server_id}/actions/detach_iso", {},
            f"detaching ISO from server {server_id}",
            "Waiting for ISO detachment to complete..."
        )

    # ------------------------------------------------------------------
    # Network Management Functions
    # ------------------------------------------------------------------

    def list_networks(self) -> List[Dict]:
        """List all networks in the project"""
        return self._get_list("networks", "networks", "listing networks")

    def get_network_by_id(self, network_id: int) -> Dict:
        """Get network by ID"""
        return self._get_resource(
            f"networks/{network_id}", "network",
            f"Network with ID {network_id}", f"getting network {network_id}"
        )

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

        return self._create_resource("networks", data, "network", f"creating network '{name}'")

    def delete_network(self, network_id: int) -> bool:
        """Delete a network by ID"""
        return self._delete_resource(f"networks/{network_id}", f"deleting network {network_id}")

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

        return self._update_resource(f"networks/{network_id}", data, "network", f"updating network {network_id}")

    def attach_server_to_network(self, network_id: int, server_id: int, ip: str = None, alias_ips: List[str] = None) -> bool:
        """Attach a server to a network"""
        data = {"network": network_id}

        if ip:
            data["ip"] = ip

        if alias_ips:
            data["alias_ips"] = alias_ips

        return self._run_action(
            f"servers/{server_id}/actions/attach_to_network", data,
            f"attaching server {server_id} to network {network_id}",
            "Waiting for network attachment to complete..."
        )

    def detach_server_from_network(self, network_id: int, server_id: int) -> bool:
        """Detach a server from a network"""
        return self._run_action(
            f"servers/{server_id}/actions/detach_from_network", {"network": network_id},
            f"detaching server {server_id} from network {network_id}",
            "Waiting for network detachment to complete..."
        )

    def add_subnet_to_network(self, network_id: int, network_zone: str, ip_range: str, type: str = "cloud") -> Dict:
        """Add a subnet to a network"""
        data = {
            "network_zone": network_zone,
            "ip_range": ip_range,
            "type": type
        }
        return self._create_resource(
            f"networks/{network_id}/actions/add_subnet", data, "network",
            f"adding subnet to network {network_id}"
        )

    def delete_subnet_from_network(self, network_id: int, ip_range: str) -> bool:
        """Delete a subnet from a network"""
        return self._run_action(
            f"networks/{network_id}/actions/delete_subnet", {"ip_range": ip_range},
            f"deleting subnet from network {network_id}"
        )

    def change_network_protection(self, network_id: int, delete: bool = None) -> Dict:
        """Change network protection settings"""
        data = {}

        if delete is not None:
            data["delete"] = delete

        if not data:
            print("No protection changes provided")
            return {}

        return self._create_resource(
            f"networks/{network_id}/actions/change_protection", data, "network",
            f"changing protection for network {network_id}"
        )

    # ------------------------------------------------------------------
    # Load Balancer Management Functions
    # ------------------------------------------------------------------

    def list_load_balancer_types(self) -> List[Dict]:
        """List all available load balancer types."""
        return self._get_list("load_balancer_types", "load_balancer_types", "listing load balancer types")

    def list_load_balancers(self) -> List[Dict]:
        """List all load balancers in the project."""
        return self._get_list("load_balancers", "load_balancers", "listing load balancers")

    def get_load_balancer_by_id(self, load_balancer_id: int) -> Dict:
        """Get load balancer details by ID."""
        return self._get_resource(
            f"load_balancers/{load_balancer_id}", "load_balancer",
            f"Load balancer with ID {load_balancer_id}", f"getting load balancer {load_balancer_id}"
        )

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

        return self._create_resource(
            "load_balancers", data, "load_balancer", f"creating load balancer '{name}'",
            wait_message="Waiting for load balancer creation to complete..."
        )

    def delete_load_balancer(self, load_balancer_id: int) -> bool:
        """Delete a load balancer by ID."""
        return self._delete_resource(
            f"load_balancers/{load_balancer_id}", f"deleting load balancer {load_balancer_id}"
        )

    def add_load_balancer_target(self, load_balancer_id: int, target: Dict) -> bool:
        """Add a target to a load balancer."""
        return self._run_action(
            f"load_balancers/{load_balancer_id}/actions/add_target", target,
            f"adding target to load balancer {load_balancer_id}",
            "Waiting for target attachment to complete..."
        )

    def remove_load_balancer_target(self, load_balancer_id: int, target: Dict) -> bool:
        """Remove a target from a load balancer."""
        return self._run_action(
            f"load_balancers/{load_balancer_id}/actions/remove_target", target,
            f"removing target from load balancer {load_balancer_id}",
            "Waiting for target removal to complete..."
        )

    # ------------------------------------------------------------------
    # Firewall Management Functions
    # ------------------------------------------------------------------

    def list_firewalls(self) -> List[Dict]:
        """List all firewalls in the project."""
        return self._get_list("firewalls", "firewalls", "listing firewalls")

    def get_firewall_by_id(self, firewall_id: int) -> Dict:
        """Get firewall details by ID."""
        return self._get_resource(
            f"firewalls/{firewall_id}", "firewall",
            f"Firewall with ID {firewall_id}", f"getting firewall {firewall_id}"
        )

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

        return self._create_resource("firewalls", data, "firewall", f"creating firewall '{name}'")

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

        return self._update_resource(f"firewalls/{firewall_id}", data, "firewall", f"updating firewall {firewall_id}")

    def delete_firewall(self, firewall_id: int) -> bool:
        """Delete a firewall by ID."""
        return self._delete_resource(f"firewalls/{firewall_id}", f"deleting firewall {firewall_id}")

    def set_firewall_rules(self, firewall_id: int, rules: List[Dict]) -> bool:
        """Replace firewall rules."""
        return self._run_action(
            f"firewalls/{firewall_id}/actions/set_rules", {"rules": rules},
            f"setting rules for firewall {firewall_id}",
            "Waiting for firewall rule update to complete..."
        )

    def apply_firewall_to_resources(self, firewall_id: int, resources: List[Dict]) -> bool:
        """Apply firewall to resources."""
        return self._run_action(
            f"firewalls/{firewall_id}/actions/apply_to_resources", {"apply_to": resources},
            f"applying firewall {firewall_id} to resources",
            "Waiting for firewall apply operation to complete..."
        )

    def remove_firewall_from_resources(self, firewall_id: int, resources: List[Dict]) -> bool:
        """Remove firewall from resources."""
        return self._run_action(
            f"firewalls/{firewall_id}/actions/remove_from_resources", {"remove_from": resources},
            f"removing firewall {firewall_id} from resources",
            "Waiting for firewall removal to complete..."
        )

    # ------------------------------------------------------------------
    # Floating IP Management Functions
    # ------------------------------------------------------------------

    def list_floating_ips(self) -> List[Dict]:
        """List all Floating IPs"""
        return self._get_list("floating_ips", "floating_ips", "listing floating IPs")

    def get_floating_ip_by_id(self, fip_id: int) -> Dict:
        """Get a Floating IP by ID"""
        return self._get_resource(
            f"floating_ips/{fip_id}", "floating_ip",
            f"Floating IP with ID {fip_id}", f"getting floating IP {fip_id}"
        )

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

        return self._create_resource("floating_ips", data, "floating_ip", f"creating floating IP '{name}'")

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

        return self._update_resource(f"floating_ips/{fip_id}", data, "floating_ip", f"updating floating IP {fip_id}")

    def delete_floating_ip(self, fip_id: int) -> bool:
        """Delete a Floating IP (must be unassigned)"""
        return self._delete_resource(f"floating_ips/{fip_id}", f"deleting floating IP {fip_id}")

    def assign_floating_ip(self, fip_id: int, server_id: int) -> bool:
        """Assign a Floating IP to a server"""
        return self._run_action(
            f"floating_ips/{fip_id}/actions/assign", {"server": server_id},
            f"assigning floating IP {fip_id} to server {server_id}",
            "Waiting for floating IP assignment..."
        )

    def unassign_floating_ip(self, fip_id: int) -> bool:
        """Unassign a Floating IP from its current server"""
        return self._run_action(
            f"floating_ips/{fip_id}/actions/unassign", {},
            f"unassigning floating IP {fip_id}",
            "Waiting for floating IP unassignment..."
        )

    def change_floating_ip_dns_ptr(self, fip_id: int, ip: str, dns_ptr: str = None) -> bool:
        """Set or reset reverse DNS for a Floating IP"""
        return self._run_action(
            f"floating_ips/{fip_id}/actions/change_dns_ptr", {"ip": ip, "dns_ptr": dns_ptr},
            f"updating rDNS for floating IP {fip_id}",
            "Waiting for rDNS update..."
        )

    def change_floating_ip_protection(self, fip_id: int, delete: bool) -> bool:
        """Enable or disable delete protection for a Floating IP"""
        return self._run_action(
            f"floating_ips/{fip_id}/actions/change_protection", {"delete": delete},
            f"changing protection for floating IP {fip_id}",
            "Waiting for protection change..."
        )

    # ------------------------------------------------------------------
    # Primary IP Management Functions
    # ------------------------------------------------------------------

    def list_primary_ips(self) -> List[Dict]:
        """List all Primary IPs"""
        return self._get_list("primary_ips", "primary_ips", "listing primary IPs")

    def get_primary_ip_by_id(self, pip_id: int) -> Dict:
        """Get a Primary IP by ID"""
        return self._get_resource(
            f"primary_ips/{pip_id}", "primary_ip",
            f"Primary IP with ID {pip_id}", f"getting primary IP {pip_id}"
        )

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

        return self._create_resource("primary_ips", data, "primary_ip", f"creating primary IP '{name}'")

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

        return self._update_resource(f"primary_ips/{pip_id}", data, "primary_ip", f"updating primary IP {pip_id}")

    def delete_primary_ip(self, pip_id: int) -> bool:
        """Delete a Primary IP (must be unassigned first)"""
        return self._delete_resource(f"primary_ips/{pip_id}", f"deleting primary IP {pip_id}")

    def assign_primary_ip(self, pip_id: int, server_id: int) -> bool:
        """Assign a Primary IP to a server"""
        return self._run_action(
            f"primary_ips/{pip_id}/actions/assign",
            {"assignee_id": server_id, "assignee_type": "server"},
            f"assigning primary IP {pip_id} to server {server_id}",
            "Waiting for primary IP assignment..."
        )

    def unassign_primary_ip(self, pip_id: int) -> bool:
        """Unassign a Primary IP from its current server"""
        return self._run_action(
            f"primary_ips/{pip_id}/actions/unassign", {},
            f"unassigning primary IP {pip_id}",
            "Waiting for primary IP unassignment..."
        )

    def change_primary_ip_dns_ptr(self, pip_id: int, ip: str, dns_ptr: str = None) -> bool:
        """Set or reset reverse DNS for a Primary IP"""
        return self._run_action(
            f"primary_ips/{pip_id}/actions/change_dns_ptr", {"ip": ip, "dns_ptr": dns_ptr},
            f"updating rDNS for primary IP {pip_id}",
            "Waiting for rDNS update..."
        )

    def change_primary_ip_protection(self, pip_id: int, delete: bool) -> bool:
        """Enable or disable delete protection for a Primary IP"""
        return self._run_action(
            f"primary_ips/{pip_id}/actions/change_protection", {"delete": delete},
            f"changing protection for primary IP {pip_id}",
            "Waiting for protection change..."
        )

    # ------------------------------------------------------------------
    # Image Management Functions
    # ------------------------------------------------------------------

    def list_images(self, image_type: str = None) -> List[Dict]:
        """List images, optionally filtered by type (snapshot, backup, system, app)"""
        endpoint = "images"
        if image_type:
            endpoint = f"images?type={image_type}"
        return self._get_list(endpoint, "images", "listing images")

    def get_image_by_id(self, image_id: int) -> Dict:
        """Get image details by ID"""
        return self._get_resource(
            f"images/{image_id}", "image",
            f"Image with ID {image_id}", f"getting image {image_id}"
        )

    def delete_image(self, image_id: int) -> bool:
        """Delete an image (only custom images can be deleted)"""
        return self._delete_resource(f"images/{image_id}", f"deleting image {image_id}")

    def update_image(self, image_id: int, description: str = None, labels: Dict = None) -> Dict:
        """Update image metadata (description and/or labels)"""
        data: Dict = {}
        if description is not None:
            data["description"] = description
        if labels is not None:
            data["labels"] = labels

        return self._update_resource(f"images/{image_id}", data, "image", f"updating image {image_id}")

    # ------------------------------------------------------------------
    # Load Balancer Service & Algorithm Functions
    # ------------------------------------------------------------------

    def add_lb_service(self, lb_id: int, service: Dict) -> bool:
        """Add a service to a load balancer"""
        return self._run_action(
            f"load_balancers/{lb_id}/actions/add_service", service,
            f"adding service to load balancer {lb_id}",
            "Waiting for service add to complete..."
        )

    def delete_lb_service(self, lb_id: int, listen_port: int) -> bool:
        """Delete a service from a load balancer by listen port"""
        return self._run_action(
            f"load_balancers/{lb_id}/actions/delete_service", {"listen_port": listen_port},
            f"deleting service (port {listen_port}) from load balancer {lb_id}",
            "Waiting for service deletion to complete..."
        )

    def update_lb_service(self, lb_id: int, service: Dict) -> bool:
        """Update a service on a load balancer"""
        return self._run_action(
            f"load_balancers/{lb_id}/actions/update_service", service,
            f"updating service on load balancer {lb_id}",
            "Waiting for service update to complete..."
        )

    def change_lb_algorithm(self, lb_id: int, algorithm: str) -> bool:
        """Change the algorithm of a load balancer (round_robin or least_connections)"""
        return self._run_action(
            f"load_balancers/{lb_id}/actions/change_algorithm", {"type": algorithm},
            f"changing algorithm for load balancer {lb_id}",
            "Waiting for algorithm change to complete..."
        )

    # ------------------------------------------------------------------
    # Location & Datacenter Functions
    # ------------------------------------------------------------------

    def list_locations(self) -> List[Dict]:
        """List all available locations"""
        return self._get_list("locations", "locations", "listing locations")

    def get_location_by_id(self, location_id: int) -> Dict:
        """Get location details by ID"""
        return self._get_resource(
            f"locations/{location_id}", "location",
            f"Location with ID {location_id}", f"getting location {location_id}"
        )

    def list_datacenters(self) -> List[Dict]:
        """List all available datacenters"""
        return self._get_list("datacenters", "datacenters", "listing datacenters")

    def get_datacenter_by_id(self, datacenter_id: int) -> Dict:
        """Get datacenter details by ID"""
        return self._get_resource(
            f"datacenters/{datacenter_id}", "datacenter",
            f"Datacenter with ID {datacenter_id}", f"getting datacenter {datacenter_id}"
        )
