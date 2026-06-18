"""
Updated Recruiter Router to use MySQL service layer.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends
from typing import Optional, List
import json
import os
from datetime import datetime

# Import MySQL services
from services.mysql_service import user_service, candidate_service
from services.recruiter_service_mysql import RecruiterService
from services.jd_matching_service import jd_matching_service
from services.auth_service import get_current_user
from middleware.role_required import ensure_permission
from models.recruiter_models import CompanyCreate, RecruiterProfileCreate, JobCreateRequest, JobUpdateRequest
from utils_others.logger import logger
from config import PROFILE_IMAGE_UPLOAD_PATH, PROFILE_IMAGE_PUBLIC_URL

# Create recruiter service instance
recruiter_service = RecruiterService()

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_from_request(request: Request):
    """Get user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        return None
    
    # Handle JWT token structure where user ID is in 'sub' field
    if "sub" in user and "id" not in user:
        user["id"] = user["sub"]
    
    return user

def handle_file_upload(file: UploadFile, upload_path: str, public_url_base: str) -> str:
    if not file:
        return None
    try:
        from services.r2_service import R2Service
        r2_service = R2Service()
        
        # Reset file pointer to beginning
        file.file.seek(0)
        
        if "profilepics" in upload_path or "profile-images" in upload_path:
            folder = "profilepics"
        elif "company" in upload_path or "logos" in upload_path:
            folder = "profilepics"
        else:
            folder = "uploads"
        
        # Read file content
        file_content = file.file.read()
        
        # Upload to R2
        public_url = r2_service.upload_file(file_content, file.filename, folder)
        
        return public_url
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# ============================================================
# COMPANY ENDPOINTS
# ============================================================

@router.get("/companies")
async def list_companies(request: Request):
    """List all companies."""
    ensure_permission(request, "companies:read")
    
    try:
        companies = recruiter_service.list_companies()
        return {"ok": True, "data": companies}
    
    except Exception as e:
        logger.error(f"List companies failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/companies")
async def create_company(request: Request, company_data: CompanyCreate):
    """Create a new company."""
    ensure_permission(request, "companies:create")
    user = get_user_from_request(request)
    
    try:
        data = company_data.model_dump()
        data["created_by"] = user["id"]
        
        result = recruiter_service.create_company(**data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Create company failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# RECRUITER PROFILE ENDPOINTS
# ============================================================

@router.get("/profile")
async def get_profile(request: Request):
    """Get recruiter profile."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        profile = recruiter_service.get_profile(user["id"])
        
        # If the user has not yet created a profile, do not auto-create a placeholder company.
        # This prevents the UI from showing "Unknown Company" or generating a company display ID
        # before the recruiter has actually completed onboarding.
        if not profile:
            return {"ok": True, "data": {}}
        
        return {"ok": True, "data": profile}
    
    except Exception as e:
        logger.error(f"Get recruiter profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile")
async def update_profile(request: Request, profile_data: dict):
    """Update recruiter profile."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        profile_data["user_id"] = user["id"]
        result = recruiter_service.upsert_profile(profile_data)
        return {"ok": True, "data": result}
    
    except ValueError as e:
        # Validation errors (e.g., missing company name) should be surfaced as 400
        logger.warning(f"Update recruiter profile validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update recruiter profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile")
async def update_profile_post(request: Request, profile_data: dict):
    """Update recruiter profile (POST endpoint for compatibility)."""
    return await update_profile(request, profile_data)

@router.post("/profile/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    """Upload recruiter avatar."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Upload file
        avatar_url = handle_file_upload(
            file,
            PROFILE_IMAGE_UPLOAD_PATH,
            PROFILE_IMAGE_PUBLIC_URL
        )
        
        # Update profile
        recruiter_service.upsert_profile({"user_id": user["id"], "avatar_url": avatar_url})
        
        return {"ok": True, "data": {"avatar_url": avatar_url}}
    
    except Exception as e:
        logger.error(f"Recruiter avatar upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/company-logo")
async def upload_company_logo(request: Request, file: UploadFile = File(...)):
    """Upload company logo."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Upload file
        logo_url = handle_file_upload(
            file,
            PROFILE_IMAGE_UPLOAD_PATH,
            PROFILE_IMAGE_PUBLIC_URL
        )
        
        # Update company logo only (doesn't require company name for existing companies)
        recruiter_service.update_company_logo(user["id"], logo_url)
        
        return {"ok": True, "data": {"avatar_url": logo_url}}
    
    except ValueError as e:
        # Validation errors should be surfaced as 400 for cleaner frontend handling.
        logger.warning(f"Company logo upload validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Company logo upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/profile/company-logo")
async def upload_company_logo_options(request: Request):
    """Handle OPTIONS preflight for company logo upload."""
    return {"ok": True}

# ============================================================
# JOB ENDPOINTS
# ============================================================

@router.post("/jobs")
async def create_job(request: Request, job_data: JobCreateRequest):
    """Create a new job posting."""
    ensure_permission(request, "jobs:create")
    user = get_user_from_request(request)
    
    try:
        # Fetch profile to get the company_id
        profile = recruiter_service.get_profile(user["id"])

        if not profile or not profile.get("company_id"):
            # Require profile completion before allowing job creation.
            raise HTTPException(status_code=400, detail="Please complete your recruiter profile before posting jobs.")

        data = job_data.model_dump()
        data["created_by"] = user["id"]
        data["company_id"] = profile.get("company_id")
        
        result = recruiter_service.post_job(data)
        return {"ok": True, "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = f"Create job failed: {str(e)}\n{traceback.format_exc()}"
        print(error_details)  # This will show in console
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/jobs")
async def list_jobs(request: Request, page: int = 1, page_size: int = 20):
    """List jobs posted by recruiter."""
    ensure_permission(request, "jobs:read")
    user = get_user_from_request(request)
    
    try:
        result = recruiter_service.list_jobs(user["id"], page, page_size)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"List jobs failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str):
    """Get job details."""
    ensure_permission(request, "jobs:read")
    user = get_user_from_request(request)
    
    try:
        job = recruiter_service.get_job(job_id, user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"ok": True, "data": job}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/jobs/{job_id}")
async def update_job(request: Request, job_id: str, job_data: JobUpdateRequest):
    """Update job posting."""
    ensure_permission(request, "jobs:update")
    user = get_user_from_request(request)
    
    try:
        data = job_data.model_dump(exclude_unset=True)
        logger.info(f"Job update data received: {data}")
        result = recruiter_service.update_job(job_id, data, user["id"])
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"ok": True, "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update job failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
async def delete_job(request: Request, job_id: str):
    """Delete job posting."""
    ensure_permission(request, "jobs:delete")
    user = get_user_from_request(request)
    
    try:
        result = recruiter_service.delete_job(job_id, user["id"])
        
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"ok": True, "message": "Job deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete job failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# APPLICATION ENDPOINTS
# ============================================================

@router.get("/applications")
async def get_applications(request: Request, job_id: Optional[str] = None):
    """Get applications for recruiter's jobs."""
    ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        applications = recruiter_service.get_recruiter_applications(user["id"], job_id)
        return {"ok": True, "data": applications}
    
    except Exception as e:
        logger.error(f"Get applications failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{application_id}")
async def get_application_details(request: Request, application_id: str):
    """Get detailed application information including video analysis."""
    ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        # Get basic application details using existing method
        app_data = recruiter_service.get_application_by_id(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")
        
        logger.info(f"Raw app_data structure: {app_data}")
        
        # Extract the nested data into a flat structure for frontend compatibility
        application = app_data.get("application", {})
        job = app_data.get("job", {})
        candidate_data = app_data.get("candidate", {})
        
        logger.info(f"Application keys: {list(application.keys()) if application else 'None'}")
        logger.info(f"Job keys: {list(job.keys()) if job else 'None'}")
        logger.info(f"Candidate data keys: {list(candidate_data.keys()) if candidate_data else 'None'}")
        
        # Handle the nested candidate profile structure
        profile = candidate_data.get("profile", {})
        logger.info(f"Profile keys: {list(profile.keys()) if profile else 'None'}")
        logger.info(f"Candidate name from profile: {profile.get('full_name', '')}")
        logger.info(f"Candidate email from profile: {profile.get('email', '')}")
        
        # Profile should now have combined data from both users and candidate_profiles tables
        if not profile or not profile.get("email"):
            logger.warning("Profile is missing or email is still missing after combining tables")
        else:
            logger.info("Profile has required fields from combined tables")
        
        # Flatten the data structure
        flat_application = {
            **application,
            "job_title": job.get("job_title", ""),
            "job_location": job.get("location", ""),
            "job_type": job.get("job_type", ""),
            "candidate_name": (
                profile.get("full_name", "") or 
                f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or
                profile.get("candidate_display_id", "") or
                "Unknown Candidate"
            ),
            "candidate_email": profile.get("email", "") or "No email available",
            "candidate_phone": profile.get("phone", ""),
            "candidate_display_id": profile.get("candidate_display_id", ""),
            "candidate_summary": profile.get("summary", ""),
            "intro_video_url": candidate_data.get("intro_video_url", ""),
            "skills": profile.get("skills", []),
            "linkedin": profile.get("linkedin_url", ""),
            "resume_url": candidate_data.get("resume_url", "") or application.get("resume_url", ""),
            "cover_letter": application.get("cover_letter", ""),
            "interview_responses": application.get("interview_responses", []),
            "interview_video_urls": application.get("interview_video_urls", [])
        }
        
        logger.info(f"Available profile fields for name: full_name={profile.get('full_name')}, first_name={profile.get('first_name')}, last_name={profile.get('last_name')}, candidate_display_id={profile.get('candidate_display_id')}")
        logger.info(f"Available profile fields for email: email={profile.get('email')}")
        
        logger.info(f"Final flat_application keys: {list(flat_application.keys())}")
        logger.info(f"Final candidate_name: '{flat_application.get('candidate_name')}'")
        logger.info(f"Final job_title: '{flat_application.get('job_title')}'")
        
        # Get video analysis data if intro video exists
        analysis_data = None
        if flat_application.get("intro_video_url"):
            from services.video_analysis_service import VideoAnalysisService
            video_analysis_svc = VideoAnalysisService()
            candidate_id = flat_application.get("candidate_id") or application.get("candidate_id")
            
            # Get existing analysis for intro video
            analysis_data = video_analysis_svc.get_analysis(
                candidate_id, 
                video_url=flat_application.get("intro_video_url")
            )
        
        # Get video response analyses if they exist
        response_analyses = []
        try:
            from services.mysql_service import MySQLService
            mysql = MySQLService()
            
            # Get video responses for this application
            video_responses = mysql.get_records("video_responses", {"application_id": application_id}, order_by="question_index ASC")
            
            for vr in video_responses:
                video_url = vr.get("video_url")
                if video_url:
                    from services.video_analysis_service import VideoAnalysisService
                    video_analysis_svc = VideoAnalysisService()
                    analysis = video_analysis_svc.get_analysis(flat_application.get("candidate_id") or application.get("candidate_id"), video_url=video_url)
                    
                    response_analyses.append({
                        "question_index": vr.get("question_index"),
                        "question": vr.get("question"),
                        "video_url": video_url,
                        "analysis": analysis
                    })
        except Exception as e:
            logger.warning(f"Failed to load response analyses: {str(e)}")
        
        # Combine all data
        result = {
            **flat_application,
            "video_analysis": analysis_data,
            "response_analyses": response_analyses
        }
        
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Get application details failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/applications/{application_id}/status")
async def update_application_status(request: Request, application_id: str, status_data: dict):
    """Update application status."""
    ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        # Extract status and optional data from request body
        new_status = status_data.get("status")
        questions = status_data.get("questions", [])
        feedback = status_data.get("rejection_reason") or status_data.get("comment") or status_data.get("feedback")
        
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        # Update the application status in the database
        success = recruiter_service.update_application_status(application_id, new_status, questions, feedback)
        
        if success:
            # ✅ NOTIFICATIONS: Notify candidate about status update
            try:
                from services.notification_service_mysql import NotificationService
                notification_service = NotificationService()
                
                # Get application details to notify candidate
                application = recruiter_service.get_application_details(application_id)
                if application:
                    candidate_id = application.get("candidate_id")
                    job_id = application.get("job_id")
                    job_title = application.get("job_title", "a position")
                    
                    # Create user-friendly status message
                    status_messages = {
                        "submitted": "received",
                        "reviewed": "reviewed", 
                        "shortlisted": "shortlisted",
                        "interviewing": "selected for interview",
                        "interview_submitted": "interview completed",
                        "responses_submitted": "responses submitted",
                        "analysis_ready": "analysis ready",
                        "hired": "hired! 🎉",
                        "rejected": "not selected"
                    }
                    
                    status_display = status_messages.get(new_status, new_status)
                    
                    # Notify candidate with full metadata for navigation
                    notification_service.create_notification({
                        "created_by": candidate_id,
                        "title": "Application Status Updated",
                        "message": f"Your application for {job_title} has been {status_display}",
                        "category": "application_status",
                        "related_id": application_id,
                        "metadata": {
                            "type": "status_update",
                            "application_id": application_id,
                            "job_id": job_id,
                            "job_title": job_title,
                            "status": new_status
                        }
                    })
                    
                    # Special handling for interview scheduling
                    if new_status == "interviewing":
                        # Create additional interview notification with full metadata
                        notification_service.create_notification({
                            "created_by": candidate_id,
                            "title": "Video Interview Scheduled",
                            "message": f"You have been invited for a video interview for {job_title}. Click to start your interview.",
                            "category": "interview",
                            "related_id": application_id,
                            "metadata": {
                                "type": "interview_invitation",
                                "application_id": application_id,
                                "job_id": job_id,
                                "job_title": job_title
                            }
                        })
                        logger.info(f"Interview notification sent to candidate {candidate_id}")
                    
                    logger.info(f"Status update notification sent to candidate {candidate_id}: {new_status}")
                    
            except Exception as notif_error:
                logger.error(f"Failed to create status update notification: {str(notif_error)}")
                # Continue without failing the main process
            
            return {"ok": True, "message": "Application status updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Application not found or update failed")
    
    except Exception as e:
        logger.error(f"Update application status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# CANDIDATE ENDPOINTS
# ============================================================

@router.get("/candidates/{candidate_id}")
async def get_candidate_details(request: Request, candidate_id: str):
    """Get candidate details for recruiter."""
    ensure_permission(request, "candidates:read")
    
    try:
        # Get candidate profile
        profile = candidate_service.get_profile(candidate_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Get user info
        user_info = user_service.get_user(candidate_id)
        
        return {"ok": True, "data": {"profile": profile, "user": user_info}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get candidate details failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# JOB SKILLS ENDPOINTS
# ============================================================

@router.post("/jobs/{job_id}/skills")
async def add_job_skill(request: Request, job_id: str, skill_data: dict):
    """Add a skill to a job posting."""
    ensure_permission(request, "jobs:update")
    user = get_user_from_request(request)
    
    try:
        # Verify job belongs to recruiter
        job = recruiter_service.get_job(job_id, user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        payload = {
            "job_id": job_id,
            "skill_name": skill_data.get("skill_name")
        }
        
        result = recruiter_service.add_job_skill(payload)
        return {"ok": True, "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add job skill failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/skills")
async def list_job_skills(request: Request, job_id: str):
    """List all skills for a job posting."""
    ensure_permission(request, "jobs:read")
    
    try:
        skills = recruiter_service.list_job_skills(job_id)
        return {"ok": True, "data": skills}
    
    except Exception as e:
        logger.error(f"List job skills failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}/skills/{skill_id}")
async def delete_job_skill(request: Request, job_id: str, skill_id: str):
    """Delete a skill from a job posting."""
    ensure_permission(request, "jobs:update")
    user = get_user_from_request(request)
    
    try:
        # Verify job belongs to recruiter
        job = recruiter_service.get_job(job_id, user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        recruiter_service.delete_job_skill(skill_id)
        return {"ok": True, "message": "Skill deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete job skill failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# INTERVIEW QUESTIONS ENDPOINTS
# ============================================================

@router.post("/jobs/{job_id}/questions")
async def add_interview_question(request: Request, job_id: str, question_data: dict):
    """Add an interview question to a job posting."""
    ensure_permission(request, "jobs:update")
    user = get_user_from_request(request)
    
    try:
        # Verify job belongs to recruiter
        job = recruiter_service.get_job(job_id, user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        payload = {
            "job_id": job_id,
            "question": question_data.get("question"),
            "question_order": question_data.get("question_order", 0),
            "time_limit": question_data.get("time_limit", 120)
        }
        
        result = recruiter_service.add_interview_question(payload)
        return {"ok": True, "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add interview question failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/questions")
async def list_interview_questions(request: Request, job_id: str):
    """List all interview questions for a job posting."""
    ensure_permission(request, "jobs:read")
    
    try:
        questions = recruiter_service.list_interview_questions(job_id)
        return {"ok": True, "data": questions}
    
    except Exception as e:
        logger.error(f"List interview questions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}/questions/{question_id}")
async def delete_interview_question(request: Request, job_id: str, question_id: str):
    """Delete an interview question from a job posting."""
    ensure_permission(request, "jobs:update")
    user = get_user_from_request(request)
    
    try:
        # Verify job belongs to recruiter
        job = recruiter_service.get_job(job_id, user["id"])
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        recruiter_service.delete_interview_question(question_id)
        return {"ok": True, "message": "Question deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete interview question failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AI CANDIDATE SCORING ENDPOINTS
# ============================================================

@router.get("/jobs/{job_id}/top-candidates")
async def get_top_candidates(request: Request, job_id: str, top_n: int = 10):
    """Get AI-scored top candidates for a job. Uses deepseek-r1 for batch ranking."""
    ensure_permission(request, "jobs:read")
    try:
        result = jd_matching_service.get_top_candidates_for_job(job_id, top_n)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"ok": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Top candidates failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications/{application_id}/ai-score")
async def get_application_ai_score(request: Request, application_id: str):
    """Get AI score for a single application. Uses llama3 for balanced evaluation."""
    ensure_permission(request, "applications:read")
    try:
        result = jd_matching_service.score_single_application(application_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"ok": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI score failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PROFILE INSIGHTS ENDPOINTS
# ============================================================

@router.get("/profile/specializations")
async def get_hiring_specializations(request: Request):
    """Get hiring specializations based on recruiter's job postings."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        # Get all jobs posted by this recruiter
        jobs_result = recruiter_service.list_jobs(user["id"], page=1, page_size=100)
        jobs = jobs_result.get("jobs", [])
        
        if not jobs:
            return {"ok": True, "data": {"specializations": [], "message": "Post jobs to see your hiring specializations"}}
        
        # Extract specializations from job data
        specializations_set = set()
        
        for job in jobs:
            # Add department if present
            if job.get("department"):
                specializations_set.add(job["department"])
            
            # Add role if present
            if job.get("role"):
                specializations_set.add(job["role"])
            
            # Add industry if present
            if job.get("industry"):
                specializations_set.add(job["industry"])
            
            # Parse skills and add them
            skills_str = job.get("skills")
            if skills_str:
                try:
                    skills = json.loads(skills_str) if isinstance(skills_str, str) else skills_str
                    if isinstance(skills, list):
                        for skill in skills:
                            if skill:
                                specializations_set.add(skill)
                except:
                    pass
            
            # Extract from job title
            job_title = job.get("job_title", "")
            if job_title:
                # Common job title keywords
                keywords = ["Engineer", "Developer", "Manager", "Designer", "Analyst", "Specialist", 
                           "Consultant", "Director", "Lead", "Senior", "Junior", "Architect",
                           "Scientist", "Coordinator", "Assistant", "Head", "Chief"]
                for keyword in keywords:
                    if keyword in job_title:
                        specializations_set.add(keyword)
        
        # Convert to sorted list and limit to top 10
        specializations = sorted(list(specializations_set))[:10]
        
        return {"ok": True, "data": {"specializations": specializations}}
    
    except Exception as e:
        logger.error(f"Get hiring specializations failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/achievements")
async def get_achievements(request: Request):
    """Get achievements based on recruiter's actual activity."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        achievements = []
        
        # Get jobs count
        jobs_result = recruiter_service.list_jobs(user["id"], page=1, page_size=100)
        jobs = jobs_result.get("jobs", [])
        jobs_count = len(jobs)
        
        # Get applications
        applications = recruiter_service.get_recruiter_applications(user["id"])
        applications_count = len(applications)
        
        # Count hired candidates
        hired_count = len([app for app in applications if (app.get("status") or "").lower() == "hired"])
        
        # Get analysis reports count
        try:
            from services.mysql_service import MySQLService
            mysql = MySQLService()
            analysis_tasks = mysql.get_records("analysis_tasks", {"created_by": user["id"]})
            completed_analysis = len([t for t in (analysis_tasks or []) if t.get("status") == "completed"])
        except:
            completed_analysis = 0
        
        # Generate achievements based on actual activity
        if jobs_count >= 1:
            achievements.append({
                "title": "First Job Posted",
                "description": f"Posted your first job listing",
                "icon": "fa-star",
                "color": "#d97706",
                "bg_color": "#fef3c7"
            })
        
        if jobs_count >= 5:
            achievements.append({
                "title": "Active Recruiter",
                "description": f"Posted {jobs_count} job listings",
                "icon": "fa-briefcase",
                "color": "#2563eb",
                "bg_color": "#dbeafe"
            })
        
        if applications_count >= 10:
            achievements.append({
                "title": "Talent Scout",
                "description": f"Received {applications_count}+ applications",
                "icon": "fa-users",
                "color": "#16a34a",
                "bg_color": "#dcfce7"
            })
        
        if applications_count >= 50:
            achievements.append({
                "title": "Talent Magnet",
                "description": f"Received {applications_count}+ applications",
                "icon": "fa-magnet",
                "color": "#7c3aed",
                "bg_color": "#f3e8ff"
            })
        
        if hired_count >= 1:
            achievements.append({
                "title": "First Hire",
                "description": "Hired your first candidate",
                "icon": "fa-user-check",
                "color": "#2563eb",
                "bg_color": "#dbeafe"
            })
        
        if hired_count >= 5:
            achievements.append({
                "title": "Hiring Expert",
                "description": f"Hired {hired_count} candidates",
                "icon": "fa-trophy",
                "color": "#dc2626",
                "bg_color": "#fee2e2"
            })
        
        if completed_analysis >= 1:
            achievements.append({
                "title": "Analysis Pioneer",
                "description": "Completed your first video analysis",
                "icon": "fa-brain",
                "color": "#9333ea",
                "bg_color": "#f3e8ff"
            })
        
        if completed_analysis >= 5:
            achievements.append({
                "title": "Analysis Expert",
                "description": f"Completed {completed_analysis} video analyses",
                "icon": "fa-chart-line",
                "color": "#0891b2",
                "bg_color": "#cffafe"
            })
        
        # If no achievements yet, show a welcome message
        if not achievements:
            achievements.append({
                "title": "Welcome Aboard",
                "description": "Start posting jobs to unlock achievements",
                "icon": "fa-rocket",
                "color": "#6366f1",
                "bg_color": "#e0e7ff"
            })
        
        return {"ok": True, "data": {"achievements": achievements}}
    
    except Exception as e:
        logger.error(f"Get achievements failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/activity")
async def get_recent_activity(request: Request, limit: int = 5):
    """Get recent activity for the recruiter."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        activities = []
        
        # Get recent jobs
        jobs_result = recruiter_service.list_jobs(user["id"], page=1, page_size=10)
        jobs = jobs_result.get("jobs", [])
        
        for job in jobs[:limit]:
            activities.append({
                "type": "job_posted",
                "title": f"Posted a new job: {job.get('job_title', 'Unknown')}",
                "description": f"Location: {job.get('location', 'Not specified')}",
                "icon": "fa-briefcase",
                "color": "#2563eb",
                "bg_color": "#dbeafe",
                "created_at": job.get("created_at")
            })
        
        # Get recent applications
        applications = recruiter_service.get_recruiter_applications(user["id"])
        
        # Group applications by job and count recent ones
        recent_apps = applications[:limit]
        for app in recent_apps:
            activities.append({
                "type": "application_received",
                "title": f"Received application from {app.get('candidate_name', 'Unknown Candidate')}",
                "description": f"For position: {app.get('job_title', 'Unknown')}",
                "icon": "fa-user-plus",
                "color": "#16a34a",
                "bg_color": "#dcfce7",
                "created_at": app.get("applied_at")
            })
        
        # Get recent analysis tasks
        try:
            from services.mysql_service import MySQLService
            mysql = MySQLService()
            analysis_tasks = mysql.get_records("analysis_tasks", {"created_by": user["id"]}, order_by="created_at DESC", limit=limit)
            
            for task in (analysis_tasks or [])[:limit]:
                activities.append({
                    "type": "analysis_completed",
                    "title": f"Completed video analysis for candidate",
                    "description": f"Status: {task.get('status', 'Unknown')}",
                    "icon": "fa-brain",
                    "color": "#9333ea",
                    "bg_color": "#f3e8ff",
                    "created_at": task.get("created_at")
                })
        except:
            pass
        
        # Sort by created_at (most recent first)
        activities.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        # Format relative time
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        for activity in activities:
            created_at = activity.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        activity["time_ago"] = "Recently"
                        continue
                
                delta = now - created_at
                if delta.days > 0:
                    activity["time_ago"] = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
                elif delta.seconds >= 3600:
                    hours = delta.seconds // 3600
                    activity["time_ago"] = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif delta.seconds >= 60:
                    minutes = delta.seconds // 60
                    activity["time_ago"] = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    activity["time_ago"] = "Just now"
            else:
                activity["time_ago"] = "Recently"
        
        # Limit to top activities
        activities = activities[:limit]
        
        if not activities:
            activities.append({
                "type": "welcome",
                "title": "Welcome to Skreenit",
                "description": "Start posting jobs to see your activity",
                "icon": "fa-rocket",
                "color": "#6366f1",
                "bg_color": "#e0e7ff",
                "time_ago": "Now"
            })

        return {"ok": True, "data": {"activities": activities}}

    except Exception as e:
        logger.error(f"Get recent activity failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-resume-questions")
async def analyze_resume_questions(
    request: Request,
    resume: UploadFile = File(...)
):
    """
    Analyze a resume and generate interview questions with difficulty levels.
    Uses Ollama LLM to generate 5-10 questions from Easy to Hard.
    """
    try:
        user = get_user_from_request(request)
        user_id = user.get("id", "unknown") if user else "unknown"

        logger.info(f"Analyzing resume for questions: {resume.filename}, user: {user_id}")

        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_ext = os.path.splitext(resume.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Parse resume text
        resume_text = parse_resume_text(resume)

        if not resume_text or len(resume_text) < 50:
            logger.warning(f"Resume text too short or empty for {resume.filename}")
            # Return fallback questions
            fallback_questions = [
                {'question': 'Can you describe your professional background?', 'difficulty': 'Easy', 'category': 'Experience'},
                {'question': 'What are your key technical skills?', 'difficulty': 'Easy', 'category': 'Technical'},
                {'question': 'Tell me about a challenging project you worked on.', 'difficulty': 'Medium', 'category': 'Experience'},
                {'question': 'How do you approach problem-solving in your work?', 'difficulty': 'Medium', 'category': 'Problem-Solving'},
                {'question': 'Describe a situation where you had to learn a new technology quickly.', 'difficulty': 'Medium', 'category': 'Technical'},
                {'question': 'How would you handle a disagreement with a team member?', 'difficulty': 'Hard', 'category': 'Behavioral'},
                {'question': 'What is the most complex technical challenge you have solved?', 'difficulty': 'Hard', 'category': 'Technical'},
                {'question': 'How do you stay updated with industry trends and technologies?', 'difficulty': 'Hard', 'category': 'Professional Development'}
            ]
            return {
                "ok": True,
                "data": {
                    "questions": fallback_questions,
                    "source": "fallback",
                    "reason": "Resume text too short or could not be parsed"
                }
            }

        # Generate questions with difficulty using Ollama
        from services.ollama_service import ollama_service
        questions = ollama_service.generate_questions_with_difficulty(resume_text, num_questions=8)

        if questions:
            logger.info(f"Successfully generated {len(questions)} questions with difficulty levels")
            return {
                "ok": True,
                "data": {
                    "questions": questions,
                    "source": "ai",
                    "model": "ollama_service"
                }
            }
        else:
            # Fallback to default questions
            logger.warning("Ollama generation failed, using fallback questions")
            fallback_questions = [
                {'question': 'Can you describe your professional background?', 'difficulty': 'Easy', 'category': 'Experience'},
                {'question': 'What are your key technical skills?', 'difficulty': 'Easy', 'category': 'Technical'},
                {'question': 'Tell me about a challenging project you worked on.', 'difficulty': 'Medium', 'category': 'Experience'},
                {'question': 'How do you approach problem-solving in your work?', 'difficulty': 'Medium', 'category': 'Problem-Solving'},
                {'question': 'Describe a situation where you had to learn a new technology quickly.', 'difficulty': 'Medium', 'category': 'Technical'},
                {'question': 'How would you handle a disagreement with a team member?', 'difficulty': 'Hard', 'category': 'Behavioral'},
                {'question': 'What is the most complex technical challenge you have solved?', 'difficulty': 'Hard', 'category': 'Technical'},
                {'question': 'How do you stay updated with industry trends and technologies?', 'difficulty': 'Hard', 'category': 'Professional Development'}
            ]
            return {
                "ok": True,
                "data": {
                    "questions": fallback_questions,
                    "source": "fallback",
                    "reason": "AI generation unavailable"
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume question analysis failed: {str(e)}")
        # Return fallback on error
        fallback_questions = [
            {'question': 'Can you describe your professional background?', 'difficulty': 'Easy', 'category': 'Experience'},
            {'question': 'What are your key technical skills?', 'difficulty': 'Easy', 'category': 'Technical'},
            {'question': 'Tell me about a challenging project you worked on.', 'difficulty': 'Medium', 'category': 'Experience'},
            {'question': 'How do you approach problem-solving in your work?', 'difficulty': 'Medium', 'category': 'Problem-Solving'},
            {'question': 'Describe a situation where you had to learn a new technology quickly.', 'difficulty': 'Medium', 'category': 'Technical'},
            {'question': 'How would you handle a disagreement with a team member?', 'difficulty': 'Hard', 'category': 'Behavioral'},
            {'question': 'What is the most complex technical challenge you have solved?', 'difficulty': 'Hard', 'category': 'Technical'},
            {'question': 'How do you stay updated with industry trends and technologies?', 'difficulty': 'Hard', 'category': 'Professional Development'}
        ]
        return {
            "ok": True,
            "data": {
                "questions": fallback_questions,
                "source": "fallback",
                "reason": f"Error: {str(e)}"
            }
        }


def parse_resume_text(resume_file: UploadFile) -> str:
    """Parse text from uploaded resume file."""
    import tempfile
    import os

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume_file.filename)[1]) as temp_file:
            content = resume_file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Parse based on file type
            file_ext = os.path.splitext(resume_file.filename)[1].lower()

            if file_ext == '.pdf':
                from services.resume_parser import ResumeParser
                parser = ResumeParser()
                parsed = parser.parse_pdf(temp_file_path)
                return parsed.get('text', '') if parsed else ''
            elif file_ext in ['.docx', '.doc']:
                from services.resume_parser import ResumeParser
                parser = ResumeParser()
                parsed = parser.parse_docx(temp_file_path)
                return parsed.get('text', '') if parsed else ''
            else:
                return ''

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"Error parsing resume text: {str(e)}")
        return ''
