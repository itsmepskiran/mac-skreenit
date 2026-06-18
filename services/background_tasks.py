"""
Background Tasks Service for long-running operations.
Uses asyncio for non-blocking background execution.
Task status is persisted in analysis_reports table.
"""
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import uuid

logger = logging.getLogger(__name__)

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

def json_serialize(obj):
    """Serialize object to JSON, handling datetime objects."""
    return json.dumps(obj, cls=DateTimeEncoder)

# In-memory cache for quick access (synced with database)
_task_cache: Dict[str, Dict[str, Any]] = {}


class BackgroundTaskService:
    """Manages background tasks for long-running operations with database persistence."""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
    
    def _get_mysql(self):
        """Get MySQL service instance."""
        from services.mysql_service import MySQLService
        return MySQLService()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a background task from cache or database."""
        # Check cache first
        if task_id in _task_cache:
            return _task_cache[task_id]
        
        # Fetch from database using raw SQL
        mysql = self._get_mysql()
        try:
            from sqlalchemy import text
            with mysql.session_factory() as db:
                result = db.execute(
                    text("SELECT * FROM analysis_reports WHERE task_id = :task_id"),
                    {"task_id": task_id}
                ).fetchone()
                
                if result:
                    columns = [desc[0] for desc in db.execute(text("DESCRIBE analysis_reports")).fetchall()]
                    record = {col: result[i] for i, col in enumerate(columns)}
                    
                    task = {
                        "task_id": record.get("task_id"),
                        "user_id": record.get("recruiter_id"),
                        "task_type": "video_analysis",
                        "status": record.get("status"),
                        "progress": record.get("progress", 0),
                        "started_at": record.get("created_at"),
                        "completed_at": record.get("completed_at"),
                        "result": json.loads(record.get("results", "{}")) if record.get("results") else None,
                        "error": record.get("error"),
                        "metadata": {
                            "job_id": record.get("job_id"),
                            "application_ids": json.loads(record.get("application_ids", "[]")) if record.get("application_ids") else []
                        }
                    }
                    _task_cache[task_id] = task
                    return task
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
        
        return None
    
    def get_all_tasks(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get all tasks from database, optionally filtered by user."""
        mysql = self._get_mysql()
        tasks = []
        
        try:
            from sqlalchemy import text
            with mysql.session_factory() as db:
                if user_id:
                    result = db.execute(
                        text("SELECT * FROM analysis_reports WHERE recruiter_id = :user_id ORDER BY created_at DESC"),
                        {"user_id": user_id}
                    ).fetchall()
                else:
                    result = db.execute(text("SELECT * FROM analysis_reports ORDER BY created_at DESC LIMIT 100")).fetchall()
                
                columns = [desc[0] for desc in db.execute(text("DESCRIBE analysis_reports")).fetchall()]
                
                for row in result:
                    record = {col: row[i] for i, col in enumerate(columns)}
                    task = {
                        "task_id": record.get("task_id"),
                        "user_id": record.get("recruiter_id"),
                        "task_type": "video_analysis",
                        "status": record.get("status"),
                        "progress": record.get("progress", 0),
                        "started_at": record.get("created_at"),
                        "completed_at": record.get("completed_at"),
                        "result": json.loads(record.get("results", "{}")) if record.get("results") else None,
                        "error": record.get("error"),
                        "metadata": {
                            "job_id": record.get("job_id"),
                            "application_ids": json.loads(record.get("application_ids", "[]")) if record.get("application_ids") else []
                        }
                    }
                    tasks.append(task)
                    _task_cache[record.get("task_id")] = task
        except Exception as e:
            logger.error(f"Failed to get all tasks: {str(e)}")
        
        return tasks
    
    def get_tasks_by_user(self, user_id: str, task_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks for a specific user, optionally filtered by task_type."""
        tasks = self.get_all_tasks(user_id)
        
        if task_type:
            tasks = [t for t in tasks if t.get("task_type") == task_type]
        
        return tasks[:limit]
    
    def create_task_record(self, task_id: str, task_type: str, user_id: str, metadata: Dict = None) -> Dict:
        """Create a task record in database."""
        mysql = self._get_mysql()
        
        try:
            from sqlalchemy import text
            with mysql.session_factory() as db:
                record_id = str(uuid.uuid4())
                db.execute(
                    text("""
                        INSERT INTO analysis_reports (id, task_id, recruiter_id, job_id, application_ids, status, progress)
                        VALUES (:id, :task_id, :recruiter_id, :job_id, :application_ids, 'pending', 0)
                    """),
                    {
                        "id": record_id,
                        "task_id": task_id,
                        "recruiter_id": user_id,
                        "job_id": metadata.get("job_id") if metadata else None,
                        "application_ids": json.dumps(metadata.get("application_ids", [])) if metadata else "[]"
                    }
                )
                db.commit()
        except Exception as e:
            logger.error(f"Failed to create task record: {str(e)}")
        
        record = {
            "task_id": task_id,
            "task_type": task_type,
            "user_id": user_id,
            "status": "pending",
            "progress": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "result": None,
            "error": None,
            "metadata": metadata or {}
        }
        _task_cache[task_id] = record
        return record
    
    def update_task_status(self, task_id: str, **kwargs):
        """Update task status in database and cache."""
        mysql = self._get_mysql()
        
        try:
            from sqlalchemy import text
            with mysql.session_factory() as db:
                # Build update query dynamically
                updates = []
                params = {"task_id": task_id}
                
                if "status" in kwargs:
                    updates.append("status = :status")
                    params["status"] = kwargs["status"]
                if "progress" in kwargs:
                    updates.append("progress = :progress")
                    params["progress"] = kwargs["progress"]
                if "result" in kwargs:
                    updates.append("results = :results")
                    params["results"] = json.dumps(kwargs["result"], cls=DateTimeEncoder)
                if "error" in kwargs:
                    updates.append("error = :error")
                    params["error"] = kwargs["error"]
                if "completed_at" in kwargs:
                    updates.append("completed_at = :completed_at")
                    # Convert datetime to string if needed
                    val = kwargs["completed_at"]
                    params["completed_at"] = val.isoformat() if hasattr(val, 'isoformat') else val
                
                if updates:
                    sql = f"UPDATE analysis_reports SET {', '.join(updates)} WHERE task_id = :task_id"
                    db.execute(text(sql), params)
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update task status: {str(e)}")
        
        # Update cache
        if task_id in _task_cache:
            _task_cache[task_id].update(kwargs)
    
    async def start_video_analysis_task(
        self,
        task_id: str,
        application_ids: List[str],
        user_id: str,
        job_id: str = None,
        force_refresh: bool = False
    ):
        """
        Background task to analyze video responses.
        This runs asynchronously and creates notifications when complete.
        force_refresh: If True, ignore cached analyses and re-analyze all videos.
        """
        from services.video_analysis_service import VideoAnalysisService
        from services.notification_service_mysql import NotificationService
        from services.mysql_service import MySQLService
        
        mysql = None
        notification_svc = None
        
        try:
            # Update status to running
            self.update_task_status(task_id, status="running", progress=0)
            
            video_analysis_svc = VideoAnalysisService()
            mysql = MySQLService()
            notification_svc = NotificationService()
            
            # Get recruiter profile
            recruiter_profile = mysql.get_single_record("recruiter_profiles", {"user_id": user_id})
            if not recruiter_profile:
                raise ValueError("Recruiter profile not found")
            
            total_apps = len(application_ids)
            results = []
            errors = []
            
            for idx, app_id in enumerate(application_ids):
                try:
                    # Update progress
                    progress = int((idx / total_apps) * 100)
                    self.update_task_status(task_id, progress=progress)
                    
                    # Get application
                    application = mysql.get_single_record("job_applications", {"id": app_id})
                    if not application:
                        errors.append({"application_id": app_id, "error": "Application not found"})
                        continue
                    
                    # Verify job ownership
                    job = mysql.get_single_record("jobs", {"id": application.get("job_id")})
                    if not job or job.get("company_id") != recruiter_profile.get("company_id"):
                        errors.append({"application_id": app_id, "error": "Access denied"})
                        continue
                    
                    # Skip if job_id filter doesn't match
                    if job_id and job.get("id") != job_id:
                        continue
                    
                    candidate_id = application.get("candidate_id")
                    
                    # Get candidate name from users table
                    candidate_user = mysql.get_single_record("users", {"id": candidate_id})
                    candidate_name = candidate_user.get("full_name") or candidate_user.get("email", "Unknown") if candidate_user else "Unknown"
                    
                    # Get video responses
                    video_responses = mysql.get_records("video_responses", {"application_id": app_id}, order_by="question_index ASC")
                    
                    # Get intro video URL first for face matching
                    candidate_profile = mysql.get_single_record("candidate_profiles", {"user_id": candidate_id})
                    intro_video_url = candidate_profile.get("intro_video_url") if candidate_profile else None
                    
                    # Also check candidate_videos table for intro video
                    if not intro_video_url:
                        intro_video_record = mysql.get_single_record("candidate_videos", {"candidate_id": candidate_id, "video_type": "intro"})
                        if intro_video_record:
                            intro_video_url = intro_video_record.get("video_url")
                    
                    # STEP 1: FACE MATCHING FIRST (before detailed analysis)
                    face_match_result = None
                    face_mismatch = False
                    face_match_technical_failure = False
                    
                    if intro_video_url and video_responses:
                        try:
                            from services.face_match_service import face_match_service
                            
                            logger.info(f"Step 1: Running face matching for candidate {candidate_id}")
                            
                            # Download intro video for face matching
                            intro_path = video_analysis_svc.download_video(intro_video_url, f"intro_{candidate_id}")
                            
                            # Download response videos for face matching
                            response_paths = []
                            response_urls = []
                            for vr in video_responses:
                                resp_url = vr.get("video_url")
                                if resp_url:
                                    resp_path = video_analysis_svc.download_video(resp_url, f"resp_{vr.get('id')}")
                                    if resp_path and os.path.exists(resp_path):
                                        response_paths.append(resp_path)
                                        response_urls.append(resp_url)
                            
                            if intro_path and response_paths:
                                face_match_result = face_match_service.match_multiple_responses(
                                    intro_path, response_paths
                                )
                                logger.info(f"Face match result: {face_match_result}")
                                
                                # Check the result - any face issue stops analysis
                                note = face_match_result.get("note", "") if face_match_result else ""
                                
                                # Determine if this is a technical failure (no face in intro, error, etc.)
                                is_technical_failure = (
                                    "No face detected" in note or
                                    "Face matching error" in note or
                                    face_match_result is None
                                )
                                
                                # Determine if this is an actual mismatch (faces detected but don't match)
                                is_face_mismatch = face_match_result and not face_match_result.get("overall_match")
                                
                                if is_technical_failure or is_face_mismatch:
                                    # ANY face issue stops analysis - both technical failure and mismatch
                                    face_mismatch = True
                                    
                                    if is_technical_failure:
                                        logger.warning(f"FACE ISSUE - Technical failure for candidate {candidate_id}: {note}")
                                    else:
                                        logger.warning(f"FACE ISSUE - Face MISMATCH detected for candidate {candidate_id}")
                                    
                                    logger.warning("STOPPING detailed analysis - face verification required")
                                    
                                    # Update application with face match result immediately
                                    mysql.update_record(
                                        "job_applications",
                                        {"id": app_id},
                                        {
                                            "face_match_result": face_match_result,
                                            "updated_at": datetime.now(timezone.utc)
                                        }
                                    )
                                    
                                    # Return early with face issue warning
                                    results.append({
                                        "application_id": app_id,
                                        "candidate_id": candidate_id,
                                        "candidate_name": candidate_name,
                                        "job_title": job.get("job_title", "Unknown"),
                                        "job_id": job.get("id"),
                                        "analyses": [],
                                        "face_match": face_match_result,
                                        "face_mismatch": True,
                                        "face_technical_failure": is_technical_failure,
                                        "status": "face_verification_failed"
                                    })
                                    continue  # Skip to next application
                        except Exception as face_err:
                            logger.warning(f"Face matching failed for candidate {candidate_id}: {face_err}")
                            logger.warning("STOPPING detailed analysis - face verification error")
                            
                            # Create error result
                            error_result = {
                                "overall_match": False,
                                "note": f"Face matching error: {str(face_err)}"
                            }
                            
                            # Update application with error result
                            mysql.update_record(
                                "job_applications",
                                {"id": app_id},
                                {
                                    "face_match_result": error_result,
                                    "updated_at": datetime.now(timezone.utc)
                                }
                            )
                            
                            results.append({
                                "application_id": app_id,
                                "candidate_id": candidate_id,
                                "candidate_name": candidate_name,
                                "job_title": job.get("job_title", "Unknown"),
                                "job_id": job.get("id"),
                                "analyses": [],
                                "face_match": error_result,
                                "face_mismatch": True,
                                "face_technical_failure": True,
                                "status": "face_verification_failed"
                            })
                            continue  # Skip to next application
                    
                    # STEP 2: DETAILED ANALYSIS (only if face match passed or no intro video)
                    analyses = []
                    
                    # Analyze intro video if exists
                    if intro_video_url:
                        existing_intro = None if force_refresh else video_analysis_svc.get_analysis(candidate_id, video_url=intro_video_url)
                        
                        if existing_intro and not force_refresh:
                            analyses.append({
                                "question_index": -1,  # -1 indicates intro video
                                "question": "Intro Video",
                                "video_url": intro_video_url,
                                "analysis": existing_intro,
                                "cached": True
                            })
                        else:
                            try:
                                intro_analysis = video_analysis_svc.analyze_video(
                                    intro_video_url, candidate_id, video_type="intro"
                                )
                                analyses.append({
                                    "question_index": -1,
                                    "question": "Intro Video",
                                    "video_url": intro_video_url,
                                    "analysis": intro_analysis,
                                    "cached": False
                                })
                            except Exception as e:
                                logger.warning(f"Failed to analyze intro video for candidate {candidate_id}: {str(e)}")
                                analyses.append({
                                    "question_index": -1,
                                    "question": "Intro Video",
                                    "video_url": intro_video_url,
                                    "analysis": None,
                                    "error": str(e)
                                })
                    
                    # Analyze video responses
                    for vr in video_responses:
                        video_url = vr.get("video_url")
                        
                        # Check for existing analysis first (skip if force_refresh)
                        existing = None if force_refresh else video_analysis_svc.get_analysis(candidate_id, video_url=video_url)
                        
                        if existing and not force_refresh:
                            analyses.append({
                                "question_index": vr.get("question_index"),
                                "question": vr.get("question"),
                                "video_url": video_url,
                                "analysis": existing,
                                "cached": True
                            })
                        else:
                            try:
                                analysis_result = video_analysis_svc.analyze_video(
                                    video_url, candidate_id, video_type="response",
                                    application_id=app_id, question_index=vr.get("question_index", 0)
                                )
                                analyses.append({
                                    "question_index": vr.get("question_index"),
                                    "question": vr.get("question"),
                                    "video_url": video_url,
                                    "analysis": analysis_result,
                                    "cached": False
                                })
                            except Exception as e:
                                analyses.append({
                                    "question_index": vr.get("question_index"),
                                    "question": vr.get("question"),
                                    "video_url": video_url,
                                    "analysis": None,
                                    "error": str(e)
                                })
                    
                    # Only mark as analyzed if we have any analyses
                    if analyses:
                        # Update application with face match result if we have one
                        if face_match_result:
                            mysql.update_record(
                                "job_applications",
                                {"id": app_id},
                                {
                                    "face_match_result": face_match_result,
                                    "updated_at": datetime.now(timezone.utc)
                                }
                            )
                        
                        results.append({
                            "application_id": app_id,
                            "candidate_id": candidate_id,
                            "candidate_name": candidate_name,
                            "job_title": job.get("job_title", "Unknown"),
                            "job_id": job.get("id"),
                            "analyses": analyses,
                            "face_match": face_match_result,
                            "face_match_technical_failure": face_match_technical_failure,
                            "status": "analyzed"
                        })
                    else:
                        results.append({
                            "application_id": app_id,
                            "candidate_id": candidate_id,
                            "candidate_name": candidate_name,
                            "job_title": job.get("job_title", "Unknown"),
                            "job_id": job.get("id"),
                            "analyses": [],
                            "status": "no_videos"
                        })
                    
                    # Update application status to analysis_ready
                    try:
                        mysql.update_record(
                            "job_applications",
                            {"id": app_id},
                            {"status": "analysis_ready", "updated_at": datetime.now(timezone.utc).isoformat()}
                        )
                        logger.info(f"Application {app_id} status updated to analysis_ready")
                        
                        # Notify candidate that their video analysis is complete
                        try:
                            notification_svc.create_notification({
                                "created_by": candidate_id,
                                "title": "Video Analysis Complete",
                                "message": f"Your video interview for {job.get('job_title', 'the position')} has been analyzed. The recruiter will review your responses soon.",
                                "category": "application_status",
                                "related_id": app_id,
                                "metadata": {
                                    "type": "analysis_ready",
                                    "application_id": app_id,
                                    "job_id": job.get("id"),
                                    "job_title": job.get("job_title", "the position"),
                                    "status": "analysis_ready"
                                }
                            })
                        except Exception as notif_err:
                            logger.warning(f"Failed to send analysis_ready notification to candidate: {notif_err}")
                    except Exception as status_err:
                        logger.warning(f"Failed to update application status: {status_err}")
                    
                except Exception as e:
                    errors.append({"application_id": app_id, "error": str(e)})
            
            # Task complete
            final_result = {
                "results": results,
                "errors": errors,
                "total_analyzed": len(results),
                "total_errors": len(errors)
            }
            
            self.update_task_status(
                task_id,
                status="completed",
                progress=100,
                completed_at=datetime.now(timezone.utc).isoformat(),
                result=final_result
            )
            
            # Create notification for recruiter
            # Include first application_id for direct redirect to analysis page
            first_application_id = results[0].get("application_id") if results else None
            notification_svc.create_notification({
                "created_by": user_id,
                "title": "Video Analysis Complete",
                "message": f"Analysis of {len(results)} candidate(s) completed. Click to view results.",
                "category": "video_analysis",
                "metadata": {
                    "task_id": task_id,
                    "application_id": first_application_id,
                    "total_analyzed": len(results),
                    "total_errors": len(errors),
                    "job_id": job_id
                }
            })
            
            logger.info(f"Video analysis task {task_id} completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Video analysis task {task_id} failed: {str(e)}")
            self.update_task_status(
                task_id,
                status="failed",
                error=str(e),
                completed_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Create failure notification
            try:
                notification_svc = NotificationService()
                notification_svc.create_notification({
                    "created_by": user_id,
                    "title": "Video Analysis Failed",
                    "message": f"Analysis failed: {str(e)}",
                    "category": "video_analysis_error",
                    "metadata": {"task_id": task_id}
                })
            except:
                pass


# Singleton instance
background_task_service = BackgroundTaskService()


async def run_video_analysis_background(
    task_id: str,
    application_ids: List[str],
    user_id: str,
    job_id: str = None,
    force_refresh: bool = False
):
    """
    Entry point for running video analysis in background.
    force_refresh: If True, ignore cached analyses and re-analyze all videos.
    """
    await background_task_service.start_video_analysis_task(
        task_id, application_ids, user_id, job_id, force_refresh
    )
