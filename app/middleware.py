from fastapi.responses import JSONResponse
from app.logger import logger
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        url = request.url.path

        logger.info(f"Incoming request: {method} {url}")

        try:
            response = await call_next(request)
            logger.info(f"Completed request: {method} {url} - Status: {response.status_code}")
            return response
        except Exception as e:
            logger.exception(f"Unhandled exception for {method} {url}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Internal server error"},
            )

