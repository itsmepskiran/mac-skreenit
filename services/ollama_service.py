"""
Ollama Question Generation Service
Generates assessment questions dynamically using local LLM models
"""

import requests
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Enum for different task types"""
    EVALUATION = "evaluation"
    TECHNICAL_ANALYSIS = "technical_analysis"
    QUICK_SUMMARY = "quick_summary"
    SCREENING = "screening"
    DEEP_ANALYSIS = "deep_analysis"
    QUESTION_GENERATION = "question_generation"


class OllamaService:
    """Service for generating assessment questions using Ollama"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.models = {
            'general': 'mistral',
            'technical': 'codellama',
            'advanced': 'llama3',
        }
        self.cache = {}
        self.cache_ttl = 3600

    def is_ollama_available(self) -> bool:
        """Check if Ollama server is running AND has at least one model loaded."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                return False
            data = response.json()
            models = data.get("models", [])
            if not models:
                logger.warning("Ollama is running but no models are loaded")
                return False
            return True
        except Exception:
            logger.warning("Ollama server not available at %s", self.base_url)
            return False

    def generate_questions(
        self,
        assessment_name: str,
        assessment_desc: str,
        skills: str,
        num_questions: int = 5,
        assessment_type: str = 'general'
    ) -> List[Dict[str, Any]]:
        """Generate open-ended assessment questions using Ollama LLM"""
        cache_key = f"{assessment_name}_{num_questions}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached questions for {assessment_name}")
                return cached_data

        if not self.is_ollama_available():
            logger.warning("Ollama not available, returning empty list")
            return []

        model = self._resolve_model(assessment_type)
        if not model:
            logger.warning("No suitable Ollama model found, returning empty list")
            return []

        prompt = self._create_prompt(assessment_name, assessment_desc, skills, num_questions)

        try:
            questions = self._call_ollama(model, prompt, num_questions)
            self.cache[cache_key] = (questions, datetime.now())
            return questions
        except Exception as e:
            logger.error(f"Failed to generate questions: {str(e)}")
            return []

    def generate_mcq_questions(
        self,
        assessment_name: str,
        assessment_desc: str,
        skills: str,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate MCQ questions with 4 options using Ollama. Correct answer is always option A."""
        cache_key = f"mcq_{assessment_name}_{num_questions}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached MCQ questions for {assessment_name}")
                return cached_data

        if not self.is_ollama_available():
            return []

        model = self._resolve_model('general')
        if not model:
            return []

        prompt = f"""You are an expert assessment designer. Generate exactly {num_questions} multiple-choice questions for:

Assessment: {assessment_name}
Description: {assessment_desc}
Skills assessed: {skills}

Output ONLY the questions in this exact format (no extra text, no numbering):

Q: <question text>
A: <correct answer>
B: <plausible wrong answer>
C: <plausible wrong answer>
D: <plausible wrong answer>

Rules:
- Option A is ALWAYS the correct answer
- Distractors (B, C, D) must be plausible but clearly wrong
- Questions must test the listed skills
- Keep question text concise and professional
- No preamble, no explanations, just the Q/A/B/C/D blocks separated by blank lines"""

        try:
            url = f"{self.base_url}/api/generate"
            response = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.6},
                timeout=180,
            )
            response.raise_for_status()
            questions = self._parse_mcq_response(response.json().get("response", ""), num_questions)
            self.cache[cache_key] = (questions, datetime.now())
            logger.info(f"Generated {len(questions)} MCQ questions for {assessment_name}")
            return questions
        except Exception as e:
            logger.error(f"MCQ generation failed: {str(e)}")
            return []

    def _parse_mcq_response(self, text: str, num_questions: int) -> List[Dict[str, Any]]:
        """Parse Q/A/B/C/D blocks from Ollama MCQ response."""
        questions = []
        current: Dict[str, Any] = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith('Q:'):
                if current.get('content') and current.get('options'):
                    questions.append(current)
                current = {'content': line[2:].strip(), 'options': [], 'correct': 0}
            elif line.upper().startswith('A:') and current:
                current['options'].append(line[2:].strip())
            elif line.upper().startswith('B:') and current:
                current['options'].append(line[2:].strip())
            elif line.upper().startswith('C:') and current:
                current['options'].append(line[2:].strip())
            elif line.upper().startswith('D:') and current:
                current['options'].append(line[2:].strip())
        if current.get('content') and current.get('options'):
            questions.append(current)

        result = []
        for i, q in enumerate(questions[:num_questions], 1):
            opts = q['options'][:4]
            while len(opts) < 4:
                opts.append('None of the above')
            result.append({'id': f'q{i}', 'content': q['content'], 'options': opts, 'correct': 0})
        return result

    def _resolve_model(self, assessment_type: str) -> Optional[str]:
        """Return the best available model for the given assessment type.
        Falls back to any installed model rather than failing."""
        preferred = self.models.get(assessment_type, 'mistral')
        available = self.get_available_models()
        if not available:
            return None
        # Try preferred first, then any model that contains the name, then first available
        for m in available:
            if preferred in m:
                return m
        return available[0]

    def _create_prompt(
        self,
        assessment_name: str,
        assessment_desc: str,
        skills: str,
        num_questions: int
    ) -> str:
        """Create a prompt for question generation"""
        return f"""You are an expert assessment designer. Generate exactly {num_questions} interview/assessment questions for:

Assessment: {assessment_name}
Description: {assessment_desc}
Skills: {skills}

Generate {num_questions} diverse, practical questions that:
- Are answerable in 60-120 seconds
- Test the listed skills
- Mix scenario-based, knowledge, technical, and behavioral questions
- Are open-ended (not yes/no)
- Include real-world scenarios

Format: Numbered list only, one question per line

Questions:"""

    def _call_ollama(self, model: str, prompt: str, num_questions: int) -> List[Dict[str, Any]]:
        """Call Ollama API to generate questions"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
        }

        try:
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            questions = self._parse_questions(response_text, num_questions)
            logger.info(f"Generated {len(questions)} questions using {model}")
            return questions
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            raise

    def _parse_questions(self, response_text: str, num_questions: int) -> List[Dict[str, Any]]:
        """Parse LLM response into structured questions"""
        questions = []
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        durations = [60, 75, 90, 75, 90, 120, 60, 75]
        question_count = 0

        for line in lines:
            if not line or len(line) < 10:
                continue
            if line[0].isdigit():
                line = line.lstrip('0123456789. ').strip()
            if line and len(line) > 10:
                duration = durations[question_count % len(durations)]
                questions.append({
                    'id': f'q_{question_count + 1}',
                    'question': line,
                    'duration': duration
                })
                question_count += 1
                if question_count >= num_questions:
                    break

        while len(questions) < num_questions:
            questions.append({
                'id': f'q_{len(questions) + 1}',
                'question': f'Question {len(questions) + 1}: Describe your experience with the skills assessed in this evaluation.',
                'duration': 90
            })

        return questions[:num_questions]

    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                return models
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return []

    def verify_model(self, model_name: str) -> bool:
        """Verify if a specific model is available"""
        available = self.get_available_models()
        return any(model_name in m for m in available)

    def generate_coding_challenge_questions(
        self,
        platform: str,
        num_questions: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generate coding problem descriptions for a specific language using Ollama."""
        cache_key = f"coding_challenge_{platform}_{num_questions}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return cached_data

        if not self.is_ollama_available():
            return []

        model = self._resolve_model('technical')
        if not model:
            return []

        prompt = f"""Generate exactly {num_questions} beginner coding problems for {platform}.

Each problem should be solvable in 20-30 minutes by an entry-level programmer.
Topics to cover: loops, conditionals, functions, basic data structures.

Output exactly {num_questions} problems as a numbered list.
Each item: 2-4 sentences describing the function name, requirements, and one concrete input/output example.
No starter code. No extra commentary. Just the numbered list.

Problems:"""

        try:
            url = f"{self.base_url}/api/generate"
            response = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.55},
                timeout=180,
            )
            response.raise_for_status()
            questions = self._parse_questions(response.json().get("response", ""), num_questions)
            for q in questions:
                q['platform'] = platform
            self.cache[cache_key] = (questions, datetime.now())
            logger.info(f"Generated {len(questions)} coding challenges for {platform}")
            return questions
        except Exception as e:
            logger.error(f"Coding challenge generation failed for {platform}: {str(e)}")
            return []

    def generate_typing_paragraph(self, duration_minutes: int) -> str:
        """Generate a long prose passage sized for a typing speed test of given duration."""
        duration_minutes = max(1, min(10, duration_minutes))
        target_words = int(100 * duration_minutes * 1.5)

        cache_key = f"typing_paragraph_{duration_minutes}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached typing paragraph for {duration_minutes}min")
                return cached_data

        if not self.is_ollama_available():
            return self._get_typing_fallback(duration_minutes)

        model = self._resolve_model('general')
        if not model:
            return self._get_typing_fallback(duration_minutes)

        prompt = (
            f"Write a continuous, engaging prose passage of approximately {target_words} words "
            f"for a professional typing speed test.\n\n"
            f"Requirements:\n"
            f"- Exactly {target_words} words of flowing prose — no headings, no bullet points, no lists\n"
            f"- Cover topics such as workplace communication, technology, nature, or everyday professional life\n"
            f"- Use varied sentence lengths and natural punctuation (commas, periods, semicolons, colons, "
            f"quotation marks, exclamation marks)\n"
            f"- Make it interesting and educational so the reader stays engaged\n"
            f"- Do NOT include any preamble, title, or explanation — start directly with the first word\n\n"
            f"Begin the passage now:"
        )

        try:
            url = f"{self.base_url}/api/generate"
            response = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.72},
                timeout=300,
            )
            response.raise_for_status()
            raw = response.json().get("response", "").strip()

            # Strip common preamble patterns Ollama sometimes adds
            lines = raw.split('\n')
            clean = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if clean:
                        clean.append(' ')
                    continue
                low = stripped.lower()
                if any(low.startswith(p) for p in ('here is', 'here\'s', 'passage:', 'typing test:', '#')):
                    continue
                clean.append(stripped)
            text = ' '.join(clean).strip()

            if len(text.split()) < target_words * 0.4:
                logger.warning("Ollama produced too short a typing paragraph; using fallback")
                return self._get_typing_fallback(duration_minutes)

            self.cache[cache_key] = (text, datetime.now())
            logger.info(f"Generated typing paragraph: {len(text.split())} words for {duration_minutes}min test")
            return text
        except Exception as e:
            logger.error(f"Typing paragraph generation failed: {e}")
            return self._get_typing_fallback(duration_minutes)

    def _get_typing_fallback(self, duration_minutes: int) -> str:
        """Return a fallback paragraph long enough for the given test duration."""
        base = (
            "In today's fast-paced digital world, the ability to communicate effectively through written words "
            "has become more important than ever before. Whether you are drafting an important email to a senior "
            "colleague, preparing a detailed report for a client presentation, or simply responding to messages "
            "in a professional chat, your typing speed and accuracy directly impact your productivity and "
            "professional image. Many employers now consider keyboard proficiency a fundamental skill, alongside "
            "communication abilities and technical knowledge. The modern workplace demands that professionals "
            "express their ideas clearly, concisely, and without hesitation. A well-articulated message, free of "
            "typographical errors and grammatical mistakes, demonstrates attention to detail and a commitment to "
            "excellence that resonates with supervisors, peers, and clients alike. Beyond the professional realm, "
            "fast and accurate typing enables you to capture your thoughts before they fade from memory, allowing "
            "for more creative expression in both personal and professional contexts. The best typists do not "
            "merely move their fingers quickly across the keyboard; they have internalized the layout so thoroughly "
            "that each keystroke becomes an extension of their thought process, creating a seamless flow between "
            "intention and execution. This level of mastery comes only through consistent practice and genuine "
            "dedication to improvement. Technology continues to evolve at a rapid pace, bringing new tools, "
            "platforms, and communication channels that require adaptability and a willingness to learn "
            "continuously. Organizations that embrace digital transformation tend to outperform their competitors "
            "by streamlining workflows, reducing manual processes, and enabling teams to collaborate more "
            "efficiently across geographical boundaries. Remote work has placed renewed emphasis on written "
            "communication, as virtual teams rely almost exclusively on emails, messaging platforms, and "
            "collaborative documents to coordinate their efforts. Scientific research demonstrates that individuals "
            "who regularly practise their typing skills show measurable improvements in overall productivity. "
            "The connection between physical dexterity and cognitive performance is well-documented; many experts "
            "note that the rhythmic nature of typing can help stimulate creative thinking and maintain focus "
            "during long work sessions. As artificial intelligence continues to transform various industries, "
            "human professionals who can quickly and accurately translate their expertise into written form will "
            "remain indispensable, particularly in roles requiring nuanced judgment, empathy, and creative "
            "problem-solving. Developing strong keyboard habits early in one's career pays dividends throughout "
            "an entire professional lifetime. Practice sessions need not be long; even ten focused minutes each "
            "day can produce significant results over the course of a few weeks. "
        )
        target_words = int(100 * duration_minutes * 1.5)
        words = base.split()
        result: list = []
        while len(result) < target_words:
            result.extend(words)
        return ' '.join(result[:target_words])

    def clear_cache(self):
        """Clear the question cache"""
        self.cache.clear()
        logger.info("Question cache cleared")

    def generate_interview_questions(self, resume_text: str, num_questions: int = 3) -> Optional[List[str]]:
        """Generate personalised interview questions from a candidate's resume text.
        Returns a plain list of question strings, or None if Ollama is unavailable."""
        if not self.is_ollama_available():
            logger.warning("Ollama not available — skipping resume-based question generation")
            return None

        model = self._resolve_model('general')
        if not model:
            return None

        prompt = f"""You are an expert HR interviewer. Read the candidate's resume below and generate exactly {num_questions} personalised interview questions.

Resume:
{resume_text[:4000]}

Rules:
- Each question must be specific to this candidate's actual experience, skills, or background shown in the resume
- Do NOT ask generic questions like "tell me about yourself" or "why do you want this job"
- Questions should be open-ended and answerable in 60-90 seconds
- Output ONLY the {num_questions} questions as a numbered list, one per line, nothing else

Questions:"""

        try:
            url = f"{self.base_url}/api/generate"
            response = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.7},
                timeout=60,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            questions = []
            for line in raw.split("\n"):
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                # Strip leading numbering
                if line[0].isdigit():
                    line = line.lstrip("0123456789.) ").strip()
                if line and len(line) > 10:
                    questions.append(line)
                if len(questions) >= num_questions:
                    break
            logger.info(f"Generated {len(questions)} resume-based interview questions")
            return questions if questions else None
        except Exception as e:
            logger.error(f"generate_interview_questions failed: {e}")
            return None

    def generate_questions_from_jd(self, jd_text: str, num_questions: int = 8) -> List[Dict[str, Any]]:
        """Generate interview questions from job description using Ollama"""
        cache_key = f"jd_questions_{hash(jd_text[:100])}_{num_questions}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info("Using cached JD questions")
                return cached_data

        try:
            if not self.is_ollama_available():
                logger.warning("Ollama not available for JD question generation")
                return []

            prompt = f"""Based on the following job description, generate {num_questions} interview questions that would be effective for evaluating candidates for this role.

Job Description:
{jd_text}

Please provide {num_questions} specific, role-relevant interview questions. Format each question as JSON with 'question' and 'category' fields."""

            model = self.models.get('general', 'mistral')
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return []

            result = response.json()
            response_text = result.get('response', '')
            questions = self._parse_jd_questions(response_text, num_questions)

            # Cache the result
            self.cache[cache_key] = (questions, datetime.now())
            return questions

        except Exception as e:
            logger.error(f"Failed to generate questions from JD: {str(e)}")
            return []

    def _parse_jd_questions(self, response_text: str, num_questions: int) -> List[Dict[str, Any]]:
        """Parse JD-based questions from Ollama response"""
        questions = []
        try:
            # Try to extract JSON objects from the response
            import re
            json_pattern = r'\{[^}]+\}'
            matches = re.finditer(json_pattern, response_text)

            for match in matches:
                try:
                    q = json.loads(match.group())
                    if 'question' in q:
                        questions.append({
                            'question': q.get('question', ''),
                            'category': q.get('category', 'General'),
                            'priority': 'Medium',
                            'preparation_tip': ''
                        })
                except json.JSONDecodeError:
                    continue

            if not questions:
                # Fallback: split by lines and treat each as a question
                lines = response_text.strip().split('\n')
                for i, line in enumerate(lines[:num_questions]):
                    if line.strip() and not line.startswith('#'):
                        questions.append({
                            'question': line.strip(),
                            'category': 'General',
                            'priority': 'Medium',
                            'preparation_tip': ''
                        })

            return questions[:num_questions]
        except Exception as e:
            logger.error(f"Failed to parse JD questions: {str(e)}")
            return []

    # Resume and Candidate Analysis Methods (stub implementations with Ollama fallback)
    def evaluate_resume_vs_jd(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        """Evaluate resume match against job description"""
        try:
            if not self.is_ollama_available():
                return {"score": 0, "analysis": "Ollama unavailable", "match_analysis": []}

            prompt = f"""Compare this resume against the job description and provide a match score (0-100) with key analysis points.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Provide a JSON response with score and analysis."""

            response = self._call_ollama(self.models['general'], prompt, 1)
            if response:
                return response[0] if isinstance(response, list) else response
            return {"score": 0, "analysis": "Generation failed"}
        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {"score": 0, "analysis": f"Error: {str(e)}"}

    def analyze_technical_skills(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        """Analyze technical skills match"""
        try:
            if not self.is_ollama_available():
                return {"technical_match": 0, "skills_gap": [], "strengths": []}

            prompt = f"""Analyze technical skills match between resume and job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Provide JSON with technical_match score, skills_gap, and strengths."""

            response = self._call_ollama(self.models['technical'], prompt, 1)
            if response:
                return response[0] if isinstance(response, list) else response
            return {"technical_match": 0, "skills_gap": [], "strengths": []}
        except Exception as e:
            logger.error(f"Technical analysis error: {str(e)}")
            return {"technical_match": 0, "skills_gap": [], "strengths": []}

    def deep_candidate_analysis(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        """Perform deep candidate analysis"""
        try:
            if not self.is_ollama_available():
                return {"analysis": "Ollama unavailable", "recommendation": "Unable to analyze"}

            prompt = f"""Perform comprehensive candidate analysis for this JD.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Provide detailed analysis with strengths, weaknesses, and recommendation."""

            response = self._call_ollama(self.models['advanced'], prompt, 1)
            if response:
                return response[0] if isinstance(response, list) else response
            return {"analysis": "Failed", "recommendation": "Unable to analyze"}
        except Exception as e:
            logger.error(f"Deep analysis error: {str(e)}")
            return {"analysis": str(e), "recommendation": "Analysis failed"}

    def generate_detailed_report(self, resume_text: str, jd_text: str, candidate_name: str = "Candidate") -> Dict[str, Any]:
        """Generate detailed evaluation report"""
        try:
            if not self.is_ollama_available():
                return {"report": "Ollama unavailable", "status": "failed"}

            prompt = f"""Generate a professional evaluation report for {candidate_name}.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Format as a professional report with summary, analysis, and recommendation."""

            response = self._call_ollama(self.models['general'], prompt, 1)
            if response:
                return response[0] if isinstance(response, list) else response
            return {"report": "Generation failed", "status": "failed"}
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            return {"report": str(e), "status": "failed"}

    def generate_screening_questions(self, resume_text: str, jd_text: str, num_questions: int = 5) -> List[str]:
        """Generate screening questions based on resume and JD"""
        try:
            if not self.is_ollama_available():
                return []

            prompt = f"""Generate {num_questions} screening interview questions based on this candidate's resume and the job requirements.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Return only the questions, one per line."""

            response = self._call_ollama(self.models['general'], prompt, num_questions)
            if response:
                return [q.get('question', '') for q in response if 'question' in q]
            return []
        except Exception as e:
            logger.error(f"Screening questions error: {str(e)}")
            return []

    def quick_summary(self, text: str) -> str:
        """Generate quick summary of text"""
        try:
            if not self.is_ollama_available():
                return "Ollama unavailable"

            prompt = f"""Provide a brief 2-3 sentence summary of this text:

{text}"""

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.models['general'], "prompt": prompt, "stream": False},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Unable to generate summary')
            return "Summary generation failed"
        except Exception as e:
            logger.error(f"Quick summary error: {str(e)}")
            return f"Error: {str(e)}"

    def generate(self, task: TaskType, prompt: str, system: str = "", model: Optional[str] = None) -> str:
        """Generic generate method for different task types"""
        try:
            if not self.is_ollama_available():
                return "Ollama service unavailable"

            selected_model = model or self.models.get('general', 'mistral')

            full_prompt = f"{system}\n\n{prompt}" if system else prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": selected_model, "prompt": full_prompt, "stream": False},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response generated')
            return f"Model request failed with status {response.status_code}"
        except Exception as e:
            logger.error(f"Generate error for task {task.value}: {str(e)}")
            return f"Generation failed: {str(e)}"




# Export module-level instance for easy access
ollama_service = OllamaService()
