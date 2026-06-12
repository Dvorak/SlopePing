# Architekturhinweise

Sprache: [English](architecture.en.md) | [中文](architecture.zh-CN.md) | Deutsch

Dieses Dokument beschreibt die Implementierung. Für die tägliche Nutzung siehe
[README.de.md](../README.de.md).

SlopePing ist auf den Dienstplan-Workflow für Trainer der Neuss Skihalle im
Allrounder-Coach-Portal zugeschnitten.

## Module

- `run_checker.py`
  Einstiegspunkt. Fügt `src/` zu `sys.path` hinzu und ruft
  `ski_checker.checker.run()` auf.
- `src/ski_checker/config.py`
  Lädt `.env` und erstellt typisierte Einstellungen.
- `src/ski_checker/browser.py`
  Verwaltet Playwright, Login, Navigation, Seitenwechsel und Screenshots.
- `src/ski_checker/parser.py`
  Findet die Planungstabelle und wandelt Tabellenzeilen in Kursdatensätze um.
- `src/ski_checker/state.py`
  Definiert Kursdatensätze, liest und schreibt `state.json` und vergleicht den
  aktuellen Lauf mit dem vorherigen.
- `src/ski_checker/notify.py`
  Sendet ntfy-Benachrichtigungen mit Console-Fallback.

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

Im normalen Modus werden nur neue Kurse gemeldet. Für Tests kann man setzen:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

Dann sendet jeder erfolgreiche Lauf einen aktuellen Bericht.

## ntfy-Benachrichtigung

Das Projekt sendet Plain Text per POST an:

```text
{NTFY_SERVER}/{NTFY_TOPIC}
```

Die Nachricht enthält:

- Aktuelle Kurse im Testbericht-Modus
- Neue Kurse zur Bestätigung
- `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`

Wenn ntfy nicht konfiguriert ist oder das Senden fehlschlägt, wird dieselbe
Nachricht in der Konsole ausgegeben und das Programm läuft weiter.

## Laufzeitdateien

- `.env`
  Lokale Zugangsdaten und Konfiguration. Von Git ignoriert.
- `state.json`
  Letzter erfolgreich gelesener Kursstand. Von Git ignoriert.
- `screenshots/`
  Erfolgs- und Fehler-Screenshots. Von Git ignoriert.

## Sicherheit

- `.env` nicht committen.
- `NTFY_TOPIC` lang und privat wählen.
- Der öffentliche Dienst `ntfy.sh` schützt Topics standardmäßig nicht mit einem
  Passwort.
- Das Skript druckt Fortschrittsmeldungen, aber kein Passwort.
