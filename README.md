Ein leistungsstarkes, interaktives Kommandozeilen-Tool zur Verwaltung von Hetzner Cloud Ressourcen. Mit hicloud können Sie VMs erstellen und verwalten, Snapshots und Backups erstellen, und viele weitere Aktionen durchführen - alles von der Kommandozeile aus.
Inhaltsverzeichnis

Installation
Konfiguration
Interaktive Konsole
Befehlsreferenz

VM-Befehle
Snapshot-Befehle
Backup-Befehle
Allgemeine Befehle


Erweiterte Funktionen

Tab-Completion
Befehlsverlauf


Beispiele
Fehlerbehebung

Installation
Systemvoraussetzungen

Python 3.6 oder höher
pip (Python-Paketmanager)
Hetzner Cloud API-Token

Installation der erforderlichen Pakete
bash# Linux/macOS
pip install requests toml

# Windows
pip install requests toml pyreadline3
Installation von hicloud
bash# Repository klonen
git clone https://github.com/rtulke/hicloud.git
cd hicloud

# Script ausführbar machen
chmod +x hicloud.py

# Optional: Systemweit verfügbar machen
sudo ln -s $(pwd)/hicloud.py /usr/local/bin/hicloud
Verwendung mit virtualenv (empfohlen)
bash# Virtuelles Environment erstellen
python3 -m venv venv

# Environment aktivieren (Linux/macOS)
source venv/bin/activate

# Environment aktivieren (Windows)
.\venv\Scripts\activate

# Abhängigkeiten installieren
pip install requests toml
Konfiguration
hicloud verwendet TOML-Konfigurationsdateien, um API-Tokens und Projekteinstellungen zu speichern.
Generieren einer Beispielkonfiguration
bash./hicloud.py --gen-config ~/.hicloud.toml
Dieser Befehl erstellt eine Beispielkonfigurationsdatei mit den richtigen Berechtigungen (chmod 600).
Konfigurationsformat
toml[default]
api_token = "your_api_token_here"
project_name = "default"

[project1]
api_token = "project1_api_token"
project_name = "Production"

[project2]
api_token = "project2_api_token"
project_name = "Development"
Sicherheitshinweise

Die Konfigurationsdatei muss mit 600-Berechtigungen geschützt sein (chmod 600 ~/.hicloud.toml)
Der API-Token gewährt vollen Zugriff auf Ihre Hetzner Cloud-Ressourcen
Es wird empfohlen, Tokens mit begrenzten Berechtigungen zu verwenden

Interaktive Konsole
hicloud bietet eine interaktive Konsole zur Verwaltung Ihrer Hetzner Cloud-Ressourcen.
Starten der interaktiven Konsole
bash# Standardkonfiguration verwenden (~/.hicloud.toml)
./hicloud.py

# Bestimmte Konfigurationsdatei angeben
./hicloud.py --config myproject.toml

# Bestimmtes Projekt aus der Konfigurationsdatei verwenden
./hicloud.py --project project1

# API-Token direkt übergeben (umgeht Konfigurationsdatei)
./hicloud.py --token your_api_token_here
Konsolen-Features

Farbige Ausgabe für bessere Lesbarkeit
Tab-Completion für Befehle und Unterbefehle
Befehlshistorie mit Pfeiltasten-Navigation
Kontextbezogene Hilfe
Bestätigungsabfragen für kritische Operationen

Befehlsreferenz
VM-Befehle
BefehlBeschreibungParameterBeispielvm listListet alle VMs aufkeinevm listvm info <id>Zeigt detaillierte Informationen zu einer VM<id>: ID der VMvm info 123456vm createStartet den interaktiven VM-Erstellungsprozesskeinevm createvm start <id>Startet eine VM<id>: ID der VMvm start 123456vm stop <id>Stoppt eine VM<id>: ID der VMvm stop 123456vm delete <id>Löscht eine VM<id>: ID der VMvm delete 123456
VM-Erstellungsoptionen
Beim Ausführen von vm create werden folgende Optionen abgefragt:
OptionBeschreibungNameDer Name der VMServer-TypCPU-Kerne, RAM und FestplattengrößeImageBetriebssystem (z.B. Ubuntu, Debian, CentOS)StandortRechenzentrum (z.B. Nürnberg, Helsinki, Falkenstein)SSH-KeysSSH-Keys für den Zugriff (optional)IP-VersionIPv4, IPv6 oder beidesRoot-PasswortAutomatisch generiertes Root-Passwort (optional)
Snapshot-Befehle
BefehlBeschreibungParameterBeispielsnapshot listListet alle Snapshots aufkeinesnapshot listsnapshot create <id>Erstellt einen Snapshot einer VM<id>: ID der VMsnapshot create 123456snapshot delete <id>Löscht einen Snapshot<id>: ID des Snapshotssnapshot delete 987654snapshot delete all <id>Löscht alle Snapshots einer VM<id>: ID der VMsnapshot delete all 123456
Backup-Befehle
BefehlBeschreibungParameterBeispielbackup listListet alle Backups aufkeinebackup listbackup enable <id> [WINDOW]Aktiviert automatische Backups für eine VM<id>: ID der VM<br>[WINDOW]: Backup-Fenster (optional)backup enable 123456 22-02backup disable <id>Deaktiviert automatische Backups für eine VM<id>: ID der VMbackup disable 123456backup delete <id>Löscht ein Backup<id>: ID des Backupsbackup delete 987654
Backup-Fenster
Beim Aktivieren von automatischen Backups können Sie ein Backup-Fenster angeben:
FensterZeitrahmen (UTC)22-0222:00 - 02:00 Uhr02-0602:00 - 06:00 Uhr06-1006:00 - 10:00 Uhr10-1410:00 - 14:00 Uhr14-1814:00 - 18:00 Uhr18-2218:00 - 22:00 Uhr
Allgemeine Befehle
BefehlBeschreibungParameterBeispielproject, infoZeigt Informationen zum aktuellen ProjektkeineprojecthistoryZeigt den Befehlsverlauf ankeinehistoryhistory clearLöscht den Befehlsverlaufkeinehistory clearclearLöscht den BildschirmkeineclearhelpZeigt Hilfeinformationen ankeinehelpexit, quit, qBeendet das Programmkeineexit
Erweiterte Funktionen
Tab-Completion
hicloud bietet eine umfassende Tab-Completion-Unterstützung:

Hauptbefehle: Drücken Sie <Tab>, um verfügbare Befehle anzuzeigen
hicloud> <Tab>
backup  clear   exit    help    history info    project quit    q       snapshot vm

Unterbefehle: Nach Eingabe eines Hauptbefehls zeigt <Tab> die verfügbaren Unterbefehle an
hicloud> vm <Tab>
create  delete  info    list    start   stop

Teilwortsuche: Geben Sie den Anfang eines Befehls ein und drücken Sie <Tab>
hicloud> vm st<Tab>
start   stop

Kontextbezogene Hilfe: Bei der Vervollständigung werden Hinweise zum Befehl angezeigt
hicloud> vm <Tab>
VM commands: list, info <id>, create, start <id>, stop <id>, delete <id>


Befehlsverlauf
hicloud speichert Ihre Befehlshistorie in ~/.tmp/hicloud/history:

Navigation: Verwenden Sie die Pfeiltasten ↑ und ↓, um durch vorherige Befehle zu navigieren
Anzeigen: Mit history können Sie den gesamten Befehlsverlauf anzeigen
Löschen: Mit history clear können Sie den Befehlsverlauf löschen
Persistenz: Die Geschichte wird zwischen Sitzungen gespeichert (maximal 1000 Befehle)

Beispiele
VM-Verwaltung
# VM-Liste anzeigen
hicloud> vm list
Virtual Machines:
ID         Name                           Status     Type            IP              Location
------------------------------------------------------------------------------------------
123456     web-server                     running    cx21            203.0.113.10    nbg1

# VM erstellen
hicloud> vm create
Name: new-server
...

# VM starten
hicloud> vm start 123456
Starting VM 'web-server' (ID: 123456)...
Waiting for server to start...
.........
VM 123456 started successfully

# VM stoppen
hicloud> vm stop 123456
Stopping VM 'web-server' (ID: 123456)...
Waiting for server to stop...
.........
VM 123456 stopped successfully

# VM-Details anzeigen
hicloud> vm info 123456
...
Snapshot-Verwaltung
# Snapshot erstellen
hicloud> snapshot create 123456
Creating snapshot for VM 'web-server' (ID: 123456)...
Waiting for snapshot creation to complete...
.........
Snapshot created successfully with ID 987654

# Snapshots anzeigen
hicloud> snapshot list
Snapshots:
ID         Name                                                  Created             Size         Server ID
-----------------------------------------------------------------------------------------------------------
987654     web-server snapshot                                   2025-05-08T15:32:45 35.50 GB     123456

# Snapshot löschen
hicloud> snapshot delete 987654
Are you sure you want to delete snapshot 987654? [y/N]: y
Deleting snapshot 987654...
Snapshot 987654 deleted successfully
Backup-Verwaltung
# Backups anzeigen
hicloud> backup list
Backups:
ID         Name                                                  Created             Size         Server ID
-----------------------------------------------------------------------------------------------------------
123789     web-server backup                                     2025-05-08T02:15:30 15.25 GB     123456

# Automatische Backups aktivieren
hicloud> backup enable 123456 22-02
Enabling automatic backups for VM 'web-server' (ID: 123456)...
Waiting for backup enablement to complete...
.........
Automatic backups enabled successfully for VM 123456

# Automatische Backups deaktivieren
hicloud> backup disable 123456
Disabling automatic backups for VM 'web-server' (ID: 123456)...
Waiting for backup disablement to complete...
.........
Automatic backups disabled successfully for VM 123456
Projektinformationen
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
Fehlerbehebung
Häufige Probleme
ProblemLösung"No configuration file found"Erstellen Sie eine Konfigurationsdatei mit --gen-config oder geben Sie einen Token direkt mit --token an"Insecure permissions on ~/.hicloud.toml"Setzen Sie die richtigen Berechtigungen mit chmod 600 ~/.hicloud.toml"Connection Status: Error"Überprüfen Sie Ihren API-Token und Ihre Internetverbindung"No VMs found"Stellen Sie sicher, dass Sie das richtige Projekt ausgewählt habenTab-Completion funktioniert nichtInstallieren Sie unter Windows pyreadline3 mit pip install pyreadline3History-Verzeichnis konnte nicht erstellt werdenÜberprüfen Sie die Schreibrechte in Ihrem Home-Verzeichnis
Debugging

Verwenden Sie --token, um die Konfigurationsdatei zu umgehen und direkt mit einem Token zu arbeiten
Prüfen Sie die Berechtigungen des API-Tokens in der Hetzner Cloud Console
Bei Problemen mit der Befehlshistorie löschen Sie den Ordner ~/.tmp/hicloud und starten Sie neu

Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe LICENSE für Details.
