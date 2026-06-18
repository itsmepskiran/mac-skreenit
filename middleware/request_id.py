# backend/middleware/request_id.py

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from utils_others.logger import logger  # ✅ Import logger
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar('request_id', default='')

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow client to send their own request ID
        incoming_id = request.headers.get("X-Request-ID")

        # Generate a short readable ID
        request_id = incoming_id or uuid.uuid4().hex[:12]

        # Attach to request state for app usage
        request.state.request_id = request_id
        
        # ✅ Set the ContextVar for the Logger
        token = request_id_context.set(request_id)

        try:
            response = await call_next(request)

        except Exception as e:
            # Log the error (Logger will now auto-pick request_id from context)
            logger.error("Unhandled exception", extra={
                "path": request.url.path,
                "error": str(e)
            })

            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": "Internal server error",
                    "request_id": request_id
                }
            )
        
        finally:
            # ✅ Clean up context var
            request_id_context.reset(token)

        # Always add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response