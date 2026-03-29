from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.finance_agent import FinanceAgent
from backend.agents.resource_agent import ResourceAgent
from backend.agents.sla_agent import SLAAgent
from backend.agents.spend_agent import SpendAgent
from backend.financial_impact import calculate_impact
from backend.graph_builder.builder import GraphBuilder
from backend.rag.pipeline import RAGPipeline


class WorkflowState(TypedDict, total=False):
	query: str
	docs: List[str]
	invoices: List[Dict[str, Any]]
	sla_logs: List[Dict[str, Any]]
	resources: List[Dict[str, Any]]
	transactions: List[Dict[str, Any]]
	context_docs: List[str]
	rag_response: str
	spend_results: Dict[str, List[Dict[str, Any]]]
	sla_results: Dict[str, List[Dict[str, Any]]]
	resource_results: Dict[str, List[Dict[str, Any]]]
	finance_results: Dict[str, List[Dict[str, Any]]]
	anomalies: Dict[str, List[Dict[str, Any]]]
	graph: Dict[str, List[Dict[str, Any]]]
	financial_impact_breakdown: Dict[str, float]
	financial_impact: float
	risk_level: Literal["low", "medium", "high"]
	approval_required: Literal["auto", "manager", "finance"]
	recommendations: List[str]
	actions: List[Dict[str, str]]
	explainability: Dict[str, Any]


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _detect_risk_level(financial_impact: float) -> Literal["low", "medium", "high"]:
	if financial_impact >= 50000:
		return "high"
	if financial_impact >= 10000:
		return "medium"
	return "low"


def _approval_role_for_risk(risk: str) -> Literal["auto", "manager", "finance"]:
	if risk == "high":
		return "finance"
	if risk == "medium":
		return "manager"
	return "auto"


def _build_recommendations(anomalies: Dict[str, List[Dict[str, Any]]]) -> List[str]:
	recommendations: List[str] = []
	if anomalies["duplicates"]:
		recommendations.append("Block duplicate vendor payment and start recovery workflow.")
	if anomalies["sla_breaches"]:
		recommendations.append("Reassign work to avoid SLA penalties in the next execution window.")
	if anomalies["underutilized"]:
		recommendations.append("Consolidate underutilized resources and decommission idle capacity.")
	if anomalies["overutilized"]:
		recommendations.append("Shift workload from overutilized resources to balance capacity.")
	if anomalies["unmatched"]:
		recommendations.append("Create reconciliation tickets for unmatched transactions.")
	if anomalies["variance"]:
		recommendations.append("Trigger variance root-cause analysis for abnormal financial drift.")
	if not recommendations:
		recommendations.append("No critical issues detected. Continue monitoring with current controls.")
	return recommendations


def _build_graph(anomalies: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
	graph = GraphBuilder()
	for inv in anomalies["duplicates"]:
		vendor_name = str(inv.get("vendor", "unknown")).replace(" ", "_")
		inv_id = str(inv.get("id", "unknown"))
		node_vendor = f"vendor_{vendor_name}"
		node_invoice = f"invoice_{inv_id}"
		node_risk = f"risk_dup_{inv_id}"
		graph.add_node(node_vendor, "vendor", label=f"Vendor {inv.get('vendor', 'Unknown')}", risk="medium")
		graph.add_node(node_invoice, "invoice", label=f"Invoice {inv_id}", risk="high")
		graph.add_node(node_risk, "risk_event", label="Duplicate Payment", risk="high")
		graph.add_edge(node_vendor, node_invoice, "PAID_TO")
		graph.add_edge(node_invoice, node_risk, "CAUSES_RISK")

	for task in anomalies["sla_breaches"][:6]:
		task_id = str(task.get("id", task.get("task", "unknown")))
		node_task = f"sla_{task_id}"
		node_risk = f"risk_sla_{task_id}"
		graph.add_node(node_task, "sla_task", label=f"SLA {task_id}", risk="medium")
		graph.add_node(node_risk, "risk_event", label="Potential SLA Breach", risk="high")
		graph.add_edge(node_task, node_risk, "CAUSES_RISK")

	return graph.build()


def _build_impact_breakdown(anomalies: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
	duplicate_impact = sum(calculate_impact(inv.get("amount", 0), 0.9, 0.8) for inv in anomalies["duplicates"])
	sla_impact = sum(calculate_impact(log.get("penalty_risk", 2500), 0.75, 0.65) for log in anomalies["sla_breaches"])
	resource_impact = sum(calculate_impact(res.get("waste", 1200), 0.7, 0.8) for res in anomalies["underutilized"])
	variance_impact = sum(calculate_impact(abs(item.get("variance", 0)), 0.6, 0.5) for item in anomalies["variance"])
	total = duplicate_impact + sla_impact + resource_impact + variance_impact
	return {
		"duplicate_payments": duplicate_impact,
		"sla_penalties": sla_impact,
		"resource_waste": resource_impact,
		"variance_risk": variance_impact,
		"total": total,
	}


def ingestion_node(state: WorkflowState) -> Dict[str, Any]:
	return {
		"docs": state.get("docs", []),
		"invoices": state.get("invoices", []),
		"sla_logs": state.get("sla_logs", []),
		"resources": state.get("resources", []),
		"transactions": state.get("transactions", []),
	}


def rag_node(state: WorkflowState) -> Dict[str, Any]:
	pipeline = RAGPipeline(state.get("docs", []))
	context_docs = [doc for doc, _ in pipeline.retrieve(state.get("query", ""), top_k=3)]
	rag_response = pipeline.generate_answer(state.get("query", ""), context_docs)
	return {"context_docs": context_docs, "rag_response": rag_response}


def spend_node(state: WorkflowState) -> Dict[str, Any]:
	agent = SpendAgent(state.get("invoices", []))
	return {
		"spend_results": {
			"duplicates": agent.detect_duplicates(),
			"cost_leakage": agent.detect_cost_leakage(),
		}
	}


def sla_node(state: WorkflowState) -> Dict[str, Any]:
	agent = SLAAgent(state.get("sla_logs", []))
	return {"sla_results": {"sla_breaches": agent.predict_breaches()}}


def resource_node(state: WorkflowState) -> Dict[str, Any]:
	agent = ResourceAgent(state.get("resources", []))
	return {
		"resource_results": {
			"underutilized": agent.underutilized(),
			"overutilized": agent.overutilized(),
		}
	}


def finance_node(state: WorkflowState) -> Dict[str, Any]:
	agent = FinanceAgent(state.get("transactions", []))
	return {
		"finance_results": {
			"unmatched": agent.reconcile(),
			"variance": agent.variance_analysis(),
		}
	}


def merge_anomalies_node(state: WorkflowState) -> Dict[str, Any]:
	anomalies = {
		"duplicates": state.get("spend_results", {}).get("duplicates", []),
		"cost_leakage": state.get("spend_results", {}).get("cost_leakage", []),
		"sla_breaches": state.get("sla_results", {}).get("sla_breaches", []),
		"underutilized": state.get("resource_results", {}).get("underutilized", []),
		"overutilized": state.get("resource_results", {}).get("overutilized", []),
		"unmatched": state.get("finance_results", {}).get("unmatched", []),
		"variance": state.get("finance_results", {}).get("variance", []),
	}
	return {"anomalies": anomalies}


def graph_node(state: WorkflowState) -> Dict[str, Any]:
	return {"graph": _build_graph(state.get("anomalies", {})) }


def impact_node(state: WorkflowState) -> Dict[str, Any]:
	breakdown = _build_impact_breakdown(state.get("anomalies", {}))
	return {
		"financial_impact_breakdown": breakdown,
		"financial_impact": breakdown.get("total", 0),
	}


def decision_node(state: WorkflowState) -> Dict[str, Any]:
	risk_level = _detect_risk_level(state.get("financial_impact", 0))
	approval_required = _approval_role_for_risk(risk_level)
	actions = [
		{"type": "block_payment", "risk": "high", "approval_required": "finance"},
		{"type": "reassign_workload", "risk": "medium", "approval_required": "manager"},
		{"type": "shutdown_resource", "risk": "high", "approval_required": "finance"},
		{"type": "create_ticket", "risk": "low", "approval_required": "auto"},
	]
	return {
		"risk_level": risk_level,
		"approval_required": approval_required,
		"recommendations": _build_recommendations(state.get("anomalies", {})),
		"actions": actions,
	}


def explainability_node(state: WorkflowState) -> Dict[str, Any]:
	anomalies = state.get("anomalies", {})
	confidence_traces = [
		{
			"signal": "duplicate_payments",
			"item_count": len(anomalies["duplicates"]),
			"confidence": 0.9,
			"evidence": "Vendor + amount + date key match across invoices.",
		},
		{
			"signal": "sla_breaches",
			"item_count": len(anomalies["sla_breaches"]),
			"confidence": 0.75,
			"evidence": "Low time remaining or elevated error rate in SLA logs.",
		},
		{
			"signal": "resource_waste",
			"item_count": len(anomalies["underutilized"]),
			"confidence": 0.7,
			"evidence": "Resource utilization below 30 percent threshold.",
		},
		{
			"signal": "variance_risk",
			"item_count": len(anomalies["variance"]),
			"confidence": 0.6,
			"evidence": "Absolute transaction variance above control threshold.",
		},
	]

	now = _utc_now_iso()
	audit_timeline = [
		{"timestamp": now, "stage": "ingestion", "actor": "orchestrator", "action": "ingest_inputs", "outcome": "success", "confidence": None},
		{"timestamp": now, "stage": "rag_retrieval", "actor": "rag_node", "action": "retrieve_context", "outcome": "success", "confidence": 0.8},
		{"timestamp": now, "stage": "parallel_agents", "actor": "spend_agent", "action": "detect_spend_anomalies", "outcome": "success", "confidence": 0.9},
		{"timestamp": now, "stage": "parallel_agents", "actor": "sla_agent", "action": "predict_breaches", "outcome": "success", "confidence": 0.75},
		{"timestamp": now, "stage": "parallel_agents", "actor": "resource_agent", "action": "score_utilization", "outcome": "success", "confidence": 0.7},
		{"timestamp": now, "stage": "parallel_agents", "actor": "finance_agent", "action": "reconcile_variance", "outcome": "success", "confidence": 0.6},
		{"timestamp": now, "stage": "decision_engine", "actor": "approval_policy", "action": "route_approval", "outcome": state.get("approval_required", "auto"), "confidence": 0.9},
	]

	return {
		"explainability": {
			"confidence_traces": confidence_traces,
			"action_audit_timeline": audit_timeline,
		}
	}


def _build_graph_workflow():
	graph_builder = StateGraph(WorkflowState)
	graph_builder.add_node("ingestion", ingestion_node)
	graph_builder.add_node("rag", rag_node)
	graph_builder.add_node("spend_agent", spend_node)
	graph_builder.add_node("sla_agent", sla_node)
	graph_builder.add_node("resource_agent", resource_node)
	graph_builder.add_node("finance_agent", finance_node)
	graph_builder.add_node("merge_anomalies", merge_anomalies_node)
	graph_builder.add_node("build_graph", graph_node)
	graph_builder.add_node("compute_impact", impact_node)
	graph_builder.add_node("decision", decision_node)
	graph_builder.add_node("explainability", explainability_node)

	graph_builder.add_edge(START, "ingestion")
	graph_builder.add_edge("ingestion", "rag")
	graph_builder.add_edge("rag", "spend_agent")
	graph_builder.add_edge("rag", "sla_agent")
	graph_builder.add_edge("rag", "resource_agent")
	graph_builder.add_edge("rag", "finance_agent")

	graph_builder.add_edge("spend_agent", "merge_anomalies")
	graph_builder.add_edge("sla_agent", "merge_anomalies")
	graph_builder.add_edge("resource_agent", "merge_anomalies")
	graph_builder.add_edge("finance_agent", "merge_anomalies")

	graph_builder.add_edge("merge_anomalies", "build_graph")
	graph_builder.add_edge("build_graph", "compute_impact")
	graph_builder.add_edge("compute_impact", "decision")
	graph_builder.add_edge("decision", "explainability")
	graph_builder.add_edge("explainability", END)

	return graph_builder.compile()


_WORKFLOW = _build_graph_workflow()


def run_langgraph_workflow(payload: Dict[str, Any]) -> WorkflowState:
	state: WorkflowState = {
		"query": payload.get("query", ""),
		"docs": payload.get("docs", []),
		"invoices": payload.get("invoices", []),
		"sla_logs": payload.get("sla_logs", []),
		"resources": payload.get("resources", []),
		"transactions": payload.get("transactions", []),
	}
	result = _WORKFLOW.invoke(state)
	return result  # type: ignore[return-value]