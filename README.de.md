# SlopePing

Sprache: [English](README.md) | [中文](README.zh-CN.md) | Deutsch

SlopePing ist ein kleiner Dienstplan-Watcher für Trainer der Neuss Skihalle.
Er meldet sich im Allrounder-Coach-Portal an, öffnet die Seite
`Arbeitsplan/Verfügbarkeit`, liest die Tabelle `Übersicht` aus und sendet bei
neuen Kursen eine Benachrichtigung über ntfy an dein Telefon.

Die erste Version bleibt bewusst einfach: Python, Playwright, lokale `.env`
Konfiguration, lokale `state.json` und ntfy-Benachrichtigungen.

## Funktionen

- Öffnet `https://allrounder-jobs.de/login`
- Meldet sich mit `SKI_USERNAME` und `SKI_PASSWORD` an
- Öffnet `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`
- Wechselt zur Planungsseite `https://anmeldung.allrounder.de/do`
- Liest diese Tabellenfelder:
  `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- Speichert nach jeder erfolgreichen Prüfung einen Screenshot
- Vergleicht aktuelle Kurse mit `state.json`
- Sendet ntfy-Benachrichtigungen bei neuen Kursen
- Kann im Testmodus bei jedem Lauf einen vollständigen Bericht senden

## Voraussetzungen

- Python 3.11+
- Ein Allrounder-Coach-Portal-Konto für das Trainersystem der Neuss Skihalle
- Die ntfy App auf dem Telefon oder ein anderer ntfy Client

## Einrichtung

```bash
cd /Users/zhang/ski-coach-checker
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

## `.env` konfigurieren

Bearbeiten:

```bash
nano .env
```

Login-Daten eintragen:

```dotenv
SKI_USERNAME=your_username
SKI_PASSWORD=your_password
```

ntfy eintragen:

```dotenv
NOTIFY_CHANNEL=ntfy
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=your-long-private-topic
```

In der ntfy App denselben `NTFY_SERVER` und dasselbe `NTFY_TOPIC` abonnieren.
Das Topic privat halten; wer es kennt, kann es abonnieren.

Für Tests bei jedem erfolgreichen Lauf eine Nachricht senden:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

Für den normalen Betrieb nur bei neuen Kursen benachrichtigen:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=false
```

## Ausführen

```bash
cd /Users/zhang/ski-coach-checker
source .venv/bin/activate
python run_checker.py
```

Das Terminal zeigt jeden Schritt: Login, Navigation, Parsing, Screenshot,
Vergleich und Benachrichtigungsstatus.

## Laufzeitdateien

- `state.json`: zuletzt bekannter Kursstand
- `screenshots/`: Erfolgs- und Fehler-Screenshots

Beide sind in Git ignoriert.

## Fehlerbehebung

- Login schlägt fehl: `SKI_USERNAME` und `SKI_PASSWORD` prüfen.
- Seite öffnet, aber keine Kurse werden gelesen: neuesten Screenshot in
  `screenshots/` prüfen.
- Terminal meldet ntfy gesendet, aber das Telefon bleibt stumm:
  Benachrichtigungsrechte, Server und Topic prüfen.
- Benachrichtigung testen ohne neuen Kurs:
  `NOTIFY_ALWAYS_SEND_REPORT=true` setzen.

## Weitere Details

Implementierungsdetails stehen separat:

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
