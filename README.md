# hicloud

hicloud is a interactive CLI console for managing Hetzner Cloud resources. It provides an interactive console with various commands for managing virtual machines, snapshots, backups, and more. And why? Because it's enough for most people and because it's faster than using complex commands a an argument since it works entirely with tab complition.

## Features

- **CLI Command Line Console with Autocompletion**
- **Manage Multiple Hetzner Projects**
- **VM Management**
- **Snapshot Management**
- **Backup Management**
- **Metrics Monitoring**
- **Project Management**
- **Pricing Information**
- **SSH Key Management**
- **Volume Management**
- **ISO Management**
- **Location & Datacenter Information**
- **BATCH Processing**

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)

### Dependencies

#### Option 1: Using Virtual Environment (Recommended)

Create and activate a virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

Or use the provided activation script:

```bash
source activate_hicloud.sh
```

#### Option 2: Global Installation

Install the required dependencies globally using pip:

```bash
pip install -r requirements.txt
```

### Configuration

Before using hicloud, you need to create a configuration file with your Hetzner Cloud API token. You can generate a sample configuration file using:

```bash
python hicloud.py --gen-config ~/.hicloud.toml
```

Then edit the generated file and replace the placeholder API token with your actual token:

```toml
[default]
api_token = "your_api_token_here"
project_name = "default"

[project1]
api_token = "project1_api_token"
project_name = "Production"

[project2]
api_token = "project2_api_token"
project_name = "Development"
```

Make sure to set the correct permissions for the configuration file:

```bash
chmod 600 ~/.hicloud.toml
```

## Usage

Start the interactive console:

```bash
python hicloud.py
```

To use a specific project from your configuration:

```bash
python hicloud.py --project project1
```

To use a one-time API token without creating a configuration file:

```bash
python hicloud.py --token your_api_token
```

### Interactive Console Commands

Once in the interactive console, type `help` to see all available commands:

```
VM Commands:
  vm list                           - List all VMs
  vm info <id>                      - Show detailed information about a VM
  vm create                         - Create a new VM (interactive)
  vm start <id>                     - Start a VM
  vm stop <id>                      - Stop a VM
  vm delete <id>                    - Delete a VM by ID
  vm resize <id> <type>             - Change server type
  vm rename <id> <name>             - Rename a VM
  vm rescue <id>                    - Enable rescue mode
  vm reset-password <id>            - Reset root password
  vm image <id> <name>              - Create custom image from VM
  
Snapshot Commands:
  snapshot list                     - List all snapshots or for specific VM
  snapshot create                   - Create a snapshot for a VM
  snapshot delete <id>              - Delete a snapshot by ID
  snapshot delete all               - Delete all snapshots for a VM
  snapshot rebuild <id> <sv>        - Rebuild a server from a snapshot
  
Backup Commands:
  backup list                       - List all backups or for specific VM
  backup enable <id> [WINDOW]       - Enable automatic backups for a VM
  backup disable <id>               - Disable automatic backups for a VM
  backup delete <id>                - Delete a backup by ID 
  
Monitoring Commands:
  metrics list <id>                 - List available metrics for a server
  metrics cpu <id> [--hours=24]     - Show CPU utilization metrics
  metrics traffic <id> [--days=7]   - Show network traffic metrics
  metrics disk <id> [--days=1]      - Show disk I/O metrics

Project Commands:
  project list                      - List all available projects
  project switch <n>                - Switch to a different project
  project resources                 - Show all resources in the current project
  project info                      - Show current project information
  
Batch Commands:
  batch start <id1,id2,id3...>      - Start multiple servers
  batch stop <id1,id2,id3...>       - Stop multiple servers
  batch delete <id1,id2,id3...>     - Delete multiple servers
  batch snapshot <id1,id2,id3...>   - Create snapshots for multiple servers

Volume Commands:
  volume list                       - List all volumes
  volume info <id>                  - Show detailed information about a volume
  volume create                     - Create a new volume (interactive)
  volume delete <id>                - Delete a volume by ID
  volume attach <vid> <sid>         - Attach volume to server
  volume detach <id>                - Detach volume from server
  volume resize <id> <size>         - Resize a volume (increase only)
  volume protect <id> <e|d>         - Enable/disable volume protection

Network Commands:
  network list                      - List all private networks
  network info <id>                 - Show detailed information about a network
  network create                    - Create a new private network (interactive)
  network update <id>               - Update network metadata (name, labels)
  network delete <id>               - Delete a network by ID
  network attach <nid> <sid> [ip]   - Attach server to network
  network detach <nid> <sid>        - Detach server from network
  network subnet add <id>           - Add a subnet to network
  network subnet delete <id> <ip>   - Remove a subnet from network
  network protect <id> <e|d>        - Enable/disable network protection

ISO Commands:
  iso list                          - List all available ISOs
  iso info <id>                     - Show detailed information about an ISO
  iso attach <iso_id> <server_id>   - Attach ISO to server
  iso detach <server_id>            - Detach ISO from server

Location & Datacenter Commands:
  location list                     - List all available locations
  location info <id>                - Show detailed information about a location
  datacenter list                   - List all available datacenters
  datacenter info <id>              - Show detailed information about a datacenter

Pricing Commands:
  pricing list                      - Show pricing table for all resources
  pricing calculate                 - Calculate monthly costs for current resources

General Commands:
  keys list                         - List all SSH keys
  keys info <id>                    - Show detailed information about an SSH key
  keys create [name] [file]         - Create/upload a new SSH key
  keys update <id>                  - Update SSH key metadata (name, labels)
  keys delete <id>                  - Delete an SSH key by ID
  history                           - Show command history
  history clear                     - Clear command history
  clear                             - Clear screen
  help [command]                    - Show help or detailed info about a command
  exit, quit, q, Ctrl-D             - Exit the program
```

### Context-Aware Help & Completion

- Use `help <command>` (for example `help vm`) to display all subcommands plus their syntax without leaving the console.
- Press <kbd>TAB</kbd> at any position to auto-complete commands, subcommands, and even resource identifiers; suggestions are derived live from Hetzner (server IDs, volume IDs, ISO IDs, etc.).
- When multiple options exist, hicloud prints the matching values above the prompt so you can keep typing without guessing argument order.

## Examples

### ISO Management

Mount an ISO image to install a custom operating system:

```bash
hicloud> iso list                    # List all available ISOs
hicloud> iso info 1234               # Show details about a specific ISO
hicloud> iso attach 1234 5678        # Attach ISO 1234 to server 5678
hicloud> iso detach 5678             # Detach ISO from server 5678
```

### Location & Datacenter Information

View available locations and datacenters before creating resources:

```bash
hicloud> location list               # List all locations (nbg1, fsn1, hel1, etc.)
hicloud> location info 1             # Show details: city, country, network zone
hicloud> datacenter list             # List all datacenters
hicloud> datacenter info 2           # Show datacenter details and supported server types
```

### Volume Management

Create and manage persistent storage volumes:

```bash
hicloud> volume create               # Interactive volume creation wizard
hicloud> volume list                 # List all volumes with attachment status
hicloud> volume attach 1234 5678     # Attach volume 1234 to server 5678
hicloud> volume resize 1234 50       # Increase volume size to 50 GB
hicloud> volume detach 1234          # Detach volume from server
```

### Network Management

Create and manage private networks for secure server communication:

```bash
hicloud> network list                # List all private networks
hicloud> network info 12345          # Show detailed network information
hicloud> network create              # Create new private network (interactive wizard)
hicloud> network attach 12345 5678   # Attach server 5678 to network 12345
hicloud> network detach 12345 5678   # Detach server from network
hicloud> network subnet add 12345    # Add a subnet to network
hicloud> network protect 12345 enable # Enable delete protection
```

### SSH Key Management

Manage SSH keys for secure server access:

```bash
hicloud> keys list                   # List all SSH keys with fingerprints
hicloud> keys info 12345             # Show detailed key information
hicloud> keys create mykey ~/.ssh/id_rsa.pub  # Upload SSH key from file
hicloud> keys update 12345           # Update key name or labels
hicloud> keys delete 12345           # Delete an SSH key
```

### Batch Operations

Perform operations on multiple servers at once:

```bash
hicloud> batch start 1,2,3           # Start multiple servers
hicloud> batch stop 1,2,3            # Stop multiple servers
hicloud> batch snapshot 1,2,3        # Create snapshots for multiple servers
hicloud> batch delete 1,2,3          # Delete multiple servers (with confirmation)
```

## Development

The project is structured as follows:

```
hicloud/
│
├── hicloud.py               # Main entry point
│
├── lib/                     # Core libraries
│   ├── __init__.py
│   ├── api.py               # HetznerCloudManager class
│   ├── config.py            # ConfigManager class
│   └── console.py           # InteractiveConsole class
│
├── commands/                # Command modules
│   ├── __init__.py
│   ├── vm.py                # VM commands
│   ├── snapshot.py          # Snapshot commands
│   ├── backup.py            # Backup commands
│   ├── metrics.py           # Metrics commands
│   ├── project.py           # Project commands
│   ├── pricing.py           # Pricing commands
│   ├── keys.py              # SSH key commands
│   ├── volume.py            # Volume commands
│   ├── batch.py             # Batch commands
│   ├── iso.py               # ISO commands
│   └── location.py          # Location & Datacenter commands
│
└── utils/                   # Utility modules
    ├── __init__.py
    ├── formatting.py        # Formatting helpers
    └── constants.py         # Global constants
```

## License

This project is licensed under the GPL-3.0 License.
