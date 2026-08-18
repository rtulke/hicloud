# Changelog

All notable changes to hicloud are documented in this file.

## [1.4.0] - 2026-08-18

Installer release: `setup.sh` replaces the old activation script and
installs hicloud end to end, either from a checkout or straight from curl.

### Added

- One-line install: `curl -fsSL .../setup.sh | bash`. The installer clones
  the repository when run standalone, or copies the tracked files when
  started from a local checkout.
- System-wide installation to `/opt/hicloud` with a command in
  `/usr/local/bin`, or per-user installation to `~/.local/share/hicloud`
  with a command in `~/.local/bin`. Only the location is asked; root
  defaults to system-wide, and without root or sudo the system-wide option
  is not offered at all.
- Dependency handling follows the system: apt packages
  (`python3-requests`, `python3-toml`) for a system-wide install on Debian
  and Ubuntu, a virtual environment everywhere else. `--apt` and `--venv`
  override the choice; `--dev` adds pytest and ruff.
- Existing `.venv`, `venv`, `~/.venv/hicloud` or `~/.venv` are reused
  instead of creating another environment. On Debian and Ubuntu a missing
  `python3-venv` is installed on demand.
- A per-user install adds `~/.local/bin` to the `PATH` in the login shell's
  startup file (zsh, bash, fish or `.profile`), idempotently across
  re-runs.
- Configuration wizard: when `~/.hicloud.toml` does not exist, the installer
  explains where to create a Hetzner API token, reads it with `*` feedback
  and echo off for the whole input, verifies it against the API and writes
  the file with permissions 600. A token the API rejects is not written.
- The run ends with `hicloud --version`; a broken installation fails loudly
  instead of reporting success.
- Non-interactive options: `--system`, `--user`, `--prefix DIR`, `-y`.

### Changed

- `activate_hicloud.sh` is gone; `setup.sh` takes over its job and more.
- README documents the one-line install, the target directories and the
  non-interactive options, and uses the installed `hicloud` command in the
  usage examples.
- Package manager output from apt, pip and venv is captured and only shown
  when a command fails.

### Fixed

- The test import path was lost when `conftest.py` was replaced: a fresh
  checkout could not collect any tests. `pythonpath = ["."]` in
  `pyproject.toml` restores it.

## [1.3.2] - 2026-08-13

### Changed

- All console colors now come from the central palette in `utils/colors.py`:
  info views, status indicators, warnings, and completion hints share the
  same look as the tables. No more hard-coded ANSI escapes in command
  modules — restyling the console is a one-file change.

## [1.3.1] - 2026-07-14

API compatibility release: an audit against the current Hetzner Cloud API
changelog surfaced several breaking upstream changes.

### Fixed

- Servers and Primary IPs now read the top-level `location` property; the
  `datacenter` property was removed by Hetzner on 2026-07-01. `vm list` and
  `vm info` show locations again instead of N/A, and creating a Primary IP
  sends `location` instead of the removed `datacenter` request field (the
  creation wizard offers locations accordingly).
- `action list` aggregates the per-resource action endpoints; the global
  `GET /v1/actions` listing has returned `410 Gone` since January 2025.
- `vm info` no longer crashes on servers whose origin image was deleted
  (`image: null`) and tolerates null `ipv4`/`ipv6`/`datacenter` fields.
- The welcome screen and `project info` use the locations endpoint instead
  of the deprecated datacenters endpoint (Hetzner removal planned after
  2026-10-01); the `datacenter` commands print a deprecation note.

### Verified against the current API

- Reverse DNS resets already send an explicit `dns_ptr: null`, matching the
  stricter behavior Hetzner enforces from 2026-09-30 on.
- Polling single actions via `GET /v1/actions/{id}` remains supported.

## [1.3.0] - 2026-07-14

### Security

- Config file permission check now rejects group- or world-accessible files
  (644 and even 666 previously passed as secure); only 600 and 400 are accepted.
- `project info` no longer prints the beginning of the Authorization header.
- The API token can be provided via the `HCLOUD_TOKEN` environment variable
  to keep it out of shell history (priority: `--token` > env > config file).

### Added

- Action management: `action list [running|success|error]` and
  `action info <id>` make long-running operations traceable. The Hetzner API
  has no cancel endpoint, so cancelling actions is out of scope.
- Placement group management: `placement-group list|info|create|update|delete`
  plus `add`/`remove` with guards (running server, non-empty group).
- Pagination: all list commands follow API pagination; projects with more
  than one page of resources are no longer silently truncated.
- Automatic retry on HTTP 429 rate limits, honoring the Retry-After header.
- CI workflow (ruff and pytest on Python 3.9 and 3.13), `pyproject.toml`
  tooling configuration, and `requirements-dev.txt`.

### Fixed

- Metrics parsing: `metrics cpu|traffic|disk` now read the actual Hetzner
  time series format; previously they reported "no data" against the real API.
- `project switch` preserves `--config` and `--debug` and saves the command
  history before restarting (`--token` is intentionally dropped on switch).
- Table cells longer than their column are truncated with an ellipsis
  instead of pushing the following columns out of alignment.
- All HTTP requests use a 30-second timeout; a hanging API no longer
  freezes the console.
- Duplicate "not found" messages removed; the API layer is the single
  source of error messages.
- Invalid input in interactive wizards re-prompts instead of silently
  substituting a default value.
- Action wait timeouts now state that the action keeps running on
  Hetzner's side.

### Changed

- API error messages are always shown (many were previously hidden behind
  `--debug`); debug mode only adds transport details.
- Command modules share a common base class (dispatch, ID parsing,
  confirmations, label prompts); the general help output is generated from
  the command registry.
- `server` is an alias for `vm` and gains tab completion; `loadbalancer`
  shares the `lb` command tree instead of duplicating it.
- Status icons and other non-ASCII symbols in output and documentation
  replaced with ASCII.
- Requires Python >= 3.9 (the previously documented 3.6 no longer worked
  with the pinned dependencies).

## [1.2.0]

Baseline release before this changelog was introduced.
