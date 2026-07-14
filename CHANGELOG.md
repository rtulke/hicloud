# Changelog

All notable changes to hicloud are documented in this file.

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
