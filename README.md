# Raspberry Pi steuert Heizungsanforderung
This project runs on Raspberry Pi (Bookworm) and controls the heating request for my house.

## Setup

* `python3 -m venv <somewhere>` and `source <somewhere>/bin/activate`
* `pip install -e .[test]`

### DB einrichten (auf dem Postgres-Server)
psql -U heizung -d heizung -f migrations/001_initial.sql

### API-Dependencies installieren
pip install -e ".[api]"

### API starten (oder via Supervisor)
export HEIZUNG_DB_URL="postgresql://heizung:secret@db-host:5432/heizung"
uvicorn heizung.api:app --host 0.0.0.0 --port 8000


## Run locally

* `python -m heizung`
* optional after editable install: `heizung`

## Migration note (old -> new)

* old: `/path/to/venv/python /path/to/heizung.py`
* new: `python -m heizung`
* optional CLI (after `pip install -e .`): `heizung`

Configuration is loaded from `etc/heizung.conf` and logging from `etc/logging.conf`.

## Run tests

* `pytest`

## Supervisor (daemon mode)

This project is intended to run as a daemon via Supervisor.
A matching example is in `supervisor/conf.d/heizung.conf`.

The command should use the module entry point, for example:

`/home/pi/raspberry-pi-heizung/venv/bin/python -m heizung`

Advantages:

* automatic start after reboot
* automatic restart on unexpected exits

## GPIO

GPIO 23 closes the relay that starts the wood gasifier.

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