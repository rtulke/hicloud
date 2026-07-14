# Test Plan - hicloud

This doc shows where testing currently stands in the repo and what is still missing.

Updated: 2026-07-14

---

## 1) Unit Tests: Command Layer (`tests/commands/`)

| Module | Test File | Test Count | Status | Notes |
|-------|-----------|------------|--------|-------|
| `commands/vm.py` | `tests/commands/test_vm.py` | 24 | done | Solid baseline incl. null-field regressions (image/ipv4/datacenter) |
| `commands/snapshot.py` | `tests/commands/test_snapshot.py` | 19 | done | List/Create/Delete/Rebuild covered |
| `commands/backup.py` | `tests/commands/test_backup.py` | 15 | done | List/Enable/Disable/Delete covered |
| `commands/network.py` | `tests/commands/test_network.py` | 19 | done | Attach/Detach/Protect etc. covered |
| `commands/volume.py` | `tests/commands/test_volume.py` | 26 | done | Broad coverage incl. protection/resize paths |
| `commands/keys.py` | `tests/commands/test_keys.py` | 14 | done | List/Info/Create/Delete covered |
| `commands/iso.py` | `tests/commands/test_iso.py` | 16 | done | List/Info/Attach/Detach covered |
| `commands/metrics.py` | `tests/commands/test_metrics.py` | 22 | done | CPU/Traffic/Disk + input validation; mocks use the real Hetzner time_series format |
| `commands/pricing.py` | `tests/commands/test_pricing.py` | 8 | done | List/Calculate + error paths |
| `commands/batch.py` | `tests/commands/test_batch.py` | 17 | done | ID parsing + Start/Stop/Delete/Snapshot |
| `commands/project.py` | `tests/commands/test_project.py` | 13 | done | List/Switch/Info/Resources covered incl. flag passthrough on switch |
| `commands/config.py` | `tests/commands/test_config.py` | 9 | done | Validation + security checks |
| `commands/firewall.py` | `tests/commands/test_firewall.py` | 6 | done | Core workflows covered |
| `commands/loadbalancer.py` | `tests/commands/test_loadbalancer.py` | 16 | done | Target/Service/Algo workflows covered |
| `commands/image.py` | `tests/commands/test_image.py` | 13 | done | List/Info/Delete/Update covered |
| `commands/floating_ip.py` | `tests/commands/test_floating_ip.py` | 22 | done | Assign/Unassign/Delete/DNS/Protect |
| `commands/primary_ip.py` | `tests/commands/test_primary_ip.py` | 20 | done | Assign/Unassign/Delete/DNS/Protect incl. legacy datacenter fallback |
| `commands/location.py` | `tests/commands/test_location_servertype.py` | 28 | done | `LocationCommands`, `DatacenterCommands`, and `ServerTypeCommands` covered |
| `commands/base.py` | `tests/commands/test_base.py` | 11 | done | Shared dispatch, parse_id, confirm, prompt_labels |
| `commands/action.py` | `tests/commands/test_action.py` | 12 | done | List/filter/info incl. error rendering |
| `commands/placement_group.py` | `tests/commands/test_placement_group.py` | 18 | done | CRUD plus add/remove guards (running server, non-empty group) |

---

## 2) Unit Tests: API Layer (`tests/lib/`)

| API Area | Test File | Test Count | Status |
|----------|-----------|------------|--------|
| API Core / Request Handling | `tests/lib/test_api_core.py` | 10 | done |
| Config Manager (permissions) | `tests/lib/test_config_manager.py` | 8 | done |
| Console registry & dispatch | `tests/lib/test_console.py` | 12 | done |
| Action API | `tests/lib/test_api_action.py` | 7 | done |
| Placement Group API | `tests/lib/test_api_placement_group.py` | 10 | done |
| Formatting / table truncation | `tests/utils/test_formatting.py` | 9 | done |
| Interactive prompt helpers | `tests/utils/test_prompts.py` | 10 | done |
| VM API | `tests/lib/test_api_vm.py` | 20 | done |
| Snapshot API | `tests/lib/test_api_snapshot.py` | 9 | done |
| Backup API | `tests/lib/test_api_backup.py` | 9 | done |
| Batch-related API paths | `tests/lib/test_api_batch.py` | 4 | done |
| Volume API | `tests/lib/test_api_volume.py` | 8 | done |
| Network API | `tests/lib/test_api_network.py` | 9 | done |
| ISO API | `tests/lib/test_api_iso.py` | 5 | done |
| SSH Key API | `tests/lib/test_api_keys.py` | 6 | done |
| Location/Datacenter/ServerType API | `tests/lib/test_api_location.py` | 5 | done |
| Metrics API | `tests/lib/test_api_metrics.py` | 6 | done |
| Pricing API | `tests/lib/test_api_pricing.py` | 3 | done |
| Project-related API paths | `tests/lib/test_api_project.py` | 4 | done |
| Firewall API | `tests/lib/test_api_firewall.py` | 8 | done |
| Load Balancer API | `tests/lib/test_api_loadbalancer.py` | 13 | done |
| Image API | `tests/lib/test_api_image.py` | 10 | done |
| Floating IP API | `tests/lib/test_api_floating_ip.py` | 14 | done |
| Primary IP API | `tests/lib/test_api_primary_ip.py` | 13 | done |

Note: `commands/config.py` does not use `HetznerCloudManager` API methods directly, so it has command-level tests only.

---

## 3) Integration Tests

Current status: `tests/integration/` does not exist yet.

Next step:
- add `tests/integration/test_read_only.py` with `pytest.mark.skipif(not HETZNER_TOKEN, ...)`
- keep it read-only (`list`/`info`/`get`), no create/delete/modify calls

---

## 4) Local Verification

Recommended inside the venv:

```bash
.venv/bin/pytest -q
```

Latest run in this repo:
- Result: `528 passed`
- Runtime: `0.21s`

Note: running global `pytest -q` without venv can fail during collection because of missing deps (`toml`, `requests`).

---

## 5) Open Priority

1. Add read-only integration tests under `tests/integration/`.
