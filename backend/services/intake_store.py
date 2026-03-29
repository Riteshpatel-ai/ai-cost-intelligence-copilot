import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

_DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'intake_events.jsonl'
_LATEST_UPLOAD_FILE = Path(__file__).resolve().parents[2] / 'data' / 'latest_upload_dataset.json'
_LOCK = Lock()


def _ensure_data_file() -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _DATA_FILE.exists():
        _DATA_FILE.touch()


def _ensure_upload_file_parent() -> None:
    _LATEST_UPLOAD_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_data_file()
    record = {
        'id': f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        'event_type': event_type,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'payload': payload,
    }

    with _LOCK:
        with _DATA_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=True) + '\n')

    return record


def recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    _ensure_data_file()

    with _LOCK:
        lines = _DATA_FILE.read_text(encoding='utf-8').splitlines()

    events: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return list(reversed(events))


def save_latest_upload(filename: str, rows: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
    _ensure_upload_file_parent()
    record = {
        'filename': filename,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'row_count': len(rows),
        'columns': columns,
        'rows': rows,
    }

    with _LOCK:
        _LATEST_UPLOAD_FILE.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')

    return {
        'filename': record['filename'],
        'created_at': record['created_at'],
        'row_count': record['row_count'],
        'columns': record['columns'],
    }


def load_latest_upload() -> Optional[Dict[str, Any]]:
    _ensure_upload_file_parent()
    if not _LATEST_UPLOAD_FILE.exists():
        return None

    with _LOCK:
        try:
            content = _LATEST_UPLOAD_FILE.read_text(encoding='utf-8').strip()
            if not content:
                return None
            payload = json.loads(content)
            if not isinstance(payload, dict):
                return None
            rows = payload.get('rows', [])
            if not isinstance(rows, list):
                return None
            return payload
        except (json.JSONDecodeError, OSError):
            return None
