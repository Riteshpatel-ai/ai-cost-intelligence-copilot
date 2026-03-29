from typing import Literal
from fastapi import APIRouter

from ..schemas import ActionRequest, ActionResponse

router = APIRouter()


def _approval_role_for_risk(risk: str) -> Literal["auto", "manager", "finance"]:
	risk = (risk or "").lower()
	if risk == "high":
		return "finance"
	if risk == "medium":
		return "manager"
	return "auto"

@router.post("/api/action", response_model=ActionResponse)
async def action_endpoint(req: ActionRequest) -> ActionResponse:
	approval_required = _approval_role_for_risk(req.risk_level)
	auto_approved = approval_required == "auto"

	if auto_approved:
		status = "executed"
		message = f"Action '{req.action}' executed automatically."
	else:
		status = "pending_approval"
		message = f"Action '{req.action}' queued for {approval_required} approval."

	return ActionResponse(
		status=status,
		message=message,
		action=req.action,
		risk_level=req.risk_level,
		approval_required=approval_required,
		payload=req.payload,
	)
