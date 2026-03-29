# AgentState definition for LangGraph
from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict):
    query: str
    context_docs: List[Any]
    anomalies: Dict[str, List[Any]]
    graph_data: Dict[str, Any]
    recommendations: List[Any]
    actions: List[Any]
    financial_impact: float
    risk_level: str
    approval_required: str
    explainability: Dict[str, Any]
