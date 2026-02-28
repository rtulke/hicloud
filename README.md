# hicloud

hicloud is an interactive CLI console for managing Hetzner Cloud resources. It provides an interactive console with tab completion, command history, and commands for managing virtual machines, volumes, networks, firewalls, load balancers, IP addresses, images, and more. And why? Because it's enough for most people and because it's faster than using complex CLI arguments — it works entirely with tab completion.

> **Communication Note:** Project discussions and status updates are provided in German, but this README remains in English.

## Features

- **CLI Console with Tab Autocompletion** — context-aware completion for commands, subcommands, and live resource IDs
- **Manage Multiple Hetzner Projects** — switch between projects without restarting
- **VM Management** — create, start, stop, resize, rename, rescue, reset password
- **Snapshot & Backup Management** — full snapshot/backup lifecycle
- **Metrics Monitoring** — CPU, traffic, disk I/O via Hetzner metrics API
- **Volume Management** — create, attach, detach, resize, protect
- **Network Management** — private networks, subnets, server attachment
- **Firewall Management** — full rule CRUD with server and label-selector targets
- **Load Balancer Management** — CRUD, targets, services, health checks, algorithm
- **Floating IP Management** — create, assign, rDNS, protection, IP Deletion Guard
- **Primary IP Management** — create, assign, auto_delete, rDNS, protection, IP Deletion Guard
- **Image Management** — list/filter snapshots & backups, delete/update custom images, import wizard
- **ISO Management** — list, attach, detach
- **SSH Key Management** — list, create, update, delete
- **Location & Datacenter Information** — location list/info, datacenter list/info, server type discovery
- **Pricing Information** — resource pricing tables and cost calculations
- **Config Validation** — validate config file permissions, token format, required fields
- **BATCH Processing** — start/stop/delete/snapshot multiple servers at once

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package manager)

### Dependencies

#### Option 1: Using Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Linux/macOS
# OR
.venv\Scripts\activate      # On Windows

pip install -r requirements.txt
```

Or use the provided activation script:

```bash
source activate_hicloud.sh
```

#### Option 2: Global Installation

```bash
pip install -r requirements.txt
```

### Configuration

Generate a sample configuration file:

```bash
python hicloud.py --gen-config ~/.hicloud.toml
```

Then edit it and replace the placeholder tokens:

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

Set correct permissions:

```bash
chmod 600 ~/.hicloud.toml
```

## Usage

Start the interactive console:

```bash
python hicloud.py
```

Use a specific project from your configuration:

```bash
python hicloud.py --project project1
```

Use a one-time API token without a configuration file:

```bash
python hicloud.py --token your_api_token
```

### Interactive Console Commands

Type `help` inside the console to see all available commands:

```
VM Commands:
  vm list                           - List all VMs
  vm info <id>                      - Show detailed information about a VM
  vm create                         - Create a new VM (interactive wizard)
  vm start <id>                     - Start a VM
  vm stop <id>                      - Stop a VM
  vm reboot <id>                    - Reboot a VM
  vm delete <id>                    - Delete a VM by ID
  vm resize <id> <type>             - Change server type
  vm rename <id> <name>             - Rename a VM
  vm rescue <id>                    - Enable rescue mode
  vm reset-password <id>            - Reset root password
  vm image <id> <name>              - Create custom image from VM
  vm image import [url]             - Start guided custom image import wizard

Snapshot Commands:
  snapshot list                     - List all snapshots
  snapshot create                   - Create a snapshot for a VM
  snapshot delete <id>              - Delete a snapshot by ID
  snapshot delete all               - Delete all snapshots for a VM
  snapshot rebuild <id> <sv>        - Rebuild a server from a snapshot

Backup Commands:
  backup list                       - List all backups
  backup enable <id> [WINDOW]       - Enable automatic backups for a VM
  backup disable <id>               - Disable automatic backups for a VM
  backup delete <id>                - Delete a backup by ID

Monitoring Commands:
  metrics list <id>                 - List available metrics for a server
  metrics cpu <id> [--hours=24]     - Show CPU utilization metrics
  metrics traffic <id> [--days=7]   - Show network traffic metrics
  metrics disk <id> [--days=1]      - Show disk I/O metrics

Image Commands:
  image list [snapshot|backup|all]  - List custom images (default: snapshot)
  image info <id>                   - Show detailed information about an image
  image delete <id>                 - Delete a custom image (with confirmation)
  image update <id>                 - Update image description/labels (interactive)
  image import [url]                - Start guided custom image import wizard

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
  volume create                     - Create a new volume (interactive wizard)
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

Firewall Commands:
  firewall list                     - List all firewalls
  firewall info <id>                - Show detailed information about a firewall
  firewall create                   - Create a new firewall (interactive)
  firewall update <id>              - Update firewall metadata
  firewall delete <id>              - Delete a firewall by ID
  firewall rules list <id>          - Show current rules for a firewall
  firewall rules add <id>           - Append new rules to a firewall
  firewall rules remove <id> <idx>  - Remove rules by 1-based index (comma-separated)
  firewall rules set <id>           - Replace all rules for a firewall
  firewall apply <fid> <sid[,..]>   - Apply firewall to one or more servers
  firewall apply <fid> label <sel>  - Apply firewall to label selector targets
  firewall remove <fid> <sid[,..]>  - Remove firewall from one or more servers
  firewall remove <fid> label <sel> - Remove firewall from label selector targets

Load Balancer Commands:
  lb list                              - List all load balancers
  lb info <id>                         - Show detailed information about a load balancer
  lb create                            - Create a new load balancer (interactive wizard)
  lb delete <id>                       - Delete a load balancer by ID
  lb targets <id> list                 - Show current targets for a load balancer
  lb targets <id> add server <sid>     - Add server target (append `private` for private-ip routing)
  lb targets <id> add label <sel>      - Add a label selector target
  lb targets <id> remove server <s>    - Remove server target
  lb targets <id> remove label <s>     - Remove label selector target
  lb service <id> list                 - Show services configured on a load balancer
  lb service <id> add                  - Add a new service (protocol, ports, health check wizard)
  lb service <id> update <port>        - Update an existing service
  lb service <id> delete <port>        - Remove a service by listen port
  lb algorithm <id> <round_robin|least_connections>  - Change load balancing algorithm

Floating IP Commands:
  floating-ip list                  - List all floating IPs
  floating-ip info <id>             - Show detailed information about a floating IP
  floating-ip create                - Create a new floating IP (interactive wizard)
  floating-ip update <id>           - Update name/description/labels (interactive)
  floating-ip delete <id>           - Delete a floating IP (guarded: unassign & unprotect first)
  floating-ip assign <id> <sid>     - Assign floating IP to a server
  floating-ip unassign <id>         - Unassign floating IP from its server
  floating-ip dns <id> <ip> <ptr>   - Set reverse DNS pointer (use "reset" to clear)
  floating-ip protect <id> <e|d>    - Enable/disable delete protection

Primary IP Commands:
  primary-ip list                   - List all primary IPs
  primary-ip info <id>              - Show detailed information about a primary IP
  primary-ip create                 - Create a new primary IP (interactive wizard)
  primary-ip update <id>            - Update name/auto_delete/labels (interactive)
  primary-ip delete <id>            - Delete a primary IP (guarded: unassign & unprotect first)
  primary-ip assign <id> <sid>      - Assign primary IP to a server
  primary-ip unassign <id>          - Unassign primary IP from its server
  primary-ip dns <id> <ip> <ptr>    - Set reverse DNS pointer (use "reset" to clear)
  primary-ip protect <id> <e|d>     - Enable/disable delete protection

ISO Commands:
  iso list                          - List all available ISOs
  iso info <id>                     - Show detailed information about an ISO
  iso attach <iso_id> <server_id>   - Attach ISO to server
  iso detach <server_id>            - Detach ISO from server

Location & Datacenter Commands:
  location list                     - List all available locations
  location info <id>                - Show detailed information about a location
  datacenter list                   - List all available datacenters
  datacenter info <id>              - Show datacenter details and supported server types

Server Type Commands:
  server-type list [location]       - List all server types, optionally filtered by location
  server-type info <name|id>        - Show CPU, RAM, disk, architecture, and pricing

Pricing Commands:
  pricing list                      - Show pricing table for all resources
  pricing calculate                 - Calculate monthly costs for current resources

Config Commands:
  config validate                   - Validate config file (permissions, fields, token format)
  config info                       - Show active config path and project sections

SSH Key Commands:
  keys list                         - List all SSH keys
  keys info <id>                    - Show detailed information about an SSH key
  keys create [name] [file]         - Create/upload a new SSH key
  keys update <id>                  - Update SSH key metadata (name, labels)
  keys delete <id>                  - Delete an SSH key by ID

General Commands:
  history                           - Show command history
  history clear                     - Clear command history
  clear                             - Clear screen
  help [command]                    - Show help or detailed info about a command
  exit, quit, q, Ctrl-D             - Exit the program
```

### Context-Aware Help & Completion

- Use `help <command>` (for example `help vm`) to display all subcommands plus their syntax without leaving the console.
- Press <kbd>TAB</kbd> at any position to auto-complete commands, subcommands, and resource identifiers; suggestions are fetched live from Hetzner (server IDs, volume IDs, floating IP IDs, etc.).
- When multiple options exist, hicloud prints the matching values above the prompt so you can keep typing without guessing argument order.

## Examples

### Floating IP Management

```bash
hicloud> floating-ip list                        # List all floating IPs
hicloud> floating-ip create                      # Interactive creation wizard
hicloud> floating-ip assign 1234 5678            # Assign IP 1234 to server 5678
hicloud> floating-ip dns 1234 1.2.3.4 host.example.com  # Set rDNS pointer
hicloud> floating-ip dns 1234 1.2.3.4 reset      # Clear rDNS pointer
hicloud> floating-ip protect 1234 enable         # Enable delete protection
hicloud> floating-ip unassign 1234               # Unassign from server
hicloud> floating-ip delete 1234                 # Delete (guarded: must be unassigned and unprotected)
```

### Primary IP Management

```bash
hicloud> primary-ip list                         # List all primary IPs
hicloud> primary-ip create                       # Interactive creation wizard
hicloud> primary-ip assign 20 5678               # Assign primary IP 20 to server 5678
hicloud> primary-ip update 20                    # Update name or auto_delete interactively
hicloud> primary-ip dns 20 10.0.0.1 host.example.com  # Set rDNS pointer
hicloud> primary-ip protect 20 enable            # Enable delete protection
hicloud> primary-ip delete 20                    # Delete (guarded: must be unassigned and unprotected)
```

### Image Management

```bash
hicloud> image list                              # List custom snapshot images
hicloud> image list backup                       # List backup images
hicloud> image list all                          # List all image types
hicloud> image info 1234                         # Show image details
hicloud> image update 1234                       # Update description or labels
hicloud> image delete 1234                       # Delete a custom image (with confirmation)
hicloud> image import                            # Interactive import wizard
hicloud> image import https://example.com/my.qcow2  # Import with URL pre-filled
```

### Load Balancer Services

```bash
hicloud> lb list                                 # List all load balancers
hicloud> lb service 1234 list                    # Show services on LB 1234
hicloud> lb service 1234 add                     # Add service via interactive wizard
hicloud> lb service 1234 update 80               # Update service on port 80
hicloud> lb service 1234 delete 80               # Remove service on port 80
hicloud> lb algorithm 1234 round_robin           # Switch to round-robin algorithm
hicloud> lb algorithm 1234 least_connections     # Switch to least-connections algorithm
```

### Server Type Discovery

```bash
hicloud> server-type list                        # List all server types grouped by architecture
hicloud> server-type list nbg1                   # Filter by location
hicloud> server-type info cx22                   # Show specs and pricing by location
hicloud> server-type info 3                      # Look up server type by numeric ID
```

### Config Validation

```bash
hicloud> config validate                         # Validate ~/.hicloud.toml (permissions, fields, token)
hicloud> config info                             # Show active config path and all project sections
```

### ISO Management

```bash
hicloud> iso list                                # List all available ISOs
hicloud> iso info 1234                           # Show details about a specific ISO
hicloud> iso attach 1234 5678                    # Attach ISO 1234 to server 5678
hicloud> iso detach 5678                         # Detach ISO from server 5678
```

### Custom Image Import

Bring your own images hosted on HTTP(S) storage via the interactive wizard:

```bash
hicloud> vm image import
```

Optional: provide a URL upfront (`vm image import https://example.com/my-image.qcow2`) and the wizard pre-fills the first step before asking for name, architecture, and description. The same wizard is also available as `image import`.

### Network Management

```bash
hicloud> network list                            # List all private networks
hicloud> network info 12345                      # Show detailed network information
hicloud> network create                          # Create new private network (interactive wizard)
hicloud> network attach 12345 5678               # Attach server 5678 to network 12345
hicloud> network detach 12345 5678               # Detach server from network
hicloud> network subnet add 12345                # Add a subnet to network
hicloud> network protect 12345 enable            # Enable delete protection
```

### Volume Management

```bash
hicloud> volume create                           # Interactive volume creation wizard
hicloud> volume list                             # List all volumes with attachment status
hicloud> volume attach 1234 5678                 # Attach volume 1234 to server 5678
hicloud> volume resize 1234 50                   # Increase volume size to 50 GB
hicloud> volume detach 1234                      # Detach volume from server
```

### Batch Operations

```bash
hicloud> batch start 1,2,3                       # Start multiple servers
hicloud> batch stop 1,2,3                        # Stop multiple servers
hicloud> batch snapshot 1,2,3                    # Create snapshots for multiple servers
hicloud> batch delete 1,2,3                      # Delete multiple servers (with confirmation)
```

## Development

```
hicloud/
│
├── hicloud.py               # Main entry point
│
├── lib/                     # Core libraries
│   ├── api.py               # HetznerCloudManager — all HTTP calls
│   ├── config.py            # ConfigManager — TOML loading, permission validation
│   └── console.py           # InteractiveConsole — REPL, tab completion, dispatch
│
├── commands/                # One class per resource
│   ├── vm.py                # VMCommands
│   ├── snapshot.py          # SnapshotCommands
│   ├── backup.py            # BackupCommands
│   ├── metrics.py           # MetricsCommands
│   ├── project.py           # ProjectCommands
│   ├── pricing.py           # PricingCommands
│   ├── keys.py              # SSHKeyCommands
│   ├── volume.py            # VolumeCommands
│   ├── network.py           # NetworkCommands
│   ├── firewall.py          # FirewallCommands
│   ├── loadbalancer.py      # LoadBalancerCommands
│   ├── floating_ip.py       # FloatingIPCommands
│   ├── primary_ip.py        # PrimaryIPCommands
│   ├── image.py             # ImageCommands
│   ├── config.py            # ConfigCommands
│   ├── batch.py             # BatchCommands
│   ├── iso.py               # ISOCommands
│   └── location.py          # LocationCommands + ServerTypeCommands
│
├── utils/
│   ├── formatting.py        # Table layout, terminal width helpers
│   ├── colors.py            # ANSI 24-bit RGB color constants
│   ├── constants.py         # API_BASE_URL, DEFAULT_CONFIG_PATH, VERSION
│   └── spinner.py           # DotsSpinner — threaded progress indicator
│
└── tests/
    ├── commands/            # Unit tests for command handlers
    └── lib/                 # Unit tests for API layer
```

## Troubleshooting

### Auto-Completion Prints "Missing \<cmd> subcommand…"

After you type a command followed by a space (for example `iso `), TAB completion switches into "subcommand mode" and prints contextual help above the prompt. If you hit <kbd>Enter</kbd> without a valid subcommand, the handler shows a usage hint. These messages are not errors — simply type a valid subcommand after the first space.

### macOS + iTerm2: Page Up/Down only print `~`

macOS Terminal and hicloud support Page Up/Down out of the box. iTerm2 ships with *"Page up, page down, home and end scroll outside interactive apps"* enabled by default, which intercepts the keys. Fix:

1. Open iTerm2 → **Preferences** (`⌘+,`) → **Keys**.
2. Either disable the above scrolling option, or add explicit *Key Bindings* for `Page Up`, `Page Down`, `Home`, and `End` that **Send Escape Sequence** with `\[5~`, `\[6~`, `\[H`, `\[F`.

## Feature Tracker

Status icons: ✅ shipped, 🟡 partial support, ⬜ not started.

| ID | Category | Feature | Status | Coverage / Next Steps |
|----|----------|---------|--------|------------------------|
| 1 | Top Priority | Network Management | ✅ | `commands/network.py` ships list/info/create/update/delete plus attach/detach/subnet/protect. |
| 2 | Top Priority | Firewall Management | ✅ | `commands/firewall.py` provides CRUD, robust `rules list|add|remove|set`, server and label-selector apply/remove flows. |
| 3 | Top Priority | Volume Management | ✅ | `commands/volume.py` implements list/info/create/delete/attach/detach/resize/protect. |
| 4 | Top Priority | Load Balancer | ✅ | `commands/loadbalancer.py` supports full CRUD, targets (server + label-selector), service list/add/update/delete wizard, health checks, algorithm change. |
| 5 | Advanced | Floating IPs | ✅ | `commands/floating_ip.py` implements list/info/create/update/delete/assign/unassign/rDNS/protection. IP Deletion Guard (ID 28) built in. |
| 6 | Advanced | Image Management | ✅ | `commands/image.py` provides list/info/delete/update/import; `vm image` alias still works. |
| 7 | Advanced | Enhanced Monitoring | 🟡 | `commands/metrics.py` covers `metrics list|cpu|traffic|disk`; alerting/export flows still to implement. |
| 8 | Advanced | Resource Overview | 🟡 | `project resources` and `datacenter resources` provide partial overview; no dedicated unified usage/limits view yet. |
| 9 | Infrastructure | ISO Management | ✅ | `commands/iso.py` delivers list/info/attach/detach. |
| 10 | Infrastructure | Placement Groups | ⬜ | No placement group module yet (`placement list|create|assign`). |
| 11 | Infrastructure | Action Management | ⬜ | `action list/status/cancel/history` absent; would wrap Hetzner action endpoints. |
| 12 | Business Intelligence | Enhanced Analytics | 🟡 | `commands/pricing.py` supports `list` and `calculate`; forecast/compare/optimization helpers missing. |
| 13 | Business Intelligence | Backup Policies | 🟡 | `commands/backup.py` handles list/enable/disable/delete; policy view/restore/schedule flows to build. |
| 14 | CLI UX | Context-aware Autocomplete | 🟡 | ID-based suggestions and inline argument hints implemented; name-based suggestions still open. |
| 15 | CLI UX | Inline Help Overlay | ⬜ | TAB-based hints exist; no toggleable overlay for invalid input. |
| 16 | CLI UX | Prompt & Status UX | 🟡 | Startup shows active project and connection state; a dedicated `status` command is not implemented. |
| 17 | CLI UX | Table `--format` / `--sort` Options | 🟡 | Table layout adapts to terminal width; command-level flags not implemented. |
| 18 | Safety | Guided Destructive Workflows | 🟡 | Many commands require confirmation prompts; standardized flags and cost previews still missing. |
| 19 | Operations | Diagnostics & Logging Command | ⬜ | No `diagnostics` command; only global `--debug` flag exists. |
| 20 | Quality | Base `tests/` + Fixtures | 🟡 | `tests/` covers commands/ and lib/ for all shipped modules; shared fixtures and broader coverage patterns still evolving. |
| 21 | Security | `config validate` + GPG | 🟡 | `config validate` CLI command shipped (`commands/config.py`); optional GPG encryption not implemented. |
| 22 | Automation | Recurring Job Helpers | ⬜ | No built-in helpers yet for snapshot rotation, backup enforcement, or cost alerts. |
| 23 | Top Priority | Load Balancer Advanced Operations | ✅ | Service/listener CRUD, health-check wizard, algorithm change implemented in `commands/loadbalancer.py`. |
| 24 | Infrastructure | Primary IP Management | ✅ | `commands/primary_ip.py` implements list/info/create/update/delete/assign/unassign/rDNS/protection. Deletion Guard built in. |
| 25 | Infrastructure | Certificates Management | ⬜ | No certificates command module yet; add list/create/update/delete for TLS workflows with load balancers. |
| 26 | Infrastructure | DNS Zones & RRsets | ⬜ | DNS API surface not represented; add zone and record-set command modules. |
| 27 | Infrastructure | Server Type Discovery | ✅ | `server-type list [location]` and `server-type info <name|id>` implemented in `commands/location.py`. |
| 28 | Safety | IP Deletion Policy Guard (May 1, 2026) | ✅ | Built into `floating-ip delete` and `primary-ip delete`: blocks deletion if IP is assigned or protected, with actionable error messages. |

## License

This project is licensed under the GPL-3.0 License.
