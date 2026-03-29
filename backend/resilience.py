"""
Circuit breaker implementation for external service calls.
Prevents cascading failures when services are unavailable.
"""

import time
import logging
from enum import Enum
from typing import Callable, Optional, Any, TypeVar
from datetime import datetime, timedelta

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service unavailable, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents repeated calls to a failing service.
    
    States:
    - CLOSED: Normal operation, all calls go through
    - OPEN: Service failing, calls are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited calls allowed
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker (for logging)
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before trying to recover
            expected_exception: Exception type to catch
            logger: Logger instance
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.logger = logger or logging.getLogger(__name__)
        
        # State tracking
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_attempt_time: Optional[datetime] = None
    
    def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception if function fails
        """
        
        # Check state and respond accordingly
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(f"[{self.name}] Circuit breaker entering HALF_OPEN state")
            else:
                from backend.exceptions import CircuitBreakerOpen
                raise CircuitBreakerOpen(self.name)
        
        # Record attempt
        self.last_attempt_time = datetime.utcnow()
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Success
            self._on_success()
            
            return result
            
        except self.expected_exception as e:
            # Failure
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Recovered! Close the circuit
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.logger.info(f"[{self.name}] Circuit breaker CLOSED (service recovered)")
        else:
            self.failure_count = 0
            self.success_count += 1
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        self.logger.warning(
            f"[{self.name}] Failure #{self.failure_count}/{self.failure_threshold}"
        )
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.error(
                f"[{self.name}] Circuit breaker OPEN (threshold reached)"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_attempt_time": self.last_attempt_time.isoformat() if self.last_attempt_time else None,
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger.info(f"[{self.name}] Circuit breaker manually reset")


class ResilientLLMClient:
    """
    Wrapper around LLM client with circuit breaker and retry logic.
    """
    
    def __init__(
        self,
        client: Any,
        max_retries: int = 2,
        timeout: int = 30,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize resilient LLM client.
        
        Args:
            client: OpenAI or Groq client
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            logger: Logger instance
        """
        self.client = client
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        
        # Circuit breaker for LLM calls
        self.circuit_breaker = CircuitBreaker(
            name="LLM",
            failure_threshold=5,
            recovery_timeout=60,
            logger=self.logger
        )
    
    def create_chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 300,
    ) -> str:
        """
        Create chat completion with circuit breaker protection.
        
        Args:
            model: Model name
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Max tokens in response
        
        Returns:
            Generated response
        
        Raises:
            CircuitBreakerOpen: If circuit is open
            ExternalServiceError: If all retries fail
        """
        
        from backend.exceptions import ExternalServiceError
        
        last_error = None
        
        # Try with retries
        for attempt in range(self.max_retries + 1):
            try:
                # Call through circuit breaker
                response = self.circuit_breaker.call(
                    self._call_with_timeout,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                return response.choices[0].message.content
                
            except self.circuit_breaker.expected_exception as e:
                last_error = e
                self.logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}"
                )
                
                # Back off before retry
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
        
        # All retries exhausted
        self.logger.error("LLM service unavailable after all retries")
        raise ExternalServiceError(
            message="LLM service unavailable. Please try again later.",
            service_name="LLM",
            retry_after=60,
        )
    
    def _call_with_timeout(self, **kwargs) -> Any:
        """Helper to call client with timeout"""
        return self.client.chat.completions.create(
            **kwargs,
            timeout=self.timeout,
        )
    
    def get_health_status(self) -> dict:
        """Get health status including circuit breaker state"""
        return {
            "service": "llm",
            "circuit_breaker": self.circuit_breaker.get_state(),
        }


# Example usage
if __name__ == "__main__":
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Create a simple circuit breaker
    cb = CircuitBreaker(
        name="ExampleService",
        failure_threshold=3,
        recovery_timeout=5
    )
    
    def failing_function():
        raise Exception("Service error")
    
    # This will fail quickly after 3 attempts
    for i in range(10):
        try:
            cb.call(failing_function)
        except Exception as e:
            print(f"Attempt {i+1}: {type(e).__name__}")
        
        time.sleep(1)
