
from typing import List, Dict, Any
import numpy as np
from logging import getLogger

from backend.exceptions import ValidationError, DataQualityError, ProcessingError
from backend.logging_config import get_logger

logger = get_logger()


class SpendAgent:
	def __init__(self, invoices: List[Dict[str, Any]]):
		if not isinstance(invoices, list):
			logger.warning(f"Expected list, got {type(invoices)}")
			self.invoices = []
		else:
			self.invoices = invoices or []
		logger.info(f"SpendAgent initialized with {len(self.invoices)} invoices")

	def detect_duplicates(self) -> List[Dict[str, Any]]:
		"""Detect duplicate invoices by vendor+amount+date."""
		if not self.invoices:
			logger.warning("No invoices to analyze for duplicates")
			return []
		
		seen = {}
		duplicates = []
		error_count = 0
		skipped_count = 0
		
		for idx, inv in enumerate(self.invoices):
			try:
				# Validate and extract fields
				vendor = str(inv.get('vendor', '')).strip()
				amount = float(inv.get('amount', 0))
				date = str(inv.get('date', '')).strip()
				
				# Skip invalid records
				if not vendor or amount <= 0 or not date:
					logger.debug(f"Skipping invalid invoice {idx}: {inv}")
					skipped_count += 1
					continue
				
				# Create key for grouping
				key = (vendor, amount, date)
				
				if key in seen:
					logger.debug(f"Duplicate found: vendor={vendor}, amount={amount}, date={date}")
					duplicates.append(inv)
				else:
					seen[key] = inv
					
			except (ValueError, TypeError, KeyError) as e:
				error_count += 1
				logger.warning(f"Error processing invoice {idx}: {e}")
				continue
			except Exception as e:
				error_count += 1
				logger.exception(f"Unexpected error processing invoice {idx}: {e}")
				continue
		
		logger.info(f"Duplicate detection: {len(duplicates)}/{len(self.invoices)} invoices are duplicates")
		
		# Raise error if too many failures
		if error_count > len(self.invoices) * 0.1:  # More than 10% failure rate
			raise DataQualityError(
				message="Too many errors while detecting duplicates",
				error_count=error_count,
				skipped_count=skipped_count,
				total_count=len(self.invoices)
			)
		
		return duplicates

	def detect_cost_leakage(self) -> List[Dict[str, Any]]:
		"""Detect anomalously high-cost invoices (95th percentile)."""
		if not self.invoices:
			logger.warning("No invoices to analyze for cost leakage")
			return []
		
		try:
			# Extract valid amounts
			valid_amounts = []
			invalid_count = 0
			for inv in self.invoices:
				try:
					amount = float(inv.get('amount', 0))
					if amount > 0:
						valid_amounts.append(amount)
				except (ValueError, TypeError):
					invalid_count += 1
					continue
			
			if not valid_amounts:
				raise DataQualityError(
					message="No valid amounts found for cost leakage analysis",
					error_count=invalid_count,
					total_count=len(self.invoices)
				)
			
			# Calculate 95th percentile threshold
			threshold = np.percentile(valid_amounts, 95)
			logger.info(f"Cost leakage threshold (95th percentile): {threshold}")
			
			# Find outliers
			leakage = []
			for inv in self.invoices:
				try:
					amount = float(inv.get('amount', 0))
					if amount > threshold:
						leakage.append(inv)
						logger.debug(f"Cost leakage found: {inv.get('vendor')} - INR {amount}")
				except (ValueError, TypeError):
					continue
			
			logger.info(f"Cost leakage detection: {len(leakage)} high-cost invoices found")
			return leakage
			
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"Cost leakage detection failed: {e}")
			raise ProcessingError(
				message="Failed to detect cost leakage",
				stage="cost_leakage_detection"
			)
