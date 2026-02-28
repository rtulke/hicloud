# Test Plan - hicloud

This doc shows where testing currently stands in the repo and what is still missing.

Updated: 2026-02-28

---

## 1) Unit Tests: Command Layer (`tests/commands/`)

| Module | Test File | Test Count | Status | Notes |
|-------|-----------|------------|--------|-------|
| `commands/vm.py` | `tests/commands/test_vm.py` | 22 | ✅ | Solid baseline, includes edge/error cases |
| `commands/snapshot.py` | `tests/commands/test_snapshot.py` | 19 | ✅ | List/Create/Delete/Rebuild covered |
| `commands/backup.py` | `tests/commands/test_backup.py` | 15 | ✅ | List/Enable/Disable/Delete covered |
| `commands/network.py` | `tests/commands/test_network.py` | 19 | ✅ | Attach/Detach/Protect etc. covered |
| `commands/volume.py` | `tests/commands/test_volume.py` | 26 | ✅ | Broad coverage incl. protection/resize paths |
| `commands/keys.py` | `tests/commands/test_keys.py` | 14 | ✅ | List/Info/Create/Delete covered |
| `commands/iso.py` | `tests/commands/test_iso.py` | 16 | ✅ | List/Info/Attach/Detach covered |
| `commands/metrics.py` | `tests/commands/test_metrics.py` | 17 | ✅ | CPU/Traffic/Disk + input validation |
| `commands/pricing.py` | `tests/commands/test_pricing.py` | 8 | ✅ | List/Calculate + error paths |
| `commands/batch.py` | `tests/commands/test_batch.py` | 17 | ✅ | ID parsing + Start/Stop/Delete/Snapshot |
| `commands/project.py` | `tests/commands/test_project.py` | 11 | ✅ | List/Switch/Info/Resources covered |
| `commands/config.py` | `tests/commands/test_config.py` | 9 | ✅ | Validation + security checks |
| `commands/firewall.py` | `tests/commands/test_firewall.py` | 6 | ✅ | Core workflows covered |
| `commands/loadbalancer.py` | `tests/commands/test_loadbalancer.py` | 16 | ✅ | Target/Service/Algo workflows covered |
| `commands/image.py` | `tests/commands/test_image.py` | 13 | ✅ | List/Info/Delete/Update covered |
| `commands/floating_ip.py` | `tests/commands/test_floating_ip.py` | 22 | ✅ | Assign/Unassign/Delete/DNS/Protect |
| `commands/primary_ip.py` | `tests/commands/test_primary_ip.py` | 19 | ✅ | Assign/Unassign/Delete/DNS/Protect |
| `commands/location.py` | `tests/commands/test_location_servertype.py` | 28 | ✅ | `LocationCommands`, `DatacenterCommands`, and `ServerTypeCommands` covered |

---

## 2) Unit Tests: API Layer (`tests/lib/`)

| API Area | Test File | Test Count | Status |
|----------|-----------|------------|--------|
| API Core / Request Handling | `tests/lib/test_api_core.py` | 3 | ✅ |
| VM API | `tests/lib/test_api_vm.py` | 20 | ✅ |
| Snapshot API | `tests/lib/test_api_snapshot.py` | 9 | ✅ |
| Backup API | `tests/lib/test_api_backup.py` | 9 | ✅ |
| Batch-related API paths | `tests/lib/test_api_batch.py` | 4 | ✅ |
| Volume API | `tests/lib/test_api_volume.py` | 8 | ✅ |
| Network API | `tests/lib/test_api_network.py` | 9 | ✅ |
| ISO API | `tests/lib/test_api_iso.py` | 5 | ✅ |
| SSH Key API | `tests/lib/test_api_keys.py` | 6 | ✅ |
| Location/Datacenter/ServerType API | `tests/lib/test_api_location.py` | 5 | ✅ |
| Metrics API | `tests/lib/test_api_metrics.py` | 6 | ✅ |
| Pricing API | `tests/lib/test_api_pricing.py` | 3 | ✅ |
| Project-related API paths | `tests/lib/test_api_project.py` | 4 | ✅ |
| Firewall API | `tests/lib/test_api_firewall.py` | 8 | ✅ |
| Load Balancer API | `tests/lib/test_api_loadbalancer.py` | 13 | ✅ |
| Image API | `tests/lib/test_api_image.py` | 10 | ✅ |
| Floating IP API | `tests/lib/test_api_floating_ip.py` | 14 | ✅ |
| Primary IP API | `tests/lib/test_api_primary_ip.py` | 13 | ✅ |

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
- Result: `446 passed`
- Runtime: `0.23s`

Note: running global `pytest -q` without venv can fail during collection because of missing deps (`toml`, `requests`).

---

## 5) Open Priority

1. Add read-only integration tests under `tests/integration/`.
