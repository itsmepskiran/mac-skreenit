"""
Updated Applicant Router to use MySQL service layer.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends, Body
from typing import Optional, List
import uuid, time, os, json, tempfile, shutil
from datetime import datetime

# Resume parsing libraries
import fitz  # PyMuPDF for PDF parsing
from docx import Document  # python-docx for DOCX parsing

# Centralized Ollama service (handles all models + fallbacks)
from services.ollama_service import ollama_service
from services.jd_matching_service import jd_matching_service

# Import MySQL services
from services.mysql_service import candidate_service, video_service, user_service, dashboard_service, MySQLService
from services.recruiter_service_mysql import RecruiterService
from services.notification_service_mysql import NotificationService
from services.auth_service import get_current_user
from middleware.role_required import ensure_permission
from models.applicant_models import ApplicationCreate
from utils_others.logger import logger
from config import PROFILE_IMAGE_UPLOAD_PATH, PROFILE_IMAGE_PUBLIC_URL, RESUME_UPLOAD_PATH, RESUME_PUBLIC_URL, VIDEO_UPLOAD_PATH, VIDEO_PUBLIC_URL

# Initialize MySQL service
mysql_service = MySQLService()

router = APIRouter(prefix="/applicant", tags=["Applicant"])

# Create recruiter service instance
recruiter_service = RecruiterService()

# Create notification service instance
notification_service = NotificationService()

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
    
    # Ensure user has an id field
    if "id" not in user:
        logger.warning(f"User object missing 'id' field: {user.keys()}")
        return None
    
    return user

def handle_file_upload(file: UploadFile, upload_path: str, public_url_base: str) -> str:
    """Handle file upload to R2 storage."""
    if not file:
        return None
    
    try:
        # Import R2 service
        from services.r2_service import R2Service
        r2_service = R2Service()
        
        # Determine folder from upload_path
        if "profilepics" in upload_path or "profile-images" in upload_path:
            folder = "profilepics"
        elif "resumes" in upload_path:
            folder = "resumes"
        elif "videos" in upload_path:
            folder = "videos"
        else:
            folder = "uploads"
        
        # Reset file pointer to beginning (important for re-uploads/replacements)
        file.file.seek(0)
        
        # Read file content
        file_content = file.file.read()
        
        # Validate file content is not empty
        if not file_content or len(file_content) == 0:
            logger.error(f"Empty file content received for {file.filename}")
            raise HTTPException(status_code=400, detail="File is empty or not properly uploaded")
        
        logger.info(f"Uploading file: {file.filename}, size: {len(file_content)} bytes")
        
        # Upload to R2
        public_url = r2_service.upload_file(file_content, file.filename, folder)
        
        return public_url
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"R2 file upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")

# ============================================================
# PROFILE ENDPOINTS
# ============================================================

@router.get("/profile")
async def get_profile(request: Request):
    """Get candidate profile."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        profile = candidate_service.get_profile(user["sub"])
        if not profile:
            # Create empty profile if doesn't exist
            profile = candidate_service.upsert_profile(user["sub"], {})
        
        return {"ok": True, "data": profile}
    
    except Exception as e:
        logger.error(f"Get profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile")
async def update_profile_put(request: Request, profile_data: Optional[dict] = None, resume: Optional[UploadFile] = File(None), profile_image: Optional[UploadFile] = File(None), intro_video: Optional[UploadFile] = File(None)):
    """Update candidate profile (PUT method)."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Handle FormData (when files are uploaded)
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            form = await request.form()
            data = {}
            
            # Process form fields
            for key, value in form.items():
                if hasattr(value, 'filename'):  # Skip files - handle separately
                    continue
                # Convert string values to appropriate types
                if key in ['skills', 'experience', 'education']:
                    try:
                        data[key] = json.loads(value) if value else []
                    except (ValueError, AttributeError):
                        data[key] = []
                elif key == 'experience_years':
                    try:
                        data[key] = int(value) if value else None
                    except (ValueError, AttributeError):
                        data[key] = None
                else:
                    data[key] = value
            
            # Handle file uploads
            if resume and resume.filename:
                resume_url = handle_file_upload(
                    resume,
                    RESUME_UPLOAD_PATH,
                    RESUME_PUBLIC_URL
                )
                data["resume_url"] = resume_url

            if profile_image and profile_image.filename:
                image_url = handle_file_upload(
                    profile_image,
                    PROFILE_IMAGE_UPLOAD_PATH,
                    PROFILE_IMAGE_PUBLIC_URL
                )
                data["avatar_url"] = image_url

            if intro_video and intro_video.filename:
                video_url = handle_file_upload(
                    intro_video,
                    VIDEO_UPLOAD_PATH,
                    VIDEO_PUBLIC_URL
                )
                data["intro_video_url"] = video_url

            profile_data = data
        elif profile_data is None:
            profile_data = {}
        
        result = candidate_service.upsert_profile(user["sub"], profile_data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Update profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile")
async def update_profile(request: Request, profile_data: dict = Body(...)):
    """Update candidate profile (POST method - alias for compatibility)."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        result = candidate_service.upsert_profile(user["sub"], profile_data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Update profile failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/education")
async def save_education(request: Request, education_data: List[dict] = Body(...)):
    """Save candidate education."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        result = candidate_service.save_education(user["sub"], education_data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Save education failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/experience")
async def save_experience(request: Request, experience_data: List[dict] = Body(...)):
    """Save candidate experience."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        result = candidate_service.save_experience(user["sub"], experience_data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Save experience failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    """Upload profile avatar."""
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
        candidate_service.upsert_profile(user["sub"], {"avatar_url": avatar_url})
        
        return {"ok": True, "data": {"avatar_url": avatar_url}}
    
    except Exception as e:
        logger.error(f"Avatar upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profile/resume")
async def upload_resume(request: Request, file: UploadFile = File(...)):
    """Upload resume."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Upload file
        resume_url = handle_file_upload(
            file,
            RESUME_UPLOAD_PATH,
            RESUME_PUBLIC_URL
        )
        
        # Update profile
        candidate_service.upsert_profile(user["sub"], {"resume_url": resume_url})
        
        return {"ok": True, "data": {"resume_url": resume_url}}
    
    except Exception as e:
        logger.error(f"Resume upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# JOB APPLICATION ENDPOINTS
# ============================================================

@router.get("/check-status")
async def check_status(request: Request, job_id: str):
    """Check if candidate has applied for job."""
    ensure_permission(request, "applications:create")
    user = get_user_from_request(request)
    
    try:
        status = candidate_service.check_application_status(job_id, user["sub"])
        return {"ok": True, "data": status}
    
    except Exception as e:
        logger.error(f"Check status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply")
async def apply_for_job(request: Request, payload: ApplicationCreate):
    """Apply for a job with auto screening."""
    ensure_permission(request, "applications:create")
    user = get_user_from_request(request)
    
    try:
        # Prepare data
        data = payload.model_dump()
        data["candidate_id"] = user["sub"]
        
        result = candidate_service.submit_application(data)
        
        # Trigger auto screening after application submission
        try:
            job_id = data.get("job_id")
            application_id = result.get("id") or result.get("application_id") if result else None
            resume_url = data.get("resume_url")
            
            if job_id and resume_url:
                # Get job details and candidate profile for screening
                from services.mysql_service import MySQLService
                mysql_service = MySQLService()
                
                job_details = mysql_service.get_single_record("jobs", {"id": job_id})
                candidate_profile = mysql_service.get_single_record("candidate_profiles", {"user_id": user["sub"]})
                
                if job_details and candidate_profile:
                    # Prepare resume text from candidate profile
                    resume_text = candidate_profile.get("summary", "") or ""
                    if candidate_profile.get("skills"):
                        resume_text += f"\nSkills: {candidate_profile.get('skills')}"
                    if candidate_profile.get("experience"):
                        resume_text += f"\nExperience: {candidate_profile.get('experience')}"
                    if candidate_profile.get("education"):
                        resume_text += f"\nEducation: {candidate_profile.get('education')}"
                    
                    job_description = job_details.get("description", "") or ""
                    job_title = job_details.get("job_title", "")
                    
                    # Call screening analysis service
                    from services.resume_jd_analysis_service import ResumeJDAnalysisService
                    from database import CandidateAnalysisResult, ScreeningQuestion, generate_uuid, get_db_session
                    
                    analysis_service = ResumeJDAnalysisService()
                    analysis_result = analysis_service.analyze_application(
                        resume_text=resume_text,
                        job_description=job_description,
                        job_title=job_title,
                        candidate_info={"name": user.get("name"), "email": user.get("email")}
                    )
                    
                    # Store analysis result in database
                    with get_db_session() as db:
                        analysis_record = CandidateAnalysisResult(
                            id=generate_uuid(),
                            job_application_id=application_id,
                            job_id=job_id,
                            candidate_id=user["sub"],
                            match_score=analysis_result["match_score"],
                            skills_matched={"skills": analysis_result["skills_matched"]},
                            skills_missing={"skills": analysis_result["skills_missing"]},
                            experience_match=analysis_result["experience_match"],
                            education_match=analysis_result["education_match"],
                            overall_fit=analysis_result["overall_fit"],
                            recommendation=analysis_result["recommendation"],
                            threshold_met=analysis_result["threshold_met"],
                            analysis_metadata=analysis_result,
                            analyzed_at=datetime.utcnow()
                        )
                        db.add(analysis_record)
                        db.flush()
                        
                        # Store screening questions
                        for i, q in enumerate(analysis_result["screening_questions"]):
                            question_record = ScreeningQuestion(
                                id=generate_uuid(),
                                analysis_result_id=analysis_record.id,
                                job_id=job_id,
                                question=q["question"],
                                question_type=q["question_type"],
                                priority=q["priority"],
                                related_skill=q.get("related_skill"),
                                order_index=i,
                                is_active=True
                            )
                            db.add(question_record)
                        
                        db.commit()
                        logger.info(f"Auto screening completed for application {application_id}. Score: {analysis_result['match_score']}, Threshold met: {analysis_result['threshold_met']}")
                        
                        # Only notify recruiter if candidate passes auto screening threshold
                        if analysis_result["threshold_met"]:
                            notify_recruiter = True
                        else:
                            notify_recruiter = False
                            logger.info(f"Candidate {user['sub']} did not pass auto screening threshold for job {job_id}")
                else:
                    logger.warning(f"Could not fetch job details or candidate profile for auto screening")
                    notify_recruiter = True  # Fallback: notify recruiter if screening fails
            else:
                logger.warning(f"Missing job_id or resume_url for auto screening")
                notify_recruiter = True  # Fallback: notify recruiter if screening fails
                
        except Exception as screening_error:
            logger.error(f"Auto screening failed: {str(screening_error)}")
            notify_recruiter = True  # Fallback: notify recruiter if screening fails
        
        # ✅ NOTIFICATIONS: Create notifications for both recruiter and candidate
        try:
            notification_service = NotificationService()
            
            # Get job details to include in notifications
            job_id = data.get("job_id")
            application_id = result.get("id") or result.get("application_id") if result else None
            job_details = None
            try:
                # Get job details
                recruiter_service = RecruiterService()
                jobs_response = recruiter_service.list_jobs(user_id=None, page=1, page_size=1000)
                all_jobs = jobs_response.get("jobs", [])
                job_details = next((job for job in all_jobs if job.get("id") == job_id), None)
            except Exception as job_error:
                logger.warning(f"Could not fetch job details for notification: {str(job_error)}")
            
            # Get candidate name
            candidate_name = user.get("name") or user.get("email", "Unknown").split("@")[0]
            job_title = job_details.get("job_title", "a position") if job_details else "a position"
            recruiter_id = job_details.get("created_by") if job_details else None
            
            # 1. Notify recruiter about new application (only if passed auto screening or screening failed)
            if recruiter_id and notify_recruiter:
                notification_service.create_notification({
                    "created_by": recruiter_id,
                    "title": "New Application Received",
                    "message": f"New application from {candidate_name} for {job_title}",
                    "category": "application",
                    "related_id": application_id,
                    "metadata": {
                        "type": "new_application",
                        "application_id": application_id,
                        "job_id": job_id,
                        "candidate_id": user["sub"],
                        "candidate_name": candidate_name,
                        "job_title": job_title
                    }
                })
                logger.info(f"Notification sent to recruiter {recruiter_id} for new application")
            
            # 2. Notify candidate about application received
            notification_service.create_notification({
                "created_by": user["sub"],
                "title": "Application Submitted Successfully",
                "message": f"Your application for {job_title} has been received successfully!",
                "category": "application_received",
                "related_id": application_id,
                "metadata": {
                    "type": "application_received",
                    "application_id": application_id,
                    "job_id": job_id,
                    "job_title": job_title
                }
            })
            logger.info(f"Confirmation notification sent to candidate {user['sub']}")
            
        except Exception as notif_error:
            logger.error(f"Failed to create application notifications: {str(notif_error)}")
            # Continue without failing the main application process
        
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Job application failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications")
async def get_applications(request: Request):
    """Get candidate's applications."""
    ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        applications = candidate_service.get_candidate_applications(user["sub"])
        return {"ok": True, "data": applications}
    
    except Exception as e:
        logger.error(f"Get applications failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-connection")
async def test_connection():
    """Test endpoint for frontend-backend connectivity."""
    return {"message": "Backend connection successful!", "timestamp": "2025-03-10"}

@router.get("/test-interview")
async def test_interview():
    """Test endpoint for interview functionality."""
    return {
        "data": {
            "interview_questions": [
                "Tell me about yourself",
                "Why do you want this job?",
                "What are your strengths?"
            ],
            "job_title": "Test Job"
        }
    }

# ... (rest of the code remains the same)

@router.get("/applications/{application_id}/interview")
async def get_interview_questions(request: Request, application_id: str):
    """Get interview questions for a specific application."""
    # Temporarily remove auth requirement for debugging
    # ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        # Get application details
        application = mysql_service.get_single_record("job_applications", {"id": application_id})
        
        if application:
            # logger.info(f"Application data keys: {list(application.keys())}")
            # logger.info(f"Application data: {application}")
            
            # Check if this ID is actually a job_id, not application_id
            if "job_id" not in application and "candidate_id" not in application:
                # logger.warning(f"This might be a job_id, not application_id. Trying to get job details...")
                try:
                    # Try to get job details instead
                    job = recruiter_service.mysql.get_single_record("jobs", {"id": application_id})
                    if job:
                        # logger.info(f"Found job with ID {application_id}: {job.get('title', 'Unknown')}")
                        # Get all applications for this candidate for this job
                        candidate_applications = recruiter_service.mysql.get_records(
                            "job_applications", 
                            {"candidate_id": user["sub"], "job_id": application_id}
                        )
                        if candidate_applications:
                            application = candidate_applications[0]  # Use first found
                            # logger.info(f"Found candidate's application for this job: {application.get('id')}")
                        else:
                            # logger.warning(f"No application found for candidate {user['id']} and job {application_id}")
                            return {
                                "data": {
                                    "interview_questions": [
                                        "Tell me about yourself and your experience",
                                        "Why do you want to work for our company?",
                                        "What are your greatest strengths?",
                                        "Describe a challenging situation you've faced at work",
                                        "Where do you see yourself in 5 years?"
                                    ],
                                    "job_title": job.get("title", "Unknown Position"),
                                    "application_id": application_id,
                                    "candidate_id": user["sub"],
                                    "note": f"No application found for this candidate and job {application_id}"
                                }
                            }
                    else:
                        # logger.warning(f"No job found with ID {application_id}")
                        pass
                except Exception as e:
                    # logger.error(f"Error trying to get job details: {str(e)}")
                    pass
            
            # CRITICAL: Verify application ownership
            application_candidate_id = application.get("candidate_id")
            logged_in_candidate_id = user["sub"]
            # logger.info(f"Application candidate_id: {application_candidate_id}")
            # logger.info(f"Logged-in candidate_id: {logged_in_candidate_id}")
            
            if application_candidate_id != logged_in_candidate_id:
                # logger.error(f"SECURITY: User {logged_in_candidate_id} trying to access application {application_id} belonging to {application_candidate_id}")
                return {
                    "data": {
                        "interview_questions": [
                            "Tell me about yourself and your experience",
                            "Why do you want to work for our company?",
                            "What are your greatest strengths?",
                            "Describe a challenging situation you've faced at work",
                            "Where do you see yourself in 5 years?"
                        ],
                        "job_title": "Access Denied",
                        "application_id": application_id,
                        "candidate_id": "unauthorized",
                        "note": f"SECURITY: This application belongs to candidate {application_candidate_id}, not {logged_in_candidate_id}"
                    }
                }
            else:
                # Ownership check passed - candidate {application_candidate_id} == logged_in {logged_in_candidate_id}
                pass
        else:
            # logger.warning(f"Application is None or empty")
            pass
        if not application:
            # logger.warning(f"Application {application_id} not found, using mock data")
            return {
                "data": {
                    "interview_questions": [
                        "Tell me about yourself and your experience",
                        "Why do you want to work for our company?",
                        "What are your greatest strengths?",
                        "Describe a challenging situation you've faced at work",
                        "Where do you see yourself in 5 years?"
                    ],
                    "job_title": "Senior Developer Position",
                    "application_id": application_id,
                    "candidate_id": user["sub"],
                    "note": "Using mock data - application not found"
                }
            }
        
        # Get job_id from the application
        job_id = application.get("job_id")
        # logger.info(f"Job ID from application: {job_id}")
        
        # If no job_id found, try alternative field names
        if not job_id:
            job_id = application.get("jobid")  # Try lowercase
            # logger.info(f"Job ID from 'jobid' field: {job_id}")
        
        if not job_id:
            job_id = application.get("job")  # Try 'job' field
            # logger.info(f"Job ID from 'job' field: {job_id}")
        
        if not job_id and "job" in application and isinstance(application["job"], dict):
            job_id = application["job"].get("id")  # Try nested job object
            # logger.info(f"Job ID from nested job.id: {job_id}")
        
        if not job_id:
            # logger.warning(f"No job_id found in application {application_id}, using mock data")
            return {
                "data": {
                    "interview_questions": [
                        "Tell me about yourself and your experience",
                        "Why do you want to work for our company?",
                        "What are your greatest strengths?",
                        "Describe a challenging situation you've faced at work",
                        "Where do you see yourself in 5 years?"
                    ],
                    "job_title": "Unknown Position",
                    "application_id": application_id,
                    "candidate_id": user["sub"],
                    "note": "Using mock data - job_id not found"
                }
            }
        
        # Fetch interview questions from the database
        try:
            # logger.info(f"Fetching interview questions for application_id: {application_id}")
            
            # First check if the application has interview_questions in JSON field
            application_questions = application.get("interview_questions")
            
            if application_questions and len(application_questions) > 0:
                # logger.info(f"Found {len(application_questions)} interview questions in application JSON field")
                questions_list = application_questions
            else:
                # Fallback to the interview_questions table (for job-level questions)
                # logger.info(f"No questions in application, checking interview_questions table for job_id: {job_id}")
                interview_questions = recruiter_service.mysql.get_records(
                    "interview_questions", 
                    {"job_id": job_id},
                    order_by="question_order ASC"
                )
                
                # logger.info(f"Found {len(interview_questions)} interview questions in database")
                
                if not interview_questions:
                    # logger.warning(f"No interview questions found for job_id: {job_id}, using mock data")
                    return {
                        "data": {
                            "interview_questions": [
                                "Tell me about yourself and your experience",
                                "Why do you want to work for our company?",
                                "What are your greatest strengths?",
                                "Describe a challenging situation you've faced at work",
                                "Where do you see yourself in 5 years?"
                            ],
                            "job_title": "Unknown Position",
                            "application_id": application_id,
                            "candidate_id": user["sub"],
                            "note": f"Using mock data - no questions found for job_id: {job_id}"
                        }
                    }
                
                # Extract question text from the records
                questions_list = [q["question"] for q in interview_questions]
                # logger.info(f"Extracted questions: {questions_list}")
            
            # logger.info(f"Final questions list: {questions_list}")
            
            # logger.info(f"Loaded {len(questions_list)} real interview questions for job_id: {job_id}")
            
            # Get job details for display
            job_details = recruiter_service.mysql.get_single_record("jobs", {"id": job_id})
            
            # Get company details
            company_name = "Unknown Company"
            if job_details and job_details.get("company_id"):
                company = recruiter_service.mysql.get_single_record("companies", {"id": job_details["company_id"]})
                if company:
                    company_name = company.get("name", "Unknown Company")
            
            return {
                "data": {
                    "interview_questions": questions_list,
                    "job_title": job_details.get("job_title", "Unknown Position") if job_details else "Unknown Position",
                    "title": job_details.get("job_title", "Unknown Position") if job_details else "Unknown Position",
                    "company_name": company_name,
                    "location": job_details.get("location", "Not specified") if job_details else "Not specified",
                    "job_type": job_details.get("job_type", "Full Time") if job_details else "Full Time",
                    "application_id": application_id,
                    "candidate_id": user["sub"],
                    "job_id": job_id,
                    "question_count": len(questions_list),
                    "note": "Using real database questions with job details"
                }
            }
            
        except Exception as db_error:
            # logger.error(f"Database error fetching interview questions: {str(db_error)}")
            # Fallback to mock data on database error
            return {
                "data": {
                    "interview_questions": [
                        "Tell me about yourself and your experience",
                        "Why do you want to work for our company?",
                        "What are your greatest strengths?",
                        "Describe a challenging situation you've faced at work",
                        "Where do you see yourself in 5 years?"
                    ],
                    "job_title": "Unknown Position",
                    "application_id": application_id,
                    "candidate_id": user["sub"],
                    "note": f"Using mock data due to database error: {str(db_error)}"
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        # logger.error(f"Get interview questions failed: {str(e)}")
        # Return mock data on any error to prevent frontend from breaking
        return {
            "data": {
                "interview_questions": [
                    "Tell me about yourself and your experience",
                    "Why do you want to work for our company?",
                    "What are your greatest strengths?",
                    "Describe a challenging situation you've faced at work",
                    "Where do you see yourself in 5 years?"
                ],
                "job_title": "Senior Developer Position",
                "application_id": application_id,
                "candidate_id": "unknown",
                "note": f"Using mock data due to error: {str(e)}"
            }
        }

@router.get("/applications/{application_id}/responses")
async def get_interview_responses(request: Request, application_id: str):
    """Get interview responses for a specific application."""
    # Temporarily remove auth requirement for debugging
    # ensure_permission(request, "applications:read")
    user = get_user_from_request(request)
    
    try:
        # Get application details first
        application = mysql_service.get_single_record("job_applications", {"id": application_id})
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get interview responses from video_responses table
        responses = mysql_service.get_records("video_responses", {"application_id": application_id})
        
        # Format responses for frontend
        formatted_responses = []
        for response in responses:
            formatted_responses.append({
                "id": response.get("id"),
                "question": response.get("question"),
                "video_url": response.get("video_url"),
                "video_path": response.get("video_path"),
                "question_index": response.get("question_index"),
                "created_at": response.get("created_at"),
                "duration": response.get("duration")
            })
        
        # Sort by question_index
        formatted_responses.sort(key=lambda x: x.get("question_index", 0))
        
        return {
            "responses": formatted_responses,
            "application_id": application_id,
            "total_responses": len(formatted_responses)
        }
        
    except Exception as e:
        logger.error(f"Get interview responses failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video-proxy/{video_path:path}")
async def video_proxy(request: Request, video_path: str):
    """Proxy video to bypass CORS issues."""
    try:
        from fastapi.responses import StreamingResponse
        import httpx
        
        # Handle both old format (filename only) and new format (full path)
        if not video_path.startswith("datastorage/"):
            # Old format: just filename, prepend the full path
            actual_url = f"https://storage.skreenit.com/datastorage/interviews/{video_path}"
        else:
            # New format: full path already included
            actual_url = f"https://storage.skreenit.com/{video_path}"
        
        logger.info(f"Video proxy: video_path={video_path}, actual_url={actual_url}")
        
        # Stream the video with proper headers
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(actual_url)
            
            if response.status_code == 200:
                return StreamingResponse(
                    response.aiter_bytes(),
                    media_type="video/webm",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "Content-Type": "video/webm",
                        "Accept-Ranges": "bytes"
                    }
                )
            else:
                logger.error(f"Video proxy failed: status={response.status_code}, url={actual_url}")
                raise HTTPException(status_code=404, detail="Video not found")
                
    except Exception as e:
        logger.error(f"Video proxy failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to proxy video")

# ============================================================
# VIDEO ENDPOINTS
# ============================================================

@router.post("/upload-intro-video")
async def upload_intro_video(request: Request, file: UploadFile = File(...)):
    """Upload intro video."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Get current profile to check for existing video
        profile = candidate_service.get_profile(user["sub"])
        old_video_url = profile.get("intro_video_url") if profile else None
        
        # Delete old video from R2 if exists
        if old_video_url:
            try:
                from services.r2_service import R2Service
                r2_service = R2Service()
                r2_service.delete_file(old_video_url)
                logger.info(f"Deleted old intro video: {old_video_url}")
            except Exception as del_err:
                logger.warning(f"Failed to delete old intro video: {del_err}")
                # Continue with upload even if delete fails
        
        # Upload file
        video_url = handle_file_upload(
            file,
            os.getenv("VIDEO_UPLOAD_PATH", "/datastorage/videos"),
            os.getenv("VIDEO_PUBLIC_URL", "https://storage.skreenit.com/datastorage/videos")
        )
        
        # Update profile
        candidate_service.upsert_profile(user["sub"], {"intro_video_url": video_url})
        
        # Also save to candidate_videos table for consistency
        video_path = video_url.replace("https://storage.skreenit.com/", "")
        intro_payload = {
            "candidate_id": user["sub"],
            "video_type": "intro",
            "video_url": video_url,
            "video_path": video_path
        }
        
        # Check if intro video already exists for this candidate
        existing_intro = mysql_service.get_single_record("candidate_videos", {
            "candidate_id": user["sub"],
            "video_type": "intro"
        })
        
        if existing_intro:
            # Update existing intro video
            mysql_service.update_record("candidate_videos", intro_payload, {
                "candidate_id": user["sub"],
                "video_type": "intro"
            })
        else:
            # Insert new intro video
            mysql_service.insert_record("candidate_videos", intro_payload)
        
        logger.info(f"Saved intro video to candidate_videos table for candidate {user['sub']}")
        
        return {"ok": True, "data": {"video_url": video_url}}
    
    except Exception as e:
        logger.error(f"Intro video upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete-intro-video")
async def delete_intro_video(request: Request):
    """Delete intro video."""
    ensure_permission(request, "profile:update")
    user = get_user_from_request(request)
    
    try:
        # Get current profile to remove old video file
        profile = candidate_service.get_profile(user["sub"])
        if profile and profile.get("intro_video_url"):
            # TODO: Delete file from storage (implement R2 file deletion)
            pass
        
        # Update profile to remove video URL
        candidate_service.upsert_profile(user["sub"], {"intro_video_url": None})
        
        # Also delete from candidate_videos table
        mysql_service.delete_record("candidate_videos", {
            "candidate_id": user["sub"],
            "video_type": "intro"
        })
        
        logger.info(f"Deleted intro video from candidate_videos table for candidate {user['sub']}")
        
        return {"ok": True, "success": True}
    
    except Exception as e:
        logger.error(f"Intro video delete failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-intro-response")
async def save_intro_response(request: Request, response_data: dict = Body(...)):
    """Save onboarding interview response metadata to database without application_id."""
    try:
        user = get_user_from_request(request)
        if not user:
            logger.warning("No user found in request for intro response")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Extract response data from frontend
        question = response_data.get("question")
        video_path = response_data.get("video_path")
        video_url = response_data.get("video_url")
        question_index = response_data.get("question_index", 0)
        user_id = user.get("sub") or user.get("id")
        
        if not video_path and not video_url:
            raise HTTPException(status_code=400, detail="Video path or URL required")
        
        # Handle question object (might be object with english property or string)
        if isinstance(question, dict):
            question = question.get("english") or question.get("translated") or str(question)
        elif not isinstance(question, str):
            question = str(question)
        
        # Build R2 URL if only path provided
        if not video_url and video_path:
            video_url = f"https://storage.skreenit.com/{video_path}"
        
        # Save to candidate_intro_responses table (matching existing table structure)
        payload = {
            "user_id": user_id,
            "question_index": question_index,
            "question_text": question,
            "video_url": video_url,
            "video_path": video_path,
            "created_at": datetime.now()
        }
        
        # Insert into candidate_intro_responses table
        result_id = mysql_service.insert_record("candidate_intro_responses", payload)
        
        # Also save the first video (question_index 0) to candidate_videos table as intro video
        if question_index == 0:
            import uuid
            intro_payload = {
                "id": str(uuid.uuid4()),
                "candidate_id": user_id,
                "video_type": "intro",
                "video_url": video_url,
                "video_path": video_path,
                "created_at": datetime.now()
            }
            
            # Check if intro video already exists for this candidate
            existing_intro = mysql_service.get_single_record("candidate_videos", {
                "candidate_id": user_id,
                "video_type": "intro"
            })
            
            if existing_intro:
                # Update existing intro video
                mysql_service.update_record("candidate_videos", intro_payload, {
                    "candidate_id": user_id,
                    "video_type": "intro"
                })
            else:
                # Insert new intro video
                mysql_service.insert_record("candidate_videos", intro_payload)
            
            logger.info(f"Saved intro video to candidate_videos table for user {user_id}")
            
            # Also update candidate_profiles table with intro_video_url
            try:
                mysql_service.update_record("candidate_profiles", {"user_id": user_id}, {"intro_video_url": video_url})
                logger.info(f"Updated candidate_profiles with intro_video_url for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to update candidate_profiles with intro_video_url: {e}")
        
        logger.info(f"Saved intro response to candidate_intro_responses table: {result_id}")
        
        return {"ok": True, "data": {"id": result_id}}
    
    except Exception as e:
        logger.error(f"Save intro response failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-video-response")
async def save_video_response(request: Request, data: dict = Body(...)):
    """Save video response for job application."""
    ensure_permission(request, "applications:create")
    user = get_user_from_request(request)
    
    try:
        data["candidate_id"] = user["sub"]
        result = video_service.save_video_response(data)
        return {"ok": True, "data": result}
    
    except Exception as e:
        logger.error(f"Save video response failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos")
async def get_candidate_videos(request: Request):
    """Get candidate's videos."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        videos = video_service.get_candidate_videos(user["sub"])
        return {"ok": True, "data": videos}
    
    except Exception as e:
        logger.error(f"Get videos failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
# PUBLIC JOBS ENDPOINTS
# ============================================================

@router.get("/jobs")
async def get_public_jobs(request: Request, search: Optional[str] = None):
    """Get public jobs list."""
    try:
        # Check if user is authenticated
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authentication required to view jobs")
        
        jobs = dashboard_service.list_public_jobs(search)
        return {"ok": True, "data": jobs}
    
    except Exception as e:
        logger.error(f"Get public jobs failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_public_job(request: Request, job_id: str):
    """Get public job details."""
    try:
        job = dashboard_service.get_public_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"ok": True, "data": job}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get public job failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-video-response")
async def upload_video_response(
    request: Request,
    video_file: UploadFile = File(...),
    application_id: str = Form(...),
    question_index: int = Form(...),
    question: str = Form(...)
):
    """Upload video response for interview question."""
    # Temporarily remove auth requirement for debugging
    # ensure_permission(request, "applications:write")
    user = get_user_from_request(request)
    
    try:
        # Read video file content
        video_content = await video_file.read()
        
        # Generate unique filename - let R2 service create its timestamp
        import uuid
        import time
        file_extension = video_file.filename.split('.')[-1] if '.' in video_file.filename else 'webm'
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]
        # Let R2 service generate its own timestamp filename
        filename = f"interview.{file_extension}"
        
        # Upload to R2 storage
        try:
            from services.r2_service import R2Service
            r2_service = R2Service()
            
            # Upload to R2 - folder "interviews" will be prepended by the service
            public_url = r2_service.upload_file(video_content, filename, "interviews")
            
            # Extract the path from the public URL (remove the endpoint)
            endpoint = "https://storage.skreenit.com"
            path_from_url = public_url.replace(endpoint + "/", "")
            
            logger.info(f"Video uploaded to R2: {filename} -> {public_url}")
            
            return {
                "data": {
                    "path": path_from_url,  # Return the full R2 path
                    "url": public_url,
                    "message": "Video uploaded successfully to R2 storage"
                }
            }
            
        except Exception as r2_error:
            logger.error(f"R2 upload failed: {str(r2_error)}, falling back to local storage")
            
            # Fallback to local storage if R2 fails
            import os
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads", "interviews", application_id)
            os.makedirs(storage_dir, exist_ok=True)
            file_path = os.path.join(storage_dir, f"q_{question_index}_{timestamp}_{unique_id}.{file_extension}")
            
            # Save file to disk
            with open(file_path, "wb") as f:
                f.write(video_content)
            
            return {
                "data": {
                    "path": filename,
                    "local_path": file_path,
                    "url": f"/uploads/interviews/{application_id}/q_{question_index}_{timestamp}_{unique_id}.{file_extension}",
                    "message": "Video uploaded to local storage (R2 fallback)"
                }
            }
        
    except Exception as e:
        logger.error(f"Upload video response failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications/{application_id}/response")
async def save_response_metadata(
    request: Request,
    application_id: str,
    response_data: dict
):
    """Save interview response metadata to database with language analysis."""
    # Import language service
    from services.indian_language_service import indian_language_service
    
    try:
        user = get_user_from_request(request)
        if not user:
            logger.warning(f"No user found in request for application {application_id}")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Extract response data from frontend
        question = response_data.get("question")
        video_path = response_data.get("video_path")  # This is the R2 path
        video_url = response_data.get("url") or response_data.get("video_url")  # R2 public URL
        question_index = response_data.get("question_index", 0)
        candidate_id = user.get("sub") or user.get("id")
        preferred_language = response_data.get("language", "auto")  # Language preference
        
        if not video_path and not video_url:
            raise HTTPException(status_code=400, detail="Video path or URL required")
        
        # Get job_id from application
        application = mysql_service.get_single_record("job_applications", {"id": application_id})
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        job_id = application.get("job_id")
        
        # Build R2 URL if only path provided
        if not video_url and video_path:
            # video_path already includes full path from R2 service
            video_url = f"https://storage.skreenit.com/{video_path}"
        
        # ===========================================
        # LANGUAGE ANALYSIS AND TRANSCRIPTION
        # ===========================================
        language_analysis = None
        transcription = None
        detected_language = None
        
        try:
            # Download video temporarily for transcription
            from services.video_analysis_service import VideoAnalysisService
            video_svc = VideoAnalysisService()
            
            # Download video to temp location
            temp_video_path = video_svc.download_video(video_url, f"lang_analysis_{application_id}_{question_index}")
            
            if temp_video_path and os.path.exists(temp_video_path):
                logger.info(f"Downloaded video for language analysis: {temp_video_path}")
                
                # Transcribe using Whisper with auto language detection
                transcribe_result = indian_language_service.transcribe_audio(
                    temp_video_path,
                    language=preferred_language if preferred_language != "auto" else None,
                    task="transcribe"
                )
                
                transcription = transcribe_result.get('text', '')
                detected_language = transcribe_result.get('language', 'unknown')
                
                logger.info(f"Transcribed in {detected_language}: {transcription[:100]}...")
                
                # Check if candidate is fresher for specialized analysis
                is_fresher = application.get("experience_years", 0) < 1
                
                # Perform communication analysis
                native_analysis = indian_language_service.analyze_communication(
                    transcription,
                    detected_language,
                    is_fresher=is_fresher
                )
                
                # Generate English report regardless of spoken language
                language_analysis = indian_language_service.generate_english_report(
                    native_analysis,
                    detected_language
                )
                
                # Cleanup temp file
                try:
                    os.unlink(temp_video_path)
                except:
                    pass
                    
        except Exception as lang_err:
            logger.warning(f"Language analysis failed (non-critical): {lang_err}")
            # Continue without language analysis - it's not critical
        
        # Save to video_responses table directly
        import uuid
        response_id = str(uuid.uuid4())
        
        # Use the video_url that was passed in or constructed
        final_video_url = video_url
        
        # Extract filename from video_path or video_url
        if video_path:
            r2_filename = video_path.split('/')[-1]
        elif video_url:
            r2_filename = video_url.split('/')[-1]
        else:
            r2_filename = "unknown.webm"
        
        # Check if this is an onboarding interview (no valid application_id or application_id is empty)
        is_onboarding = not application_id or application_id == "" or application_id == "null"
        
        if is_onboarding:
            # Save to candidate_intro_responses table for onboarding interviews
            payload = {
                "id": response_id,
                "candidate_id": candidate_id,
                "question_index": question_index,
                "question": question,
                "video_url": final_video_url,
                "video_path": video_path or f"interviews/{r2_filename}",
                "transcription": transcription,
                "detected_language": detected_language,
                "language_analysis": language_analysis,  # Already a dict, no need to json.dumps
                "communication_score": language_analysis.get('metrics', {}).get('word_count', 0) if language_analysis else 0,
                "created_at": datetime.now()
            }
            
            # Insert into candidate_intro_responses table
            result_id = mysql_service.insert_record("candidate_intro_responses", payload)
            
            # Also save the first video (question_index 0) to candidate_videos table as intro video
            if question_index == 0:
                intro_payload = {
                    "id": str(uuid.uuid4()),
                    "candidate_id": candidate_id,
                    "video_type": "intro",
                    "video_url": final_video_url,
                    "video_path": video_path or f"interviews/{r2_filename}",
                    "created_at": datetime.now()
                }
                
                # Check if intro video already exists for this candidate
                existing_intro = mysql_service.get_single_record("candidate_videos", {
                    "candidate_id": candidate_id,
                    "video_type": "intro"
                })
                
                if existing_intro:
                    # Update existing intro video
                    mysql_service.update_record("candidate_videos", intro_payload, {
                        "candidate_id": candidate_id,
                        "video_type": "intro"
                    })
                else:
                    # Insert new intro video
                    mysql_service.insert_record("candidate_videos", intro_payload)
                
                logger.info(f"Saved intro video to candidate_videos table for candidate {candidate_id}")
        else:
            # Save to video_responses table for job application interviews
            payload = {
                "id": response_id,
                "job_id": job_id,
                "application_id": application_id,
                "candidate_id": candidate_id,
                "question": question,
                "video_url": final_video_url,  # Use the actual URL
                "video_path": video_path or f"interviews/{r2_filename}",  # Store the path
                "question_index": question_index,
                "created_at": datetime.now(),
                "transcription": transcription,
                "detected_language": detected_language,
                "language_analysis": json.dumps(language_analysis) if language_analysis else None,
                "communication_score": language_analysis.get('metrics', {}).get('word_count', 0) if language_analysis else 0
            }
            
            # Insert into video_responses table
            result_id = mysql_service.insert_record("video_responses", payload)
        
        # Update application status based on completion
        interview_questions = application.get("interview_questions")
        if interview_questions:
            try:
                questions = json.loads(interview_questions) if isinstance(interview_questions, str) else interview_questions
                total_questions = len(questions) if isinstance(questions, list) else 0
                
                # Count existing responses
                existing_responses = mysql_service.get_records(
                    "video_responses", 
                    {"application_id": application_id}
                )
                total_responses = len(existing_responses) if existing_responses else 0
                
                # Update status if all questions answered
                if total_responses >= total_questions and total_questions > 0:
                    # Run face matching before updating status
                    face_match_result = None
                    try:
                        intro_video_url = application.get("intro_video_url")
                        if intro_video_url and existing_responses:
                            from services.face_match_service import face_match_service
                            from services.video_analysis_service import VideoAnalysisService
                            
                            video_svc = VideoAnalysisService()
                            
                            # Download intro video
                            intro_path = video_svc.download_video(intro_video_url, f"intro_{application_id}")
                            
                            # Get all response video paths
                            response_paths = []
                            for resp in existing_responses:
                                resp_url = resp.get("video_url")
                                if resp_url:
                                    resp_path = video_svc.download_video(resp_url, f"resp_{resp.get('id')}")
                                    if resp_path:
                                        response_paths.append(resp_path)
                            
                            if intro_path and response_paths:
                                logger.info(f"Running face matching for application {application_id}")
                                face_match_result = face_match_service.match_multiple_responses(
                                    intro_path, response_paths
                                )
                                logger.info(f"Face match result: {face_match_result}")
                                
                                # Notify recruiter if face mismatch detected
                                if face_match_result and not face_match_result.get("overall_match"):
                                    try:
                                        from services.notification_service_mysql import NotificationService
                                        notification_svc = NotificationService()
                                        
                                        # Get recruiter for this job
                                        job = mysql_service.get_single_record("jobs", {"id": application.get("job_id")})
                                        if job:
                                            recruiter_id = job.get("recruiter_id")
                                            job_title = job.get("job_title", "a position")
                                            
                                            notification_svc.create_notification({
                                                "created_by": recruiter_id,
                                                "title": "Face Mismatch Alert",
                                                "message": f"Face mismatch detected for candidate in '{job_title}'. Intro video and response videos show different persons. Please verify candidate identity.",
                                                "category": "face_mismatch",
                                                "related_id": application_id,
                                                "metadata": {
                                                    "type": "face_mismatch",
                                                    "application_id": application_id,
                                                    "job_id": application.get("job_id"),
                                                    "similarity": face_match_result.get("avg_similarity"),
                                                    "mismatch_count": face_match_result.get("mismatch_count")
                                                }
                                            })
                                            logger.info(f"Face mismatch notification sent to recruiter {recruiter_id}")
                                    except Exception as notif_err:
                                        logger.warning(f"Failed to send face mismatch notification: {notif_err}")
                    except Exception as face_err:
                        logger.warning(f"Face matching failed for application {application_id}: {face_err}")
                    
                    # Update status with face match result
                    update_data = {"status": "responses_submitted", "updated_at": datetime.now()}
                    if face_match_result:
                        update_data["face_match_result"] = face_match_result
                    
                    mysql_service.update_record(
                        "job_applications",
                        {"id": application_id},
                        update_data
                    )
                    logger.info(f"Application {application_id} status updated to responses_submitted")
            except Exception as e:
                logger.warning(f"Could not update application status: {e}")
        
        logger.info(f"Interview response saved: application_id={application_id}, question_index={question_index}, language={detected_language}")
        
        return {
            "ok": True,
            "data": {
                "message": "Response saved successfully",
                "application_id": application_id,
                "question": question,
                "video_path": video_path,
                "video_url": video_url,
                "question_index": question_index,
                "response_id": result_id or response_id,
                "language_analysis": {
                    "detected_language": detected_language,
                    "language_name": indian_language_service.INDIAN_LANGUAGES.get(detected_language, {}).get('name', 'Unknown') if detected_language else None,
                    "transcription": transcription,
                    "analysis": language_analysis
                } if language_analysis else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save response metadata failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save response: {str(e)}")

@router.get("/supported-languages")
async def get_supported_languages(request: Request):
    """Get list of supported Indian languages for video interviews."""
    try:
        from services.indian_language_service import indian_language_service
        
        languages = indian_language_service.get_supported_languages()
        
        return {
            "ok": True,
            "data": {
                "languages": languages,
                "note": "Auto-detection is recommended. The system will automatically detect the language spoken.",
                "features": {
                    "auto_detection": True,
                    "transcription": True,
                    "translation_to_english": True,
                    "fresher_communication_analysis": True
                }
            }
        }
    except Exception as e:
        logger.error(f"Get supported languages failed: {str(e)}")
        return {
            "ok": True,
            "data": {
                "languages": [
                    {"code": "hi", "name": "Hindi", "script": "Devanagari"},
                    {"code": "bn", "name": "Bengali", "script": "Bengali"},
                    {"code": "te", "name": "Telugu", "script": "Telugu"},
                    {"code": "ta", "name": "Tamil", "script": "Tamil"},
                    {"code": "mr", "name": "Marathi", "script": "Devanagari"},
                    {"code": "gu", "name": "Gujarati", "script": "Gujarati"},
                    {"code": "kn", "name": "Kannada", "script": "Kannana"},
                    {"code": "ml", "name": "Malayalam", "script": "Malayalam"},
                    {"code": "pa", "name": "Punjabi", "script": "Gurmukhi"},
                    {"code": "en", "name": "English", "script": "Latin"}
                ],
                "note": "Using fallback language list"
            }
        }

@router.post("/translate-questions")
async def translate_interview_questions(request: Request, data: dict = Body(...)):
    """
    Translate interview questions to the selected language.
    Returns questions in both English and the selected language.
    """
    try:
        from services.indian_language_service import indian_language_service
        
        questions = data.get("questions", [])
        target_language = data.get("language", "en")
        
        if not questions:
            return {"ok": True, "data": {"questions": []}}
        
        # Translate questions to target language
        translated_questions = indian_language_service.translate_questions_batch(
            questions, target_language
        )
        
        logger.info(f"Translated {len(questions)} questions to {target_language}")
        
        return {
            "ok": True,
            "data": {
                "questions": translated_questions,
                "language": target_language,
                "language_name": indian_language_service.INDIAN_LANGUAGES.get(target_language, {}).get('name', 'English')
            }
        }
    except Exception as e:
        logger.error(f"Translate questions failed: {str(e)}")
        # Return original questions in English on failure
        return {
            "ok": True,
            "data": {
                "questions": [{"english": q, "translated": q, "language": "en"} for q in data.get("questions", [])],
                "language": "en",
                "language_name": "English",
                "fallback": True,
                "error": str(e)
            }
        }

@router.post("/delete-video")
async def delete_video(request: Request, video_data: dict = Body(...)):
    """Delete video file from storage."""
    # Temporarily remove auth requirement for debugging
    # ensure_permission(request, "video:delete")
    user = get_user_from_request(request)
    
    try:
        video_path = video_data.get("video_path")
        
        if not video_path:
            raise HTTPException(status_code=400, detail="Video path is required")
        
        # TODO: For local storage, delete from disk
        # In production, delete from cloud storage (AWS S3, etc.)
        import os
        
        # Try to delete from local uploads directory
        # Extract filename from path like "interviews/app_id/q_0_timestamp.webm"
        if "interviews/" in video_path:
            path_parts = video_path.split("interviews/")[1].split("/")
            if len(path_parts) >= 2:
                application_id = path_parts[0]
                filename = path_parts[1]
                
                local_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    "..", "uploads", "interviews", application_id, filename
                )
                
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Deleted video file: {local_path}")
                else:
                    logger.warning(f"Video file not found for deletion: {local_path}")
        
        # TODO: Also delete from database record
        # await db.execute("DELETE FROM interview_responses WHERE video_path = ?", (video_path,))
        
        return {
            "ok": True,
            "data": {
                "message": f"Video {video_path} deleted successfully"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete video failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# AI INTERVIEW QUESTION GENERATION
# ============================================================

def parse_resume_text(file: UploadFile) -> str:
    """Extract text from PDF or DOCX resume file."""
    text = ""
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Parse based on file type
        if file_extension == '.pdf':
            # Parse PDF using PyMuPDF
            with fitz.open(tmp_path) as pdf:
                for page in pdf:
                    text += page.get_text()
        elif file_extension in ['.docx', '.doc']:
            # Parse DOCX using python-docx
            doc = Document(tmp_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Cleanup temp file
        os.unlink(tmp_path)
        
        # Clean up text
        text = text.strip()
        if len(text) > 8000:
            text = text[:8000]  # Limit to 8000 chars for Ollama context
        
        return text
        
    except Exception as e:
        logger.error(f"Resume parsing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")

async def generate_questions_with_ollama(resume_text: str) -> List[str]:
    """Generate personalized interview questions using Ollama (centralized service)."""
    
    try:
        logger.info(f"[OLLAMA_DEBUG] Starting question generation. Resume text length: {len(resume_text)}")
        logger.info(f"[OLLAMA_DEBUG] Resume text preview: {resume_text[:200]}...")
        
        # Uses llama3.2 (primary) → mistral → llama3 (fallbacks)
        questions = ollama_service.generate_interview_questions(resume_text)
        
        logger.info(f"[OLLAMA_DEBUG] Ollama returned: {questions}")
        
        if questions is None:
            logger.error("[OLLAMA_DEBUG] Ollama returned None - checking service health")
            # Check if Ollama service is available
            available_models = ollama_service.get_available_models()
            logger.error(f"[OLLAMA_DEBUG] Available models: {available_models}")
        
        return questions
    except Exception as e:
        logger.error(f"[OLLAMA_DEBUG] Ollama question generation failed with exception: {str(e)}", exc_info=True)
        return None

@router.post("/generate-interview-questions")
async def generate_interview_questions(
    request: Request,
    resume: UploadFile = File(...)
):
    """Generate personalized interview questions from uploaded resume using AI."""
    # Temporarily remove auth for debugging
    # ensure_permission(request, "applications:create")
    
    try:
        user = get_user_from_request(request)
        user_id = user.get("id", "unknown") if user else "unknown"
        
        logger.info(f"Generating interview questions for resume: {resume.filename}, user: {user_id}")
        
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
            return {
                "ok": True,
                "data": {
                    "questions": [
                        "Please introduce yourself in 30 seconds.",
                        "What are your key skills and strengths that make you a great candidate?",
                        "Why are you interested in this position and what are your career goals?"
                    ],
                    "source": "fallback",
                    "reason": "Resume text too short or could not be parsed"
                }
            }
        
        # Generate questions using Ollama (centralized service with fallbacks)
        questions = await generate_questions_with_ollama(resume_text)
        
        if questions:
            logger.info(f"Successfully generated {len(questions)} questions using Ollama")
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
            return {
                "ok": True,
                "data": {
                    "questions": [
                        "Please introduce yourself in 30 seconds.",
                        "What are your key skills and strengths that make you a great candidate?",
                        "Why are you interested in this position and what are your career goals?"
                    ],
                    "source": "fallback",
                    "reason": "AI generation unavailable"
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate interview questions failed: {str(e)}")
        # Return fallback on error
        return {
            "ok": True,
            "data": {
                "questions": [
                    "Please introduce yourself in 30 seconds.",
                    "What are your key skills and strengths that make you a great candidate?",
                    "Why are you interested in this position and what are your career goals?"
                ],
                "source": "fallback",
                "reason": f"Error: {str(e)}"
            }
        }

@router.post("/applications/{application_id}/finish-interview")
async def finish_interview(request: Request, application_id: str):
    """Mark interview as completed and update application status."""
    # Temporarily remove auth requirement for debugging
    ensure_permission(request, "applications:update")
    
    try:
        user = get_user_from_request(request)
        if not user:
            logger.warning(f"No user found in request, using mock finish for application {application_id}")
            # Return mock success response to prevent frontend from breaking
            return {
                "ok": True,
                "data": {
                    "application_id": application_id,
                    "status": "interviewing",
                    "candidate_id": "unknown",
                    "completed_at": time.time(),
                    "note": "Mock completion due to missing authentication"
                }
            }
        
        # Update application status in database
        try:
            success = recruiter_service.update_application_status(application_id, "responses_submitted")
            if success:
                logger.info(f"Application status updated to 'responses_submitted' for {application_id}")
                
                # ✅ NEW: Create notification for recruiter
                try:
                    # Get application details to find job and recruiter
                    from services.mysql_service import MySQLService
                    mysql = MySQLService()
                    application = mysql.get_single_record("job_applications", {"id": application_id})
                    
                    if application:
                        job_id = application.get("job_id")
                        candidate_id = application.get("candidate_id")
                        
                        # Get job details to find recruiter
                        job = mysql.get_single_record("jobs", {"id": job_id})
                        if job:
                            recruiter_id = job.get("created_by")
                            job_title = job.get("job_title", "Unknown Position")
                            
                            # Get candidate name
                            candidate = mysql.get_single_record("users", {"id": candidate_id})
                            candidate_name = candidate.get("full_name", "A candidate") if candidate else "A candidate"
                            
                            # Create notification for recruiter
                            notification = {
                                "created_by": recruiter_id,
                                "title": "Interview Responses Submitted",
                                "message": f"{candidate_name} has submitted video interview responses for '{job_title}'",
                                "category": "interview_submitted",
                                "related_id": application_id,
                                "metadata": {
                                    "application_id": application_id,
                                    "job_id": job_id,
                                    "candidate_id": candidate_id,
                                    "candidate_name": candidate_name,
                                    "job_title": job_title
                                }
                            }
                            
                            notification_service.create_notification(notification)
                            logger.info(f"Notification created for recruiter {recruiter_id} about interview submission")
                except Exception as notif_error:
                    logger.error(f"Failed to create notification: {str(notif_error)}")
                    # Don't fail the whole operation if notification fails
            else:
                logger.warning(f"Failed to update application status for {application_id}")
        except Exception as status_error:
            logger.error(f"Error updating application status: {str(status_error)}")
        
        logger.info(f"Interview completed for application {application_id} by user {user['sub']}")
        
        return {
            "ok": True,
            "data": {
                "message": "Interview completed successfully",
                "application_id": application_id,
                "status": "interviewing",
                "candidate_id": user["sub"],
                "completed_at": time.time()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Finish interview failed: {str(e)}")
        # Return mock success response to prevent frontend from breaking
        return {
            "ok": True,
            "data": {
                "message": "Interview completed successfully (mock due to error)",
                "application_id": application_id,
                "status": "interviewing",
                "candidate_id": "unknown",
                "completed_at": time.time(),
                "note": f"Mock completion due to error: {str(e)}"
            }
        }


# ============================================================
# AI JOB MATCHING & RESUME TEMPLATE ENDPOINTS (for candidates)
# ============================================================

@router.post("/find-matching-jobs")
async def find_matching_jobs(request: Request):
    """
    Find best matching active jobs for the logged-in candidate.
    Uses the candidate's resume text to match against all active JDs.
    Uses llama3 for JD matching → mistral → llama3.2 fallbacks.
    """
    try:
        user = get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = user.get("id") or user.get("sub", "unknown")

        # Get candidate's resume text from profile
        from database import get_db, CandidateProfile, User as DBUser
        db = next(get_db())
        try:
            cand = db.query(DBUser).filter(DBUser.id == user_id).first()
            prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
            if not cand:
                raise HTTPException(status_code=404, detail="Candidate profile not found")

            resume_text = ""
            if prof:
                parts = []
                if cand.full_name: parts.append(f"Name: {cand.full_name}")
                if prof.skills: parts.append(f"Skills: {prof.skills}")
                if prof.experience: parts.append(f"Experience: {prof.experience}")
                if prof.education: parts.append(f"Education: {prof.education}")
                if prof.summary: parts.append(f"Summary: {prof.summary}")
                resume_text = "\n".join(parts)

            if not resume_text or len(resume_text) < 50:
                raise HTTPException(status_code=400, detail="Profile too incomplete for matching. Please update your profile with skills, experience, and education.")
        finally:
            db.close()

        result = jd_matching_service.find_matching_jobs_for_resume(resume_text, user_id)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {"ok": True, "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find matching jobs failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/find-matching-jobs-by-resume")
async def find_matching_jobs_by_resume(
    request: Request,
    resume: UploadFile = File(...)
):
    """
    Upload a resume file and find best matching active jobs.
    Uses llama3 for JD matching → mistral → llama3.2 fallbacks.
    """
    try:
        user = get_user_from_request(request)
        user_id = user.get("id", "unknown") if user else "unknown"

        # Parse resume text
        resume_text = parse_resume_text(resume)
        if not resume_text or len(resume_text) < 50:
            raise HTTPException(status_code=400, detail="Resume text too short or could not be parsed")

        result = jd_matching_service.find_matching_jobs_for_resume(resume_text, user_id)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {"ok": True, "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find matching jobs by resume failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-suggest-template")
async def ai_suggest_template_for_resume(
    request: Request,
    resume: UploadFile = File(...),
    target_role: str = Form("")
):
    """
    Upload resume and get AI-suggested template (modern/traditional/ats/creative).
    Uses mistral for fast analysis.
    """
    try:
        resume_text = parse_resume_text(resume)
        if not resume_text or len(resume_text) < 50:
            raise HTTPException(status_code=400, detail="Resume text too short or could not be parsed")

        result = ollama_service.suggest_resume_template(resume_text, target_role)
        if result:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                import json as json_lib
                try:
                    parsed = json_lib.loads(json_match.group())
                    return {"ok": True, "data": parsed, "model": "mistral"}
                except json_lib.JSONDecodeError:
                    pass
            return {"ok": True, "data": {"raw_response": result}, "model": "mistral"}

        raise HTTPException(status_code=503, detail="AI template suggestion unavailable")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI template suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PROFILE INSIGHTS ENDPOINTS
# ============================================================

@router.get("/profile/specializations")
async def get_candidate_specializations(request: Request):
    """Get candidate specializations based on skills, experience, and applications."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        specializations_set = set()
        
        # Get candidate profile
        profile = candidate_service.get_profile(user["id"])
        if profile:
            # Add skills from profile
            skills = profile.get("skills", [])
            if isinstance(skills, list):
                for skill in skills:
                    if skill:
                        specializations_set.add(skill)
            elif isinstance(skills, str):
                try:
                    parsed_skills = json.loads(skills)
                    if isinstance(parsed_skills, list):
                        for skill in parsed_skills:
                            if skill:
                                specializations_set.add(skill)
                except:
                    pass
            
            # Add from experience
            experience = profile.get("experience", [])
            if isinstance(experience, list):
                for exp in experience:
                    if isinstance(exp, dict):
                        role = exp.get("role") or exp.get("title")
                        if role:
                            specializations_set.add(role)
                        department = exp.get("department")
                        if department:
                            specializations_set.add(department)
            
            # Add from education
            education = profile.get("education", [])
            if isinstance(education, list):
                for edu in education:
                    if isinstance(edu, dict):
                        field = edu.get("field_of_study") or edu.get("degree")
                        if field:
                            specializations_set.add(field)
        
        # Get applications to add job titles/roles applied for
        try:
            applications = mysql_service.get_records("job_applications", {"candidate_id": user["id"]})
            if applications:
                job_ids = [app.get("job_id") for app in applications if app.get("job_id")]
                if job_ids:
                    jobs = mysql_service.get_records("jobs", {"id": job_ids})
                    for job in (jobs or []):
                        job_title = job.get("job_title")
                        if job_title:
                            specializations_set.add(job_title)
                        role = job.get("role")
                        if role:
                            specializations_set.add(role)
                        department = job.get("department")
                        if department:
                            specializations_set.add(department)
        except:
            pass
        
        # Convert to sorted list and limit to top 10
        specializations = sorted(list(specializations_set))[:10]
        
        if not specializations:
            return {"ok": True, "data": {"specializations": [], "message": "Add skills and experience to see your specializations"}}
        
        return {"ok": True, "data": {"specializations": specializations}}
    
    except Exception as e:
        logger.error(f"Get candidate specializations failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/achievements")
async def get_candidate_achievements(request: Request):
    """Get achievements based on candidate's actual activity."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        achievements = []
        
        # Get applications count
        try:
            applications = mysql_service.get_records("job_applications", {"candidate_id": user["id"]})
            applications_count = len(applications or [])
        except:
            applications_count = 0
        
        # Get profile completion
        profile = candidate_service.get_profile(user["id"])
        profile_complete = False
        if profile:
            required_fields = ["skills", "experience", "education"]
            profile_complete = all(profile.get(field) for field in required_fields)
        
        # Check for intro video
        has_intro_video = False
        try:
            videos = mysql_service.get_records("candidate_videos", {"candidate_id": user["id"], "video_type": "intro"})
            has_intro_video = len(videos or []) > 0
        except:
            pass
        
        # Check for resume
        has_resume = False
        if profile and profile.get("resume_url"):
            has_resume = True
        
        # Check for video analysis
        has_analysis = False
        try:
            analysis_tasks = mysql_service.get_records("analysis_tasks", {"created_by": user["id"]})
            has_analysis = len([t for t in (analysis_tasks or []) if t.get("status") == "completed"]) > 0
        except:
            pass
        
        # Generate achievements based on actual activity
        if profile_complete:
            achievements.append({
                "title": "Profile Complete",
                "description": "Completed your profile with skills, experience, and education",
                "icon": "fa-user-check",
                "color": "#16a34a",
                "bg_color": "#dcfce7"
            })
        
        if has_resume:
            achievements.append({
                "title": "Resume Uploaded",
                "description": "Your resume is ready for recruiters to view",
                "icon": "fa-file-pdf",
                "color": "#dc2626",
                "bg_color": "#fee2e2"
            })
        
        if has_intro_video:
            achievements.append({
                "title": "Video Star",
                "description": "Added an introduction video to your profile",
                "icon": "fa-video",
                "color": "#9333ea",
                "bg_color": "#f3e8ff"
            })
        
        if applications_count >= 1:
            achievements.append({
                "title": "First Application",
                "description": "Applied to your first job",
                "icon": "fa-paper-plane",
                "color": "#2563eb",
                "bg_color": "#dbeafe"
            })
        
        if applications_count >= 5:
            achievements.append({
                "title": "Active Job Seeker",
                "description": f"Applied to {applications_count} jobs",
                "icon": "fa-briefcase",
                "color": "#0891b2",
                "bg_color": "#cffafe"
            })
        
        if applications_count >= 10:
            achievements.append({
                "title": "Dedicated Applicant",
                "description": f"Applied to {applications_count}+ jobs",
                "icon": "fa-fire",
                "color": "#ea580c",
                "bg_color": "#ffedd5"
            })
        
        if has_analysis:
            achievements.append({
                "title": "Video Analyzed",
                "description": "Got AI insights on your introduction video",
                "icon": "fa-brain",
                "color": "#7c3aed",
                "bg_color": "#f3e8ff"
            })
        
        # If no achievements yet, show a welcome message
        if not achievements:
            achievements.append({
                "title": "Welcome Aboard",
                "description": "Complete your profile to unlock achievements",
                "icon": "fa-rocket",
                "color": "#6366f1",
                "bg_color": "#e0e7ff"
            })
        
        return {"ok": True, "data": {"achievements": achievements}}
    
    except Exception as e:
        logger.error(f"Get candidate achievements failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/activity")
async def get_candidate_recent_activity(request: Request, limit: int = 5):
    """Get recent activity for the candidate."""
    ensure_permission(request, "profile:read")
    user = get_user_from_request(request)
    
    try:
        activities = []
        
        # Get recent applications
        try:
            applications = mysql_service.get_records("job_applications", {"candidate_id": user["id"]}, order_by="applied_at DESC", limit=limit)
            
            for app in (applications or [])[:limit]:
                # Get job details
                job = mysql_service.get_single_record("jobs", {"id": app.get("job_id")})
                job_title = job.get("job_title") if job else "Unknown Position"
                
                activities.append({
                    "type": "application_submitted",
                    "title": f"Applied to {job_title}",
                    "description": f"Status: {app.get('status', 'Pending')}",
                    "icon": "fa-paper-plane",
                    "color": "#2563eb",
                    "bg_color": "#dbeafe",
                    "created_at": app.get("applied_at")
                })
        except:
            pass
        
        # Get recent video uploads
        try:
            videos = mysql_service.get_records("candidate_videos", {"candidate_id": user["id"]}, order_by="created_at DESC", limit=limit)
            
            for video in (videos or [])[:limit]:
                video_type = video.get("video_type", "intro")
                activities.append({
                    "type": "video_uploaded",
                    "title": f"Uploaded {video_type.replace('_', ' ').title()} video",
                    "description": "Video added to profile",
                    "icon": "fa-video",
                    "color": "#9333ea",
                    "bg_color": "#f3e8ff",
                    "created_at": video.get("created_at")
                })
        except:
            pass
        
        # Get recent profile updates
        try:
            profile = candidate_service.get_profile(user["id"])
            if profile and profile.get("updated_at"):
                activities.append({
                    "type": "profile_updated",
                    "title": "Profile updated",
                    "description": "Your profile information was updated",
                    "icon": "fa-user-edit",
                    "color": "#16a34a",
                    "bg_color": "#dcfce7",
                    "created_at": profile.get("updated_at")
                })
        except:
            pass
        
        # Get recent analysis tasks
        try:
            analysis_tasks = mysql_service.get_records("analysis_tasks", {"created_by": user["id"]}, order_by="created_at DESC", limit=limit)
            
            for task in (analysis_tasks or [])[:limit]:
                activities.append({
                    "type": "analysis_completed",
                    "title": "Video analysis completed",
                    "description": f"Status: {task.get('status', 'Unknown')}",
                    "icon": "fa-brain",
                    "color": "#7c3aed",
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
                
                # Ensure created_at is timezone-aware
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
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
                "description": "Start applying to jobs to see your activity",
                "icon": "fa-rocket",
                "color": "#6366f1",
                "bg_color": "#e0e7ff",
                "time_ago": "Now"
            })

        return {"ok": True, "data": {"activities": activities}}

    except Exception as e:
        logger.error(f"Get candidate recent activity failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job-sample-questions")
async def get_job_sample_questions(request: Request, job_data: dict = Body(...)):
    """
    Generate sample interview questions for a specific job based on its job description.
    Accepts job_id, fetches job details, and uses Ollama LLM to generate 5-10 questions with High/Medium/Low priority.
    """
    try:
        user = get_user_from_request(request)
        user_id = user.get("id", "unknown") if user else "unknown"

        job_id = job_data.get("job_id") if isinstance(job_data, dict) else job_data
        
        logger.info(f"Fetching sample questions for job_id: {job_id}, user: {user_id}")

        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")

        # Fetch job details from database
        from services.mysql_service import MySQLService
        mysql = MySQLService()
        job = mysql.get_single_record("jobs", {"id": job_id})

        if not job:
            logger.warning(f"Job not found: {job_id}")
            # Return fallback questions
            fallback_questions = [
                {'question': 'Tell me about yourself and your background.', 'priority': 'High', 'category': 'Introduction', 'preparation_tip': 'Keep it concise and relevant to the role'},
                {'question': 'What interests you about this position?', 'priority': 'High', 'category': 'Motivation', 'preparation_tip': 'Research the company and role beforehand'},
                {'question': 'What are your key technical skills?', 'priority': 'High', 'category': 'Technical', 'preparation_tip': 'Focus on skills mentioned in the JD'},
                {'question': 'Describe a challenging project you worked on.', 'priority': 'Medium', 'category': 'Experience', 'preparation_tip': 'Use STAR method (Situation, Task, Action, Result)'},
                {'question': 'How do you handle tight deadlines?', 'priority': 'Medium', 'category': 'Behavioral', 'preparation_tip': 'Give a specific example from your experience'},
                {'question': 'What are your career goals?', 'priority': 'Medium', 'category': 'Career', 'preparation_tip': 'Align your goals with the company\'s vision'},
                {'question': 'How do you stay updated with industry trends?', 'priority': 'Low', 'category': 'Professional Development', 'preparation_tip': 'Mention blogs, courses, or communities you follow'},
                {'question': 'Do you have any questions for us?', 'priority': 'Low', 'category': 'Closing', 'preparation_tip': 'Prepare thoughtful questions about the role and company'}
            ]
            return {
                "ok": True,
                "questions": fallback_questions,
                "source": "fallback",
                "reason": "Job not found"
            }

        # Construct JD text from job details
        jd_text = f"""
Job Title: {job.get('job_title', '')}
Company: {job.get('company_name', '')}
Location: {job.get('location', '')}
Department: {job.get('department', '')}
Role: {job.get('role', '')}

Job Description:
{job.get('description', '')}

Requirements:
{job.get('requirements', '')}

Skills Required:
{job.get('skills', '')}
"""

        if not jd_text or len(jd_text.strip()) < 50:
            logger.warning(f"Job description too short for job_id: {job_id}")
            # Return fallback questions
            fallback_questions = [
                {'question': 'Tell me about yourself and your background.', 'priority': 'High', 'category': 'Introduction', 'preparation_tip': 'Keep it concise and relevant to the role'},
                {'question': 'What interests you about this position?', 'priority': 'High', 'category': 'Motivation', 'preparation_tip': 'Research the company and role beforehand'},
                {'question': 'What are your key technical skills?', 'priority': 'High', 'category': 'Technical', 'preparation_tip': 'Focus on skills mentioned in the JD'},
                {'question': 'Describe a challenging project you worked on.', 'priority': 'Medium', 'category': 'Experience', 'preparation_tip': 'Use STAR method (Situation, Task, Action, Result)'},
                {'question': 'How do you handle tight deadlines?', 'priority': 'Medium', 'category': 'Behavioral', 'preparation_tip': 'Give a specific example from your experience'},
                {'question': 'What are your career goals?', 'priority': 'Medium', 'category': 'Career', 'preparation_tip': 'Align your goals with the company\'s vision'},
                {'question': 'How do you stay updated with industry trends?', 'priority': 'Low', 'category': 'Professional Development', 'preparation_tip': 'Mention blogs, courses, or communities you follow'},
                {'question': 'Do you have any questions for us?', 'priority': 'Low', 'category': 'Closing', 'preparation_tip': 'Prepare thoughtful questions about the role and company'}
            ]
            return {
                "ok": True,
                "questions": fallback_questions,
                "source": "fallback",
                "reason": "Job description too short"
            }

        # Generate questions with priority using Ollama
        from services.ollama_service import ollama_service
        questions = ollama_service.generate_questions_from_jd(jd_text, num_questions=8)

        if questions:
            logger.info(f"Successfully generated {len(questions)} questions for job_id: {job_id}")
            return {
                "ok": True,
                "questions": questions,
                "source": "ai",
                "model": "ollama_service"
            }
        else:
            # Fallback to default questions
            logger.warning("Ollama generation failed, using fallback questions")
            fallback_questions = [
                {'question': 'Tell me about yourself and your background.', 'priority': 'High', 'category': 'Introduction', 'preparation_tip': 'Keep it concise and relevant to the role'},
                {'question': 'What interests you about this position?', 'priority': 'High', 'category': 'Motivation', 'preparation_tip': 'Research the company and role beforehand'},
                {'question': 'What are your key technical skills?', 'priority': 'High', 'category': 'Technical', 'preparation_tip': 'Focus on skills mentioned in the JD'},
                {'question': 'Describe a challenging project you worked on.', 'priority': 'Medium', 'category': 'Experience', 'preparation_tip': 'Use STAR method (Situation, Task, Action, Result)'},
                {'question': 'How do you handle tight deadlines?', 'priority': 'Medium', 'category': 'Behavioral', 'preparation_tip': 'Give a specific example from your experience'},
                {'question': 'What are your career goals?', 'priority': 'Medium', 'category': 'Career', 'preparation_tip': 'Align your goals with the company\'s vision'},
                {'question': 'How do you stay updated with industry trends?', 'priority': 'Low', 'category': 'Professional Development', 'preparation_tip': 'Mention blogs, courses, or communities you follow'},
                {'question': 'Do you have any questions for us?', 'priority': 'Low', 'category': 'Closing', 'preparation_tip': 'Prepare thoughtful questions about the role and company'}
            ]
            return {
                "ok": True,
                "questions": fallback_questions,
                "source": "fallback",
                "reason": "AI generation unavailable"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job sample questions failed: {str(e)}")
        # Return fallback on error
        fallback_questions = [
            {'question': 'Tell me about yourself and your background.', 'priority': 'High', 'category': 'Introduction', 'preparation_tip': 'Keep it concise and relevant to the role'},
            {'question': 'What interests you about this position?', 'priority': 'High', 'category': 'Motivation', 'preparation_tip': 'Research the company and role beforehand'},
            {'question': 'What are your key technical skills?', 'priority': 'High', 'category': 'Technical', 'preparation_tip': 'Focus on skills mentioned in the JD'},
            {'question': 'Describe a challenging project you worked on.', 'priority': 'Medium', 'category': 'Experience', 'preparation_tip': 'Use STAR method (Situation, Task, Action, Result)'},
            {'question': 'How do you handle tight deadlines?', 'priority': 'Medium', 'category': 'Behavioral', 'preparation_tip': 'Give a specific example from your experience'},
            {'question': 'What are your career goals?', 'priority': 'Medium', 'category': 'Career', 'preparation_tip': 'Align your goals with the company\'s vision'},
            {'question': 'How do you stay updated with industry trends?', 'priority': 'Low', 'category': 'Professional Development', 'preparation_tip': 'Mention blogs, courses, or communities you follow'},
            {'question': 'Do you have any questions for us?', 'priority': 'Low', 'category': 'Closing', 'preparation_tip': 'Prepare thoughtful questions about the role and company'}
        ]
        return {
            "ok": True,
            "questions": fallback_questions,
            "source": "fallback",
            "reason": f"Error: {str(e)}"
        }

