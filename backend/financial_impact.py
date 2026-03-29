def _clamp_probability(value: float) -> float:
	return max(0.0, min(1.0, float(value)))


def calculate_impact(amount: float, confidence: float, recovery: float) -> float:
	"""Expected recoverable impact using risk-weighted probability."""
	safe_amount = max(0.0, float(amount))
	safe_confidence = _clamp_probability(confidence)
	safe_recovery = _clamp_probability(recovery)
	return safe_amount * safe_confidence * safe_recovery
