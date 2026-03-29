import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def disable_external_llm_calls(monkeypatch):
    # Keep tests deterministic and offline-safe even when .env contains a real key.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
