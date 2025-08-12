"""Middleware for metrics and logging."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request metrics and structured logging."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Add request ID to context
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            # Log request start
            self.logger.info(
                "request_start",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else None,
            )
            
            # Process request
            try:
                response = await call_next(request)
                duration = time.time() - start_time
                
                # Log successful response
                self.logger.info(
                    "request_complete",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                )
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                self.logger.error(
                    "request_error",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=round(duration * 1000, 2),
                    error=str(e),
                )
                
                raise
