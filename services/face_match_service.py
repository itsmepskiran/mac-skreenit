"""
Face Matching Service using InsightFace
Compares faces between intro video and response videos to verify same candidate.
"""

import os
import cv2
import numpy as np
import traceback
from typing import Dict, Any, List, Optional, Tuple
from utils_others.logger import logger

# Lazy-loaded insightface model
_face_analyser = None

def _get_face_analyser():
    """Lazy load InsightFace model with robust path checking."""
    global _face_analyser
    if _face_analyser is None:
        try:
            from insightface.app import FaceAnalysis
            import onnxruntime as ort
            
            logger.info(f"ONNX Runtime version: {ort.__version__}")
            logger.info(f"ONNX Runtime providers: {ort.get_available_providers()}")
            
            # 1. Define and verify model paths
            model_root = os.path.expanduser("~/.insightface")
            model_dir = os.path.join(model_root, "models")
            
            logger.info(f"Checking model directory: {model_dir}")
            
            if os.path.exists(model_dir):
                files = os.listdir(model_dir)
                logger.info(f"Found files: {files}")
                # If det_10g.onnx is missing, the assertion will fail
                if not any(f.endswith('.onnx') for f in files):
                    logger.error("No .onnx files found in buffalo_m folder! Extraction failed.")
            else:
                logger.warning("buffalo_m directory does not exist yet.")

            logger.info("Initializing InsightFace buffalo_m model...")
            
            # 2. Initialize with explicit root if needed
            # Adding root=model_root helps on Windows if the library defaults to the wrong drive
            try:
                _face_analyser = FaceAnalysis(
                    name='buffalo_m', 
                    root=model_root, 
                    providers=['CPUExecutionProvider']
                )
                _face_analyser.prepare(ctx_id=0, det_size=(480, 480))
                logger.info("InsightFace buffalo_m model loaded successfully")
            except AssertionError as ae:
                logger.error(f"InsightFace Assertion Failed: {ae}. Likely missing det_10g.onnx.")
                _face_analyser = None
                raise
                
        except Exception as e:
            logger.error(f"Failed to load InsightFace model: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            _face_analyser = None
            raise
    return _face_analyser


class FaceMatchService:
    """
    Service for matching faces between videos.
    Uses InsightFace for face detection and recognition.
    """
    
    SIMILARITY_THRESHOLD = 0.7 
    
    def extract_face_embedding(self, image_path: str = None, frame: np.ndarray = None) -> Optional[np.ndarray]:
        try:
            analyser = _get_face_analyser()
            if analyser is None: return None

            if image_path and os.path.exists(image_path):
                frame = cv2.imread(image_path)
            
            if frame is None:
                return None
            
            faces = analyser.get(frame)
            
            if not faces:
                return None
            
            if len(faces) > 1:
                faces = sorted(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]), reverse=True)
            
            return faces[0].embedding
            
        except Exception as e:
            logger.error(f"Face embedding extraction failed: {e}")
            return None
    
    def extract_face_from_video(self, video_path: str, sample_frames: int = 5) -> Optional[np.ndarray]:
        try:
            if not os.path.exists(video_path): return None
            
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                cap.release()
                return None
            
            sample_indices = np.linspace(0, total_frames - 1, sample_frames, dtype=int)
            embeddings = []
            
            # Use the getter once to ensure model is ready
            _get_face_analyser()

            for idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret or frame is None: continue
                
                embedding = self.extract_face_embedding(frame=frame)
                if embedding is not None:
                    embeddings.append(embedding)
            
            cap.release()
            
            if not embeddings: return None
            
            avg_embedding = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(avg_embedding)
            if norm > 0:
                avg_embedding = avg_embedding / norm
            
            return avg_embedding
        except Exception as e:
            logger.error(f"Video face extraction failed: {e}")
            return None

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        try:
            norm1, norm2 = np.linalg.norm(embedding1), np.linalg.norm(embedding2)
            if norm1 == 0 or norm2 == 0: return 0.0
            
            similarity = np.dot(embedding1/norm1, embedding2/norm2)
            return float((similarity + 1) / 2)
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0

    def match_multiple_responses(self, intro_video_path: str, response_video_paths: List[str]) -> Dict[str, Any]:
        """
        Match intro video face against multiple response videos.
        
        Args:
            intro_video_path: Path to intro video
            response_video_paths: List of paths to response videos
            
        Returns:
            Dict with overall match result and per-video details
        """
        overall_result = {
            "overall_match": True,  # True if ALL responses match
            "match_count": 0,
            "mismatch_count": 0,
            "avg_similarity": 0.0,
            "details": [],
            "note": ""
        }
        
        try:
            # Extract intro embedding once
            intro_embedding = self.extract_face_from_video(intro_video_path)
            
            if intro_embedding is None:
                overall_result["overall_match"] = False
                overall_result["note"] = "No face detected in intro video"
                return overall_result
            
            similarities = []
            
            for idx, response_path in enumerate(response_video_paths):
                response_embedding = self.extract_face_from_video(response_path)
                
                detail = {
                    "video_index": idx,
                    "video_path": response_path,
                    "face_detected": response_embedding is not None,
                    "similarity": 0.0,
                    "match": False
                }
                
                if response_embedding is not None:
                    similarity = self.compute_similarity(intro_embedding, response_embedding)
                    detail["similarity"] = round(similarity * 100, 2)
                    detail["match"] = similarity >= self.SIMILARITY_THRESHOLD
                    similarities.append(similarity)
                    
                    if detail["match"]:
                        overall_result["match_count"] += 1
                    else:
                        overall_result["mismatch_count"] += 1
                        overall_result["overall_match"] = False
                else:
                    overall_result["mismatch_count"] += 1
                    overall_result["overall_match"] = False
                
                overall_result["details"].append(detail)
            
            if similarities:
                overall_result["avg_similarity"] = round(np.mean(similarities) * 100, 2)
            
            # Generate summary note
            if overall_result["overall_match"]:
                overall_result["note"] = f"All {overall_result['match_count']} response videos match intro video face"
            else:
                overall_result["note"] = f"Face mismatch: {overall_result['match_count']} matched, {overall_result['mismatch_count']} did not match"
            
            return overall_result
            
        except Exception as e:
            logger.error(f"Multiple response face matching failed: {e}")
            overall_result["note"] = f"Face matching error: {str(e)}"
            return overall_result
        pass

# Singleton instance
face_match_service = FaceMatchService()
