"""
Indian Language Support Service
Handles speech-to-text, translation, and analysis for Indian vernacular languages.
Supports all 22 scheduled Indian languages.
"""

import whisper
import os
import json
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from utils_others.logger import logger

# Language detection
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0  # For consistent results
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available. Language detection will use fallback.")

# Indian NLP
try:
    from indicnlp.tokenize import indic_tokenize
    from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
    INDIC_NLP_AVAILABLE = True
except ImportError:
    INDIC_NLP_AVAILABLE = False
    logger.warning("indic-nlp-library not available. Indian NLP features disabled.")

# Translation
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    logger.warning("deep-translator not available. Translation will use fallback.")

# Bhashini API for Indian languages (via HTTP requests)
BHASHINI_AVAILABLE = False  # Requires API key setup

# Supported Indian Languages (22 scheduled languages)
INDIAN_LANGUAGES = {
    'hi': {'name': 'Hindi', 'script': 'Devanagari'},
    'bn': {'name': 'Bengali', 'script': 'Bengali'},
    'te': {'name': 'Telugu', 'script': 'Telugu'},
    'mr': {'name': 'Marathi', 'script': 'Devanagari'},
    'ta': {'name': 'Tamil', 'script': 'Tamil'},
    'ur': {'name': 'Urdu', 'script': 'Perso-Arabic'},
    'gu': {'name': 'Gujarati', 'script': 'Gujarati'},
    'kn': {'name': 'Kannada', 'script': 'Kannada'},
    'ml': {'name': 'Malayalam', 'script': 'Malayalam'},
    'or': {'name': 'Odia', 'script': 'Odia'},
    'pa': {'name': 'Punjabi', 'script': 'Gurmukhi'},
    'as': {'name': 'Assamese', 'script': 'Bengali'},
    'ne': {'name': 'Nepali', 'script': 'Devanagari'},
    'si': {'name': 'Sinhala', 'script': 'Sinhala'},
    'sd': {'name': 'Sindhi', 'script': 'Perso-Arabic'},
    'sa': {'name': 'Sanskrit', 'script': 'Devanagari'},
    'kok': {'name': 'Konkani', 'script': 'Devanagari'},
    'mni': {'name': 'Manipuri', 'script': 'Bengali/Meetei'},
    'brx': {'name': 'Bodo', 'script': 'Devanagari'},
    'doi': {'name': 'Dogri', 'script': 'Devanagari'},
    'sat': {'name': 'Santali', 'script': 'Ol Chiki'},
    'ks': {'name': 'Kashmiri', 'script': 'Perso-Arabic/Devanagari'},
    'en': {'name': 'English', 'script': 'Latin'}  # Including English as reference
}

# Whisper language codes mapping
WHISPER_LANGUAGE_CODES = {
    'hi': 'hi',  # Hindi
    'bn': 'bn',  # Bengali
    'te': 'te',  # Telugu
    'mr': 'mr',  # Marathi
    'ta': 'ta',  # Tamil
    'ur': 'ur',  # Urdu
    'gu': 'gu',  # Gujarati
    'kn': 'kn',  # Kannada
    'ml': 'ml',  # Malayalam
    'or': 'or',  # Odia
    'pa': 'pa',  # Punjabi
    'as': 'as',  # Assamese
    'ne': 'ne',  # Nepali
    'en': 'en',  # English
}

class IndianLanguageService:
    """Service for processing Indian vernacular languages in video responses."""
    
    def __init__(self):
        self.whisper_model = None
        self.bhashini_available = BHASHINI_AVAILABLE
        self.INDIAN_LANGUAGES = INDIAN_LANGUAGES
        self._load_whisper_model()
        
    def _load_whisper_model(self):
        """Load Whisper model for multilingual speech recognition."""
        try:
            # Use base model for efficiency, can upgrade to 'small' or 'medium' with 64GB RAM
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully for multilingual STT")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            self.whisper_model = None
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of given text.
        Returns: (language_code, confidence)
        """
        if not text or len(text.strip()) < 10:
            return 'en', 0.0
        
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                # Check if detected language is in our Indian languages
                if detected in INDIAN_LANGUAGES:
                    return detected, 0.9
                return detected, 0.7
            except Exception as e:
                logger.warning(f"Language detection failed: {str(e)}")
        
        # Fallback: Assume English
        return 'en', 0.5
    
    def transcribe_audio(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict:
        """
        Transcribe audio/video file using Whisper.
        Supports all Indian languages that Whisper supports.
        
        Args:
            audio_path: Path to audio/video file
            language: Language code (optional, auto-detect if None)
            task: 'transcribe' or 'translate' (to English)
        
        Returns:
            Dict with transcription, detected language, confidence
        """
        if not self.whisper_model:
            logger.error("Whisper model not available")
            return {
                'text': '',
                'language': 'unknown',
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
        
        try:
            # Prepare options
            options = {'task': task}
            
            # If language specified, use it; otherwise Whisper will auto-detect
            if language and language in WHISPER_LANGUAGE_CODES:
                options['language'] = WHISPER_LANGUAGE_CODES[language]
            
            # Transcribe
            result = self.whisper_model.transcribe(audio_path, **options)
            
            detected_lang = result.get('language', 'unknown')
            
            return {
                'text': result.get('text', ''),
                'language': detected_lang,
                'confidence': result.get('confidence', 0.8),
                'segments': result.get('segments', []),
                'duration': result.get('duration', 0)
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                'text': '',
                'language': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translate text from Indian language to English.
        Uses Bhashini if available, otherwise googletrans.
        """
        if not text or source_lang == 'en':
            return text
        
        # Try Bhashini first (better for Indian languages)
        if BHASHINI_AVAILABLE:
            try:
                bhashini = Bhashini()
                result = bhashini.translate(text, source_lang, 'en')
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Bhashini translation failed: {str(e)}")
        
        # Fallback to Google Translate (deep_translator)
        if TRANSLATOR_AVAILABLE:
            try:
                translator = GoogleTranslator(source=source_lang, target='en')
                result = translator.translate(text)
                return result if result else text
            except Exception as e:
                logger.warning(f"Google translation failed: {str(e)}")
        
        return text  # Return original if all fails
    
    def analyze_communication(
        self, 
        transcription: str,
        language: str,
        is_fresher: bool = False
    ) -> Dict:
        """
        Analyze communication skills in native language.
        For freshers, focuses on clarity, confidence, and language proficiency.
        """
        analysis = {
            'language': language,
            'language_name': INDIAN_LANGUAGES.get(language, {}).get('name', 'Unknown'),
            'is_native_language': language in INDIAN_LANGUAGES,
            'transcription': transcription,
            'translated_to_english': '',
            'metrics': {}
        }
        
        # Translate to English for analysis
        if language != 'en':
            analysis['translated_to_english'] = self.translate_to_english(
                transcription, language
            )
        
        # Basic metrics
        word_count = len(transcription.split())
        char_count = len(transcription)
        
        analysis['metrics'] = {
            'word_count': word_count,
            'character_count': char_count,
            'avg_word_length': char_count / word_count if word_count > 0 else 0,
        }
        
        # Fresher-specific analysis
        if is_fresher:
            analysis['fresher_assessment'] = {
                'communication_level': self._assess_communication_level(word_count, language),
                'confidence_indicator': 'adequate' if word_count > 20 else 'needs_improvement',
                'language_proficiency': 'native' if language in INDIAN_LANGUAGES else 'other',
                'recommendation': self._get_fresher_recommendation(word_count, language)
            }
        
        return analysis
    
    def _assess_communication_level(self, word_count: int, language: str) -> str:
        """Assess communication level based on response length."""
        if word_count < 10:
            return 'brief'
        elif word_count < 30:
            return 'adequate'
        elif word_count < 60:
            return 'good'
        else:
            return 'excellent'
    
    def _get_fresher_recommendation(self, word_count: int, language: str) -> str:
        """Get recommendation for fresher candidates."""
        if word_count < 15:
            return 'Candidate should work on providing more detailed responses'
        elif language in INDIAN_LANGUAGES:
            return 'Good communication in native language. English proficiency to be verified.'
        else:
            return 'Good communication skills observed'
    
    def get_supported_languages(self) -> List[Dict]:
        """Get list of supported languages with metadata."""
        languages = []
        for code, info in self.INDIAN_LANGUAGES.items():
            languages.append({
                'code': code,
                'name': info['name'],
                'script': info.get('script', 'Latin'),
                'native_name': info.get('native_name', info['name'])
            })
        return languages

    def translate_question(self, question: str, target_lang: str) -> Dict[str, str]:
        """
        Translate a question from English to target language.
        Returns both English and translated versions.
        """
        if target_lang == 'en' or not question:
            return {'english': question, 'translated': question, 'language': 'en'}
        
        translated = question
        translation_method = 'fallback'
        
        # Try Bhashini first
        if self.bhashini_available:
            try:
                result = self.bhashini.translate(
                    text=question,
                    source_language='en',
                    target_language=target_lang
                )
                if result and 'translated_text' in result:
                    translated = result['translated_text']
                    translation_method = 'bhashini'
                    logger.info(f"Translated question via Bhashini: {target_lang}")
                    return {'english': question, 'translated': translated, 'language': target_lang, 'method': translation_method}
            except Exception as e:
                logger.warning(f"Bhashini translation failed: {e}")
        
        # Fallback to Google Translate (deep_translator)
        if TRANSLATOR_AVAILABLE:
            try:
                translator = GoogleTranslator(source='en', target=target_lang)
                translated = translator.translate(question)
                translation_method = 'google'
                logger.info(f"Translated question via Google: {target_lang} - '{question}' -> '{translated}'")
            except Exception as e:
                logger.warning(f"Translation failed for {target_lang}: {e}")
                translated = question  # Fallback to English
                translation_method = 'failed'
        else:
            logger.warning("Google Translator not available, using English fallback")
            translated = question
            translation_method = 'not_available'
        
        logger.info(f"Translation result for {target_lang}: method={translation_method}, translated={translated}")
        return {'english': question, 'translated': translated, 'language': target_lang, 'method': translation_method}

    def translate_questions_batch(self, questions: List[str], target_lang: str) -> List[Dict[str, str]]:
        """
        Translate multiple questions to target language.
        Returns list of dicts with english and translated versions.
        """
        translated_questions = []
        for q in questions:
            translated_questions.append(self.translate_question(q, target_lang))
        return translated_questions

    def generate_english_report(self, analysis: Dict, detected_lang: str) -> Dict:
        """
        Generate analysis report in English regardless of spoken language.
        Takes analysis in native language and produces English report.
        """
        report = {
            'language_detected': detected_lang,
            'language_name': self.INDIAN_LANGUAGES.get(detected_lang, {}).get('name', 'Unknown'),
            'metrics': analysis.get('metrics', {}),
            'proficiency_level': analysis.get('proficiency_level', 'Unknown'),
            'recommendations': [],
            'strengths': [],
            'areas_for_improvement': [],
            'overall_assessment': ''
        }
        
        # Translate recommendations to English if needed
        recommendations = analysis.get('recommendations', [])
        for rec in recommendations:
            if detected_lang != 'en' and TRANSLATOR_AVAILABLE:
                try:
                    translator = GoogleTranslator(source=detected_lang, target='en')
                    translated_rec = translator.translate(rec)
                    report['recommendations'].append(translated_rec)
                except:
                    report['recommendations'].append(rec)
            else:
                report['recommendations'].append(rec)
        
        
        # Generate English assessment based on metrics
        metrics = analysis.get('metrics', {})
        word_count = metrics.get('word_count', 0)
        sentence_count = metrics.get('sentence_count', 0)
        avg_sentence_length = metrics.get('avg_sentence_length', 0)
        
        # Overall assessment in English
        if word_count < 20:
            report['overall_assessment'] = 'Candidate provided a very brief response. May need encouragement to elaborate.'
            report['proficiency_level'] = 'Basic'
        elif word_count < 50:
            report['overall_assessment'] = 'Candidate provided a moderate response with basic communication skills.'
            report['proficiency_level'] = 'Intermediate'
        elif word_count < 100:
            report['overall_assessment'] = 'Candidate demonstrated good communication skills with adequate elaboration.'
            report['proficiency_level'] = 'Proficient'
        else:
            report['overall_assessment'] = 'Candidate demonstrated strong communication skills with detailed and articulate responses.'
            report['proficiency_level'] = 'Advanced'
        
        
        # Add strengths and areas for improvement in English
        if avg_sentence_length > 15:
            report['strengths'].append('Uses complex sentence structures effectively')
        else:
            report['areas_for_improvement'].append('Could use more varied sentence structures')
        
        if word_count > 50:
            report['strengths'].append('Provides detailed and comprehensive responses')
        
        if metrics.get('has_fillers', False):
            report['areas_for_improvement'].append('Reduce use of filler words for more professional delivery')
        
        
        return report
    
    def normalize_indic_text(self, text: str, language: str) -> str:
        """Normalize Indian language text using Indic NLP."""
        if not INDIC_NLP_AVAILABLE or language not in INDIAN_LANGUAGES:
            return text
        
        try:
            # Normalize the text
            factory = IndicNormalizerFactory()
            normalizer = factory.get_normalizer(language)
            normalized = normalizer.normalize(text)
            return normalized
        except Exception as e:
            logger.warning(f"Text normalization failed: {str(e)}")
            return text

# Singleton instance
indian_language_service = IndianLanguageService()
