"""
Ollama Question Generation Service
Generates assessment questions dynamically using local LLM models
"""

import os

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

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("ollama_base_url", "https://ollama.skreenit.com")
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

    def generate_voice_test_content(
        self,
        assessment_name: str,
        assessment_desc: str,
        skills: str,
    ) -> Dict[str, Any]:
        """Generate all dynamic content for a voice_test assessment in one call.

        Returns a dict with keys:
          passages  – list of 2 reading passage strings
          sentences – list of 6 repeat-sentence strings
          topics    – list of 4 topic-speaking strings
          questions – list of 3 open-ended QA question strings
        Returns {} on failure so build_sections falls back to hardcoded content.
        """
        cache_key = f"voice_test_{assessment_name}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached voice test content for {assessment_name}")
                return cached_data

        if not self.is_ollama_available():
            return {}

        model = self._resolve_model('general')
        if not model:
            return {}

        prompt = f"""You are designing a spoken English assessment for the following role/context.

Assessment: {assessment_name}
Description: {assessment_desc}
Skills: {skills}

Generate fresh assessment content. Return ONLY valid JSON — no extra text, no markdown, no explanations.

{{
  "passages": [
    "<A professional reading passage of 2-4 sentences directly relevant to {assessment_name}. Use formal English.>",
    "<A second passage on a different angle of the same context, 2-4 sentences.>"
  ],
  "sentences": [
    "<One clear 8-15 word sentence relevant to {assessment_name} for repetition practice.>",
    "<Another sentence, different topic within the same context.>",
    "<Third sentence.>",
    "<Fourth sentence.>",
    "<Fifth sentence.>",
    "<Sixth sentence.>"
  ],
  "topics": [
    "<One speaking topic closely related to {assessment_name} — a phrase, not a question.>",
    "<Second topic.>",
    "<Third topic.>",
    "<Fourth topic.>"
  ],
  "questions": [
    "<Open-ended question answerable in 45-60 seconds, testing {skills}.>",
    "<Second question, different skill area.>",
    "<Third question.>"
  ]
}}"""

        try:
            url = f"{self.base_url}/api/generate"
            response = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.55},
                timeout=180,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start == -1 or end <= start:
                logger.warning("Voice test content: no JSON found in Ollama response")
                return {}
            data = json.loads(raw[start:end])
            # Validate minimum keys
            if not all(k in data for k in ('passages', 'sentences', 'topics', 'questions')):
                logger.warning("Voice test content: missing required keys in Ollama response")
                return {}
            self.cache[cache_key] = (data, datetime.now())
            logger.info(f"Generated voice test content for {assessment_name}")
            return data
        except Exception as e:
            logger.error(f"Voice test content generation failed: {e}")
            return {}

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

    def analyze_assessment_responses(
        self,
        assessment_name: str,
        assessment_key: str,
        responses: List[Dict[str, Any]],
        mcq_score: Optional[int] = None,
        mcq_total: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate submitted assessment responses using Ollama.
        Returns overall score, grade, summary, strengths, improvements, and per-response feedback.
        Falls back to rule-based scoring when Ollama is unavailable.
        """
        from datetime import datetime as _dt
        from utils_others.grading import GradeCalculator

        # Build text for analysis (only scorable responses)
        scorable = []
        voice_count = 0
        for i, r in enumerate(responses):
            rtype = r.get('response_type') or r.get('type', '')
            if rtype == 'mcq':
                correct = r.get('is_correct')
                label = 'Correct' if correct == 1 else ('Incorrect' if correct == 0 else 'Not graded')
                scorable.append({'index': i, 'type': 'mcq', 'label': label, 'text': None})
            elif rtype in ('text', 'text_response', 'code'):
                txt = (r.get('text_response') or r.get('text') or '').strip()
                if txt:
                    scorable.append({'index': i, 'type': rtype, 'label': rtype, 'text': txt[:800]})
            elif rtype in ('voice', 'voice_scenario', 'read_aloud', 'repeat_sentence', 'qa_verbal',
                           'vocabulary', 'topic_speaking'):
                voice_count += 1

        # Attempt Ollama analysis if available and there are text/code responses to score
        text_items = [s for s in scorable if s['type'] not in ('mcq',)]
        ollama_result = None

        if self.is_ollama_available() and (text_items or scorable):
            model = self._resolve_model('general')
            if model:
                try:
                    response_lines = []
                    for s in scorable:
                        if s['type'] == 'mcq':
                            response_lines.append(f"- [MCQ] Result: {s['label']}")
                        else:
                            response_lines.append(f"- [{s['type'].upper()}] Answer: {s['text']}")
                    if voice_count:
                        response_lines.append(f"- [VOICE] {voice_count} voice recording(s) submitted (audio not transcribed)")

                    mcq_line = ''
                    if mcq_total and mcq_total > 0:
                        mcq_line = f"\nMCQ Score: {mcq_score}/{mcq_total} correct."

                    prompt = f"""You are an expert assessment evaluator. Evaluate the following assessment responses.

Assessment: {assessment_name}{mcq_line}

Responses:
{chr(10).join(response_lines)}

Return ONLY valid JSON with this exact structure (no extra text):
{{
  "overall_score": <integer 0-100>,
  "summary": "<2-3 sentence overall evaluation>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "areas_for_improvement": ["<area 1>", "<area 2>"],
  "response_feedback": [
    {{"index": <response index>, "score": <0-100>, "feedback": "<brief feedback>"}}
  ]
}}

Scoring: 90-100=Exceptional, 80-89=Excellent, 70-79=Very Good, 60-69=Good, 50-59=Average, below 50=Needs Improvement."""

                    raw = requests.post(
                        f"{self.base_url}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                        timeout=180,
                    )
                    if raw.status_code == 200:
                        text_out = raw.json().get('response', '')
                        # Extract JSON block
                        start = text_out.find('{')
                        end = text_out.rfind('}') + 1
                        if start != -1 and end > start:
                            ollama_result = json.loads(text_out[start:end])
                except Exception as e:
                    logger.warning(f"Ollama assessment analysis failed: {e}")

        # Build result (Ollama or fallback)
        if ollama_result and isinstance(ollama_result.get('overall_score'), (int, float)):
            overall_score = max(0, min(100, int(ollama_result['overall_score'])))
            summary = ollama_result.get('summary', '')
            strengths = ollama_result.get('strengths', [])
            improvements = ollama_result.get('areas_for_improvement', [])
            response_feedback = ollama_result.get('response_feedback', [])
        else:
            # Rule-based fallback
            scores = []
            if mcq_total and mcq_total > 0:
                scores.append(int((mcq_score or 0) / mcq_total * 100))
            for s in text_items:
                # Baseline: 65 for any submitted text, scaled by length
                length_bonus = min(20, len(s.get('text') or '') // 30)
                scores.append(65 + length_bonus)
            if voice_count:
                scores.extend([65] * voice_count)
            overall_score = int(sum(scores) / len(scores)) if scores else 60
            summary = (
                f"Your assessment for '{assessment_name}' has been submitted and saved. "
                f"You completed {len(responses)} exercise(s). "
                "Detailed AI feedback will be available once analysis is complete."
            )
            strengths = ["Assessment completed successfully", "All exercises attempted"]
            improvements = ["Review your responses to identify areas for growth"]
            response_feedback = []

        grade_info = GradeCalculator.score_to_grade(overall_score)

        return {
            "overall_score": overall_score,
            "overall_grade": grade_info["grade"],
            "grade_label": grade_info["label"],
            "grade_color": grade_info["color"],
            "summary": summary,
            "strengths": strengths[:4],
            "areas_for_improvement": improvements[:4],
            "response_feedback": response_feedback,
            "analyzed_at": _dt.utcnow().isoformat(),
            "analyzer": "ollama" if ollama_result else "fallback",
        }

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

        # Generic pads used when Ollama returns fewer questions than requested
        _pads = [
            "Can you walk us through a challenging project from your experience and how you handled it?",
            "What are the key skills from your background that you would bring to this role?",
            "Describe a situation where you had to learn something new quickly. How did you approach it?",
        ]

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
                # Strip leading numbering like "1." "2)" "3 "
                if line[0].isdigit():
                    line = line.lstrip("0123456789.) ").strip()
                if line and len(line) > 10:
                    questions.append(line)
                if len(questions) >= num_questions:
                    break

            # Pad to exactly num_questions so the interview always has intro + num_questions = 4 total
            pad_idx = 0
            while len(questions) < num_questions:
                questions.append(_pads[pad_idx % len(_pads)])
                pad_idx += 1

            logger.info(f"Generated {len(questions)} resume-based interview questions")
            return questions
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
