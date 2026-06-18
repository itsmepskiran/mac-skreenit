from typing import Optional, Dict, Any, List
from services.mysql_service import MySQLService
from utils_others.logger import logger


class DashboardService:
    """
    Provides dashboard summaries for both recruiters and candidates.
    Fetches:
    - User role
    - Jobs (for recruiters)
    - Applications (for both)
    - Basic stats
    """

    def __init__(self, mysql_service: Optional[MySQLService] = None):
        self.mysql = mysql_service or MySQLService()

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    def get_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Returns dashboard summary for recruiter or candidate.
        Structure:
        {
            "role": "recruiter" | "candidate",
            "stats": {...},
            "jobs": [...],
            "applications": [...]
        }
        """
        try:
            role = self._get_user_role(user_id)

            if role == "recruiter":
                return self._get_recruiter_summary(user_id)

            if role == "candidate":
                return self._get_candidate_summary(user_id)

            logger.warning("Unknown user role, returning empty summary", extra={"user_id": user_id})
            return {"role": None, "stats": self._empty_stats(), "jobs": [], "applications": []}

        except Exception as e:
            logger.error(f"Dashboard summary failed: {str(e)}", extra={"user_id": user_id})
            return {"role": None, "stats": self._empty_stats(), "jobs": [], "applications": []}

    # ---------------------------------------------------------
    # PRIVATE HELPERS
    # ---------------------------------------------------------
    def _get_user_role(self, user_id: str) -> Optional[str]:
        """Get user role from MySQL."""
        try:
            user = self.mysql.get_single_record("users", {"id": user_id})
            return user.get("role") if user else None
        except Exception as e:
            logger.error(f"Get user role failed: {str(e)}")
            return None

    def _get_recruiter_summary(self, recruiter_id: str) -> Dict[str, Any]:
        """Get recruiter dashboard summary."""
        try:
            # Get jobs stats
            jobs = self.mysql.get_records("jobs", {"created_by": recruiter_id})
            active_jobs = [j for j in jobs if j.get("status") == "active"]
            
            # Get applications for recruiter's jobs
            job_ids = [j["id"] for j in jobs]
            applications = []
            if job_ids:
                applications = self.mysql.get_records("job_applications", {"job_id": job_ids})
            
            # Calculate stats
            stats = {
                "total_jobs": len(jobs),
                "active_jobs": len(active_jobs),
                "total_applications": len(applications),
                "pending_applications": len([a for a in applications if a.get("status") == "submitted"]),
                "reviewed_applications": len([a for a in applications if a.get("status") in ["reviewing", "shortlisted"]]),
                "accepted_applications": len([a for a in applications if a.get("status") == "accepted"]),
                "rejected_applications": len([a for a in applications if a.get("status") == "rejected"])
            }

            return {
                "role": "recruiter",
                "stats": stats,
                "jobs": jobs or [],
                "applications": applications or []
            }

        except Exception as e:
            logger.error(f"Get recruiter summary failed: {str(e)}")
            return {"role": "recruiter", "stats": self._empty_stats(), "jobs": [], "applications": []}

    def _get_candidate_summary(self, candidate_id: str) -> Dict[str, Any]:
        """Get candidate dashboard summary."""
        try:
            # Get candidate's applications
            applications = self.mysql.get_records(
                "job_applications",
                {"candidate_id": candidate_id},
                order_by="applied_at DESC"
            )
            
            # Get candidate profile
            profile = self.mysql.get_single_record("candidate_profiles", {"user_id": candidate_id})
            
            # Calculate stats
            stats = {
                "total_applications": len(applications),
                "pending_applications": len([a for a in applications if a.get("status") == "submitted"]),
                "reviewing_applications": len([a for a in applications if a.get("status") == "reviewing"]),
                "shortlisted_applications": len([a for a in applications if a.get("status") == "shortlisted"]),
                "accepted_applications": len([a for a in applications if a.get("status") == "accepted"]),
                "rejected_applications": len([a for a in applications if a.get("status") == "rejected"]),
                "profile_completion": self._calculate_profile_completion(profile)
            }

            return {
                "role": "candidate",
                "stats": stats,
                "jobs": [],  # Candidates don't have jobs
                "applications": applications or []
            }

        except Exception as e:
            logger.error(f"Get candidate summary failed: {str(e)}")
            return {"role": "candidate", "stats": self._empty_stats(), "jobs": [], "applications": []}

    def _calculate_profile_completion(self, profile: Optional[Dict[str, Any]]) -> int:
        """Calculate profile completion percentage."""
        if not profile:
            return 0
        
        required_fields = [
            "resume_url",
            "intro_video_url", 
            "linkedin_url",
            "education",
            "experience",
            "skills"
        ]
        
        completed_fields = 0
        for field in required_fields:
            if field in ["education", "experience", "skills"]:
                # These are arrays/lists - check for non-empty arrays
                field_value = profile.get(field)
                if field_value and isinstance(field_value, list) and len(field_value) > 0:
                    # For skills, just check if list has items
                    if field == "skills":
                        completed_fields += 1
                    else:
                        # For education/experience, check if at least one item has meaningful content
                        has_valid_item = any(
                            item and isinstance(item, dict) and 
                            any(str(value).strip() for value in item.values() if value is not None)
                            for item in field_value
                        )
                        if has_valid_item:
                            completed_fields += 1
            else:
                # For URL fields - check for non-empty strings (less strict validation)
                field_value = profile.get(field)
                if field_value and isinstance(field_value, str) and field_value.strip():
                    value = field_value.strip()
                    # Check if it's a valid URL or file path
                    if len(value) > 3:  # Basic length check
                        completed_fields += 1
        
        return int((completed_fields / len(required_fields)) * 100)

    def _empty_stats(self) -> Dict[str, int]:
        """Return empty stats structure."""
        return {
            "total_jobs": 0,
            "active_jobs": 0,
            "total_applications": 0,
            "pending_applications": 0,
            "reviewed_applications": 0,
            "accepted_applications": 0,
            "rejected_applications": 0,
            "profile_completion": 0
        }

    # ---------------------------------------------------------
    # ADDITIONAL DASHBOARD METHODS
    # ---------------------------------------------------------
    def get_recent_activity(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity for user."""
        try:
            role = self._get_user_role(user_id)
            
            if role == "recruiter":
                # Get recent job postings and applications
                recent_jobs = self.mysql.get_records(
                    "jobs",
                    {"created_by": user_id},
                    order_by="created_at DESC",
                    limit=limit
                )
                
                job_ids = [j["id"] for j in recent_jobs]
                recent_applications = []
                if job_ids:
                    recent_applications = self.mysql.get_records(
                        "job_applications",
                        {"job_id": job_ids},
                        order_by="applied_at DESC",
                        limit=limit
                    )
                
                # Combine and sort by date
                activity = []
                for job in recent_jobs:
                    activity.append({
                        "type": "job_posted",
                        "title": f"Posted: {job.get('title', 'Untitled Job')}",
                        "date": job.get("created_at"),
                        "data": job
                    })
                
                for app in recent_applications:
                    activity.append({
                        "type": "application_received",
                        "title": f"New application for job",
                        "date": app.get("applied_at"),
                        "data": app
                    })
                
                # Sort by date (most recent first)
                activity.sort(key=lambda x: x.get("date", ""), reverse=True)
                return activity[:limit]
            
            elif role == "candidate":
                # Get recent applications
                recent_applications = self.mysql.get_records(
                    "job_applications",
                    {"candidate_id": user_id},
                    order_by="applied_at DESC",
                    limit=limit
                )
                
                activity = []
                for app in recent_applications:
                    activity.append({
                        "type": "application_submitted",
                        "title": f"Applied to: {app.get('job_title', 'Job')}",
                        "date": app.get("applied_at"),
                        "data": app
                    })
                
                return activity
            
            return []

        except Exception as e:
            logger.error(f"Get recent activity failed: {str(e)}")
            return []

    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications for user."""
        try:
            conditions = {"user_id": user_id}
            if unread_only:
                conditions["read"] = False
            
            notifications = self.mysql.get_records(
                "notifications",
                conditions,
                order_by="created_at DESC"
            )
            
            return notifications or []

        except Exception as e:
            logger.error(f"Get notifications failed: {str(e)}")
            return []

    def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        try:
            success = self.mysql.update_record(
                "notifications",
                {"read": True, "read_at": datetime.now(timezone.utc)},
                {"id": notification_id, "user_id": user_id}
            )
            return success

        except Exception as e:
            logger.error(f"Mark notification read failed: {str(e)}")
            return False
    # Add this inside the DashboardService class
    def list_public_jobs(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active jobs for the public job board."""
        try:
            conditions = {"status": "active"}
            # Fetch active jobs
            jobs = self.mysql.get_records("jobs", conditions, order_by="created_at DESC")
            if not jobs:
                return []
                
            # Fetch company details to append company names
            company_ids = list(set(j["company_id"] for j in jobs if j.get("company_id")))
            companies_map = {}
            if company_ids:
                companies = self.mysql.get_records("companies", {"id": company_ids})
                companies_map = {c["id"]: c["name"] for c in (companies or [])}
                
            # Enrich job data with skills from jobs table
            for job in jobs:
                job["company_name"] = companies_map.get(job["company_id"], "Unknown Company")
                # Skills are now stored directly in the jobs table as JSON
                job["skills"] = job.get("skills", [])  # Get skills from jobs table or empty array
                
            # Basic text search filter
            if search:
                search_lower = search.lower()
                jobs = [
                    j for j in jobs 
                    if search_lower in j.get("job_title", "").lower() 
                    or search_lower in j.get("company_name", "").lower()
                ]
                
            return jobs
        except Exception as e:
            logger.error(f"List public jobs failed: {str(e)}")
            return []

    def get_public_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a single public job."""
        logger.info(f"=== get_public_job called for job_id: {job_id} ===")
        try:
            job = self.mysql.get_single_record("jobs", {"id": job_id, "status": "active"})
            logger.info(f"=== get_single_record returned: {job.keys() if job else 'None'} ===")
            if not job:
                return None
            
            logger.info(f"Raw job data from DB: {job.keys()} - department: {job.get('department')}, role: {job.get('role')}")
                
            # Enrich with company and skills
            if job.get("company_id"):
                company = self.mysql.get_single_record("companies", {"id": job["company_id"]})
                if company:
                    job["company_name"] = company.get("name")
                    job["company_logo_url"] = company.get("logo_url")
                    
            skills = self.mysql.get_records("job_skills", {"job_id": job_id})
            job["skills"] = [s["skill_name"] for s in (skills or [])]
            
            # Debug: Log reference field values
            logger.info(f"Job reference fields - department: {job.get('department')}, role: {job.get('role')}, employment_type: {job.get('employment_type')}, industry: {job.get('industry')}, education: {job.get('education_qualification')}")
            
            # Resolve reference IDs to names (gracefully handle missing tables)
            try:
                if job.get("department"):
                    dept = self.mysql.get_single_record("departments", {"id": job["department"]})
                    if dept:
                        job["department"] = dept.get("name")
                    else:
                        logger.warning(f"Department not found for id: {job['department']}")
            except Exception as e:
                logger.warning(f"Failed to resolve department: {e}")
                    
            try:
                if job.get("role"):
                    role = self.mysql.get_single_record("roles", {"id": job["role"]})
                    if role:
                        job["role"] = role.get("name")
                    else:
                        logger.warning(f"Role not found for id: {job['role']}")
            except Exception as e:
                logger.warning(f"Failed to resolve role: {e}")
                    
            try:
                if job.get("employment_type"):
                    emp_type = self.mysql.get_single_record("employment_types", {"id": job["employment_type"]})
                    if emp_type:
                        job["employment_type"] = emp_type.get("name")
                    else:
                        logger.warning(f"Employment type not found for id: {job['employment_type']}")
            except Exception as e:
                logger.warning(f"Failed to resolve employment_type: {e}")
                    
            try:
                if job.get("industry"):
                    industry = self.mysql.get_single_record("industries", {"id": job["industry"]})
                    if industry:
                        job["industry"] = industry.get("name")
                    else:
                        logger.warning(f"Industry not found for id: {job['industry']}")
            except Exception as e:
                logger.warning(f"Failed to resolve industry: {e}")
                    
            try:
                if job.get("education_qualification"):
                    edu_level = self.mysql.get_single_record("education_levels", {"id": job["education_qualification"]})
                    if edu_level:
                        job["education_qualification"] = edu_level.get("name")
                    else:
                        logger.warning(f"Education level not found for id: {job['education_qualification']}")
            except Exception as e:
                logger.warning(f"Failed to resolve education_qualification: {e}")
            
            return job
        except Exception as e:
            logger.error(f"Get public job failed: {str(e)}")
            return None