from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from services.video_service_mysql import VideoService
# ✅ FIX: Correct Import
from middleware.role_required import ensure_permission

router = APIRouter(prefix="/video", tags=["Video"])
svc = VideoService()


# ---------------------------------------------------------
# UPLOAD VIDEO (Candidate)
# ---------------------------------------------------------
@router.post("/upload")
async def upload_video(request: Request, file: UploadFile = File(...)):
    ensure_permission(request, "video:upload")

    try:
        content = await file.read()
        url = svc.upload_video_to_storage(
            content,
            file.filename,
            request.state.user["id"]
        )
        return {"ok": True, "data": {"video_url": url}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# UPLOAD GENERAL VIDEO (Candidate)
# ---------------------------------------------------------
@router.post("/general")
async def upload_general_video(request: Request, video: UploadFile = File(...)):
    ensure_permission(request, "video:upload")

    try:
        content = await video.read()
        url = svc.upload_video_to_storage(
            content,
            video.filename,
            request.state.user["id"]
        )
        return {"ok": True, "data": {"video_url": url}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# SAVE VIDEO RESPONSE (Per‑question)
# ---------------------------------------------------------
@router.post("/response")
async def save_video_response(request: Request, payload: dict):
    ensure_permission(request, "video:upload")

    try:
        saved = svc.save_video_response(
            **payload,
            candidate_id=request.state.user["id"]
        )
        return {"ok": True, "data": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# GET VIDEO RESPONSES FOR AN APPLICATION (Recruiter/Admin)
# ---------------------------------------------------------
@router.get("/application/{application_id}")
async def get_video_responses(request: Request, application_id: str):
    ensure_permission(request, "applications:view")

    try:
        responses = svc.list_video_responses(application_id)
        return {"ok": True, "data": responses}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))