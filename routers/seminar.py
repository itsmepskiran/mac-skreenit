"""
Seminar Router — Public Endpoints
==================================
Public listing, registration and Razorpay payment for seminars.
Admin CRUD endpoints live in routers/admin.py under /admin/seminars*.
"""

import uuid
import time
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import JSONResponse

from services.mysql_service import MySQLService
from services.payment_service import PaymentService
from utils_others.logger import logger

router = APIRouter(prefix="/seminars", tags=["Seminars"])
mysql_service = MySQLService()
payment_service = PaymentService()


def _fmt_seminar(s: dict) -> dict:
    """Prepare a seminar dict for public consumption."""
    topics = s.get("topics")
    if topics and isinstance(topics, str):
        try:
            topics = json.loads(topics)
        except Exception:
            topics = [t.strip() for t in topics.split(",") if t.strip()]
    return {
        "id":                   s.get("id"),
        "seminar_id":           s.get("seminar_id"),
        "title":                s.get("title"),
        "short_desc":           s.get("short_desc"),
        "description":          s.get("description"),
        "seminar_date":         str(s.get("seminar_date") or ""),
        "seminar_time":         s.get("seminar_time"),
        "end_time":             s.get("end_time"),
        "duration_label":       s.get("duration_label"),
        "mode":                 s.get("mode"),
        "venue":                s.get("venue"),
        "venue_address":        s.get("venue_address"),
        "city":                 s.get("city"),
        "meeting_link":         s.get("meeting_link"),
        "price_inr":            s.get("price_inr", 0),
        "early_bird_price":     s.get("early_bird_price"),
        "early_bird_deadline":  str(s.get("early_bird_deadline") or ""),
        "capacity":             s.get("capacity"),
        "enrolled_count":       s.get("enrolled_count", 0),
        "speaker_name":         s.get("speaker_name"),
        "speaker_bio":          s.get("speaker_bio"),
        "speaker_image_url":    s.get("speaker_image_url"),
        "topics":               topics or [],
        "image_url":            s.get("image_url"),
        "is_featured":          bool(s.get("is_featured")),
    }


# ============================================================
# PUBLIC: LIST & DETAIL
# ============================================================

@router.get("")
async def list_seminars(upcoming_only: bool = True):
    """List all active seminars; optionally filter to upcoming only."""
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        where = "is_active = 1"
        if upcoming_only:
            where += " AND seminar_date >= CURDATE()"
        rows = db.execute(text(f"""
            SELECT * FROM seminars WHERE {where}
            ORDER BY is_featured DESC, seminar_date ASC
        """)).fetchall()
        return {"ok": True, "data": [_fmt_seminar(dict(r._mapping)) for r in rows]}
    except Exception as e:
        logger.error(f"List seminars failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{seminar_id}")
async def get_seminar(seminar_id: str):
    """Get a single seminar by its friendly seminar_id."""
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        row = db.execute(text(
            "SELECT * FROM seminars WHERE (seminar_id = :sid OR id = :sid) AND is_active = 1"
        ), {"sid": seminar_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Seminar not found")
        return {"ok": True, "data": _fmt_seminar(dict(row._mapping))}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get seminar failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUBLIC: PAYMENT CONFIG
# ============================================================

@router.get("/config/payment")
async def get_payment_config():
    return {"ok": True, "data": payment_service.get_public_config("Skreenit Seminars")}


# ============================================================
# PUBLIC: REGISTER
# ============================================================

@router.post("/register")
async def register_seminar(body: dict = Body(...)):
    """
    Create a pending seminar registration.
    Call this before opening Razorpay checkout.
    Body: seminar_id, full_name, email, mobile, [company, designation, city]
    """
    try:
        seminar_id   = body.get("seminar_id", "").strip()
        full_name    = body.get("full_name", "").strip()
        email        = body.get("email", "").strip()
        mobile       = body.get("mobile", "").strip()
        company      = body.get("company", "").strip() or None
        designation  = body.get("designation", "").strip() or None
        city         = body.get("city", "").strip() or None

        if not all([seminar_id, full_name, email, mobile]):
            raise HTTPException(status_code=400, detail="seminar_id, full_name, email, mobile are required")

        seminar = mysql_service.get_single_record("seminars", {"seminar_id": seminar_id, "is_active": True})
        if not seminar:
            seminar = mysql_service.get_single_record("seminars", {"id": seminar_id, "is_active": True})
        if not seminar:
            raise HTTPException(status_code=404, detail="Seminar not found or inactive")

        # Capacity check
        if seminar.get("capacity"):
            if seminar.get("enrolled_count", 0) >= seminar["capacity"]:
                raise HTTPException(status_code=400, detail="This seminar has reached full capacity")

        # Effective price (early bird if applicable)
        price = seminar["price_inr"]
        eb_deadline = seminar.get("early_bird_deadline")
        eb_price    = seminar.get("early_bird_price")
        if eb_price is not None and eb_deadline:
            try:
                from datetime import date
                if isinstance(eb_deadline, str):
                    eb_deadline = date.fromisoformat(eb_deadline)
                if date.today() <= eb_deadline:
                    price = eb_price
            except Exception:
                pass

        registration_id = f"SEMREG{int(time.time() * 1000)}{str(uuid.uuid4())[:4].upper()}"
        reg_id = str(uuid.uuid4())

        mysql_service.insert_record("seminar_registrations", {
            "id":               reg_id,
            "registration_id":  registration_id,
            "seminar_id":       seminar["id"],
            "seminar_title":    seminar["title"],
            "full_name":        full_name,
            "email":            email,
            "mobile":           mobile,
            "company":          company,
            "designation":      designation,
            "city":             city,
            "amount":           price,
            "payment_status":   "pending",
            "status":           "pending",
            "created_at":       datetime.now(),
            "updated_at":       datetime.now(),
        })

        logger.info(f"Seminar registration created: {registration_id} for seminar {seminar['title']}")

        return {
            "ok": True,
            "data": {
                "registration_id": registration_id,
                "seminar_title":   seminar["title"],
                "seminar_date":    str(seminar.get("seminar_date") or ""),
                "amount":          price,
                "status":          "pending_payment",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seminar registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUBLIC: PAYMENT ORDER
# ============================================================

@router.post("/create-order")
async def create_seminar_order(body: dict = Body(...)):
    """Create a Razorpay order for a seminar registration."""
    try:
        registration_id = body.get("registration_id", "").strip()
        if not registration_id:
            raise HTTPException(status_code=400, detail="registration_id is required")

        reg = mysql_service.get_single_record("seminar_registrations", {"registration_id": registration_id})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        if reg.get("payment_status") == "completed":
            raise HTTPException(status_code=400, detail="Payment already completed")
        if reg.get("amount", 0) <= 0:
            raise HTTPException(status_code=400, detail="Cannot create order for free seminar")

        order = payment_service.create_order(
            amount_inr=reg["amount"],
            receipt=registration_id,
            notes={"registration_id": registration_id, "seminar_title": reg.get("seminar_title", "")},
        )

        mysql_service.update_record(
            "seminar_registrations",
            {"razorpay_order_id": order["id"], "updated_at": datetime.now()},
            {"registration_id": registration_id},
        )

        return {"ok": True, "data": {"order_id": order["id"], "amount": order["amount"], "currency": order["currency"]}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seminar order creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUBLIC: PAYMENT SUCCESS
# ============================================================

@router.post("/payment-success")
async def seminar_payment_success(body: dict = Body(...)):
    """Verify Razorpay payment and confirm seminar registration."""
    try:
        registration_id     = body.get("registration_id")
        razorpay_order_id   = body.get("razorpay_order_id")
        razorpay_payment_id = body.get("razorpay_payment_id")
        razorpay_signature  = body.get("razorpay_signature")

        if not all([registration_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            raise HTTPException(status_code=400, detail="Missing required payment fields")

        if not payment_service.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            raise HTTPException(status_code=400, detail="Payment signature verification failed")

        reg = mysql_service.get_single_record("seminar_registrations", {"registration_id": registration_id})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")

        mysql_service.update_record(
            "seminar_registrations",
            {
                "payment_status":   "completed",
                "payment_id":       razorpay_payment_id,
                "razorpay_order_id": razorpay_order_id,
                "payment_date":     datetime.now(),
                "status":           "confirmed",
                "updated_at":       datetime.now(),
            },
            {"registration_id": registration_id},
        )

        # Increment enrolled_count on the seminar
        try:
            from sqlalchemy import text as _text
            from database import get_db as _get_db
            _db = next(_get_db())
            _db.execute(_text("UPDATE seminars SET enrolled_count = enrolled_count + 1 WHERE id = :sid"), {"sid": reg["seminar_id"]})
            _db.commit()
        except Exception as e2:
            logger.warning(f"Failed to increment enrolled_count: {e2}")

        logger.info(f"Seminar payment confirmed: {registration_id}")
        return {"ok": True, "data": {"registration_id": registration_id, "status": "confirmed"}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seminar payment success failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUBLIC: WEBHOOK
# ============================================================

@router.post("/webhook")
async def seminar_webhook(request: Request):
    """Razorpay webhook for seminar payments."""
    try:
        raw_body  = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not payment_service.verify_webhook_signature(raw_body, signature):
            return JSONResponse(status_code=400, content={"error": "Invalid signature"})

        event = json.loads(raw_body)
        event_type = event.get("event")

        if event_type in ("payment.captured", "order.paid"):
            order_id   = event.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
            payment_id = event.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            if order_id:
                reg = mysql_service.get_single_record("seminar_registrations", {"razorpay_order_id": order_id})
                if reg and reg.get("payment_status") != "completed":
                    mysql_service.update_record(
                        "seminar_registrations",
                        {"payment_status": "completed", "payment_id": payment_id,
                         "payment_date": datetime.now(), "status": "confirmed", "updated_at": datetime.now()},
                        {"razorpay_order_id": order_id},
                    )
                    try:
                        mysql_service.execute_raw(
                            "UPDATE seminars SET enrolled_count = enrolled_count + 1 WHERE id = %s",
                            [reg["seminar_id"]],
                        )
                    except Exception:
                        pass

        elif event_type == "payment.failed":
            order_id = event.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
            if order_id:
                mysql_service.update_record(
                    "seminar_registrations",
                    {"payment_status": "failed", "updated_at": datetime.now()},
                    {"razorpay_order_id": order_id},
                )

        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as e:
        logger.error(f"Seminar webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": "Webhook processing failed"})


# ============================================================
# PUBLIC: GET REGISTRATION (for confirmation page)
# ============================================================

@router.get("/registration/{registration_id}")
async def get_registration(registration_id: str):
    """Get seminar registration details."""
    try:
        reg = mysql_service.get_single_record("seminar_registrations", {"registration_id": registration_id})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        seminar = mysql_service.get_single_record("seminars", {"id": reg.get("seminar_id")})
        return {
            "ok": True,
            "data": {
                "registration": reg,
                "seminar": _fmt_seminar(seminar) if seminar else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
