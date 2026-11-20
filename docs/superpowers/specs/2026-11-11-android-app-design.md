# Android-App „Heizung" — Design

Datum: 2026-11-11
Status: Entwurf zur Freigabe

## Wozu

Die Heizungskurven sollen auf dem Handy in zwei Sekunden da sein: Icon antippen,
Pufferspeicher steht. Heute kostet der Weg dorthin einen Browser, eine Adresse
und danach Zoomgesten, weil die Seite für den Desktop gebaut ist.

Die App ist außerdem der Ort für das, was später dazukommen soll: Widget mit
Live-Werten, Benachrichtigung, wenn der Kessel aus ist, irgendwann Schalten.
Eine WebView-Hülle könnte das nicht ohne Umbau.

## Ziele

- Vom Homescreen bis zur ersten Kurve: ein Tipp, keine Adresszeile.
- Alle vier Bereiche auf einem Bildschirm, Wechsel per Reiter — kein senkrechtes
  Scrollen, um an ein Diagramm zu kommen.
- Lesbar auf einem 360-dp-Telefon ohne Zoom: Kurven, Achsen, Legende.
- Verlauf verschieben: Tag/Woche umschalten, Tag zurück/vor, Pinch-Zoom,
  horizontales Wischen im Diagramm.
- Installation ohne Play Store; ein Update ist ein neuer APK-Download.

## Nicht-Ziele (erste Version)

- Kein Widget, keine Benachrichtigungen, kein Schalten oder Regeln.
- Kein Offline-Speicher: ohne Netz eine Meldung, keine alten Kurven.
- Nur Deutsch, nur Android, nur Lesen.
- Keine Änderung an der Python-API und an `src/heizung/static`.
- Kein Login: die App nutzt dieselbe offene HTTPS-Adresse wie der Browser.
- Kein Play-Store-Auftritt.

## Anti-Ziele

- **WebView-/Plotly-Hülle.** Die Darstellung soll nativ gezeichnet werden und
  ohne CDN auskommen; sonst wäre die App nur ein Lesezeichen mit Icon.
- **Arbeit für den Menschen.** Der Nutzer schreibt keinen Kotlin-Code und
  pflegt nichts; sein einziger Handgriff ist das Hinterlegen des
  Signatur-Secrets in GitHub.
- **Träge.** Kalter Start bis zur ersten Kurve über zwei Sekunden bei guter
  Verbindung gilt als Fehler.

## Randbedingungen

- Datenquelle: `GET {base}/api/chart?date=YYYY-MM-DD&period=day|week`.
  Antwort: JSON-Array von Zeilen `[unix_ts, 17 analoge, 11 digitale Werte]`,
  `null` für fehlende Werte, Spaltenreihenfolge fix (Anhang).
- Zeitfenster (so macht es die API bereits): heutiges Datum + `day` = letzte
  24 Stunden bis jetzt; anderes Datum + `day` = lokale Mitternacht bis
  Mitternacht; `week` = sieben Tage, endend mit dem Datum.
- Zeitstempel sind UNIX-Sekunden, Anzeige in lokaler Zeitzone (Europe/Berlin).
- Erreichbarkeit über HTTPS mit gültigem Zertifikat, von unterwegs und zu Hause.
- Bau und Auslieferung über GitHub Actions (Ubuntu-Runner), Release-Assets im
  öffentlichen Repo `zwotzie/raspberry-pi-heizung`.
- Technik: Kotlin, Jetpack Compose, minSdk 26, targetSdk 35.

## Entscheidungen des Menschen

1. Es wird eine echte Android-App, keine Web-Hülle.
2. Reiter **oben** unter dem Titel (Variante B der Entwürfe).
3. Keine Kästchen mit aktuellen Werten über dem Diagramm.
4. Legende **unten** als Chips, antippbar zum Ausblenden einer Kurve.
5. Gebaut wird über GitHub Actions, nicht lokal auf dem Mac.

## Entscheidungen des Builders (dürfen mit Begründung abweichen)

- Diagramm als eigener Compose-Canvas-Renderer statt Chart-Bibliothek: volle
  Kontrolle über Digitalbänder, Achsen und Gesten, keine Abhängigkeit, die
  später gegen die Wünsche arbeitet.
- Farben je Sensor fest und dunkel, an die Webseite angelehnt, damit beide
  Oberflächen gleich aussehen. Dunkler Hintergrund, kein Hell/Dunkel-Wechsel.
- Kein Fadenkreuz in der ersten Version (bewusst weggelassen, später möglich).
- Server-Adresse wird nicht einkompiliert: Einstellungsbildschirm, beim ersten
  Start einmal abgefragt, gespeichert in DataStore. Ein falsch geratener
  Hostname im Code wäre schlimmer als ein leeres Feld.
- Netzwerk: OkHttp, JSON mit kotlinx.serialization.
- Signierung mit eigenem Keystore, der als GitHub-Secret liegt; fehlt das
  Secret, wird mit dem Wegwerf-Debug-Schlüssel signiert und der Workflow weist
  darauf hin (dann ist vor jedem Update eine Deinstallation nötig).
- App-Name „Heizung", schlichtes eigenes Icon (Thermometer/Kessel-Silhouette),
  kein Store-Auftritt, keine Screenshots.

## Bildschirme

**Hauptbildschirm**

```
┌──────────────────────────────┐
│ Heizung                 ⟳    │  Titel + Datum (z. B. "Di, 11. Nov")
│ [Tag] [Woche]  ◀  Heute ▶    │  Zeitraum-Steuerung
│ Puffer │ Solar │ Heizung │ … │  TabRow, 4 Reiter
│                              │
│        Diagramm              │  analoge Kurven, y-Achse rechts
│                              │  darunter Digitalbänder
│ ● 1 Kopf ● 2 Oben ● 3 Unten  │  Legende-Chips, umbrechend
└──────────────────────────────┘
```

**Einstellungen** — Server-URL (Textfeld, Plausibilitätsprüfung auf `https://`),
Schaltfläche „Verbindung testen" (ruft `api/chart` für heute ab), App-Version.
Erreichbar über ein Icon in der Titelzeile.

**Zustände** — Laden (Fortschrittsanzeige im Diagrammbereich), Fehler (Meldung
plus „Erneut versuchen"), leer („Keine Daten für diesen Tag"), keine
Server-Adresse (Hinweis mit Knopf zu den Einstellungen).

## Verhalten im Detail

- Start: Reiter Puffer, Zeitraum Tag, Datum heute.
- „Heute" springt auf das heutige Datum; ◀/▶ verschieben um einen Tag, im
  Wochenmodus um sieben. Nach jedem Wechsel wird neu geladen.
- Wischen verschiebt den sichtbaren Zeitausschnitt innerhalb des geladenen
  Fensters; an den Rändern stoppt es (kein Nachladen in v1).
- Zwei Finger zoomen die Zeitachse, Doppeltipp setzt auf das volle Fenster
  zurück.
- Reiterwechsel zeigt sofort den bereits geladenen Datensatz; es wird nicht
  neu geladen.
- Legende: Chip antippen blendet die Kurve aus, erneut antippen holt sie
  zurück; der Zustand gilt je Reiter und nur für die laufende Sitzung.
- Digitale Zustände: gefüllte Stufenlinie (`hv`), eine schmale Zeile pro
  Signal, ohne eigene Beschriftung — die Zuordnung steht in der Legende.
- Achsen: x als Uhrzeit, im Wochenmodus als Wochentag; y rechts, Einheit aus
  der Serie (überwiegend °C, Solarstrahlung W/m², Drehzahlen %). Der
  y-Bereich wird aus den sichtbaren Daten bestimmt, mit einer Mindestspanne,
  damit eine flache Linie nicht zur Zickzack-Linie wird.
- Fehlende Werte (`null`) erzeugen Lücken, keine Verbindungslinie.

## Reihen je Reiter

Namen entsprechen den Metriknamen aus `src/heizung/metrics.py`; die
Zuordnung ist dieselbe wie in `src/heizung/static/uvr-charts.js`.

| Reiter | Analoge Kurven | Digitale Bänder |
|---|---|---|
| Puffer | `aussentemperatur`, `raum_rasp`, `speicher_1_kopf` … `speicher_5_boden` | — |
| Solar | `aussentemperatur`, `solar_strahlung`, `solar_vl`, `solar_ladepumpe_drehzahl` | `d_solar_kreispumpe`, `d_solar_ladepumpe`, `d_solar_freigabepumpe` |
| Heizung | `heizung_vl`, `heizung_rl`, `heizung_pumpe_drehzahl` | `d_heizung_pumpe`, `d_heizung_mischer_auf`, `d_heizung_mischer_zu` |
| Erzeuger | `kessel_rl`, `kessel_ladepumpe_drehzahl`, `kessel_betriebstemperatur`, `speicher_ladeleitung` | `heizung_an`, `d_kessel_ladepumpe`, `d_kessel_freigabe`, `d_kessel_mischer_auf`, `d_kessel_mischer_zu` |

Anzeigenamen (Legende, deutsch): Außen, Raum, 1 Kopf, 2 Oben, 3 Unten, 4 Mitte,
5 Boden, Solarstrahlung, VL Solar, Solarpumpe, VL Heizung, RL Heizung,
Heizungspumpe, RL Kessel, Kesselpumpe, Kesseltemperatur, Ladeleitung,
Heizung: Pumpe, Hz Mischer auf/zu, Kessel: Ladepumpe/Freigabe, Kessel Mischer
auf/zu, Solarkreispumpe, Solar: Ladepumpe, Solar: Freigabe, Heizung An.

## Bau und Auslieferung

- Neues Gradle-Projekt unter `android/`, unabhängig vom Python-Paket.
- `.github/workflows/android.yml`: Auslöser ist ein Tag `app-v*`; der Runner
  baut `assembleRelease`, signiert, erzeugt ein GitHub-Release und hängt die
  APK an. `versionCode` aus dem Tag, `versionName` ebenso.
- Einmalig vom Menschen: Keystore als Base64-Secret plus Passwörter in den
  Repo-Einstellungen hinterlegen (Anleitung liefert der Builder).
- Installation: Release-Seite im Handy-Browser öffnen, APK laden, „Unbekannte
  Quellen erlauben". Updates installieren sich über die alte Version.

## Was der Builder selbst entscheiden darf

- Aufbau der Compose-Hierarchie, Details des Canvas-Renderers, Gradle- und
  Bibliotheksversionen.
- Umfang der Tests: Einheitstests für JSON-Parsing, Zeitfenster und
  sichtbaren Ausschnitt gelten als Pflicht; UI-Tests sind optional.
- Aussehen des Icons, Feinheiten bei Abständen, Schriftgrößen, Farbtönen.

## Anhang: Spaltenreihenfolge der API

Analog (17): `kessel_rl`, `kessel_ladepumpe_drehzahl`,
`kessel_betriebstemperatur`, `speicher_ladeleitung`, `aussentemperatur`,
`raum_rasp`, `speicher_1_kopf`, `speicher_2_kopf`, `speicher_3_kopf`,
`speicher_4_mitte`, `speicher_5_boden`, `heizung_vl`, `heizung_rl`,
`heizung_pumpe_drehzahl`, `solar_strahlung`, `solar_vl`,
`solar_ladepumpe_drehzahl`.

Digital (11): `d_heizung_pumpe`, `d_kessel_ladepumpe`, `d_kessel_freigabe`,
`d_heizung_mischer_auf`, `d_heizung_mischer_zu`, `d_kessel_mischer_auf`,
`d_kessel_mischer_zu`, `d_solar_kreispumpe`, `d_solar_ladepumpe`,
`d_solar_freigabepumpe`, `heizung_an`.
