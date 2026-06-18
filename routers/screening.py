"""
Screening System API Endpoints
Handles resume + JD analysis, screening questions, and candidate responses.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db
from database import (
    CandidateAnalysisResult, 
    ScreeningQuestion, 
    ScreeningResponse,
    Job,
    User,
    generate_uuid
)
from services.resume_jd_analysis_service import ResumeJDAnalysisService
from services.ollama_service import ollama_service, TaskType
from utils_others.logger import logger

router = APIRouter(prefix="/screening", tags=["screening"])


# =========================================================================
# Request/Response Models
# =========================================================================

class AnalysisRequest(BaseModel):
    """Request model for resume + JD analysis."""
    job_id: str
    candidate_id: str
    resume_text: str
    job_description: str
    job_title: str
    candidate_info: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    id: str
    job_id: str
    candidate_id: str
    match_score: int
    skills_matched: List[str]
    skills_missing: List[str]
    experience_match: bool
    education_match: bool
    overall_fit: str
    recommendation: str
    threshold_met: bool
    screening_questions: List[Dict[str, Any]]
    analyzed_at: str


class QuestionRequest(BaseModel):
    """Request model for answering screening questions."""
    analysis_result_id: str
    question_id: str
    candidate_id: str
    response: str


class QuestionResponse(BaseModel):
    """Response model for question submission."""
    id: str
    question: str
    response: str
    score: int
    answered_at: str


class FinalScoreRequest(BaseModel):
    """Request model for calculating final score after all responses."""
    analysis_result_id: str


class FinalScoreResponse(BaseModel):
    """Response model for final score."""
    overall_score: int
    question_scores: List[Dict[str, Any]]
    recommendation: str
    should_push_to_recruiter: bool


# =========================================================================
# API Endpoints
# =========================================================================

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_candidate(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze a candidate's resume against a job description.
    
    This endpoint:
    1. Parses the resume and job description
    2. Calculates match score
    3. Identifies skill gaps
    4. Generates screening questions
    5. Stores the analysis results
    """
    try:
        # Verify job exists
        job = db.query(Job).filter(Job.id == request.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify candidate exists
        candidate = db.query(User).filter(User.id == request.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Run analysis
        analysis_service = ResumeJDAnalysisService()
        analysis_result = analysis_service.analyze_application(
            resume_text=request.resume_text,
            job_description=request.job_description,
            job_title=request.job_title,
            candidate_info=request.candidate_info
        )
        
        # Store analysis result
        analysis_record = CandidateAnalysisResult(
            id=generate_uuid(),
            job_id=request.job_id,
            candidate_id=request.candidate_id,
            match_score=analysis_result["match_score"],
            skills_matched={"skills": analysis_result["skills_matched"]},
            skills_missing={"skills": analysis_result["skills_missing"]},
            experience_match=analysis_result["experience_match"],
            education_match=analysis_result["education_match"],
            overall_fit=analysis_result["overall_fit"],
            recommendation=analysis_result["recommendation"],
            threshold_met=analysis_result["threshold_met"],
            analysis_metadata=analysis_result,
            analyzed_at=datetime.utcnow()
        )
        db.add(analysis_record)
        db.flush()  # Get the ID before adding questions
        
        # Store screening questions
        screening_questions = []
        for i, q in enumerate(analysis_result["screening_questions"]):
            question_record = ScreeningQuestion(
                id=generate_uuid(),
                analysis_result_id=analysis_record.id,
                job_id=request.job_id,
                question=q["question"],
                question_type=q["question_type"],
                priority=q["priority"],
                related_skill=q.get("related_skill"),
                order_index=i,
                is_active=True
            )
            db.add(question_record)
            screening_questions.append({
                "id": question_record.id,
                "question": q["question"],
                "question_type": q["question_type"],
                "priority": q["priority"],
                "related_skill": q.get("related_skill")
            })
        
        db.commit()
        
        logger.info(f"Analysis completed for candidate {request.candidate_id} on job {request.job_id}. Score: {analysis_result['match_score']}")
        
        return AnalysisResponse(
            id=analysis_record.id,
            job_id=request.job_id,
            candidate_id=request.candidate_id,
            match_score=analysis_result["match_score"],
            skills_matched=analysis_result["skills_matched"],
            skills_missing=analysis_result["skills_missing"],
            experience_match=analysis_result["experience_match"],
            education_match=analysis_result["education_match"],
            overall_fit=analysis_result["overall_fit"],
            recommendation=analysis_result["recommendation"],
            threshold_met=analysis_result["threshold_met"],
            screening_questions=screening_questions,
            analyzed_at=analysis_record.analyzed_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/questions/{analysis_result_id}")
async def get_screening_questions(
    analysis_result_id: str,
    db: Session = Depends(get_db)
):
    """Get all screening questions for an analysis result."""
    try:
        questions = db.query(ScreeningQuestion).filter(
            ScreeningQuestion.analysis_result_id == analysis_result_id,
            ScreeningQuestion.is_active == True
        ).order_by(ScreeningQuestion.order_index).all()
        
        if not questions:
            raise HTTPException(status_code=404, detail="No questions found")
        
        return [
            {
                "id": q.id,
                "question": q.question,
                "question_type": q.question_type,
                "priority": q.priority,
                "related_skill": q.related_skill,
                "order_index": q.order_index
            }
            for q in questions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")


@router.post("/respond", response_model=QuestionResponse)
async def submit_response(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Submit a candidate's response to a screening question."""
    try:
        # Verify question exists
        question = db.query(ScreeningQuestion).filter(
            ScreeningQuestion.id == request.question_id
        ).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Verify analysis result exists
        analysis_result = db.query(CandidateAnalysisResult).filter(
            CandidateAnalysisResult.id == request.analysis_result_id
        ).first()
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Check if response already exists
        existing_response = db.query(ScreeningResponse).filter(
            ScreeningResponse.screening_question_id == request.question_id,
            ScreeningResponse.analysis_result_id == request.analysis_result_id
        ).first()
        
        if existing_response:
            # Update existing response
            existing_response.response = request.response
            existing_response.answered_at = datetime.utcnow()
            response_id = existing_response.id
        else:
            # Create new response
            response_record = ScreeningResponse(
                id=generate_uuid(),
                screening_question_id=request.question_id,
                analysis_result_id=request.analysis_result_id,
                candidate_id=request.candidate_id,
                response=request.response,
                score=0,  # Will be calculated later
                answered_at=datetime.utcnow()
            )
            db.add(response_record)
            response_id = response_record.id
        
        db.commit()
        
        logger.info(f"Response submitted for question {request.question_id}")
        
        return QuestionResponse(
            id=response_id,
            question=question.question,
            response=request.response,
            score=0,
            answered_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to submit response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")


@router.post("/calculate-final-score", response_model=FinalScoreResponse)
async def calculate_final_score(
    request: FinalScoreRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate final score after all responses are submitted.
    This scores all responses and determines if the candidate should be pushed to the recruiter.
    """
    try:
        # Get analysis result
        analysis_result = db.query(CandidateAnalysisResult).filter(
            CandidateAnalysisResult.id == request.analysis_result_id
        ).first()
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Get all questions and responses
        questions = db.query(ScreeningQuestion).filter(
            ScreeningQuestion.analysis_result_id == request.analysis_result_id,
            ScreeningQuestion.is_active == True
        ).order_by(ScreeningQuestion.order_index).all()
        
        # Get responses
        question_responses = []
        for q in questions:
            response = db.query(ScreeningResponse).filter(
                ScreeningResponse.screening_question_id == q.id,
                ScreeningResponse.analysis_result_id == request.analysis_result_id
            ).first()
            
            question_responses.append({
                "question": q.question,
                "question_type": q.question_type,
                "priority": q.priority,
                "response": response.response if response else "",
                "has_response": response is not None
            })
        
        # Score responses using analysis service
        analysis_service = ResumeJDAnalysisService()
        scoring_result = analysis_service.score_candidate_responses(
            questions=[
                {
                    "question": qr["question"],
                    "question_type": qr["question_type"],
                    "priority": qr["priority"]
                }
                for qr in question_responses
            ],
            responses=[qr["response"] for qr in question_responses]
        )
        
        # Update response scores in database
        for i, q in enumerate(questions):
            response = db.query(ScreeningResponse).filter(
                ScreeningResponse.screening_question_id == q.id,
                ScreeningResponse.analysis_result_id == request.analysis_result_id
            ).first()
            if response:
                response.score = scoring_result["question_scores"][i]["score"]
                response.response_metadata = scoring_result["question_scores"][i]
        
        # Determine if should push to recruiter
        # Combine resume match score with response score
        resume_weight = 0.6
        response_weight = 0.4
        combined_score = (
            analysis_result.match_score * resume_weight +
            scoring_result["overall_score"] * response_weight
        )
        
        should_push = combined_score >= 70  # Threshold for pushing to recruiter
        
        # Update analysis result with final recommendation
        if should_push:
            analysis_result.recommendation = "push_to_recruiter"
            analysis_result.threshold_met = True
        else:
            analysis_result.recommendation = "hold"
            analysis_result.threshold_met = False
        
        db.commit()
        
        logger.info(f"Final score calculated: {combined_score}. Push to recruiter: {should_push}")
        
        return FinalScoreResponse(
            overall_score=int(combined_score),
            question_scores=scoring_result["question_scores"],
            recommendation=scoring_result["recommendation"],
            should_push_to_recruiter=should_push
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to calculate final score: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate final score: {str(e)}")


@router.get("/analysis/{analysis_result_id}")
async def get_analysis_result(
    analysis_result_id: str,
    db: Session = Depends(get_db)
):
    """Get a complete analysis result including all responses."""
    try:
        analysis = db.query(CandidateAnalysisResult).filter(
            CandidateAnalysisResult.id == analysis_result_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Get questions and responses
        questions = db.query(ScreeningQuestion).filter(
            ScreeningQuestion.analysis_result_id == analysis_result_id
        ).order_by(ScreeningQuestion.order_index).all()
        
        questions_with_responses = []
        for q in questions:
            response = db.query(ScreeningResponse).filter(
                ScreeningResponse.screening_question_id == q.id
            ).first()
            
            questions_with_responses.append({
                "id": q.id,
                "question": q.question,
                "question_type": q.question_type,
                "priority": q.priority,
                "related_skill": q.related_skill,
                "response": response.response if response else None,
                "score": response.score if response else 0,
                "answered_at": response.answered_at.isoformat() if response else None
            })
        
        return {
            "id": analysis.id,
            "job_id": analysis.job_id,
            "candidate_id": analysis.candidate_id,
            "match_score": analysis.match_score,
            "skills_matched": analysis.skills_matched,
            "skills_missing": analysis.skills_missing,
            "experience_match": analysis.experience_match,
            "education_match": analysis.education_match,
            "overall_fit": analysis.overall_fit,
            "recommendation": analysis.recommendation,
            "threshold_met": analysis.threshold_met,
            "analyzed_at": analysis.analyzed_at.isoformat(),
            "questions": questions_with_responses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get analysis result: {str(e)}")


@router.get("/qualified-candidates/{job_id}")
async def get_qualified_candidates(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get all candidates who meet the threshold for a specific job."""
    try:
        qualified = db.query(CandidateAnalysisResult).filter(
            CandidateAnalysisResult.job_id == job_id,
            CandidateAnalysisResult.threshold_met == True,
            CandidateAnalysisResult.recommendation == "push_to_recruiter"
        ).all()
        
        candidates = []
        for analysis in qualified:
            candidate = db.query(User).filter(User.id == analysis.candidate_id).first()
            candidates.append({
                "analysis_id": analysis.id,
                "candidate_id": analysis.candidate_id,
                "candidate_name": candidate.full_name if candidate else "Unknown",
                "candidate_email": candidate.email if candidate else "Unknown",
                "match_score": analysis.match_score,
                "overall_fit": analysis.overall_fit,
                "analyzed_at": analysis.analyzed_at.isoformat()
            })
        
        return {
            "job_id": job_id,
            "qualified_count": len(candidates),
            "candidates": candidates
        }
        
    except Exception as e:
        logger.error(f"Failed to get qualified candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get qualified candidates: {str(e)}")


# =========================================================================
# AI-Powered Screening Endpoints (using all Ollama models)
# =========================================================================

class AIScreeningRequest(BaseModel):
    """Request model for AI-powered screening analysis."""
    resume_text: str
    jd_text: str
    job_title: str
    candidate_id: Optional[str] = None
    job_id: Optional[str] = None


class AIResponseScoringRequest(BaseModel):
    """Request model for AI-powered response scoring."""
    question: str
    response: str
    question_type: str = "technical"
    related_skill: Optional[str] = None


@router.post("/ai-screen")
async def ai_screen_candidate(request: AIScreeningRequest):
    """
    Full AI-powered screening pipeline using multiple models:
    1. Resume evaluation (llama3)
    2. Technical skill analysis (codellama)
    3. Screening question generation (mistral)
    Returns combined results from all models.
    """
    try:
        # Step 1: Resume evaluation (llama3 → mistral → llama3.2)
        evaluation = ollama_service.evaluate_resume_vs_jd(request.resume_text, request.jd_text)

        # Step 2: Technical skill analysis (codellama → llama3 → mistral)
        tech_analysis = ollama_service.analyze_technical_skills(request.resume_text, request.jd_text)

        # Step 3: Generate screening questions (mistral → llama3 → llama3.2)
        screening_qs = ollama_service.generate_screening_questions(
            request.resume_text, request.jd_text, []
        )

        return {
            "status": "success",
            "job_title": request.job_title,
            "evaluation": evaluation,
            "technical_analysis": tech_analysis,
            "screening_questions": screening_qs,
            "models_used": {
                "evaluation": "llama3",
                "technical_analysis": "codellama",
                "screening_questions": "mistral"
            }
        }

    except Exception as e:
        logger.error(f"AI screening failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI screening failed: {str(e)}")


@router.post("/ai-deep-screen")
async def ai_deep_screen_candidate(request: AIScreeningRequest):
    """
    Deep AI screening using heavy models:
    1. Deep reasoning analysis (deepseek-r1:32b)
    2. Detailed report (llama3.3:70b)
    Best for final-round candidate evaluation.
    """
    try:
        # Deep analysis (deepseek-r1:32b → llama3.3:70b → llama3)
        deep_result = ollama_service.deep_candidate_analysis(request.resume_text, request.jd_text)

        # Detailed report (llama3.3:70b → deepseek-r1:32b → llama3)
        detailed_report = ollama_service.generate_detailed_report(
            request.resume_text, request.jd_text,
            {"deep_analysis": deep_result} if deep_result else {}
        )

        return {
            "status": "success",
            "job_title": request.job_title,
            "deep_analysis": deep_result,
            "detailed_report": detailed_report,
            "models_used": {
                "deep_analysis": "deepseek-r1:32b",
                "detailed_report": "llama3.3:70b"
            }
        }

    except Exception as e:
        logger.error(f"AI deep screening failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI deep screening failed: {str(e)}")


@router.post("/ai-score-response")
async def ai_score_response(request: AIResponseScoringRequest):
    """
    Score a candidate's response to a screening question using AI.
    Uses mistral for fast scoring, with fallback chain.
    """
    try:
        prompt = f"""Score this candidate's response to an interview question on a scale of 0-100.

Question: {request.question}
Question Type: {request.question_type}
{"Related Skill: " + request.related_skill if request.related_skill else ""}

Candidate Response:
{request.response}

Provide:
1. Score (0-100)
2. Strengths (1-2 bullet points)
3. Weaknesses (1-2 bullet points)
4. Improvement suggestion (1 sentence)"""

        result = ollama_service.generate(
            task=TaskType.QUICK_SUMMARY,
            prompt=prompt,
            system="You are an expert interview evaluator. Score responses objectively and provide brief feedback.",
            options={"temperature": 0.3, "num_predict": 400},
        )

        if result:
            return {"status": "success", "scoring": result, "model": "mistral"}
        raise HTTPException(status_code=503, detail="AI scoring unavailable")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI response scoring failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI scoring failed: {str(e)}")
