"""
Resume + Job Description Analysis Service
Analyzes candidate resumes against job descriptions to determine fit and generate screening questions.
"""

import os
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ResumeJDAnalysisService:
    """
    Service for analyzing resumes against job descriptions to:
    1. Calculate match score
    2. Identify skill gaps
    3. Generate screening questions
    4. Score candidate responses
    """

    def __init__(self):
        """Initialize the analysis service."""
        # Configuration for match threshold (can be made configurable)
        self.match_threshold = 75  # Candidates need 75%+ match to be pushed to recruiter

    def analyze_application(
        self,
        resume_text: str,
        job_description: str,
        job_title: str,
        candidate_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main method to analyze a candidate's resume against a job description.

        Args:
            resume_text: The text content of the candidate's resume
            job_description: The job description text
            job_title: The title of the job being applied for
            candidate_info: Additional candidate information (name, email, etc.)

        Returns:
            Dictionary containing:
            - match_score: 0-100 score
            - skills_matched: List of skills found in both resume and JD
            - skills_missing: List of skills in JD but not in resume
            - experience_match: Boolean indicating if experience requirements are met
            - education_match: Boolean indicating if education requirements are met
            - overall_fit: "high" | "medium" | "low"
            - screening_questions: List of generated questions
            - recommendation: "push_to_recruiter" | "hold" | "reject"
        """
        candidate_info = candidate_info or {}

        # Extract key information from both documents
        resume_data = self._parse_resume(resume_text)
        jd_data = self._parse_job_description(job_description)

        # Calculate match score
        match_score = self._calculate_match_score(resume_data, jd_data)

        # Identify skill gaps
        skills_matched = self._find_matching_skills(resume_data, jd_data)
        skills_missing = self._find_missing_skills(resume_data, jd_data)

        # Check experience requirements
        experience_match = self._check_experience_match(resume_data, jd_data)

        # Check education requirements
        education_match = self._check_education_match(resume_data, jd_data)

        # Generate screening questions
        screening_questions = self._generate_screening_questions(
            resume_data, jd_data, skills_missing, job_title
        )

        # Determine overall fit and recommendation
        overall_fit = self._determine_fit_level(match_score, experience_match, education_match)
        recommendation = self._determine_recommendation(
            match_score, overall_fit, experience_match, education_match
        )

        return {
            "analyzed_at": datetime.utcnow().isoformat(),
            "job_title": job_title,
            "candidate_info": candidate_info,
            "match_score": match_score,
            "skills_matched": skills_matched,
            "skills_missing": skills_missing,
            "experience_match": experience_match,
            "education_match": education_match,
            "overall_fit": overall_fit,
            "screening_questions": screening_questions,
            "recommendation": recommendation,
            "threshold_met": match_score >= self.match_threshold
        }

    def _parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract key information from resume text.

        Returns:
            {
                "skills": List[str],
                "experience_years": int,
                "education_level": str,
                "key_qualifications": List[str],
                "raw_sections": Dict
            }
        """
        # Extract skills (common technical and soft skills)
        skills = self._extract_skills(resume_text)

        # Extract experience
        experience_years = self._extract_experience_years(resume_text)

        # Extract education level
        education_level = self._extract_education_level(resume_text)

        # Extract key qualifications/phrases
        key_qualifications = self._extract_key_phrases(resume_text)

        return {
            "skills": skills,
            "experience_years": experience_years,
            "education_level": education_level,
            "key_qualifications": key_qualifications,
            "raw_text": resume_text
        }

    def _parse_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract key information from job description.

        Returns:
            {
                "required_skills": List[str],
                "required_experience_years": int,
                "required_education_level": str,
                "key_responsibilities": List[str],
                "qualifications": List[str]
            }
        """
        # Extract required skills
        required_skills = self._extract_skills(jd_text)

        # Extract required experience
        required_experience = self._extract_required_experience(jd_text)

        # Extract required education
        required_education = self._extract_required_education(jd_text)

        # Extract key responsibilities
        responsibilities = self._extract_responsibilities(jd_text)

        # Extract qualifications
        qualifications = self._extract_qualifications(jd_text)

        return {
            "required_skills": required_skills,
            "required_experience_years": required_experience,
            "required_education_level": required_education,
            "key_responsibilities": responsibilities,
            "qualifications": qualifications,
            "raw_text": jd_text
        }

    def _calculate_match_score(self, resume_data: Dict, jd_data: Dict) -> int:
        """
        Calculate overall match score (0-100) based on multiple factors.

        Weights:
        - Skill match: 40%
        - Experience: 30%
        - Education: 20%
        - Keywords/qualifications: 10%
        """
        # Skill match score
        skill_score = self._calculate_skill_match_score(
            resume_data.get("skills", []),
            jd_data.get("required_skills", [])
        )

        # Experience score
        experience_score = self._calculate_experience_score(
            resume_data.get("experience_years", 0),
            jd_data.get("required_experience_years", 0)
        )

        # Education score
        education_score = self._calculate_education_score(
            resume_data.get("education_level", ""),
            jd_data.get("required_education_level", "")
        )

        # Keyword/qualification score
        keyword_score = self._calculate_keyword_match_score(
            resume_data.get("key_qualifications", []),
            jd_data.get("qualifications", [])
        )

        # Weighted overall score
        overall_score = (
            skill_score * 0.40 +
            experience_score * 0.30 +
            education_score * 0.20 +
            keyword_score * 0.10
        )

        return int(overall_score)

    def _calculate_skill_match_score(self, resume_skills: List[str], jd_skills: List[str]) -> int:
        """Calculate skill match percentage (0-100)."""
        if not jd_skills:
            return 100  # No skills required, full credit

        resume_skills_set = set([s.lower() for s in resume_skills])
        jd_skills_set = set([s.lower() for s in jd_skills])

        # Count matching skills (including partial matches)
        matched = 0
        for jd_skill in jd_skills_set:
            for resume_skill in resume_skills_set:
                if jd_skill in resume_skill or resume_skill in jd_skill:
                    matched += 1
                    break

        return int((matched / len(jd_skills_set)) * 100) if jd_skills_set else 0

    def _calculate_experience_score(self, resume_exp: int, required_exp: int) -> int:
        """Calculate experience match score (0-100)."""
        if required_exp == 0:
            return 100  # No experience requirement

        if resume_exp >= required_exp:
            # Bonus for exceeding requirements (up to 100%)
            excess = resume_exp - required_exp
            bonus = min(20, excess * 5)
            return min(100, 80 + bonus)
        else:
            # Penalty for not meeting requirements
            deficit = required_exp - resume_exp
            penalty = min(80, deficit * 20)
            return max(0, 100 - penalty)

    def _calculate_education_score(self, resume_edu: str, required_edu: str) -> int:
        """Calculate education match score (0-100)."""
        education_hierarchy = {
            "phd": 5,
            "doctorate": 5,
            "master": 4,
            "mba": 4,
            "bachelor": 3,
            "bs": 3,
            "ba": 3,
            "btech": 3,
            "be": 3,
            "associate": 2,
            "diploma": 2,
            "high school": 1,
            "secondary": 1
        }

        resume_level = self._normalize_education(resume_edu, education_hierarchy)
        required_level = self._normalize_education(required_edu, education_hierarchy)

        if required_level == 0:
            return 100  # No education requirement

        if resume_level >= required_level:
            return 100
        else:
            # Partial credit for lower education
            return int((resume_level / required_level) * 70)

    def _normalize_education(self, edu_str: str, hierarchy: Dict[str, int]) -> int:
        """Normalize education string to hierarchy level."""
        if not edu_str:
            return 0

        edu_lower = edu_str.lower()
        for key, level in hierarchy.items():
            if key in edu_lower:
                return level
        return 0

    def _calculate_keyword_match_score(self, resume_keywords: List[str], jd_keywords: List[str]) -> int:
        """Calculate keyword/qualification match score (0-100)."""
        if not jd_keywords:
            return 100

        resume_keywords_set = set([k.lower() for k in resume_keywords])
        jd_keywords_set = set([k.lower() for k in jd_keywords])

        matched = len(resume_keywords_set & jd_keywords_set)
        return int((matched / len(jd_keywords_set)) * 100) if jd_keywords_set else 0

    def _find_matching_skills(self, resume_data: Dict, jd_data: Dict) -> List[str]:
        """Find skills present in both resume and JD."""
        resume_skills = set([s.lower() for s in resume_data.get("skills", [])])
        jd_skills = set([s.lower() for s in jd_data.get("required_skills", [])])

        matched = []
        for jd_skill in jd_skills:
            for resume_skill in resume_skills:
                if jd_skill in resume_skill or resume_skill in jd_skill:
                    matched.append(jd_skill)
                    break

        return matched

    def _find_missing_skills(self, resume_data: Dict, jd_data: Dict) -> List[str]:
        """Find skills in JD but not in resume."""
        resume_skills = set([s.lower() for s in resume_data.get("skills", [])])
        jd_skills = set([s.lower() for s in jd_data.get("required_skills", [])])

        missing = []
        for jd_skill in jd_skills:
            found = False
            for resume_skill in resume_skills:
                if jd_skill in resume_skill or resume_skill in jd_skill:
                    found = True
                    break
            if not found:
                missing.append(jd_skill)

        return missing

    def _check_experience_match(self, resume_data: Dict, jd_data: Dict) -> bool:
        """Check if candidate meets experience requirements."""
        resume_exp = resume_data.get("experience_years", 0)
        required_exp = jd_data.get("required_experience_years", 0)
        return resume_exp >= required_exp

    def _check_education_match(self, resume_data: Dict, jd_data: Dict) -> bool:
        """Check if candidate meets education requirements."""
        education_hierarchy = {
            "phd": 5,
            "doctorate": 5,
            "master": 4,
            "mba": 4,
            "bachelor": 3,
            "bs": 3,
            "ba": 3,
            "btech": 3,
            "be": 3,
            "associate": 2,
            "diploma": 2,
            "high school": 1,
            "secondary": 1
        }

        resume_level = self._normalize_education(
            resume_data.get("education_level", ""),
            education_hierarchy
        )
        required_level = self._normalize_education(
            jd_data.get("required_education_level", ""),
            education_hierarchy
        )

        return resume_level >= required_level

    def _determine_fit_level(self, match_score: int, exp_match: bool, edu_match: bool) -> str:
        """Determine overall fit level."""
        if match_score >= 80 and exp_match and edu_match:
            return "high"
        elif match_score >= 60:
            return "medium"
        else:
            return "low"

    def _determine_recommendation(self, match_score: int, fit_level: str, exp_match: bool, edu_match: bool) -> str:
        """Determine recommendation for the candidate."""
        if match_score >= self.match_threshold and fit_level == "high":
            return "push_to_recruiter"
        elif match_score >= self.match_threshold - 10:
            return "hold"
        else:
            return "reject"

    def _generate_screening_questions(
        self,
        resume_data: Dict,
        jd_data: Dict,
        missing_skills: List[str],
        job_title: str
    ) -> List[Dict[str, Any]]:
        """
        Generate screening questions based on the analysis.

        Returns:
            List of questions with:
            - question: str
            - question_type: "technical" | "experience" | "behavioral"
            - priority: "high" | "medium" | "low"
        """
        questions = []

        # Technical questions based on missing skills
        for skill in missing_skills[:3]:  # Limit to top 3 missing skills
            questions.append({
                "question": f"Can you describe your experience with {skill}?",
                "question_type": "technical",
                "priority": "high",
                "related_skill": skill
            })

        # Experience questions based on responsibilities
        responsibilities = jd_data.get("key_responsibilities", [])
        for resp in responsibilities[:2]:
            questions.append({
                "question": f"Tell us about a time you handled: {resp}",
                "question_type": "experience",
                "priority": "medium"
            })

        # Behavioral questions
        questions.append({
            "question": "What interests you most about this role?",
            "question_type": "behavioral",
            "priority": "medium"
        })

        questions.append({
            "question": "Describe a challenging project you worked on and how you overcame obstacles.",
            "question_type": "behavioral",
            "priority": "low"
        })

        return questions

    def score_candidate_responses(
        self,
        questions: List[Dict[str, Any]],
        responses: List[str]
    ) -> Dict[str, Any]:
        """
        Score candidate's responses to screening questions.

        Args:
            questions: List of questions with metadata
            responses: List of candidate responses (in same order)

        Returns:
            {
                "overall_score": 0-100,
                "question_scores": List of individual scores,
                "recommendation": "proceed" | "review" | "reject"
            }
        """
        if len(questions) != len(responses):
            logger.warning("Number of questions and responses don't match")
            return {"overall_score": 0, "recommendation": "reject"}

        question_scores = []
        for i, (question, response) in enumerate(zip(questions, responses)):
            score = self._score_single_response(question, response)
            question_scores.append({
                "question": question.get("question"),
                "response": response,
                "score": score,
                "question_type": question.get("question_type")
            })

        # Calculate overall score (weighted by priority)
        weighted_scores = []
        for qs in question_scores:
            weight = {"high": 1.5, "medium": 1.0, "low": 0.5}.get(qs["question_type"], 1.0)
            weighted_scores.append(qs["score"] * weight)

        overall_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0

        # Determine recommendation
        if overall_score >= 70:
            recommendation = "proceed"
        elif overall_score >= 50:
            recommendation = "review"
        else:
            recommendation = "reject"

        return {
            "overall_score": int(overall_score),
            "question_scores": question_scores,
            "recommendation": recommendation
        }

    def _score_single_response(self, question: Dict[str, Any], response: str) -> int:
        """
        Score a single response (0-100).

        Simple heuristic scoring based on:
        - Response length (too short = bad)
        - Contains relevant keywords
        - Sentence structure
        """
        if not response or len(response.strip()) < 20:
            return 20  # Too short

        score = 50  # Base score

        # Length bonus (reasonable length is good)
        word_count = len(response.split())
        if 20 <= word_count <= 100:
            score += 20
        elif word_count > 100:
            score += 10

        # Keyword bonus (if related_skill exists, check for it)
        related_skill = question.get("related_skill")
        if related_skill and related_skill.lower() in response.lower():
            score += 15

        # Structure bonus (multiple sentences)
        if response.count('.') >= 2:
            score += 10

        return min(100, score)

    # =========================================================================
    # Helper methods for text extraction
    # =========================================================================

    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using common tech/soft skills."""
        # Common technical skills
        tech_skills = [
            "python", "java", "javascript", "typescript", "react", "angular", "vue",
            "node.js", "django", "flask", "spring", "sql", "nosql", "mongodb",
            "postgresql", "mysql", "aws", "azure", "gcp", "docker", "kubernetes",
            "git", "ci/cd", "agile", "scrum", "machine learning", "data science",
            "deep learning", "nlp", "computer vision", "tensorflow", "pytorch",
            "react native", "flutter", "ios", "android", "swift", "kotlin",
            "html", "css", "sass", "webpack", "rest api", "graphql", "microservices",
            "linux", "bash", "powershell", "cloud", "devops", "testing", "junit"
        ]

        # Common soft skills
        soft_skills = [
            "communication", "leadership", "teamwork", "problem solving",
            "analytical", "critical thinking", "adaptability", "creativity",
            "time management", "project management", "collaboration"
        ]

        all_skills = tech_skills + soft_skills
        found_skills = []

        text_lower = text.lower()
        for skill in all_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)

        return found_skills

    def _extract_experience_years(self, text: str) -> int:
        """Extract years of experience from text."""
        # Look for patterns like "5 years", "5+ years", "5 years of experience"
        patterns = [
            r'(\d+)\+?\s*years?\s*(of)?\s*(experience)?',
            r'(\d+)\s*years?',
            r'experience[:\s]*(\d+)\+?'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                try:
                    # Take the first match and extract the number
                    match = matches[0]
                    if isinstance(match, tuple):
                        num = match[0]
                    else:
                        num = match
                    return int(num)
                except (ValueError, IndexError):
                    continue

        return 0

    def _extract_education_level(self, text: str) -> str:
        """Extract education level from text."""
        education_keywords = {
            "phd": ["phd", "doctorate", "doctor of philosophy"],
            "master": ["master", "m.s.", "m.sc", "mba", "m.tech"],
            "bachelor": ["bachelor", "b.s.", "b.sc", "b.tech", "b.e.", "ba", "bs"],
            "associate": ["associate", "diploma"],
            "high school": ["high school", "secondary", "12th", "10+2"]
        }

        text_lower = text.lower()
        for level, keywords in education_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level

        return ""

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key qualification phrases from text."""
        # Look for action verbs and qualifications
        action_verbs = [
            "developed", "implemented", "managed", "led", "designed",
            "created", "built", "deployed", "optimized", "analyzed",
            "coordinated", "executed", "delivered", "achieved"
        ]

        phrases = []
        sentences = text.split('.')
        for sentence in sentences:
            for verb in action_verbs:
                if verb.lower() in sentence.lower():
                    phrases.append(sentence.strip())
                    break

        return phrases[:10]  # Limit to top 10

    def _extract_required_experience(self, jd_text: str) -> int:
        """Extract required experience years from JD."""
        patterns = [
            r'(\d+)\+?\s*years?\s*(of)?\s*experience',
            r'minimum\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*(or more)?'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, jd_text.lower())
            if matches:
                try:
                    match = matches[0]
                    if isinstance(match, tuple):
                        num = match[0]
                    else:
                        num = match
                    return int(num)
                except (ValueError, IndexError):
                    continue

        return 0

    def _extract_required_education(self, jd_text: str) -> str:
        """Extract required education level from JD."""
        return self._extract_education_level(jd_text)

    def _extract_responsibilities(self, jd_text: str) -> List[str]:
        """Extract key responsibilities from JD."""
        # Look for bullet points or numbered lists
        responsibilities = []

        # Split by common delimiters
        lines = re.split(r'[•\-\*]\s*|\n\d+\.\s*', jd_text)
        for line in lines:
            line = line.strip()
            if 10 <= len(line) <= 200:  # Reasonable length
                responsibilities.append(line)

        return responsibilities[:5]  # Limit to top 5

    def _extract_qualifications(self, jd_text: str) -> List[str]:
        """Extract qualifications/requirements from JD."""
        qualifications = []

        # Look for qualification-related sections
        sections = re.split(r'requirements|qualifications|skills|what you need', jd_text, flags=re.IGNORECASE)
        if len(sections) > 1:
            # Take the first section after these keywords
            content = sections[1]
            lines = content.split('\n')[:5]
            for line in lines:
                line = line.strip()
                if line and len(line) > 5:
                    qualifications.append(line)

        return qualifications
