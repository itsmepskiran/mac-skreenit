import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator
from contextlib import contextmanager
from urllib.parse import quote
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, func, Index, ForeignKeyConstraint, JSON, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker
from sqlalchemy.sql import func as sql_func
from sqlalchemy.dialects.mysql import VARCHAR
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "skreenit")

# URL-encode the password to handle special characters like @
ENCD_PASS = quote(MYSQL_PASSWORD, safe='')

# Create database URL with encoded password and charset
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{ENCD_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_timeout=30,  # Timeout for getting connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "read_timeout": 30,     # Read timeout in seconds
        "write_timeout": 30     # Write timeout in seconds
    },
    echo=False  # Set to True for SQL logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


# ============================================================
# REFERENCE TABLES (for dropdowns)
# ============================================================

class Department(Base):
    """Department reference table."""
    __tablename__ = "departments"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Role(Base):
    """Role/Designation reference table."""
    __tablename__ = "roles"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    department_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department: Mapped[Optional["Department"]] = relationship("Department")


class EmploymentType(Base):
    """Employment type reference table."""
    __tablename__ = "employment_types"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Industry(Base):
    """Industry reference table."""
    __tablename__ = "industries"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobType(Base):
    """Job type (work location preference) reference table."""
    __tablename__ = "job_types"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EducationLevel(Base):
    """Education level reference table."""
    __tablename__ = "education_levels"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalaryRange(Base):
    """Salary range reference table."""
    __tablename__ = "salary_ranges"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    label: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=False)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(VARCHAR(10), default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExperienceLevel(Base):
    """Experience level reference table."""
    __tablename__ = "experience_levels"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    min_years: Mapped[int] = mapped_column(Integer, nullable=False)
    max_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# DATABASE MODELS
# ============================================================

class User(Base):
    """User model for custom authentication."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    role: Mapped[str] = mapped_column(Enum("admin", "recruiter", "candidate", name="user_role"), default="candidate")
    roles: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=lambda: ["candidate"])
    location: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    email_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sign_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    user_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    
    # Relationships
    recruiter_profile: Mapped[Optional["RecruiterProfile"]] = relationship("RecruiterProfile", back_populates="user", uselist=False)
    candidate_profile: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", back_populates="user", uselist=False)
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="creator")
    applications: Mapped[List["JobApplication"]] = relationship("JobApplication", foreign_keys="JobApplication.candidate_id", back_populates="candidate")


class Company(Base):
    """Company model."""
    __tablename__ = "companies"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    company_display_id: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True, index=True)
    recruiter_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recruiter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[recruiter_id])
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")
    recruiter_profiles: Mapped[List["RecruiterProfile"]] = relationship("RecruiterProfile", back_populates="company")


class RecruiterProfile(Base):
    """Recruiter profile model."""
    __tablename__ = "recruiter_profiles"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    # Removed: company_name, company_website, company_description (these belong in companies/users table)
    location: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    # Removed: avatar_url (belongs in users table)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recruiter_profile")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="recruiter_profiles")


class CandidateProfile(Base):
    """Candidate profile model."""
    __tablename__ = "candidate_profiles"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # Display ID for candidates (similar to company_display_id)
    candidate_display_id: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True, index=True)
    
    # Personal Information
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    
    # Current Address
    current_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_city: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    current_state: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    current_country: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    
    # Permanent Address
    permanent_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permanent_city: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    permanent_state: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    permanent_country: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    
    # Professional Details
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notice_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Social & Web Presence
    linkedin_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    personal_projects: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personal_blogs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Skills & Languages
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    spoken_languages: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    certifications: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    # Education - Structured
    highest_qualification: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    schooling: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    schooling_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schooling_percentage: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    pre_university: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    pre_university_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pre_university_percentage: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    graduation: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    graduation_percentage: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    post_graduation: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    post_graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    post_graduation_percentage: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    
    # Experience
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Latest/Current Experience
    current_company: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    current_designation: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    current_doj: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_dol: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Full experience history as JSON
    experience: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    # Full education history as JSON (for additional degrees)
    education: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    # Documents
    resume_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    converted_resume_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    resume_template: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    intro_video_url: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")


class Job(Base):
    """Job posting model."""
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    job_title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    
    # Job Classification
    department: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)  # full-time, part-time, contract, internship
    job_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)  # work type preference (wfo, wfh, hybrid)
    
    # Location
    location: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    location_city: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    location_state: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    location_country: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Experience Requirements
    experience_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)  # Candidate current industry
    
    # Diversity & Inclusion
    diversity_hiring: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)  # e.g., "women-only", "disability-friendly", "open-to-all"
    
    # Job Details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(VARCHAR(10), default="INR")
    
    # Hiring Details
    no_of_openings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    notice_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Education & Skills
    education_qualification: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    work_location_preference: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Contact Person
    contact_person_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    contact_person_email: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    
    # Status & Ownership
    status: Mapped[str] = mapped_column(Enum("active", "closed", "draft", name="job_status"), default="active", index=True)
    company_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="jobs")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="jobs")
    skills_rel: Mapped[List["JobSkill"]] = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    interview_questions: Mapped[List["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["JobApplication"]] = relationship("JobApplication", back_populates="job")


class JobSkill(Base):
    """Skills required for a job."""
    __tablename__ = "job_skills"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="skills_rel")


class InterviewQuestion(Base):
    """Interview questions for a job."""
    __tablename__ = "interview_questions"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    question_order: Mapped[int] = mapped_column(Integer, default=0)
    time_limit: Mapped[int] = mapped_column(Integer, default=120)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="interview_questions")


class JobApplication(Base):
    """Job application from candidate."""
    __tablename__ = "job_applications"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    cover_letter: Mapped[Optional[str]] = mapped_column(Text)
    intro_video_url: Mapped[Optional[str]] = mapped_column(String(500))
    resume_url: Mapped[Optional[str]] = mapped_column(String(500))
    custom_answers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    interview_questions: Mapped[Optional[List[str]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        Enum("submitted", "responses_submitted", "reviewed", "shortlisted", "interview_scheduled", "interviewing", "hired", "rejected", name="application_status"),
        default="submitted"
    )
    ai_score: Mapped[Optional[int]] = mapped_column(Integer)
    feedback: Mapped[Optional[str]] = mapped_column(Text)  # Recruiter feedback for candidate
    face_match_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Face verification result
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id], back_populates="applications")
    video_responses: Mapped[List["VideoResponse"]] = relationship("VideoResponse", back_populates="application")


class VideoResponse(Base):
    """Video response for job application questions."""
    __tablename__ = "video_responses"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("jobs.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    video_url: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    video_path: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    question_index: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="video_responses")


class InterviewResponse(Base):
    """Alternative interview response table."""
    __tablename__ = "interview_responses"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_url: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    status: Mapped[str] = mapped_column(Enum("pending_review", "reviewed", "approved", "rejected", name="interview_response_status"), default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CandidateVideo(Base):
    """Videos for candidates (intro, portfolio, etc.)."""
    __tablename__ = "candidate_videos"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_type: Mapped[str] = mapped_column(Enum("intro", "portfolio", "other", name="video_type"), default="intro")
    video_url: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    video_path: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CandidateIntroResponse(Base):
    """Interview video responses from Step 7 (onboarding interview)."""
    __tablename__ = "candidate_intro_responses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(VARCHAR(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    video_url: Mapped[str] = mapped_column(VARCHAR(1024), nullable=False)
    video_path: Mapped[str] = mapped_column(VARCHAR(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrainingRegistration(Base):
    """Base model for training registrations."""
    __tablename__ = "training_registrations"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    registration_type: Mapped[str] = mapped_column(Enum("college", "corporate", name="registration_type"), nullable=False, index=True)
    training_course: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    training_course_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(50), default="pending", index=True)
    payment_status: Mapped[str] = mapped_column(VARCHAR(50), default="pending")
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True, index=True)
    payment_id: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CollegeTrainingRegistration(Base):
    """College/Student training registration details."""
    __tablename__ = "college_training_registrations"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    
    # Personal Details
    first_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    last_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, index=True)
    mobile: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    
    # College Details
    college_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    university_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    college_address: Mapped[str] = mapped_column(Text, nullable=False)
    roll_number: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    course: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    year_of_study: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    passing_year: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Training Details
    training_course: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    batch_timing: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Foreign Key to base registration
    __table_args__ = (
        ForeignKeyConstraint(['registration_id'], ['training_registrations.registration_id'], ondelete="CASCADE"),
    )


class CorporateTrainingRegistration(Base):
    """Corporate training registration details."""
    __tablename__ = "corporate_training_registrations"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    
    # Company Details
    company_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    company_hq: Mapped[str] = mapped_column(Text, nullable=False)
    company_headcount: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    industry: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    company_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    company_website: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    
    # Contact Person Details
    contact_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    contact_designation: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    contact_email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    contact_mobile: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    
    # Training Requirements
    training_course: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    training_mode: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    preferred_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    additional_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Foreign Key to base registration
    __table_args__ = (
        ForeignKeyConstraint(['registration_id'], ['training_registrations.registration_id'], ondelete="CASCADE"),
    )


# ============================================================
# TRAINING ASSESSMENT MODELS
# ============================================================

class TrainingAssessmentQuestion(Base):
    """Assessment questions assigned to training sessions."""
    __tablename__ = "training_assessment_questions"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), ForeignKey("training_registrations.registration_id", ondelete="CASCADE"), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(VARCHAR(50), default="video_response")  # video_response, mcq, essay, etc.
    duration: Mapped[int] = mapped_column(Integer, default=60)  # seconds
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TrainingAssessmentResponse(Base):
    """Individual assessment responses from training participants."""
    __tablename__ = "training_assessment_responses"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), ForeignKey("training_registrations.registration_id", ondelete="CASCADE"), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    response_type: Mapped[str] = mapped_column(VARCHAR(50), default="video")  # video, text, audio, etc.
    response_path: Mapped[Optional[str]] = mapped_column(VARCHAR(500), nullable=True)  # S3 path or URL
    response_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # for text responses
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrainingAssessmentCompletion(Base):
    """Overall assessment completion status for training registrations."""
    __tablename__ = "training_assessment_completions"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    registration_id: Mapped[str] = mapped_column(VARCHAR(50), ForeignKey("training_registrations.registration_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    questions_completed: Mapped[int] = mapped_column(Integer, default=0)
    completion_status: Mapped[str] = mapped_column(VARCHAR(50), default="pending")  # pending, in_progress, completed
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evaluation_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    evaluation_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    """Notifications for users."""
    __tablename__ = "notifications"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    created_by: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(VARCHAR(50), default="system")
    related_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notification_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


# ============================================================
# ADMIN USERS (separate from main users table)
# ============================================================

class AdminUser(Base):
    """Admin portal users — completely separate from recruiter/candidate users."""
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    role: Mapped[str] = mapped_column(Enum("admin", "super_admin", name="admin_role"), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# PRICING MODELS
# ============================================================

class PricingPlan(Base):
    """Central pricing table for all Skreenit services."""
    __tablename__ = "pricing_plans"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    service_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, index=True)
    service_key: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_inr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(VARCHAR(3), nullable=False, default="INR")
    billing_cycle: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    trial_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    duration: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PricingAuditLog(Base):
    """Audit log for all pricing changes."""
    __tablename__ = "pricing_audit_log"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    plan_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    service_key: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    action: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    changed_by_user_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    changed_by_email: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    changed_by_role: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    old_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class UserSubscription(Base):
    """Track purchased subscriptions and paid services."""
    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("pricing_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    service_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Enum("pending", "active", "trial", "cancelled", "expired", name="user_subscription_status"), nullable=False, default="pending", index=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0)
    reason_cancelled: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Allow multiple active subscriptions per user: unique only on (user_id, plan_id)
    # Users can have multiple subscriptions for same service_type with different plans
    __table_args__ = (
        Index('idx_user_active_status', 'user_id', 'status'),
        Index('idx_plan_service', 'plan_id', 'service_type'),
        Index('idx_user_plan_unique', 'user_id', 'plan_id', unique=True),
    )



class UserSubscriptionFeature(Base):
    """Individual features attached to a subscription."""
    __tablename__ = "user_subscription_features"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    subscription_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("user_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserSubscriptionHistory(Base):
    """Subscription status history for audit and rollback."""
    __tablename__ = "user_subscription_history"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    subscription_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    old_status: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    new_status: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    changed_by: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


# ============================================================
# SCREENING SYSTEM MODELS
# ============================================================

class CandidateAnalysisResult(Base):
    """Results of resume + JD analysis for candidate screening."""
    __tablename__ = "candidate_analysis_results"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    job_application_id: Mapped[Optional[str]] = mapped_column(VARCHAR(36), nullable=True, index=True)
    job_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    skills_matched: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    skills_missing: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    experience_match: Mapped[bool] = mapped_column(Boolean, default=False)
    education_match: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_fit: Mapped[str] = mapped_column(VARCHAR(20), default="low")
    recommendation: Mapped[str] = mapped_column(VARCHAR(30), default="reject")
    threshold_met: Mapped[bool] = mapped_column(Boolean, default=False)
    
    analysis_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScreeningQuestion(Base):
    """Screening questions generated for candidates during application."""
    __tablename__ = "screening_questions"
    
    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    analysis_result_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(VARCHAR(20), default="technical")
    priority: Mapped[str] = mapped_column(VARCHAR(10), default="medium")
    related_skill: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScreeningResponse(Base):
    """Candidate responses to screening questions."""
    __tablename__ = "screening_responses"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    screening_question_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    analysis_result_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(VARCHAR(36), nullable=False, index=True)

    response: Mapped[str] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    response_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# PREMIUM ASSESSMENT MODELS
# ============================================================

class PremiumAssessmentResponse(Base):
    """Individual assessment response video + metadata."""
    __tablename__ = "premium_assessment_responses"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    question_id: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    video_path: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PremiumAssessmentCompletion(Base):
    """Assessment completion record with response metadata."""
    __tablename__ = "premium_assessment_completions"

    id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(VARCHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(VARCHAR(50), default="completed")
    pm_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# DATABASE UTILITIES
# ============================================================

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(Session, 'before_flush')
def receive_before_flush(session, flush_context, instances):
    """Automatically update updated_at timestamp before flush."""
    for instance in session.dirty:
        if hasattr(instance, 'updated_at'):
            instance.updated_at = datetime.utcnow()
