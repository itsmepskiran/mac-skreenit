"""
Resume Analysis Database Models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class ResumeAnalysis(Base):
    """Model for storing resume analysis results"""
    __tablename__ = "resume_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    
    # Analysis results
    overall_score = Column(Float, nullable=False)
    sections_data = Column(JSON, nullable=False)  # Store section analyses
    format_issues = Column(JSON, nullable=False)  # List of format issues
    recommendations = Column(JSON, nullable=False)  # List of recommendations
    parsed_data = Column(JSON, nullable=False)  # Raw parsed resume data
    
    # Metadata
    analysis_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)  # File size in bytes
    processing_time = Column(Float)  # Processing time in seconds
    
    # Relationships
    user = relationship("User", back_populates="resume_analyses")
    
    def __repr__(self):
        return f"<ResumeAnalysis(id={self.id}, user_id={self.user_id}, score={self.overall_score})>"

class ResumeAnalysisHistory(Base):
    """Model for tracking resume analysis history and improvements"""
    __tablename__ = "resume_analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("resume_analyses.id"), nullable=False)
    
    # Change tracking
    previous_score = Column(Float)
    new_score = Column(Float)
    score_change = Column(Float)
    improvements_made = Column(JSON)  # List of improvements made
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="resume_analysis_history")
    analysis = relationship("ResumeAnalysis")
    
    def __repr__(self):
        return f"<ResumeAnalysisHistory(id={self.id}, user_id={self.user_id}, change={self.score_change})>"
