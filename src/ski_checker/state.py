from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScheduleRecord:
    tag: str
    von: str
    bis: str
    raum_ort: str
    trainingsbezeichnung: str
    bestaetigung: str

    @property
    def key(self) -> str:
        parts = [
            self.tag,
            self.von,
            self.bis,
            self.raum_ort,
            self.trainingsbezeichnung,
        ]
        return stable_hash(parts)

    @property
    def fingerprint(self) -> str:
        return stable_hash(list(asdict(self).values()))


@dataclass(frozen=True)
class StateChange:
    kind: str
    previous: ScheduleRecord | None
    current: ScheduleRecord


def stable_hash(parts: list[str]) -> str:
    payload = "\u241f".join(part.strip() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _record_from_dict(data: dict[str, Any]) -> ScheduleRecord:
    return ScheduleRecord(
        tag=str(data.get("tag", "")),
        von=str(data.get("von", "")),
        bis=str(data.get("bis", "")),
        raum_ort=str(data.get("raum_ort", "")),
        trainingsbezeichnung=str(data.get("trainingsbezeichnung", "")),
        bestaetigung=str(data.get("bestaetigung", "")),
    )


def load_records(path: Path) -> list[ScheduleRecord]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    records = raw.get("records", raw if isinstance(raw, list) else [])
    if not isinstance(records, list):
        raise ValueError(f"State file {path} is invalid: records must be a list")

    return [_record_from_dict(item) for item in records if isinstance(item, dict)]


def save_records(path: Path, records: list[ScheduleRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "records": [asdict(record) for record in records],
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp_path.replace(path)


def diff_records(
    previous_records: list[ScheduleRecord],
    current_records: list[ScheduleRecord],
) -> list[StateChange]:
    previous_by_key = {record.key: record for record in previous_records}
    changes: list[StateChange] = []

    for current in current_records:
        previous = previous_by_key.get(current.key)
        if previous is None:
            changes.append(StateChange(kind="new", previous=None, current=current))
        elif previous.fingerprint != current.fingerprint:
            changes.append(StateChange(kind="changed", previous=previous, current=current))

    return changes

