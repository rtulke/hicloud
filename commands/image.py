#!/usr/bin/env python3
# commands/image.py - Image-related commands for hicloud

from typing import List


class ImageCommands:
    """Image management commands for Interactive Console."""

    def __init__(self, console):
        """Initialize with reference to the console."""
        self.console = console
        self.hetzner = console.hetzner

    def handle_command(self, args: List[str]):
        """Handle image-related commands."""
        if not args:
            print("Missing image subcommand. Use 'image list|info|delete|update|import'")
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            self.list_images(args[1:])
        elif subcommand == "info":
            self.show_image_info(args[1:])
        elif subcommand == "delete":
            self.delete_image(args[1:])
        elif subcommand == "update":
            self.update_image(args[1:])
        elif subcommand == "import":
            # Delegate to the vm_commands import wizard
            self.console.vm_commands.import_image_from_url(args[1:])
        else:
            print(f"Unknown image subcommand: {subcommand}")

    def list_images(self, args: List[str]):
        """List custom images (snapshots by default)."""
        image_type = "snapshot"
        if args:
            arg = args[0].lower()
            if arg in ("snapshot", "backup", "system", "app", "all"):
                image_type = None if arg == "all" else arg
            else:
                print(f"Unknown image type '{arg}'. Use snapshot|backup|system|app|all")
                return

        images = self.hetzner.list_images(image_type)
        if not images:
            label = image_type or "any"
            print(f"No images found (type: {label})")
            return

        headers = ["ID", "Name/Description", "Type", "OS", "Architecture", "Size (GB)", "Status"]
        rows = []

        for img in sorted(images, key=lambda x: x.get("id", 0)):
            img_id = img.get("id", "N/A")
            name = img.get("name") or img.get("description") or "N/A"
            img_type = img.get("type", "N/A")
            os_flavor = img.get("os_flavor", "N/A")
            arch = img.get("architecture", "N/A")
            size = img.get("image_size") or img.get("disk_size") or "-"
            status = img.get("status", "N/A")
            rows.append([img_id, name, img_type, os_flavor, arch, size, status])

        title = f"Images ({image_type or 'all'})"
        self.console.print_table(headers, rows, title)

    def show_image_info(self, args: List[str]):
        """Show detailed information about an image."""
        if not args:
            print("Missing image ID. Use 'image info <id>'")
            return

        try:
            image_id = int(args[0])
        except ValueError:
            print("Invalid image ID. Must be an integer.")
            return

        image = self.hetzner.get_image_by_id(image_id)
        if not image:
            return

        print(f"\n{self.console.horizontal_line('=')}")
        name = image.get("name") or image.get("description") or f"Image {image_id}"
        print(f"Image Information: \033[1;32m{name}\033[0m (ID: {image_id})")
        print(f"{self.console.horizontal_line('=')}")

        print(f"Type:          {image.get('type', 'N/A')}")
        print(f"Status:        {image.get('status', 'N/A')}")
        print(f"Architecture:  {image.get('architecture', 'N/A')}")
        print(f"OS Flavor:     {image.get('os_flavor', 'N/A')}")
        print(f"OS Version:    {image.get('os_version', 'N/A')}")

        size = image.get("image_size") or image.get("disk_size")
        if size is not None:
            print(f"Size:          {size} GB")

        print(f"Created:       {image.get('created', 'N/A')}")

        created_from = image.get("created_from")
        if created_from:
            print(f"Created From:  {created_from.get('name', 'N/A')} (ID: {created_from.get('id', 'N/A')})")

        if image.get("description"):
            print(f"Description:   {image['description']}")

        labels = image.get("labels", {})
        if labels:
            print("\nLabels:")
            for key, value in labels.items():
                print(f"  {key}: {value}")

        print(f"{self.console.horizontal_line('-')}")

    def delete_image(self, args: List[str]):
        """Delete a custom image by ID."""
        if not args:
            print("Missing image ID. Use 'image delete <id>'")
            return

        try:
            image_id = int(args[0])
        except ValueError:
            print("Invalid image ID. Must be an integer.")
            return

        image = self.hetzner.get_image_by_id(image_id)
        if not image:
            return

        name = image.get("name") or image.get("description") or f"Image {image_id}"
        img_type = image.get("type", "")
        if img_type not in ("snapshot", "backup"):
            print(f"Only custom images (snapshots/backups) can be deleted. This image is of type '{img_type}'.")
            return

        confirm = input(f"Delete image '{name}' (ID: {image_id})? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Operation cancelled")
            return

        if self.hetzner.delete_image(image_id):
            print(f"Image {image_id} deleted successfully")
        else:
            print(f"Failed to delete image {image_id}")

    def update_image(self, args: List[str]):
        """Interactively update image description and/or labels."""
        if not args:
            print("Missing image ID. Use 'image update <id>'")
            return

        try:
            image_id = int(args[0])
        except ValueError:
            print("Invalid image ID. Must be an integer.")
            return

        image = self.hetzner.get_image_by_id(image_id)
        if not image:
            return

        current_name = image.get("name") or image.get("description") or f"Image {image_id}"
        print(f"Updating image: {current_name} (ID: {image_id})")

        current_description = image.get("description", "")
        desc_prompt = f"New description [{current_description}]: " if current_description else "New description (leave blank to keep): "
        new_description = input(desc_prompt).strip()
        if not new_description:
            new_description = None

        update_labels = input("Update labels? [y/N]: ").strip().lower()
        new_labels = None
        if update_labels == "y":
            new_labels = {}
            print("Enter new labels (these will REPLACE all existing labels):")
            while True:
                key = input("Label key (or press Enter to finish): ").strip()
                if not key:
                    break
                value = input(f"Label value for '{key}': ").strip()
                new_labels[key] = value

        if new_description is None and new_labels is None:
            print("No changes provided. Skipping update.")
            return

        updated = self.hetzner.update_image(image_id, description=new_description, labels=new_labels)
        if updated:
            print(f"Image {image_id} updated successfully")
        else:
            print(f"Failed to update image {image_id}")
