from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

# -------------------------------------------------------------------
# SHARED / BASE MODELS
# -------------------------------------------------------------------

class RecruiterProfileBase(BaseModel):
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    location: Optional[str] = None

# -------------------------------------------------------------------
# COMPANY MODELS
# -------------------------------------------------------------------

class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    company_logo_url: Optional[str] = None
    company_display_id: Optional[str] = None
    recruiter_id: Optional[str] = None

class CompanyCreate(CompanyBase):
    """
    Model used when creating a company.
    """
    pass

# -------------------------------------------------------------------
# PROFILE MODELS
# -------------------------------------------------------------------

class RecruiterProfileCreate(RecruiterProfileBase):
    """
    Model used when creating a profile (often internally or via Auth)
    """
    user_id: str

class RecruiterProfileUpdate(RecruiterProfileBase):
    """
    Used when the recruiter updates their profile from the dashboard.
    All fields are optional because they might update just one.
    """
    pass

# -------------------------------------------------------------------
# JOB MODELS
# -------------------------------------------------------------------

class JobBase(BaseModel):
    # Basic Info
    job_title: str
    department: Optional[str] = None
    role: Optional[str] = None
    employment_type: Optional[str] = None
    job_type: str = Field(..., description="onsite, remote, hybrid")
    no_of_openings: Optional[int] = 1
    
    # Location
    location: Optional[str] = None
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    is_remote: Optional[bool] = False
    
    # Experience & Salary
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    notice_period_days: Optional[int] = None
    industry: Optional[str] = None
    
    # Education & Skills
    education_qualification: Optional[str] = None
    skills: Optional[str] = None  # JSON string of skills array
    diversity_hiring: Optional[bool] = False
    
    # Job Details
    description: str
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    
    # Contact Person
    contact_person_name: Optional[str] = None
    contact_person_email: Optional[str] = None
    
    # Meta
    currency: Optional[str] = "INR"
    status: Optional[str] = "active"

class JobCreateRequest(JobBase):
    """
    Payload for POST /api/v1/recruiter/jobs
    """
    pass

class JobUpdateRequest(BaseModel):
    """
    Payload for PUT /api/v1/recruiter/jobs/{job_id}
    All fields optional to allow partial updates.
    """
    # Basic Info
    job_title: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    employment_type: Optional[str] = None
    job_type: Optional[str] = None
    no_of_openings: Optional[int] = None
    
    # Location
    location: Optional[str] = None
    location_country: Optional[str] = None
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    is_remote: Optional[bool] = None
    
    # Experience & Salary
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    notice_period_days: Optional[int] = None
    industry: Optional[str] = None
    
    # Education & Skills
    education_qualification: Optional[str] = None
    skills: Optional[str] = None
    diversity_hiring: Optional[bool] = None
    
    # Job Details
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    
    # Contact Person
    contact_person_name: Optional[str] = None
    contact_person_email: Optional[str] = None
    
    # Meta
    currency: Optional[str] = None
    status: Optional[str] = None