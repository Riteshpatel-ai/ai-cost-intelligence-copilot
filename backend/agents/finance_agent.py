
from typing import List, Dict, Any
from logging import getLogger

from backend.exceptions import ValidationError, DataQualityError, ProcessingError
from backend.logging_config import get_logger

logger = get_logger()


class FinanceAgent:
	def __init__(self, transactions: List[Dict[str, Any]]):
		self.transactions = transactions or []
		logger.info(f"FinanceAgent initialized with {len(self.transactions)} transactions")

	def reconcile(self) -> List[Dict[str, Any]]:
		"""Flag unmatched transactions."""
		if not self.transactions:
			logger.warning("No transactions to reconcile")
			return []
		
		error_count = 0
		try:
			seen = set()
			unmatched = []
			
			for idx, t in enumerate(self.transactions):
				try:
					key = (str(t.get('id', '')), float(t.get('amount', 0)))
					if key in seen:
						continue
					if not t.get('matched', False):
						unmatched.append(t)
						logger.debug(f"Unmatched transaction: id={t.get('id')}, amount={t.get('amount')}")
					seen.add(key)
				except (ValueError, TypeError, KeyError) as e:
					error_count += 1
					logger.warning(f"Error processing transaction {idx}: {e}")
					continue
			
			if error_count > len(self.transactions) * 0.1:
				raise DataQualityError(
					message="Too many errors while reconciling transactions",
					error_count=error_count,
					total_count=len(self.transactions)
				)
			
			logger.info(f"Reconciliation: {len(unmatched)}/{len(self.transactions)} unmatched transactions")
			return unmatched
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"Reconciliation failed: {e}")
			raise ProcessingError(
				message="Failed to reconcile transactions",
				stage="transaction_reconciliation"
			)

	def variance_analysis(self) -> List[Dict[str, Any]]:
		"""Flag transactions with variance above threshold."""
		if not self.transactions:
			logger.warning("No transactions for variance analysis")
			return []
		
		error_count = 0
		try:
			variances = []
			threshold = 1000  # INR
			
			for t in self.transactions:
				try:
					variance = float(t.get('variance', 0))
					if abs(variance) > threshold:
						variances.append(t)
						logger.debug(f"Variance detected: id={t.get('id')}, variance={variance}")
				except (ValueError, TypeError) as e:
					error_count += 1
					logger.warning(f"Error processing variance for transaction {t.get('id')}: {e}")
					continue
			
			if error_count > len(self.transactions) * 0.1:
				raise DataQualityError(
					message="Too many errors during variance analysis",
					error_count=error_count,
					total_count=len(self.transactions)
				)
			
			logger.info(f"Variance analysis: {len(variances)} transactions exceed threshold")
			return variances
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"Variance analysis failed: {e}")
			raise ProcessingError(
				message="Failed to perform variance analysis",
				stage="variance_analysis"
			)
