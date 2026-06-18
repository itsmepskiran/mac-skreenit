import uuid
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from services.mysql_service import MySQLService
from utils_others.logger import logger


class VideoService:
    """
    Handles all video-related operations:
    - Uploading videos to Cloudflare R2/Local storage
    - Creating signed URLs
    - Saving per-question video responses
    - Saving general video interviews
    - Listing video responses
    - Listing candidate videos
    """

    def __init__(self, mysql_service: Optional[MySQLService] = None):
        self.mysql = mysql_service or MySQLService()
        self.storage_path = "storage/videos"

    # ---------------------------------------------------------
    # STORAGE UPLOAD
    # ---------------------------------------------------------
    def upload_video_to_storage(self, file_content: bytes, filename: str, candidate_id: str) -> str:
        """
        Upload a video file to storage and return a public URL.
        """
        try:
            file_extension = filename.split(".")[-1] if "." in filename else "mp4"
            unique_filename = f"{candidate_id}/{uuid.uuid4()}.{file_extension}"
            
            # Create directory if it doesn't exist
            full_path = os.path.join(self.storage_path, unique_filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save file locally (TODO: Implement Cloudflare R2)
            with open(full_path, "wb") as f:
                f.write(file_content)
            
            # Return public URL (TODO: Implement Cloudflare R2 URL)
            public_url = f"/api/videos/{unique_filename}"
            
            logger.info(f"Video uploaded: {unique_filename}")
            return public_url

        except Exception as e:
            logger.error(f"Video upload failed: {str(e)}")
            raise RuntimeError("Failed to upload video")

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Create a signed URL for video access.
        TODO: Implement Cloudflare R2 signed URLs
        """
        try:
            # For now, return direct URL (implement signed URLs for R2 later)
            return f"/api/videos/{file_path}"
        except Exception as e:
            logger.error(f"Failed to create signed URL: {str(e)}")
            return None

    # ---------------------------------------------------------
    # VIDEO RESPONSES
    # ---------------------------------------------------------
    def save_video_response(
        self,
        application_id: str,
        question: str,
        video_url: str,
        transcript: Optional[str] = None,
        duration: Optional[int] = None,
        candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a video response for a specific interview question.
        """
        try:
            payload: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "application_id": application_id,
                "question_text": question,  # Updated column name for MySQL
                "video_url": video_url,
                "transcript": transcript,
                "duration": duration,
                "recorded_at": datetime.now(timezone.utc)
            }

            if candidate_id:
                payload["candidate_id"] = candidate_id

            # Insert into MySQL
            response_id = self.mysql.insert_record("video_responses", payload)
            
            logger.info(f"Video response saved for application {application_id}")
            return {"data": payload, "id": response_id}

        except Exception as e:
            logger.error(f"Save video response failed: {str(e)}")
            raise RuntimeError("Failed to save video response")

    def save_general_video_interview(
        self,
        candidate_id: str,
        video_url: str,
        transcript: Optional[str] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save a general video interview (not tied to specific job).
        """
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "candidate_id": candidate_id,
                "video_url": video_url,
                "transcript": transcript,
                "duration": duration,
                "recorded_at": datetime.now(timezone.utc)
            }

            # Check if exists and update, or insert new
            existing = self.mysql.get_single_record("intro_videos", {"candidate_id": candidate_id})
            
            if existing:
                success = self.mysql.update_record(
                    "intro_videos", 
                    payload, 
                    {"candidate_id": candidate_id}
                )
                action = "updated"
            else:
                response_id = self.mysql.insert_record("intro_videos", payload)
                action = "created"

            logger.info(f"Intro video {action} for candidate {candidate_id}")
            return {"data": payload, "action": action}

        except Exception as e:
            logger.error(f"Save general video interview failed: {str(e)}")
            raise RuntimeError("Failed to save general video interview")

    # ---------------------------------------------------------
    # VIDEO RETRIEVAL
    # ---------------------------------------------------------
    def get_video_responses_for_application(self, application_id: str) -> List[Dict[str, Any]]:
        """
        Get all video responses for a specific job application.
        """
        try:
            responses = self.mysql.get_records(
                "video_responses",
                {"application_id": application_id},
                order_by="recorded_at ASC"
            )
            return responses or []

        except Exception as e:
            logger.error(f"Get video responses failed: {str(e)}")
            return []

    def get_candidate_videos(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get all video responses for a candidate.
        """
        try:
            responses = self.mysql.get_records(
                "video_responses",
                {"candidate_id": candidate_id},
                order_by="recorded_at DESC"
            )
            return responses or []

        except Exception as e:
            logger.error(f"Get candidate videos failed: {str(e)}")
            return []

    def get_intro_video(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the introduction video for a candidate.
        """
        try:
            video = self.mysql.get_single_record("intro_videos", {"candidate_id": candidate_id})
            return video

        except Exception as e:
            logger.error(f"Get general video interview failed: {str(e)}")
            return None

    # ---------------------------------------------------------
    # INTERVIEW RESPONSES
    # ---------------------------------------------------------
    def save_interview_response(
        self,
        interview_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save a video interview response for a specific question.
        This method handles the data structure from the interview recording system.
        """
        try:
            payload = {
                "application_id": interview_response.get("application_id"),
                "candidate_id": interview_response.get("candidate_id"),
                "question": interview_response.get("question"),
                "video_url": interview_response.get("video_url"),
                "status": interview_response.get("status", "pending_review")
            }

            # Insert into interview_responses table
            response_id = self.mysql.insert_record("interview_responses", payload)
            
            logger.info(f"Video interview response saved for application {interview_response.get('application_id')}")
            return {"data": payload, "id": response_id}

        except Exception as e:
            logger.error(f"Save video interview response failed: {str(e)}")
            raise RuntimeError("Failed to save video interview response")

    def save_interview_response_text(
        self,
        application_id: str,
        question_id: str,
        response_text: str,
        candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a text response to an interview question.
        """
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "application_id": application_id,
                "question_id": question_id,
                "response_text": response_text,
                "responded_at": datetime.now(timezone.utc)
            }

            if candidate_id:
                payload["candidate_id"] = candidate_id

            response_id = self.mysql.insert_record("interview_responses", payload)
            
            logger.info(f"Interview response saved for application {application_id}")
            return {"data": payload, "id": response_id}

        except Exception as e:
            logger.error(f"Save interview response failed: {str(e)}")
            raise RuntimeError("Failed to save interview response")

    def get_interview_responses(self, application_id: str) -> List[Dict[str, Any]]:
        """
        Get all interview responses for a job application.
        """
        try:
            # First get all responses for this application
            responses = self.mysql.get_records(
                "interview_responses",
                {"application_id": application_id},
                order_by="responded_at ASC"
            )
            
            if not responses:
                return []
            
            # Get question details for each response
            question_ids = [r["question_id"] for r in responses]
            questions_map = {}
            
            if question_ids:
                questions = self.mysql.get_records("interview_questions", {"id": question_ids})
                questions_map = {q["id"]: q for q in questions}
            
            # Enrich responses with question text
            enriched_responses = []
            for response in responses:
                question = questions_map.get(response["question_id"])
                if question:
                    response["question_text"] = question.get("question_text", "")
                    response["question_type"] = question.get("question_type", "")
                enriched_responses.append(response)
            
            return enriched_responses

        except Exception as e:
            logger.error(f"Get interview responses failed: {str(e)}")
            return []
