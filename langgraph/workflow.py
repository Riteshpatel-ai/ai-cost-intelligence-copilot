from typing import Any, Dict

from backend.langgraph_execution import run_langgraph_workflow, WorkflowState


def run_workflow(initial_state: Dict[str, Any]) -> WorkflowState:
	"""Compatibility wrapper around the compiled backend LangGraph pipeline."""
	return run_langgraph_workflow(initial_state)

