import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils_others.grading import GradeCalculator

logger = logging.getLogger(__name__)


class GradingSystem:
    """
    Thin wrapper around shared GradeCalculator to keep grading consistent.
    """

    @classmethod
    def score_to_grade(cls, score: int) -> Dict[str, Any]:
        """Convert numerical score to grade info using shared calculator."""
        return GradeCalculator.score_to_grade(score)

    @classmethod
    def get_grade_index(cls) -> List[Dict[str, Any]]:
        """Expose the full grade index for UI/reference."""
        return GradeCalculator.get_grade_index()


# ---------------------------------------------------------------------------
# Core parameter definitions (11 parameters, flat but ready for grouping)
# ---------------------------------------------------------------------------

PARAMETERS = [
    "speaking_pace",
    "confidence",
    "face_visibility",
    "filler_words",
    "pronunciation",
    "voice_modulation",
    "communication",
    "grammar",
    "vocabulary",
    "sentences",
    "dominant_emotion",
]

PARAMETER_LABELS = {
    "speaking_pace": "Speaking Pace",
    "confidence": "Confidence",
    "face_visibility": "Face Visibility",
    "filler_words": "Filler Words",
    "pronunciation": "Pronunciation",
    "voice_modulation": "Voice Modulation",
    "communication": "Communication",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "sentences": "Sentence Formation",
    "dominant_emotion": "Dominant Emotion",
}

# Importance weights for overall grade (can be tuned later)
PARAMETER_WEIGHTS = {
    "speaking_pace": 0.10,
    "confidence": 0.15,
    "face_visibility": 0.05,
    "filler_words": 0.05,
    "pronunciation": 0.10,
    "voice_modulation": 0.10,
    "communication": 0.15,
    "grammar": 0.10,
    "vocabulary": 0.10,
    "sentences": 0.08,
    "dominant_emotion": 0.02,
}


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0

class AssessmentReportService:
    """
    New assessment engine built around 11 explicit parameters.

    Inputs:
      - transcription: Whisper stats (wpm, filler_words, word_count, transcript, etc.)
      - visual_analysis: FER/OpenCV stats (dominant_emotion, face_presence_rate, avg_confidence, etc.)
      - nlp_analysis: NLPAnalysisService output (grammar, vocabulary, sentences, communication_skills)
      - audio_analysis: AudioAnalysisService output (pronunciation, voice_modulation, speech_patterns)
      - visual_behavior: VisualBehaviorService output (eye_contact, motion, posture, confidence_visual)
    """

    def __init__(self):
        self.grading = GradingSystem()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate_report(
        self,
        transcription: Dict[str, Any],
        visual_analysis: Dict[str, Any],
        nlp_analysis: Dict[str, Any],
        audio_analysis: Dict[str, Any] = None,
        visual_behavior: Dict[str, Any] = None,
        candidate_info: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate a full 11‑parameter report with:
        - Per‑parameter grade + explanation
        - Overall grade + recommendation
        - Strengths + improvement areas
        """
        candidate_info = candidate_info or {}

        # 1) Compute per‑parameter scores + grades
        parameter_assessments = self._build_parameter_assessments(
            transcription, visual_analysis, nlp_analysis, audio_analysis, visual_behavior
        )

        # 2) Compute overall grade + recommendation
        executive_summary = self._build_executive_summary(parameter_assessments)

        # 3) Extract strengths + improvement areas
        strengths = self._identify_strengths(parameter_assessments)
        improvement_areas = self._identify_improvement_areas(parameter_assessments)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "candidate_info": candidate_info,
            "grade_index": self.grading.get_grade_index(),
            "parameters": parameter_assessments,   # flat 11 parameters
            "executive_summary": executive_summary,
            "strengths": strengths,
            "areas_for_improvement": improvement_areas,
        }

    # ------------------------------------------------------------------ #
    # Parameter assessment builder
    # ------------------------------------------------------------------ #

    def _build_parameter_assessments(
        self,
        transcription: Dict[str, Any],
        visual: Dict[str, Any],
        nlp: Dict[str, Any],
        audio: Dict[str, Any],
        visual_behavior: Dict[str, Any],
    ) -> Dict[str, Any]:
        assessments: Dict[str, Any] = {}

        # Speaking Pace
        assessments["speaking_pace"] = self._assess_speaking_pace(transcription)

        # Confidence (visual + behavior + voice)
        assessments["confidence"] = self._assess_confidence(visual, visual_behavior, audio)

        # Face Visibility (face presence + eye contact)
        assessments["face_visibility"] = self._assess_face_visibility(visual, visual_behavior)

        # Filler Words (ratio)
        assessments["filler_words"] = self._assess_filler_words(transcription)

        # Pronunciation (audio)
        assessments["pronunciation"] = self._assess_pronunciation(audio)

        # Voice Modulation (audio)
        assessments["voice_modulation"] = self._assess_voice_modulation(audio)

        # Communication (overall NLP communication score)
        assessments["communication"] = self._assess_communication(nlp)

        # Grammar
        assessments["grammar"] = self._assess_grammar(nlp)

        # Vocabulary
        assessments["vocabulary"] = self._assess_vocabulary(nlp)

        # Sentences (sentence formation)
        assessments["sentences"] = self._assess_sentences(nlp)

        # Dominant Emotion
        assessments["dominant_emotion"] = self._assess_dominant_emotion(visual)

        return assessments

    # ------------------------------------------------------------------ #
    # Individual parameter assessors
    # ------------------------------------------------------------------ #

    def _assess_speaking_pace(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        wpm = transcription.get("wpm", 0)
        score = 70  # base

        if 120 <= wpm <= 150:
            score += 20
            pace_label = "Ideal professional pace"
        elif 100 <= wpm <= 170:
            score += 10
            pace_label = "Generally good pace"
        elif wpm < 80:
            score -= 10
            pace_label = "Too slow, may feel dragged"
        else:
            score -= 5
            pace_label = "Too fast, may be hard to follow"

        grade_info = self.grading.score_to_grade(int(score))

        why = f"Speaking pace was approximately {wpm} words per minute. {pace_label}."
        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Aim for 120–150 words per minute by practicing timed responses and recording yourself."
            )

        return {
            "parameter": "speaking_pace",
            "label": PARAMETER_LABELS["speaking_pace"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {"wpm": wpm},
        }

    def _assess_confidence(
        self,
        visual: Dict[str, Any],
        visual_behavior: Dict[str, Any],
        audio: Dict[str, Any],
    ) -> Dict[str, Any]:
        vb_conf = (visual_behavior or {}).get("confidence_visual", {}).get("score", 0)
        face_presence = visual.get("face_presence_rate", 0) if visual else 0
        emotion_conf = visual.get("avg_confidence", 0) if visual else 0
        expressiveness = (audio or {}).get("voice_modulation", {}).get("expressiveness", 50)

        # Blend multiple cues
        factors = [
            vb_conf or 50,
            face_presence * 0.8,
            emotion_conf,
            expressiveness,
        ]
        score = sum(factors) / len(factors) if factors else 50
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Confidence is inferred from visual presence, eye contact, emotional stability, "
            f"and vocal expressiveness. Visual confidence score was ~{vb_conf}, "
            f"face presence around {face_presence}%, and voice expressiveness around {int(expressiveness)}."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Maintain steady eye contact with the camera and keep posture open to project stronger confidence."
            )
            improvement.append(
                "Practice delivering answers with clear emphasis and fewer hesitations to sound more assured."
            )

        return {
            "parameter": "confidence",
            "label": PARAMETER_LABELS["confidence"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "visual_confidence": vb_conf,
                "face_presence_rate": face_presence,
                "emotion_confidence": emotion_conf,
                "voice_expressiveness": expressiveness,
            },
        }

    def _assess_face_visibility(self, visual: Dict[str, Any], visual_behavior: Dict[str, Any]) -> Dict[str, Any]:
        face_presence = visual.get("face_presence_rate", 0) if visual else 0
        eye_contact_rate = (visual_behavior or {}).get("eye_contact", {}).get("eye_contact_rate", 0)

        score = 60
        if face_presence >= 90:
            score += 20
        elif face_presence >= 70:
            score += 10
        else:
            score -= 5

        if eye_contact_rate >= 75:
            score += 10
        elif eye_contact_rate < 50:
            score -= 5

        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Face was visible in approximately {face_presence}% of sampled frames, "
            f"with eye contact around {eye_contact_rate}%. "
            "Higher visibility and consistent eye contact improve perceived engagement."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Position the camera at eye level with good lighting so your face stays clearly visible."
            )
            improvement.append(
                "Avoid leaning too far away or out of frame during responses."
            )

        return {
            "parameter": "face_visibility",
            "label": PARAMETER_LABELS["face_visibility"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "face_presence_rate": face_presence,
                "eye_contact_rate": eye_contact_rate,
            },
        }

    def _assess_filler_words(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        filler_count = transcription.get("filler_words", 0)
        word_count = transcription.get("word_count", 0)
        ratio = _safe_div(filler_count, word_count)

        score = 80
        if ratio < 0.02:
            score += 15
            label = "Very low filler usage"
        elif ratio < 0.05:
            score += 5
            label = "Acceptable filler usage"
        elif ratio < 0.10:
            score -= 10
            label = "Noticeable fillers"
        else:
            score -= 20
            label = "High filler usage"

        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Detected {filler_count} filler words out of {word_count} total words "
            f"(~{round(ratio * 100, 1)}%). {label}."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Replace fillers (like 'um', 'uh', 'like') with short pauses to sound more confident and deliberate."
            )

        return {
            "parameter": "filler_words",
            "label": PARAMETER_LABELS["filler_words"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "filler_count": filler_count,
                "word_count": word_count,
                "filler_ratio": round(ratio, 3),
            },
        }

    def _assess_pronunciation(self, audio: Dict[str, Any]) -> Dict[str, Any]:
        pron = (audio or {}).get("pronunciation", {}) or {}
        score = pron.get("score", 0)
        grade_info = self.grading.score_to_grade(int(score))

        clarity = pron.get("clarity_score", 0)
        articulation = pron.get("articulation_score", 0)
        phoneme_acc = pron.get("phoneme_accuracy", 0)
        notes = pron.get("notes", [])

        why = (
            f"Pronunciation score reflects clarity ({int(clarity)}), articulation ({int(articulation)}), "
            f"and phoneme accuracy ({int(phoneme_acc)}). "
        )
        if notes:
            why += "Key observations: " + "; ".join(notes[:2])

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Practice reading aloud slowly and clearly, focusing on ending sounds and difficult words."
            )

        return {
            "parameter": "pronunciation",
            "label": PARAMETER_LABELS["pronunciation"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "clarity_score": clarity,
                "articulation_score": articulation,
                "phoneme_accuracy": phoneme_acc,
            },
        }

    def _assess_voice_modulation(self, audio: Dict[str, Any]) -> Dict[str, Any]:
        vm = (audio or {}).get("voice_modulation", {}) or {}
        score = vm.get("score", 0)
        grade_info = self.grading.score_to_grade(int(score))

        pitch_var = vm.get("pitch", {}).get("variation_score", 0)
        energy_var = vm.get("energy", {}).get("variation_score", 0)
        tone_score = vm.get("tone_quality", {}).get("score", 0)
        expressiveness = vm.get("expressiveness", 0)

        why = (
            f"Voice modulation score combines pitch variation ({int(pitch_var)}), "
            f"energy dynamics ({int(energy_var)}), tone quality ({int(tone_score)}), "
            f"and overall expressiveness ({int(expressiveness)})."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Avoid a flat tone by intentionally varying pitch and volume on key points."
            )
            improvement.append(
                "Record yourself and listen for sections that sound monotone, then exaggerate variation slightly."
            )

        return {
            "parameter": "voice_modulation",
            "label": PARAMETER_LABELS["voice_modulation"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "pitch_variation_score": pitch_var,
                "energy_variation_score": energy_var,
                "tone_quality_score": tone_score,
                "expressiveness": expressiveness,
            },
        }

    def _assess_communication(self, nlp: Dict[str, Any]) -> Dict[str, Any]:
        comm = (nlp or {}).get("communication_skills", {}) or {}
        score = comm.get("score", 0)
        level = comm.get("level", "unknown")
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Overall communication score reflects how clearly ideas are structured and conveyed. "
            f"Detected communication level: {level}."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Structure answers using a simple pattern (context → action → result) to make points clearer."
            )

        return {
            "parameter": "communication",
            "label": PARAMETER_LABELS["communication"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {"level": level},
        }

    def _assess_grammar(self, nlp: Dict[str, Any]) -> Dict[str, Any]:
        gram = (nlp or {}).get("grammar", {}) or {}
        score = gram.get("score", 0)
        errors = gram.get("error_count", 0)
        errors_per_100 = gram.get("errors_per_100_words", 0.0)
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Grammar score is based on approximately {errors_per_100} errors per 100 words "
            f"({errors} total issues detected)."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Review common grammar patterns (subject–verb agreement, tense consistency) and re-read answers before recording."
            )

        return {
            "parameter": "grammar",
            "label": PARAMETER_LABELS["grammar"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "error_count": errors,
                "errors_per_100_words": errors_per_100,
            },
        }

    def _assess_vocabulary(self, nlp: Dict[str, Any]) -> Dict[str, Any]:
        vocab = (nlp or {}).get("vocabulary", {}) or {}
        score = vocab.get("score", 0)
        ttr = vocab.get("type_token_ratio", 0.0)
        tier = vocab.get("word_frequency_tier", "unknown")
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Vocabulary score reflects diversity (type-token ratio ~{round(ttr, 3)}) "
            f"and sophistication level classified as '{tier}'."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Introduce a few role-specific or technical terms to show familiarity with the domain."
            )

        return {
            "parameter": "vocabulary",
            "label": PARAMETER_LABELS["vocabulary"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "type_token_ratio": ttr,
                "word_frequency_tier": tier,
            },
        }

    def _assess_sentences(self, nlp: Dict[str, Any]) -> Dict[str, Any]:
        sent = (nlp or {}).get("sentence_formation", {}) or {}
        score = sent.get("score", 0)
        avg_len = sent.get("avg_sentence_length", 0.0)
        complexity = sent.get("complexity", "unknown")
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Sentence formation score reflects average sentence length (~{avg_len} words) "
            f"and overall complexity classified as '{complexity}'."
        )

        improvement = []
        if grade_info["grade"] not in ["A+", "A"]:
            improvement.append(
                "Mix short, direct sentences with a few well-structured complex sentences to keep answers engaging."
            )

        return {
            "parameter": "sentences",
            "label": PARAMETER_LABELS["sentences"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "avg_sentence_length": avg_len,
                "complexity": complexity,
            },
        }

    def _assess_dominant_emotion(self, visual: Dict[str, Any]) -> Dict[str, Any]:
        dominant = (visual or {}).get("dominant_emotion", "unknown")
        emotion_dist = (visual or {}).get("emotion_distribution", {}) or {}
        avg_conf = (visual or {}).get("avg_confidence", 0)

        # Map emotion to a soft score (we don't want this to dominate)
        base = 70
        if dominant in ["happy", "neutral"]:
            base += 15
        elif dominant in ["sad", "fear", "angry"]:
            base -= 10

        score = base
        grade_info = self.grading.score_to_grade(int(score))

        why = (
            f"Dominant emotion detected was '{dominant}' with average confidence {avg_conf}. "
            "Positive or neutral expressions generally support a professional impression."
        )

        improvement = []
        if dominant in ["sad", "fear", "angry"]:
            improvement.append(
                "Aim for a neutral or slight smile to appear more approachable and confident on camera."
            )

        return {
            "parameter": "dominant_emotion",
            "label": PARAMETER_LABELS["dominant_emotion"],
            "score": int(score),
            "grade": grade_info["grade"],
            "color": grade_info["color"],
            "description": grade_info["description"],
            "why_this_grade": why,
            "improvement_areas": improvement,
            "metrics": {
                "dominant_emotion": dominant,
                "emotion_distribution": emotion_dist,
                "avg_confidence": avg_conf,
            },
        }

    # ------------------------------------------------------------------ #
    # Overall summary, strengths, and improvement areas
    # ------------------------------------------------------------------ #

    def _build_executive_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Weighted numeric score from parameter grades
        total_weight = sum(PARAMETER_WEIGHTS.values())
        weighted_score = 0.0

        for key, data in params.items():
            score = data.get("score", 50)
            weight = PARAMETER_WEIGHTS.get(key, 0.0)
            weighted_score += score * weight

        overall_score = int(weighted_score / total_weight) if total_weight else 0
        grade_info = self.grading.score_to_grade(overall_score)

        # Recommendation
        grade = grade_info["grade"]
        if grade in ["A+", "A"]:
            recommendation = "Highly Recommended"
        elif grade in ["B+", "B"]:
            recommendation = "Recommended"
        elif grade in ["C+", "C"]:
            recommendation = "Consider with Reservations"
        else:
            recommendation = "Not Recommended"

        summary_text = self._build_summary_text(params, grade)

        return {
            "overall_score": overall_score,
            "overall_grade": grade_info["grade"],
            "overall_label": grade_info["label"],
            "color": grade_info["color"],
            "recommendation": recommendation,
            "summary_text": summary_text,
        }

    def _build_summary_text(self, params: Dict[str, Any], overall_grade: str) -> str:
        strong = [
            p["label"]
            for p in params.values()
            if p.get("grade") in ["A+", "A", "B+"]
        ]
        weak = [
            p["label"]
            for p in params.values()
            if p.get("grade") in ["C", "D", "F"]
        ]

        summary = f"Overall performance is graded {overall_grade}. "
        if strong:
            summary += "Key strengths include " + ", ".join(strong[:3]) + ". "
        if weak:
            summary += "Areas that need attention include " + ", ".join(weak[:3]) + "."

        return summary

    def _identify_strengths(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        strengths = []
        for key, data in params.items():
            grade = data.get("grade", "F")
            if grade in ["A+", "A", "B+"]:
                strengths.append(
                    {
                        "parameter": key,
                        "label": data.get("label", key),
                        "grade": grade,
                        "highlight": data.get("why_this_grade", ""),
                    }
                )
        return strengths

    def _identify_improvement_areas(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        areas = []
        for key, data in params.items():
            grade = data.get("grade", "A")
            if grade in ["C", "D", "F"]:
                areas.append(
                    {
                        "parameter": key,
                        "label": data.get("label", key),
                        "grade": grade,
                        "suggestion": data.get("why_this_grade", ""),
                        "action_items": data.get("improvement_areas", []),
                    }
                )
        return areas
