import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


class VectorDocumentStore:
    """Simple document persistence for RAG context assembly."""

    def __init__(self, file_path: Optional[Path] = None):
        base_path = Path(__file__).resolve().parents[2] / 'data'
        self.file_path = file_path or (base_path / 'rag_documents.jsonl')
        self._lock = Lock()

    def add_document(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            'id': f"doc_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            'created_at': datetime.now(timezone.utc).isoformat(),
            'text': text,
            'metadata': metadata,
        }
        with self._lock:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with self.file_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=True) + '\n')
        return record

    def recent_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        if not self.file_path.exists():
            return []

        with self._lock:
            lines = self.file_path.read_text(encoding='utf-8').splitlines()

        docs: List[Dict[str, Any]] = []
        for line in lines[-safe_limit:]:
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    docs.append(payload)
            except json.JSONDecodeError:
                continue
        return list(reversed(docs))

    def recent_document_texts(self, limit: int = 50) -> List[str]:
        docs = self.recent_documents(limit)
        rendered: List[str] = []
        for item in docs:
            text = str(item.get('text', '')).strip()
            metadata = item.get('metadata', {})
            if not text:
                continue
            if isinstance(metadata, dict) and metadata:
                rendered.append(f"{text}\nMETADATA: {json.dumps(metadata, ensure_ascii=True)}")
            else:
                rendered.append(text)
        return rendered
