# Test Plan — hicloud

Dieses Dokument beschreibt die vollständige Teststrategie für hicloud.
Es dient als Vorlage für die Implementierung der noch fehlenden Test-Dateien.

---

## Übersicht: Aktueller Stand

| Modul | Unit-Tests | API-Tests | Status |
|-------|-----------|-----------|--------|
| `commands/firewall.py` | `tests/commands/test_firewall.py` | `tests/lib/test_api_firewall.py` | ✅ |
| `commands/loadbalancer.py` | `tests/commands/test_loadbalancer.py` | `tests/lib/test_api_loadbalancer.py` | ✅ |
| `commands/image.py` | `tests/commands/test_image.py` | `tests/lib/test_api_image.py` | ✅ |
| `commands/config.py` | `tests/commands/test_config.py` | — | ✅ |
| `commands/location.py` | `tests/commands/test_location_servertype.py` | — | ✅ |
| `commands/floating_ip.py` | `tests/commands/test_floating_ip.py` | `tests/lib/test_api_floating_ip.py` | ✅ |
| `commands/primary_ip.py` | `tests/commands/test_primary_ip.py` | `tests/lib/test_api_primary_ip.py` | ✅ |
| `commands/vm.py` | — | — | ⬜ |
| `commands/snapshot.py` | — | — | ⬜ |
| `commands/backup.py` | — | — | ⬜ |
| `commands/network.py` | — | — | ⬜ |
| `commands/volume.py` | — | — | ⬜ |
| `commands/keys.py` | — | — | ⬜ |
| `commands/iso.py` | — | — | ⬜ |
| `commands/metrics.py` | — | — | ⬜ |
| `commands/pricing.py` | — | — | ⬜ |
| `commands/batch.py` | — | — | ⬜ |
| `commands/project.py` | — | — | ⬜ |

---

## Aufbau: Wie Tests in diesem Projekt strukturiert sind

Jede Test-Datei folgt demselben Muster (siehe z.B. `test_floating_ip.py`):

```python
# Minimales Stub-Setup
class DummyConsole:
    def __init__(self, hetzner):
        self.hetzner = hetzner
        self.tables = []

    def print_table(self, headers, rows, title=None):
        self.tables.append((headers, rows, title))

    def horizontal_line(self, char="="):
        return char * 60


class DummyHetzner:
    # Nur die Methoden implementieren, die das Modul aufruft
    ...


def build():
    h = DummyHetzner()
    c = DummyConsole(h)
    return XyzCommands(c), h, c
```

Die `build()`-Funktion gibt immer `(cmd, hetzner, console)` zurück.
Assertions prüfen entweder `capsys.readouterr().out` (Textausgabe) oder Tracking-Listen auf `DummyHetzner`.

---

## Zwei Test-Arten

### 1. Unit Tests (`tests/commands/`, `tests/lib/`)
Laufen ohne Netzwerk, mit gefakten Daten. Immer ausführbar mit `pytest -q`.

### 2. Integrations-Tests (`tests/integration/`)
Laufen gegen die echte Hetzner API. Werden per Marker übersprungen wenn kein Token gesetzt:

```python
import pytest, os

pytestmark = pytest.mark.skipif(
    not os.environ.get("HETZNER_TOKEN"),
    reason="HETZNER_TOKEN not set"
)
```

Ausführen: `HETZNER_TOKEN=xxx pytest tests/integration/ -q`

Integrations-Tests dürfen **keine** schreibenden Operationen ausführen (kein create/delete/modify).
Nur read-only Calls: list, info, get.

---

## Fehlende Unit Tests

---

### `tests/commands/test_vm.py`

```python
from commands.vm import VMCommands

# DummyHetzner braucht:
# list_servers(), get_server_by_id(id),
# start_server(id), stop_server(id), reboot_server(id),
# delete_server(id), shutdown_server(id)

def test_list_builds_table():
    # cmd.list_vms()
    # assert len(console.tables) == 1
    # assert "Name" in console.tables[0][0]
    pass

def test_list_empty(capsys):
    # h.servers = []
    # cmd.list_vms()
    # assert "No VMs" in capsys.readouterr().out
    pass

def test_show_info(capsys):
    # cmd.show_vm_info(["1"])
    # assert server name, IP, status in output
    pass

def test_show_info_missing_id(capsys):
    # cmd.show_vm_info([])
    # assert "Missing" in output
    pass

def test_start_vm(monkeypatch):
    # h.server["status"] = "off"
    # monkeypatch input -> "y"
    # cmd.start_vm(["1"])
    # assert h.start_calls == [1]
    pass

def test_start_already_running(capsys):
    # h.server["status"] = "running"
    # cmd.start_vm(["1"])
    # assert "already running" in output
    # assert h.start_calls == []
    pass

def test_stop_vm(monkeypatch):
    # h.server["status"] = "running"
    # cmd.stop_vm(["1"])
    # assert h.stop_calls == [1]
    pass

def test_stop_already_off(capsys):
    # h.server["status"] = "off"
    # cmd.stop_vm(["1"])
    # assert "already stopped" in output
    pass

def test_reboot_vm(monkeypatch):
    # h.server["status"] = "running"
    # cmd.reboot_vm(["1"])
    # assert h.reboot_calls == [1]
    pass

def test_reboot_blocked_if_off(capsys):
    # h.server["status"] = "off"
    # cmd.reboot_vm(["1"])
    # assert "vm start" in output  (hint to use start instead)
    # assert h.reboot_calls == []
    pass

def test_delete_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.delete_vm(["1"])
    # assert h.delete_calls == [1]
    pass

def test_delete_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # cmd.delete_vm(["1"])
    # assert h.delete_calls == []
    pass

def test_rename_vm(monkeypatch):
    # cmd.rename_vm(["1", "new-name"])
    # assert h.rename_calls == [(1, "new-name")]
    pass

def test_resize_vm_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # cmd.resize_vm(["1", "cx22"])
    # assert h.resize_calls == []
    pass
```

---

### `tests/commands/test_snapshot.py`

```python
from commands.snapshot import SnapshotCommands

# DummyHetzner braucht:
# list_snapshots(vm_id=None), get_server_by_id(id),
# create_snapshot(vm_id), delete_snapshot(snap_id),
# rebuild_server_from_snapshot(server_id, snap_id)

def test_list_groups_by_server():
    # Zwei Snapshots von zwei verschiedenen Servern
    # cmd.list_snapshots([])
    # assert len(console.tables) == 2   (eine Tabelle pro Server-Gruppe)
    # assert console.tables[0][2] == "server-a"  (Titel = Server-Name)
    pass

def test_list_empty(capsys):
    # h.snapshots = []
    # assert "No snapshots" in output
    pass

def test_create_snapshot(capsys):
    # cmd.create_snapshot(["1"])
    # assert h.create_calls == [1]
    # assert "successfully" in output
    pass

def test_create_missing_id(capsys):
    # cmd.create_snapshot([])
    # assert "Missing VM ID" in output
    pass

def test_delete_single_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.delete_snapshot(["99"])
    # assert h.delete_calls == [99]
    pass

def test_delete_single_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # cmd.delete_snapshot(["99"])
    # assert h.delete_calls == []
    pass

def test_delete_all_confirmed(monkeypatch):
    # h.snapshots = [{"id": 10, ...}, {"id": 11, ...}]
    # monkeypatch input -> "y"
    # cmd.delete_snapshot(["all", "1"])
    # assert h.delete_calls == [10, 11]
    pass

def test_delete_all_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # cmd.delete_snapshot(["all", "1"])
    # assert h.delete_calls == []
    pass

def test_rebuild_confirmed(monkeypatch):
    # monkeypatch input -> "rebuild"
    # cmd.rebuild_snapshot(["99", "1"])
    # assert h.rebuild_calls == [(1, 99)]
    pass

def test_rebuild_wrong_confirmation(monkeypatch, capsys):
    # monkeypatch input -> "yes"  (not "rebuild")
    # assert "Operation cancelled" in output
    # assert h.rebuild_calls == []
    pass
```

---

### `tests/commands/test_backup.py`

```python
from commands.backup import BackupCommands

# DummyHetzner braucht:
# list_backups(vm_id=None), get_server_by_id(id),
# enable_server_backups(vm_id, window), disable_server_backups(vm_id),
# delete_backup(backup_id)

def test_list_groups_by_server():
    # Backups von zwei Servern
    # assert len(console.tables) == 2
    # assert console.tables[0][2] == "server-a"  (Titel = Server-Name)
    pass

def test_list_filtered_by_vm():
    # cmd.list_backups(["1"])
    # assert DummyHetzner.list_backups wurde mit vm_id=1 aufgerufen
    pass

def test_list_empty(capsys):
    # assert "No backups" in output
    pass

def test_enable_backup(capsys):
    # cmd.enable_backup(["1"])
    # assert h.enable_calls == [(1, None)]
    pass

def test_enable_backup_with_window(capsys):
    # cmd.enable_backup(["1", "22-02"])
    # assert h.enable_calls == [(1, "22-02")]
    pass

def test_enable_backup_invalid_window(capsys):
    # cmd.enable_backup(["1", "99-99"])
    # assert "Invalid backup window" in output
    # assert h.enable_calls == []
    pass

def test_disable_backup(capsys):
    # cmd.disable_backup(["1"])
    # assert h.disable_calls == [1]
    pass

def test_delete_backup_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.delete_backup(["50"])
    # assert h.delete_calls == [50]
    pass

def test_delete_backup_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # assert h.delete_calls == []
    pass
```

---

### `tests/commands/test_network.py`

```python
from commands.network import NetworkCommands

# DummyHetzner braucht:
# list_networks(), get_network_by_id(id),
# delete_network(id), attach_server_to_network(nid, sid, ip),
# detach_server_from_network(nid, sid),
# add_subnet_to_network(id, subnet), delete_subnet_from_network(id, ip),
# change_network_protection(id, delete)

def test_list_builds_table():
    # cmd.list_networks()
    # assert "Name" in headers
    # assert "IP Range" in headers
    pass

def test_list_empty(capsys):
    # assert "No networks" in output
    pass

def test_show_info(capsys):
    # cmd.show_network_info(["1"])
    # assert network name, IP range in output
    pass

def test_show_info_missing_id(capsys):
    # assert "Missing" in output
    pass

def test_delete_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.delete_network(["1"])
    # assert h.delete_calls == [1]
    pass

def test_delete_blocked_if_protected(capsys):
    # h.network["protection"] = {"delete": True}
    # assert "ERROR" in output
    # assert h.delete_calls == []
    pass

def test_delete_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # assert h.delete_calls == []
    pass

def test_attach_server(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.attach_server(["1", "42"])
    # assert h.attach_calls == [(1, 42, None)]
    pass

def test_detach_server(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.detach_server(["1", "42"])
    # assert h.detach_calls == [(1, 42)]
    pass

def test_protect_enable():
    # cmd.protect_network(["1", "enable"])
    # assert h.protect_calls == [(1, True)]
    pass

def test_protect_disable():
    # cmd.protect_network(["1", "disable"])
    # assert h.protect_calls == [(1, False)]
    pass

def test_subnet_add(monkeypatch):
    # monkeypatch input: network_zone, ip_range, ...
    # cmd.manage_subnet(["1", "add"])
    # assert h.subnet_add_calls contains network id
    pass

def test_subnet_delete(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.manage_subnet(["1", "delete", "10.0.0.0/24"])
    # assert h.subnet_delete_calls == [(1, "10.0.0.0/24")]
    pass
```

---

### `tests/commands/test_volume.py`

```python
from commands.volume import VolumeCommands

# DummyHetzner braucht:
# list_volumes(), get_volume_by_id(id),
# delete_volume(id), attach_volume(vid, sid),
# detach_volume(id), resize_volume(id, size),
# change_volume_protection(id, delete)

def test_list_builds_table():
    # assert "Name" in headers, "Size" in headers
    pass

def test_list_empty(capsys):
    # assert "No volumes" in output
    pass

def test_show_info(capsys):
    # assert name, size, status in output
    pass

def test_delete_unattached_confirmed(monkeypatch):
    # h.volume["server"] = None
    # monkeypatch input -> "y"
    # assert h.delete_calls == [1]
    pass

def test_delete_blocked_if_attached(capsys):
    # h.volume["server"] = {"id": 42}
    # assert "ERROR" in output (must detach first)
    # assert h.delete_calls == []
    pass

def test_delete_blocked_if_protected(capsys):
    # h.volume["protection"] = {"delete": True}
    # assert "ERROR" in output
    # assert h.delete_calls == []
    pass

def test_delete_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # assert h.delete_calls == []
    pass

def test_attach_volume(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.attach_volume(["1", "42"])
    # assert h.attach_calls == [(1, 42)]
    pass

def test_detach_volume(monkeypatch):
    # h.volume["server"] = {"id": 42}
    # monkeypatch input -> "y"
    # cmd.detach_volume(["1"])
    # assert h.detach_calls == [1]
    pass

def test_detach_already_detached(capsys):
    # h.volume["server"] = None
    # assert "not attached" in output
    pass

def test_resize_volume(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.resize_volume(["1", "50"])
    # assert h.resize_calls == [(1, 50)]
    pass

def test_resize_smaller_blocked(capsys):
    # h.volume["size"] = 100
    # cmd.resize_volume(["1", "50"])
    # assert "increase only" in output (oder ähnlich)
    pass

def test_protect_enable():
    # cmd.protect_volume(["1", "enable"])
    # assert h.protect_calls == [(1, True)]
    pass

def test_protect_disable():
    # cmd.protect_volume(["1", "disable"])
    # assert h.protect_calls == [(1, False)]
    pass
```

---

### `tests/commands/test_keys.py`

```python
from commands.keys import KeysCommands

# DummyHetzner braucht:
# list_ssh_keys(), get_ssh_key_by_id(id),
# create_ssh_key(name, public_key, labels),
# update_ssh_key(id, name, labels),
# delete_ssh_key(id)

def test_list_builds_table():
    # assert "Name" in headers, "Fingerprint" in headers
    pass

def test_list_empty(capsys):
    # assert "No SSH keys" in output
    pass

def test_show_info(capsys):
    # assert name, fingerprint in output
    pass

def test_show_info_missing_id(capsys):
    # assert "Missing" in output
    pass

def test_create_from_file(monkeypatch, tmp_path):
    # tmp_path / "id_rsa.pub" mit Dummy-Key-Content erstellen
    # cmd.create_key(["mykey", str(pub_key_path)])
    # assert h.create_calls[0]["name"] == "mykey"
    # assert "ssh-rsa" in h.create_calls[0]["public_key"]
    pass

def test_create_missing_file(capsys):
    # cmd.create_key(["mykey", "/nonexistent.pub"])
    # assert "not found" in output
    # assert h.create_calls == []
    pass

def test_update_name(monkeypatch):
    # monkeypatch input: "new-name", "", "y"
    # cmd.update_key(["1"])
    # assert h.update_calls[0][1]["name"] == "new-name"
    pass

def test_update_no_changes(monkeypatch, capsys):
    # monkeypatch input: "", "", "n"
    # assert "No changes" in output
    # assert h.update_calls == []
    pass

def test_delete_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.delete_key(["1"])
    # assert h.delete_calls == [1]
    pass

def test_delete_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # assert h.delete_calls == []
    pass
```

---

### `tests/commands/test_iso.py`

```python
from commands.iso import ISOCommands

# DummyHetzner braucht:
# list_isos(), get_iso_by_id(id),
# attach_iso_to_server(iso_id, server_id),
# detach_iso_from_server(server_id)

def test_list_builds_table():
    # assert "Name" in headers, "Type" in headers
    pass

def test_list_empty(capsys):
    # assert "No ISOs" in output
    pass

def test_show_info(capsys):
    # assert iso name, type, architecture in output
    pass

def test_show_info_missing_id(capsys):
    # assert "Missing" in output
    pass

def test_attach_iso(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.attach_iso(["10", "42"])
    # assert h.attach_calls == [(10, 42)]
    pass

def test_attach_missing_args(capsys):
    # cmd.attach_iso(["10"])  (server_id fehlt)
    # assert "Usage" in output
    pass

def test_detach_iso(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.detach_iso(["42"])
    # assert h.detach_calls == [42]
    pass

def test_detach_missing_id(capsys):
    # cmd.detach_iso([])
    # assert "Missing" in output
    pass
```

---

### `tests/commands/test_metrics.py`

```python
from commands.metrics import MetricsCommands

# DummyHetzner braucht:
# get_server_by_id(id),
# get_server_metrics(server_id, metric_type, start, end)
# Rückgabe z.B. {"time_series": {"cpu": {"values": [[ts, val], ...]}}}

def test_list_metrics_shows_available(capsys):
    # cmd.list_metrics(["1"])
    # assert "cpu" in output
    # assert "network" in output
    pass

def test_list_missing_id(capsys):
    # cmd.list_metrics([])
    # assert "Missing" in output
    pass

def test_cpu_metrics_default_hours(capsys):
    # cmd.show_cpu_metrics(["1"])
    # assert metric values / bar chart in output
    pass

def test_cpu_metrics_custom_hours(capsys):
    # cmd.show_cpu_metrics(["1", "--hours=48"])
    # assert output produced
    pass

def test_traffic_metrics(capsys):
    # cmd.show_traffic_metrics(["1"])
    # assert output produced
    pass

def test_disk_metrics(capsys):
    # cmd.show_disk_metrics(["1"])
    # assert output produced
    pass

def test_server_not_found(capsys):
    # h returns empty for get_server_by_id
    # assert "not found" in output
    pass
```

---

### `tests/commands/test_pricing.py`

```python
from commands.pricing import PricingCommands

# DummyHetzner braucht:
# get_pricing() -> Dict mit server_types, floating_ips, volumes, load_balancers etc.
# list_servers(), list_volumes(), list_floating_ips(), list_load_balancers()

def test_list_all_builds_tables():
    # cmd.list_pricing("all")
    # assert len(console.tables) >= 1
    pass

def test_list_server_category():
    # cmd.list_pricing("server")
    # assert title enthält "Server"
    pass

def test_list_invalid_category(capsys):
    # cmd.list_pricing("unknown")
    # assert "Unknown pricing category" in output
    pass

def test_calculate_shows_total(capsys):
    # h hat 2 Server, 1 Volume
    # cmd.calculate_costs()
    # assert "Total" in output
    pass

def test_calculate_empty_project(capsys):
    # h hat keine Ressourcen
    # cmd.calculate_costs()
    # assert "0" oder "No resources" in output
    pass
```

---

### `tests/commands/test_batch.py`

```python
from commands.batch import BatchCommands

# DummyHetzner braucht:
# get_server_by_id(id), start_server(id), stop_server(id),
# delete_server(id), create_snapshot(id)

def test_batch_start_multiple():
    # cmd.batch_start(["1,2,3"])
    # assert h.start_calls == [1, 2, 3]
    pass

def test_batch_start_space_separated():
    # cmd.batch_start(["1", "2", "3"])
    # assert h.start_calls == [1, 2, 3]
    pass

def test_batch_stop():
    # cmd.batch_stop(["1,2"])
    # assert h.stop_calls == [1, 2]
    pass

def test_batch_delete_confirmed(monkeypatch):
    # monkeypatch input -> "y"
    # cmd.batch_delete(["1,2"])
    # assert h.delete_calls == [1, 2]
    pass

def test_batch_delete_cancelled(monkeypatch):
    # monkeypatch input -> "n"
    # assert h.delete_calls == []
    pass

def test_batch_snapshot():
    # cmd.batch_snapshot(["1,2"])
    # assert h.snapshot_calls == [1, 2]
    pass

def test_batch_missing_ids(capsys):
    # cmd.batch_start([])
    # assert "Missing" in output
    pass

def test_batch_invalid_id(capsys):
    # cmd.batch_start(["1,abc,3"])
    # assert "invalid" in output (abc überspringen oder Fehler)
    pass

def test_batch_partial_failure(capsys):
    # h.start_server gibt bei id=2 False zurück
    # assert "failed" für id=2 in output
    # assert id=1 und id=3 wurden gestartet
    pass
```

---

### `tests/commands/test_project.py`

```python
from commands.project import ProjectCommands

# project.py liest ConfigManager direkt — Tests brauchen tmp_path Fixture
# für eine echte TOML-Datei (wie test_config.py es macht)

def test_list_projects(tmp_path, monkeypatch):
    # tmp_path / ".hicloud.toml" mit 2 Sektionen erstellen
    # monkeypatch DEFAULT_CONFIG_PATH -> tmp_path
    # cmd.list_projects()
    # assert beide Projektnamen in output
    pass

def test_list_no_config(tmp_path, monkeypatch, capsys):
    # monkeypatch DEFAULT_CONFIG_PATH -> nicht existierende Datei
    # assert "No configuration file" in output
    pass

def test_switch_project(monkeypatch, capsys):
    # cmd.switch_project(["1"])
    # assert Projekt gewechselt / hetzner token neu gesetzt
    pass

def test_switch_invalid_number(capsys):
    # cmd.switch_project(["99"])
    # assert "not found" oder "Invalid" in output
    pass

def test_show_info(capsys):
    # cmd.show_info()
    # assert aktiver Projekt-Name in output
    pass

def test_show_resources():
    # cmd.show_resources()
    # assert Tabellen für Server, Volumes etc. ausgegeben
    pass
```

---

## Integrations-Tests

**Datei:** `tests/integration/test_read_only.py`

Diese Tests laufen nur wenn `HETZNER_TOKEN` gesetzt ist und führen **ausschließlich lesende** API-Calls aus.

```python
import os
import pytest
from lib.api import HetznerCloudManager

pytestmark = pytest.mark.skipif(
    not os.environ.get("HETZNER_TOKEN"),
    reason="HETZNER_TOKEN not set — skip integration tests"
)


@pytest.fixture(scope="module")
def api():
    return HetznerCloudManager(os.environ["HETZNER_TOKEN"])


# --- Ressource-Listen ---

def test_list_servers(api):
    result = api.list_servers()
    assert isinstance(result, list)

def test_list_volumes(api):
    result = api.list_volumes()
    assert isinstance(result, list)

def test_list_networks(api):
    result = api.list_networks()
    assert isinstance(result, list)

def test_list_firewalls(api):
    result = api.list_firewalls()
    assert isinstance(result, list)

def test_list_load_balancers(api):
    result = api.list_load_balancers()
    assert isinstance(result, list)

def test_list_floating_ips(api):
    result = api.list_floating_ips()
    assert isinstance(result, list)

def test_list_primary_ips(api):
    result = api.list_primary_ips()
    assert isinstance(result, list)

def test_list_ssh_keys(api):
    result = api.list_ssh_keys()
    assert isinstance(result, list)

def test_list_images(api):
    result = api.list_images()
    assert isinstance(result, list)

def test_list_isos(api):
    result = api.list_isos()
    assert isinstance(result, list)

def test_list_locations(api):
    result = api.list_locations()
    assert isinstance(result, list)
    assert len(result) > 0  # Hetzner hat immer mindestens einen Standort

def test_list_datacenters(api):
    result = api.list_datacenters()
    assert isinstance(result, list)
    assert len(result) > 0

def test_list_server_types(api):
    result = api.list_server_types()
    assert isinstance(result, list)
    assert len(result) > 0

def test_get_pricing(api):
    result = api.get_pricing()
    assert isinstance(result, dict)
    assert "server_types" in result or "floating_ips" in result


# --- Einzelne Ressourcen (nur wenn vorhanden) ---

def test_get_first_server_if_exists(api):
    servers = api.list_servers()
    if not servers:
        pytest.skip("No servers in project")
    server = api.get_server_by_id(servers[0]["id"])
    assert server.get("id") == servers[0]["id"]

def test_get_first_volume_if_exists(api):
    volumes = api.list_volumes()
    if not volumes:
        pytest.skip("No volumes in project")
    volume = api.get_volume_by_id(volumes[0]["id"])
    assert volume.get("id") == volumes[0]["id"]

def test_get_first_floating_ip_if_exists(api):
    ips = api.list_floating_ips()
    if not ips:
        pytest.skip("No floating IPs in project")
    ip = api.get_floating_ip_by_id(ips[0]["id"])
    assert ip.get("id") == ips[0]["id"]
```

---

## Ausführen

```bash
# Alle Unit Tests
pytest -q

# Nur ein bestimmtes Modul
pytest tests/commands/test_vm.py -q

# Integrations-Tests (nur mit echtem Token)
HETZNER_TOKEN=your_token pytest tests/integration/ -q

# Alle Tests inkl. Integration
HETZNER_TOKEN=your_token pytest -q
```
