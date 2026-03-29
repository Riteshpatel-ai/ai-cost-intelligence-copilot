import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional


class GmailStateStore:
    """Persist processed Gmail event identifiers to keep webhook handling idempotent."""

    def __init__(self, file_path: Optional[Path] = None, max_items: int = 5000):
        base_path = Path(__file__).resolve().parents[2] / 'data'
        self.file_path = file_path or (base_path / 'gmail_state.json')
        self.max_items = max(100, max_items)
        self._lock = Lock()

    def is_duplicate(self, message_id: Optional[str], history_id: Optional[str]) -> bool:
        state = self._load_state()
        message_ids = set(state.get('processed_message_ids', []))
        history_ids = set(state.get('processed_history_ids', []))

        if message_id and message_id in message_ids:
            return True
        if not message_id and history_id and history_id in history_ids:
            return True
        return False

    def mark_processed(self, message_id: Optional[str], history_id: Optional[str]) -> Dict[str, Any]:
        with self._lock:
            state = self._load_state()
            message_ids = list(state.get('processed_message_ids', []))
            history_ids = list(state.get('processed_history_ids', []))

            if message_id and message_id not in message_ids:
                message_ids.append(message_id)
            if history_id and history_id not in history_ids:
                history_ids.append(history_id)

            state['processed_message_ids'] = message_ids[-self.max_items :]
            state['processed_history_ids'] = history_ids[-self.max_items :]
            state['last_history_id'] = self._max_history_id(state.get('last_history_id'), history_id)

            self._write_state(state)
            return state

    def status_snapshot(self) -> Dict[str, Any]:
        state = self._load_state()
        return {
            'last_history_id': state.get('last_history_id'),
            'processed_message_count': len(state.get('processed_message_ids', [])),
            'processed_history_count': len(state.get('processed_history_ids', [])),
        }

    def _max_history_id(self, current: Optional[str], incoming: Optional[str]) -> Optional[str]:
        if not incoming:
            return current
        if not current:
            return incoming
        try:
            return str(max(int(current), int(incoming)))
        except ValueError:
            return incoming

    def _load_state(self) -> Dict[str, Any]:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            return {
                'processed_message_ids': [],
                'processed_history_ids': [],
                'last_history_id': None,
            }

        try:
            raw = self.file_path.read_text(encoding='utf-8').strip()
            if not raw:
                return {
                    'processed_message_ids': [],
                    'processed_history_ids': [],
                    'last_history_id': None,
                }
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError('Invalid payload')
            payload.setdefault('processed_message_ids', [])
            payload.setdefault('processed_history_ids', [])
            payload.setdefault('last_history_id', None)
            return payload
        except (json.JSONDecodeError, OSError, ValueError):
            return {
                'processed_message_ids': [],
                'processed_history_ids': [],
                'last_history_id': None,
            }

    def _write_state(self, state: Dict[str, Any]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(state, ensure_ascii=True), encoding='utf-8')
