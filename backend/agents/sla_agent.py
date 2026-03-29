
from typing import List, Dict, Any
from logging import getLogger

from backend.exceptions import ValidationError, DataQualityError, ProcessingError
from backend.logging_config import get_logger

logger = get_logger()


class SLAAgent:
	def __init__(self, sla_logs: List[Dict[str, Any]]):
		self.sla_logs = sla_logs or []
		logger.info(f"SLAAgent initialized with {len(self.sla_logs)} logs")

	def predict_breaches(self) -> List[Dict[str, Any]]:
		"""Predict SLA breaches from operational signals."""
		if not self.sla_logs:
			logger.warning("No SLA logs to analyze")
			return []
		
		breaches = []
		error_count = 0
		try:
			for idx, log in enumerate(self.sla_logs):
				try:
					time_remaining = float(log.get('time_remaining', 9999))
					error_rate = float(log.get('error_rate', 0))
					
					if time_remaining < 2 or error_rate > 0.1:
						breaches.append(log)
						logger.debug(f"SLA breach detected: task={log.get('task')}, time_remaining={time_remaining}")
				except (ValueError, TypeError) as e:
					error_count += 1
					logger.warning(f"Error processing SLA log {idx}: {e}")
					continue
			
			if error_count > len(self.sla_logs) * 0.1:
				raise DataQualityError(
					message="Too many errors while predicting SLA breaches",
					error_count=error_count,
					total_count=len(self.sla_logs)
				)
			
			logger.info(f"SLA prediction: {len(breaches)}/{len(self.sla_logs)} potential breaches")
			return breaches
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"SLA breach prediction failed: {e}")
			raise ProcessingError(
				message="Failed to predict SLA breaches",
				stage="sla_breach_prediction"
			)
