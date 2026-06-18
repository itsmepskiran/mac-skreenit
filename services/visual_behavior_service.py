"""
Visual Behavior Analysis Service for Video Interviews
Analyzes confidence, motion, eye contact, and body language from video frames.

Uses:
- OpenCV for motion detection
- MediaPipe for face landmarks and eye gaze estimation
- FER for emotion-based confidence scoring
"""

import os
import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)

# Lazy imports
_mediapipe_face_mesh = None


def _get_face_mesh():
    """Lazy load MediaPipe Face Mesh for eye tracking."""
    global _mediapipe_face_mesh
    if _mediapipe_face_mesh is None:
        try:
            import mediapipe as mp
            _mediapipe_face_mesh = mp.solutions.face_mesh
            logger.info("MediaPipe Face Mesh loaded for eye tracking")
        except ImportError:
            logger.warning("MediaPipe not installed. Eye contact detection limited.")
    return _mediapipe_face_mesh


class VisualBehaviorService:
    """
    Analyzes visual behavior in video interviews including:
    - Motion and body movement (fidgeting, gestures)
    - Eye contact (looking at camera vs away)
    - Confidence from visual cues
    - Professional posture
    """
    
    def __init__(self):
        self.face_mesh_module = _get_face_mesh()
    
    def analyze_visual_behavior(
        self, 
        video_path: str, 
        emotion_data: Dict = None,
        sample_interval: int = 1,  # Sample every N seconds
        audio_duration: float = 0  # Duration from audio (more reliable than video metadata)
    ) -> Dict[str, Any]:
        """
        Main method to analyze visual behavior from video.
        
        Args:
            video_path: Path to video file
            emotion_data: Pre-computed emotion analysis from FER
            sample_interval: Interval in seconds between frame samples
            audio_duration: Duration from audio extraction (more reliable than video metadata)
        
        Returns:
            Dictionary containing all visual behavior analysis
        """
        result = {
            "motion_analysis": self._empty_motion_result(),
            "eye_contact": self._empty_eye_contact_result(),
            "confidence_visual": self._empty_confidence_result(),
            "posture_analysis": self._empty_posture_result(),
            "summary": {
                "visual_behavior_score": 0,
                "grade": "N/A"
            }
        }
        
        if not os.path.exists(video_path):
            result["error"] = f"Video file not found: {video_path}"
            return result
        
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError("Could not open video file")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Handle invalid video metadata (common with webm files)
            # Use audio_duration as fallback since it's more reliable
            if fps <= 0 or fps > 120 or total_frames <= 0 or total_frames > 1e15:
                logger.warning(f"Invalid video metadata - fps: {fps}, frames: {total_frames}, using defaults")
                fps = 30  # Default reasonable fps
                total_frames = int(audio_duration * fps) if audio_duration > 0 else 0
            
            frame_interval = int(fps * sample_interval)
            
            # Initialize trackers
            motion_scores = []
            eye_contact_frames = []
            confidence_frames = []
            posture_scores = []
            frame_positions = []  # Track face position over time
            
            prev_frame = None
            frame_num = 0
            
            # Face mesh for eye tracking
            face_mesh = None
            if self.face_mesh_module:
                face_mesh = self.face_mesh_module.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_num % frame_interval == 0:
                    # Convert to grayscale for motion detection
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.GaussianBlur(gray, (21, 21), 0)
                    
                    # 1. Motion Analysis
                    if prev_frame is not None:
                        motion_score = self._calculate_motion(prev_frame, gray)
                        motion_scores.append(motion_score)
                    
                    prev_frame = gray
                    
                    # 2. Eye Contact Analysis
                    eye_result = self._analyze_eye_contact(frame, face_mesh)
                    eye_contact_frames.append(eye_result)
                    
                    # 3. Posture/Position Analysis
                    posture_result = self._analyze_posture(frame, face_mesh)
                    posture_scores.append(posture_result["score"])
                    frame_positions.append(posture_result.get("face_center", (0, 0)))
                    
                    # 4. Confidence from visual cues
                    confidence_result = self._assess_visual_confidence(
                        frame, eye_result, posture_result, emotion_data
                    )
                    confidence_frames.append(confidence_result)
                
                frame_num += 1
            
            # Aggregate results
            result["motion_analysis"] = self._aggregate_motion_results(motion_scores)
            result["eye_contact"] = self._aggregate_eye_contact_results(eye_contact_frames)
            result["posture_analysis"] = self._aggregate_posture_results(posture_scores, frame_positions)
            result["confidence_visual"] = self._aggregate_confidence_results(confidence_frames)
            
            # Calculate overall visual behavior score
            result["summary"]["visual_behavior_score"] = self._calculate_overall_visual_score(result)
            result["summary"]["grade"] = self._score_to_grade(result["summary"]["visual_behavior_score"])
            
            if face_mesh:
                face_mesh.close()
                
        except Exception as e:
            logger.error(f"Visual behavior analysis failed: {e}")
            result["error"] = str(e)
        
        finally:
            if cap:
                cap.release()
        
        return result
    
    # =========================================================================
    # MOTION ANALYSIS
    # =========================================================================
    
    def _calculate_motion(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
        """
        Calculate motion between frames.
        Returns motion score (0-100, higher = more movement).
        """
        try:
            # Calculate absolute difference
            frame_delta = cv2.absdiff(prev_frame, curr_frame)
            
            # Threshold the difference
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            
            # Dilate to fill holes
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Calculate motion as percentage of changed pixels
            motion_pixels = np.count_nonzero(thresh)
            total_pixels = thresh.shape[0] * thresh.shape[1]
            motion_ratio = motion_pixels / total_pixels
            
            # Scale to 0-100
            return min(100, motion_ratio * 1000)  # Amplify small movements
            
        except Exception as e:
            logger.warning(f"Motion calculation error: {e}")
            return 0
    
    def _aggregate_motion_results(self, motion_scores: List[float]) -> Dict[str, Any]:
        """Aggregate motion analysis results."""
        if not motion_scores:
            return self._empty_motion_result()
        
        avg_motion = np.mean(motion_scores)
        std_motion = np.std(motion_scores)
        
        # Determine motion level
        if avg_motion < 5:
            level = "Very Low"
            assessment = "Too still - may appear stiff or nervous"
            score = 60
        elif avg_motion < 15:
            level = "Low"
            assessment = "Calm and composed - good for professional setting"
            score = 90
        elif avg_motion < 30:
            level = "Moderate"
            assessment = "Natural movement with good energy"
            score = 85
        elif avg_motion < 50:
            level = "High"
            assessment = "Active gesturing - may be enthusiastic or nervous"
            score = 70
        else:
            level = "Very High"
            assessment = "Excessive movement - may appear restless"
            score = 50
        
        # Check for fidgeting (high variance in motion)
        fidgeting = std_motion > 20
        
        return {
            "score": score,
            "grade": self._score_to_grade(score),
            "average_motion": round(avg_motion, 2),
            "motion_variance": round(std_motion, 2),
            "motion_level": level,
            "assessment": assessment,
            "fidgeting_detected": fidgeting,
            "notes": self._generate_motion_notes(avg_motion, std_motion, fidgeting)
        }
    
    def _generate_motion_notes(self, avg: float, std: float, fidgeting: bool) -> List[str]:
        """Generate notes for motion analysis."""
        notes = []
        
        if avg < 5:
            notes.append("⚠️ Very low movement - consider using natural hand gestures")
        elif avg < 30:
            notes.append("✓ Good composure with natural movement")
        else:
            notes.append("⚠️ High movement detected - try to stay more centered")
        
        if fidgeting:
            notes.append("⚠️ Fidgeting detected - practice stillness during key points")
        
        return notes
    
    # =========================================================================
    # EYE CONTACT ANALYSIS
    # =========================================================================
    
    def _analyze_eye_contact(self, frame: np.ndarray, face_mesh) -> Dict[str, Any]:
        """
        Analyze eye contact using face landmarks.
        Detects if person is looking at camera or away.
        """
        result = {
            "looking_at_camera": False,
            "confidence": 0.0,
            "gaze_direction": "unknown"
        }
        
        if not face_mesh:
            # Fallback: use face detection to estimate
            return self._estimate_eye_contact_simple(frame)
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                
                # Get key eye landmarks
                # Left eye: landmarks 33 (inner), 133 (outer), 159 (top), 145 (bottom)
                # Right eye: landmarks 362 (inner), 263 (outer), 386 (top), 374 (bottom)
                # Iris: landmarks 468 (left center), 473 (right center)
                
                h, w = frame.shape[:2]
                
                # Get iris positions if available (refined landmarks)
                # These are indices 468-477 for left eye, 478-487 for right eye
                left_iris_x = landmarks.landmark[468].x if len(landmarks.landmark) > 468 else None
                left_iris_y = landmarks.landmark[468].y if len(landmarks.landmark) > 468 else None
                right_iris_x = landmarks.landmark[473].x if len(landmarks.landmark) > 473 else None
                right_iris_y = landmarks.landmark[473].y if len(landmarks.landmark) > 473 else None
                
                if left_iris_x and right_iris_x:
                    # Check if iris is centered in the eye
                    # Get eye corners
                    left_eye_inner = landmarks.landmark[33].x
                    left_eye_outer = landmarks.landmark[133].x
                    right_eye_inner = landmarks.landmark[362].x
                    right_eye_outer = landmarks.landmark[263].x
                    
                    # Calculate eye center
                    left_eye_center = (left_eye_inner + left_eye_outer) / 2
                    right_eye_center = (right_eye_inner + right_eye_outer) / 2
                    
                    # Check if iris is close to center
                    left_offset = abs(left_iris_x - left_eye_center)
                    right_offset = abs(right_iris_x - right_eye_center)
                    
                    avg_offset = (left_offset + right_offset) / 2
                    
                    # Looking at camera if iris is centered
                    if avg_offset < 0.02:  # Threshold for "centered"
                        result["looking_at_camera"] = True
                        result["gaze_direction"] = "center"
                        result["confidence"] = 95 - (avg_offset * 1000)
                    elif left_iris_x < left_eye_center - 0.02:
                        result["gaze_direction"] = "left"
                        result["confidence"] = 50
                    elif left_iris_x > left_eye_center + 0.02:
                        result["gaze_direction"] = "right"
                        result["confidence"] = 50
                    else:
                        result["looking_at_camera"] = True
                        result["gaze_direction"] = "center"
                        result["confidence"] = 80
                        
        except Exception as e:
            logger.warning(f"Eye contact analysis error: {e}")
        
        return result
    
    def _estimate_eye_contact_simple(self, frame: np.ndarray) -> Dict[str, Any]:
        """Simple eye contact estimation without face mesh."""
        # Use face detection to check if face is centered
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                # Assume looking at camera if face is detected and frontal
                return {
                    "looking_at_camera": True,
                    "confidence": 70,  # Lower confidence without iris tracking
                    "gaze_direction": "estimated_center"
                }
        except Exception:
            pass
        
        return {
            "looking_at_camera": False,
            "confidence": 0,
            "gaze_direction": "unknown"
        }
    
    def _aggregate_eye_contact_results(self, eye_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate eye contact analysis results."""
        if not eye_results:
            return self._empty_eye_contact_result()
        
        looking_count = sum(1 for r in eye_results if r.get("looking_at_camera", False))
        total_frames = len(eye_results)
        
        eye_contact_rate = (looking_count / total_frames) * 100 if total_frames > 0 else 0
        avg_confidence = np.mean([r.get("confidence", 0) for r in eye_results])
        
        # Determine gaze patterns
        gaze_directions = [r.get("gaze_direction", "unknown") for r in eye_results]
        gaze_counts = {}
        for g in gaze_directions:
            gaze_counts[g] = gaze_counts.get(g, 0) + 1
        
        dominant_gaze = max(gaze_counts, key=gaze_counts.get) if gaze_counts else "unknown"
        
        # Score calculation
        if eye_contact_rate >= 90:
            score = 95
            assessment = "Excellent eye contact throughout"
        elif eye_contact_rate >= 75:
            score = 85
            assessment = "Good eye contact with occasional breaks"
        elif eye_contact_rate >= 50:
            score = 70
            assessment = "Moderate eye contact - room for improvement"
        else:
            score = 45
            assessment = "Poor eye contact - frequently looking away"
        
        return {
            "score": score,
            "grade": self._score_to_grade(score),
            "eye_contact_rate": round(eye_contact_rate, 1),
            "avg_confidence": round(avg_confidence, 1),
            "dominant_gaze": dominant_gaze,
            "assessment": assessment,
            "notes": self._generate_eye_contact_notes(eye_contact_rate, dominant_gaze)
        }
    
    def _generate_eye_contact_notes(self, rate: float, dominant: str) -> List[str]:
        """Generate notes for eye contact."""
        notes = []
        
        if rate >= 90:
            notes.append("✓ Excellent eye contact - maintains professional engagement")
        elif rate >= 75:
            notes.append("✓ Good eye contact overall")
        elif rate >= 50:
            notes.append("⚠️ Inconsistent eye contact - practice looking at camera")
        else:
            notes.append("⚠️ Poor eye contact - this may appear disengaged or nervous")
        
        if dominant == "left" or dominant == "right":
            notes.append(f"⚠️ Frequently looking {dominant} - try to center gaze")
        
        return notes
    
    # =========================================================================
    # POSTURE ANALYSIS
    # =========================================================================
    
    def _analyze_posture(self, frame: np.ndarray, face_mesh) -> Dict[str, Any]:
        """Analyze posture and face positioning."""
        result = {
            "score": 50,
            "face_center": (0, 0),
            "face_size_ratio": 0,
            "positioning": "unknown"
        }
        
        try:
            # Simple face detection for posture
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                x, y, w, h = faces[0]
                frame_h, frame_w = frame.shape[:2]
                
                # Face center
                face_center = (x + w/2, y + h/2)
                result["face_center"] = face_center
                
                # Face size ratio (should be reasonable portion of frame)
                face_area = w * h
                frame_area = frame_w * frame_h
                result["face_size_ratio"] = face_area / frame_area
                
                # Check positioning
                center_x = frame_w / 2
                center_y = frame_h / 2
                
                # How centered is the face?
                x_offset = abs(face_center[0] - center_x) / center_x
                y_offset = abs(face_center[1] - center_y) / center_y
                
                # Score based on centering
                if x_offset < 0.1 and y_offset < 0.2:
                    result["positioning"] = "well_centered"
                    result["score"] = 90
                elif x_offset < 0.2 and y_offset < 0.3:
                    result["positioning"] = "acceptable"
                    result["score"] = 75
                else:
                    result["positioning"] = "off_center"
                    result["score"] = 60
                
                # Check face size (should be 15-40% of frame)
                if 0.15 <= result["face_size_ratio"] <= 0.40:
                    result["score"] += 10
                elif result["face_size_ratio"] < 0.10:
                    result["positioning"] += "_too_far"
                    result["score"] -= 10
                elif result["face_size_ratio"] > 0.50:
                    result["positioning"] += "_too_close"
                    result["score"] -= 5
                    
        except Exception as e:
            logger.warning(f"Posture analysis error: {e}")
        
        return result
    
    def _aggregate_posture_results(self, posture_scores: List[float], positions: List[Tuple]) -> Dict[str, Any]:
        """Aggregate posture analysis results."""
        if not posture_scores:
            return self._empty_posture_result()
        
        avg_score = np.mean(posture_scores)
        
        # Check for movement patterns (shifting position)
        if len(positions) > 1:
            position_changes = []
            for i in range(1, len(positions)):
                dx = abs(positions[i][0] - positions[i-1][0])
                dy = abs(positions[i][1] - positions[i-1][1])
                position_changes.append(dx + dy)
            
            avg_movement = np.mean(position_changes) if position_changes else 0
            
            if avg_movement > 50:  # Significant position shifting
                shifting = True
                avg_score -= 10
            else:
                shifting = False
        else:
            shifting = False
        
        return {
            "score": int(avg_score),
            "grade": self._score_to_grade(int(avg_score)),
            "position_stability": "stable" if not shifting else "shifting",
            "assessment": "Good professional posture" if avg_score >= 75 else "Posture could be improved",
            "notes": [
                "✓ Stable, centered positioning" if not shifting else "⚠️ Position shifting detected - try to stay centered"
            ]
        }
    
    # =========================================================================
    # CONFIDENCE FROM VISUAL CUES
    # =========================================================================
    
    def _assess_visual_confidence(
        self, 
        frame: np.ndarray, 
        eye_result: Dict, 
        posture_result: Dict,
        emotion_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Assess confidence from visual cues.
        Combines eye contact, posture, and emotions.
        """
        score = 50  # Base
        
        # Eye contact contribution (40%)
        if eye_result.get("looking_at_camera", False):
            score += 20
        if eye_result.get("confidence", 0) > 70:
            score += 10
        
        # Posture contribution (30%)
        score += (posture_result.get("score", 50) - 50) * 0.3
        
        # Emotion contribution (30%)
        if emotion_data:
            dominant = emotion_data.get("dominant_emotion", "neutral")
            if dominant in ["happy", "neutral"]:
                score += 15
            elif dominant in ["confident", "surprise"]:
                score += 10
            elif dominant in ["fear", "sad", "angry"]:
                score -= 10
        
        return {
            "score": min(100, max(0, int(score))),
            "contributing_factors": {
                "eye_contact": eye_result.get("looking_at_camera", False),
                "posture_score": posture_result.get("score", 50),
                "emotion": emotion_data.get("dominant_emotion", "unknown") if emotion_data else "unknown"
            }
        }
    
    def _aggregate_confidence_results(self, confidence_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate confidence analysis results."""
        if not confidence_results:
            return self._empty_confidence_result()
        
        scores = [r["score"] for r in confidence_results]
        avg_score = np.mean(scores)
        
        # Count consistent eye contact
        eye_contact_count = sum(1 for r in confidence_results if r["contributing_factors"].get("eye_contact", False))
        eye_contact_rate = (eye_contact_count / len(confidence_results)) * 100
        
        return {
            "score": int(avg_score),
            "grade": self._score_to_grade(int(avg_score)),
            "confidence_level": "High" if avg_score >= 80 else "Moderate" if avg_score >= 60 else "Low",
            "eye_contact_contribution": round(eye_contact_rate, 1),
            "assessment": "Appears confident and engaged" if avg_score >= 75 else "Could project more confidence",
            "notes": [
                "✓ Projects confidence through visual presence" if avg_score >= 75 else "⚠️ Work on projecting more confidence"
            ]
        }
    
    # =========================================================================
    # OVERALL SCORING
    # =========================================================================
    
    def _calculate_overall_visual_score(self, result: Dict) -> int:
        """Calculate overall visual behavior score."""
        weights = {
            "motion_analysis": 0.15,      # 15% - movement quality
            "eye_contact": 0.35,          # 35% - eye contact is crucial
            "posture_analysis": 0.20,     # 20% - professional posture
            "confidence_visual": 0.30     # 30% - overall confidence projection
        }
        
        total_score = 0
        for key, weight in weights.items():
            score = result.get(key, {}).get("score", 50)
            total_score += score * weight
        
        return int(total_score)
    
    def _score_to_grade(self, score: int) -> str:
        """Convert score to grade."""
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
    # EMPTY RESULTS
    # =========================================================================
    
    def _empty_motion_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "average_motion": 0,
            "motion_variance": 0,
            "motion_level": "unknown",
            "assessment": "Motion analysis unavailable",
            "fidgeting_detected": False,
            "notes": []
        }
    
    def _empty_eye_contact_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "eye_contact_rate": 0,
            "avg_confidence": 0,
            "dominant_gaze": "unknown",
            "assessment": "Eye contact analysis unavailable",
            "notes": []
        }
    
    def _empty_posture_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "position_stability": "unknown",
            "assessment": "Posture analysis unavailable",
            "notes": []
        }
    
    def _empty_confidence_result(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "grade": "N/A",
            "confidence_level": "unknown",
            "assessment": "Confidence analysis unavailable",
            "notes": []
        }
