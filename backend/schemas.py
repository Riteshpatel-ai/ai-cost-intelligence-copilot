from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Constraints
MAX_QUERY_LENGTH = 2000
MAX_RECORDS = 100000


class BaseRecord(BaseModel):
	model_config = ConfigDict(extra="allow")


class InvoiceRecord(BaseRecord):
	id: Optional[str] = None
	vendor: Optional[str] = None
	amount: Optional[float] = None
	date: Optional[str] = None
	
	@field_validator('amount')
	@classmethod
	def validate_amount(cls, v: Optional[float]) -> Optional[float]:
		"""Validate amount is non-negative and reasonable"""
		if v is not None and v < 0:
			raise ValueError("Amount cannot be negative")
		if v is not None and v > 1_000_000_000:
			raise ValueError("Amount exceeds maximum threshold")
		return v


class SLALogRecord(BaseRecord):
	id: Optional[str] = None
	task: Optional[str] = None
	time_remaining: Optional[float] = None
	error_rate: Optional[float] = None
	penalty_risk: Optional[float] = None
	
	@field_validator('error_rate')
	@classmethod
	def validate_error_rate(cls, v: Optional[float]) -> Optional[float]:
		"""Validate error rate is between 0 and 1"""
		if v is not None and (v < 0 or v > 1):
			raise ValueError("Error rate must be between 0 and 1")
		return v


class ResourceRecord(BaseRecord):
	id: Optional[str] = None
	resource: Optional[str] = None
	utilization: Optional[float] = None
	waste: Optional[float] = None
	
	@field_validator('utilization')
	@classmethod
	def validate_utilization(cls, v: Optional[float]) -> Optional[float]:
		"""Validate utilization is between 0 and 1"""
		if v is not None and (v < 0 or v > 1):
			raise ValueError("Utilization must be between 0 and 1")
		return v


class TransactionRecord(BaseRecord):
	id: Optional[str] = None
	amount: Optional[float] = None
	matched: Optional[bool] = None
	variance: Optional[float] = None
	
	@field_validator('amount')
	@classmethod
	def validate_amount(cls, v: Optional[float]) -> Optional[float]:
		"""Validate amount is non-negative"""
		if v is not None and v < 0:
			raise ValueError("Amount cannot be negative")
		return v


class ChatRequest(BaseModel):
	query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
	docs: List[str] = Field(default_factory=list, max_length=1000)
	invoices: List[InvoiceRecord] = Field(default_factory=list, max_length=MAX_RECORDS)
	sla_logs: List[SLALogRecord] = Field(default_factory=list, max_length=MAX_RECORDS)
	resources: List[ResourceRecord] = Field(default_factory=list, max_length=MAX_RECORDS)
	transactions: List[TransactionRecord] = Field(default_factory=list, max_length=MAX_RECORDS)
	uploaded_rows: List[Dict[str, Any]] = Field(default_factory=list, max_length=MAX_RECORDS)
	uploaded_filename: Optional[str] = Field(None, max_length=255)
	
	@field_validator('query')
	@classmethod
	def validate_query(cls, v: str) -> str:
		"""Validate query is not empty or whitespace only"""
		if not v.strip():
			raise ValueError("Query cannot be empty or whitespace only")
		return v.strip()


class Position(BaseModel):
	x: float
	y: float


class GraphNode(BaseModel):
	id: str
	position: Position
	data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
	id: str
	source: str
	target: str
	label: str
	animated: bool = False


class GraphPayload(BaseModel):
	nodes: List[GraphNode] = Field(default_factory=list)
	edges: List[GraphEdge] = Field(default_factory=list)


class AnomaliesPayload(BaseModel):
	duplicates: List[Dict[str, Any]] = Field(default_factory=list)
	cost_leakage: List[Dict[str, Any]] = Field(default_factory=list)
	sla_breaches: List[Dict[str, Any]] = Field(default_factory=list)
	underutilized: List[Dict[str, Any]] = Field(default_factory=list)
	overutilized: List[Dict[str, Any]] = Field(default_factory=list)
	unmatched: List[Dict[str, Any]] = Field(default_factory=list)
	variance: List[Dict[str, Any]] = Field(default_factory=list)


class ActionDescriptor(BaseModel):
	type: str
	risk: Literal["low", "medium", "high"]
	approval_required: Literal["auto", "manager", "finance"]


class ImpactBreakdown(BaseModel):
	duplicate_payments: float
	sla_penalties: float
	resource_waste: float
	variance_risk: float
	total: float


class ConfidenceTrace(BaseModel):
	signal: str
	item_count: int
	confidence: float
	evidence: str


class ActionAuditEvent(BaseModel):
	timestamp: str
	stage: str
	actor: str
	action: str
	outcome: str
	confidence: Optional[float] = None


class ExplainabilityPayload(BaseModel):
	confidence_traces: List[ConfidenceTrace] = Field(default_factory=list)
	action_audit_timeline: List[ActionAuditEvent] = Field(default_factory=list)


class ReportArtifact(BaseModel):
	report_id: str
	title: str
	generated_at: str
	download_url: str
	currency: str = 'INR'


class ChatResponse(BaseModel):
	response: str
	anomalies: AnomaliesPayload
	recommendations: List[str] = Field(default_factory=list)
	graph: GraphPayload
	financial_impact: float
	financial_impact_breakdown: ImpactBreakdown
	risk_level: Literal["low", "medium", "high"]
	approval_required: Literal["auto", "manager", "finance"]
	actions: List[ActionDescriptor] = Field(default_factory=list)
	explainability: ExplainabilityPayload
	report: Optional[ReportArtifact] = None


class ActionRequest(BaseModel):
	action: str
	risk_level: Literal["low", "medium", "high"] = "medium"
	payload: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
	status: Literal["executed", "pending_approval"]
	message: str
	action: str
	risk_level: Literal["low", "medium", "high"]
	approval_required: Literal["auto", "manager", "finance"]
	payload: Dict[str, Any] = Field(default_factory=dict)