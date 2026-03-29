# FastAPI app entrypoint for backend
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from uuid import uuid4

from backend.api import action, chat, gmail, graph, ingest, report
from backend.config.logging import setup_logging
from backend.logging_config import RequestLogger, get_logger, set_correlation_id
from backend.exceptions import CopilotException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize logging
logger = setup_logging()
base_logger = get_logger()
req_logger = RequestLogger(base_logger)
logger.info("Starting Cost Intelligence Copilot")

app = FastAPI()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Request tracking middleware - logs all requests with correlation IDs
@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    """Add correlation ID and request tracking to all requests"""
    import time
    request_id = str(uuid4())
    set_correlation_id(request_id)
    
    start_time = time.time()
    req_logger.log_request(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params) if request.query_params else None
    )
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        req_logger.log_response(
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        return response
    except CopilotException as e:
        duration_ms = (time.time() - start_time) * 1000
        req_logger.log_error(
            request_id=request_id,
            error_message=str(e),
            error_type=type(e).__name__
        )
        return JSONResponse(
            status_code=400,
            content=e.to_dict()
        )
    except RateLimitExceeded as e:
        duration_ms = (time.time() - start_time) * 1000
        req_logger.log_error(
            request_id=request_id,
            error_message="Rate limit exceeded",
            error_type="RateLimitExceeded"
        )
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests", "detail": str(e)}
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        req_logger.log_error(
            request_id=request_id,
            error_message=str(e),
            error_type=type(e).__name__
        )
        logger.exception(f"Unhandled exception in request {request_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "request_id": request_id}
        )

# Include routers
app.include_router(chat.router)
app.include_router(action.router)
app.include_router(graph.router)
app.include_router(ingest.router)
app.include_router(gmail.router)
app.include_router(report.router)

@app.get("/")
def root():
    return {"message": "AI Cost Intelligence Copilot Backend Running"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cost-intelligence-copilot",
        "version": "1.0.0"
    }
