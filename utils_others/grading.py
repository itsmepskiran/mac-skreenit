"""
Shared Grading Utility for Video Interview Analysis
Single source of truth for grade calculations across frontend and backend.
"""

from typing import Dict, Any, Tuple


class GradeCalculator:
    """
    Standardized grading system for all analysis parameters.
    Used by: PDF reports, assessment reports, frontend displays
    """
    
    # Standard grade scale - single source of truth
    GRADE_SCALE = [
        {"min": 90, "grade": "A+", "label": "Exceptional", "color": "#059669"},
        {"min": 80, "grade": "A", "label": "Excellent", "color": "#10b981"},
        {"min": 70, "grade": "B+", "label": "Very Good", "color": "#22c55e"},
        {"min": 60, "grade": "B", "label": "Good", "color": "#84cc16"},
        {"min": 50, "grade": "C", "label": "Average", "color": "#eab308"},
        {"min": 40, "grade": "D", "label": "Below Average", "color": "#f97316"},
        {"min": 0, "grade": "F", "label": "Poor", "color": "#dc2626"},
    ]
    
    @classmethod
    def score_to_grade(cls, score: int) -> Dict[str, Any]:
        """
        Convert numeric score to grade information.
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            Dict with grade, label, description, color
        """
        score = max(0, min(100, int(score)))
        
        for grade_info in cls.GRADE_SCALE:
            if score >= grade_info["min"]:
                return {
                    "grade": grade_info["grade"],
                    "label": grade_info["label"],
                    "description": grade_info["label"],
                    "color": grade_info["color"],
                    "score": score
                }
        
        return {"grade": "F", "label": "Poor", "description": "Poor", "color": "#dc2626", "score": score}
    
    @classmethod
    def get_grade_index(cls) -> list:
        """Get grade index for reports."""
        return [
            {"grade": "A+", "range": "90-100", "meaning": "Exceptional performance"},
            {"grade": "A", "range": "80-89", "meaning": "Excellent performance"},
            {"grade": "B+", "range": "70-79", "meaning": "Very Good performance"},
            {"grade": "B", "range": "60-69", "meaning": "Good performance"},
            {"grade": "C", "range": "50-59", "meaning": "Average performance"},
            {"grade": "D", "range": "40-49", "meaning": "Below Average"},
            {"grade": "F", "range": "0-39", "meaning": "Poor - Needs Improvement"},
        ]
    
    @classmethod
    def calculate_wpm_grade(cls, wpm: int) -> str:
        """Calculate grade for speaking pace (WPM)."""
        if wpm == 0:
            return "N/A"
        if 120 <= wpm <= 150:
            return "A"
        if 100 <= wpm < 120 or 150 < wpm <= 170:
            return "B"
        if 80 <= wpm < 100 or 170 < wpm <= 190:
            return "C"
        return "D"
    
    @classmethod
    def calculate_filler_grade(cls, count: int) -> str:
        """Calculate grade for filler words."""
        if count == 0:
            return "A+"
        if count <= 2:
            return "A"
        if count <= 5:
            return "B"
        if count <= 10:
            return "C"
        return "D"


# Convenience function for simple grade calculation
def get_grade(score: int) -> str:
    """Get just the grade letter for a score."""
    return GradeCalculator.score_to_grade(score)["grade"]


def get_grade_with_color(score: int) -> Tuple[str, str]:
    """Get grade and color for a score."""
    result = GradeCalculator.score_to_grade(score)
    return result["grade"], result["color"]
