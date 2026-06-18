"""
Updated Dashboard Router to use MySQL service layer.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import json

# Import MySQL services
from services.mysql_service import dashboard_service, user_service
from services.auth_service import get_current_user
from middleware.role_required import ensure_permission
from utils_others.logger import logger

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_from_request(request: Request):
    """Get user from request state."""
    return getattr(request.state, "user", None)

# ============================================================
# DASHBOARD SUMMARY ENDPOINTS
# ============================================================

@router.get("/summary")
async def get_dashboard_summary(request: Request):
    """Get dashboard summary for user."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        return {"ok": True, "data": summary}
    
    except Exception as e:
        logger.error(f"Get dashboard summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# RECRUITER DASHBOARD ENDPOINTS
# ============================================================

@router.get("/recruiter/stats")
async def get_recruiter_stats(request: Request):
    """Get recruiter statistics."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        if summary.get("role") != "recruiter":
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {"ok": True, "data": summary.get("stats", {})}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get recruiter stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recruiter/jobs")
async def get_recruiter_jobs(request: Request, page: int = 1, page_size: int = 20):
    """Get recruiter's jobs."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        if summary.get("role") != "recruiter":
            raise HTTPException(status_code=403, detail="Access denied")
        
        jobs = summary.get("jobs", [])
        
        # Simple pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_jobs = jobs[start:end]
        
        return {
            "ok": True, 
            "data": {
                "jobs": paginated_jobs,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(jobs)
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get recruiter jobs failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recruiter/applications")
async def get_recruiter_applications(request: Request, page: int = 1, page_size: int = 20):
    """Get recruiter's applications."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        if summary.get("role") != "recruiter":
            raise HTTPException(status_code=403, detail="Access denied")
        
        applications = summary.get("applications", [])
        
        # Simple pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_apps = applications[start:end]
        
        return {
            "ok": True,
            "data": {
                "applications": paginated_apps,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(applications)
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get recruiter applications failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# CANDIDATE DASHBOARD ENDPOINTS
# ============================================================

@router.get("/candidate/stats")
async def get_candidate_stats(request: Request):
    """Get candidate statistics."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        if summary.get("role") != "candidate":
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {"ok": True, "data": summary.get("stats", {})}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get candidate stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidate/applications")
async def get_candidate_applications(request: Request, page: int = 1, page_size: int = 20):
    """Get candidate's applications."""
    ensure_permission(request, "dashboard:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        if summary.get("role") != "candidate":
            raise HTTPException(status_code=403, detail="Access denied")
        
        applications = summary.get("applications", [])
        
        # Simple pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_apps = applications[start:end]
        
        return {
            "ok": True,
            "data": {
                "applications": paginated_apps,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(applications)
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get candidate applications failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# PUBLIC DASHBOARD ENDPOINTS
# ============================================================

# TRULY PUBLIC JOBS ENDPOINT (NO AUTH REQUIRED)
# ============================================================
@router.get("/jobs")
async def get_public_jobs_no_auth(request: Request, search: Optional[str] = None, page: int = 1, page_size: int = 20):
    """Get public jobs without authentication requirement."""
    try:
        logger.info(f"Fetching public jobs - search: {search}, page: {page}, page_size: {page_size}")
        jobs = dashboard_service.list_public_jobs(search)
        logger.info(f"Successfully fetched {len(jobs)} jobs")
        
        # Simple pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_jobs = jobs[start:end]
        
        return {
            "ok": True,
            "data": {
                "jobs": paginated_jobs,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": len(jobs)
                }
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Get public jobs failed: {str(e)}\n{traceback.format_exc()}")
        # Return empty jobs array instead of error to prevent page from breaking
        return {
            "ok": True,
            "data": {
                "jobs": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": 0
                }
            }
        }

@router.get("/jobs/{job_id}")
async def get_public_job_details(request: Request, job_id: str):
    """Get public job details."""
    logger.info(f"get_public_job_details called for job_id: {job_id}")
    try:
        job = dashboard_service.get_public_job(job_id)
        logger.info(f"get_public_job returned: {job.keys() if job else 'None'}")
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"ok": True, "data": job}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get public job details failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# USER PROFILE ENDPOINTS
# ============================================================

@router.get("/profile")
async def get_user_profile(request: Request):
    """Get user profile information."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        user_info = user_service.get_user(user["id"])
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"ok": True, "data": user_info}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ANALYTICS ENDPOINTS
# ============================================================

@router.get("/analytics/overview")
async def get_analytics_overview(request: Request):
    """Get analytics overview."""
    ensure_permission(request, "analytics:read")
    user = get_user_from_request(request)
    
    try:
        summary = dashboard_service.get_summary(user["id"])
        
        # Return basic analytics based on role
        if summary.get("role") == "recruiter":
            stats = summary.get("stats", {})
            return {
                "ok": True,
                "data": {
                    "total_jobs": stats.get("total_jobs", 0),
                    "active_jobs": stats.get("active_jobs", 0),
                    "total_applications": stats.get("total_applications", 0),
                    "shortlisted": stats.get("shortlisted", 0),
                    "interviews": stats.get("interviews", 0),
                    "hired": stats.get("hired", 0)
                }
            }
        elif summary.get("role") == "candidate":
            stats = summary.get("stats", {})
            return {
                "ok": True,
                "data": {
                    "total_applications": stats.get("total_applications", 0),
                    "shortlisted": stats.get("shortlisted", 0),
                    "interviews": stats.get("interviews", 0),
                    "hired": stats.get("hired", 0)
                }
            }
        else:
            return {"ok": True, "data": {}}
    
    except Exception as e:
        logger.error(f"Get analytics overview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
