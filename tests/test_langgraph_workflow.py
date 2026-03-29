from backend.langgraph_execution import run_langgraph_workflow


def test_langgraph_parallel_workflow_outputs_explainability():
    payload = {
        "query": "Find waste and duplicate payments",
        "docs": [],
        "invoices": [
            {"id": "101", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
            {"id": "202", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
            {"id": "203", "vendor": "Beta", "amount": 22000, "date": "2026-03-10"},
        ],
        "sla_logs": [
            {"id": "sla1", "time_remaining": 1.5, "error_rate": 0.12, "penalty_risk": 3200},
        ],
        "resources": [
            {"id": "res1", "utilization": 0.2, "waste": 1800},
            {"id": "res2", "utilization": 0.95, "waste": 0},
        ],
        "transactions": [
            {"id": "tx1", "amount": 12000, "matched": False, "variance": 2000},
        ],
    }

    result = run_langgraph_workflow(payload)

    assert "anomalies" in result
    assert len(result["anomalies"]["duplicates"]) == 1
    assert len(result["anomalies"]["sla_breaches"]) == 1
    assert "explainability" in result
    assert len(result["explainability"]["confidence_traces"]) >= 4
    assert len(result["explainability"]["action_audit_timeline"]) >= 6
    assert result.get("risk_level") in {"low", "medium", "high"}
    assert result.get("approval_required") in {"auto", "manager", "finance"}
