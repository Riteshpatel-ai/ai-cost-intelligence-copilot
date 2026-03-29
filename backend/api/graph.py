
from typing import cast
from fastapi import APIRouter
from ..graph_builder.builder import GraphBuilder
from ..schemas import GraphPayload

router = APIRouter()

@router.get("/api/graph", response_model=GraphPayload)
async def get_graph() -> GraphPayload:
	# Sample graph for initial UI load.
	graph = GraphBuilder()
	graph.add_node("vendor_1", "vendor", label="Vendor A", risk="medium")
	graph.add_node("invoice_1", "invoice", label="Invoice 101", risk="high")
	graph.add_node("invoice_2", "invoice", label="Invoice 202", risk="high")
	graph.add_node("risk_1", "risk_event", label="Duplicate Payment", risk="high")
	graph.add_edge("vendor_1", "invoice_1", "PAID_TO")
	graph.add_edge("vendor_1", "invoice_2", "PAID_TO")
	graph.add_edge("invoice_1", "invoice_2", "DUPLICATE_OF")
	graph.add_edge("invoice_2", "risk_1", "CAUSES_RISK")
	return GraphPayload(**graph.build())  # type: ignore[arg-type]
