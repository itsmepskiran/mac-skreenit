"""
Premium Assessment Models
"""
from pydantic import BaseModel
from typing import List, Optional

# ── Legacy models (kept for /assessment-response endpoint) ────────────────────
class AssessmentQuestion(BaseModel):
    id: str
    question: str
    duration: int = 60
    instructions: Optional[str] = None

class AssessmentQuestionsResponse(BaseModel):
    questions: List[AssessmentQuestion]
    totalDuration: int
    assessmentType: str

class AssessmentResponse(BaseModel):
    planId: str
    mode: str
    questionId: str
    videoPath: str
    duration: int
    timestamp: str

# ── New models used by the redesigned assessment UI ───────────────────────────
class ExerciseResponse(BaseModel):
    """One exercise response from the frontend."""
    questionId: str                         # "{sectionId}_{itemId}"
    type: str                               # voice | mcq | code | text | topic
    text: Optional[str] = None             # written answer, code, or chosen topic
    hasRecording: bool = False
    selectedIdx: Optional[int] = None      # MCQ option index (0-based)

class AssessmentFinishRequest(BaseModel):
    planId: str
    mode: str
    responses: List[ExerciseResponse]
    timeTakenSeconds: Optional[int] = None
