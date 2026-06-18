import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging middleware."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        # Skip verbose logging for health checks
        is_health = request.url.path == "/api/health"

        if not is_health:
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Client: {request.client.host if request.client else 'unknown'}"
            )

        try:
            response = await call_next(request)
            process_time_ms = (time.perf_counter() - start_time) * 1000

            if not is_health:
                logger.info(
                    f"[{request_id}] {request.method} {request.url.path} "
                    f"-> {response.status_code} ({process_time_ms:.1f}ms)"
                )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time_ms:.1f}ms"
            return response
        except Exception as exc:
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"-> 500 ({process_time_ms:.1f}ms) - Error: {exc}"
            )
            raise
