"""
MySQL Service Layer - Complete data operations.
Custom authentication handles user management.
"""

import os
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Import database models in a way that works whether the app is run as a package (uvicorn backend.main:app)
# or from the backend folder (uvicorn main:app --app-dir backend).
# This also helps static analysis tools (like Pylance) resolve the module correctly.
import os
import sys

try:
    import backend.database as _database
except ModuleNotFoundError:
    # If running with --app-dir backend, the 'backend' package is not on sys.path.
    # Add the project root to sys.path so we can import it as a package.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import database as _database

# Export names used by the service layer
get_db_session = _database.get_db_session
User = _database.User
Company = _database.Company
RecruiterProfile = _database.RecruiterProfile
CandidateProfile = _database.CandidateProfile
Job = _database.Job
JobSkill = _database.JobSkill
InterviewQuestion = _database.InterviewQuestion
JobApplication = _database.JobApplication
VideoResponse = _database.VideoResponse
InterviewResponse = _database.InterviewResponse
CandidateVideo = _database.CandidateVideo
CandidateIntroResponse = _database.CandidateIntroResponse
Notification = _database.Notification
TrainingRegistration = _database.TrainingRegistration
CollegeTrainingRegistration = _database.CollegeTrainingRegistration
CorporateTrainingRegistration = _database.CorporateTrainingRegistration
TrainingAssessmentQuestion = _database.TrainingAssessmentQuestion
TrainingAssessmentResponse = _database.TrainingAssessmentResponse
TrainingAssessmentCompletion = _database.TrainingAssessmentCompletion
AdminUser = _database.AdminUser
PricingPlan = _database.PricingPlan
PricingAuditLog = _database.PricingAuditLog
UserSubscription = _database.UserSubscription
UserSubscriptionFeature = _database.UserSubscriptionFeature
UserSubscriptionHistory = _database.UserSubscriptionHistory
PremiumAssessmentResponse = _database.PremiumAssessmentResponse
PremiumAssessmentCompletion = _database.PremiumAssessmentCompletion
generate_uuid = _database.generate_uuid
# Reference tables for dropdowns
Department = _database.Department
Role = _database.Role
EmploymentType = _database.EmploymentType
Industry = _database.Industry
JobType = _database.JobType
EducationLevel = _database.EducationLevel
SalaryRange = _database.SalaryRange
ExperienceLevel = _database.ExperienceLevel

from utils_others.logger import logger


# Custom exceptions for better error handling
class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass

class DuplicateUserError(Exception):
    """Raised when trying to create a user that already exists."""
    pass

class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class MySQLService:
    """Base MySQL service class with common operations."""
    
    def __init__(self):
        self.session_factory = get_db_session

    def insert_record(self, table: str, data: Dict[str, Any]) -> str:
        """Insert a record into the specified table."""
        with self.session_factory() as db:
            try:
                # Get the model class based on table name
                model_map = {
                    'users': User,
                    'companies': Company,
                    'recruiter_profiles': RecruiterProfile,
                    'candidate_profiles': CandidateProfile,
                    'jobs': Job,
                    'job_skills': JobSkill,
                    'interview_questions': InterviewQuestion,
                    'job_applications': JobApplication,
                    'video_responses': VideoResponse,
                    'interview_responses': InterviewResponse,
                    'candidate_videos': CandidateVideo,
                    'candidate_intro_responses': CandidateIntroResponse,
                    'video_analysis': None,  # Handle with raw SQL
                    'notifications': Notification,
                    'training_registrations': TrainingRegistration,
                    'college_training_registrations': CollegeTrainingRegistration,
                    'corporate_training_registrations': CorporateTrainingRegistration,
                    'training_assessment_questions': TrainingAssessmentQuestion,
                    'training_assessment_responses': TrainingAssessmentResponse,
                    'training_assessment_completions': TrainingAssessmentCompletion,
                    'pricing_plans': PricingPlan,
                    'pricing_audit_log': PricingAuditLog,
                    'user_subscriptions': UserSubscription,
                    'user_subscription_features': UserSubscriptionFeature,
                    'user_subscription_history': UserSubscriptionHistory,
                    'admin_users': AdminUser,
                    'premium_assessment_responses': PremiumAssessmentResponse,
                    'premium_assessment_completions': PremiumAssessmentCompletion,
                }
                
                model_class = model_map.get(table)
                if not model_class:
                    raise ValueError(f"Unknown table: {table}")
                
                # Only include fields that actually exist in the model
                model_columns = {column.name for column in model_class.__table__.columns}
                filtered_data = {k: v for k, v in data.items() if k in model_columns}
                
                # Create instance
                instance = model_class(**filtered_data)
                db.add(instance)
                db.commit()
                db.refresh(instance)
                return str(instance.id)
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Database insert failed: {str(e)}")
                raise RuntimeError(f"Database insert failed: {str(e)}")

    def insert_records(self, table: str, records: List[Dict[str, Any]]) -> List[str]:
        """Bulk insert multiple records into the specified table."""
        if not records:
            return []

        with self.session_factory() as db:
            model_map = {
                'users': User,
                'companies': Company,
                'recruiter_profiles': RecruiterProfile,
                'candidate_profiles': CandidateProfile,
                'jobs': Job,
                'job_skills': JobSkill,
                'interview_questions': InterviewQuestion,
                'job_applications': JobApplication,
                'video_responses': VideoResponse,
                'interview_responses': InterviewResponse,
                'candidate_videos': CandidateVideo,
                'candidate_intro_responses': CandidateIntroResponse,
                'notifications': Notification,
                'training_registrations': TrainingRegistration,
                'college_training_registrations': CollegeTrainingRegistration,
                'corporate_training_registrations': CorporateTrainingRegistration,
                'pricing_plans': PricingPlan,
                'pricing_audit_log': PricingAuditLog,
                'user_subscriptions': UserSubscription,
                'user_subscription_features': UserSubscriptionFeature,
                'user_subscription_history': UserSubscriptionHistory,
                'admin_users': AdminUser,
                'premium_assessment_responses': PremiumAssessmentResponse,
                'premium_assessment_completions': PremiumAssessmentCompletion,
            }

            model_class = model_map.get(table)
            if not model_class:
                raise ValueError(f"Unknown table: {table}")

            model_columns = {column.name for column in model_class.__table__.columns}
            instances = []

            for record in records:
                filtered_data = {k: v for k, v in record.items() if k in model_columns}
                instances.append(model_class(**filtered_data))

            db.add_all(instances)
            db.commit()

            # Return ids for inserted records if available
            return [str(getattr(instance, 'id', '')) for instance in instances]

    def get_single_record(self, table: str, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get a single record from the specified table."""
        with self.session_factory() as db:
            model_map = {
                'users': User,
                'companies': Company,
                'recruiter_profiles': RecruiterProfile,
                'candidate_profiles': CandidateProfile,
                'jobs': Job,
                'job_skills': JobSkill,
                'interview_questions': InterviewQuestion,
                'job_applications': JobApplication,
                'video_responses': VideoResponse,
                'interview_responses': InterviewResponse,
                'candidate_videos': CandidateVideo,
                'candidate_intro_responses': CandidateIntroResponse,
                'notifications': Notification,
                'training_registrations': TrainingRegistration,
                'college_training_registrations': CollegeTrainingRegistration,
                'corporate_training_registrations': CorporateTrainingRegistration,
                'pricing_plans': PricingPlan,
                'pricing_audit_log': PricingAuditLog,
                'user_subscriptions': UserSubscription,
                'user_subscription_features': UserSubscriptionFeature,
                'user_subscription_history': UserSubscriptionHistory,
                'admin_users': AdminUser,
                # Reference tables for dropdowns
                'departments': Department,
                'roles': Role,
                'employment_types': EmploymentType,
                'industries': Industry,
                'job_types': JobType,
                'education_levels': EducationLevel,
                'salary_ranges': SalaryRange,
                'experience_levels': ExperienceLevel,
                'premium_assessment_responses': PremiumAssessmentResponse,
                'premium_assessment_completions': PremiumAssessmentCompletion,
            }
            
            model_class = model_map.get(table)
            if not model_class:
                raise ValueError(f"Unknown table: {table}")
            
            query = db.query(model_class)
            
            # Apply conditions
            for key, value in conditions.items():
                if isinstance(value, list):
                    query = query.filter(getattr(model_class, key).in_(value))
                else:
                    query = query.filter(getattr(model_class, key) == value)
            
            result = query.first()
            if not result:
                return None
            
            # Convert to dict - only include actual table columns
            return {
                column.name: getattr(result, column.name) 
                for column in result.__table__.columns
            }

    def get_records(self, table: str, conditions: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get multiple records from the specified table."""
        with self.session_factory() as db:
            model_map = {
                'users': User,
                'companies': Company,
                'recruiter_profiles': RecruiterProfile,
                'candidate_profiles': CandidateProfile,
                'jobs': Job,
                'job_skills': JobSkill,
                'interview_questions': InterviewQuestion,
                'job_applications': JobApplication,
                'video_responses': VideoResponse,
                'interview_responses': InterviewResponse,
                'candidate_videos': CandidateVideo,
                'candidate_intro_responses': CandidateIntroResponse,
                'notifications': Notification,
                'training_registrations': TrainingRegistration,
                'college_training_registrations': CollegeTrainingRegistration,
                'corporate_training_registrations': CorporateTrainingRegistration,
                'pricing_plans': PricingPlan,
                'pricing_audit_log': PricingAuditLog,
                'user_subscriptions': UserSubscription,
                'user_subscription_features': UserSubscriptionFeature,
                'user_subscription_history': UserSubscriptionHistory,
                'admin_users': AdminUser,
                # Reference tables for dropdowns
                'departments': Department,
                'roles': Role,
                'employment_types': EmploymentType,
                'industries': Industry,
                'job_types': JobType,
                'education_levels': EducationLevel,
                'salary_ranges': SalaryRange,
                'experience_levels': ExperienceLevel,
                'premium_assessment_responses': PremiumAssessmentResponse,
                'premium_assessment_completions': PremiumAssessmentCompletion,
            }
            
            model_class = model_map.get(table)
            if not model_class:
                raise ValueError(f"Unknown table: {table}")
            
            query = db.query(model_class)
            
            # Apply conditions
            if conditions:
                for key, value in conditions.items():
                    if isinstance(value, list):
                        query = query.filter(getattr(model_class, key).in_(value))
                    else:
                        query = query.filter(getattr(model_class, key) == value)
            
            # Apply ordering - handle multiple columns like "sort_order ASC, name ASC"
            if order_by:
                order_parts = order_by.split(',')
                for part in order_parts:
                    part = part.strip()
                    if part.endswith(' DESC'):
                        column = part.replace(' DESC', '').strip()
                        query = query.order_by(desc(getattr(model_class, column)))
                    else:
                        column = part.replace(' ASC', '').strip()
                        query = query.order_by(asc(getattr(model_class, column)))
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            # Convert to dict
            return [
                {column.name: getattr(result, column.name) for column in result.__table__.columns}
                for result in results
            ]

    def get_records_with_pagination(self, table: str, conditions: Dict[str, Any], order_by: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Get records with pagination."""
        return self.get_records(table, conditions, order_by, limit)

    def count_records(self, table: str, conditions: Optional[Dict[str, Any]] = None) -> int:
        """Count records in the specified table."""
        with self.session_factory() as db:
            model_map = {
                'users': User,
                'companies': Company,
                'recruiter_profiles': RecruiterProfile,
                'candidate_profiles': CandidateProfile,
                'jobs': Job,
                'job_skills': JobSkill,
                'interview_questions': InterviewQuestion,
                'job_applications': JobApplication,
                'video_responses': VideoResponse,
                'interview_responses': InterviewResponse,
                'candidate_videos': CandidateVideo,
                'candidate_intro_responses': CandidateIntroResponse,
                'notifications': Notification,
                'training_registrations': TrainingRegistration,
                'college_training_registrations': CollegeTrainingRegistration,
                'corporate_training_registrations': CorporateTrainingRegistration,
                'pricing_plans': PricingPlan,
                'pricing_audit_log': PricingAuditLog,
                'user_subscriptions': UserSubscription,
                'user_subscription_features': UserSubscriptionFeature,
                'user_subscription_history': UserSubscriptionHistory,
                'admin_users': AdminUser,
                'premium_assessment_responses': PremiumAssessmentResponse,
                'premium_assessment_completions': PremiumAssessmentCompletion,
            }

            model_class = model_map.get(table)
            if not model_class:
                raise ValueError(f"Unknown table: {table}")

            query = db.query(model_class)

            # Apply conditions
            if conditions:
                for key, value in conditions.items():
                    if isinstance(value, list):
                        query = query.filter(getattr(model_class, key).in_(value))
                    else:
                        query = query.filter(getattr(model_class, key) == value)

            return query.count()

    def update_record(self, table: str, update_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Update records in the specified table."""
        with self.session_factory() as db:
            model_map = {
                'users': User,
                'companies': Company,
                'recruiter_profiles': RecruiterProfile,
                'candidate_profiles': CandidateProfile,
                'jobs': Job,
                'job_skills': JobSkill,
                'interview_questions': InterviewQuestion,
                'job_applications': JobApplication,
                'video_responses': VideoResponse,
                'interview_responses': InterviewResponse,
                'candidate_videos': CandidateVideo,
                'candidate_intro_responses': CandidateIntroResponse,
                'notifications': Notification,
                'training_registrations': TrainingRegistration,
                'college_training_registrations': CollegeTrainingRegistration,
                'corporate_training_registrations': CorporateTrainingRegistration,
                'pricing_plans': PricingPlan,
                'pricing_audit_log': PricingAuditLog,
                'user_subscriptions': UserSubscription,
                'user_subscription_features': UserSubscriptionFeature,
                'user_subscription_history': UserSubscriptionHistory,
                'admin_users': AdminUser,
                'premium_assessment_responses': PremiumAssessmentResponse,
                'premium_assessment_completions': PremiumAssessmentCompletion,
            }

            model_class = model_map.get(table)
            if not model_class:
                raise ValueError(f"Unknown table: {table}")

            # Only include fields that actually exist in the model
            model_columns = {column.name for column in model_class.__table__.columns}
            filtered_data = {k: v for k, v in update_data.items() if k in model_columns}

            logger.info(f"Update record - table: {table}, model_columns: {model_columns}")
            logger.info(f"Update record - update_data: {update_data}")
            logger.info(f"Update record - filtered_data: {filtered_data}")

            query = db.query(model_class)

            # Apply conditions
            for key, value in conditions.items():
                query = query.filter(getattr(model_class, key) == value)

            # Update
            # NOTE: SQLAlchemy typings can be strict; ignore arg type mismatch in type checkers.
            updated = query.update(filtered_data)  # type: ignore[arg-type]
            db.commit()

            return updated > 0

    def delete_record(self, table: str, conditions: Dict[str, Any]) -> bool:
        """Delete records from the specified table matching all conditions."""
        with self.session_factory() as db:
            try:
                from sqlalchemy import text
                if not conditions:
                    raise ValueError("delete_record requires at least one condition")
                where_clause = " AND ".join([f"{col} = :{col}" for col in conditions])
                sql = f"DELETE FROM {table} WHERE {where_clause}"
                result = db.execute(text(sql), conditions)
                db.commit()
                return result.rowcount > 0
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"delete_record failed on {table}: {str(e)}")
                raise RuntimeError(f"Delete failed: {str(e)}")

    # Custom methods for video_analysis table (raw SQL since no model)
    def create_video_analysis(self, data: Dict[str, Any]) -> str:
        """Create a video analysis record."""
        with self.session_factory() as db:
            try:
                from sqlalchemy import text
                columns = ', '.join(data.keys())
                placeholders = ', '.join([f':{key}' for key in data.keys()])
                sql = f"INSERT INTO video_analysis ({columns}) VALUES ({placeholders})"
                
                result = db.execute(text(sql), data)
                db.commit()
                
                # Get the ID of inserted record
                id_result = db.execute(text("SELECT LAST_INSERT_ID()"))
                return str(id_result.scalar())
                
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Video analysis insert failed: {str(e)}")
                raise RuntimeError(f"Video analysis insert failed: {str(e)}")

    def get_video_analysis(self, conditions: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get video analysis record(s)."""
        with self.session_factory() as db:
            try:
                from sqlalchemy import text
                sql = "SELECT * FROM video_analysis"
                params = {}
                
                if conditions:
                    where_clauses = []
                    for key, value in conditions.items():
                        where_clauses.append(f"{key} = :{key}")
                        params[key] = value
                    sql += " WHERE " + " AND ".join(where_clauses)
                
                result = db.execute(text(sql), params).fetchone()
                if result:
                    # Convert to dict
                    columns = [desc[0] for desc in db.execute(text("DESCRIBE video_analysis")).fetchall()]
                    return {col: result[i] for i, col in enumerate(columns)}
                return None
                
            except SQLAlchemyError as e:
                logger.error(f"Video analysis query failed: {str(e)}")
                raise RuntimeError(f"Video analysis query failed: {str(e)}")

    def get_video_analyses(self, conditions: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get multiple video analysis records."""
        with self.session_factory() as db:
            try:
                from sqlalchemy import text
                sql = "SELECT * FROM video_analysis"
                params = {}
                
                if conditions:
                    where_clauses = []
                    for key, value in conditions.items():
                        where_clauses.append(f"{key} = :{key}")
                        params[key] = value
                    sql += " WHERE " + " AND ".join(where_clauses)
                
                results = db.execute(text(sql), params).fetchall()
                if results:
                    # Convert to list of dicts
                    columns = [desc[0] for desc in db.execute(text("DESCRIBE video_analysis")).fetchall()]
                    return [{col: row[i] for i, col in enumerate(columns)} for row in results]
                return []
                
            except SQLAlchemyError as e:
                logger.error(f"Video analysis query failed: {str(e)}")
                raise RuntimeError(f"Video analysis query failed: {str(e)}")

    def update_video_analysis(self, update_data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Update video analysis record."""
        with self.session_factory() as db:
            try:
                from sqlalchemy import text
                
                set_clauses = []
                params = {}
                
                for key, value in update_data.items():
                    set_clauses.append(f"{key} = :{key}")
                    params[key] = value
                
                where_clauses = []
                for key, value in conditions.items():
                    where_clauses.append(f"{key} = :{key}")
                    params[key] = value
                
                sql = f"UPDATE video_analysis SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
                
                result = db.execute(text(sql), params)
                db.commit()
                return result.rowcount > 0
                
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Video analysis update failed: {str(e)}")
                raise RuntimeError(f"Video analysis update failed: {str(e)}")

    def create_record(self, table: str, data: Dict[str, Any]) -> str:
        """Alias for insert_record for convenience."""
        return self.insert_record(table, data)


# ============================================================
# USER SERVICE
# ============================================================

class UserService(MySQLService):
    """Handles user operations with custom authentication."""

    def is_role_onboarded(self, user_id: str, role: str) -> bool:
        """Check whether the user has completed onboarding for the given role.

        Onboarding is per-role:
          - recruiter: requires a recruiter_profile linked to a company with a company_display_id.
          - candidate: requires the legacy users.onboarded flag AND an existing candidate_profile.

        The legacy ``users.onboarded`` column predates dual-role support and is shared across
        roles, so it cannot be used on its own to determine the onboarding state of a specific
        role.
        """
        if not user_id or not role:
            return False

        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            role_key = (role or "").lower()

            if role_key == "recruiter":
                profile = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == user_id).first()
                if not profile or not profile.company_id:
                    return False
                company = db.query(Company).filter(Company.id == profile.company_id).first()
                return bool(company and company.company_display_id)

            if role_key == "candidate":
                profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
                return bool(user.onboarded and profile)

            # Other roles (e.g. admin) fall back to the legacy flag
            return bool(user.onboarded)

    def _is_role_onboarded_in_session(self, db: Session, user: "User", role: str) -> bool:
        """Same logic as ``is_role_onboarded`` but reuses an existing SQLAlchemy session.

        Used internally by methods that already hold an open session (e.g.
        ``add_role_to_user``, ``switch_active_role``) to avoid opening a nested session
        on the same connection.
        """
        if not user or not role:
            return False

        role_key = (role or "").lower()

        if role_key == "recruiter":
            profile = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == user.id).first()
            if not profile or not profile.company_id:
                return False
            company = db.query(Company).filter(Company.id == profile.company_id).first()
            return bool(company and company.company_display_id)

        if role_key == "candidate":
            profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
            return bool(user.onboarded and profile)

        return bool(user.onboarded)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "roles": user.roles or [user.role],
                "location": user.location,
                "avatar_url": user.avatar_url,
                "onboarded": user.onboarded,
                "user_metadata": user.user_metadata
            }
    
    def create_user_from_auth(self, auth_user: Dict[str, Any]) -> Dict[str, Any]:
        """Create user from custom auth data."""
        user_id = auth_user.get("id")
        if not user_id:
            raise ValueError("User ID is required")
        
        with self.session_factory() as db:
            # Check if user exists
            existing_user = db.query(User).filter(User.id == user_id).first()
            
            if existing_user:
                # Update existing user
                existing_user.email = auth_user.get("email", existing_user.email)
                existing_user.full_name = auth_user.get("full_name", existing_user.full_name)
                existing_user.phone = auth_user.get("phone", existing_user.phone)
                existing_user.role = auth_user.get("role", existing_user.role)
                existing_user.location = auth_user.get("location", existing_user.location)
                existing_user.avatar_url = auth_user.get("avatar_url", existing_user.avatar_url)
                existing_user.user_metadata = auth_user.get("metadata", existing_user.user_metadata)
                existing_user.last_sign_in_at = datetime.now(timezone.utc)
                # Don't change onboarded flag on update - it's set manually
                db.commit()
                return {"id": existing_user.id, "action": "updated", "onboarded": existing_user.onboarded}
            else:
                # Create new user - default to not onboarded
                new_user = User(
                    id=user_id,
                    email=auth_user.get("email"),
                    full_name=auth_user.get("full_name"),
                    phone=auth_user.get("phone"),
                    role=auth_user.get("role", "candidate"),
                    location=auth_user.get("location"),
                    avatar_url=auth_user.get("avatar_url"),
                    user_metadata=auth_user.get("metadata"),
                    onboarded=False,
                    email_confirmed_at=datetime.now(timezone.utc) if auth_user.get("email_confirmed_at") else None
                )
                db.add(new_user)
                db.commit()
                return {"id": new_user.id, "action": "created", "onboarded": False}
    
    def mark_as_onboarded(self, user_id: str) -> bool:
        """Mark user as onboarded after completing profile."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.onboarded = True
            db.commit()
            return True
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "roles": user.roles or [user.role],
                "location": user.location,
                "avatar_url": user.avatar_url,
                "onboarded": user.onboarded,
                "email_verified": user.email_confirmed_at is not None,
                "user_metadata": user.user_metadata
            }
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "roles": user.roles or [user.role],
                "location": user.location,
                "avatar_url": user.avatar_url,
                "onboarded": user.onboarded,
                "email_verified": user.email_confirmed_at is not None,
                "user_metadata": user.user_metadata
            }
    
    def get_user_for_auth(self, login_id: str) -> Optional[Dict[str, Any]]:
        """Get user by email OR display_id (candidate_display_id/company_display_id) with password hash for authentication."""
        with self.session_factory() as db:
            # First try to find by email
            user = db.query(User).filter(User.email == login_id).first()
            
            # If not found by email, try to find by candidate_display_id
            if not user:
                # Check candidate_profiles for candidate_display_id
                from sqlalchemy import or_
                candidate_profile = db.query(CandidateProfile).filter(
                    CandidateProfile.candidate_display_id == login_id.upper()
                ).first()
                if candidate_profile:
                    user = db.query(User).filter(User.id == candidate_profile.user_id).first()
            
            # If still not found, try to find by company_display_id via recruiter_profiles
            if not user:
                # Join recruiter_profiles with companies to find by company_display_id
                from sqlalchemy import join
                recruiter_profile = db.query(RecruiterProfile).join(
                    Company, RecruiterProfile.company_id == Company.id
                ).filter(
                    Company.company_display_id == login_id.upper()
                ).first()
                if recruiter_profile:
                    user = db.query(User).filter(User.id == recruiter_profile.user_id).first()
            
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "roles": user.roles or [user.role],  # Default to single role array if not set
                "location": user.location,
                "avatar_url": user.avatar_url,
                "onboarded": user.onboarded,
                "email_verified": user.email_confirmed_at is not None,
                "password": user.password_hash,  # Include password hash for verification only
                "user_metadata": user.user_metadata
            }
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user in the database."""
        # Validate required fields
        required_fields = ["email", "full_name", "phone", "password"]
        for field in required_fields:
            if not user_data.get(field):
                raise ValidationError(f"Missing required field: {field}")
        
        with self.session_factory() as db:
            try:
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == user_data["email"]).first()
                if existing_user:
                    raise DuplicateUserError(f"User with email {user_data['email']} already exists")
                
                user_role = user_data.get("role", "candidate")
                new_user = User(
                    id=user_data.get("id", generate_uuid()),
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    phone=user_data.get("phone"),
                    role=user_role,
                    roles=[user_role],  # Initialize roles array with the primary role
                    location=user_data.get("location"),
                    avatar_url=user_data.get("avatar_url"),
                    password_hash=user_data.get("password"),  # Store hashed password
                    onboarded=user_data.get("onboarded", False),
                    email_confirmed_at=datetime.now(timezone.utc) if user_data.get("email_verified") else None,
                    user_metadata=user_data.get("user_metadata", {}),
                    extra_metadata=user_data.get("metadata", {}),
                    created_at=datetime.now(timezone.utc)
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                return {
                    "id": new_user.id,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "phone": new_user.phone,
                    "role": new_user.role,
                    "roles": new_user.roles or [new_user.role],
                    "location": new_user.location,
                    "avatar_url": new_user.avatar_url,
                    "onboarded": new_user.onboarded,
                    "email_confirmed_at": new_user.email_confirmed_at,
                    "user_metadata": new_user.user_metadata,
                    "created_at": new_user.created_at,
                    "updated_at": new_user.updated_at,
                    "last_sign_in_at": new_user.last_sign_in_at
                }
                
            except IntegrityError as e:
                db.rollback()
                logger.error(f"Integrity error creating user: {str(e)}")
                raise DuplicateUserError("User already exists")
            except SQLAlchemyError as e:
                db.rollback()
                logger.error(f"Database error creating user: {str(e)}")
                raise DatabaseError("Failed to create user")
            except Exception as e:
                db.rollback()
                logger.error(f"Unexpected error creating user: {str(e)}")
                raise DatabaseError("Failed to create user")
    
    def update_user_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user password."""
        with self.session_factory() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.password_hash = hashed_password
                user.updated_at = datetime.now(timezone.utc)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to update user password: {str(e)}")
                return False

    def add_role_to_user(self, user_id: str, new_role: str) -> Optional[Dict[str, Any]]:
        """Add a role to an existing user's roles array. Returns updated user data or None.

        The returned ``onboarded`` reflects the *new active role* (i.e. the role just added),
        so the caller can route the user to the correct onboarding flow when they have not
        yet completed onboarding for the newly-added role.
        """
        with self.session_factory() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None

                current_roles = user.roles or [user.role]
                logger.info(f"Before update - User: {user_id}, Current roles: {current_roles}, New role: {new_role}")
                
                if new_role not in current_roles:
                    # Create a new list instead of mutating the existing one to ensure SQLAlchemy detects the change
                    updated_roles = current_roles + [new_role]
                    logger.info(f"After append - Updated roles: {updated_roles}")
                    
                    # Update both roles and active role
                    user.roles = updated_roles
                    user.role = new_role
                    user.updated_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Before commit - user.roles: {user.roles}, type: {type(user.roles)}")
                    
                    # Explicitly mark the object as dirty for SQLAlchemy
                    db.add(user)
                    db.commit()
                    logger.info(f"After commit - user.roles: {user.roles}")
                    
                    # Get fresh data from database
                    db.refresh(user)
                    logger.info(f"After refresh - user.roles: {user.roles}")

                active_role_onboarded = self._is_role_onboarded_in_session(db, user, user.role)

                return {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "role": user.role,
                    "roles": user.roles or [user.role],
                    "location": user.location,
                    "avatar_url": user.avatar_url,
                    "onboarded": active_role_onboarded,
                    "email_verified": user.email_confirmed_at is not None,
                    "user_metadata": user.user_metadata
                }
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to add role to user: {str(e)}")
                return None

    def switch_active_role(self, user_id: str, active_role: str) -> Optional[Dict[str, Any]]:
        """Switch the active role for a user. Returns updated user data or None.

        The returned ``onboarded`` reflects the new active role so the caller can route the
        user appropriately when the target role has not yet been onboarded.
        """
        with self.session_factory() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None

                current_roles = user.roles or [user.role]
                if active_role not in current_roles:
                    logger.warning(f"User {user_id} does not have role {active_role}")
                    return None

                user.role = active_role
                user.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(user)

                active_role_onboarded = self._is_role_onboarded_in_session(db, user, user.role)

                return {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "role": user.role,
                    "roles": user.roles or [user.role],
                    "location": user.location,
                    "avatar_url": user.avatar_url,
                    "onboarded": active_role_onboarded,
                    "email_verified": user.email_confirmed_at is not None,
                    "user_metadata": user.user_metadata
                }
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to switch active role: {str(e)}")
                return None
    
    def update_user_email_confirmed(self, user_id: str) -> bool:
        """Mark user email as confirmed."""
        with self.session_factory() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.email_confirmed_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to update email confirmation: {str(e)}")
                return False
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        with self.session_factory() as db:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.last_sign_in_at = datetime.now(timezone.utc)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to update last login: {str(e)}")
                return False


# ============================================================
# RECRUITER SERVICE
# ============================================================

class RecruiterService(MySQLService):
    """Handles recruiter operations."""
    
    def create_company(self, name: str, created_by: str, description: Optional[str] = None, website: Optional[str] = None) -> Dict[str, Any]:
        """Create a new company."""
        with self.session_factory() as db:
            company = Company(
                id=generate_uuid(),
                name=name,
                description=description,
                website=website,
                created_by=created_by
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            
            return {
                "company_id": company.id,
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "description": company.description,
                    "website": company.website
                }
            }
    
    def list_companies(self) -> List[Dict[str, Any]]:
        """List all companies."""
        with self.session_factory() as db:
            companies = db.query(Company).order_by(Company.name).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "website": c.website,
                    "created_by": c.created_by
                }
                for c in companies
            ]
    
    def upsert_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update recruiter profile."""
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
        
        # Separate user data from profile data - only include valid RecruiterProfile fields
        user_fields = ["avatar_url"]
        profile_fields = ["company_id", "contact_name", "contact_email", "location", "company_description"]
        company_fields = ["company_name", "company_website", "company_description"]
        
        user_data = {k: v for k, v in payload.items() if k in user_fields}
        profile_data = {k: v for k, v in payload.items() if k in profile_fields}
        company_data = {k: v for k, v in payload.items() if k in company_fields and v is not None}
        
        with self.session_factory() as db:
            # Update user table if needed (for avatar_url)
            if user_data:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    for key, value in user_data.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
            
            # Check if recruiter profile exists
            existing_profile = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == user_id).first()
            
            # Handle company creation/update
            company_id = None
            if company_data:
                if existing_profile and existing_profile.company_id:
                    # Update existing company
                    company = db.query(Company).filter(Company.id == existing_profile.company_id).first()
                    if company:
                        if "company_name" in company_data:
                            company.name = company_data["company_name"]
                        if "company_website" in company_data:
                            company.website = company_data["company_website"]
                        if "company_description" in company_data:
                            company.description = company_data["company_description"]
                        company_id = company.id
                else:
                    # Create new company only when a name is provided.
                    # Prevent placeholder companies such as "Unknown Company" being created by default.
                    company_name = (company_data.get("company_name") or "").strip()
                    if company_name:
                        company = Company(
                            id=generate_uuid(),
                            name=company_name,
                            website=company_data.get("company_website"),
                            description=company_data.get("company_description"),
                            created_by=user_id
                        )
                        db.add(company)
                        db.flush()  # Get the ID
                        company_id = company.id
                    else:
                        company_id = None
            
            if existing_profile:
                # Update existing profile
                for key, value in profile_data.items():
                    if hasattr(existing_profile, key):
                        setattr(existing_profile, key, value)
                # Update company_id if we created/updated a company
                if company_id:
                    existing_profile.company_id = company_id
                db.commit()
                db.refresh(existing_profile)
                return {"id": existing_profile.id, "action": "updated"}
            else:
                # Create new profile
                profile = RecruiterProfile(
                    id=generate_uuid(),
                    user_id=user_id,
                    company_id=company_id,
                    **profile_data
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)
                return {"id": profile.id, "action": "created"}
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get recruiter profile."""
        with self.session_factory() as db:
            # Get profile and user data
            profile = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == user_id).first()
            user = db.query(User).filter(User.id == user_id).first()
            if not profile or not user:
                return None
            
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "company_id": profile.company_id,
                "company_name": profile.company_name,
                "company_website": profile.company_website,
                "contact_name": profile.contact_name,
                "contact_email": profile.contact_email,
                "location": profile.location,
                "about": profile.about,
                "avatar_url": user.avatar_url
            }
    
    def post_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Post a new job."""
        with self.session_factory() as db:
            job = Job(
                id=generate_uuid(),
                title=job_data.get("title"),
                description=job_data.get("description"),
                requirements=job_data.get("requirements"),
                location=job_data.get("location"),
                job_type=job_data.get("job_type"),
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                currency=job_data.get("currency", "INR"),
                is_remote=job_data.get("is_remote", False),
                status=job_data.get("status", "active"),
                company_id=job_data.get("company_id"),
                created_by=job_data.get("created_by")
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            return {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "created_at": job.created_at.isoformat()
            }
    
    def list_jobs(self, recruiter_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List jobs posted by recruiter."""
        with self.session_factory() as db:
            offset = (page - 1) * page_size
            
            # Get total count
            total = db.query(func.count(Job.id)).filter(Job.created_by == recruiter_id).scalar()
            
            # Get jobs with pagination
            jobs = db.query(Job).filter(Job.created_by == recruiter_id)\
                .order_by(desc(Job.created_at))\
                .offset(offset)\
                .limit(page_size)\
                .all()
            
            return {
                "jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "status": job.status,
                        "created_at": job.created_at.isoformat(),
                        "location": job.location,
                        "job_type": job.job_type
                    }
                    for job in jobs
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total or 0
                }
            }
    
    def get_job(self, job_id: str, recruiter_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get job details."""
        with self.session_factory() as db:
            query = db.query(Job).filter(Job.id == job_id)
            
            if recruiter_id:
                query = query.filter(Job.created_by == recruiter_id)
            
            job = query.first()
            if not job:
                return None
            
            # Resolve country ID to name if stored as numeric ID
            country_name = None
            if job.location_country:
                try:
                    country_id = int(job.location_country)
                    from sqlalchemy import text
                    result = db.execute(text("SELECT name FROM countries WHERE id = :id"), {"id": country_id})
                    row = result.first()
                    if row:
                        country_name = row[0]
                except (ValueError, Exception):
                    country_name = job.location_country
            
            # Build location string with resolved country name
            location_display = job.location
            if job.is_remote:
                location_display = "Remote"
            elif job.location_city or job.location_state or country_name:
                location_parts = [job.location_city, job.location_state, country_name]
                location_display = ", ".join([p for p in location_parts if p])
            
            return {
                "id": job.id,
                "job_title": job.job_title,
                "title": job.job_title,
                "description": job.description,
                "requirements": job.requirements,
                "location": location_display,
                "location_city": job.location_city,
                "location_state": job.location_state,
                "location_country": country_name or job.location_country,
                "job_type": job.job_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "is_remote": job.is_remote,
                "status": job.status,
                "company_id": job.company_id,
                "created_by": job.created_by,
                "created_at": job.created_at.isoformat()
            }
    
    def update_job(self, job_id: str, update_data: Dict[str, Any], recruiter_id: str) -> Optional[Dict[str, Any]]:
        """Update job."""
        with self.session_factory() as db:
            job = db.query(Job).filter(
                and_(Job.id == job_id, Job.created_by == recruiter_id)
            ).first()
            
            if not job:
                return None
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            db.commit()
            db.refresh(job)
            
            return {
                "id": job.id,
                "title": job.title,
                "status": job.status,
                "updated_at": job.updated_at.isoformat()
            }
    
    def delete_job(self, job_id: str, recruiter_id: str) -> bool:
        """Delete job."""
        with self.session_factory() as db:
            job = db.query(Job).filter(
                and_(Job.id == job_id, Job.created_by == recruiter_id)
            ).first()
            
            if not job:
                return False
            
            db.delete(job)
            db.commit()
            return True
    
    def get_recruiter_applications(self, recruiter_id: str, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get applications for recruiter's jobs."""
        with self.session_factory() as db:
            # Get jobs created by this recruiter
            jobs_query = db.query(Job.id, Job.job_title).filter(Job.created_by == recruiter_id)
            
            if job_id:
                jobs_query = jobs_query.filter(Job.id == job_id)
            
            jobs = jobs_query.all()
            if not jobs:
                return []
            
            job_ids = [j.id for j in jobs]
            job_map = {j.id: j.title for j in jobs}
            
            # Get applications for these jobs
            applications_query = db.query(JobApplication).filter(JobApplication.job_id.in_(job_ids))
            
            if not job_id:
                applications_query = applications_query.limit(100)
            
            applications = applications_query.order_by(desc(JobApplication.applied_at)).all()
            
            # Get candidate info
            candidate_ids = list(set(app.candidate_id for app in applications))
            candidates = {}
            
            if candidate_ids:
                users = db.query(User.id, User.full_name, User.email, User.phone)\
                    .filter(User.id.in_(candidate_ids)).all()
                candidates = {u.id: {
                    "name": u.full_name or u.email or "Candidate",
                    "email": u.email,
                    "phone": u.phone
                } for u in users}
            
            # Format results
            results = []
            for app in applications:
                candidate_info = candidates.get(app.candidate_id, {})
                results.append({
                    "id": app.id,
                    "job_id": app.job_id,
                    "candidate_id": app.candidate_id,
                    "job_title": job_map.get(app.job_id, "Unknown Job"),
                    "candidate_name": candidate_info.get("name", "Unknown Candidate"),
                    "candidate_email": candidate_info.get("email"),
                    "candidate_phone": candidate_info.get("phone"),
                    "status": app.status,
                    "applied_at": app.applied_at.isoformat(),
                    "intro_video_url": app.intro_video_url
                })
            
            return results


# ============================================================
# CANDIDATE SERVICE
# ============================================================

class CandidateService(MySQLService):
    """Handles candidate operations."""
    
    def upsert_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update candidate profile."""
        # Separate data for different tables
        # Hybrid approach: keep avatar_url on users for backwards compatibility,
        # but also persist it on candidate_profiles for candidate-centric media.
        user_fields = ["full_name", "phone", "location", "avatar_url"]
        profile_fields = [
            "summary", "avatar_url", "resume_url", "intro_video_url",
            "linkedin_url", "portfolio_url", "skills", "experience_years",
            "preferred_job_type", "expected_salary", "languages", 
            "willing_to_relocate", "availability",
            # New personal details
            "date_of_birth", "gender", "marital_status",
            # Current address
            "current_address", "current_city", "current_state", "current_country",
            # Permanent address
            "permanent_address", "permanent_city", "permanent_state", "permanent_country",
            # Professional details
            "current_salary", "notice_period_days", "highest_qualification",
            # Social/Projects
            "personal_projects", "personal_blogs",
            # Education details
            "schooling", "schooling_year", "schooling_percentage",
            "pre_university", "pre_university_year", "pre_university_percentage",
            "graduation", "graduation_year", "graduation_percentage",
            "post_graduation", "post_graduation_year", "post_graduation_percentage",
            # Skills & Languages
            "spoken_languages", "certifications",
            # Current/Latest Experience
            "current_company", "current_designation", "current_doj", "current_dol"
        ]
        separate_tables = ["experience", "education"]
        
        # Filter data for each table
        user_data = {k: v for k, v in data.items() if k in user_fields}
        profile_data = {k: v for k, v in data.items() if k in profile_fields}
        experience_data = data.get("experience", [])
        education_data = data.get("education", [])
        
        with self.session_factory() as db:
            # Update user table if needed
            if user_data:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    for key, value in user_data.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
            
            # Get or create profile first (needed for experience/education FK)
            existing_profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
            
            if not existing_profile:
                # Create new profile if doesn't exist
                existing_profile = CandidateProfile(
                    id=generate_uuid(),
                    user_id=user_id
                )
                db.add(existing_profile)
                db.flush()  # Get the ID without committing
                
                # Generate candidate_display_id for new profiles
                user = db.query(User).filter(User.id == user_id).first()
                location = user.location if user else ""
                prefix = "".join([c for c in (location or "") if c.isalnum()]).upper()[:3]
                if not prefix:
                    prefix = "LOC"
                import uuid
                import random
                hex_part = uuid.uuid4().hex[:7]
                numeric_suffix = str(int(hex_part, 16))[:7].zfill(7)
                existing_profile.candidate_display_id = f"{prefix}{numeric_suffix}"
            else:
                # Check if existing profile needs candidate_display_id
                if not existing_profile.candidate_display_id:
                    user = db.query(User).filter(User.id == user_id).first()
                    location = user.location if user else ""
                    prefix = "".join([c for c in (location or "") if c.isalnum()]).upper()[:3]
                    if not prefix:
                        prefix = "LOC"
                    import uuid
                    import random
                    hex_part = uuid.uuid4().hex[:7]
                    numeric_suffix = str(int(hex_part, 16))[:7].zfill(7)
                    existing_profile.candidate_display_id = f"{prefix}{numeric_suffix}"
            
            profile_id = existing_profile.id  # This is the FK for experience/education
            
            # Handle experience - store as JSON
            if experience_data:
                existing_profile.experience = experience_data
            
            # Handle education - store as JSON
            if education_data:
                existing_profile.education = education_data
            
            # Update candidate profile fields
            for key, value in profile_data.items():
                if hasattr(existing_profile, key):
                    setattr(existing_profile, key, value)

            # Ensure candidate_videos table stays in sync when intro_video_url is updated
            if "intro_video_url" in profile_data:
                intro_url = profile_data.get("intro_video_url")
                existing_intro = db.query(CandidateVideo).filter(CandidateVideo.candidate_id == user_id, CandidateVideo.video_type == "intro").first()
                if intro_url:
                    if existing_intro:
                        existing_intro.video_url = intro_url
                        existing_intro.created_at = datetime.utcnow()
                    else:
                        intro_record = CandidateVideo(
                            id=generate_uuid(),
                            candidate_id=user_id,
                            video_type="intro",
                            video_url=intro_url,
                            video_path=intro_url.split("/")[-1] if "/" in intro_url else "intro_video.webm",
                            created_at=datetime.utcnow()
                        )
                        db.add(intro_record)
                else:
                    # Remove intro video record if URL is cleared
                    if existing_intro:
                        db.delete(existing_intro)

            db.commit()
            db.refresh(existing_profile)
            return {"id": existing_profile.id, "action": "updated" if existing_profile else "created"}
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get candidate profile - combines user data + profile data."""
        with self.session_factory() as db:
            # Get user data (full_name, email, phone from users table)
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Debug logging
            
            # Get profile data (extended fields from candidate_profiles)
            profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
            
            # Get experience + education data from JSON fields
            experience = []
            education = []
            if profile:
                # Read from JSON fields instead of separate tables
                experience = profile.experience if profile.experience else []
                education = profile.education if profile.education else []
            
            # Combine user + profile data
            # If the candidate profile does not have an intro_video_url (legacy data),
            # fallback to the latest entry from the candidate_videos table.
            intro_video_url = profile.intro_video_url if profile else None
            if not intro_video_url:
                latest_intro = db.query(CandidateVideo).filter(CandidateVideo.candidate_id == user_id, CandidateVideo.video_type == "intro").order_by(desc(CandidateVideo.created_at)).first()
                if latest_intro:
                    intro_video_url = latest_intro.video_url

            # Avatar URL is now only in users table
            resolved_avatar_url = user.avatar_url

            result = {
                "id": user.id,
                "user_id": user.id,
                "full_name": user.full_name,  # From users table
                "email": user.email,  # From users table
                "phone": user.phone,  # From users table only
                "location": user.location,  # From users table only
                "summary": profile.summary if profile else None,
                "avatar_url": resolved_avatar_url,
                "resume_url": profile.resume_url if profile else None,
                "intro_video_url": intro_video_url,
                "linkedin_url": profile.linkedin_url if profile else None,
                "portfolio_url": profile.portfolio_url if profile else None,
                "skills": profile.skills if profile else [],
                "experience_years": profile.experience_years if profile else None,
                "experience": experience,  # Add experience data
                "education": education,    # Add education data
                "onboarded": user.onboarded,
                "candidate_display_id": profile.candidate_display_id if profile else None,
                # New personal details
                "date_of_birth": profile.date_of_birth if profile else None,
                "gender": profile.gender if profile else None,
                "marital_status": profile.marital_status if profile else None,
                # Current address
                "current_address": profile.current_address if profile else None,
                "current_city": profile.current_city if profile else None,
                "current_state": profile.current_state if profile else None,
                "current_country": profile.current_country if profile else None,
                # Permanent address
                "permanent_address": profile.permanent_address if profile else None,
                "permanent_city": profile.permanent_city if profile else None,
                "permanent_state": profile.permanent_state if profile else None,
                "permanent_country": profile.permanent_country if profile else None,
                # Professional details
                "current_salary": profile.current_salary if profile else None,
                "expected_salary": profile.expected_salary if profile else None,
                "notice_period_days": profile.notice_period_days if profile else None,
                "highest_qualification": profile.highest_qualification if profile else None,
                # Social/Projects
                "personal_projects": profile.personal_projects if profile else None,
                "personal_blogs": profile.personal_blogs if profile else None,
                # Education details
                "schooling": profile.schooling if profile else None,
                "schooling_year": profile.schooling_year if profile else None,
                "schooling_percentage": profile.schooling_percentage if profile else None,
                "pre_university": profile.pre_university if profile else None,
                "pre_university_year": profile.pre_university_year if profile else None,
                "pre_university_percentage": profile.pre_university_percentage if profile else None,
                "graduation": profile.graduation if profile else None,
                "graduation_year": profile.graduation_year if profile else None,
                "graduation_percentage": profile.graduation_percentage if profile else None,
                "post_graduation": profile.post_graduation if profile else None,
                "post_graduation_year": profile.post_graduation_year if profile else None,
                "post_graduation_percentage": profile.post_graduation_percentage if profile else None,
                # Skills & Languages
                "spoken_languages": profile.spoken_languages if profile else None,
                "certifications": profile.certifications if profile else None,
                # Current/Latest Experience
                "current_company": profile.current_company if profile else None,
                "current_designation": profile.current_designation if profile else None,
                "current_doj": profile.current_doj if profile else None,
                "current_dol": profile.current_dol if profile else None
            }
            
            return result
    
    def save_education(self, candidate_id: str, education_list: List[Dict[str, Any]]) -> bool:
        """Save candidate education to JSON field in candidate_profiles."""
        with self.session_factory() as db:
            # Find or create the candidate profile
            profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == candidate_id).first()
            if not profile:
                # If no profile exists, create one so we can store education
                profile = CandidateProfile(id=generate_uuid(), user_id=candidate_id)
                db.add(profile)
                db.flush()

            # Update education JSON field
            profile.education = education_list if education_list else []
            
            db.commit()
            return True
    
    def save_experience(self, candidate_id: str, experience_list: List[Dict[str, Any]]) -> bool:
        """Save candidate experience to JSON field in candidate_profiles."""
        with self.session_factory() as db:
            # Find or create the candidate profile
            profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == candidate_id).first()
            if not profile:
                # If no profile exists, create one so we can store experience
                profile = CandidateProfile(id=generate_uuid(), user_id=candidate_id)
                db.add(profile)
                db.flush()

            # Update experience JSON field
            profile.experience = experience_list if experience_list else []
            
            db.commit()
            return True
    
    def submit_application(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit job application."""
        with self.session_factory() as db:
            # Check if already applied
            existing = db.query(JobApplication).filter(
                and_(JobApplication.job_id == data["job_id"], JobApplication.candidate_id == data["candidate_id"])
            ).first()
            
            if existing:
                raise ValueError("Already applied for this job")
            
            application = JobApplication(
                id=generate_uuid(),
                job_id=data["job_id"],
                candidate_id=data["candidate_id"],
                cover_letter=data.get("cover_letter"),
                intro_video_url=data.get("intro_video_url"),
                resume_url=data.get("resume_url"),
                custom_answers=data.get("custom_answers"),
                status="pending"
            )
            
            db.add(application)
            db.commit()
            db.refresh(application)
            
            return {
                "id": application.id,
                "job_id": application.job_id,
                "candidate_id": application.candidate_id,
                "status": application.status,
                "applied_at": application.applied_at.isoformat()
            }
    
    def check_application_status(self, job_id: str, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Check if candidate has applied for job."""
        with self.session_factory() as db:
            application = db.query(JobApplication).filter(
                and_(JobApplication.job_id == job_id, JobApplication.candidate_id == candidate_id)
            ).first()
            
            if not application:
                return None
            
            return {
                "applied": True,
                "status": application.status,
                "applied_at": application.applied_at.isoformat()
            }
    
    def get_candidate_applications(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Get all applications by candidate."""
        with self.session_factory() as db:
            applications = db.query(JobApplication).filter(JobApplication.candidate_id == candidate_id)\
                .order_by(desc(JobApplication.applied_at)).all()
            
            job_ids = [app.job_id for app in applications]
            application_ids = [app.id for app in applications]  # Get all application IDs
            jobs = {}
            
            if job_ids:
                job_list = db.query(Job.id, Job.job_title, Job.location, Job.job_type, Job.company_id)\
                    .filter(Job.id.in_(job_ids)).all()
                jobs = {j.id: {
                    "title": j.job_title,
                    "location": j.location,
                    "job_type": j.job_type,
                    "company_id": j.company_id
                } for j in job_list}
            
            # Get company names from companies table
            company_ids = list(set(job.get("company_id") for job in jobs.values() if job.get("company_id")))
            companies = {}
            if company_ids:
                company_list = db.query(Company.id, Company.name)\
                    .filter(Company.id.in_(company_ids)).all()
                companies = {c.id: c.name for c in company_list}
            
            # Get interview responses for all applications
            interview_response_map = {}
            if application_ids:
                try:
                    interview_responses = db.query(VideoResponse).filter(
                        VideoResponse.application_id.in_(application_ids)
                    ).all()
                    for response in interview_responses:
                        app_id = response.application_id
                        if app_id not in interview_response_map:
                            interview_response_map[app_id] = []
                        interview_response_map[app_id].append({
                            "question": response.question,
                            "video_url": response.video_url,
                            "video_path": response.video_path,
                            "question_index": response.question_index,
                            "duration": response.duration,
                            "transcript": response.transcript,
                            "created_at": response.created_at.isoformat() if response.created_at else None
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch interview responses: {str(e)}")
            
            results = []
            for app in applications:
                job_info = jobs.get(app.job_id, {})
                company_id = job_info.get("company_id")
                company_name = companies.get(company_id, "Hiring Company")
                
                app_data = {
                    "id": app.id,
                    "job_id": app.job_id,
                    "status": app.status,
                    "feedback": app.feedback,  # Include recruiter feedback
                    "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                    "job_title": job_info.get("title"),
                    "location": job_info.get("location"),
                    "job_type": job_info.get("job_type"),
                    "company_name": company_name
                }
                
                # Add interview responses if available
                interview_videos = interview_response_map.get(app.id, [])
                if interview_videos:
                    app_data["interview_responses"] = interview_videos
                    app_data["interview_video_count"] = len(interview_videos)
                    app_data["interview_video_urls"] = [v.get("video_url") for v in interview_videos if v.get("video_url")]
                
                results.append(app_data)
            
            return results
# ============================================================
# DASHBOARD SERVICE
# ============================================================

class DashboardService(MySQLService):
    """Handles dashboard operations for both roles."""
    
    def get_summary(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard summary."""
        with self.session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"role": None, "stats": {}, "jobs": [], "applications": []}
            
            role = user.role
            
            if role == "recruiter":
                return self._get_recruiter_summary(user_id, db)
            elif role == "candidate":
                return self._get_candidate_summary(user_id, db)
            else:
                return {"role": None, "stats": {}, "jobs": [], "applications": []}
    
    def _get_recruiter_summary(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Get recruiter dashboard summary."""
        # Get jobs
        jobs = db.query(Job).filter(Job.created_by == user_id)\
            .order_by(desc(Job.created_at)).all()
        
        job_ids = [j.id for j in jobs]
        
        # Get application counts per job
        app_counts = {}
        if job_ids:
            from sqlalchemy import func
            counts_query = db.query(JobApplication.job_id, func.count(JobApplication.id))\
                .filter(JobApplication.job_id.in_(job_ids))\
                .group_by(JobApplication.job_id).all()
            app_counts = {row[0]: row[1] for row in counts_query}
        
        # Get skills for jobs
        job_skills = {}
        if job_ids:
            skills_list = db.query(JobSkill.job_id, JobSkill.skill_name)\
                .filter(JobSkill.job_id.in_(job_ids)).all()
            for skill in skills_list:
                if skill.job_id not in job_skills:
                    job_skills[skill.job_id] = []
                job_skills[skill.job_id].append(skill.skill_name)
        
        # Get applications for these jobs
        applications = []
        if job_ids:
            apps = db.query(JobApplication).filter(JobApplication.job_id.in_(job_ids))\
                .order_by(desc(JobApplication.applied_at)).all()
            applications = [
                {
                    "id": app.id,
                    "job_id": app.job_id,
                    "status": app.status,
                    "applied_at": app.applied_at.isoformat()
                }
                for app in apps
            ]
        
        # Resolve job_type IDs to names
        job_type_ids = list(set(j.job_type for j in jobs if j.job_type))
        job_type_names = {}
        if job_type_ids:
            jt_list = db.query(JobType.id, JobType.name).filter(JobType.id.in_(job_type_ids)).all()
            job_type_names = {jt.id: jt.name for jt in jt_list}
        
        # Calculate stats
        stats = {
            "total_jobs": len(jobs),
            "active_jobs": sum(1 for j in jobs if j.status == "active"),
            "closed_jobs": sum(1 for j in jobs if j.status == "closed"),
            "total_applications": len(applications),
            "shortlisted": sum(1 for a in applications if a["status"] == "shortlisted"),
            "interviews": sum(1 for a in applications if a["status"] == "interview_scheduled"),
            "hired": sum(1 for a in applications if a["status"] == "hired")
        }
        
        return {
            "role": "recruiter",
            "stats": stats,
            "jobs": [
                {
                    "id": j.id,
                    "job_title": j.job_title,
                    "title": j.job_title,
                    "status": j.status,
                    "created_at": j.created_at.isoformat(),
                    "location": j.location,
                    "job_type": job_type_names.get(j.job_type) or j.job_type,
                    "work_mode": "Remote" if j.is_remote else "On-site",
                    "salary_min": j.salary_min,
                    "salary_max": j.salary_max,
                    "currency": j.currency,
                    "experience_min": j.experience_min,
                    "experience_max": j.experience_max,
                    "applications_count": app_counts.get(j.id, 0),
                    "views": 0,  # Views tracking not implemented yet
                    "skills": job_skills.get(j.id, [])
                }
                for j in jobs
            ],
            "applications": applications
        }
    
    def _get_candidate_summary(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Get candidate dashboard summary."""
        # Get applications
        applications = db.query(JobApplication).filter(JobApplication.candidate_id == user_id)\
            .order_by(desc(JobApplication.applied_at)).all()
        
        job_ids = [app.job_id for app in applications]
        jobs = {}
        
        if job_ids:
            job_list = db.query(Job.id, Job.job_title, Job.location, Job.job_type)\
                .filter(Job.id.in_(job_ids)).all()
            jobs = {j.id: {
                "title": j.job_title,
                "location": j.location,
                "job_type": j.job_type
            } for j in job_list}
        
        # Format applications with job info
        formatted_apps = []
        for app in applications:
            job_info = jobs.get(app.job_id, {})
            formatted_apps.append({
                "id": app.id,
                "job_id": app.job_id,
                "status": app.status,
                "applied_at": app.applied_at.isoformat(),
                "job_title": job_info.get("title"),
                "location": job_info.get("location"),
                "job_type": job_info.get("job_type")
            })
        
        # Calculate stats
        stats = {
            "total_applications": len(formatted_apps),
            "shortlisted": sum(1 for a in formatted_apps if a["status"] == "shortlisted"),
            "interviews": sum(1 for a in formatted_apps if a["status"] == "interview_scheduled"),
            "hired": sum(1 for a in formatted_apps if a["status"] == "hired")
        }
        
        return {
            "role": "candidate",
            "stats": stats,
            "jobs": [],  # Candidates don't have jobs
            "applications": formatted_apps
        }
    
    def list_public_jobs(self, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active jobs for public view."""
        with self.session_factory() as db:
            query = db.query(Job).filter(Job.status == "active")
            
            if search_query:
                query = query.filter(
                    or_(
                        Job.job_title.ilike(f"%{search_query}%"),
                        Job.location.ilike(f"%{search_query}%")
                    )
                )
            
            jobs = query.order_by(desc(Job.created_at)).limit(100).all()
            
            # Get company info
            company_ids = list(set(j.company_id for j in jobs if j.company_id))
            companies = {}
            
            if company_ids:
                company_list = db.query(Company.id, Company.name)\
                    .filter(Company.id.in_(company_ids)).all()
                companies = {c.id: c.name for c in company_list}
            
            # Get skills for all jobs
            job_ids = [j.id for j in jobs]
            job_skills = {}
            
            if job_ids:
                skills_list = db.query(JobSkill.job_id, JobSkill.skill_name)\
                    .filter(JobSkill.job_id.in_(job_ids)).all()
                
                # Group skills by job_id
                for skill in skills_list:
                    if skill.job_id not in job_skills:
                        job_skills[skill.job_id] = []
                    job_skills[skill.job_id].append(skill.skill_name)
            
            # Resolve country IDs to names
            country_ids = set()
            for job in jobs:
                if job.location_country:
                    try:
                        country_ids.add(int(job.location_country))
                    except (ValueError, TypeError):
                        pass
            country_names = {}
            if country_ids:
                from sqlalchemy import text
                result = db.execute(text("SELECT id, name FROM countries WHERE id IN :ids"), {"ids": tuple(country_ids)})
                for row in result:
                    country_names[row[0]] = row[1]
            
            def resolve_country(job):
                if job.location_country:
                    try:
                        cid = int(job.location_country)
                        return country_names.get(cid, job.location_country)
                    except (ValueError, TypeError):
                        return job.location_country
                return None
            
            def build_location(job):
                if job.is_remote:
                    return "Remote"
                country = resolve_country(job)
                parts = [job.location_city, job.location_state, country]
                return ", ".join([p for p in parts if p]) or job.location
            
            return [
                {
                    "id": job.id,
                    "job_title": job.job_title,
                    "title": job.job_title,
                    "description": job.description,
                    "location": build_location(job),
                    "location_city": job.location_city,
                    "location_state": job.location_state,
                    "location_country": resolve_country(job),
                    "job_type": job.job_type,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "currency": job.currency,
                    "is_remote": job.is_remote,
                    "status": job.status,
                    "company_name": companies.get(job.company_id, "Unknown Company"),
                    "skills": job_skills.get(job.id, []),
                    "created_at": job.created_at.isoformat()
                }
                for job in jobs
            ]
    
    def get_public_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get single job for public view."""
        with self.session_factory() as db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != "active":
                return None
            
            # Get company info
            company_name = "Unknown Company"
            if job.company_id:
                company = db.query(Company.name).filter(Company.id == job.company_id).first()
                if company:
                    company_name = company.name
            
            # Resolve reference IDs to names
            department_name = None
            if job.department:
                dept = db.query(Department.name).filter(Department.id == job.department).first()
                if dept:
                    department_name = dept.name
            
            role_name = None
            if job.role:
                role_rec = db.query(Role.name).filter(Role.id == job.role).first()
                if role_rec:
                    role_name = role_rec.name
            
            employment_type_name = None
            if job.employment_type:
                emp_type = db.query(EmploymentType.name).filter(EmploymentType.id == job.employment_type).first()
                if emp_type:
                    employment_type_name = emp_type.name
            
            industry_name = None
            if job.industry:
                industry = db.query(Industry.name).filter(Industry.id == job.industry).first()
                if industry:
                    industry_name = industry.name
            
            education_name = None
            if job.education_qualification:
                edu = db.query(EducationLevel.name).filter(EducationLevel.id == job.education_qualification).first()
                if edu:
                    education_name = edu.name
            
            job_type_name = None
            if job.job_type:
                jt = db.query(JobType.name).filter(JobType.id == job.job_type).first()
                if jt:
                    job_type_name = jt.name
            
            # Resolve country ID to name if stored as numeric ID
            country_name = None
            if job.location_country:
                try:
                    # Check if it's a numeric ID
                    country_id = int(job.location_country)
                    from sqlalchemy import text
                    result = db.execute(text("SELECT name FROM countries WHERE id = :id"), {"id": country_id})
                    row = result.first()
                    if row:
                        country_name = row[0]
                except (ValueError, Exception):
                    # Not a numeric ID, use as-is (already a name)
                    country_name = job.location_country
            
            # Build location string with resolved country name
            location_display = job.location
            if job.is_remote:
                location_display = "Remote"
            elif job.location_city or job.location_state or country_name:
                location_parts = [job.location_city, job.location_state, country_name]
                location_display = ", ".join([p for p in location_parts if p])
            
            return {
                "id": job.id,
                "job_title": job.job_title,
                "title": job.job_title,
                "description": job.description,
                "requirements": job.requirements,
                "location": location_display,
                "location_city": job.location_city,
                "location_state": job.location_state,
                "location_country": country_name or job.location_country,
                "job_type": job_type_name or job.job_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "is_remote": job.is_remote,
                "status": job.status,
                "company_name": company_name,
                "department": department_name,
                "role": role_name,
                "employment_type": employment_type_name,
                "industry": industry_name,
                "education_qualification": education_name,
                "experience_min": job.experience_min,
                "experience_max": job.experience_max,
                "notice_period_days": job.notice_period_days,
                "contact_person_name": job.contact_person_name,
                "contact_person_email": job.contact_person_email,
                "created_at": job.created_at.isoformat()
            }


# ============================================================
# NOTIFICATION SERVICE
# ============================================================

class NotificationService(MySQLService):
    """Handles notification operations."""
    
    def create_notification(self, notif: Dict[str, Any]) -> Dict[str, Any]:
        """Create notification."""
        with self.session_factory() as db:
            notification = Notification(
                id=generate_uuid(),
                created_by=notif.get("created_by"),
                title=notif.get("title"),
                message=notif.get("message"),
                category=notif.get("category", "system"),
                related_id=notif.get("related_id"),
                notification_metadata=notif.get("metadata", {})
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            return {
                "id": notification.id,
                "created_by": notification.created_by,
                "message": notification.message,
                "category": notification.category,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
            }
    
    def list_notifications(self, user_id: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List notifications for user."""
        with self.session_factory() as db:
            offset = (page - 1) * page_size
            
            # Get total count
            total = db.query(func.count(Notification.id)).filter(Notification.created_by == user_id).scalar()
            
            # Get notifications
            notifications = db.query(Notification).filter(Notification.created_by == user_id)\
                .order_by(desc(Notification.created_at))\
                .offset(offset)\
                .limit(page_size)\
                .all()
            
            return {
                "notifications": [
                    {
                        "id": notif.id,
                        "created_by": notif.created_by,
                        "title": notif.title,
                        "message": notif.message,
                        "category": notif.category,
                        "related_id": notif.related_id,
                        "is_read": notif.is_read,
                        "metadata": notif.notification_metadata,
                        "created_at": notif.created_at.isoformat()
                    }
                    for notif in notifications
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total or 0
                }
            }
    
    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read."""
        with self.session_factory() as db:
            notification = db.query(Notification).filter(
                and_(Notification.id == notification_id, Notification.created_by == user_id)
            ).first()
            
            if not notification:
                return False
            
            notification.is_read = True
            db.commit()
            return True
    
    def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read."""
        with self.session_factory() as db:
            db.query(Notification).filter(Notification.created_by == user_id)\
                .update({"is_read": True})
            db.commit()
            return True


# ============================================================
# VIDEO SERVICE
# ============================================================

class VideoService(MySQLService):
    """Handles video operations."""
    
    def save_video_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save video response."""
        with self.session_factory() as db:
            response = VideoResponse(
                id=generate_uuid(),
                application_id=data.get("application_id"),
                candidate_id=data.get("candidate_id"),
                question=data.get("question"),
                video_url=data.get("video_url"),
                transcript=data.get("transcript"),
                duration=data.get("duration"),
                status=data.get("status", "completed"),
                ai_analysis=data.get("ai_analysis", {})
            )
            db.add(response)
            db.commit()
            db.refresh(response)
            
            return {
                "id": response.id,
                "application_id": response.application_id,
                "question": response.question,
                "video_url": response.video_url,
                "status": response.status,
                "recorded_at": response.recorded_at.isoformat()
            }
    
    def save_interview_response(self, interview_response: Dict[str, Any]) -> Dict[str, Any]:
        """Save a video interview response for a specific question."""
        with self.session_factory() as db:
            # Get job_id from application
            application = db.query(JobApplication).filter(
                JobApplication.id == interview_response.get("application_id")
            ).first()
            
            if not application:
                raise ValueError(f"Application {interview_response.get('application_id')} not found")
            
            response = VideoResponse(
                id=generate_uuid(),
                job_id=application.job_id,
                application_id=interview_response.get("application_id"),
                candidate_id=interview_response.get("candidate_id"),
                question=interview_response.get("question"),
                video_url=interview_response.get("video_url") or f"https://storage.skreenit.com/datastorage/{interview_response.get('video_path', '')}",
                video_path=interview_response.get("video_path", ""),
                question_index=interview_response.get("question_index", 0)
            )
            db.add(response)
            db.commit()
            db.refresh(response)
            
            logger.info(f"Video interview response saved for application {interview_response.get('application_id')}")
            return {
                "id": response.id,
                "application_id": response.application_id,
                "candidate_id": response.candidate_id,
                "question": response.question,
                "video_url": response.video_url,
                "video_path": response.video_path,
                "question_index": response.question_index,
                "created_at": response.created_at.isoformat()
            }
    
    def save_intro_video(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save introduction video."""
        with self.session_factory() as db:
            video = CandidateVideo(
                id=generate_uuid(),
                candidate_id=data.get("candidate_id"),
                video_type="intro",
                video_url=data.get("video_url"),
                video_path=data.get("video_path", data.get("video_url", "").split("/")[-1]),
                title=data.get("title", "Introduction Video"),
                description=data.get("description", ""),
            )
            db.add(video)
            db.commit()
            return {"id": video.id, "candidate_id": video.candidate_id, "video_url": video.video_url}
    
    def get_candidate_videos(self, candidate_id: str) -> List[Dict[str, Any]]:
        """Get all videos for candidate."""
        with self.session_factory() as db:
            videos = db.query(VideoResponse).filter(VideoResponse.candidate_id == candidate_id)\
                .order_by(desc(VideoResponse.recorded_at)).all()
            
            return [
                {
                    "id": video.id,
                    "application_id": video.application_id,
                    "question": video.question,
                    "video_url": video.video_url,
                    "status": video.status,
                    "recorded_at": video.recorded_at.isoformat()
                }
                for video in videos
            ]


# ============================================================
# SERVICE INSTANCES
# ============================================================

# Create service instances
user_service = UserService()
recruiter_service = RecruiterService()
candidate_service = CandidateService()
dashboard_service = DashboardService()
notification_service = NotificationService()
video_service = VideoService()
