"""
Structured logging for Cost Intelligence Copilot.
Includes correlation IDs for request tracing and JSON formatted output.
"""

import logging
import json
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> Optional[str]:
    """Get current request correlation ID"""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current request"""
    correlation_id_var.set(correlation_id)


class StructuredFormatter(logging.Formatter):
    """Formats logs as JSON for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id() or "no-correlation",
            "service": "cost-copilot",
            "version": "1.0.0",
        }
        
        # Add custom fields if present
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'action'):
            log_data["action"] = record.action
        if hasattr(record, 'details'):
            log_data["details"] = record.details
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }
        
        return json.dumps(log_data)


class PerformanceFilter(logging.Filter):
    """Add performance metrics to logs"""
    
    def __init__(self):
        super().__init__()
        self.start_times: Dict[str, float] = {}
    
    def format_record_with_timing(self, record: logging.LogRecord, duration_ms: float):
        """Add timing to record"""
        record.duration_ms = duration_ms
        return record


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    format_json: bool = True
) -> logging.Logger:
    """
    Setup structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        format_json: Whether to format as JSON
    
    Returns:
        Configured logger
    """
    
    # Create logger
    logger = logging.getLogger("cost-copilot")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.propagate = False
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Choose formatter
    if format_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class RequestLogger:
    """Log request/response with correlation tracking"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        query_params: Optional[Dict] = None,
        user_id: Optional[str] = None
    ):
        """Log incoming request"""
        set_correlation_id(request_id)
        
        extra = {
            'request_id': request_id,
            'user_id': user_id or 'anonymous',
            'action': f'{method} {path}',
        }
        
        self.logger.info(
            f"Request: {method} {path}",
            extra=extra
        )
    
    def log_response(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None
    ):
        """Log outgoing response"""
        set_correlation_id(request_id)
        
        extra = {
            'request_id': request_id,
            'user_id': user_id or 'anonymous',
            'action': f'Response {status_code}',
            'details': {
                'status_code': status_code,
                'duration_ms': duration_ms
            }
        }
        
        level = logging.INFO if status_code < 400 else logging.WARNING
        self.logger.log(
            level,
            f"Response: {status_code} ({duration_ms:.1f}ms)",
            extra=extra
        )
    
    def log_error(
        self,
        request_id: str,
        error_message: str,
        error_type: str,
        user_id: Optional[str] = None,
    ):
        """Log error"""
        set_correlation_id(request_id)
        
        extra = {
            'request_id': request_id,
            'user_id': user_id or 'anonymous',
            'action': f'Error: {error_type}',
        }
        
        self.logger.error(
            f"Error: {error_message}",
            extra=extra,
            exc_info=True
        )
    
    def log_agent_execution(
        self,
        request_id: str,
        agent_name: str,
        findings_count: int,
        duration_ms: float,
        error_count: int = 0,
    ):
        """Log agent execution result"""
        set_correlation_id(request_id)
        
        extra = {
            'request_id': request_id,
            'action': f'{agent_name} execution',
            'details': {
                'findings': findings_count,
                'errors': error_count,
                'duration_ms': duration_ms
            }
        }
        
        self.logger.info(
            f"Agent {agent_name}: {findings_count} findings, {error_count} errors ({duration_ms:.1f}ms)",
            extra=extra
        )


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: str = "cost-copilot") -> logging.Logger:
    """Get or create logger"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return logging.getLogger(name)


# Example usage in modules
if __name__ == "__main__":
    logger = setup_logging(log_file="logs/copilot.log")
    req_logger = RequestLogger(logger)
    
    # Simulate request
    req_logger.log_request(
        request_id="req_abc123",
        method="POST",
        path="/api/chat",
        query_params={"query": "show duplicates"},
        user_id="user_456"
    )
    
    # Simulate agent execution
    req_logger.log_agent_execution(
        request_id="req_abc123",
        agent_name="SpendAgent",
        findings_count=5,
        duration_ms=1234.5,
        error_count=2
    )
    
    # Simulate response
    req_logger.log_response(
        request_id="req_abc123",
        status_code=200,
        duration_ms=2000.0
    )
