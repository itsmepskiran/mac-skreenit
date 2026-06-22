import os
import sys
from dotenv import load_dotenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR) # Add backend directory to sys.path
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi import FastAPI, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
import asyncio
import time
from jinja2 import Environment, FileSystemLoader
from utils_others.logger import logger
from utils_others.error_handler import register_exception_handlers

from middleware.security_headers import SecurityHeadersMiddleware
from middleware.auth_middleware import CustomAuthMiddleware, EXCLUDED_PATHS

from routers import (
    auth,
    applicant_new as applicant,
    recruiter_new as recruiter,
    dashboard_new as dashboard,
    analytics,
    video,
    notifications,
    locations,
    reference,
    screening,
    training_registration,
    resume_analysis,
    admin,
    subscription,
    premium_assessment
)

ENV = os.getenv("ENVIRONMENT", "development")
IS_PROD = ENV == "production"

# ---------------------------------------------------------
# Initialize FastAPI
# ---------------------------------------------------------
app = FastAPI(
    title="Skreenit API",
    description="Backend API for Skreenit recruitment platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 1. Define the Security Scheme (Bearer Token)
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # 2. Apply it globally to all endpoints
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ---------------------------------------------------------
# Setup Jinja2 Template Environment
# ---------------------------------------------------------
template_dir = os.path.join(BASE_DIR, "..", "assets", "templates")
if os.path.exists(template_dir):
    template_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True
    )
    print(f"[OK] Templates loaded from: {template_dir}")
else:
    print(f"[WARNING] Templates directory not found at {template_dir}")
    template_env = None

# ---------------------------------------------------------
# Mount Static Files (Logos & Assets)
# ---------------------------------------------------------
logos_dir = os.path.join(BASE_DIR, "logos")
if os.path.exists(logos_dir):
    app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")
    print(f"[OK] Mounted logos from: {logos_dir}")
else:
    print(f"[WARNING] Logos directory not found at {logos_dir}")

assets_dir = os.path.join(BASE_DIR, "..", "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    print(f"[OK] Mounted assets from: {assets_dir}")
else:
    print(f"[WARNING] Assets directory not found at {assets_dir}")

# Note: uploads_dir is kept just in case you still use it for temporary local processing 
# before pushing to R2. If not, this can be removed in the future too.
uploads_dir = os.path.join(BASE_DIR, "..", "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
    print(f"[OK] Mounted uploads from: {uploads_dir}")
else:
    print(f"[WARNING] Uploads directory not found at {uploads_dir}")


# ---------------------------------------------------------
# Browser Display (Root) - HEAD added for Health Checks
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def root_page():
    if not template_env:
        return HTMLResponse("""
        <html>
            <head><title>Skreenit Local Server API</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>Skreenit Local Server API</h2>
                <p>Running on Machine Xeon E-2276M + 64GB RAM + Quadro T2000</p>
            </body>
        </html>
        """)
    
    try:
        template = template_env.get_template("backend.html")
        context = {
            "jobsLink": "https://jobs.skreenit.com/jobs.html" if IS_PROD else "http://localhost:8080/jobs/jobs.html"
        }
        html_content = template.render(**context)
        return HTMLResponse(html_content)
        
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return HTMLResponse(f"""
        <html>
            <head><title>Skreenit Local Server API</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>Skreenit Local Server API</h2>
                <p>Running on Machine Xeon E-2276M + 64GB RAM + Quadro T2000</p>
                <p>Template Error: {str(e)}</p>
            </body>
        </html>
        """)

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
from typing import Optional

def _mask(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = str(v)
    return (v[:8] + "...") if len(v) > 12 else "***"

logger.info("Backend Startup", extra={
    "environment": ENV,
    "auth_system": "Custom JWT",
})

# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
async def health_root():
    print(f"[HEALTH_ENDPOINT] Request received!", flush=True)
    return {"status": "healthy", "version": "1.0.0", "environment": ENV}

# ---------------------------------------------------------
# Test Endpoint
# ---------------------------------------------------------
@app.get("/test")
async def test_root():
    print(f"[TEST_ENDPOINT] Request received!", flush=True)
    return {"status": "ok", "message": "Test endpoint reached"}

# ---------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------
# API Router
# ---------------------------------------------------------
api = APIRouter(prefix="/api/v1")
api.include_router(auth.router, tags=["Authentication"])
api.include_router(applicant.router, tags=["Applicant"])
api.include_router(recruiter.router, tags=["Recruiter"])
api.include_router(dashboard.router, tags=["Dashboard"])
api.include_router(analytics.router, tags=["Analytics"])
api.include_router(video.router, tags=["Video"])
api.include_router(notifications.router, tags=["Notifications"])
api.include_router(locations.router, tags=["Locations"])
api.include_router(reference.router, tags=["Reference"])
api.include_router(screening.router, tags=["Screening"])
api.include_router(training_registration.router, tags=["Training Registration"])
api.include_router(resume_analysis.router, tags=["Resume Analysis"])
api.include_router(admin.router, tags=["Admin"])
api.include_router(subscription.router, tags=["Subscription"])
api.include_router(premium_assessment.router, tags=["Premium Assessments"])

@api.get("/health")
async def versioned_health():
    return {"status": "healthy", "version": "1.0.0"}

app.include_router(api)

# ---------------------------------------------------------
# MIDDLEWARE SETUP (CRITICAL ORDER)
# ---------------------------------------------------------
class PatchedCustomAuthMiddleware(CustomAuthMiddleware): 
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        return await super().dispatch(request, call_next)

app.add_middleware(PatchedCustomAuthMiddleware, excluded_paths=EXCLUDED_PATHS)
app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------
# Timeout Middleware - Extended for heavy ML processing
# ---------------------------------------------------------
TIMEOUT_EXCLUDED_PATHS = {
    "/api/v1/analytics/bulk-analyze-responses",
    "/api/v1/analytics/analyze",
    "/api/v1/analytics/reanalyze",
    "/api/v1/analytics/analyze-video",
    "/api/v1/analytics/analyze-video-response",
}

class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = 120):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: StarletteRequest, call_next):
        path = request.url.path
        is_excluded = path in TIMEOUT_EXCLUDED_PATHS or path.startswith("/api/v1/analytics/reanalyze/")
        
        if is_excluded:
            logger.info(f"Timeout middleware: Skipping timeout for {path}")
            return await call_next(request)
        
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.url.path}")
            return JSONResponse(
                {"error": "Request timeout", "detail": f"Request took longer than {self.timeout} seconds"},
                status_code=408
            )

app.add_middleware(TimeoutMiddleware, timeout=120)

# ---------------------------------------------------------
# CORS Middleware - Configured for Local Server + Tunnel Bridge
# ---------------------------------------------------------
# Cloudflare Pages Frontend origins
FRONTEND_ORIGINS = [
    "https://www.skreenit.com",
    "https://skreenit.com",
    "https://login.skreenit.com",
    "https://auth.skreenit.com",
    "https://applicant.skreenit.com",
    "https://recruiter.skreenit.com",
    "https://dashboard.skreenit.com",
    "https://backend.skreenit.com",
    "https://assets.skreenit.com",
    "https://storage.skreenit.com",
    "https://support.skreenit.com",
    "https://in.skreenit.com",
    "https://legal.skreenit.com",
    "https://app.skreenit.com",
    "https://hrms.skreenit.com",
    "https://jobs.skreenit.com",
]

# Local development origins
LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
    "http://localhost:8083",
    "http://127.0.0.1:8083",
]

# Tunnel bridge origins - Allow all Cloudflare tunnel URLs
# The tunnel will bridge between local server and Cloudflare Pages
TUNNEL_ORIGINS = [
    "https://*.trycloudflare.com",  # Cloudflare tunnel URLs
    "https://api.skreenit.com",     # Your custom tunnel domain
    "https://skreenit-backend.pages.dev",  # Cloudflare Pages backend URL if used
]

# Combine all origins
origins = FRONTEND_ORIGINS + LOCAL_DEV_ORIGINS + TUNNEL_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# ---------------------------------------------------------
# Events
# ---------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("Backend Started")

    # Print platform-aware system information
    try:
        from services.platform_utils import print_system_info
        print_system_info()
    except Exception as e:
        logger.warning(f"Could not print system info: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend Stopped")

# ---------------------------------------------------------
# Server Startup
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)