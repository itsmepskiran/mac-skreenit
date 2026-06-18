from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


# ---------------------------------------------------------
# JOB ITEM FOR DASHBOARD (Recruiter)
# ---------------------------------------------------------
class DashboardJob(BaseModel):
    id: str
    title: str
    status: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None

    # Dashboard metrics
    applicant_count: Optional[int] = None
    shortlisted_count: Optional[int] = None
    interview_count: Optional[int] = None
    video_submissions: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# APPLICATION ITEM FOR DASHBOARD (Candidate)
# ---------------------------------------------------------
class DashboardApplication(BaseModel):
    id: str
    status: Optional[str] = None
    ai_score: Optional[int] = None
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    applied_at: Optional[str] = None

    # Extra fields for UI
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# DASHBOARD STATS
# ---------------------------------------------------------
class DashboardStats(BaseModel):
    total_jobs: int = 0
    active_jobs: int = 0
    closed_jobs: int = 0
    total_applications: int = 0
    shortlisted: int = 0
    interviews: int = 0
    hired: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# DASHBOARD SUMMARY (MAIN RESPONSE MODEL)
# ---------------------------------------------------------
class DashboardSummary(BaseModel):
    role: str
    stats: DashboardStats
    jobs: List[DashboardJob] = Field(default_factory=list)
    applications: List[DashboardApplication] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
