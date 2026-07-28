import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import HTTP_DURATION, HTTP_REQUESTS

logger = logging.getLogger("finanalytics.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", "")[:128] or str(uuid.uuid4())
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - started_at
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            HTTP_REQUESTS.labels(request.method, route_path, "500").inc()
            HTTP_DURATION.labels(request.method, route_path).observe(duration_seconds)
            logger.exception(
                "http_request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )
            raise

        response.headers["X-Request-ID"] = request_id
        duration_seconds = time.perf_counter() - started_at
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        HTTP_REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
        HTTP_DURATION.labels(request.method, route_path).observe(duration_seconds)
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )
        return response
