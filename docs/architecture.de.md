# Architekturhinweise

Sprache: [English](architecture.en.md) | [中文](architecture.zh-CN.md) | Deutsch

Dieses Dokument beschreibt die Implementierung. Für die tägliche Nutzung siehe
[README.de.md](../README.de.md).

SlopePing ist auf den Dienstplan-Workflow für Trainer der Neuss Skihalle im
Allrounder-Coach-Portal zugeschnitten.

## Module

- `run_checker.py`
  Kompatibilitätseinstieg. Fügt `src/` zu `sys.path` hinzu und ruft
  `slopeping.cli.main()` auf.
- `scripts/webhook_server.py`
  Kompatibilitätseinstieg für `slopeping.server.main()`.
- `src/slopeping/cli.py`
  Definiert CLI-Argumente und leitet Aktionen an `slopeping.checker.run()` weiter.
- `src/slopeping/server.py`
  Lädt und prüft Webhook-Server-Einstellungen und startet Uvicorn.
- `src/slopeping/config.py`
  Lädt `.env`, typisierte Einstellungen und zentrale `var/` Laufzeitpfade.
- `src/slopeping/browser.py`
  Verwaltet Playwright, Login, Navigation, Seitenwechsel und Screenshots.
- `src/slopeping/parser.py`
  Findet die Planungstabelle und wandelt Tabellenzeilen in Kursdatensätze um.
- `src/slopeping/state.py`
  Definiert Kursdatensätze, liest und schreibt `var/state.json` mit Sicherung
  und vergleicht den aktuellen Lauf mit dem vorherigen.
- `src/slopeping/notify.py`
  Sendet ntfy-Benachrichtigungen mit Console-Fallback.
- `src/slopeping/webhook.py`
  Definiert FastAPI-Routen und koordiniert Cache, Kalenderexport und geprüfte
  Remote-Aktionen.
- `src/slopeping/web_views.py`
  Rendert Kontroll-, Bestätigungs-, Ergebnis- und Kalenderseiten.
- `src/slopeping/execution_lock.py`
  Stellt eine prozessübergreifende Browsersperre für Checker, CLI und Webhook bereit.
- `src/slopeping/health.py` und `src/slopeping/retry.py`
  Speichern Laufstatus und wiederholen nur behebbare temporäre Fehler.
- `src/slopeping/maintenance.py`
  Löscht alte Screenshots/Kalenderdateien und rotiert zu große Protokolle.
- `src/slopeping/security.py` und `src/slopeping/replay.py`
  Erzeugen kurzlebige HMAC-Token und verhindern wiederholte Aktionsformulare.
- `src/slopeping/runtime_migration.py`
  Migriert alte Laufzeitdaten sicher nach `var/`.
- `src/slopeping/ui_preview.py`
  Erzeugt mit anonymen Kursen und denselben Templates Offline-HTML und mobile
  Screenshots, ohne auf das Portal zuzugreifen.
- `scripts/generate_ui_previews.py`
  Entwicklungs- und Dokumentationseinstieg für UI-Vorschauen, kein
  Produktionsdienst.
- `src/slopeping/ics_generator.py`
  Erstellt `.ics` Kalenderereignisse mit Europe/Berlin Zeitzone.

Die einzigen offiziellen Laufzeiteinstiege sind `run_checker.py` und
`scripts/webhook_server.py`. `scripts/run_checker.sh` und
`scripts/run_webhook_server.sh` dienen nur als launchd-Wrapper.

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
11. Vorherige Datensätze aus `var/state.json` laden.
12. Aktuelle und vorherige Datensätze vergleichen.
13. Bei Bedarf per ntfy benachrichtigen.
14. Aktuelle Datensätze in `var/state.json` speichern und die vorige Version sichern.

Wenn `--accept` oder `--decline` übergeben wird, läuft statt des normalen
Benachrichtigungs- und Speicherflusses ein Aktionsfluss:

1. Login und Planungsseite öffnen.
2. Tabellenzeilen und passende DOM-Zeilen parsen.
3. Kurs per `lesson_id`, vollem Hash-Key oder Hash-Präfix finden.
4. Aktion verweigern, wenn der Kurs nicht `pending` ist.
5. `Bestätigen` oder `Absagen` auswählen.
6. `Speichern` klicken.
7. Vorher-/Nachher-Screenshots speichern.
8. Eine JSON-Zeile an `var/actions.log` anhängen.

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

Wenn dieser Schlüssel nicht in `var/state.json` vorhanden ist, gilt der Kurs als
neu.

Wenn der Schlüssel vorhanden ist, aber der komplette Datensatz anders ist, zum
Beispiel bei geänderter `Bestätigung`, gilt der Kurs als geändert.

`NOTIFY_REPORT_MODE` steuert die Benachrichtigungen erfolgreicher Läufe:

```dotenv
NOTIFY_REPORT_MODE=changes
```

`changes` meldet nur neue und pending Kurse, `compact` sendet nach jedem
erfolgreichen Lauf einen kurzen Status und `detailed` den vollständigen
Diagnosebericht.

Wenn ein gemeldeter Kurs pending ist, lautet der Benachrichtigungstitel:

```text
SlopePing · 1 节课程待确认
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
fügt ntfy HMAC-signierte Links hinzu, die standardmäßig 24 Stunden gelten:

- `打开 SlopePing`: öffnet `/control?token=...`
- `打开日历`: öffnet `/calendar?token=...`

Die Benachrichtigung führt Bestätigen oder Absagen nicht direkt aus. Kontroll-
und Kalenderseite lesen standardmäßig den zuletzt gespeicherten `var/state.json`
Snapshot, sodass das Öffnen der Seite Playwright nicht startet.
`/actions/execute` meldet sich nach der zweiten Bestätigung an, prüft die Live-
Allrounder-Seite erneut und speichert erst danach.

Die Bestätigungsseite erzeugt ein zehn Minuten gültiges Ausführungstoken, das an
Kurs und Aktion gebunden ist. Die Nonce wird vor der Ausführung gespeichert, das
Formular kann nicht zweimal ausgeführt werden. Alle Browserpfade teilen eine
prozessübergreifende Sperre.

## Zuverlässigkeitsschutz

- Ein erstes leeres Ergebnis nach einem nicht leeren Zustand behält den alten
  Stand; erst die zweite strukturell gültige leere Tabelle bestätigt ihn.
- Unvollständige Datenzeilen führen zu einem sicheren Parserfehler.
- Normale Prüfungen wiederholen nur temporäre Playwright-/Netzwerkfehler;
  Aktionen werden nie automatisch wiederholt.
- `var/health.json` speichert Laufzeit, Kurszahl, Fehlerfolge und Fehlerart.
- Erster Fehler, Fehlerschwelle und Erholung erzeugen Statusmeldungen.
- Screenshots und Kalenderdateien sind begrenzt; große Protokolle rotieren.

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

## Qualitätsbasis

- `tests/fixtures/` enthält anonymisierte Dienstplan-HTML-Dateien ohne echte Kontodaten.
- Parser-Fixture-Tests laufen lokal in Headless-Chromium ohne Zugriff auf Allrounder.
- Sicherheitstests decken nicht-pending, nicht verfügbare und direkte Remote-Aktionen ab.
- `./scripts/check.sh` führt Ruff-Formatierung, Ruff-Lint, mypy und pytest aus.
- `.github/workflows/ci.yml` führt dieselben Prüfungen mit Python 3.11 aus.
- Direkte Laufzeit- und Entwicklungsabhängigkeiten sind festgeschrieben.

## Laufzeitdateien

- `.env`
  Lokale Zugangsdaten und Konfiguration. Von Git ignoriert.
- `var/state.json` und `var/state.json.bak`
  Letzter erfolgreich gelesener Kursstand und vorige Sicherung. Von Git ignoriert.
- `var/screenshots/`
  Erfolgs- und Fehler-Screenshots. Von Git ignoriert.
- `var/actions.log`
  JSON-Line-Historie für CLI- und Webhook-Aktionen. Von Git ignoriert.
- `var/calendar_events/`
  Generierte `.ics` Dateien für Webhook-Aktionen. Von Git ignoriert.
- `var/health.json`
  Letzter Lauf und aufeinanderfolgende Anomalien. Von Git ignoriert.
- `var/logs/`
  Checker-, Webhook- und launchd-Protokolle. Von Git ignoriert.

## Sicherheit

- `.env` nicht committen.
- `NTFY_TOPIC` lang und privat wählen.
- Der öffentliche Dienst `ntfy.sh` schützt Topics standardmäßig nicht mit einem
  Passwort.
- Das Skript druckt Fortschrittsmeldungen, aber kein Passwort.
- Der Webhook-Server hört standardmäßig auf `127.0.0.1`. `0.0.0.0` nur in
  einem vertrauenswürdigen Netzwerk oder hinter einem gesicherten Tunnel nutzen.
- URLs enthalten nur kurzlebige signierte Token; das langfristige Geheimnis
  bleibt in `.env`.
- Kurzlebige Token sind weiterhin Zugangsdaten. Öffentlicher Zugriff erfordert
  HTTPS und eine zusätzliche Authentifizierungsschicht.
