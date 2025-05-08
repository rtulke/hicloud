# HiCloud

A powerful, interactive command-line tool for managing Hetzner Cloud resources. With hicloud, you can create and manage VMs, create snapshots and backups, and perform many other actions - all from the command line.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Interactive Console](#interactive-console)
- [Command Reference](#command-reference)
  - [VM Commands](#vm-commands)
  - [Snapshot Commands](#snapshot-commands)
  - [Backup Commands](#backup-commands)
  - [General Commands](#general-commands)
- [Advanced Features](#advanced-features)
  - [Tab Completion](#tab-completion)
  - [Command History](#command-history)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Installation

### System Requirements

- Python 3.6 or higher
- pip (Python package manager)
- Hetzner Cloud API token

### Installation of Required Packages

```bash
# Linux/macOS
pip install requests toml

# Windows
pip install requests toml pyreadline3
```

### Installation of hicloud

```bash
# Clone repository
git clone https://github.com/rtulke/hicloud.git
cd hicloud

# Make script executable
chmod +x hicloud.py

# Optional: Make available system-wide
sudo ln -s $(pwd)/hicloud.py /usr/local/bin/hicloud
```

### Usage with virtualenv (recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment (Linux/macOS)
source venv/bin/activate

# Activate environment (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install requests toml
```

## Configuration

hicloud uses TOML configuration files to store API tokens and project settings.

### Generating an Example Configuration

```bash
./hicloud.py --gen-config ~/.hicloud.toml
```

This command creates an example configuration file with the correct permissions (chmod 600).

### Configuration Format

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

### Security Notes

- The configuration file must be protected with 600 permissions (`chmod 600 ~/.hicloud.toml`)
- The API token grants full access to your Hetzner Cloud resources
- It is recommended to use tokens with limited permissions

## Interactive Console

hicloud provides an interactive console for managing your Hetzner Cloud resources.

### Starting the Interactive Console

```bash
# Use default configuration (~/.hicloud.toml)
./hicloud.py

# Specify a specific configuration file
./hicloud.py --config myproject.toml

# Use a specific project from the configuration file
./hicloud.py --project project1

# Pass API token directly (bypasses configuration file)
./hicloud.py --token your_api_token_here
```

### Console Features

- Colored output for better readability
- Tab completion for commands and subcommands
- Command history with arrow key navigation
- Contextual help
- Confirmation prompts for critical operations

## Command Reference

### VM Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| vm list | Lists all VMs | none | `vm list` |
| vm info \<id\> | Shows detailed information about a VM | \<id\>: ID of the VM | `vm info 123456` |
| vm create | Starts the interactive VM creation process | none | `vm create` |
| vm start \<id\> | Starts a VM | \<id\>: ID of the VM | `vm start 123456` |
| vm stop \<id\> | Stops a VM | \<id\>: ID of the VM | `vm stop 123456` |
| vm delete \<id\> | Deletes a VM | \<id\>: ID of the VM | `vm delete 123456` |

#### VM Creation Options

When running `vm create`, the following options are requested:

| Option | Description |
|--------|-------------|
| Name | The name of the VM |
| Server Type | CPU cores, RAM and disk size |
| Image | Operating system (e.g., Ubuntu, Debian, CentOS) |
| Location | Data center (e.g., Nuremberg, Helsinki, Falkenstein) |
| SSH Keys | SSH keys for access (optional) |
| IP Version | IPv4, IPv6, or both |
| Root Password | Automatically generated root password (optional) |

### Snapshot Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| snapshot list | Lists all snapshots | none | `snapshot list` |
| snapshot create \<id\> | Creates a snapshot of a VM | \<id\>: ID of the VM | `snapshot create 123456` |
| snapshot delete \<id\> | Deletes a snapshot | \<id\>: ID of the snapshot | `snapshot delete 987654` |
| snapshot delete all \<id\> | Deletes all snapshots of a VM | \<id\>: ID of the VM | `snapshot delete all 123456` |

### Backup Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| backup list | Lists all backups | none | `backup list` |
| backup enable \<id\> [WINDOW] | Enables automatic backups for a VM | \<id\>: ID of the VM<br>[WINDOW]: Backup window (optional) | `backup enable 123456 22-02` |
| backup disable \<id\> | Disables automatic backups for a VM | \<id\>: ID of the VM | `backup disable 123456` |
| backup delete \<id\> | Deletes a backup | \<id\>: ID of the backup | `backup delete 987654` |

#### Backup Windows

When enabling automatic backups, you can specify a backup window:

| Window | Time Frame (UTC) |
|--------|------------------|
| 22-02 | 22:00 - 02:00 |
| 02-06 | 02:00 - 06:00 |
| 06-10 | 06:00 - 10:00 |
| 10-14 | 10:00 - 14:00 |
| 14-18 | 14:00 - 18:00 |
| 18-22 | 18:00 - 22:00 |

### General Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| project, info | Shows information about the current project | none | `project` |
| history | Shows the command history | none | `history` |
| history clear | Clears the command history | none | `history clear` |
| clear | Clears the screen | none | `clear` |
| help | Shows help information | none | `help` |
| exit, quit, q | Exits the program | none | `exit` |

## Advanced Features

### Tab Completion

hicloud provides comprehensive tab completion support:

- Main commands: Press \<Tab\> to display available commands
  ```
  hicloud> <Tab>
  backup  clear   exit    help    history info    project quit    q       snapshot vm
  ```

- Subcommands: After entering a main command, \<Tab\> shows available subcommands
  ```
  hicloud> vm <Tab>
  create  delete  info    list    start   stop
  ```

- Partial word search: Enter the beginning of a command and press \<Tab\>
  ```
  hicloud> vm st<Tab>
  start   stop
  ```

- Contextual help: When completing, hints about the command are displayed
  ```
  hicloud> vm <Tab>
  VM commands: list, info <id>, create, start <id>, stop <id>, delete <id>
  ```

### Command History

hicloud stores your command history in `~/.tmp/hicloud/history`:

- Navigation: Use the arrow keys ↑ and ↓ to navigate through previous commands
- Display: With `history` you can display the entire command history
- Clear: With `history clear` you can clear the command history
- Persistence: The history is saved between sessions (maximum 1000 commands)

## Examples

### VM Management

```
# Display VM list
hicloud> vm list
Virtual Machines:
ID         Name                           Status     Type            IP              Location
------------------------------------------------------------------------------------------
123456     web-server                     running    cx21            203.0.113.10    nbg1

# Create VM
hicloud> vm create
Name: new-server
...

# Start VM
hicloud> vm start 123456
Starting VM 'web-server' (ID: 123456)...
Waiting for server to start...
.........
VM 123456 started successfully

# Stop VM
hicloud> vm stop 123456
Stopping VM 'web-server' (ID: 123456)...
Waiting for server to stop...
.........
VM 123456 stopped successfully

# Display VM details
hicloud> vm info 123456
...
```

### Snapshot Management

```
# Create snapshot
hicloud> snapshot create 123456
Creating snapshot for VM 'web-server' (ID: 123456)...
Waiting for snapshot creation to complete...
.........
Snapshot created successfully with ID 987654

# Display snapshots
hicloud> snapshot list
Snapshots:
ID         Name                                                  Created             Size         Server ID
-----------------------------------------------------------------------------------------------------------
987654     web-server snapshot                                   2025-05-08T15:32:45 35.50 GB     123456

# Delete snapshot
hicloud> snapshot delete 987654
Are you sure you want to delete snapshot 987654? [y/N]: y
Deleting snapshot 987654...
Snapshot 987654 deleted successfully
```

### Backup Management

```
# Display backups
hicloud> backup list
Backups:
ID         Name                                                  Created             Size         Server ID
-----------------------------------------------------------------------------------------------------------
123789     web-server backup                                     2025-05-08T02:15:30 15.25 GB     123456

# Enable automatic backups
hicloud> backup enable 123456 22-02
Enabling automatic backups for VM 'web-server' (ID: 123456)...
Waiting for backup enablement to complete...
.........
Automatic backups enabled successfully for VM 123456

# Disable automatic backups
hicloud> backup disable 123456
Disabling automatic backups for VM 'web-server' (ID: 123456)...
Waiting for backup disablement to complete...
.........
Automatic backups disabled successfully for VM 123456
```

### Project Information

```
hicloud> project
Project Information: Production
============================================================
Connection Status: Connected
API Endpoint: https://api.hetzner.cloud/v1

Resources:
  VMs: 5 total, 3 running
  Snapshots: 12
  Datacenters: 6
  Available Locations:
    - fsn1 (Falkenstein DC Park 1)
    - nbg1 (Nuremberg DC Park 1)
    - hel1 (Helsinki DC Park 1)
    - ash (Ashburn, VA)
    - hil (Hillsboro, OR)
    - sin (Singapore)
  Networks: 2
  SSH Keys: 3
```

## Troubleshooting

### Common Problems

| Problem | Solution |
|---------|----------|
| "No configuration file found" | Create a configuration file with `--gen-config` or provide a token directly with `--token` |
| "Insecure permissions on ~/.hicloud.toml" | Set the correct permissions with `chmod 600 ~/.hicloud.toml` |
| "Connection Status: Error" | Check your API token and your internet connection |
| "No VMs found" | Make sure you have selected the correct project |
| Tab completion doesn't work | On Windows, install pyreadline3 with `pip install pyreadline3` |
| History directory could not be created | Check write permissions in your home directory |

### Debugging

- Use `--token` to bypass the configuration file and work directly with a token
- Check the permissions of the API token in the Hetzner Cloud Console
- If you have problems with the command history, delete the folder `~/.tmp/hicloud` and restart

## License

This project is licensed under the MIT License - see LICENSE for details.
