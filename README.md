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
- **BATCH Processing**

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)

### Dependencies

Install the required dependencies using pip:

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

Pricing Commands:
  pricing list                      - Show pricing table for all resources
  pricing calculate                 - Calculate monthly costs for current resources
  
General Commands:
  keys list                         - List all SSH keys
  keys delete <id>                  - Delete an SSH key by ID
  history                           - Show command history
  history clear                     - Clear command history
  clear                             - Clear screen
  help                              - Show this help message
  exit, quit, q                     - Exit the program
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
│   └── keys.py              # SSH key commands
│
└── utils/                   # Utility modules
    ├── __init__.py
    ├── formatting.py        # Formatting helpers
    └── constants.py         # Global constants
```

## License

This project is licensed under the GPL-3.0 License.
