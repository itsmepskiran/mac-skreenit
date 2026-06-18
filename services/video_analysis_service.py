# SECTION 1 — Imports & Class Setup

import os
import re
import tempfile
import requests
import subprocess
import shutil
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

import cv2
import numpy as np

from services.mysql_service import MySQLService
from utils_others.logger import logger


def _convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    else:
        return obj

# Whisper (lazy)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

# FER (Facial Expression Recognition) - lighter than DeepFace
try:
    from fer import FER
    FER_AVAILABLE = True
    _fer_detector = FER(mtcnn=False)  # Use OpenCV backend (lighter)
except ImportError:
    FER = None
    FER_AVAILABLE = False
    _fer_detector = None


class VideoAnalysisService:
    """
    Unified video analysis pipeline for:
    - Candidate Intro Video Analysis
    - Recruiter Response Video Analysis

    Produces:
    - Transcription
    - NLP analysis
    - Audio analysis
    - Visual analysis
    - Visual behavior analysis
    - Final 11‑parameter assessment report
    """

    def __init__(self, mysql_service: Optional[MySQLService] = None):
        self.mysql = mysql_service or MySQLService()
        self.whisper_model = None
        self.temp_dir = tempfile.gettempdir()
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if FFmpeg is installed and available."""
        # Try to find ffmpeg in PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg is not installed or not in PATH. Please install FFmpeg and add it to PATH.")
        
        try:
            result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"FFmpeg is available at: {ffmpeg_path}")
            else:
                raise RuntimeError("FFmpeg not working")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"FFmpeg check failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"FFmpeg execution failed: {str(e)}")

    def _load_whisper(self):
        """Lazy load Whisper model (base is good balance of speed/accuracy)."""
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper is not installed. Audio transcription is disabled.")
        if self.whisper_model is None:
            logger.info("Loading Whisper model (base)...")
            self.whisper_model = whisper.load_model("base")
        return self.whisper_model

    def _preprocess_video(self, video_path: str) -> str:
        """
        Preprocess video to fix format/metadata issues.
        Converts webm/variable-frame-rate videos to stable mp4 format.
        """
        try:
            # Check if video needs preprocessing
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            # If metadata looks valid, skip preprocessing
            if 10 <= fps <= 120 and 0 < total_frames < 1000000:
                logger.info(f"Video metadata looks valid (fps={fps}, frames={total_frames}), skipping preprocessing")
                return video_path
            
            # Video has issues - re-encode with FFmpeg
            logger.info(f"Video has metadata issues (fps={fps}, frames={total_frames}), re-encoding with FFmpeg")
            
            ffmpeg_path = shutil.which('ffmpeg')
            if not ffmpeg_path:
                logger.warning("FFmpeg not found, skipping preprocessing")
                return video_path
            
            output_path = video_path.replace(os.path.splitext(video_path)[1], '_processed.mp4')
            
            # Re-encode to standard MP4 with fixed 30fps
            cmd = [
                ffmpeg_path, '-y', '-i', video_path,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-r', '30',  # Force 30fps
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Video preprocessed successfully: {output_path}")
                # Verify the output
                cap = cv2.VideoCapture(output_path)
                new_fps = cap.get(cv2.CAP_PROP_FPS)
                new_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                logger.info(f"Processed video: fps={new_fps}, frames={new_frames}")
                return output_path
            else:
                logger.warning(f"FFmpeg preprocessing failed: {result.stderr}")
                return video_path
                
        except Exception as e:
            logger.warning(f"Video preprocessing failed: {e}")
            return video_path

    def download_video(self, video_url: str, candidate_id: str) -> str:
        """Download video from URL to temp file."""
        try:
            # Handle relative URLs
            if video_url.startswith('/'):
                video_url = f"http://localhost:8080{video_url}"

            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()

            # Determine extension
            content_type = response.headers.get('content-type', '')
            ext = '.mp4'
            if 'webm' in content_type:
                ext = '.webm'
            elif 'quicktime' in content_type or 'mov' in content_type:
                ext = '.mov'

            temp_path = os.path.join(self.temp_dir, f"video_analysis_{candidate_id}{ext}")

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Video downloaded: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to download video: {str(e)}")
            raise RuntimeError(f"Failed to download video: {str(e)}")
    
    def _get_cached_video_path(self, video_url: str, candidate_id: str) -> Optional[str]:
        """
        Get video path for face matching - either existing or re-download.
        Uses a unique filename based on video_url hash to avoid conflicts.
        """
        try:
            # Create unique filename based on URL hash
            import hashlib
            url_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
            
            # Check for existing video files with this candidate_id
            for ext in ['.mp4', '.webm', '.mov']:
                existing_path = os.path.join(self.temp_dir, f"video_analysis_{candidate_id}{ext}")
                if os.path.exists(existing_path):
                    return existing_path
            
            # Also check for hash-based filename
            for ext in ['.mp4', '.webm', '.mov']:
                hash_path = os.path.join(self.temp_dir, f"video_face_{candidate_id}_{url_hash}{ext}")
                if os.path.exists(hash_path):
                    return hash_path
            
            # Re-download for face matching
            logger.info(f"Re-downloading video for face matching: {video_url}")
            return self.download_video(video_url, f"{candidate_id}_{url_hash}")
            
        except Exception as e:
            logger.warning(f"Failed to get video path for face matching: {e}")
            return None

    def extract_audio(self, video_path: str) -> str:
        """Extract audio from video using FFmpeg."""
        try:
            audio_path = video_path.replace(os.path.splitext(video_path)[1], '_audio.wav')
            
            # Get FFmpeg path
            ffmpeg_path = shutil.which('ffmpeg')
            logger.info(f"FFmpeg path found: {ffmpeg_path}")
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg not found in PATH")

            # FFmpeg command to extract audio
            cmd = [
                ffmpeg_path, '-y', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                audio_path
            ]
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            logger.info(f"Audio extracted successfully to: {audio_path}")
            return audio_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg timeout - video too long")
        except Exception as e:
            logger.error(f"Audio extraction failed: {str(e)}")
            raise RuntimeError(f"Audio extraction failed: {str(e)}")

    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper."""
        if not WHISPER_AVAILABLE:
            logger.warning("Whisper not available, returning empty transcription")
            return {
                'transcript': '',
                'word_count': 0,
                'duration_seconds': 0,
                'wpm': 0,
                'filler_words': 0,
                'error': 'Whisper not installed'
            }
        
        try:
            logger.info(f"Transcribing audio from: {audio_path}")
            model = self._load_whisper()
            result = model.transcribe(audio_path, language='en', fp16=False)

            text = result.get('text', '').strip()
            segments = result.get('segments', [])
            
            # Get duration - prefer segments end time as it's more reliable
            duration = result.get('duration', 0)
            if duration <= 0 and segments:
                # Calculate from last segment's end time
                duration = segments[-1].get('end', 0) if segments else 0
            
            # Fallback: get duration from audio file using soundfile (lightweight)
            if duration <= 0:
                try:
                    import soundfile as sf
                    info = sf.info(audio_path)
                    duration = info.duration
                    logger.info(f"Got duration from soundfile: {duration} seconds")
                except Exception as e:
                    logger.warning(f"Could not get duration from soundfile: {e}")
                    duration = 0
            
            logger.info(f"Transcription result - text length: {len(text)}, duration: {duration}, segments: {len(segments)}")

            # Calculate word count and speaking pace
            words = text.split()
            word_count = len(words)

            # Calculate WPM (words per minute)
            wpm = round((word_count / duration) * 60) if duration > 0 else 0

            # Detect filler words
            filler_words = ['um', 'uh', 'like', 'you know', 'so', 'basically', 'actually', 'right']
            filler_count = sum(1 for word in words if word.lower().strip('.,!?') in filler_words)

            logger.info(f"Transcription stats - word_count: {word_count}, wpm: {wpm}, duration: {duration}")

            return {
                'transcript': text,
                'word_count': word_count,
                'duration_seconds': round(duration, 1),
                'wpm': wpm,
                'filler_words': filler_count,
                'language': result.get('language', 'en')
            }

        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                'transcript': '',
                'word_count': 0,
                'duration_seconds': 0,
                'wpm': 0,
                'filler_words': 0,
                'error': str(e)
            }

    def analyze_frames(self, video_path: str, sample_interval: int = 2, audio_duration: float = 0) -> Dict[str, Any]:
        """
        Sample frames and analyze emotions/face presence.
        Returns emotion distribution, face detection rate, and confidence metrics.
        
        Args:
            video_path: Path to video file
            sample_interval: Seconds between frame samples
            audio_duration: Duration from audio extraction (more reliable than video metadata)
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError("Could not open video file")

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            logger.info(f"OpenCV video info - fps: {fps}, total_frames: {total_frames}")
            
            # Calculate duration - prefer audio_duration as it's more reliable
            # OpenCV can return invalid values for webm files
            if audio_duration > 0:
                duration = audio_duration
                logger.info(f"Using audio duration: {duration} seconds")
            elif fps > 0 and total_frames > 0 and total_frames < 1e15:  # Sanity check for invalid values
                duration = total_frames / fps
                logger.info(f"Calculated duration from video: {duration} seconds")
            else:
                duration = 0
                logger.warning(f"Invalid video metadata - fps: {fps}, frames: {total_frames}, audio_duration: {audio_duration}")
            
            # Frame interval - use reasonable defaults if fps is invalid
            if fps > 0 and fps < 120:  # Sanity check
                frame_interval = int(fps * sample_interval)
            else:
                frame_interval = 30  # Default: sample every ~1 second at 30fps
            emotions = []
            face_detected_count = 0
            total_samples = 0
            confidence_scores = []

            frame_num = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample every N seconds
                if frame_num % frame_interval == 0:
                    total_samples += 1

                    try:
                        # FER emotion analysis (lighter than DeepFace)
                        if not FER_AVAILABLE or _fer_detector is None:
                            logger.warning("FER not available, skipping emotion analysis")
                            break
                        
                        try:
                            # FER returns dict with emotions and dominant emotion
                            analysis = _fer_detector.detect_emotions(frame)
                            
                            if analysis and len(analysis) > 0:
                                face_detected_count += 1
                                emotion_data = analysis[0].get('emotions', {})
                                if emotion_data:
                                    # FER returns emotions as percentages
                                    dominant_emotion = max(emotion_data, key=emotion_data.get)
                                    emotions.append(dominant_emotion)
                                    # Get confidence score (dominant emotion value)
                                    confidence = emotion_data.get(dominant_emotion, 0)
                                    confidence_scores.append(confidence)
                        except Exception as fer_error:
                            logger.warning(f"FER analysis failed for frame {frame_num}: {fer_error}")
                            # Continue without this frame - that's okay
                            pass

                    except Exception as e:
                        # Face not detected in this frame - that's okay
                        pass

                frame_num += 1

            cap.release()

            # Calculate emotion distribution
            emotion_counts = {}
            for e in emotions:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1

            # Normalize to percentages
            if emotions:
                emotion_distribution = {
                    k: round((v / len(emotions)) * 100, 1)
                    for k, v in emotion_counts.items()
                }
                dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            else:
                emotion_distribution = {}
                dominant_emotion = 'unknown'

            # Face presence rate
            face_presence_rate = round((face_detected_count / total_samples) * 100, 1) if total_samples > 0 else 0

            # Average confidence
            avg_confidence = round(sum(confidence_scores) / len(confidence_scores), 1) if confidence_scores else 0

            return {
                'emotion_distribution': emotion_distribution,
                'dominant_emotion': dominant_emotion,
                'face_presence_rate': face_presence_rate,
                'avg_confidence': avg_confidence,
                'total_frames_analyzed': total_samples,
                'face_detected_frames': face_detected_count,
                'duration_seconds': round(duration, 1),
                'fps': round(fps, 2) if fps > 0 else 0
            }

        except Exception as e:
            logger.error(f"Frame analysis failed: {str(e)}")
            return {
                'emotion_distribution': {},
                'dominant_emotion': 'error',
                'face_presence_rate': 0,
                'error': str(e)
            }

    # SECTION 2 — Main Pipeline

    def analyze_video(
        self,
        video_url: str,
        candidate_id: str,
        video_type: str = "intro",      # "intro" or "response"
        application_id: str = None,
        question_index: int = None
    ) -> Dict[str, Any]:

        video_path = None
        audio_path = None
        processed_video_path = None

        try:
            logger.info(f"Starting {video_type} video analysis for candidate {candidate_id}")

            # 1. Download
            video_path = self.download_video(video_url, candidate_id)

            # 2. Preprocess (fix metadata)
            processed_video_path = self._preprocess_video(video_path)
            analysis_video_path = processed_video_path or video_path

            # 3. Extract audio
            audio_path = self.extract_audio(video_path)

            # 4. Transcribe
            transcription_data = self.transcribe_audio(audio_path)
            audio_duration = transcription_data.get("duration_seconds", 0)

            # 5. Visual analysis (FER)
            frame_analysis = self.analyze_frames(
                analysis_video_path,
                audio_duration=audio_duration
            )

            # 6. Visual behavior (motion, posture, eye contact)
            visual_behavior = self._analyze_visual_behavior(
                analysis_video_path,
                emotion_data=frame_analysis,
                sample_interval=1,
                audio_duration=audio_duration
            )

            # 7. NLP analysis
            nlp_analysis = self._analyze_communication_skills(
                transcription_data.get("transcript", "")
            )

            # 8. Audio analysis
            audio_analysis = self._analyze_audio_features(
                audio_path,
                transcription_data.get("transcript", ""),
                transcription_data.get("word_timestamps", None)
            )

            # 9. Final 11‑parameter assessment report
            assessment_report = self._generate_assessment_report(
                transcription_data,
                frame_analysis,
                nlp_analysis,
                audio_analysis,
                visual_behavior,
                candidate_id
            )

            # 10. Build final response
            video_duration = frame_analysis.get("duration_seconds", 0)
            word_count = transcription_data.get("word_count", 0)
            wpm = round((word_count / video_duration) * 60) if video_duration > 0 else 0

            result = {
                "candidate_id": candidate_id,
                "video_url": video_url,
                "video_type": video_type,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),

                "transcription": transcription_data,
                "visual_analysis": frame_analysis,
                "visual_behavior": visual_behavior,
                "nlp_analysis": nlp_analysis,
                "audio_analysis": audio_analysis,

                "assessment": assessment_report,

                "summary": {
                    "speaking_pace": wpm,
                    "word_count": word_count,
                    "duration": video_duration,
                    "filler_words": transcription_data.get("filler_words", 0),
                    "confidence_score": frame_analysis.get("avg_confidence", 0),
                    "dominant_emotion": frame_analysis.get("dominant_emotion", "unknown"),
                    "face_presence": frame_analysis.get("face_presence_rate", 0),
                    "eye_contact_rate": visual_behavior.get("eye_contact", {}).get("eye_contact_rate", 0),
                    "motion_level": visual_behavior.get("motion_analysis", {}).get("motion_level", "unknown"),
                    "visual_confidence": visual_behavior.get("confidence_visual", {}).get("score", 0),
                    "overall_score": assessment_report.get("executive_summary", {}).get("overall_score", 0),
                    "overall_grade": assessment_report.get("executive_summary", {}).get("overall_grade", "N/A"),
                    "recommendation": assessment_report.get("executive_summary", {}).get("recommendation", "N/A")
                }
            }

            # 11. Save to DB
            self._save_analysis(
                candidate_id,
                result,
                video_url,
                video_type=video_type,
                application_id=application_id,
                question_index=question_index
            )

            # Convert numpy types to Python native types for JSON serialization
            return _convert_numpy_types(result)

        except Exception as e:
            logger.error(f"Video analysis failed: {str(e)}")
            raise

        finally:
            self._cleanup_files(video_path, audio_path, processed_video_path)

    def _analyze_audio_features(self, audio_path: str, transcript: str, word_timestamps: List = None) -> Dict[str, Any]:
        """Analyze audio features including pronunciation and voice modulation."""
        logger.info(f"_analyze_audio_features called with audio_path={audio_path}, transcript_len={len(transcript) if transcript else 0}")
        
        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"Audio file does not exist: {audio_path}")
            return {
                "pronunciation": {"score": 0, "grade": "N/A", "note": "Audio file not found"},
                "voice_modulation": {"score": 0, "grade": "N/A", "note": "Audio file not found"},
                "speech_patterns": {"score": 0, "note": "Audio file not found"},
                "summary": {"overall_audio_score": 0}
            }
        
        try:
            from services.audio_analysis_service import AudioAnalysisService
            audio_service = AudioAnalysisService()
            result = audio_service.analyze_audio(audio_path, transcript, word_timestamps)
            logger.info(f"Audio analysis result: pronunciation_score={result.get('pronunciation', {}).get('score', 0)}, voice_score={result.get('voice_modulation', {}).get('score', 0)}")
            return result
        except ImportError as e:
            logger.warning(f"AudioAnalysisService not available: {e}. Skipping audio analysis.")
            return {
                "pronunciation": {"score": 0, "grade": "N/A", "note": "Audio analysis unavailable"},
                "voice_modulation": {"score": 0, "grade": "N/A", "note": "Audio analysis unavailable"},
                "speech_patterns": {"score": 0, "note": "Audio analysis unavailable"},
                "summary": {"overall_audio_score": 0}
            }
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}", exc_info=True)
            return {
                "pronunciation": {"score": 0, "error": str(e)},
                "voice_modulation": {"score": 0, "error": str(e)},
                "speech_patterns": {"score": 0, "error": str(e)},
                "summary": {"overall_audio_score": 0, "error": str(e)}
            }

# SECTION 3 — Assessment Report Hook

    def _generate_assessment_report(
        self,
        transcription: Dict,
        visual: Dict,
        nlp: Dict,
        audio: Dict,
        visual_behavior: Dict,
        candidate_id: str
    ) -> Dict[str, Any]:
        """
        Calls the new 11‑parameter AssessmentReportService.
        """
        try:
            from services.assessment_report_service import AssessmentReportService
            report_service = AssessmentReportService()

            return report_service.generate_report(
                transcription=transcription,
                visual_analysis=visual,
                nlp_analysis=nlp,
                audio_analysis=audio,
                visual_behavior=visual_behavior,
                candidate_info={"candidate_id": candidate_id}
            )

        except Exception as e:
            logger.error(f"Assessment report generation failed: {e}")
            return {
                "executive_summary": {
                    "overall_score": 0,
                    "overall_grade": "N/A",
                    "recommendation": "Assessment unavailable",
                    "error": str(e)
                },
                "parameters": {},
                "strengths": [],
                "areas_for_improvement": []
            }


    def _analyze_visual_behavior(self, video_path: str, emotion_data: Dict = None, sample_interval: int = 1, audio_duration: float = 0) -> Dict[str, Any]:
        """Analyze visual behavior including motion, eye contact, and confidence."""
        try:
            from services.visual_behavior_service import VisualBehaviorService
            behavior_service = VisualBehaviorService()
            return behavior_service.analyze_visual_behavior(video_path, emotion_data, sample_interval, audio_duration)
        except ImportError:
            logger.warning("VisualBehaviorService not available. Skipping visual behavior analysis.")
            return {
                "motion_analysis": {"score": 0, "grade": "N/A", "note": "Visual behavior analysis unavailable"},
                "eye_contact": {"score": 0, "grade": "N/A", "eye_contact_rate": 0},
                "posture_analysis": {"score": 0, "grade": "N/A"},
                "confidence_visual": {"score": 0, "grade": "N/A"},
                "summary": {"visual_behavior_score": 0}
            }
        except Exception as e:
            logger.error(f"Visual behavior analysis failed: {e}")
            return {
                "motion_analysis": {"score": 0, "error": str(e)},
                "eye_contact": {"score": 0, "error": str(e)},
                "posture_analysis": {"score": 0, "error": str(e)},
                "confidence_visual": {"score": 0, "error": str(e)},
                "summary": {"visual_behavior_score": 0, "error": str(e)}
            }

    def _analyze_communication_skills(self, transcript: str) -> Dict[str, Any]:
        """Analyze communication skills using NLP service."""
        try:
            from services.nlp_analysis_service import NLPAnalysisService
            nlp_service = NLPAnalysisService()
            return nlp_service.analyze_transcript(transcript)
        except ImportError:
            logger.warning("NLPAnalysisService not available. Skipping communication analysis.")
            return {
                "grammar": {"score": 0, "note": "NLP analysis unavailable"},
                "sentence_formation": {"score": 0},
                "vocabulary": {"score": 0},
                "communication_skills": {"score": 0, "level": "unknown"},
                "summary": {"communication_score": 0}
            }
        except Exception as e:
            logger.error(f"NLP analysis failed: {e}")
            return {
                "grammar": {"score": 0, "error": str(e)},
                "sentence_formation": {"score": 0},
                "vocabulary": {"score": 0},
                "communication_skills": {"score": 0, "level": "unknown"},
                "summary": {"communication_score": 0}
            }

    def _calculate_overall_score(self, transcription: Dict, visual: Dict, nlp: Dict = None) -> int:
        """Calculate an overall confidence/quality score (0-100)."""
        score = 50  # Base score

        # Speaking pace: ideal is 120-150 WPM
        wpm = transcription.get('wpm', 0)
        if 120 <= wpm <= 150:
            score += 15
        elif 100 <= wpm <= 170:
            score += 10
        elif wpm > 0:
            score += 5

        # Face presence (eye contact/professional setup)
        face_presence = visual.get('face_presence_rate', 0)
        if face_presence >= 90:
            score += 20
        elif face_presence >= 70:
            score += 15
        elif face_presence >= 50:
            score += 10
        else:
            score -= 10

        # Emotion confidence
        confidence = visual.get('avg_confidence', 0)
        if confidence >= 80:
            score += 15
        elif confidence >= 60:
            score += 10
        elif confidence >= 40:
            score += 5

        # Duration (ideal 60-90 seconds)
        duration = transcription.get('duration_seconds', 0)
        if 60 <= duration <= 90:
            score += 10
        elif duration > 30:
            score += 5

        # Filler words penalty
        filler_count = transcription.get('filler_words', 0)
        if filler_count == 0:
            score += 10
        elif filler_count <= 3:
            score += 5
        elif filler_count > 10:
            score -= 10

        # NLP Communication Score (if available)
        if nlp and nlp.get('communication_skills', {}).get('score', 0) > 0:
            comm_score = nlp['communication_skills']['score']
            # Weight: 30% of overall score comes from communication
            nlp_contribution = (comm_score - 50) * 0.3  # Normalize around 50
            score += nlp_contribution

        return max(0, min(100, int(score)))

    def _save_analysis(self, candidate_id: str, analysis: Dict, video_url: str, video_type: str = 'intro', application_id: str = None, question_index: int = None):
        """Save analysis results to database."""
        try:
            import hashlib
            # Generate video hash for uniqueness
            video_hash = hashlib.sha256(video_url.encode()).hexdigest()
            
            # Check if this specific video already has analysis (by video_hash)
            existing = self.mysql.get_video_analysis({"video_hash": video_hash})
            
            analysis_data = {
                "video_url": video_url,
                "video_type": video_type,
                "video_hash": video_hash,
                "analysis_data": json.dumps(_convert_numpy_types(analysis)),
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Add application_id and question_index for video responses
            if application_id:
                analysis_data["application_id"] = application_id
            if question_index is not None:
                analysis_data["question_index"] = question_index
            
            if existing:
                # Update existing analysis for this video
                self.mysql.update_video_analysis(
                    analysis_data,
                    {"video_hash": video_hash}
                )
                logger.info(f"Updated analysis for candidate {candidate_id}, video_type: {video_type}")
            else:
                # Create new analysis record
                self.mysql.create_video_analysis({
                    "candidate_id": candidate_id,
                    **analysis_data
                })
                logger.info(f"New analysis saved for candidate {candidate_id}, video_type: {video_type}")

        except Exception as e:
            logger.error(f"Failed to save analysis: {str(e)}")
            # Don't raise - analysis succeeded even if save failed

    def get_analysis(self, candidate_id: str, video_url: str = None, video_hash: str = None) -> Optional[Dict]:
        """Retrieve existing analysis for a candidate."""
        try:
            logger.info(f"get_analysis called: candidate_id={candidate_id}, video_url={video_url}, video_hash={video_hash}")
            
            if video_hash:
                # Best case: lookup by video hash
                analysis = self.mysql.get_video_analysis({"video_hash": video_hash})
                logger.info(f"Lookup by video_hash: found={analysis is not None}")
            elif video_url:
                # Fallback: lookup by video URL
                analysis = self.mysql.get_video_analysis({"video_url": video_url})
                logger.info(f"Lookup by video_url: found={analysis is not None}")
            else:
                # Last resort: get latest analysis for candidate
                analysis = self.mysql.get_video_analysis({"candidate_id": candidate_id})
                logger.info(f"Lookup by candidate_id: found={analysis is not None}")
            
            if analysis and analysis.get("analysis_data"):
                # Parse the JSON string and add analyzed_at
                result = json.loads(analysis.get("analysis_data"))
                result["analyzed_at"] = analysis.get("analyzed_at")
                logger.info(f"Returning analysis with keys: {list(result.keys())}")
                return result
            
            logger.warning(f"No analysis found for candidate_id={candidate_id}, video_url={video_url}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve analysis: {str(e)}")
            return None

    def _cleanup_files(self, video_path: Optional[str], audio_path: Optional[str], processed_video_path: Optional[str] = None):
        """Clean up temporary files."""
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            # Clean up preprocessed video if it exists and is different from original
            if processed_video_path and processed_video_path != video_path and os.path.exists(processed_video_path):
                os.remove(processed_video_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {str(e)}")
