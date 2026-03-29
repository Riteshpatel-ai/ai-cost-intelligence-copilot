import base64
import json
import os
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.financial_impact import calculate_impact
from backend.langgraph_execution import run_langgraph_workflow
from backend.main import app
from backend.services.duplicate_payment_analyzer import analyze_uploaded_duplicates
from backend.services.gmail_pipeline import GmailPipeline
from backend.services.gmail_state_store import GmailStateStore
from backend.services.vector_store import VectorDocumentStore
from backend.tools.csv_search_tool import CSVSearchTool
from backend.tools.file_read_tool import FileReadTool


client = TestClient(app)


def _workflow_payload(**overrides):
    payload = {
        "query": "Evaluate enterprise cost leakage and actions",
        "docs": [],
        "invoices": [],
        "sla_logs": [],
        "resources": [],
        "transactions": [],
    }
    payload.update(overrides)
    return payload


def test_financial_impact_formula_and_clamping():
    assert calculate_impact(50000, 0.9, 0.8) == 36000
    assert calculate_impact(-100, 0.9, 0.8) == 0
    assert calculate_impact(1000, 1.2, 0.5) == 500
    assert calculate_impact(1000, -0.1, 0.5) == 0


def test_quantifiable_cost_impact_matches_breakdown_sum():
    response = client.post(
        "/api/chat",
        json={
            "query": "Show duplicate losses",
            "docs": [],
            "invoices": [
                {"id": "a1", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
                {"id": "a2", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
            ],
            "sla_logs": [{"id": "s1", "time_remaining": 1.0, "error_rate": 0.02, "penalty_risk": 4000}],
            "resources": [{"id": "r1", "utilization": 0.2, "waste": 1000}],
            "transactions": [{"id": "t1", "matched": False, "variance": 2000, "amount": 2000}],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    breakdown = payload["financial_impact_breakdown"]
    total = breakdown["duplicate_payments"] + breakdown["sla_penalties"] + breakdown["resource_waste"] + breakdown["variance_risk"]

    assert payload["financial_impact"] > 0
    assert abs(payload["financial_impact"] - total) < 1e-6


def test_approval_workflow_thresholds_low_medium_high():
    low = run_langgraph_workflow(_workflow_payload())
    assert low.get("risk_level") == "low"
    assert low.get("approval_required") == "auto"

    medium = run_langgraph_workflow(
        _workflow_payload(
            sla_logs=[{"id": "s1", "time_remaining": 1.0, "error_rate": 0.2, "penalty_risk": 25000}]
        )
    )
    assert medium.get("risk_level") == "medium"
    assert medium.get("approval_required") == "manager"

    high = run_langgraph_workflow(
        _workflow_payload(
            invoices=[
                {"id": "x1", "vendor": "Apex", "amount": 100000, "date": "2026-03-01"},
                {"id": "x2", "vendor": "Apex", "amount": 100000, "date": "2026-03-01"},
            ]
        )
    )
    assert high.get("risk_level") == "high"
    assert high.get("approval_required") == "finance"


def test_actionability_outputs_playbooks_with_approval_mapping():
    result = run_langgraph_workflow(
        _workflow_payload(
            invoices=[
                {"id": "a1", "vendor": "Apex", "amount": 70000, "date": "2026-03-01"},
                {"id": "a2", "vendor": "Apex", "amount": 70000, "date": "2026-03-01"},
            ],
            resources=[{"id": "r1", "utilization": 0.1, "waste": 1400}],
        )
    )

    result_actions = result.get("actions")
    assert result_actions is not None
    actions = {item["type"]: item for item in result_actions}

    assert set(actions.keys()) == {"block_payment", "reassign_workload", "shutdown_resource", "create_ticket"}
    assert actions["block_payment"]["approval_required"] == "finance"
    assert actions["reassign_workload"]["approval_required"] == "manager"
    assert actions["create_ticket"]["approval_required"] == "auto"


def test_data_integration_depth_all_domain_anomalies_present():
    result = run_langgraph_workflow(
        _workflow_payload(
            invoices=[
                {"id": "i1", "vendor": "Apex", "amount": 10, "date": "2026-03-01"},
                {"id": "i2", "vendor": "Apex", "amount": 10, "date": "2026-03-01"},
                {"id": "i3", "vendor": "Beta", "amount": 2000, "date": "2026-03-02"},
            ],
            sla_logs=[{"id": "s1", "time_remaining": 0.5, "error_rate": 0.15, "penalty_risk": 3000}],
            resources=[
                {"id": "r1", "utilization": 0.2, "waste": 1200},
                {"id": "r2", "utilization": 0.95, "waste": 0},
            ],
            transactions=[
                {"id": "t1", "matched": False, "variance": 2500, "amount": 2500},
            ],
        )
    )

    anomalies = result.get("anomalies")
    assert anomalies is not None
    assert len(anomalies["duplicates"]) >= 1
    assert len(anomalies["cost_leakage"]) >= 1
    assert len(anomalies["sla_breaches"]) >= 1
    assert len(anomalies["underutilized"]) >= 1
    assert len(anomalies["overutilized"]) >= 1
    assert len(anomalies["unmatched"]) >= 1
    assert len(anomalies["variance"]) >= 1


def test_explainability_contains_confidence_traces_and_audit_stages():
    result = run_langgraph_workflow(
        _workflow_payload(
            invoices=[
                {"id": "i1", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
                {"id": "i2", "vendor": "Apex", "amount": 50000, "date": "2026-03-01"},
            ]
        )
    )

    explain = result.get("explainability")
    assert explain is not None
    traces = explain["confidence_traces"]
    timeline = explain["action_audit_timeline"]

    assert len(traces) >= 4
    assert all(0 <= trace["confidence"] <= 1 for trace in traces)

    stages = {event["stage"] for event in timeline}
    assert "ingestion" in stages
    assert "rag_retrieval" in stages
    assert "parallel_agents" in stages
    assert "decision_engine" in stages


def test_graph_analyzer_output_contains_risk_relationship_edges():
    result = run_langgraph_workflow(
        _workflow_payload(
            invoices=[
                {"id": "x1", "vendor": "Apex", "amount": 40000, "date": "2026-03-01"},
                {"id": "x2", "vendor": "Apex", "amount": 40000, "date": "2026-03-01"},
            ],
            sla_logs=[{"id": "s2", "time_remaining": 1.0, "error_rate": 0.02, "penalty_risk": 2500}],
        )
    )

    graph = result.get("graph")
    assert graph is not None
    assert len(graph["nodes"]) >= 3
    assert len(graph["edges"]) >= 2

    labels = {edge["label"] for edge in graph["edges"]}
    assert "PAID_TO" in labels
    assert "CAUSES_RISK" in labels


def test_uploaded_rows_action_query_returns_data_driven_response():
    response = client.post(
        "/api/chat",
        json={
            "query": "What actions should we approve first for max savings?",
            "uploaded_filename": "intake.csv",
            "uploaded_rows": [
                {"Tool": "Cloud Compute", "Cost_INR": 250000},
                {"Tool": "Cloud Compute", "Cost_INR": 250000},
                {"Tool": "SaaS CRM", "Cost_INR": 120000},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert "No uploaded dataset is available" not in payload["response"]
    assert "intake.csv" in payload["response"]
    assert payload["financial_impact"] > 0

    action_types = {action["type"] for action in payload["actions"]}
    assert "optimize_high_spend_tools" in action_types


def test_action_query_without_uploaded_rows_prompts_for_upload():
    with patch("backend.api.chat.load_latest_upload", return_value=None):
        response = client.post(
            "/api/chat",
            json={
                "query": "What actions should we approve first for max savings?",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert "No uploaded dataset is available" in payload["response"]


def test_uploaded_rows_report_query_returns_data_report():
    response = client.post(
        "/api/chat",
        json={
            "query": "give me one report",
            "uploaded_filename": "intake.csv",
            "uploaded_rows": [
                {"Tool": "Cloud Compute", "Cost_INR": 250000},
                {"Tool": "Cloud Compute", "Cost_INR": 250000},
                {"Tool": "SaaS CRM", "Cost_INR": 120000},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert "No uploaded dataset is available" not in payload["response"]
    assert "Report for uploaded file 'intake.csv'" in payload["response"]
    assert payload["financial_impact"] > 0
    assert payload["report"]["download_url"] == "/api/reports/latest-pdf"
    assert payload["report"]["title"] == "Cost Optimization Decision Audit Report"


def test_uploaded_rows_sla_query_without_sla_fields_returns_sla_guidance():
    response = client.post(
        "/api/chat",
        json={
            "query": "Which SLA breaches can trigger penalties this week?",
            "uploaded_filename": "intake.csv",
            "uploaded_rows": [
                {"Tool": "Cloud Compute", "Cost_INR": 250000},
                {"Tool": "SaaS CRM", "Cost_INR": 120000},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert "does not include explicit SLA breach/penalty fields" in payload["response"]
    assert "Impact math: amount x confidence x recoveryProbability" not in payload["response"]


def test_file_read_tool_parses_csv_content():
    tool = FileReadTool()
    content = b"Tool,Cost_INR\nCloud Compute,250000\nSaaS CRM,120000\n"

    rows = tool.parse_uploaded_content("intake.csv", content)

    assert len(rows) == 2
    assert rows[0]["Tool"] == "Cloud Compute"
    assert rows[1]["Cost_INR"] == "120000"


def test_csv_search_tool_extracts_spend_and_sla_signals():
    tool = CSVSearchTool()
    rows = [
        {"Tool": "Cloud Compute", "Cost_INR": 250000, "SLA_Breach_Risk": 0.81, "Penalty_Risk_INR": 15000},
        {"Tool": "SaaS CRM", "Cost_INR": 120000, "SLA_Breach_Risk": 0.1, "Penalty_Risk_INR": 0},
    ]

    top_spend = tool.top_items_by_amount(rows, top_n=2)
    sla_signals = tool.extract_sla_signals(rows, top_n=2)

    assert top_spend[0]["tool"] == "Cloud Compute"
    assert float(top_spend[0]["amount"]) == 250000
    assert len(sla_signals) == 1
    assert sla_signals[0]["task"] == "Cloud Compute"


def test_csv_search_tool_supports_salary_department_schema():
    tool = CSVSearchTool()
    rows = [
        {"Employee_ID": "E101", "Department": "AI", "Salary": 80000},
        {"Employee_ID": "E102", "Department": "DevOps", "Salary": 150000},
    ]

    top_spend = tool.top_items_by_amount(rows, top_n=2)

    assert len(top_spend) == 2
    assert top_spend[0]["tool"] == "DevOps"
    assert float(top_spend[0]["amount"]) == 150000


def test_csv_search_tool_infers_dynamic_amount_and_sla_headers():
    tool = CSVSearchTool()
    rows = [
        {
            "Business Unit": "Cloud Ops",
            "Monthly Spend (INR)": "250000",
            "SLA Breach Probability": "0.91",
            "Penalty Exposure INR": "45000",
            "Days until Breach": "3",
        },
        {
            "Business Unit": "HR",
            "Monthly Spend (INR)": "80000",
            "SLA Breach Probability": "0.10",
            "Penalty Exposure INR": "0",
            "Days until Breach": "30",
        },
    ]

    top_spend = tool.top_items_by_amount(rows, top_n=2)
    sla_signals = tool.extract_sla_signals(rows, top_n=2)

    assert top_spend[0]["tool"] == "Cloud Ops"
    assert float(top_spend[0]["amount"]) == 250000
    assert len(sla_signals) == 1
    assert sla_signals[0]["task"] == "Cloud Ops"
    assert float(sla_signals[0]["penalty_risk"]) == 45000


def test_duplicate_analyzer_infers_dynamic_amount_and_name_columns():
    rows = [
        {"Business Unit": "AI", "Monthly Spend (INR)": "90000", "Period": "2026-03"},
        {"Business Unit": "AI", "Monthly Spend (INR)": "90000", "Period": "2026-03"},
        {"Business Unit": "DevOps", "Monthly Spend (INR)": "120000", "Period": "2026-03"},
    ]

    result = analyze_uploaded_duplicates(rows, top_n=3)

    assert result["coverage"]["rows_with_amount"] == 3
    assert len(result["duplicate_sets"]) >= 1
    assert result["duplicate_sets"][0]["vendor"] == "AI"
    assert result["duplicate_sets"][0]["calculated_impact"] > 0


def test_gmail_webhook_message_id_routes_to_message_pipeline():
    headers = {"x-webhook-token": os.getenv("GMAIL_WEBHOOK_SHARED_SECRET", "")}
    with patch("backend.api.gmail._PIPELINE.process_message", return_value={"status": "processed"}) as mock_process:
        response = client.post(
            "/gmail/webhook",
            json={
                "messageId": "msg_123",
                "historyId": "789",
            },
            headers=headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    mock_process.assert_called_once_with(message_id="msg_123", history_id="789")


def test_gmail_health_endpoint_returns_status_payload():
    response = client.get("/gmail/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "gmail" in payload
    assert "auto_webhook_ready" in payload["gmail"]


def test_gmail_webhook_pubsub_history_routes_to_history_pipeline():
    pubsub_body = base64.urlsafe_b64encode(json.dumps({"historyId": "9001"}).encode("utf-8")).decode("utf-8")
    headers = {"x-webhook-token": os.getenv("GMAIL_WEBHOOK_SHARED_SECRET", "")}

    with patch("backend.api.gmail._PIPELINE.process_history", return_value={"status": "no_messages"}) as mock_history:
        response = client.post(
            "/api/gmail/webhook",
            json={
                "message": {
                    "data": pubsub_body,
                }
            },
            headers=headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    mock_history.assert_called_once_with(history_id="9001")


def test_gmail_manual_message_endpoint_routes_to_pipeline():
    with patch("backend.api.gmail._PIPELINE.process_message", return_value={"status": "processed"}) as mock_process:
        response = client.post(
            "/gmail/manual/process-message",
            json={
                "message_id": "msg_manual_1",
                "history_id": "123",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["mode"] == "manual_message_fetch"
    mock_process.assert_called_once_with(message_id="msg_manual_1", history_id="123")


def test_gmail_manual_email_endpoint_routes_to_pipeline():
    with patch("backend.api.gmail._PIPELINE.process_manual_email", return_value={"status": "processed"}) as mock_process:
        response = client.post(
            "/gmail/manual/process-email",
            json={
                "sender": "ops@example.com",
                "subject": "SLA warning",
                "body": "Penalty risk increased",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["mode"] == "manual_raw_email"
    mock_process.assert_called_once()


def test_gmail_manual_latest_fetch_endpoint_routes_to_pipeline():
    with patch(
        "backend.api.gmail._PIPELINE.process_latest_messages",
        return_value={"status": "processed", "fetched_count": 1, "processed_count": 1, "results": []},
    ) as mock_process:
        response = client.post(
            "/gmail/manual/fetch-latest",
            json={
                "limit": 3,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["mode"] == "manual_latest_fetch"
    mock_process.assert_called_once_with(limit=3)


def test_gmail_state_store_is_idempotent(tmp_path):
    store = GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20)

    assert store.is_duplicate(message_id="m1", history_id="h1") is False
    store.mark_processed(message_id="m1", history_id="h1")
    assert store.is_duplicate(message_id="m1", history_id="h1") is True
    assert store.is_duplicate(message_id=None, history_id="h1") is True


class _FakeGmailClient:
    def list_recent_message_ids(self, max_results: int = 1, label_ids=None):
        return ["msg_A", "msg_B", "msg_C"][:max_results]

    def get_email(self, msg_id: str):
        return {
            "message_id": msg_id,
            "history_id": "321",
            "subject": "Invoice escalation",
            "sender": "finance@example.com",
            "body": "Duplicate payment found for vendor Apex",
        }


def test_gmail_pipeline_process_message_and_deduplicate(tmp_path):
    pipeline = GmailPipeline(
        gmail_client=_FakeGmailClient(),
        state_store=GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20),
        vector_store=VectorDocumentStore(file_path=tmp_path / "rag_docs.jsonl"),
    )

    with patch(
        "backend.services.gmail_pipeline.run_langgraph_workflow",
        return_value={
            "financial_impact": 12345.0,
            "risk_level": "medium",
            "approval_required": "manager",
            "recommendations": ["Investigate duplicate invoice"],
        },
    ):
        first = pipeline.process_message(message_id="msg_A", history_id="321")
        second = pipeline.process_message(message_id="msg_A", history_id="321")

    assert first["status"] == "processed"
    assert first["classification"] == "finance"
    assert first["workflow"]["financial_impact"] == 12345.0
    assert second["status"] == "duplicate"


def test_gmail_pipeline_process_manual_email_and_deduplicate(tmp_path):
    pipeline = GmailPipeline(
        gmail_client=_FakeGmailClient(),
        state_store=GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20),
        vector_store=VectorDocumentStore(file_path=tmp_path / "rag_docs.jsonl"),
    )

    with patch(
        "backend.services.gmail_pipeline.run_langgraph_workflow",
        return_value={
            "financial_impact": 777.0,
            "risk_level": "low",
            "approval_required": "auto",
            "recommendations": ["Monitor"],
        },
    ):
        first = pipeline.process_manual_email(
            sender="finance@example.com",
            subject="Invoice update",
            body="Please review vendor invoice",
            message_id="manual_777",
        )
        second = pipeline.process_manual_email(
            sender="finance@example.com",
            subject="Invoice update",
            body="Please review vendor invoice",
            message_id="manual_777",
        )

    assert first["status"] == "processed"
    assert first["classification"] == "finance"
    assert second["status"] == "duplicate"


def test_gmail_pipeline_process_latest_messages(tmp_path):
    pipeline = GmailPipeline(
        gmail_client=_FakeGmailClient(),
        state_store=GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20),
        vector_store=VectorDocumentStore(file_path=tmp_path / "rag_docs.jsonl"),
    )

    with patch(
        "backend.services.gmail_pipeline.run_langgraph_workflow",
        return_value={
            "financial_impact": 555.0,
            "risk_level": "medium",
            "approval_required": "manager",
            "recommendations": ["Review latest email"],
        },
    ):
        result = pipeline.process_latest_messages(limit=2)

    assert result["status"] == "processed"
    assert result["fetched_count"] == 2
    assert result["processed_count"] == 2
    assert len(result["results"]) == 2


def test_gmail_pipeline_process_latest_skips_duplicate_and_processes_next(tmp_path):
    pipeline = GmailPipeline(
        gmail_client=_FakeGmailClient(),
        state_store=GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20),
        vector_store=VectorDocumentStore(file_path=tmp_path / "rag_docs.jsonl"),
    )

    pipeline.state_store.mark_processed(message_id="msg_A", history_id=None)

    with patch(
        "backend.services.gmail_pipeline.run_langgraph_workflow",
        return_value={
            "financial_impact": 101.0,
            "risk_level": "low",
            "approval_required": "auto",
            "recommendations": ["Proceed"],
        },
    ):
        result = pipeline.process_latest_messages(limit=1)

    assert result["status"] == "processed"
    assert result["processed_count"] == 1
    assert result["duplicates_skipped"] == 1
    assert result["results"][0]["status"] == "duplicate"
    assert result["results"][1]["status"] == "processed"


def test_gmail_pipeline_process_latest_returns_no_new_messages_when_all_duplicates(tmp_path):
    pipeline = GmailPipeline(
        gmail_client=_FakeGmailClient(),
        state_store=GmailStateStore(file_path=tmp_path / "gmail_state.json", max_items=20),
        vector_store=VectorDocumentStore(file_path=tmp_path / "rag_docs.jsonl"),
    )

    pipeline.state_store.mark_processed(message_id="msg_A", history_id=None)
    pipeline.state_store.mark_processed(message_id="msg_B", history_id=None)
    pipeline.state_store.mark_processed(message_id="msg_C", history_id=None)

    with patch(
        "backend.services.gmail_pipeline.run_langgraph_workflow",
        return_value={
            "financial_impact": 202.0,
            "risk_level": "low",
            "approval_required": "auto",
            "recommendations": ["Proceed"],
        },
    ):
        result = pipeline.process_latest_messages(limit=1)

    assert result["status"] == "no_new_messages"
    assert result["processed_count"] == 0
    assert result["duplicates_skipped"] >= 1
