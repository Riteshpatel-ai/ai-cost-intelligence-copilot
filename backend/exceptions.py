"""
Comprehensive error handling for Cost Intelligence Copilot.
Provides custom exceptions and error categorization.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Non-critical, can continue
    MEDIUM = "medium"    # Important but recoverable
    HIGH = "high"        # Critical, needs attention
    CRITICAL = "critical"  # System failure


class ErrorCategory(Enum):
    """Error categories for routing and handling"""
    VALIDATION = "validation"
    DATA_QUALITY = "data_quality"
    EXTERNAL_SERVICE = "external_service"
    PROCESSING = "processing"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    INTERNAL = "internal"


class CopilotException(Exception):
    """Base exception for Cost Intelligence Copilot"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.message = message
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.request_id = request_id
        self.retry_after = retry_after
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dict"""
        return {
            "error": True,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "request_id": self.request_id,
            "retry_after": self.retry_after,
        }


class ValidationError(CopilotException):
    """Raised when input validation fails"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[str] = None,
        received: Optional[Any] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if expected:
            details["expected"] = expected
        if received is not None:
            details["received"] = received
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            details=details,
            request_id=request_id,
        )


class DataQualityError(CopilotException):
    """Raised when data quality is insufficient"""
    
    def __init__(
        self,
        message: str,
        skipped_count: int = 0,
        error_count: int = 0,
        total_count: int = 0,
        request_id: Optional[str] = None,
    ):
        details: Dict[str, Any] = {
            "skipped_count": skipped_count,
            "error_count": error_count,
            "total_count": total_count,
        }
        
        if total_count > 0:
            details["quality_score"] = (total_count - error_count) / total_count
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DATA_QUALITY,
            details=details,
            request_id=request_id,
        )


class ExternalServiceError(CopilotException):
    """Raised when external service (LLM, API) fails"""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
        request_id: Optional[str] = None,
    ):
        details: Dict[str, Any] = {"service_name": service_name}
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXTERNAL_SERVICE,
            details=details,
            request_id=request_id,
            retry_after=retry_after,
        )


class ProcessingError(CopilotException):
    """Raised when agent processing fails"""
    
    def __init__(
        self,
        message: str,
        stage: str,
        record_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {"stage": stage}
        if record_id:
            details["record_id"] = record_id
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PROCESSING,
            details=details,
            request_id=request_id,
        )


class AuthorizationError(CopilotException):
    """Raised when user lacks permission"""
    
    def __init__(
        self,
        message: str,
        required_role: Optional[str] = None,
        action: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        details = {}
        if required_role:
            details["required_role"] = required_role
        if action:
            details["action"] = action
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHORIZATION,
            details=details,
            request_id=request_id,
        )


class NotFoundError(CopilotException):
    """Raised when resource not found"""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        request_id: Optional[str] = None,
    ):
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.NOT_FOUND,
            details=details,
            request_id=request_id,
        )


class CircuitBreakerOpen(ExternalServiceError):
    """Raised when circuit breaker is open"""
    
    def __init__(
        self,
        service_name: str,
        retry_after: int = 60,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Circuit breaker is open for {service_name}. Service temporarily unavailable.",
            service_name=service_name,
            retry_after=retry_after,
            request_id=request_id,
        )


# Error recovery/fallback strategies
class ErrorRecoveryStrategy:
    """Strategies for recovering from errors"""
    
    @staticmethod
    def fallback_for_llm_failure(query: str, context_docs: list) -> str:
        """Fallback answer when LLM unavailable"""
        if not query:
            return "Please provide a query."
        
        q = query.lower()
        
        # Pattern-based fallback responses
        if any(word in q for word in ["duplicate", "overpayment"]):
            return "Duplicate payment analysis: Based on available data, I found potential duplicate transactions. Please review the uploaded dataset for detailed matching analysis."
        
        if any(word in q for word in ["sla", "breach", "penalty"]):
            return "SLA analysis: I can identify approaching SLA breaches from operational signals. Please provide SLA logs for prediction."
        
        if any(word in q for word in ["resource", "utilization", "waste"]):
            return "Resource optimization: I can identify underutilized resources. Please provide resource usage data."
        
        if any(word in q for word in ["variance", "reconciliation", "mismatch"]):
            return "Financial reconciliation: I can detect transaction discrepancies and variance patterns. Upload transaction and invoice data."
        
        if any(word in q for word in ["saving", "impact", "recover", "cost"]):
            return "Impact analysis: I analyze financial impact across multiple domains. Share your operational and financial data for assessment."
        
        return "Cost intelligence analysis ready. Please provide data (invoices, SLA logs, resources, transactions) for comprehensive analysis."
    
    @staticmethod
    def fallback_for_data_quality_issue(agent_name: str, quality_score: float) -> Dict[str, Any]:
        """Fallback response when data quality is low"""
        return {
            "findings": [],
            "errors": [
                {
                    "message": f"Data quality issue in {agent_name}: only {quality_score:.1%} of data was usable",
                    "severity": "MEDIUM",
                    "recommendation": "Verify data format and required fields"
                }
            ],
            "quality_metrics": {
                "usable_score": quality_score,
                "agent": agent_name,
                "status": "partial_results"
            }
        }
