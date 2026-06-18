"""JD ↔ Candidate Matching Service using Ollama LLM models."""

import json as json_lib, re
from typing import Dict, Any, List
from database import get_db, Job, JobApplication, User, CandidateProfile
from services.ollama_service import ollama_service
from utils_others.logger import logger


def _parse_json(raw: str) -> Dict[str, Any]:
    if not raw: return {}
    try: return json_lib.loads(raw)
    except json_lib.JSONDecodeError: pass
    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        try: return json_lib.loads(m.group())
        except json_lib.JSONDecodeError: pass
    return {"raw_response": raw}


def _jd_text(job) -> str:
    return f"Title: {job.job_title}\nDept: {job.department or 'N/A'}\nDesc: {job.description}\nReqs: {job.requirements or 'N/A'}\nSkills: {job.skills or 'N/A'}\nExp: {job.experience_min or 0}-{job.experience_max or 0}yrs"


def _resume_text(cand, prof) -> str:
    parts = []
    if cand.full_name: parts.append(f"Name: {cand.full_name}")
    if prof and prof.skills: parts.append(f"Skills: {prof.skills}")
    if prof and prof.experience: parts.append(f"Experience: {prof.experience}")
    if prof and prof.education: parts.append(f"Education: {prof.education}")
    if prof and prof.summary: parts.append(f"Summary: {prof.summary}")
    return "\n".join(parts) or f"Name: {cand.full_name}, Email: {cand.email}"


class JDMatchingService:

    def get_top_candidates_for_job(self, job_id: str, top_n: int = 10) -> Dict[str, Any]:
        db = next(get_db())
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job: return {"error": "Job not found"}
            apps = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()
            if not apps: return {"job_id": job_id, "job_title": job.job_title, "candidates": [], "message": "No applications"}

            cands = []
            for app in apps:
                c = db.query(User).filter(User.id == app.candidate_id).first()
                if not c: continue
                p = db.query(CandidateProfile).filter(CandidateProfile.user_id == app.candidate_id).first()
                cands.append({"name": c.full_name or "Unknown", "candidate_id": app.candidate_id, "resume_text": _resume_text(c, p)})

            if not cands: return {"job_id": job_id, "job_title": job.job_title, "candidates": [], "message": "No candidate data"}

            ai = ollama_service.batch_score_candidates(cands, _jd_text(job), job.job_title)
            ranked = _parse_json(ai).get("ranked_candidates", []) if ai else []
            for rc in ranked:
                for c in cands:
                    if c["name"] == rc.get("candidate_name", ""):
                        ap = db.query(JobApplication).filter(JobApplication.candidate_id == c["candidate_id"], JobApplication.job_id == job_id).first()
                        if ap: ap.ai_score = rc.get("match_score", 0); db.commit()
                        break
            ranked.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return {"job_id": job_id, "job_title": job.job_title, "total_applicants": len(cands), "top_candidates": ranked[:top_n]}
        except Exception as e:
            logger.error(f"get_top_candidates failed: {e}")
            return {"error": str(e)}
        finally: db.close()

    def find_matching_jobs_for_resume(self, resume_text: str, user_id: str = "", top_n: int = 10) -> Dict[str, Any]:
        db = next(get_db())
        try:
            jobs = db.query(Job).filter(Job.status == "active").all()
            if not jobs: return {"candidate_id": user_id, "matched_jobs": [], "message": "No active jobs"}
            jobs_list = [{"id": j.id, "title": j.job_title, "description": _jd_text(j)} for j in jobs]
            ai = ollama_service.find_matching_jobs(resume_text, jobs_list)
            matched = _parse_json(ai).get("matched_jobs", []) if ai else []
            matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return {"candidate_id": user_id, "total_jobs": len(jobs), "matched_jobs": matched[:top_n]}
        except Exception as e:
            logger.error(f"find_matching_jobs failed: {e}")
            return {"error": str(e)}
        finally: db.close()

    def score_single_application(self, application_id: str) -> Dict[str, Any]:
        db = next(get_db())
        try:
            app = db.query(JobApplication).filter(JobApplication.id == application_id).first()
            if not app: return {"error": "Application not found"}
            job = db.query(Job).filter(Job.id == app.job_id).first()
            cand = db.query(User).filter(User.id == app.candidate_id).first()
            if not job or not cand: return {"error": "Job or candidate not found"}
            prof = db.query(CandidateProfile).filter(CandidateProfile.user_id == app.candidate_id).first()
            resume = _resume_text(cand, prof)
            ai = ollama_service.score_resume_vs_jd(resume, _jd_text(job), job.job_title)
            parsed = _parse_json(ai) if ai else {}
            if parsed.get("match_score"):
                app.ai_score = parsed["match_score"]; db.commit()
            return {"application_id": application_id, "job_title": job.job_title, "candidate": cand.full_name, "score": parsed}
        except Exception as e:
            logger.error(f"score_single failed: {e}")
            return {"error": str(e)}
        finally: db.close()


jd_matching_service = JDMatchingService()
