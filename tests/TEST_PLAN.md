# Test Plan - hicloud

Dieses Dokument zeigt den aktuellen Test-Status im Repository und die verbleibenden Luecken.

Stand: 2026-02-28

---

## 1) Unit-Tests: Command-Layer (`tests/commands/`)

| Modul | Testdatei | Anzahl Tests | Status | Hinweis |
|-------|-----------|--------------|--------|---------|
| `commands/vm.py` | `tests/commands/test_vm.py` | 22 | ✅ | Gute Basis inkl. Fehlerfaelle |
| `commands/snapshot.py` | `tests/commands/test_snapshot.py` | 19 | ✅ | Listen/Create/Delete/Rebuild abgedeckt |
| `commands/backup.py` | `tests/commands/test_backup.py` | 15 | ✅ | Listen/Enable/Disable/Delete abgedeckt |
| `commands/network.py` | `tests/commands/test_network.py` | 19 | ✅ | Attach/Detach/Protect etc. abgedeckt |
| `commands/volume.py` | `tests/commands/test_volume.py` | 26 | ✅ | Umfangreich, inkl. Schutz-/Resize-Faelle |
| `commands/keys.py` | `tests/commands/test_keys.py` | 14 | ✅ | List/Info/Create/Delete abgedeckt |
| `commands/iso.py` | `tests/commands/test_iso.py` | 16 | ✅ | List/Info/Attach/Detach abgedeckt |
| `commands/metrics.py` | `tests/commands/test_metrics.py` | 17 | ✅ | CPU/Traffic/Disk + Eingabevalidierung |
| `commands/pricing.py` | `tests/commands/test_pricing.py` | 8 | ✅ | List/Calculate + Fehlerpfade |
| `commands/batch.py` | `tests/commands/test_batch.py` | 17 | ✅ | Parsing + Start/Stop/Delete/Snapshot |
| `commands/project.py` | `tests/commands/test_project.py` | 11 | ✅ | List/Switch/Info/Resources abgedeckt |
| `commands/config.py` | `tests/commands/test_config.py` | 9 | ✅ | Validierung + Sicherheitschecks |
| `commands/firewall.py` | `tests/commands/test_firewall.py` | 6 | ✅ | Kern-Workflows getestet |
| `commands/loadbalancer.py` | `tests/commands/test_loadbalancer.py` | 16 | ✅ | Target/Service/Algo-Workflows getestet |
| `commands/image.py` | `tests/commands/test_image.py` | 13 | ✅ | List/Info/Delete/Update abgedeckt |
| `commands/floating_ip.py` | `tests/commands/test_floating_ip.py` | 22 | ✅ | Assign/Unassign/Delete/DNS/Protect |
| `commands/primary_ip.py` | `tests/commands/test_primary_ip.py` | 19 | ✅ | Assign/Unassign/Delete/DNS/Protect |
| `commands/location.py` | `tests/commands/test_location_servertype.py` | 28 | ✅ | `LocationCommands`, `DatacenterCommands` und `ServerTypeCommands` abgedeckt |

---

## 2) Unit-Tests: API-Layer (`tests/lib/`)

| API-Bereich | Testdatei | Anzahl Tests | Status |
|------------|-----------|--------------|--------|
| Firewall API | `tests/lib/test_api_firewall.py` | 8 | ✅ |
| Load Balancer API | `tests/lib/test_api_loadbalancer.py` | 13 | ✅ |
| Image API | `tests/lib/test_api_image.py` | 10 | ✅ |
| Floating IP API | `tests/lib/test_api_floating_ip.py` | 14 | ✅ |
| Primary IP API | `tests/lib/test_api_primary_ip.py` | 13 | ✅ |

Hinweis: Fuer weitere API-Bereiche (z.B. VM, Network, Volume, Backup, Snapshot) existieren aktuell keine separaten `tests/lib/test_api_*.py`-Dateien.

---

## 3) Integration-Tests

Aktueller Status: `tests/integration/` existiert derzeit nicht.

Geplanter naechster Schritt:
- `tests/integration/test_read_only.py` mit `pytest.mark.skipif(not HETZNER_TOKEN, ...)`
- Nur read-only Endpunkte (list/info/get), keine create/delete/modify Calls

---

## 4) Verifikation (lokal)

Empfohlen innerhalb der venv:

```bash
.venv/bin/pytest -q
```

Letzter Lauf im Repo:
- Ergebnis: `355 passed`
- Laufzeit: `0.15s`

Hinweis: Ein globales `pytest -q` ohne venv kann wegen fehlender Abhaengigkeiten (`toml`, `requests`) bei der Collection scheitern.

---

## 5) Offene Prioritaeten

1. Read-only Integration-Tests unter `tests/integration/` anlegen.
