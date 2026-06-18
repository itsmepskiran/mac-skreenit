# backend/middleware/auth_middleware.py

import os
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from services.auth_service import AuthService
from utils_others.logger import logger

# ---------------------------------------------------------
# CONFIG: EXCLUDED PATHS (Public)
# ---------------------------------------------------------
# Ensure these match the exact prefixes and full paths used in your routers
EXCLUDED_PATHS = {
    "/",
    "/favicon.ico",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/api/v1/health",
    "/api/v1/login",
    "/api/v1/register",
    "/api/v1/confirm-email",
    "/api/v1/forgot-password",
    "/api/v1/reset-password",
    "/api/v1/verify-email",
    "/api/v1/locations/countries",
    "/api/v1/locations/states",
    "/api/v1/locations/cities",
    "/api/v1/locations/universities",
    "/api/v1/locations/colleges",
    "/api/v1/reference/all",
    "/api/v1/reference/departments",
    "/api/v1/dashboard/jobs",
    "/api/v1/dashboard/jobs/",
    "/api/v1/reference/roles",
    "/api/v1/reference/employment-types",
    "/api/v1/reference/industries",
    "/api/v1/reference/job-types",
    "/api/v1/reference/education-levels",
    "/api/v1/reference/salary-ranges",
    "/api/v1/reference/experience-levels",
    "/api/v1/locations/search",
    "/api/v1/training/courses",
    "/api/v1/training/register-college",
    "/api/v1/training/register-corporate",
    "/api/v1/training/create-order",
    "/api/v1/training/payment-success",
    "/api/v1/training/webhook",
    "/api/v1/training/registrations",
    "/api/v1/training/payment-config",
    "/api/v1/admin/login",
    "/api/v1/subscription/pricing/plans",
    "/api/v1/subscription/payment-config",
    "/api/v1/subscription/webhook",
}

class CustomAuthMiddleware(BaseHTTPMiddleware):
    """
    Custom Authentication Middleware.
    Validates JWT tokens using the custom auth service.
    """

    def __init__(self, app, excluded_paths=None):
        super().__init__(app)
        # Combine provided paths with default excluded set
        self.excluded_paths = EXCLUDED_PATHS.copy()
        if excluded_paths:
            self.excluded_paths.update(excluded_paths)
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path  # This includes query params in some cases
        
        # 1. Allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # 2. Allow Static Files & Logos
        if path.startswith("/logos") or path.startswith("/static") or path.startswith("/uploads") or path.startswith("/datastorage"):
            return await call_next(request)

        # 3. Check Excluded Paths (Handling trailing slashes and query params)
        # Strip query parameters for excluded path matching
        path_without_query = path.split('?')[0] if '?' in path else path
        clean_path = path_without_query.rstrip("/")
        is_excluded = clean_path in self.excluded_paths or path_without_query in self.excluded_paths

        # Also exclude subscription details endpoint (dynamic subscription ID)
        # Only GET requests to /api/v1/subscription/{id} are excluded
        if request.method == "GET" and clean_path.startswith("/api/v1/subscription/sub_"):
            is_excluded = True

        if is_excluded:
            return await call_next(request)

        # 4. Require Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401, 
                content={"detail": "Missing Authorization header"}
            )

        # Extract token
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401, 
                content={"detail": "Invalid Authorization header format"}
            )

        token = auth_header.replace("Bearer ", "").strip()

        try:
            # Verify token using custom auth service
            user_data = self.auth_service.verify_token(token)
            
            # Add user data to request state
            request.state.user = user_data

        except ValueError as e:
            logger.error(f"Authentication failed: {str(e)}")
            return JSONResponse(
                status_code=401, 
                content={"detail": str(e)}
            )
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return JSONResponse(
                status_code=401, 
                content={"detail": "Invalid authentication token"}
            )

        return await call_next(request)