"""
Resume Analysis Router
Provides resume upload, parsing, and improvement recommendations
"""

import os
import tempfile
import json as json_lib
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from services.resume_analyzer import ResumeAnalyzer
from services.resume_parser import ResumeParser
from services.ollama_service import ollama_service
from services.resume_template_service import resume_template_service
from utils_others.logger import logger
from services.auth_service import get_current_user

router = APIRouter(prefix="/resume-analysis", tags=["Resume Analysis"])

# Pydantic models for responses
class ResumeSection(BaseModel):
    name: str
    content: str
    score: float
    issues: List[str]
    suggestions: List[str]

class ResumeAnalysisResponse(BaseModel):
    success: bool
    filename: str
    overall_score: float
    sections: List[ResumeSection]
    format_issues: List[str]
    recommendations: List[str]
    parsed_data: Dict[str, Any]

class ResumeFormatCheck(BaseModel):
    format_type: str
    is_compliant: bool
    issues: List[str]
    suggestions: List[str]

@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and analyze a resume for format compliance and improvement suggestions
    Supports PDF, DOCX, and TXT files
    """
    try:
        # Validate file type
        allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, DOCX, TXT"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Parse resume
            parser = ResumeParser()
            parsed_data = await parser.parse_resume(temp_file_path, file.content_type)
            
            # Analyze resume
            analyzer = ResumeAnalyzer()
            analysis_result = await analyzer.analyze_resume(parsed_data, file.content_type)
            
            # Format response
            response = ResumeAnalysisResponse(
                success=True,
                filename=file.filename,
                overall_score=analysis_result["overall_score"],
                sections=[
                    ResumeSection(
                        name=section["name"],
                        content=section["content"],
                        score=section["score"],
                        issues=section["issues"],
                        suggestions=section["suggestions"]
                    )
                    for section in analysis_result["sections"]
                ],
                format_issues=analysis_result["format_issues"],
                recommendations=analysis_result["recommendations"],
                parsed_data=parsed_data
            )
            
            logger.info(f"Resume analysis completed for user {current_user.get('user_id')}: {file.filename}")
            return response
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {str(e)}")

@router.post("/check-format")
async def check_resume_format(
    file: UploadFile = File(...),
    format_type: str = "modern",
    current_user: dict = Depends(get_current_user)
):
    """
    Check if resume complies with a specific format type
    Available formats: modern, traditional, ats, creative
    """
    try:
        # Validate file type
        allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Parse and check format
            parser = ResumeParser()
            parsed_data = await parser.parse_resume(temp_file_path, file.content_type)
            
            analyzer = ResumeAnalyzer()
            format_check = await analyzer.check_format_compliance(parsed_data, format_type)
            
            response = ResumeFormatCheck(
                format_type=format_type,
                is_compliant=format_check["is_compliant"],
                issues=format_check["issues"],
                suggestions=format_check["suggestions"]
            )
            
            return response
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Format check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Format check failed: {str(e)}")

@router.get("/formats")
async def get_available_formats():
    """
    Get list of available resume formats with descriptions
    """
    formats = {
        "modern": {
            "name": "Modern Professional",
            "description": "Clean, contemporary format with clear sections and modern typography",
            "features": ["Contact info at top", "Professional summary", "Bullet points", "Clean layout"]
        },
        "traditional": {
            "name": "Traditional Conservative",
            "description": "Classic format suitable for traditional industries",
            "features": ["Formal structure", "Objective statement", "Chronological order", "Standard fonts"]
        },
        "ats": {
            "name": "ATS Optimized",
            "description": "Optimized for Applicant Tracking Systems with keywords and structure",
            "features": ["Simple formatting", "Keyword optimization", "Standard headings", "No tables/columns"]
        },
        "creative": {
            "name": "Creative Industry",
            "description": "Visual format for creative roles with design elements",
            "features": ["Visual elements", "Portfolio links", "Skills showcase", "Modern design"]
        }
    }
    
    return {"formats": formats}

@router.get("/analysis-history")
async def get_analysis_history(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's resume analysis history (placeholder for future implementation)
    """
    # This would typically fetch from a database
    return {"history": [], "message": "Analysis history feature coming soon"}


# =========================================================================
# AI-POWERED RESUME ANALYSIS ENDPOINTS (using Ollama LLM models)
# =========================================================================

class AITemplateSuggestionRequest(BaseModel):
    resume_text: str
    target_role: str = ""

class AIResumeImprovementRequest(BaseModel):
    resume_text: str
    jd_text: str = ""

class AIResumeScoreRequest(BaseModel):
    resume_text: str
    jd_text: str
    job_title: str = ""

class ResumeTemplateConversionRequest(BaseModel):
    resume_text: str
    template_id: str = "modern"
    parsed_data: Optional[Dict[str, Any]] = None


def _parse_json_response(raw: str) -> Dict[str, Any]:
    """Try to extract JSON from LLM response text."""
    if not raw:
        return {}
    # Try direct parse
    try:
        return json_lib.loads(raw)
    except json_lib.JSONDecodeError:
        pass
    # Try extracting JSON block
    import re
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        try:
            return json_lib.loads(json_match.group())
        except json_lib.JSONDecodeError:
            pass
    return {"raw_response": raw}


@router.post("/ai-suggest-template")
async def ai_suggest_template(request: AITemplateSuggestionRequest):
    """
    AI-powered resume template suggestion.
    Uses mistral for fast analysis — recommends modern/traditional/ats/creative
    with improvement tips and ATS compatibility score.
    """
    try:
        result = ollama_service.suggest_resume_template(request.resume_text, request.target_role)
        if result:
            parsed = _parse_json_response(result)
            return {"status": "success", "data": parsed, "model": "mistral"}
        raise HTTPException(status_code=503, detail="AI template suggestion unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI template suggestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI suggestion failed: {str(e)}")


@router.post("/ai-improve-resume")
async def ai_improve_resume(request: AIResumeImprovementRequest):
    """
    AI-powered resume improvement suggestions.
    Uses codellama for technical roles — provides section-by-section improvements,
    skill gaps, and actionable items.
    """
    try:
        result = ollama_service.ai_improve_resume(request.resume_text, request.jd_text)
        if result:
            parsed = _parse_json_response(result)
            return {"status": "success", "data": parsed, "model": "codellama"}
        raise HTTPException(status_code=503, detail="AI resume improvement unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI resume improvement failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI improvement failed: {str(e)}")


@router.post("/ai-score-resume")
async def ai_score_resume_vs_jd(request: AIResumeScoreRequest):
    """
    AI-powered resume scoring against a job description.
    Uses llama3 for balanced evaluation — returns match score, skill/experience/education
    breakdowns, matched/missing skills, and hire recommendation.
    """
    try:
        result = ollama_service.score_resume_vs_jd(
            request.resume_text, request.jd_text, request.job_title
        )
        if result:
            parsed = _parse_json_response(result)
            return {"status": "success", "data": parsed, "model": "llama3"}
        raise HTTPException(status_code=503, detail="AI resume scoring unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI resume scoring failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI scoring failed: {str(e)}")


@router.post("/convert-template")
async def convert_resume_template(
    file: UploadFile = File(...),
    template_id: str = "modern",
    current_user: dict = Depends(get_current_user)
):
    """
    Convert uploaded resume to a specific template format.
    Converts to HTML, then to PDF, and uploads to R2 storage.
    Returns the PDF URL of the converted resume.
    """
    try:
        # Validate template_id
        valid_templates = ["modern", "ats", "traditional", "creative"]
        if template_id not in valid_templates:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid template. Valid options: {', '.join(valid_templates)}"
            )
        
        # Validate file type
        allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, DOCX, TXT"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Convert resume to template with PDF conversion and R2 upload
            user_id = current_user.get('sub') or current_user.get('user_id') or current_user.get('id')
            logger.info(f"Converting resume for user_id: {user_id}, current_user keys: {list(current_user.keys())}")
            conversion_result = await resume_template_service.convert_resume_to_template(
                temp_file_path, 
                template_id,
                convert_to_pdf=True,
                upload_to_r2=True,
                user_id=str(user_id) if user_id else None
            )
            
            if not conversion_result:
                raise HTTPException(status_code=500, detail="Resume conversion failed")
            
            # Store converted resume URL in database
            if conversion_result.get('pdf_url'):
                from services.mysql_service import mysql_service
                try:
                    # Update candidate profile with converted resume URL
                    mysql_service.update_record(
                        "candidate_profiles",
                        {"user_id": user_id},
                        {"converted_resume_url": conversion_result['pdf_url'], "resume_template": template_id}
                    )
                    logger.info(f"Updated candidate {user_id} with converted resume URL")
                except Exception as db_error:
                    logger.warning(f"Failed to update database with converted resume URL: {db_error}")
            
            logger.info(f"Resume converted to {template_id} template for user {user_id}")
            
            return {
                "success": True,
                "template_id": template_id,
                "html_content": conversion_result.get('html_content'),
                "pdf_url": conversion_result.get('pdf_url'),
                "filename": file.filename
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume template conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template conversion failed: {str(e)}")
