# SlopePing

Sprache: [English](README.md) | [中文](README.zh-CN.md) | Deutsch

SlopePing ist ein kleiner Dienstplan-Watcher für Trainer der Neuss Skihalle.
Er meldet sich im Allrounder-Coach-Portal an, öffnet die Seite
`Arbeitsplan/Verfügbarkeit`, liest die Tabelle `Übersicht` aus und sendet bei
neuen Kursen oder nötigen Bestätigungen eine Benachrichtigung über ntfy an dein
Telefon.

Die erste Version bleibt bewusst einfach: Python, Playwright, lokale `.env`
Konfiguration, lokale `state.json` und ntfy-Benachrichtigungen.

## Funktionen

- Öffnet `https://allrounder-jobs.de/login`
- Meldet sich mit `SKI_USERNAME` und `SKI_PASSWORD` an
- Öffnet `Meine Daten` -> `Arbeitsplan/Verfügbarkeit`
- Wechselt zur Planungsseite `https://anmeldung.allrounder.de/do`
- Liest diese Tabellenfelder:
  `Tag`, `Von`, `Bis`, `Raum/Ort`, `Trainingsbezeichnung`, `Bestätigung`
- Erkennt den Bestätigungsstatus:
  `confirmed`, `pending` oder `unknown`
- Markiert Zeilen mit `Bestätigen` / `Absagen` Auswahl als handlungsbedürftig
- Speichert nach jeder erfolgreichen Prüfung einen Screenshot
- Vergleicht aktuelle Kurse mit `state.json`
- Sendet ntfy-Benachrichtigungen bei neuen Kursen oder pending Aktionen
- Öffnet über ntfy eine mobile SlopePing-Kontrollseite
- Verlangt eine zweite Bestätigung, bevor remote bestätigt oder abgesagt wird
- Kann Kurse als `.ics` Kalenderdateien exportieren
- Kann im Testmodus bei jedem Lauf einen vollständigen Bericht senden

SlopePing erkennt und meldet handlungsbedürftige Kurse. Es klickt nur nach
einem ausdrücklichen CLI-Befehl oder nach einer zweiten Bestätigung auf der
mobilen Kontrollseite auf `Bestätigen`, `Absagen` und `Speichern`.

In ntfy-Benachrichtigungen erscheint `Open SlopePing` für die mobile
Kontrollseite.

## Voraussetzungen

- Python 3.11+
- Ein Allrounder-Coach-Portal-Konto für das Trainersystem der Neuss Skihalle
- Die ntfy App auf dem Telefon oder ein anderer ntfy Client

## Einrichtung

```bash
cd SlopePing
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

Für die mobile Kontrollseite Webhook-Werte eintragen:

```dotenv
ACTION_WEBHOOK_TOKEN=your-generated-secure-token
ACTION_WEBHOOK_BASE_URL=http://YOUR_LOCAL_IP:8000
WEBHOOK_HOST=127.0.0.1
WEBHOOK_PORT=8000
```

Für Zugriff vom Telefon im lokalen Netz muss `ACTION_WEBHOOK_BASE_URL` die
lokale IP des Computers verwenden. `WEBHOOK_HOST=0.0.0.0` nur in einem
vertrauenswürdigen Netzwerk setzen.

Für Tests bei jedem erfolgreichen Lauf eine Nachricht senden:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=true
```

Für den normalen Betrieb nur bei neuen Kursen oder nötigen Bestätigungen benachrichtigen:

```dotenv
NOTIFY_ALWAYS_SEND_REPORT=false
```

## Ausführen

Für die mobile Kontrollseite zuerst den Webhook-Server starten:

```bash
cd SlopePing
source .venv/bin/activate
python scripts/webhook_server.py
```

Danach die Prüfung ausführen:

```bash
cd SlopePing
source .venv/bin/activate
python run_checker.py
```

Das Terminal zeigt jeden Schritt: Login, Navigation, Parsing, Screenshot,
Vergleich und Benachrichtigungsstatus.

Wenn ein Kurs pending ist, druckt das Terminal direkt kopierbare Befehle für
diesen Kurs.

Auf dem Handy öffnet `Open SlopePing` die Kontrollseite. Dort kannst du Kurse
prüfen, Kalenderdateien laden und erst nach einer zweiten Bestätigung annehmen
oder absagen.

## Per CLI bestätigen oder absagen

SlopePing führt eine Bestätigung oder Absage nur aus, wenn du ausdrücklich einen
dieser Befehle startest:

```bash
python run_checker.py --accept "LESSON_KEY_OR_ID"
python run_checker.py --decline "LESSON_KEY_OR_ID"
```

Am einfachsten ist die `lesson_id` aus der ntfy- oder Konsolenmeldung, zum
Beispiel:

```text
17.06.2026|14:00|16:00|Skischule|Extraschicht Skischule
```

`--accept` wählt `Bestätigen`. `--decline` wählt `Absagen`. Danach klickt
SlopePing auf `Speichern`, speichert Vorher-/Nachher-Screenshots und schreibt
`actions.log`.

Sicherheitsregeln:

- Nur pending Kurse können bearbeitet werden.
- Wenn Kurs, Dropdown, Aktion oder `Speichern` Button fehlt, gibt SlopePing eine
  klare Fehlermeldung aus und stoppt.
- ntfy-Benachrichtigungen lösen niemals automatisch Aktionen aus.
- Der Webhook-Server hört standardmäßig nur auf `127.0.0.1`. Für Zugriff aus
  dem lokalen Netz setze `WEBHOOK_HOST=0.0.0.0` nur in einem vertrauenswürdigen
  Netzwerk und verwende die lokale IP in `ACTION_WEBHOOK_BASE_URL`.

## Laufzeitdateien

- `state.json`: zuletzt bekannter Kursstand
- `actions.log`: Historie manueller Bestätigungen und Absagen
- `calendar_events/`: Kalenderdateien aus Webhook-Aktionen
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
- Wenn ein Kurs eine Aktion braucht, lautet der Titel `SlopePing: action needed`
  und die Nachricht zeigt die verfügbaren Aktionen.

## Weitere Details

Implementierungsdetails stehen separat:

- [Architecture notes, English](docs/architecture.en.md)
- [架构说明，中文](docs/architecture.zh-CN.md)
- [Architekturhinweise, Deutsch](docs/architecture.de.md)
