# Architekturhinweise

Sprache: [English](architecture.en.md) | [中文](architecture.zh-CN.md) | Deutsch

Dieses Dokument beschreibt die Implementierung. Für die tägliche Nutzung siehe
[README.de.md](../README.de.md).

SlopePing ist auf den Dienstplan-Workflow für Trainer der Neuss Skihalle im
Allrounder-Coach-Portal zugeschnitten.

## Module

- `run_checker.py`
  Einstiegspunkt. Fügt `src/` zu `sys.path` hinzu und ruft
  `slopeping.checker.run()` auf.
- `scripts/webhook_server.py`
  Startet den FastAPI Webhook- und Kontrollseiten-Server.
- `src/slopeping/config.py`
  Lädt `.env` und erstellt typisierte Einstellungen.
- `src/slopeping/browser.py`
  Verwaltet Playwright, Login, Navigation, Seitenwechsel und Screenshots.
- `src/slopeping/parser.py`
  Findet die Planungstabelle und wandelt Tabellenzeilen in Kursdatensätze um.
- `src/slopeping/state.py`
  Definiert Kursdatensätze, liest und schreibt `state.json` und vergleicht den
  aktuellen Lauf mit dem vorherigen.
- `src/slopeping/notify.py`
  Sendet ntfy-Benachrichtigungen mit Console-Fallback.
- `src/slopeping/webhook.py`
  Stellt die mobile Kontrollseite, Kalenderexport und geprüfte Remote-Aktionen
  bereit.
- `src/slopeping/ics_generator.py`
  Erstellt `.ics` Kalenderereignisse mit Europe/Berlin Zeitzone.

## Ablauf

1. Einstellungen aus `.env` laden.
2. Playwright Chromium starten.
3. Login-Seite öffnen.
4. Benutzername und Passwort ausfüllen.
5. `Anmelden` klicken.
6. `Meine Daten` -> `Arbeitsplan/Verfügbarkeit` öffnen.
7. Neue Planungsseite oder neuen Tab erkennen und dorthin wechseln.
8. Auf `table#TAB` oder den Text `Übersicht` warten.
9. Kurse parsen.
10. Screenshot speichern.
11. Vorherige Datensätze aus `state.json` laden.
12. Aktuelle und vorherige Datensätze vergleichen.
13. Bei Bedarf per ntfy benachrichtigen.
14. Aktuelle Datensätze in `state.json` speichern.

Wenn `--accept` oder `--decline` übergeben wird, läuft statt des normalen
Benachrichtigungs- und Speicherflusses ein Aktionsfluss:

1. Login und Planungsseite öffnen.
2. Tabellenzeilen und passende DOM-Zeilen parsen.
3. Kurs per `lesson_id`, vollem Hash-Key oder Hash-Präfix finden.
4. Aktion verweigern, wenn der Kurs nicht `pending` ist.
5. `Bestätigen` oder `Absagen` auswählen.
6. `Speichern` klicken.
7. Vorher-/Nachher-Screenshots speichern.
8. Eine JSON-Zeile an `actions.log` anhängen.

## Tabellenanalyse

Bevorzugter Selektor:

```text
table#TAB
```

Der Parser erwartet diese Spalten:

- `Tag`
- `Von`
- `Bis`
- `Raum/Ort`
- `Trainingsbezeichnung`
- `Bestätigung`

Jeder gelesene Kurs enthält zusätzlich:

- `confirmation_status`: `confirmed`, `pending` oder `unknown`
- `available_actions`: Aktionen aus dem Dropdown der Tabellenzeile

Regeln zur Statuserkennung:

- `confirmed`: die Bestätigungszelle enthält den Text `Bestätigt`
- `pending`: die Bestätigungszelle enthält ein `select` mit `Bestätigen` und
  `Absagen`
- `unknown`: keine der Regeln passt

Wenn `table#TAB` nicht sichtbar ist, sucht der Parser eine Tabelle nahe
`Übersicht` und danach Tabellen mit passenden Kopfzeilen.

## Änderungserkennung

Der stabile Schlüssel eines Kurses besteht aus:

```text
Tag + Von + Bis + Raum/Ort + Trainingsbezeichnung
```

Wenn dieser Schlüssel nicht in `state.json` vorhanden ist, gilt der Kurs als
neu.

Wenn der Schlüssel vorhanden ist, aber der komplette Datensatz anders ist, zum
Beispiel bei geänderter `Bestätigung`, gilt der Kurs als geändert.

Im normalen Modus werden neue Kurse und pending Kurse mit Handlungsbedarf
gemeldet. Für Tests kann man setzen:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

Dann sendet jeder erfolgreiche Lauf einen aktuellen Bericht.

Wenn ein gemeldeter Kurs pending ist, lautet der Benachrichtigungstitel:

```text
SlopePing: action needed
```

SlopePing wählt nicht automatisch `Bestätigen` oder `Absagen` und klickt nicht
auf `Speichern`.

Bei einem normalen Lauf werden pending Kurse mit kopierbaren Befehlen im
Terminal ausgegeben:

```bash
python run_checker.py --accept "LESSON_ID"
python run_checker.py --decline "LESSON_ID"
```

## Mobile Kontrollseite

Wenn `ACTION_WEBHOOK_BASE_URL` und `ACTION_WEBHOOK_TOKEN` konfiguriert sind,
fügt ntfy sichere Links hinzu:

- `Open SlopePing`: öffnet `/control?token=...`
- `Open calendar page`: öffnet `/calendar?token=...`

Die Benachrichtigung führt Bestätigen oder Absagen nicht direkt aus. Kontroll-
und Kalenderseite lesen standardmäßig den zuletzt gespeicherten `state.json`
Snapshot, sodass das Öffnen der Seite Playwright nicht startet.
`/actions/execute` meldet sich nach der zweiten Bestätigung an, prüft die Live-
Allrounder-Seite erneut und speichert erst danach.

Der Webhook-Aktionspfad verwendet eine prozesslokale Sperre, sodass immer nur
eine Remote-Aktion gleichzeitig laufen kann.

## ntfy-Benachrichtigung

Das Projekt sendet Plain Text per POST an:

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

Die Nachricht enthält:

- Aktuelle Kurse im Testbericht-Modus
- Neue Kurse zur Bestätigung
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- `confirmation_status`
- `available_actions`

Wenn ntfy nicht konfiguriert ist oder das Senden fehlschlägt, wird dieselbe
Nachricht in der Konsole ausgegeben und das Programm läuft weiter.

## Laufzeitdateien

- `.env`
  Lokale Zugangsdaten und Konfiguration. Von Git ignoriert.
- `state.json`
  Letzter erfolgreich gelesener Kursstand. Von Git ignoriert.
- `screenshots/`
  Erfolgs- und Fehler-Screenshots. Von Git ignoriert.
- `actions.log`
  JSON-Line-Historie für CLI- und Webhook-Aktionen. Von Git ignoriert.
- `calendar_events/`
  Generierte `.ics` Dateien für Webhook-Aktionen. Von Git ignoriert.

## Sicherheit

- `.env` nicht committen.
- `NTFY_TOPIC` lang und privat wählen.
- Der öffentliche Dienst `ntfy.sh` schützt Topics standardmäßig nicht mit einem
  Passwort.
- Das Skript druckt Fortschrittsmeldungen, aber kein Passwort.
- Der Webhook-Server hört standardmäßig auf `127.0.0.1`. `0.0.0.0` nur in
  einem vertrauenswürdigen Netzwerk oder hinter einem gesicherten Tunnel nutzen.
- Der Webhook-Token steht weiterhin in URLs. Den Server daher nicht ohne HTTPS
  und stärkere Authentifizierung öffentlich erreichbar machen.
