import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..services.metrics import REQUEST_COUNT, REQUEST_LATENCY


class MetricsLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.perf_counter() - start
            path = request.url.path
            method = request.method
            status = str(response.status_code if response else 500)
            REQUEST_COUNT.labels(path=path, method=method, status=status).inc()
            REQUEST_LATENCY.labels(path=path, method=method).observe(duration)
            structlog.get_logger().info(
                "request",
                path=path,
                method=method,
                status=status,
                duration_ms=int(duration * 1000),
            )


