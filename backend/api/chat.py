from fastapi import APIRouter
from typing import Any, Dict, List, Literal, cast

from ..agents.data_analyzer_agent import DataAnalyzerAgent
from ..agents.pattern_detection_agent import PatternDetectionAgent
from ..langgraph_execution import run_langgraph_workflow
from ..services.duplicate_payment_analyzer import analyze_uploaded_duplicates
from ..services.intake_store import load_latest_upload
from ..services.report_service import build_and_store_chat_report
from ..services.vector_store import VectorDocumentStore
from ..schemas import (
	ActionAuditEvent,
	ActionDescriptor,
	AnomaliesPayload,
	ChatRequest,
	ChatResponse,
	ConfidenceTrace,
	ExplainabilityPayload,
	GraphEdge,
	GraphNode,
	GraphPayload,
	ImpactBreakdown,
	Position,
	ReportArtifact,
)

router = APIRouter()
_VECTOR_STORE = VectorDocumentStore()


def _attach_report_artifact(query: str, response_model: ChatResponse) -> ChatResponse:
	report_artifact = build_and_store_chat_report(query=query, chat_payload=response_model.model_dump())
	response_model.report = ReportArtifact(**report_artifact)
	return response_model


def _contains_duplicate_query(query: str) -> bool:
	q = (query or '').strip().lower()
	keywords = ('duplicate', 'duplicates', 'overpayment', 'duplicate payment', 'double payment')
	return any(keyword in q for keyword in keywords)


def _contains_uploaded_data_query(query: str) -> bool:
	q = (query or '').strip().lower()
	keywords = (
		'duplicate',
		'overpayment',
		'report',
		'summary',
		'action',
		'approve',
		'saving',
		'recoverable',
		'recovery',
		'recover',
		'cost',
		'money',
		'spend',
		'leakage',
		'risk',
		'sla',
		'breach',
		'penalty',
		'resource',
		'finance',
		'anomaly',
	)
	return any(keyword in q for keyword in keywords)


def _looks_like_action_query(query: str) -> bool:
	q = (query or '').strip().lower()
	action_keywords = ('action', 'approve', 'fix first', 'what to fix', 'max savings', 'priority')
	return any(keyword in q for keyword in action_keywords)


def _looks_like_sla_query(query: str) -> bool:
	q = (query or '').strip().lower()
	sla_keywords = ('sla', 'breach', 'penalty', 'penalties', 'latency', 'uptime', 'response time')
	return any(keyword in q for keyword in sla_keywords)


def _looks_like_report_query(query: str) -> bool:
	q = (query or '').strip().lower()
	report_keywords = ('report', 'summary', 'overall', 'full picture', 'one report', 'quarter', 'command center')
	return any(keyword in q for keyword in report_keywords)


def _risk_for_impact(amount: float) -> Literal["low", "medium", "high"]:
	if amount >= 50000:
		return 'high'
	if amount >= 10000:
		return 'medium'
	return 'low'


def _approval_for_risk(risk: str) -> Literal["auto", "manager", "finance"]:
	if risk == 'high':
		return 'finance'
	if risk == 'medium':
		return 'manager'
	return 'auto'


def _fmt_inr(amount: float) -> str:
	return f"INR {float(amount or 0.0):,.2f}"


def _build_professional_message(
	title: str,
	context: str,
	findings: List[str],
	impact_lines: List[str] | None = None,
	action_lines: List[str] | None = None,
) -> str:
	lines: List[str] = [
		f"{title}",
		f"Context: {context}",
		"",
		"Key Findings:",
	]
	for item in findings:
		lines.append(f"- {item}")

	if impact_lines:
		lines.append("")
		lines.append("Impact Summary:")
		for item in impact_lines:
			lines.append(f"- {item}")

	if action_lines:
		lines.append("")
		lines.append("Recommended Next Actions:")
		for item in action_lines:
			lines.append(f"- {item}")

	return "\n".join(lines)


def _build_uploaded_data_chat_response(
	query: str,
	uploaded_rows: List[Dict[str, Any]] | None = None,
	uploaded_filename: str | None = None,
) -> ChatResponse | None:
	if not _contains_uploaded_data_query(query):
		return None

	rows = uploaded_rows or []
	filename = uploaded_filename or 'latest upload'
	upload_created_at = ''

	if not rows:
		upload = load_latest_upload()
		if not upload:
			return None
		rows = cast(List[Dict[str, Any]], upload.get('rows', []))
		if not rows:
			return None
		filename = str(upload.get('filename', filename))
		upload_created_at = str(upload.get('created_at', ''))
	else:
		upload = None

	analysis = analyze_uploaded_duplicates(rows, top_n=5)
	duplicate_sets = cast(List[Dict[str, Any]], analysis.get('duplicate_sets', []))
	total_impact = float(analysis.get('total_calculated_impact', 0.0) or 0.0)
	total_overpayment = float(analysis.get('total_overpayment', 0.0) or 0.0)
	data_analyzer = DataAnalyzerAgent()
	pattern_detector = PatternDetectionAgent()
	data_analysis = data_analyzer.analyze_rows(rows)

	top_spend_items = cast(List[Dict[str, Any]], data_analysis.get('top_spend_items', []))
	sla_breaches = cast(List[Dict[str, Any]], data_analysis.get('sla_breaches', []))
	estimated_optimization_impact = pattern_detector.estimate_optimization_impact(top_spend_items, top_n=3)
	sla_penalty_impact = sum(float(item.get('penalty_risk', 0.0)) * 0.75 for item in sla_breaches[:3])

	combined_impact = float(total_impact + estimated_optimization_impact + sla_penalty_impact)
	risk_level = _risk_for_impact(combined_impact)
	approval_required = _approval_for_risk(risk_level)
	is_action_query = _looks_like_action_query(query)
	is_sla_query = _looks_like_sla_query(query)
	is_report_query = _looks_like_report_query(query)
	is_duplicate_query = _contains_duplicate_query(query)

	duplicates: List[Dict[str, Any]] = []
	cost_leakage = pattern_detector.detect_cost_leakage(top_spend_items, top_n=3)
	nodes: List[GraphNode] = []
	edges: List[GraphEdge] = []

	for idx, item in enumerate(duplicate_sets[:5]):
		vendor = str(item.get('vendor', f'Group {idx + 1}'))
		dp_id = f"dup_{idx + 1}"
		node_vendor_id = f"vendor_{idx + 1}"
		node_risk_id = f"risk_{idx + 1}"

		duplicates.append(
			{
				'id': dp_id,
				'vendor': vendor,
				'amount': item.get('average_amount', 0.0),
				'date': '',
				'dup_count': item.get('dup_count', 0),
				'overpayment': item.get('overpayment', 0.0),
				'confidence': item.get('confidence', 0.0),
				'recovery_probability': item.get('recovery_probability', 0.0),
				'calculated_impact': item.get('calculated_impact', 0.0),
			}
		)

		nodes.append(
			GraphNode(
				id=node_vendor_id,
				position=Position(x=float(80 + (idx * 60)), y=float(80 + (idx * 65))),
				data={'label': vendor},
			)
		)
		nodes.append(
			GraphNode(
				id=node_risk_id,
				position=Position(x=float(340 + (idx * 45)), y=float(80 + (idx * 65))),
				data={'label': f"Duplicate Set {idx + 1}"},
			)
		)
		edges.append(
			GraphEdge(
				id=f"edge_{idx + 1}",
				source=node_vendor_id,
				target=node_risk_id,
				label='CAUSES_RISK',
			)
		)

	if is_report_query:
		top_duplicate_vendor = str(duplicate_sets[0].get('vendor', 'none')) if duplicate_sets else 'none'
		top_duplicate_impact = float(duplicate_sets[0].get('calculated_impact', 0.0)) if duplicate_sets else 0.0
		top_sla_penalty = float(sla_breaches[0].get('penalty_risk', 0.0)) if sla_breaches else 0.0
		top_spend_label = top_spend_items[0]['tool'] if top_spend_items else 'none'
		response = _build_professional_message(
			title='Executive Cost Intelligence Summary',
			context=f"Uploaded dataset '{filename}'",
			findings=[
				f"Duplicate clusters detected: {len(duplicate_sets)}; top vendor: {top_duplicate_vendor}.",
				f"Top spend concentration: {top_spend_label}.",
				f"SLA penalty risk signals this week: {len(sla_breaches)} (highest potential penalty {_fmt_inr(top_sla_penalty)}).",
			],
			impact_lines=[
				f"Top duplicate recoverable impact: {_fmt_inr(top_duplicate_impact)}.",
				f"Combined estimated recoverable impact this cycle: {_fmt_inr(combined_impact)}.",
			],
			action_lines=[
				'Prioritize the highest-impact duplicate cluster for immediate finance review.',
				'Release optimization actions for top spend categories in the current cycle.',
			],
		)
	elif is_sla_query and sla_breaches:
		top = sla_breaches[0]
		response = _build_professional_message(
			title='SLA Penalty Risk Assessment',
			context=f"Uploaded dataset '{filename}'",
			findings=[
				f"SLA breach signals identified: {len(sla_breaches)}.",
				f"Highest-risk task: {top.get('task', 'unknown')} with potential penalty {_fmt_inr(float(top.get('penalty_risk', 0.0)))}.",
			],
			impact_lines=[
				f"Estimated penalty-prevention impact (top 3 signals at 0.75 confidence): {_fmt_inr(sla_penalty_impact)}.",
			],
			action_lines=[
				'Escalate high-risk tasks to SLA control desk for immediate mitigation.',
			],
		)
	elif is_sla_query:
		top_spend_summary = ', '.join(
			f"{item['tool']} (INR {float(item['amount']):.2f})" for item in top_spend_items[:3]
		) or 'no high-spend tools detected'
		response = _build_professional_message(
			title='SLA Risk Readiness Check',
			context=f"Uploaded dataset '{filename}'",
			findings=[
				'SLA breach/penalty predictor fields are not present in the uploaded file.',
				f"Available spend signals: {top_spend_summary}.",
			],
			action_lines=[
				'Include fields: SLA_Breach_Risk, Penalty_Risk_INR, Days_To_Breach for predictive SLA analytics.',
			],
		)
	elif is_action_query and duplicate_sets:
		top = duplicate_sets[0]
		top_spend_label = top_spend_items[0]['tool'] if top_spend_items else 'highest-cost tool cluster'
		response = _build_professional_message(
			title='Approval Prioritization for Maximum Savings',
			context=f"Uploaded dataset '{filename}'",
			findings=[
				f"Highest-impact duplicate cluster: {top.get('vendor', 'unknown')} ({_fmt_inr(float(top.get('calculated_impact', 0.0)))} recoverable).",
				f"Top spend optimization candidate: {top_spend_label}.",
			],
			impact_lines=[
				f"Total estimated recoverable impact from current dataset: {_fmt_inr(combined_impact)}.",
			],
			action_lines=[
				"Priority 1: Block and recover payments for the highest-impact duplicate cluster.",
				'Priority 2: Launch optimization plan for top cost categories.',
				'Priority 3: Enforce pre-approval duplicate controls before payout.',
			],
		)
	elif is_duplicate_query and duplicate_sets:
		top = duplicate_sets[0]
		overpayment = float(top.get('overpayment', 0.0))
		confidence = float(top.get('confidence', 0.0))
		recovery_probability = float(top.get('recovery_probability', 0.0))
		calculated_impact = float(top.get('calculated_impact', 0.0))
		response = _build_professional_message(
			title='Duplicate Payment Impact Assessment',
			context=f"Uploaded dataset '{filename}'",
			findings=[
				f"Duplicate clusters detected: {len(duplicate_sets)}.",
				f"Top cluster: {top.get('vendor', 'unknown')} with {top.get('dup_count', 0)} similar payments.",
				f"Estimated overpayment in top cluster: {_fmt_inr(overpayment)}.",
			],
			impact_lines=[
				f"Impact math: amount x confidence x recoveryProbability = {overpayment:.2f} x {confidence:.2f} x {recovery_probability:.2f} = {calculated_impact:.2f}.",
				f"Calculated recoverable impact for top cluster: {_fmt_inr(calculated_impact)}.",
			],
			action_lines=[
				'Validate duplicate evidence with finance controls and vendor records.',
				'Initiate recovery workflow for the highest-impact cluster first.',
			],
		)
	elif is_duplicate_query:
		top_spend_summary = ', '.join(
			f"{item['tool']} (INR {float(item['amount']):.2f})" for item in top_spend_items[:3]
		) or 'no high-spend tools detected'
		if is_action_query:
			response = (
				f"Analyzed uploaded file '{filename}'. No direct duplicate clusters were detected, "
				f"but the top spend concentrations are: {top_spend_summary}. "
				"Approve optimization actions for these tools first, then enforce stronger duplicate controls."
			)
		else:
			response = (
				f"Analyzed uploaded file '{filename}'. "
				"No duplicate clusters were detected with current matching rules. "
				f"Top spend concentrations: {top_spend_summary}."
			)
	else:
		top_spend_summary = ', '.join(
			f"{item['tool']} (INR {float(item['amount']):.2f})" for item in top_spend_items[:3]
		) or 'no high-spend tools detected'
		response = (
			f"Analyzed uploaded file '{filename}'. "
			f"Top spend concentrations: {top_spend_summary}. "
			f"Current estimated recoverable impact across detected leakages is INR {combined_impact:.2f}."
		)

	if is_report_query:
		recommendations = [
			'Approve highest-impact duplicate recovery and freeze further duplicate payouts.',
			'Prioritize top spend optimization actions with manager approval this week.',
			'Feed SLA breach/penalty fields in future uploads for penalty-risk precision.',
		]
	elif is_sla_query:
		recommendations = [
			'Escalate high-risk SLA tasks and set daily review until breach risk drops.',
			'Approve preventive remediation before penalties are realized.',
			'Include SLA_Breach_Risk, Penalty_Risk_INR, Days_To_Breach in uploads for stronger predictions.',
		]
	elif is_action_query:
		recommendations = [
			'Review and approve recovery workflow for highest-impact duplicate cluster first.',
			'Prioritize optimization playbooks for top spend tools from uploaded dataset.',
			'Enable pre-payment duplicate controls on vendor, amount, and invoice references.',
		]
	else:
		recommendations = [
			'Review the top duplicate clusters and validate with finance before action.',
			'Prioritize recovery on clusters with highest calculated impact.',
			'Reinforce payment controls using invoice/date/payee match checks before approval.',
		]

	if is_sla_query:
		actions = [
			ActionDescriptor(type='prevent_sla_breach', risk='high', approval_required='finance'),
			ActionDescriptor(type='create_sla_escalation_ticket', risk='medium', approval_required='manager'),
			ActionDescriptor(type='enable_sla_risk_monitoring', risk='low', approval_required='auto'),
		]
	elif is_action_query or is_report_query:
		actions = [
			ActionDescriptor(type='block_payment', risk='high', approval_required='finance'),
			ActionDescriptor(type='optimize_high_spend_tools', risk='medium', approval_required='manager'),
			ActionDescriptor(type='tighten_duplicate_rules', risk='low', approval_required='auto'),
		]
	else:
		actions = [
			ActionDescriptor(type='block_payment', risk='high', approval_required='finance'),
			ActionDescriptor(type='create_recovery_ticket', risk='medium', approval_required='manager'),
			ActionDescriptor(type='tighten_duplicate_rules', risk='low', approval_required='auto'),
		]

	impact_breakdown = ImpactBreakdown(
		duplicate_payments=total_impact,
		sla_penalties=sla_penalty_impact,
		resource_waste=estimated_optimization_impact,
		variance_risk=0.0,
		total=combined_impact,
	)

	confidence_traces: List[ConfidenceTrace] = [
		ConfidenceTrace(
			signal='uploaded_duplicate_analysis',
			item_count=len(duplicate_sets),
			confidence=0.82,
			evidence=(
				f"Rows analyzed={analysis.get('coverage', {}).get('rows_analyzed', 0)}, "
				f"rows with amount={analysis.get('coverage', {}).get('rows_with_amount', 0)}"
			),
		)
	]
	if top_spend_items:
		confidence_traces.append(
			ConfidenceTrace(
				signal='uploaded_spend_concentration',
				item_count=len(top_spend_items),
				confidence=0.7,
				evidence='Top cost tools ranked from uploaded Cost_INR values.',
			)
		)
	if is_sla_query and not sla_breaches:
		confidence_traces.append(
			ConfidenceTrace(
				signal='uploaded_sla_scan',
				item_count=0,
				confidence=0.45,
				evidence='No SLA_Breach_Risk/Penalty_Risk_INR style fields were found in uploaded rows.',
			)
		)
	elif sla_breaches:
		confidence_traces.append(
			ConfidenceTrace(
				signal='uploaded_sla_scan',
				item_count=len(sla_breaches),
				confidence=0.73,
				evidence='SLA breach and penalty signals detected from uploaded fields.',
			)
		)

	action_audit_timeline: List[ActionAuditEvent] = [
		ActionAuditEvent(
			timestamp=upload_created_at,
			stage='manual_upload',
			actor='ingestion_api',
			action='persist_dataset',
			outcome='success',
			confidence=None,
		),
		ActionAuditEvent(
			timestamp=upload_created_at,
			stage='chat_analysis',
			actor='duplicate_payment_analyzer',
			action='detect_duplicate_clusters',
			outcome='success',
			confidence=0.82,
		),
	]

	chat_response = ChatResponse(
		response=response,
		anomalies=AnomaliesPayload(
			duplicates=duplicates,
			cost_leakage=cost_leakage,
			sla_breaches=sla_breaches,
			underutilized=[],
			overutilized=[],
			unmatched=[],
			variance=[],
		),
		recommendations=recommendations,
		graph=GraphPayload(nodes=nodes, edges=edges),
		financial_impact=combined_impact,
		financial_impact_breakdown=impact_breakdown,
		risk_level=risk_level,
		approval_required=approval_required,
		actions=actions,
		explainability=ExplainabilityPayload(
			confidence_traces=confidence_traces,
			action_audit_timeline=action_audit_timeline,
		),
	)
	return _attach_report_artifact(query, chat_response)


def _build_no_upload_data_response() -> ChatResponse:
	chat_response = ChatResponse(
		response=(
			"No uploaded dataset is available for analysis. "
			"Use Start Here > Manual File Upload, then run your query again."
		),
		anomalies=AnomaliesPayload(
			duplicates=[],
			cost_leakage=[],
			sla_breaches=[],
			underutilized=[],
			overutilized=[],
			unmatched=[],
			variance=[],
		),
		recommendations=[
			'Upload CSV or XLSX from the Start Here intake section.',
			'Re-run your savings or action query to compute impact and approval priorities.',
		],
		graph=GraphPayload(nodes=[], edges=[]),
		financial_impact=0.0,
		financial_impact_breakdown=ImpactBreakdown(
			duplicate_payments=0.0,
			sla_penalties=0.0,
			resource_waste=0.0,
			variance_risk=0.0,
			total=0.0,
		),
		risk_level='low',
		approval_required='auto',
		actions=[ActionDescriptor(type='upload_dataset', risk='low', approval_required='auto')],
		explainability=ExplainabilityPayload(confidence_traces=[], action_audit_timeline=[]),
	)
	return _attach_report_artifact('no_upload_data', chat_response)


def _risk_literal(value: Any) -> Literal["low", "medium", "high"]:
	if value in {"low", "medium", "high"}:
		return cast(Literal["low", "medium", "high"], value)
	return "low"


def _approval_literal(value: Any) -> Literal["auto", "manager", "finance"]:
	if value in {"auto", "manager", "finance"}:
		return cast(Literal["auto", "manager", "finance"], value)
	return "auto"


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
	runtime_docs = req.docs or _VECTOR_STORE.recent_document_texts(limit=200)
	has_runtime_docs = len(runtime_docs) > 0

	uploaded_data_response = _build_uploaded_data_chat_response(
		req.query,
		uploaded_rows=req.uploaded_rows,
		uploaded_filename=req.uploaded_filename,
	)
	if uploaded_data_response is not None:
		return uploaded_data_response

	if _contains_uploaded_data_query(req.query) and not has_runtime_docs:
		return _build_no_upload_data_response()

	workflow_payload = req.model_dump()
	workflow_payload["docs"] = runtime_docs
	workflow_output = run_langgraph_workflow(workflow_payload)
	anomalies = AnomaliesPayload(**workflow_output.get("anomalies", {}))
	graph_raw = cast(Dict[str, Any], workflow_output.get("graph", {"nodes": [], "edges": []}))
	node_models: List[GraphNode] = [
		GraphNode(**node) for node in cast(List[Dict[str, Any]], graph_raw.get("nodes", []))
	]
	edge_models: List[GraphEdge] = [
		GraphEdge(**edge) for edge in cast(List[Dict[str, Any]], graph_raw.get("edges", []))
	]
	graph = GraphPayload(nodes=node_models, edges=edge_models)
	impact_breakdown = ImpactBreakdown(
		**workflow_output.get(
			"financial_impact_breakdown",
			{
				"duplicate_payments": 0.0,
				"sla_penalties": 0.0,
				"resource_waste": 0.0,
				"variance_risk": 0.0,
				"total": 0.0,
			},
		)
	)
	actions = [
		ActionDescriptor(
			type=str(item.get("type", "create_ticket")),
			risk=_risk_literal(item.get("risk")),
			approval_required=_approval_literal(item.get("approval_required")),
		)
		for item in cast(List[Dict[str, Any]], workflow_output.get("actions", []))
	]
	explainability = ExplainabilityPayload(
		**workflow_output.get(
			"explainability",
			{"confidence_traces": [], "action_audit_timeline": []},
		)
	)

	chat_response = ChatResponse(
		response=workflow_output.get("rag_response", ""),
		anomalies=anomalies,
		recommendations=workflow_output.get("recommendations", []),
		graph=graph,
		financial_impact=workflow_output.get("financial_impact", 0.0),
		financial_impact_breakdown=impact_breakdown,
		risk_level=_risk_literal(workflow_output.get("risk_level", "low")),
		approval_required=_approval_literal(workflow_output.get("approval_required", "auto")),
		actions=actions,
		explainability=explainability,
	)
	return _attach_report_artifact(req.query, chat_response)
