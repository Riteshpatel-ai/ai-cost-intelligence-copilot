from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_chat_response_schema_and_explainability():
    response = client.post(
        "/api/chat",
        json={
            "query": "Show duplicate vendor payments",
            "docs": [],
            "invoices": [
                {"id": "1", "vendor": "Vendor A", "amount": 50000, "date": "2026-03-01"},
                {"id": "2", "vendor": "Vendor A", "amount": 50000, "date": "2026-03-01"},
            ],
            "sla_logs": [],
            "resources": [],
            "transactions": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert "response" in payload
    assert "anomalies" in payload
    assert "graph" in payload
    assert "actions" in payload
    assert "financial_impact_breakdown" in payload
    assert "explainability" in payload
    assert "confidence_traces" in payload["explainability"]
    assert "action_audit_timeline" in payload["explainability"]


def test_action_policy_contracts():
    high_risk = client.post("/api/action", json={"action": "block_payment", "risk_level": "high"})
    assert high_risk.status_code == 200
    high_payload = high_risk.json()
    assert high_payload["status"] == "pending_approval"
    assert high_payload["approval_required"] == "finance"

    low_risk = client.post("/api/action", json={"action": "create_ticket", "risk_level": "low"})
    assert low_risk.status_code == 200
    low_payload = low_risk.json()
    assert low_payload["status"] == "executed"
    assert low_payload["approval_required"] == "auto"
