
from typing import List, Dict, Any
from logging import getLogger

from backend.exceptions import ValidationError, DataQualityError, ProcessingError
from backend.logging_config import get_logger

logger = get_logger()


class ResourceAgent:
	def __init__(self, resources: List[Dict[str, Any]]):
		self.resources = resources or []
		logger.info(f"ResourceAgent initialized with {len(self.resources)} resources")

	def underutilized(self) -> List[Dict[str, Any]]:
		"""Flag resources with < 30% utilization."""
		if not self.resources:
			logger.warning("No resources to analyze for underutilization")
			return []
		
		underutilized = []
		error_count = 0
		try:
			for resource in self.resources:
				try:
					utilization = float(resource.get('utilization', 0))
					if utilization < 0.3:
						underutilized.append(resource)
						logger.debug(f"Underutilized resource: {resource.get('name')} at {utilization*100:.1f}%")
				except (ValueError, TypeError) as e:
					error_count += 1
					logger.warning(f"Error processing resource {resource.get('name')}: {e}")
					continue
			
			if error_count > len(self.resources) * 0.1:
				raise DataQualityError(
					message="Too many errors while analyzing resources",
					error_count=error_count,
					total_count=len(self.resources)
				)
			
			logger.info(f"Resource analysis: {len(underutilized)} underutilized resources found")
			return underutilized
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"Underutilization analysis failed: {e}")
			raise ProcessingError(
				message="Failed to analyze underutilized resources",
				stage="underutilization_detection"
			)

	def overutilized(self) -> List[Dict[str, Any]]:
		"""Flag resources with > 90% utilization."""
		if not self.resources:
			logger.warning("No resources to analyze for overutilization")
			return []
		
		overutilized = []
		error_count = 0
		try:
			for resource in self.resources:
				try:
					utilization = float(resource.get('utilization', 0))
					if utilization > 0.9:
						overutilized.append(resource)
						logger.debug(f"Overutilized resource: {resource.get('name')} at {utilization*100:.1f}%")
				except (ValueError, TypeError) as e:
					error_count += 1
					logger.warning(f"Error processing resource {resource.get('name')}: {e}")
					continue
			
			if error_count > len(self.resources) * 0.1:
				raise DataQualityError(
					message="Too many errors while analyzing resources",
					error_count=error_count,
					total_count=len(self.resources)
				)
			
			logger.info(f"Resource analysis: {len(overutilized)} overutilized resources found")
			return overutilized
		except DataQualityError:
			raise
		except Exception as e:
			logger.exception(f"Overutilization analysis failed: {e}")
			raise ProcessingError(
				message="Failed to analyze overutilized resources",
				stage="overutilization_detection"
			)
