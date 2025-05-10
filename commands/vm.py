#!/usr/bin/env python3
# commands/vm.py - VM-related commands for hicloud

from typing import List

class VMCommands:
    """VM-related commands for Interactive Console"""
    
    def __init__(self, console):
        """Initialize with reference to the console"""
        self.console = console
        self.hetzner = console.hetzner
    
    def handle_command(self, args: List[str]):
        """Handle VM-related commands"""
        if not args:
            print("Missing VM subcommand. Use 'vm list|info|create|start|stop|delete|resize|rename|rescue|reset-password|image'")
            return
            
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.list_vms()
        elif subcommand == "info":
            self.show_vm_info(args[1:])
        elif subcommand == "create":
            self.create_vm()
        elif subcommand == "start":
            self.start_vm(args[1:])
        elif subcommand == "stop":
            self.stop_vm(args[1:])
        elif subcommand == "delete":
            self.delete_vm(args[1:])
        elif subcommand == "resize":
            self.resize_vm(args[1:])
        elif subcommand == "rename":
            self.rename_vm(args[1:])
        elif subcommand == "rescue":
            self.rescue_vm(args[1:])
        elif subcommand == "reset-password":
            self.reset_password(args[1:])
        elif subcommand == "image":
            self.create_image(args[1:])
        else:
            print(f"Unknown VM subcommand: {subcommand}")
    
    def list_vms(self):
        """List all VMs"""
        servers = self.hetzner.list_servers()
        
        if not servers:
            print("No VMs found")
            return
            
        # Daten für die Tabelle vorbereiten
        headers = ["ID", "Name", "Status", "Type", "IP", "DC"]
        rows = []
        
        for server in servers:
            ip = server.get("public_net", {}).get("ipv4", {}).get("ip", "N/A")
            rows.append([
                server['id'],
                server['name'],
                server['status'],
                server['server_type']['name'],
                ip,
                server['datacenter']['location']['name']
            ])
            
        # Tabelle drucken
        self.console.print_table(headers, rows, "Virtual Machines")
    
    def show_vm_info(self, args: List[str]):
        """Show detailed information about a specific VM"""
        if not args:
            print("Missing VM ID. Use 'vm info <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            # Die Fehlermeldung wird bereits in get_server_by_id ausgegeben
            return
            
        print(f"\n{self.console.horizontal_line('=')}")
        print(f"VM Information: \033[1;32m{server.get('name')}\033[0m (ID: {vm_id})")
        print(f"{self.console.horizontal_line('=')}")
        
        # Grundlegende Informationen
        status = server.get('status', 'unknown')
        status_color = "\033[1;32m" if status == "running" else "\033[1;31m" if status == "off" else "\033[1;33m"
        print(f"Status: {status_color}{status}\033[0m")
        created = server.get('created', 'unknown')
        if created != 'unknown':
            created_date = created.split('T')[0]
            created_time = created.split('T')[1].split('+')[0] if '+' in created else created.split('T')[1].split('Z')[0]
            print(f"Created: {created_date} {created_time}")
        
        # Hardware-Informationen
        print("\nHardware:")
        server_type = server.get('server_type', {})
        print(f"  Type: {server_type.get('name', 'N/A')}")
        print(f"  CPU Cores: {server_type.get('cores', 'N/A')}")
        print(f"  Memory: {server_type.get('memory', 'N/A')} GB")
        print(f"  Disk: {server_type.get('disk', 'N/A')} GB")
        
        # Standort-Informationen
        print("\nLocation:")
        datacenter = server.get('datacenter', {})
        location = datacenter.get('location', {})
        print(f"  Datacenter: {datacenter.get('name', 'N/A')}")
        print(f"  City: {location.get('city', 'N/A')}")
        print(f"  Country: {location.get('country', 'N/A')}")
        
        # Netzwerkinformationen
        print("\nNetwork:")
        public_net = server.get('public_net', {})
        ipv4 = public_net.get('ipv4', {})
        ipv6 = public_net.get('ipv6', {})
        print(f"  IPv4: {ipv4.get('ip', 'N/A')}")
        print(f"  IPv6: {ipv6.get('ip', 'N/A')}")
        
        # DNS-Einträge
        dns_ptr = []
        for entry in public_net.get('dns_ptr', []):
            dns_ptr.append(f"{entry.get('ip', 'N/A')} -> {entry.get('dns_ptr', 'N/A')}")
        if dns_ptr:
            print("\nDNS Reverse Records:")
            for entry in dns_ptr:
                print(f"  {entry}")
        
        # Volumes
        try:
            status_code, volumes_response = self.hetzner._make_request("GET", f"servers/{vm_id}/volumes")
            if status_code == 200:
                volumes = volumes_response.get('volumes', [])
                if volumes:
                    print("\nAttached Volumes:")
                    for vol in volumes:
                        print(f"  {vol.get('name', 'N/A')} ({vol.get('size', 'N/A')} GB)")
        except Exception:
            pass
        
        # Backup-Status
        backup_window = server.get('backup_window', 'disabled')
        if backup_window != 'disabled':
            print(f"\nBackup: Enabled (Window: {backup_window})")
        else:
            print("\nBackup: Disabled")
        
        # Image-Informationen
        print("\nImage Information:")
        image = server.get('image', {})
        print(f"  OS: {image.get('name', 'N/A')}")
        print(f"  Description: {image.get('description', 'N/A')}")
        
        # Protection-Informationen
        protection = server.get('protection', {})
        if protection:
            delete_protection = "Enabled" if protection.get('delete', False) else "Disabled"
            rebuild_protection = "Enabled" if protection.get('rebuild', False) else "Disabled"
            print("\nProtection:")
            print(f"  Delete Protection: {delete_protection}")
            print(f"  Rebuild Protection: {rebuild_protection}")
        
        # Preisberechnung (wenn verfügbar)
        try:
            status_code, pricing = self.hetzner._make_request("GET", "pricing")
            if status_code == 200:
                server_prices = pricing.get('pricing', {}).get('server_types', [])
                for price in server_prices:
                    if price.get('id') == server_type.get('id'):
                        price_monthly = price.get('prices', [{}])[0].get('price_monthly', {}).get('gross', 'N/A')
                        price_hourly = price.get('prices', [{}])[0].get('price_hourly', {}).get('gross', 'N/A')
                        if price_monthly != 'N/A' or price_hourly != 'N/A':
                            print("\nPricing:")
                            if price_monthly != 'N/A':
                                print(f"  Monthly: {price_monthly} €")
                            if price_hourly != 'N/A':
                                print(f"  Hourly: {price_hourly} €")
        except Exception:
            pass
            
        print(f"{self.console.horizontal_line('-')}")
    
    def create_vm(self):
        """Create a new VM (interactive)"""
        print("Create a new VM:")
        name = input("Name: ")
        if not name:
            print("Name is required")
            return
            
        # Get available server types
        status_code, response = self.hetzner._make_request("GET", "server_types")
        if status_code != 200:
            print("Failed to get server types")
            return
            
        server_types = response.get("server_types", [])
        
        # Gruppiere nach Servertyp-Präfixen (unabhängig von Groß-/Kleinschreibung)
        server_type_groups = {
            "CAX": {"name": "ARM64 (shared vCPU)", "types": []},
            "CCX": {"name": "x86 AMD (dedicated vCPU)", "types": []},
            "CPX": {"name": "x86 AMD (shared vCPU)", "types": []},
            "CX": {"name": "x86 Intel (shared vCPU)", "types": []}
        }
        
        # Andere Typen
        other_types = []
        
        # Sortiere Server-Typen nach Gruppen (unabhängig von Groß-/Kleinschreibung)
        for st in server_types:
            st_name = st.get("name", "").upper()  # Konvertiere zu Großbuchstaben für Vergleich
            for prefix in server_type_groups.keys():
                if st_name.startswith(prefix):
                    server_type_groups[prefix]["types"].append(st)
                    break
            else:
                other_types.append(st)
        
        # Zeige Server-Typen nach Gruppe an
        print("\nAvailable Server Types:")
        print("-" * 80)
        
        type_options = []
        option_index = 1
        
        for prefix, group in server_type_groups.items():
            if group["types"]:
                print(f"\n{group['name']}:")
                for st in sorted(group["types"], key=lambda x: x.get("memory", 0)):
                    cores = st.get("cores", "N/A")
                    memory = st.get("memory", "N/A")
                    disk = st.get("disk", "N/A")
                    price_info = ""
                    try:
                        # Hetzner Preise sind in € pro Monat
                        price = float(st.get("prices", [{}])[0].get("price_monthly", {}).get("gross", 0))
                        if price > 0:
                            price_info = f", {price:.2f}€/mo"
                    except:
                        pass

                    print(f"{option_index}. {st['name']} (Cores: {cores}, Memory: {memory} GB, Disk: {disk} GB{price_info})")
                    type_options.append(st)
                    option_index += 1

        # Andere Typen, falls vorhanden
        if other_types:
            print("\nOther Types:")
            for st in other_types:
                cores = st.get("cores", "N/A")
                memory = st.get("memory", "N/A")
                disk = st.get("disk", "N/A")
                print(f"{option_index}. {st['name']} (Cores: {cores}, Memory: {memory} GB, Disk: {disk} GB)")
                type_options.append(st)
                option_index += 1

        type_choice = input("\nSelect server type (number): ")
        try:
            type_index = int(type_choice) - 1
            if type_index < 0 or type_index >= len(type_options):
                print("Invalid selection")
                return
            server_type = type_options[type_index]["name"]
        except ValueError:
            print("Invalid input")
            return

        # Get available images
        status_code, response = self.hetzner._make_request("GET", "images?type=system")
        if status_code != 200:
            print("Failed to get images")
            return

        images = response.get("images", [])
        system_images = [img for img in images if img.get("type") == "system"]

        print("\nAvailable Images:")
        for i, img in enumerate(system_images):
            print(f"{i+1}. {img['name']} ({img['description']})")

        image_choice = input("\nSelect image (number): ")
        try:
            image_index = int(image_choice) - 1
            if image_index < 0 or image_index >= len(system_images):
                print("Invalid selection")
                return
            image = system_images[image_index]["name"]
        except ValueError:
            print("Invalid input")
            return

        # Get available locations
        status_code, response = self.hetzner._make_request("GET", "locations")
        if status_code != 200:
            print("Failed to get locations")
            return

        locations = response.get("locations", [])
        print("\nAvailable Locations:")
        for i, loc in enumerate(locations):
            print(f"{i+1}. {loc['name']} ({loc['description']})")

        location_choice = input("\nSelect location (number): ")
        try:
            location_index = int(location_choice) - 1
            if location_index < 0 or location_index >= len(locations):
                print("Invalid selection")
                return
            location = locations[location_index]["name"]
        except ValueError:
            print("Invalid input")
            return

        # Get SSH keys
        status_code, response = self.hetzner._make_request("GET", "ssh_keys")
        ssh_keys = []

        if status_code == 200:
            available_keys = response.get("ssh_keys", [])
            if available_keys:
                print("\nAvailable SSH Keys:")
                for i, key in enumerate(available_keys):
                    print(f"{i+1}. {key['name']}")

                keys_choice = input("\nSelect SSH keys (comma-separated numbers or 'none'): ")
                if keys_choice.lower() != "none":
                    try:
                        key_indices = [int(idx.strip()) - 1 for idx in keys_choice.split(",")]
                        ssh_keys = [available_keys[idx]["id"] for idx in key_indices if 0 <= idx < len(available_keys)]
                    except ValueError:
                        print("Invalid input, proceeding without SSH keys")

        # IP-Version auswählen
        print("\nIP Version:")
        print("1. IPv4 only")
        print("2. IPv6 only")
        print("3. Both IPv4 and IPv6 (default)")

        ip_choice = input("\nSelect IP version (number, default: 3): ").strip()

        ipv4 = True
        ipv6 = True

        if ip_choice == "1":
            ipv6 = False
        elif ip_choice == "2":
            ipv4 = False
        elif ip_choice != "" and ip_choice != "3":
            print("Invalid selection, using both IPv4 and IPv6")

        # Option für Root-Passwort
        generate_password = input("\nDo you want to set a root password? [y/N]: ").strip().lower()
        use_auto_password = generate_password == 'y'

        # Final confirmation
        print("\nVM Creation Summary:")
        print(f"  Name: {name}")
        print(f"  Type: {server_type}")
        print(f"  Image: {image}")
        print(f"  Location: {location}")
        print(f"  SSH Keys: {', '.join(str(k) for k in ssh_keys) if ssh_keys else 'None'}")
        print(f"  Network: {'IPv4' if ipv4 else ''}{' and ' if ipv4 and ipv6 else ''}{'IPv6' if ipv6 else ''}")
        print(f"  Root Password: {'Auto-generated' if use_auto_password else 'None'}")

        confirm = input("\nCreate this VM? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return

        print("Creating VM...")

        # VM erstellen
        server = self.hetzner.create_server(
            name=name,
            server_type=server_type,
            image=image,
            location=location,
            ssh_keys=ssh_keys,
            ipv4=ipv4,
            ipv6=ipv6,
            auto_password=use_auto_password
        )

        if server:
            print(f"\nVM created successfully!")
            print(f"ID: {server.get('id')}")
            print(f"Name: {server.get('name')}")
            print(f"Status: {server.get('status')}")

            # IP-Adressen anzeigen
            public_net = server.get("public_net", {})
            if ipv4:
                ipv4_info = public_net.get("ipv4", {})
                print(f"IPv4: {ipv4_info.get('ip', 'N/A')}")
            if ipv6:
                ipv6_info = public_net.get("ipv6", {})
                print(f"IPv6: {ipv6_info.get('ip', 'N/A')}")

            # Root-Passwort anzeigen, wenn generiert
            if use_auto_password:
                # Bei direkter API-Anfrage bekommen wir das Passwort zurück
                # Aber in diesem Fall verwenden wir die create_server-Methode, die das Passwort nicht zurückgibt
                print("\nCheck your email or Hetzner Cloud Console for the root password.")
                print("\nYou can use: “vm list” to display all vms.")

        else:
            print(f"Failed to create VM")
    
    def start_vm(self, args: List[str]):
        """Start a VM by ID"""
        if not args:
            print("Missing VM ID. Use 'vm start <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            print(f"VM with ID {vm_id} not found")
            return
            
        if server.get("status") == "running":
            print(f"VM '{server.get('name')}' is already running")
            return
            
        print(f"Starting VM '{server.get('name')}' (ID: {vm_id})...")
        if self.hetzner.start_server(vm_id):
            print(f"VM {vm_id} started successfully")
        else:
            print(f"Failed to start VM {vm_id}")
    
    def stop_vm(self, args: List[str]):
        """Stop a VM by ID"""
        if not args:
            print("Missing VM ID. Use 'vm stop <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            print(f"VM with ID {vm_id} not found")
            return
            
        if server.get("status") == "off":
            print(f"VM '{server.get('name')}' is already stopped")
            return
            
        print(f"Stopping VM '{server.get('name')}' (ID: {vm_id})...")
        if self.hetzner.stop_server(vm_id):
            print(f"VM {vm_id} stopped successfully")
        else:
            print(f"Failed to stop VM {vm_id}")
    
    def delete_vm(self, args: List[str]):
        """Delete a VM by ID"""
        if not args:
            print("Missing VM ID. Use 'vm delete <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        server = self.hetzner.get_server_by_id(vm_id)
        
        if not server:
            print(f"VM with ID {vm_id} not found")
            return
            
        confirm = input(f"Are you sure you want to delete VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
        
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        print(f"Deleting VM {vm_id}...")
        if self.hetzner.delete_server(vm_id):
            print(f"VM {vm_id} deleted successfully")
        else:
            print(f"Failed to delete VM {vm_id}")
    
    def resize_vm(self, args: List[str]):
        """Change the server type of a VM"""
        if len(args) < 2:
            print("Missing parameters. Use 'vm resize <id> <new_type>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        new_type = args[1]
        
        # Get server details
        server = self.hetzner.get_server_by_id(vm_id)
        if not server:
            return
            
        # Get available server types
        status_code, response = self.hetzner._make_request("GET", "server_types")
        if status_code != 200:
            print("Failed to get server types")
            return
            
        server_types = response.get("server_types", [])
        type_names = [st["name"] for st in server_types]
        
        # Validate the new type
        if new_type not in type_names:
            print(f"Invalid server type: {new_type}")
            print("Available types:")
            for type_name in sorted(type_names):
                print(f"  - {type_name}")
            return
            
        # Show warning about upgrade/downgrade implications
        current_type = server.get("server_type", {}).get("name", "unknown")
        print(f"\nWARNING:")
        print(f"You are about to change the server type of VM '{server.get('name')}' (ID: {vm_id})")
        print(f"from {current_type} to {new_type}.")
        print("\nThis operation requires the server to be powered off.")
        print("All your data will be preserved, but the server will be unavailable during the operation.")
        print("This may take several minutes to complete.")
        
        # Security check
        confirm = input(f"\nAre you sure you want to resize VM '{server.get('name')}' (ID: {vm_id}) to {new_type}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Check if server is running and needs to be powered off
        if server.get("status") == "running":
            print(f"VM '{server.get('name')}' is currently running and needs to be powered off.")
            confirm_stop = input("Do you want to power off the VM now? [y/N]: ")
            if confirm_stop.lower() != 'y':
                print("Operation cancelled")
                return
                
            # Stop the server
            print(f"Stopping VM {vm_id}...")
            if not self.hetzner.stop_server(vm_id):
                print("Failed to stop VM. Operation cancelled.")
                return
                
            # Wait a bit for the server to be fully stopped
            print("Waiting for VM to stop completely...")
            import time
            time.sleep(5)
            
        # Resize the server
        print(f"Resizing VM '{server.get('name')}' to {new_type}...")
        if self.hetzner.resize_server(vm_id, new_type):
            print(f"VM {vm_id} successfully resized to {new_type}")
            
            # Ask if user wants to start the server again
            start_again = input("Do you want to start the VM now? [y/N]: ")
            if start_again.lower() == 'y':
                print(f"Starting VM {vm_id}...")
                if self.hetzner.start_server(vm_id):
                    print(f"VM {vm_id} started successfully")
                else:
                    print(f"Failed to start VM {vm_id}")
        else:
            print(f"Failed to resize VM {vm_id}")
    
    def rename_vm(self, args: List[str]):
        """Rename a VM"""
        if len(args) < 2:
            print("Missing parameters. Use 'vm rename <id> <new_name>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        new_name = args[1]
        
        # Get server details
        server = self.hetzner.get_server_by_id(vm_id)
        if not server:
            return
            
        # Security check
        old_name = server.get("name", "unknown")
        confirm = input(f"Are you sure you want to rename VM '{old_name}' (ID: {vm_id}) to '{new_name}'? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Rename the server
        print(f"Renaming VM '{old_name}' to '{new_name}'...")
        if self.hetzner.rename_server(vm_id, new_name):
            print(f"VM {vm_id} successfully renamed to '{new_name}'")
        else:
            print(f"Failed to rename VM {vm_id}")
    
    def rescue_vm(self, args: List[str]):
        """Enable rescue mode for a VM"""
        if not args:
            print("Missing VM ID. Use 'vm rescue <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        # Get server details
        server = self.hetzner.get_server_by_id(vm_id)
        if not server:
            return
            
        # Check if server needs to be powered off
        if server.get("status") == "running":
            print(f"WARNING: VM '{server.get('name')}' is currently running.")
            print("Enabling rescue mode does not automatically reboot the server.")
            print("You will need to trigger a reboot manually after rescue mode is enabled.")
            
        # Show rescue mode options
        print("\nRescue Mode Options:")
        print("1. linux64 (Default)")
        print("2. linux32")
        print("3. freebsd64")
        
        mode_choice = input("\nSelect rescue mode (number, default: 1): ").strip()
        rescue_type = "linux64"  # Default
        
        if mode_choice == "2":
            rescue_type = "linux32"
        elif mode_choice == "3":
            rescue_type = "freebsd64"
            
        # Security check
        confirm = input(f"\nAre you sure you want to enable {rescue_type} rescue mode for VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Enable rescue mode
        print(f"Enabling {rescue_type} rescue mode for VM {vm_id}...")
        rescue_result = self.hetzner.enable_rescue_mode(vm_id, rescue_type)
        
        if rescue_result and "root_password" in rescue_result:
            print(f"Rescue mode enabled successfully for VM {vm_id}")
            print(f"Root password: {rescue_result['root_password']}")
            print("\nIMPORTANT: Save this password, it will not be shown again!")
            print("To enter rescue mode, you need to reboot the server.")
            
            # Ask if user wants to reboot now
            reboot = input("\nDo you want to reboot the VM now to enter rescue mode? [y/N]: ")
            if reboot.lower() == 'y':
                print(f"Rebooting VM {vm_id}...")
                if self.hetzner.reboot_server(vm_id):
                    print(f"VM {vm_id} is rebooting into rescue mode")
                else:
                    print(f"Failed to reboot VM {vm_id}")
        else:
            print(f"Failed to enable rescue mode for VM {vm_id}")
    
    def reset_password(self, args: List[str]):
        """Reset the root password of a VM"""
        if not args:
            print("Missing VM ID. Use 'vm reset-password <id>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        # Get server details
        server = self.hetzner.get_server_by_id(vm_id)
        if not server:
            return
            
        # Security check
        print("\nWARNING:")
        print("Resetting the root password will generate a new random password.")
        print("Any existing password will no longer work.")
        print("The server needs to be powered on for this operation.")
        
        confirm = input(f"Are you sure you want to reset the root password for VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Check if server is powered on
        if server.get("status") != "running":
            print(f"VM '{server.get('name')}' is not running. Starting it now...")
            if not self.hetzner.start_server(vm_id):
                print("Failed to start VM. Cannot reset password.")
                return
                
            # Wait a bit for the server to start
            print("Waiting for VM to start completely...")
            import time
            time.sleep(10)
            
        # Reset password
        print(f"Resetting root password for VM {vm_id}...")
        password_result = self.hetzner.reset_server_password(vm_id)
        
        if password_result and "root_password" in password_result:
            print(f"Root password reset successful for VM {vm_id}")
            print(f"New root password: {password_result['root_password']}")
            print("\nIMPORTANT: Save this password, it will not be shown again!")
        else:
            print(f"Failed to reset root password for VM {vm_id}")
    
    def create_image(self, args: List[str]):
        """Create a custom image from a server"""
        if len(args) < 2:
            print("Missing parameters. Use 'vm image <id> <name>'")
            return
            
        try:
            vm_id = int(args[0])
        except ValueError:
            print("Invalid VM ID. Must be an integer.")
            return
            
        image_name = args[1]
        
        # Get server details
        server = self.hetzner.get_server_by_id(vm_id)
        if not server:
            return
            
        # Security check
        print("\nWARNING:")
        print(f"Creating an image from VM '{server.get('name')}' (ID: {vm_id})")
        print("This operation could take a while depending on the server's disk size.")
        print("It is recommended to shut down the server before creating an image to ensure data consistency.")
        
        # Check if server is running
        if server.get("status") == "running":
            shut_down = input("VM is currently running. Do you want to shut it down before creating the image? [Y/n]: ")
            if shut_down.lower() != 'n':
                print(f"Stopping VM {vm_id}...")
                if not self.hetzner.stop_server(vm_id):
                    print("Failed to stop VM.")
                    continue_anyway = input("Continue with image creation anyway? [y/N]: ")
                    if continue_anyway.lower() != 'y':
                        print("Operation cancelled")
                        return
                else:
                    # Wait a bit for the server to stop
                    print("Waiting for VM to stop completely...")
                    import time
                    time.sleep(5)
        
        # Final confirmation
        confirm = input(f"Create image '{image_name}' from VM '{server.get('name')}' (ID: {vm_id})? [y/N]: ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            return
            
        # Create image
        print(f"Creating image '{image_name}' from VM {vm_id}...")
        image_result = self.hetzner.create_image(vm_id, image_name)
        
        if image_result and "id" in image_result:
            print(f"Image created successfully with ID {image_result['id']}")
            
            # Ask if user wants to start the server again
            if server.get("status") == "off":
                start_again = input("Do you want to start the VM now? [y/N]: ")
                if start_again.lower() == 'y':
                    print(f"Starting VM {vm_id}...")
                    if self.hetzner.start_server(vm_id):
                        print(f"VM {vm_id} started successfully")
                    else:
                        print(f"Failed to start VM {vm_id}")
        else:
            print(f"Failed to create image from VM {vm_id}")
