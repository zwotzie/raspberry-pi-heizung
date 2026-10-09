# Raspberry Pi steuert Heizungsanforderung
This project runs on Raspberry Pi (Bookworm/Trixie) and controls the heating request for my house.

## Architektur

```
BL-NET ──TCP──▶ Poller-Thread (60 s) ──▶ Puffer (30 min) ──▶ Regelung ──▶ Relais (GPIO)
                     │
                     └──▶ Snapshot ──▶ VictoriaMetrics ◀── API / Grafana
                                     ▲
                         Push-Modus:  Push nach jedem Poll (push_url, empfohlen)
                         Scrape-Modus: Exporter auf :9100, Scrape 30 s (Standard)
```

* **Daemon** (`python -m heizung`, systemd `Type=notify` mit Watchdog), zwei entkoppelte Teile:
  * *Poller-Thread*: holt alle 60 s (fester Takt, 3 Versuche) die UVR1611-Werte vom BL-NET,
    füllt den Puffer der letzten 30 Minuten und aktualisiert den Metrics-Snapshot.
  * *Regelung* (Hauptthread): bewertet den Puffer, schaltet das Relais (Holzvergaser / Pellets);
    ohne aktuelle Daten (>30 min) wird der Kessel ausgeschaltet.
  * *Metrics*: der letzte Snapshot liegt als Prometheus-Samples vor (veraltete Daten
    (`metrics_stale_after`) werden nicht ausgegeben, dazu `heizung_up` und Health-Metriken).
    Delivery ans TSDB entweder per **Push** an VictoriaMetrics (optional, `push_url`)
    oder per **Scrape** eines lokalen HTTP-Exporters (Standard, Port `metrics_port`, 9100).
* **VictoriaMetrics** (bzw. Prometheus im Scrape-Modus, Beispiel: `prometheus/heizung.yml`)
  empfängt die Daten.
* **API** (`uvicorn heizung.api:app`): liefert `GET /api/chart?date=&period=` aus dem TSDB
  und das statische Dashboard unter `/`. Grafana-Dashboard: `grafana/dashboard-heizung.json`,
  Reverse-Proxy-Beispiel: `traefik/heizung.yml`.

## Logging

Der Daemon loggt per `logging` in `/var/log/heizung/heizung.log` (tägliche Rotation, 14 Tage;
siehe `etc/logging.conf`). Die systemd-Unit legt das Verzeichnis per `LogsDirectory=heizung` an.
Im Journal (`journalctl -u heizung`) erscheinen nur noch Start-/Absturzmeldungen (stderr).

## Setup

Mit [uv](https://docs.astral.sh/uv/) (empfohlen, `uv.lock` liegt im Repo):

```bash
uv sync --extra test          # legt .venv an und installiert exakt die Versionen aus uv.lock
uv sync --extra test --extra dev --extra backfill   # optional weitere Extras
uv run python -m heizung      # Befehle ohne manuelles Aktivieren des venv ausführen
uv run pytest
```

Auf dem Raspberry Pi zusätzlich `--extra raspberry_pi` (siehe Abschnitt GPIO).
Extras: `test`, `dev` (ruff, mypy), `backfill` (pymysql), `raspberry_pi` (lgpio).

Alternativ mit pip:

* `python3 -m venv venv` und `source venv/bin/activate`
* `pip install -e .[test]`

### Installation auf Pi Zero / Pi 1 (armv6l, piwheels)

Für `armv6l` (`uname -m`) gibt es auf PyPI kaum Wheels; Kompilieren (z. B. `pydantic-core`,
`uvloop`) scheitert an RAM. Stattdessen Wheels von [piwheels](https://www.piwheels.org) nutzen
und `uv sync` vermeiden (`uv.lock` kennt nur PyPI-URLs):

```bash
sudo apt install python3-lgpio
python3 -m venv --system-site-packages venv
venv/bin/pip install --only-binary :all: --extra-index-url https://www.piwheels.org/simple \
  requests fastapi uvicorn prometheus-client
venv/bin/pip install htmldom PyBLNET      # htmldom ist reines Python (nur sdist), wird lokal gebaut
venv/bin/pip install --no-deps -e .
```

`--only-binary :all:` bricht ab, statt zu kompilieren. Fehlt für ein Paket ein Wheel, eine
ältere Version fixieren, die bei piwheels vorhanden ist (`https://www.piwheels.org/project/<paket>/`).
`lgpio` kommt aus apt (`--system-site-packages`), nicht aus dem Extra `raspberry_pi`.

### Troubleshooting: `uv sync` bricht ab / Pi rebootet

Spontane Reboots während `uv sync` deuten meist auf Unterspannung (Netzteil) oder
RAM-Mangel hin, ausgelöst durch das Kompilieren von `lgpio`.

1. Diagnose:
   ```bash
   vcgencmd get_throttled        # 0x0 = ok, sonst Unterspannung/Überhitzung
   dmesg -T | grep -iE "voltage|oom|killed"
   free -h
   journalctl -b -1 | tail -50   # Log vor dem Reboot
   ```
2. Netzteil prüfen: Original-Netzteil (Pi 4: 5V/3A, Pi 5: 5A) und gutes Kabel;
   Lastspitzen beim Kompilieren überfordern schwache Netzteile.
3. Swap vergrößern (bei ≤ 1 GB RAM):
   ```bash
   sudo dphys-swapfile swapoff
   sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
   sudo dphys-swapfile setup && sudo dphys-swapfile swapon
   ```
4. Last reduzieren:
   ```bash
   UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=1 MAKEFLAGS="-j1" uv sync --extra raspberry_pi
   ```
5. Kompilieren vermeiden: Build-Tools vorab installieren
   (`sudo apt install build-essential swig liblgpio-dev`) oder `lgpio` per apt
   (`python3-lgpio`) nutzen und das venv mit `--system-site-packages` anlegen.
   Nur benötigte Extras syncen (kein `--all-extras`).
6. Außerdem prüfen: Temperatur (`vcgencmd measure_temp`) und SD-Karte
   (`sudo dmesg | grep mmc`).

Konfiguration:

* `etc/sample_heizung.conf` nach `etc/heizung.conf` kopieren und anpassen
  (`blnet_host`, `operating_mode`, `metrics_port`, `prometheus_url`, optional `push_url`).
  Logging wird aus `etc/logging.conf` geladen.
* Optional: `HEIZUNG_CONFIG_PATH` setzt das Verzeichnis, das `etc/` enthält
  (Standard: Verzeichnis des gestarteten Skripts).

## Lokal starten

* Daemon: `uv run python -m heizung` bzw. `python -m heizung` (oder `heizung`)
* API: `uv run uvicorn heizung.api:app --host 0.0.0.0 --port 8000`

## Tests

* `uv run pytest` bzw. `pytest`
* Lint/Typen (Extra `dev`): `uv run ruff check .` und `uv run mypy src`
* CI: `.github/workflows/python-tests.yml` (Python 3.11/3.13 und Debian Bookworm)

## Metriken: Push (empfohlen) oder Scrape (Standard)

Der Daemon stellt pro Sensor ein Sample bereit (Namen wie `aussentemperatur`,
`speicher_1_kopf`, `d_kessel_ladepumpe`, …; Definition in `src/heizung/metrics.py`)
sowie Health-Metriken: `heizung_up`, `heizung_data_age_seconds`,
`heizung_poll_errors_total`, `heizung_poll_duration_seconds`,
`heizung_operating_mode{mode=…}`. Die Werte kommen aus dem Poller-Thread, der
alle 60 s (feste Taktung, 3 Versuche à 5 s Abstand) die Daten vom BL-Net holt; die
Regelung liest nur den Puffer.

### Push-Modus (empfohlen, VictoriaMetrics)

Optional in `etc/heizung.conf` setzen (`etc/sample_heizung.conf` als Vorlage):

```
push_url="http://victoriametrics.lan:8428"
push_job="heizung"        # optional, Standard: heizung
push_instance="heizung"   # optional, Standard: heizung
```

Der Daemon pusht nach jedem BL-Net-Poll den Snapshot per
`POST {push_url}/api/v1/import/prometheus` nach VictoriaMetrics – exakt das
Format des Backfill-Tools (`tools/backfill_to_victoriametrics.py`). Im
Push-Modus wird der lokale Scrape-HTTP-Server (`:9100`) NICHT mehr gestartet.
Push-Fehler (z. B. VM kurzzeitig down) werden nur geloggt und brechen den
Poll-Loop nicht ab.

### Scrape-Modus (Standard, ohne `push_url`)

Der Daemon stellt auf `metrics_port` (Standard 9100) einen Prometheus-Exporter
bereit; Prometheus (oder VictoriaMetrics/vmagent) scrapt das:
`prometheus/heizung.yml` als `scrape_configs`-Eintrag in die eigene
`prometheus.yml` übernehmen (Job `heizung`, Intervall 30s, Target `<pi-host>:9100`).

### Staleness (beide Modi)

Ist der letzte erfolgreiche Poll älter als `metrics_stale_after`
(Standard 180 s, optional in `[heizung]`), werden keine Sensorwerte mehr
exportiert bzw. gepusht (Lücke statt veralteter Linie) und `heizung_up` ist
0. Dashboards/Alerts sollten auf `heizung_up == 1` bzw.
`heizung_data_age_seconds` filtern. Ohne aktuelle Daten (>30 min) schaltet die
Regelung den Kessel aus.

Zusätzlich:

* `prometheus_url` in `etc/heizung.conf` muss auf die Instanz zeigen, aus der
  die API die Chart-Daten abfragt – im Push-Modus dieselbe VictoriaMetrics
  wie `push_url`.
* systemd (`Type=notify`, `WatchdogSec=300`) startet den Daemon neu, wenn der
  Poller hängt. Alert-Beispiele stehen in `prometheus/heizung.yml`.

## Grafana

`grafana/dashboard-heizung.json` (UID `heizung-uvr1611`) in Grafana importieren
(Dashboards → New → Import). Es nutzt eine Prometheus-kompatible Datenquelle
(Prometheus oder VictoriaMetrics), die über die Variable `datasource` gewählt wird, und
filtert auf `job="heizung"`. Panels: Pufferspeicher, Solar, Heizung, Wärmeerzeuger
(jeweils analog und digital).

## Traefik / Dashboard

Die API liefert das eingebaute Dashboard (`/`, `src/heizung/static/`) und `/api/chart`.
`traefik/heizung.yml` ist ein Beispiel für die dynamische Traefik-Konfiguration:
Host `heizung.domain.de` → uvicorn auf `host.docker.internal:8000` (systemd-Dienst
`heizung-api`). Hostname, Entrypoint und Ziel-URL anpassen; TLS/Auth nach Bedarf ergänzen,
da die API keine eigene Authentifizierung hat.

## Betrieb mit systemd

Beide Dienste laufen als systemd-Units (Beispiele in `systemd/`):

* `systemd/heizung.service` – Daemon (`python -m heizung`)
* `systemd/heizung-api.service` – API (uvicorn)

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now heizung heizung-api
```

Pfade (`/home/pi/raspberry-pi-heizung`) und User in den Units bei Bedarf anpassen.
Vorteile: automatischer Start nach Reboot und Neustart bei unerwartetem Beenden.
Änderungen an `operating_mode` werden mit `sudo systemctl restart heizung` übernommen.

## Historische Daten importieren (optional)

Alte Daten aus einer MySQL-Datenbank lassen sich nach VictoriaMetrics übernehmen
(`uv sync --extra backfill` bzw. `pip install -e .[backfill]`):

* `tools/mysql-export.sh` – Export als gzip-CSV (auf dem DB-Host)
* `tools/backfill_to_victoriametrics.py <datei.csv.gz> [--vm-url ...]` – Import;
  `tools/backfill-csv.sh` ruft ihn für mehrere Jahre auf.

## GPIO

GPIO 23 closes the relay that starts the wood gasifier.

On the Raspberry Pi (Debian Trixie / Python 3.13) the relay is driven via the
[`lgpio`](https://pypi.org/project/lgpio/) library:

```bash
sudo apt install python3-lgpio   # recommended on Trixie
# or, inside the venv:
pip install '.[raspberry_pi]'
```

### Developing off-device (macOS / Windows)

`lgpio` only builds on Linux (it needs `linux/gpio.h`), so it cannot be
installed on macOS/Windows. For local development a no-op stub lives in
`dev_stubs/lgpio.py`. Make `import lgpio` resolve to it by putting the folder
on the interpreter path, e.g. via a `.pth` file in your venv:

```bash
echo "$(pwd)/dev_stubs" > "$(python -c 'import site; print(site.getsitepackages()[0])')/lgpio-dev-stub.pth"
```

The stub logs every GPIO call instead of touching real hardware.


## Acknowledgment

Thanks to Erik Bartmann for his inspiring book "Die elektronische Welt mit Raspberry Pi entdecken"

```text
19-01-26 00:02:24.663  INFO     aussentemperatur          : 1.6
19-01-26 00:02:24.665  INFO     d_heizung_mischer_auf     : 0
19-01-26 00:02:24.667  INFO     d_heizung_mischer_zu      : 0
19-01-26 00:02:24.669  INFO     d_heizung_pumpe           : 1
19-01-26 00:02:24.671  INFO     d_kessel_freigabe         : 0
19-01-26 00:02:24.673  INFO     d_kessel_ladepumpe        : 0
19-01-26 00:02:24.674  INFO     d_kessel_mischer_auf      : 0
19-01-26 00:02:24.676  INFO     d_kessel_mischer_zu       : 0
19-01-26 00:02:24.678  INFO     d_solar_freigabepumpe     : 0
19-01-26 00:02:24.680  INFO     d_solar_kreispumpe        : 0
19-01-26 00:02:24.682  INFO     d_solar_ladepumpe         : 0
19-01-26 00:02:24.684  INFO     heizung_d                 : 30
19-01-26 00:02:24.686  INFO     heizung_rl                : 26.6
19-01-26 00:02:24.688  INFO     heizung_vl                : 29.4
19-01-26 00:02:24.690  INFO     kessel_betriebstemperatur : 36.6
19-01-26 00:02:24.692  INFO     kessel_d_ladepumpe        : 0
19-01-26 00:02:24.694  INFO     kessel_rl                 : 27.7
19-01-26 00:02:24.696  INFO     raum_rasp                 : 20.3
19-01-26 00:02:24.698  INFO     solar_d_ladepumpe         : 0
19-01-26 00:02:24.699  INFO     solar_strahlung           : 0
19-01-26 00:02:24.701  INFO     solar_vl                  : 34
19-01-26 00:02:24.703  INFO     speicher_1_kopf           : 75.2
19-01-26 00:02:24.705  INFO     speicher_2_kopf           : 69
19-01-26 00:02:24.707  INFO     speicher_3_kopf           : 37.8
19-01-26 00:02:24.709  INFO     speicher_4_mitte          : 26.5
19-01-26 00:02:24.711  INFO     speicher_5_boden          : 26.3
19-01-26 00:02:24.712  INFO     speicher_ladeleitung      : 31.9
19-01-26 00:02:24.714  INFO     timestamp                 : 1548457290
19-01-26 00:02:24.716  INFO     datetime                  : 2019-01-26 00:01:30
```