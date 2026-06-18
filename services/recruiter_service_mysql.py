from typing import Optional, Dict, Any, List
from datetime import datetime
from services.mysql_service import MySQLService
from utils_others.logger import logger
from database import JobApplication
from uuid import uuid4
import json

class RecruiterService:
    """
    Enterprise-grade Recruiter Service - MySQL Version
    """

    def __init__(self, mysql_service: Optional[MySQLService] = None):
        self.mysql = mysql_service or MySQLService()

    # ---------------------------------------------------------
    # JOB CRUD
    # ---------------------------------------------------------
    def post_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post a new job with all new fields."""
        try:
            if not job_data.get("company_id"):
                raise ValueError("company_id is required")

            job_data["id"] = str(uuid4())
            
            # Handle skills - store as JSON string if it's a list
            if "skills" in job_data and isinstance(job_data["skills"], list):
                job_data["skills"] = json.dumps(job_data["skills"])
            
            job_id = self.mysql.insert_record("jobs", job_data)
            
            logger.info("Job posted", extra={"created_by": job_data.get("created_by")})
            return {"data": job_data, "id": job_id}
        except Exception as e:
            logger.error(f"Job post failed: {str(e)}")
            raise RuntimeError("Failed to post job")

    def update_job(self, job_id: str, update_data: Dict[str, Any], recruiter_id: str) -> Dict[str, Any]:
        """Update job with all new fields."""
        try:
            # Handle skills - store as JSON string if it's a list
            if "skills" in update_data and isinstance(update_data["skills"], list):
                update_data["skills"] = json.dumps(update_data["skills"])
            
            conditions = {"id": job_id, "created_by": recruiter_id}
            success = self.mysql.update_record("jobs", update_data, conditions)
            
            if not success:
                raise ValueError("Job not found or update failed")
            return self.get_job(job_id, recruiter_id)
        except Exception as e:
            logger.error(f"Update job failed: {str(e)}")
            raise RuntimeError("Failed to update job")

    def list_jobs(self, recruiter_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        try:
            offset = (page - 1) * page_size
            conditions = {"created_by": recruiter_id}
            
            jobs = self.mysql.get_records_with_pagination(
                table="jobs",
                conditions=conditions,
                order_by="created_at DESC",
                limit=page_size,
                offset=offset
            )
            total_count = self.mysql.count_records("jobs", conditions)
            
            # Resolve job_type IDs to names
            job_type_ids = list(set(job.get("job_type") for job in (jobs or []) if job.get("job_type")))
            job_type_names = {}
            if job_type_ids:
                try:
                    for jt_id in job_type_ids:
                        jt = self.mysql.get_single_record("job_types", {"id": jt_id})
                        if jt:
                            job_type_names[jt_id] = jt.get("name")
                except Exception:
                    pass  # Table may not exist
            
            # Resolve country IDs to names using raw SQL
            country_ids = set()
            for job in (jobs or []):
                loc_country = job.get("location_country")
                if loc_country:
                    try:
                        country_ids.add(int(loc_country))
                    except (ValueError, TypeError):
                        pass  # Not a numeric ID
            country_names = {}
            if country_ids:
                try:
                    from sqlalchemy import text
                    from database import engine
                    with engine.connect() as conn:
                        # Handle single element tuple for IN clause
                        ids_tuple = tuple(country_ids) if len(country_ids) > 1 else (list(country_ids)[0],)
                        result = conn.execute(text("SELECT id, name FROM countries WHERE id IN :ids"), {"ids": ids_tuple})
                        for row in result:
                            country_names[row[0]] = row[1]
                except Exception:
                    pass
            
            def resolve_country(job):
                loc_country = job.get("location_country")
                if loc_country:
                    try:
                        cid = int(loc_country)
                        return country_names.get(cid, loc_country)
                    except (ValueError, TypeError):
                        return loc_country
                return None
            
            return {
                "jobs": [
                    {
                        "id": job.get("id"),
                        "job_title": job.get("job_title"),
                        "location": job.get("location"),
                        "job_type": job_type_names.get(job.get("job_type")) or job.get("job_type"),
                        "status": job.get("status"),
                        "salary_min": job.get("salary_min"),
                        "salary_max": job.get("salary_max"),
                        "experience_min": job.get("experience_min"),
                        "experience_max": job.get("experience_max"),
                        "skills": job.get("skills"),
                        "location_city": job.get("location_city"),
                        "location_state": job.get("location_state"),
                        "location_country": resolve_country(job),
                        "is_remote": job.get("is_remote"),
                        "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
                        "updated_at": job.get("updated_at").isoformat() if job.get("updated_at") else None
                    }
                    for job in (jobs or [])
                ],
                "count": total_count,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"List jobs failed: {str(e)}")
            raise RuntimeError("Failed to list jobs")

    def get_job(self, job_id: str, recruiter_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            conditions = {"id": job_id}
            if recruiter_id:
                conditions["created_by"] = recruiter_id
            
            job = self.mysql.get_single_record("jobs", conditions)
            if not job:
                raise ValueError("Job not found")
            
            # Resolve reference IDs to names while preserving original IDs for editing
            try:
                if job.get("department"):
                    dept = self.mysql.get_single_record("departments", {"id": job["department"]})
                    if dept:
                        job["department_id"] = job["department"]  # Preserve UUID for editing
                        job["department"] = dept.get("name")
            except Exception:
                pass  # Table may not exist
                    
            try:
                if job.get("role"):
                    role = self.mysql.get_single_record("roles", {"id": job["role"]})
                    if role:
                        job["role_id"] = job["role"]  # Preserve UUID for editing
                        job["role"] = role.get("name")
            except Exception:
                pass
                    
            try:
                if job.get("employment_type"):
                    emp_type = self.mysql.get_single_record("employment_types", {"id": job["employment_type"]})
                    if emp_type:
                        job["employment_type_id"] = job["employment_type"]  # Preserve UUID for editing
                        job["employment_type"] = emp_type.get("name")
            except Exception:
                pass
                    
            try:
                if job.get("industry"):
                    industry = self.mysql.get_single_record("industries", {"id": job["industry"]})
                    if industry:
                        job["industry_id"] = job["industry"]  # Preserve UUID for editing
                        job["industry"] = industry.get("name")
            except Exception:
                pass
                    
            try:
                if job.get("education_qualification"):
                    edu_level = self.mysql.get_single_record("education_levels", {"id": job["education_qualification"]})
                    if edu_level:
                        job["education_qualification_id"] = job["education_qualification"]  # Preserve UUID for editing
                        job["education_qualification"] = edu_level.get("name")
            except Exception:
                pass
            
            try:
                if job.get("job_type"):
                    jt = self.mysql.get_single_record("job_types", {"id": job["job_type"]})
                    if jt:
                        job["job_type_id"] = job["job_type"]  # Preserve UUID for editing
                        job["job_type"] = jt.get("name")
            except Exception:
                pass
            
            # Resolve country ID to name if stored as numeric ID
            if job.get("location_country"):
                try:
                    country_id = int(job["location_country"])
                    # Use raw SQL since countries table is not in ORM model_map
                    from sqlalchemy import text
                    from database import engine
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT name FROM countries WHERE id = :id"), {"id": country_id})
                        row = result.first()
                        if row:
                            job["location_country_id"] = job["location_country"]  # Preserve ID for editing
                            job["location_country"] = row[0]
                except (ValueError, Exception):
                    pass  # Not a numeric ID, already a name
            
            # Rebuild location string with resolved country name
            if job.get("is_remote"):
                job["location"] = "Remote"
            elif job.get("location_city") or job.get("location_state") or job.get("location_country"):
                parts = [job.get("location_city"), job.get("location_state"), job.get("location_country")]
                job["location"] = ", ".join([p for p in parts if p])
            
            return job
        except Exception as e:
            logger.error(f"Get job failed: {str(e)}")
            raise RuntimeError("Failed to get job")

    def update_job(self, job_id: str, update_data: Dict[str, Any], recruiter_id: str) -> Dict[str, Any]:
        try:
            conditions = {"id": job_id, "created_by": recruiter_id}
            success = self.mysql.update_record("jobs", update_data, conditions)
            
            if not success:
                raise ValueError("Job not found or update failed")
            return self.get_job(job_id, recruiter_id)
        except Exception as e:
            logger.error(f"Update job failed: {str(e)}")
            raise RuntimeError("Failed to update job")

    def delete_job(self, job_id: str, recruiter_id: str) -> Dict[str, Any]:
        try:
            conditions = {"id": job_id, "created_by": recruiter_id}
            success = self.mysql.delete_record("jobs", conditions)
            
            if not success:
                raise ValueError("Job not found or delete failed")
            return {"success": True, "message": "Job deleted successfully"}
        except Exception as e:
            logger.error(f"Delete job failed: {str(e)}")
            raise RuntimeError("Failed to delete job")

    # ---------------------------------------------------------
    # APPLICATIONS
    # ---------------------------------------------------------
    def get_recruiter_applications(self, recruiter_id: str, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # Get jobs created by this recruiter
            job_conditions = {"created_by": recruiter_id}
            if job_id:
                job_conditions["id"] = job_id
                
            jobs = self.mysql.get_records("jobs", job_conditions)
            if not jobs:
                return []
            
            job_ids = [job["id"] for job in jobs]
            
            # Keep a quick lookup for job data (job_title and other metadata)
            job_map = {job["id"]: job for job in jobs}
            
            app_conditions = {"job_id": job_ids}
            applications = self.mysql.get_records("job_applications", app_conditions, order_by="applied_at DESC")
            
            if not applications:
                return []
            
            candidate_ids = list(set(app["candidate_id"] for app in applications))
            application_ids = [app["id"] for app in applications]  # Get all application IDs
            candidate_map = {}
            profile_map = {}
            video_map = {}
            interview_response_map = {}  # Map to store interview responses by application_id
            
            if candidate_ids:
                # Get basic user info
                users = self.mysql.get_records("users", {"id": candidate_ids})
                for user in users or []:
                    candidate_map[user["id"]] = user
                
                # Get candidate profiles (contains resume_url, skills, etc.) - handle if table doesn't exist
                try:
                    profiles = self.mysql.get_records("candidate_profiles", {"user_id": candidate_ids})
                    for profile in profiles or []:
                        profile_map[profile["user_id"]] = profile
                except Exception as e:
                    logger.warning(f"Could not fetch candidate profiles: {str(e)}")
                
                # Get intro videos - handle if table doesn't exist  
                try:
                    videos = self.mysql.get_records("candidate_videos", {"candidate_id": candidate_ids, "video_type": "intro"})
                    for video in videos or []:
                        video_map[video["candidate_id"]] = video
                except Exception as e:
                    logger.warning(f"Could not fetch intro videos: {str(e)}")
                
                # ✅ NEW: Get interview video responses from video_responses table
                try:
                    interview_responses = self.mysql.get_records("video_responses", {"application_id": application_ids})
                    for response in interview_responses or []:
                        app_id = response.get("application_id")
                        if app_id not in interview_response_map:
                            interview_response_map[app_id] = []
                        interview_response_map[app_id].append({
                            "question": response.get("question"),
                            "video_url": response.get("video_url"),
                            "video_path": response.get("video_path"),
                            "question_index": response.get("question_index"),
                            "duration": response.get("duration"),
                            "transcript": response.get("transcript"),
                            "created_at": response.get("created_at")
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch interview video responses: {str(e)}")
            
            enriched_apps = []
            for app in applications:
                candidate = candidate_map.get(app["candidate_id"])
                if candidate:
                    app["candidate"] = {
                        "full_name": candidate.get("full_name"),
                        "email": candidate.get("email"),
                        "phone": candidate.get("phone")
                    }
                    # Normalize for frontend convenience
                    app["candidate_name"] = candidate.get("full_name")
                    app["candidate_email"] = candidate.get("email")
                    app["candidate_phone"] = candidate.get("phone")

                # Add candidate profile data (resume, skills, cover letter, etc.)
                try:
                    profile = profile_map.get(app["candidate_id"])
                    if profile:
                        # Check for converted resume first, then fallback to original
                        app["resume_url"] = (
                            profile.get("converted_resume_url") or
                            profile.get("resume_url") or 
                            profile.get("resume") or 
                            profile.get("cv_url") or 
                            profile.get("cv") or
                            profile.get("resume_file") or
                            profile.get("cv_file")
                        )
                        app["resume_template"] = profile.get("resume_template", "original")
                        app["skills"] = profile.get("skills", [])
                        app["cover_letter"] = profile.get("cover_letter")
                        app["linkedin"] = profile.get("linkedin_url") or profile.get("linkedin")
                        app["custom_answers"] = profile.get("custom_answers", [])
                        app["ai_score"] = profile.get("ai_score")
                        
                        # Add intro video URL from application if available
                        app["intro_video_url"] = app.get("intro_video_url")
                        
                        # Debug logging to see what profile fields are available
                        if not app["resume_url"]:
                            pass  # No resume URL found
                    else:
                        pass  # No profile found
                except Exception as e:
                    logger.warning(f"Could not add profile data for candidate {app['candidate_id']}: {str(e)}")

                # Add intro video data
                try:
                    video = video_map.get(app["candidate_id"])
                    if video:
                        app["intro_video_url"] = video.get("video_url")
                except Exception as e:
                    logger.warning(f"Could not add video data for candidate {app['candidate_id']}: {str(e)}")

                # ✅ NEW: Add interview video responses to application data
                try:
                    interview_videos = interview_response_map.get(app["id"], [])
                    if interview_videos:
                        app["interview_responses"] = interview_videos
                        app["interview_video_count"] = len(interview_videos)
                        # Also provide a convenience field with just the video URLs
                        app["interview_video_urls"] = [v.get("video_url") for v in interview_videos if v.get("video_url")]
                except Exception as e:
                    logger.warning(f"Could not add interview videos for application {app['id']}: {str(e)}")

                job = job_map.get(app.get("job_id"))
                if job:
                    app["job_title"] = job.get("job_title")
                    # ❌ REMOVED: app["status"] = job.get("status") - was overwriting application status!
                    # ✅ Application status comes from job_applications table, not jobs table
                    app["created_at"] = job.get("created_at")

                enriched_apps.append(app)
            return enriched_apps
        except Exception as e:
            logger.error(f"Get recruiter applications failed: {str(e)}")
            raise RuntimeError("Failed to get applications")

    def update_application_status(self, application_id: str, new_status: str, questions: List[str] = None, feedback: str = None) -> bool:
        """Update application status and optionally save interview questions and feedback."""
        try:
            
            # Get the application first to verify it exists
            applications = self.mysql.get_records("job_applications", {"id": application_id})
            if not applications:
                return False
            
            # Prepare update data
            update_data = {
                "status": new_status
            }
            
            # If questions are provided, save them in the application's interview_questions JSON field
            if questions and len(questions) > 0:
                update_data["interview_questions"] = questions
            
            # If feedback is provided, save it
            if feedback:
                update_data["feedback"] = feedback
            
            # Update the application
            success = self.mysql.update_record("job_applications", 
                update_data, {"id": application_id})
            
            if success:
                if questions and len(questions) > 0:
                    logger.info(f"Successfully saved {len(questions)} interview questions")
                if feedback:
                    logger.info(f"Successfully saved feedback for application {application_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Update application status failed: {str(e)}")
            return False

    # ---------------------------------------------------------
    # COMPANY & PROFILE MANAGEMENT
    # ---------------------------------------------------------
    def create_company(self, name: str, recruiter_id: str, description: str = None, website: str = None, avatar_url: str = None) -> Dict[str, Any]:
        try:
            display_id = self._generate_company_display_id(name)
            payload = {
                "id": str(uuid4()),
                "name": name,
                "description": description,
                "website": website,
                "avatar_url": avatar_url,
                "company_display_id": display_id,
                "recruiter_id": recruiter_id
            }
            company_id = self.mysql.insert_record("companies", payload)
            return {"data": payload, "id": company_id}
        except Exception as e:
            logger.error(f"Create company failed: {str(e)}")
            raise RuntimeError("Failed to create company")

    def list_companies(self) -> List[Dict[str, Any]]:
        try:
            companies = self.mysql.get_records("companies", order_by="name ASC")
            return companies or []
        except Exception as e:
            logger.error(f"List companies failed: {str(e)}")
            raise RuntimeError("Failed to list companies")

    def update_company_logo(self, user_id: str, logo_url: str) -> Dict[str, Any]:
        """Update company logo without requiring company name (for existing companies)."""
        try:
            existing = self.mysql.get_single_record("recruiter_profiles", {"user_id": user_id})
            
            if not existing:
                raise ValueError("Recruiter profile not found")
            
            if not existing.get("company_id"):
                raise ValueError("Company not found. Please complete your profile first.")
            
            # Update only the company avatar (use avatar_url to match schema)
            company_update_data = {"avatar_url": logo_url}
            self.mysql.update_record("companies", company_update_data, {"id": existing["company_id"]})
            
            return {"ok": True, "avatar_url": logo_url}
            
        except Exception as e:
            logger.error(f"Update company logo failed: {str(e)}")
            raise RuntimeError("Failed to update company logo")

    def upsert_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            existing = self.mysql.get_single_record("recruiter_profiles", {"user_id": payload["user_id"]})

            # Backend validation: Company name is MANDATORY for company ID generation
            # All recruiter profiles must have an associated company with a name
            company_name = (payload.get("company_name") or "").strip()
            
            if not company_name:
                raise ValueError("Company name is required to generate company ID")

            if existing:
                profile_update_data = {
                    "contact_name": payload.get("contact_name"),
                    "contact_email": payload.get("contact_email"),
                    "location": payload.get("location")
                }
                profile_update_data = {k: v for k, v in profile_update_data.items() if v not in (None, "")}
                
                if profile_update_data:
                    self.mysql.update_record("recruiter_profiles", profile_update_data, {"user_id": payload["user_id"]})
                
                if existing.get("company_id"):
                    company_update_data = {
                        "name": payload.get("company_name"),
                        "description": payload.get("company_description"),
                        "website": payload.get("company_website"),
                        "location": payload.get("location"),  # Copy location from recruiter profile
                        "avatar_url": payload.get("company_logo_url"),  # Use avatar_url to match schema
                    }
                    company_update_data = {k: v for k, v in company_update_data.items() if v not in (None, "")}
                    
                    if company_update_data:
                        self.mysql.update_record("companies", company_update_data, {"id": existing["company_id"]})

                    # Update company_display_id if name changed
                    if company_update_data.get("name"):
                        # Get current company data to check if name actually changed
                        current_company = self.mysql.get_single_record("companies", {"id": existing["company_id"]})
                        if current_company and current_company.get("name") != company_update_data["name"]:
                            display_id = self._generate_company_display_id(company_update_data["name"])
                            self.mysql.update_record("companies", {"company_display_id": display_id}, {"id": existing["company_id"]})
                
                # If this recruiter has a profile but no company record yet, check if company already exists
                elif payload.get("company_name"):
                    # First check if there's already a company for this recruiter
                    existing_company = self.mysql.get_single_record("companies", {"recruiter_id": payload["user_id"]})
                    
                    if existing_company:
                        # Update existing company
                        company_update_data = {
                            "name": payload.get("company_name"),
                            "description": payload.get("company_description"),
                            "website": payload.get("company_website"),
                            "location": payload.get("location"),  # Copy location from recruiter profile
                            "avatar_url": payload.get("company_logo_url"),
                        }
                        company_update_data = {k: v for k, v in company_update_data.items() if v not in (None, "")}
                        
                        if company_update_data:
                            self.mysql.update_record("companies", company_update_data, {"id": existing_company["id"]})
                        
                        # Update the recruiter profile to reference the existing company
                        self.mysql.update_record("recruiter_profiles", {"company_id": existing_company["id"]}, {"user_id": payload["user_id"]})
                    else:
                        # Create new company only if none exists
                        company_name = payload.get("company_name")
                        company_data = {
                            "id": str(uuid4()),
                            "name": company_name,
                            "description": payload.get("company_description"),
                            "website": payload.get("company_website"),
                            "location": payload.get("location"),  # Copy location from recruiter profile
                            "avatar_url": payload.get("company_logo_url"),
                            "company_display_id": self._generate_company_display_id(company_name),
                            "recruiter_id": payload["user_id"]
                        }
                        new_company_id = self.mysql.insert_record("companies", company_data)
                        if new_company_id:
                            self.mysql.update_record("recruiter_profiles", {"company_id": new_company_id}, {"user_id": payload["user_id"]})

                if profile_update_data:
                    self.mysql.update_record("recruiter_profiles", profile_update_data, {"user_id": payload["user_id"]})
                
                updated_profile = self.get_profile(payload["user_id"])
                return {"data": updated_profile, "updated": True}
            else:
                # Create a new recruiter profile.
                # If a company name is provided, create the company record immediately.
                # This ensures the company name is preserved and visible in the UI.
                company_id = None
                company_name = (payload.get("company_name") or "").strip()

                if company_name:
                    company_data = {
                        "id": str(uuid4()),
                        "name": company_name,
                        "description": payload.get("company_description"),
                        "website": payload.get("company_website"),
                        "avatar_url": payload.get("company_logo_url"),  # Use avatar_url to match schema
                        "company_display_id": self._generate_company_display_id(company_name),
                        "recruiter_id": payload["user_id"]
                    }
                    company_id = self.mysql.insert_record("companies", company_data)

                profile_data = {
                    "id": str(uuid4()),
                    "user_id": payload["user_id"],
                    "company_id": company_id,
                    "contact_name": payload.get("contact_name"),
                    "contact_email": payload.get("contact_email")
                }

                profile_id = self.mysql.insert_record("recruiter_profiles", profile_data)
                complete_profile = self.get_profile(payload["user_id"])

                return {"data": complete_profile, "id": profile_id, "updated": False}
                
        except ValueError:
            # Validation errors should be handled by the caller (e.g., returning 400).
            raise
        except Exception as e:
            logger.error(f"Upsert recruiter profile failed: {str(e)}")
            raise RuntimeError("Failed to save recruiter profile")

    def _generate_company_display_id(self, company_name: Optional[str] = None) -> str:
        """Generate company display ID: 3 letters from company name + 5 letters from company_id/UUID."""
        try:
            # Take first 3 letters from company name (alphanumeric only, uppercase)
            prefix = "".join([c for c in (company_name or "") if c.isalnum()]).upper()[:3]
            if not prefix: prefix = "CMP"
            
            # Take 5 letters from UUID
            import uuid
            suffix = uuid.uuid4().hex.upper()[:5]
            
            return f"{prefix}{suffix}"  # 3 + 5 = 8 characters total
        except Exception:
            import random
            import string
            prefix = (company_name or "CMP").upper()[:3]
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            return f"{prefix}{suffix}"

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the combined profile data for the recruiter."""
        try:
            profile = self.mysql.get_single_record("recruiter_profiles", {"user_id": user_id})
            if not profile:
                return None

            user = self.mysql.get_single_record("users", {"id": user_id})
            if user:
                profile["contact_name"] = profile.get("contact_name") or user.get("full_name")
                profile["contact_email"] = profile.get("contact_email") or user.get("email")
                profile["avatar_url"] = profile.get("avatar_url") or user.get("avatar_url")

            if profile.get("company_id"):
                company = self.mysql.get_single_record("companies", {"id": profile["company_id"]})
                if company:
                    # Always include company fields so frontend can make correct decisions.
                    # Use empty string defaults to ensure the key is always present.
                    profile["company_name"] = company.get("name") or ""
                    profile["company_website"] = company.get("website") or ""
                    profile["company_description"] = company.get("description") or ""
                    profile["company_display_id"] = company.get("company_display_id") or ""
                    profile["company_logo_url"] = company.get("avatar_url") or ""

            return profile
        except Exception as e:
            logger.error(f"Get recruiter profile failed: {str(e)}")
            return None

    # ---------------------------------------------------------
    # SKILLS & QUESTIONS (Trimmed for brevity, assuming standard setup)
    # ---------------------------------------------------------
    def add_job_skill(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload["id"] = str(uuid4())
        return {"data": payload, "id": self.mysql.insert_record("job_skills", payload)}

    def list_job_skills(self, job_id: str) -> List[Dict[str, Any]]:
        return self.mysql.get_records("job_skills", {"job_id": job_id}) or []

    def delete_job_skill(self, skill_id: str) -> None:
        self.mysql.delete_record("job_skills", {"id": skill_id})

    def add_interview_question(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload["id"] = str(uuid4())
        return {"data": payload, "id": self.mysql.insert_record("interview_questions", payload)}

    def list_interview_questions(self, job_id: str) -> List[Dict[str, Any]]:
        return self.mysql.get_records("interview_questions", {"job_id": job_id}, order_by="question_order ASC") or []

    def delete_interview_question(self, question_id: str) -> None:
        self.mysql.delete_record("interview_questions", {"id": question_id})

    # ---------------------------------------------------------
    # CANDIDATE DETAILS
    # ---------------------------------------------------------
    def get_candidate_details_for_application(self, candidate_id: str, job_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            profile = self._fetch_candidate_profile(candidate_id)
            application = self._fetch_candidate_application(candidate_id, job_id) if job_id else None
            resume_url = self._get_resume_signed_url(profile) if profile else None
            intro_video = self._fetch_intro_video(candidate_id)
            
            # Get intro video URL from application if available
            intro_video_url = None
            if application and application.get("intro_video_url"):
                intro_video_url = application.get("intro_video_url")
            elif intro_video:
                intro_video_url = intro_video.get("video_url")
                
            job_videos = self._fetch_job_video_responses(candidate_id, job_id) if job_id else []
            
            return {
                "profile": profile or {},
                "application": application,
                "resume_url": resume_url,
                "intro_video": intro_video,
                "intro_video_url": intro_video_url,
                "job_videos": job_videos
            }
        except Exception as e:
            logger.error(f"Get candidate details failed: {str(e)}")
            return {}

    def _fetch_candidate_profile(self, candidate_id: str):
        """Fetch candidate profile by combining data from both users and candidate_profiles tables."""
        logger.info(f"Fetching candidate profile for candidate_id: {candidate_id}")
        try:
            # Get data from candidate_profiles table
            profile = self.mysql.get_single_record("candidate_profiles", {"user_id": candidate_id})
            logger.info(f"Candidate_profiles result: {profile}")
            
            # Get basic user info from users table
            user_info = self.mysql.get_single_record("users", {"id": candidate_id})
            logger.info(f"Users table result for {candidate_id}: {user_info}")
            
            if profile and user_info:
                # Combine data from both tables, with user info taking precedence for basic fields
                combined_profile = {
                    **profile,
                    # Basic user fields that should come from users table
                    "full_name": user_info.get("full_name", ""),
                    "first_name": user_info.get("first_name", ""),
                    "last_name": user_info.get("last_name", ""),
                    "email": user_info.get("email", ""),
                    "phone": user_info.get("phone", ""),
                    "location": user_info.get("location", ""),
                    "avatar_url": user_info.get("avatar_url", ""),
                }
                logger.info(f"Combined profile keys: {list(combined_profile.keys())}")
                logger.info(f"Combined profile name: {combined_profile.get('full_name')}")
                logger.info(f"Combined profile email: {combined_profile.get('email')}")
                return combined_profile
            elif profile:
                # Profile exists but no user info (shouldn't happen but handle gracefully)
                logger.warning(f"Candidate profile found for {candidate_id} but no user info")
                return profile
            else:
                logger.warning(f"No candidate profile found for {candidate_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch candidate profile for {candidate_id}: {str(e)}")
            return None

    def _fetch_candidate_application(self, candidate_id: str, job_id: Optional[str]):
        if job_id:
            return self.mysql.get_single_record("job_applications", {"candidate_id": candidate_id, "job_id": job_id})
        apps = self.mysql.get_records("job_applications", {"candidate_id": candidate_id}, order_by="applied_at DESC", limit=1)
        return apps[0] if apps else None

    def _get_resume_signed_url(self, profile: Dict[str, Any]):
        # Check for converted resume first, then fallback to original
        path = profile.get("converted_resume_url") or profile.get("resume_url")
        return f"/storage/resumes/{path}" if path else None

    def _fetch_intro_video(self, candidate_id: str):
        return self.mysql.get_single_record("candidate_videos", {"candidate_id": candidate_id, "video_type": "intro"})

    def _fetch_job_video_responses(self, candidate_id: str, job_id: Optional[str]) -> List[Dict[str, Any]]:
        if not job_id: return []
        try:
            app = self.mysql.get_single_record("job_applications", {"candidate_id": candidate_id, "job_id": job_id})
            if not app: return []
            return self.mysql.get_records("video_responses", {"candidate_id": candidate_id, "application_id": app["id"]}, order_by="created_at ASC") or []
        except Exception:
            return []

    def get_application_by_id(self, app_id: str) -> Dict[str, Any]:
        application = self.mysql.get_single_record("job_applications", {"id": app_id})
        if not application: raise ValueError("Application not found")
        job = self.mysql.get_single_record("jobs", {"id": application["job_id"]})
        candidate_details = self.get_candidate_details_for_application(application["candidate_id"], application["job_id"])
        
        # Get interview responses from video_responses table
        interview_responses = []
        try:
            video_responses = self.mysql.get_records("video_responses", {"application_id": app_id}, order_by="question_index ASC")
            for vr in video_responses or []:
                interview_responses.append({
                    "question": vr.get("question"),
                    "video_url": vr.get("video_url"),
                    "video_path": vr.get("video_path"),
                    "question_index": vr.get("question_index"),
                    "duration": vr.get("duration"),
                    "transcript": vr.get("transcript"),
                    "created_at": vr.get("created_at")
                })
        except Exception as e:
            logger.warning(f"Could not fetch interview responses for application {app_id}: {str(e)}")
        
        # Add interview responses to application
        application["interview_responses"] = interview_responses
        application["interview_video_urls"] = [v.get("video_url") for v in interview_responses if v.get("video_url")]
        
        return {
            "application": application,
            "job": job,
            "candidate": candidate_details
        }