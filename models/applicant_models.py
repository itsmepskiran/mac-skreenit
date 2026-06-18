from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any

# -------------------------------------------------------------------
# SHARED / BASE MODELS
# -------------------------------------------------------------------

class ApplicantProfileBase(BaseModel):
    # Basic Info
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    
    # Personal Info
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    
    # Current Address
    current_address: Optional[str] = None
    current_city: Optional[str] = None
    current_state: Optional[str] = None
    current_country: Optional[str] = None
    
    # Permanent Address
    permanent_address: Optional[str] = None
    permanent_city: Optional[str] = None
    permanent_state: Optional[str] = None
    permanent_country: Optional[str] = None
    
    # Professional Details
    current_salary: Optional[int] = None
    expected_salary: Optional[int] = None
    notice_period_days: Optional[int] = None
    highest_qualification: Optional[str] = None
    
    # Social Links
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    personal_projects: Optional[str] = None
    personal_blogs: Optional[str] = None
    
    # Education Details
    schooling: Optional[str] = None
    schooling_year: Optional[str] = None
    schooling_percentage: Optional[float] = None
    pre_university: Optional[str] = None
    pre_university_year: Optional[str] = None
    pre_university_percentage: Optional[float] = None
    graduation: Optional[str] = None
    graduation_year: Optional[str] = None
    graduation_percentage: Optional[float] = None
    post_graduation: Optional[str] = None
    post_graduation_year: Optional[str] = None
    post_graduation_percentage: Optional[float] = None
    
    # Languages & Certifications
    spoken_languages: Optional[str] = None  # JSON string
    certifications: Optional[str] = None  # JSON string
    
    # Current/Latest Experience
    current_company: Optional[str] = None
    current_designation: Optional[str] = None
    current_doj: Optional[str] = None
    current_dol: Optional[str] = None
    
    # Files
    resume_url: Optional[str] = None
    intro_video_url: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Skills
    skills: Optional[str] = None  # JSON string

class ApplicantProfileUpdate(ApplicantProfileBase):
    """
    Used for profile updates via PUT /api/v1/applicant/profile
    """
    pass

# -------------------------------------------------------------------
# APPLICATION MODELS
# -------------------------------------------------------------------

class ApplicationBase(BaseModel):
    job_id: str
    cover_letter: Optional[str] = None
    custom_answers: Optional[Dict[str, Any]] = None

class ApplicationCreate(BaseModel):
    job_id: str
    candidate_id: Optional[str] = None
    cover_letter: Optional[str] = None
    custom_answers: Optional[Dict[str, Any]] = None
    
class ApplicationResponse(ApplicationBase):
    id: str
    status: str
    applied_at: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None