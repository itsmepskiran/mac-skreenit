from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from utils_others.logger import logger


# ---------------------------------------------------------
# BASE APPLICATION ERRORS
# ---------------------------------------------------------
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404, code="not_found")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, code="unauthorized")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, code="forbidden")


class ValidationError(AppError):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422, code="validation_error")


# ---------------------------------------------------------
# REGISTER GLOBAL EXCEPTION HANDLERS
# ---------------------------------------------------------
def register_exception_handlers(app: FastAPI) -> None:

    # -----------------------------
    # Custom AppError
    # -----------------------------
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        logger.error(
            f"AppError: {exc.code} - {exc.message}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "request_id": getattr(request.state, "request_id", None),
                "user_id": getattr(getattr(request.state, "user", {}), "id", None),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # -----------------------------
    # FastAPI validation errors
    # -----------------------------
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        logger.error(
            "Request validation failed",
            extra={
                "errors": exc.errors(),
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        
        # Convert errors to safe JSON format (handle bytes)
        def make_safe(obj):    
            if isinstance(obj, bytes):
                return obj.decode('utf-8', errors='replace')
            elif isinstance(obj, dict):
                return {k: make_safe(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_safe(item) for item in obj]
            return obj
        
        safe_errors = make_safe(exc.errors())
        
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "error": "validation_error",
                "message": safe_errors,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # -----------------------------
    # HTTPException (FastAPI built-in)
    # -----------------------------
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        logger.warning(
            f"HTTPException: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        
        # Determine error type based on the detail message
        error_type = "http_error"
        if "already registered" in str(exc.detail).lower():
            error_type = "email_exists"
        elif "invalid credentials" in str(exc.detail).lower():
            error_type = "invalid_credentials"
        elif "not found" in str(exc.detail).lower():
            error_type = "not_found"
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": error_type,
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # -----------------------------
    # Unexpected server errors
    # -----------------------------
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception(
            "Unexpected server error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        
        # Use actual error message if available, otherwise generic
        error_message = str(exc) if str(exc) else "Internal server error"
        
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": "server_error",
                "message": error_message,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
