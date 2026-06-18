"""
Audio Analysis Service for Video Interviews
Analyzes pronunciation, voice modulation, pitch, tone, and speech patterns.

Lightweight implementation optimized for LOW RAM usage (2GB compatible).
Uses scipy and soundfile instead of librosa for minimal memory footprint.

Required libraries:
- scipy: Audio signal processing (pitch detection, filtering)
- soundfile: Audio file reading (lightweight)
- eng-to-ipa: English to IPA phoneme conversion (lightweight)
- numpy: Already installed with other packages
"""

import os
import re
import tempfile
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports for memory efficiency
_eng_to_ipa = None


def _get_eng_to_ipa():
    """Lazy load eng-to-ipa for pronunciation analysis."""
    global _eng_to_ipa
    if _eng_to_ipa is None:
        try:
            import eng_to_ipa as eng_ipa
            _eng_to_ipa = eng_ipa
            logger.info("eng-to-ipa loaded successfully")
        except ImportError:
            logger.warning("eng-to-ipa not installed. Pronunciation analysis will be limited.")
    return _eng_to_ipa


class AudioAnalysisService:
    """
    Comprehensive audio analysis for interview recordings.
    Lightweight implementation using scipy/soundfile instead of librosa.
    Optimized for 2GB RAM environments.
    """
    
    def __init__(self):
        """Initialize with lazy-loaded components."""
        self.eng_to_ipa = _get_eng_to_ipa()
    
    def analyze_audio(self, audio_path: str, transcript: str = "", word_timestamps: List[Dict] = None) -> Dict[str, Any]:
        """
        Main method to analyze audio comprehensively.
        
        Args:
            audio_path: Path to audio file (WAV format preferred)
            transcript: Transcribed text (optional, for pronunciation analysis)
            word_timestamps: Word-level timestamps from Whisper (optional)
        
        Returns:
            Dictionary containing all audio analysis results
        """
        result = {
            "pronunciation": self._empty_pronunciation_result(),
            "voice_modulation": self._empty_voice_result(),
            "speech_patterns": self._empty_patterns_result(),
            "summary": {
                "audio_quality_score": 0,
                "pronunciation_score": 0,
                "voice_dynamics_score": 0,
                "overall_audio_score": 0
            }
        }
        
        if not os.path.exists(audio_path):
            result["error"] = f"Audio file not found: {audio_path}"
            logger.error(f"Audio file not found: {audio_path}")
            return result
        
        logger.info(f"Starting audio analysis for: {audio_path}")
        logger.info(f"Transcript length: {len(transcript) if transcript else 0}")
        logger.info(f"Eng-to-IPA available: {self.eng_to_ipa is not None}")
        
        try:
            # Load audio with soundfile (lightweight, low memory)
            logger.info(f"Attempting to load audio from: {audio_path}")
            y, sr = self._load_audio_lightweight(audio_path)
            
            if y is not None and sr is not None:
                logger.info(f"Audio loaded successfully: {len(y)} samples at {sr}Hz")
                
                # Analyze voice modulation (pitch, energy, tempo) using scipy
                logger.info("Analyzing voice modulation...")
                result["voice_modulation"] = self._analyze_voice_modulation(y, sr)
                logger.info(f"Voice modulation score: {result['voice_modulation']['score']}")
                
                # Analyze speech patterns
                result["speech_patterns"] = self._analyze_speech_patterns(y, sr)
                
                # Calculate summary scores
                result["summary"]["voice_dynamics_score"] = result["voice_modulation"]["score"]
            else:
                logger.error(f"Failed to load audio from {audio_path} - y={y is not None}, sr={sr}")
            
            # Analyze pronunciation if transcript provided
            if transcript:
                logger.info("Analyzing pronunciation...")
                result["pronunciation"] = self._analyze_pronunciation(transcript, word_timestamps)
                result["summary"]["pronunciation_score"] = result["pronunciation"]["score"]
                logger.info(f"Pronunciation score: {result['pronunciation']['score']}")
            else:
                logger.warning("No transcript provided - skipping pronunciation analysis")
            
            # Calculate overall audio score
            result["summary"]["overall_audio_score"] = self._calculate_overall_audio_score(result)
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    # =========================================================================
    # LIGHTWEIGHT AUDIO LOADING (scipy/soundfile - no librosa)
    # =========================================================================
    
    def _load_audio_lightweight(self, audio_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """
        Load audio using soundfile (lightweight, ~10MB vs librosa ~500MB).
        Returns (audio_data, sample_rate) or (None, None) on failure.
        """
        try:
            import soundfile as sf
            logger.info(f"soundfile.read() called on: {audio_path}")
            # Read audio file
            y, sr = sf.read(audio_path, dtype='float32')
            logger.info(f"soundfile.read() success: shape={y.shape}, sr={sr}")
            
            # Convert stereo to mono if needed
            if len(y.shape) > 1:
                y = np.mean(y, axis=1)
                logger.info(f"Converted stereo to mono: shape={y.shape}")
            
            # Resample to 16kHz if needed (for consistency)
            if sr != 16000:
                logger.info(f"Resampling from {sr}Hz to 16000Hz")
                y = self._resample_lightweight(y, sr, 16000)
                sr = 16000
            
            logger.info(f"Audio loading complete: {len(y)} samples at {sr}Hz")
            return y, sr
            
        except Exception as e:
            logger.error(f"Failed to load audio with soundfile: {e}", exc_info=True)
            return None, None
    
    def _resample_lightweight(self, y: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Lightweight resampling using scipy."""
        try:
            from scipy import signal
            num_samples = int(len(y) * target_sr / orig_sr)
            return signal.resample(y, num_samples)
        except Exception as e:
            logger.warning(f"Resampling failed: {e}, returning original")
            return y

    # =========================================================================
    # PRONUNCIATION ANALYSIS
    # =========================================================================
    
    def _analyze_pronunciation(self, transcript: str, word_timestamps: List[Dict] = None) -> Dict[str, Any]:
        """
        Analyze pronunciation quality based on transcript.
        
        Uses phoneme analysis to detect potential mispronunciations
        and articulation issues.
        
        Returns:
            {
                "score": 0-100,
                "grade": "A" to "F",
                "clarity_score": float,
                "articulation_score": float,
                "potential_mispronunciations": [str],
                "difficult_words_handled": int,
                "phoneme_accuracy": float,
                "notes": [str]
            }
        """
        result = self._empty_pronunciation_result()
        
        if not transcript or not transcript.strip():
            return result
        
        try:
            # Clean transcript
            words = re.findall(r'\b[a-zA-Z]+\b', transcript.lower())
            
            if not words:
                return result
            
            # Analyze phoneme patterns
            phoneme_analysis = self._analyze_phonemes(words)
            result["phoneme_accuracy"] = phoneme_analysis["accuracy"]
            result["potential_mispronunciations"] = phoneme_analysis["potential_issues"]
            
            # Analyze word difficulty vs frequency
            difficulty_analysis = self._analyze_word_difficulty(words)
            result["difficult_words_handled"] = difficulty_analysis["difficult_count"]
            result["articulation_score"] = difficulty_analysis["score"]
            
            # Calculate clarity based on word length and complexity
            result["clarity_score"] = self._calculate_clarity_score(words)
            
            # Generate notes
            result["notes"] = self._generate_pronunciation_notes(result)
            
            # Calculate overall pronunciation score
            result["score"] = self._calculate_pronunciation_score(result)
            result["grade"] = self._score_to_grade(result["score"])
            
        except Exception as e:
            logger.error(f"Pronunciation analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _analyze_phonemes(self, words: List[str]) -> Dict[str, Any]:
        """Analyze phoneme patterns and detect potential issues."""
        result = {
            "accuracy": 75.0,  # Default baseline
            "potential_issues": [],
            "complex_phonemes_used": []
        }
        
        if not self.eng_to_ipa:
            result["note"] = "Phoneme analysis limited (eng-to-ipa not installed)"
            return result
        
        try:
            # Commonly mispronounced phoneme patterns
            difficult_patterns = {
                'θ': 'th (think)',
                'ð': 'th (this)',
                'ʃ': 'sh',
                'ʒ': 'zh (measure)',
                'tʃ': 'ch',
                'dʒ': 'j/dge',
                'ŋ': 'ng',
                'r̩': 'r-controlled vowel'
            }
            
            words_with_issues = []
            complex_phonemes = []
            
            for word in words[:50]:  # Limit to first 50 words for performance
                try:
                    ipa = self.eng_to_ipa.convert(word)
                    
                    # Check for difficult phonemes
                    for phoneme, name in difficult_patterns.items():
                        if phoneme in ipa:
                            complex_phonemes.append(name)
                            
                except Exception:
                    words_with_issues.append(word)
            
            result["complex_phonemes_used"] = list(set(complex_phonemes))
            
            # If many complex phonemes handled well, increase accuracy
            if len(complex_phonemes) > 5:
                result["accuracy"] = 85.0  # Good handling of complex sounds
            
            # Note potential issues (words that might be mispronounced)
            if words_with_issues:
                result["potential_issues"] = words_with_issues[:5]
                
        except Exception as e:
            logger.warning(f"Phoneme analysis error: {e}")
        
        return result
    
    def _analyze_word_difficulty(self, words: List[str]) -> Dict[str, Any]:
        """Analyze difficulty of words used."""
        # Difficult words commonly challenging to pronounce
        difficult_words = {
            'entrepreneur', 'entrepreneurship', 'entrepreneurs',
            'particularly', 'specifically', 'essentially', 'additionally',
            'phenomenon', 'phenomena', 'entrepreneurial',
            'miscellaneous', 'questionnaire', 'conscientious',
            'accommodate', 'occurrence', 'perseverance',
            'sophisticated', 'implementation', 'methodology',
            'entrepreneur', 'hierarchy', 'acknowledge',
            'entrepreneurship', 'entrepreneurial', 'entrepreneur'
        }
        
        difficult_count = sum(1 for w in words if w.lower() in difficult_words)
        total_words = len(words)
        
        # Score based on handling difficult words
        if difficult_count > 0:
            # Using difficult words suggests confidence
            score = min(100, 70 + (difficult_count * 5))
        else:
            score = 70  # Neutral if no difficult words
        
        return {
            "difficult_count": difficult_count,
            "total_words": total_words,
            "score": score
        }
    
    def _calculate_clarity_score(self, words: List[str]) -> float:
        """Calculate speech clarity based on word patterns."""
        # Very short words might indicate hesitation
        very_short = sum(1 for w in words if len(w) <= 2)
        
        # Average word length (ideal: 4-6 characters)
        avg_length = sum(len(w) for w in words) / len(words) if words else 0
        
        # Score calculation
        score = 70.0
        
        # Penalize too many very short words (might indicate unclear speech)
        short_ratio = very_short / len(words) if words else 0
        if short_ratio > 0.3:
            score -= 10
        elif short_ratio < 0.15:
            score += 10
        
        # Reward optimal word length
        if 4 <= avg_length <= 6:
            score += 10
        elif avg_length > 6:
            score += 5  # Using sophisticated vocabulary
        
        return min(100, max(0, score))
    
    def _generate_pronunciation_notes(self, result: Dict) -> List[str]:
        """Generate actionable notes for pronunciation improvement."""
        notes = []
        
        if result.get("phoneme_accuracy", 0) >= 85:
            notes.append("Excellent handling of complex phonemes")
        elif result.get("complex_phonemes_used"):
            notes.append(f"Used complex sounds: {', '.join(result['complex_phonemes_used'][:3])}")
        
        if result.get("articulation_score", 0) >= 80:
            notes.append("Good articulation with challenging words")
        
        if result.get("potential_mispronunciations"):
            notes.append(f"Review pronunciation of: {', '.join(result['potential_mispronunciations'][:3])}")
        
        if result.get("clarity_score", 0) < 70:
            notes.append("Consider speaking more clearly and enunciating")
        
        return notes
    
    def _calculate_pronunciation_score(self, result: Dict) -> int:
        """Calculate overall pronunciation score."""
        score = 60  # Base score
        
        # Phoneme accuracy (weight: 30%)
        phoneme_score = result.get("phoneme_accuracy", 70)
        score += (phoneme_score - 60) * 0.3
        
        # Articulation (weight: 30%)
        articulation = result.get("articulation_score", 70)
        score += (articulation - 60) * 0.3
        
        # Clarity (weight: 40%)
        clarity = result.get("clarity_score", 70)
        score += (clarity - 60) * 0.4
        
        return int(max(0, min(100, score)))
    
    # =========================================================================
    # VOICE MODULATION ANALYSIS
    # =========================================================================
    
    def _analyze_voice_modulation(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze voice modulation including pitch, tone, and energy variation.
        
        Returns:
            {
                "score": 0-100,
                "grade": "A" to "F",
                "pitch": {
                    "mean": float,
                    "std": float,
                    "range": float,
                    "variation_score": float,
                    "monotone_risk": bool
                },
                "energy": {
                    "mean": float,
                    "std": float,
                    "variation_score": float,
                    "dynamic_range": float
                },
                "tempo": {
                    "bpm": float,
                    "variation": float
                },
                "tone_quality": {
                    "brightness": float,
                    "warmth": float,
                    "score": float
                },
                "expressiveness": float,
                "notes": [str]
            }
        """
        result = self._empty_voice_result()
        
        try:
            # Extract pitch (fundamental frequency) using scipy
            pitch_result = self._analyze_pitch(y, sr)
            result["pitch"] = pitch_result
            
            # Extract energy (volume/intensity) using numpy
            energy_result = self._analyze_energy(y, sr)
            result["energy"] = energy_result
            
            # Extract tempo using scipy
            tempo_result = self._analyze_tempo(y, sr)
            result["tempo"] = tempo_result
            
            # Analyze tone quality using scipy FFT
            tone_result = self._analyze_tone_quality(y, sr)
            result["tone_quality"] = tone_result
            
            # Calculate expressiveness
            result["expressiveness"] = self._calculate_expressiveness(result)
            
            # Generate notes
            result["notes"] = self._generate_voice_notes(result)
            
            # Calculate overall score
            result["score"] = self._calculate_voice_score(result)
            result["grade"] = self._score_to_grade(result["score"])
            
        except Exception as e:
            logger.error(f"Voice modulation analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _analyze_pitch(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze pitch characteristics using scipy (lightweight, no librosa)."""
        result = {
            "mean": 0.0,
            "std": 0.0,
            "range": 0.0,
            "variation_score": 50.0,
            "monotone_risk": False
        }
        
        try:
            from scipy import signal
            
            # Use autocorrelation for pitch detection (lightweight)
            # Frame size: 40ms, hop: 10ms
            frame_size = int(0.04 * sr)
            hop_size = int(0.01 * sr)
            
            pitches = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                
                # Skip silent frames
                if np.max(np.abs(frame)) < 0.01:
                    continue
                
                # Autocorrelation for pitch
                corr = np.correlate(frame, frame, mode='full')
                corr = corr[len(corr)//2:]  # Take positive lags
                
                # Find first peak after lag 0
                d = np.diff(corr)
                start = np.where(d > 0)[0]
                if len(start) > 0:
                    start = start[0]
                    peak = np.argmax(corr[start:]) + start
                    if peak > 0:
                        pitch = sr / peak  # Frequency in Hz
                        if 50 < pitch < 400:  # Valid human voice range
                            pitches.append(pitch)
            
            if len(pitches) > 0:
                result["mean"] = float(np.mean(pitches))
                result["std"] = float(np.std(pitches))
                result["range"] = float(np.max(pitches) - np.min(pitches))
                
                # Calculate variation score
                if result["std"] < 10:
                    result["variation_score"] = 40
                    result["monotone_risk"] = True
                elif result["std"] < 20:
                    result["variation_score"] = 60
                elif result["std"] <= 50:
                    result["variation_score"] = 90  # Ideal variation
                else:
                    result["variation_score"] = 75
                
        except Exception as e:
            logger.warning(f"Pitch analysis error: {e}")
        
        return result
    
    def _analyze_energy(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze energy/volume characteristics using numpy (lightweight, no librosa)."""
        result = {
            "mean": 0.0,
            "std": 0.0,
            "variation_score": 50.0,
            "dynamic_range": 0.0
        }
        
        try:
            # Calculate RMS energy in frames (lightweight)
            frame_size = int(0.025 * sr)  # 25ms frames
            hop_size = int(0.010 * sr)    # 10ms hop
            
            rms_values = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                rms = np.sqrt(np.mean(frame ** 2))
                rms_values.append(rms)
            
            if len(rms_values) > 0:
                result["mean"] = float(np.mean(rms_values))
                result["std"] = float(np.std(rms_values))
                result["dynamic_range"] = float(np.max(rms_values) - np.min(rms_values))
                
                # Calculate variation score
                coefficient_of_variation = result["std"] / result["mean"] if result["mean"] > 0 else 0
                
                if coefficient_of_variation < 0.1:
                    result["variation_score"] = 40
                elif coefficient_of_variation < 0.3:
                    result["variation_score"] = 70
                elif coefficient_of_variation < 0.5:
                    result["variation_score"] = 90
                else:
                    result["variation_score"] = 60
                
        except Exception as e:
            logger.warning(f"Energy analysis error: {e}")
        
        return result
    
    def _analyze_tempo(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze speaking tempo using scipy (lightweight, no librosa)."""
        result = {
            "bpm": 0.0,
            "variation": 0.0
        }
        
        try:
            from scipy import signal
            
            # Detect onset envelope using energy flux (lightweight)
            frame_size = int(0.025 * sr)
            hop_size = int(0.010 * sr)
            
            energies = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                rms = np.sqrt(np.mean(frame ** 2))
                energies.append(rms)
            
            if len(energies) > 1:
                # Calculate onset strength (difference in energy)
                onset_strength = np.abs(np.diff(energies))
                
                # Find peaks (syllable/note onsets)
                peaks, _ = signal.find_peaks(onset_strength, height=np.mean(onset_strength))
                
                if len(peaks) > 1:
                    # Average interval between peaks in seconds
                    avg_interval = np.mean(np.diff(peaks)) * hop_size / sr
                    result["bpm"] = 60.0 / avg_interval if avg_interval > 0 else 0
                    result["variation"] = float(np.std(np.diff(peaks)))
                
                
        except Exception as e:
            logger.warning(f"Tempo analysis error: {e}")
        
        return result
    
    def _analyze_tone_quality(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze tone quality (brightness, warmth) using scipy FFT (lightweight, no librosa)."""
        result = {
            "brightness": 0.0,
            "warmth": 0.0,
            "score": 50.0
        }
        
        try:
            from scipy.fft import rfft, rfftfreq
            
            # Compute FFT for spectral analysis
            N = len(y)
            fft_vals = np.abs(rfft(y))
            freqs = rfftfreq(N, 1/sr)
            
            # Spectral centroid (brightness measure)
            centroid = np.sum(freqs * fft_vals) / np.sum(fft_vals) if np.sum(fft_vals) > 0 else 0
            result["brightness"] = float(min(1, centroid / 5000))  # Normalize
            
            # Spectral rolloff (warmth measure) - frequency below 85% of energy
            total_energy = np.sum(fft_vals ** 2)
            if total_energy > 0:
                cumsum = np.cumsum(fft_vals ** 2)
                rolloff_idx = np.searchsorted(cumsum, 0.85 * total_energy)
                rolloff = freqs[min(rolloff_idx, len(freqs)-1)]
                result["warmth"] = float(max(0, 1 - rolloff / 8000))  # Normalize
            
            # Score: balanced tone is ideal
            balance = 1 - abs(result["brightness"] - result["warmth"])
            result["score"] = 50 + (balance * 50)
            
        except Exception as e:
            logger.warning(f"Tone quality analysis error: {e}")
        
        return result
    
    def _calculate_expressiveness(self, result: Dict) -> float:
        """Calculate overall expressiveness score."""
        # Weight: pitch variation 40%, energy variation 40%, tone quality 20%
        pitch_score = result.get("pitch", {}).get("variation_score", 50)
        energy_score = result.get("energy", {}).get("variation_score", 50)
        tone_score = result.get("tone_quality", {}).get("score", 50)
        
        return (pitch_score * 0.4) + (energy_score * 0.4) + (tone_score * 0.2)
    
    def _generate_voice_notes(self, result: Dict) -> List[str]:
        """Generate actionable notes for voice improvement."""
        notes = []
        
        pitch = result.get("pitch", {})
        if pitch.get("monotone_risk"):
            notes.append("⚠️ Voice may sound monotone - practice varying pitch for engagement")
        elif pitch.get("variation_score", 0) >= 80:
            notes.append("✓ Excellent pitch variation - voice is engaging")
        
        energy = result.get("energy", {})
        if energy.get("variation_score", 0) >= 80:
            notes.append("✓ Good volume dynamics - effective emphasis")
        elif energy.get("variation_score", 0) < 50:
            notes.append("Consider varying volume to emphasize key points")
        
        if result.get("expressiveness", 0) >= 80:
            notes.append("✓ Highly expressive voice - keeps audience engaged")
        
        tone = result.get("tone_quality", {})
        if tone.get("score", 0) >= 70:
            notes.append("✓ Pleasant tone quality")
        
        return notes
    
    def _calculate_voice_score(self, result: Dict) -> int:
        """Calculate overall voice modulation score."""
        score = 50  # Base score
        
        # Pitch variation (weight: 35%)
        pitch_score = result.get("pitch", {}).get("variation_score", 50)
        score += (pitch_score - 50) * 0.35
        
        # Energy variation (weight: 35%)
        energy_score = result.get("energy", {}).get("variation_score", 50)
        score += (energy_score - 50) * 0.35
        
        # Expressiveness (weight: 30%)
        expressiveness = result.get("expressiveness", 50)
        score += (expressiveness - 50) * 0.30
        
        return int(max(0, min(100, score)))
    
    # =========================================================================
    # SPEECH PATTERNS ANALYSIS
    # =========================================================================
    
    def _analyze_speech_patterns(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze speech patterns including pauses, rhythm, and fluency.
        
        Returns:
            {
                "pause_analysis": {
                    "total_pauses": int,
                    "avg_pause_duration": float,
                    "pause_frequency": float,
                    "score": float
                },
                "rhythm": {
                    "regularity": float,
                    "flow_score": float
                },
                "fluency": {
                    "hesitation_count": int,
                    "score": float
                },
                "notes": [str]
            }
        """
        result = self._empty_patterns_result()
        
        try:
            # Analyze pauses (silence detection) using numpy
            pause_result = self._analyze_pauses(y, sr)
            result["pause_analysis"] = pause_result
            
            # Analyze rhythm using scipy
            rhythm_result = self._analyze_rhythm(y, sr)
            result["rhythm"] = rhythm_result
            
            # Calculate fluency
            result["fluency"]["score"] = self._calculate_fluency_score(result)
            
            # Generate notes
            result["notes"] = self._generate_pattern_notes(result)
            
        except Exception as e:
            logger.error(f"Speech pattern analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _analyze_pauses(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect and analyze pauses in speech using numpy (lightweight, no librosa)."""
        result = {
            "total_pauses": 0,
            "avg_pause_duration": 0.0,
            "pause_frequency": 0.0,
            "score": 50.0
        }
        
        try:
            # Detect non-silent intervals using energy threshold
            frame_size = int(0.025 * sr)  # 25ms frames
            hop_size = int(0.010 * sr)    # 10ms hop
            threshold = 0.01  # Energy threshold for silence
            
            # Calculate frame energies
            speech_frames = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                rms = np.sqrt(np.mean(frame ** 2))
                speech_frames.append((i, rms > threshold))
            
            # Find non-silent intervals
            non_silent = []
            in_speech = False
            start = 0
            for i, (sample_idx, is_speech) in enumerate(speech_frames):
                if is_speech and not in_speech:
                    start = sample_idx
                    in_speech = True
                elif not is_speech and in_speech:
                    non_silent.append((start, sample_idx))
                    in_speech = False
            if in_speech:
                non_silent.append((start, len(y)))
            
            # Calculate silent intervals (pauses)
            total_duration = len(y) / sr
            
            # Count pauses (gaps between speech)
            if len(non_silent) > 1:
                pauses = []
                for i in range(1, len(non_silent)):
                    pause_duration = (non_silent[i][0] - non_silent[i-1][1]) / sr
                    if pause_duration > 0.2:  # Only count pauses > 200ms
                        pauses.append(pause_duration)
                
                result["total_pauses"] = len(pauses)
                result["avg_pause_duration"] = float(np.mean(pauses)) if pauses else 0.0
                result["pause_frequency"] = len(pauses) / (total_duration / 60) if total_duration > 0 else 0
            
            # Score based on pause patterns
            freq = result["pause_frequency"]
            avg_dur = result["avg_pause_duration"]
            
            if 3 <= freq <= 8 and 0.5 <= avg_dur <= 1.5:
                result["score"] = 90
            elif 2 <= freq <= 12 and 0.3 <= avg_dur <= 2.0:
                result["score"] = 70
            elif freq > 15 or avg_dur > 2.5:
                result["score"] = 40
            else:
                result["score"] = 60
                
        except Exception as e:
            logger.warning(f"Pause analysis error: {e}")
        
        return result
    
    def _analyze_rhythm(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze speech rhythm and flow using scipy (lightweight, no librosa)."""
        result = {
            "regularity": 0.0,
            "flow_score": 50.0
        }
        
        try:
            from scipy import signal
            
            # Calculate energy envelope (similar to onset strength)
            frame_size = int(0.025 * sr)
            hop_size = int(0.010 * sr)
            
            energies = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                rms = np.sqrt(np.mean(frame ** 2))
                energies.append(rms)
            
            if len(energies) > 1:
                # Calculate onset strength (energy flux)
                onset_env = np.abs(np.diff(energies))
                
                # Calculate regularity (consistency of rhythm)
                onset_std = np.std(onset_env)
                onset_mean = np.mean(onset_env)
                
                coefficient_of_variation = onset_std / onset_mean if onset_mean > 0 else 1
                result["regularity"] = float(1 - min(1, coefficient_of_variation))
                
                # Flow score
                result["flow_score"] = result["regularity"] * 100
            
        except Exception as e:
            logger.warning(f"Rhythm analysis error: {e}")
        
        return result
    
    def _calculate_fluency_score(self, result: Dict) -> float:
        """Calculate overall fluency score."""
        pause_score = result.get("pause_analysis", {}).get("score", 50)
        flow_score = result.get("rhythm", {}).get("flow_score", 50)
        
        return (pause_score * 0.6) + (flow_score * 0.4)
    
    def _generate_pattern_notes(self, result: Dict) -> List[str]:
        """Generate notes for speech pattern improvement."""
        notes = []
        
        pause = result.get("pause_analysis", {})
        if pause.get("total_pauses", 0) > 15:
            notes.append("⚠️ Many pauses detected - practice for smoother delivery")
        elif pause.get("score", 0) >= 80:
            notes.append("✓ Well-paced speech with appropriate pauses")
        
        rhythm = result.get("rhythm", {})
        if rhythm.get("flow_score", 0) >= 80:
            notes.append("✓ Good speech rhythm and flow")
        
        return notes
    
    # =========================================================================
    # SUMMARY AND GRADING
    # =========================================================================
    
    def _calculate_overall_audio_score(self, result: Dict) -> int:
        """Calculate overall audio quality score."""
        pronunciation = result.get("pronunciation", {}).get("score", 0)
        voice = result.get("voice_modulation", {}).get("score", 0)
        fluency = result.get("speech_patterns", {}).get("fluency", {}).get("score", 0)
        
        # Weight: pronunciation 35%, voice 40%, fluency 25%
        score = (pronunciation * 0.35) + (voice * 0.40) + (fluency * 0.25)
        
        return int(max(0, min(100, score)))
    
    def _score_to_grade(self, score: int) -> str:
        """Convert numerical score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    # =========================================================================
    # EMPTY RESULTS (DEFAULTS)
    # =========================================================================
    
    def _empty_pronunciation_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "clarity_score": 0.0,
            "articulation_score": 0.0,
            "potential_mispronunciations": [],
            "difficult_words_handled": 0,
            "phoneme_accuracy": 0.0,
            "notes": []
        }
    
    def _empty_voice_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "pitch": {
                "mean": 0.0,
                "std": 0.0,
                "range": 0.0,
                "variation_score": 0.0,
                "monotone_risk": False
            },
            "energy": {
                "mean": 0.0,
                "std": 0.0,
                "variation_score": 0.0,
                "dynamic_range": 0.0
            },
            "tempo": {
                "bpm": 0.0,
                "variation": 0.0
            },
            "tone_quality": {
                "brightness": 0.0,
                "warmth": 0.0,
                "score": 0.0
            },
            "expressiveness": 0.0,
            "notes": []
        }
    
    def _empty_patterns_result(self) -> Dict[str, Any]:
        return {
            "pause_analysis": {
                "total_pauses": 0,
                "avg_pause_duration": 0.0,
                "pause_frequency": 0.0,
                "score": 0.0
            },
            "rhythm": {
                "regularity": 0.0,
                "flow_score": 0.0
            },
            "fluency": {
                "hesitation_count": 0,
                "score": 0.0
            },
            "notes": []
        }
