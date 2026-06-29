"""
Admin Router — Pricing Management & Admin Auth
================================================
Endpoints:
  POST /admin/login         — Admin/Super Admin login (public)
  GET  /admin/pricing       — List all pricing plans (admin+)
  PUT  /admin/pricing/{id}  — Update a pricing plan (admin+)
  POST /admin/pricing       — Create a new pricing plan (super_admin only)
  PATCH /admin/pricing/{id}/toggle — Toggle is_active (super_admin only)
  GET  /admin/audit-log     — View price change audit log (admin+)
"""

import json
import uuid
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import JSONResponse

from services.mysql_service import MySQLService
from utils_others.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])
mysql_service = MySQLService()

ADMIN_ROLES = {"admin", "super_admin"}

JWT_SECRET    = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = 60 * 8  # 8-hour session for admin


# ============================================================
# ROLE GUARD HELPERS
# ============================================================

def require_admin(request: Request):
    """Raise 403 if the requester is not admin or super_admin."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_super_admin(request: Request):
    """Raise 403 if the requester is not super_admin."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return user


def _generate_admin_token(admin: dict) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": admin["id"],
        "email": admin["email"],
        "full_name": admin.get("full_name", ""),
        "role": admin["role"],
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _slugify(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "plan"


def _make_service_key(service_type: str, name: str) -> str:
    base = _slugify(f"{service_type} {name}")
    candidate = base[:100]

    # If this exact key already exists for the same service_type, add a timestamp suffix.
    existing = mysql_service.get_single_record("pricing_plans", {"service_type": service_type, "service_key": candidate})
    if not existing:
        return candidate

    suffix = int(datetime.utcnow().timestamp())
    return f"{candidate}_{suffix}"[:100]


# ============================================================
# AUTH — queries admin_users table, not main users table
# ============================================================

@router.post("/login")
async def admin_login(request: Request):
    """Login for Admin / Super Admin. Queries admin_users table only."""
    try:
        body = await request.json()
        email    = body.get("login_id", "").strip()
        password = body.get("password", "").strip()

        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")

        admin = mysql_service.get_single_record("admin_users", {"email": email})
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not admin.get("is_active", True):
            raise HTTPException(status_code=403, detail="This admin account is inactive")

        if not bcrypt.checkpw(password.encode("utf-8"), admin["password_hash"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = _generate_admin_token(admin)
        mysql_service.update_record("admin_users", {"last_login_at": datetime.now()}, {"id": admin["id"]})

        logger.info(f"Admin login: {email} ({admin['role']})")
        return {
            "ok": True,
            "data": {
                "access_token": token,
                "user": {
                    "id": admin["id"],
                    "email": admin["email"],
                    "full_name": admin.get("full_name"),
                    "role": admin["role"],
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        message = str(e)
        logger.error(f"Admin login error: {message}")

        if "Can't connect to MySQL server" in message or "Connection refused" in message or "timed out" in message.lower():
            raise HTTPException(status_code=503, detail="Database unavailable. Please try again in a moment.")

        raise HTTPException(status_code=500, detail="Login failed")


# ============================================================
# PRICING ENDPOINTS
# ============================================================

@router.get("/pricing")
async def list_pricing_plans(request: Request, service_type: str | None = None):
    """List all pricing plans. Optionally filter by service_type."""
    require_admin(request)
    try:
        filters = {}
        if service_type:
            filters["service_type"] = service_type
        records = mysql_service.get_records("pricing_plans", filters, order_by="service_type, sort_order")
        return {"ok": True, "data": records}
    except Exception as e:
        logger.error(f"Failed to list pricing plans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pricing/{plan_id}")
async def update_pricing_plan(request: Request, plan_id: str, body: dict = Body(...)):
    """Update a pricing plan. Admin and Super Admin can update."""
    user = require_admin(request)
    try:
        existing = mysql_service.get_single_record("pricing_plans", {"id": plan_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Pricing plan not found")

        allowed_fields = {
            "name", "description", "price_inr", "billing_cycle", "duration", "features", "sort_order",
            "assessment_format", "assessment_content", "icon_class", "icon_color", "icon_bg",
            "industry_key", "industry_label", "skills_measured",
        }
        update_payload = {k: v for k, v in body.items() if k in allowed_fields}

        if not update_payload:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_payload["updated_at"] = datetime.now()
        mysql_service.update_record("pricing_plans", update_payload, {"id": plan_id})

        # Write audit log
        _write_audit_log(
            user_id=user.get("sub"),
            user_email=user.get("email"),
            role=user.get("role"),
            action="update",
            plan_id=plan_id,
            service_key=existing.get("service_key"),
            old_values={k: existing.get(k) for k in update_payload if k != "updated_at"},
            new_values={k: update_payload[k] for k in update_payload if k != "updated_at"},
        )

        logger.info(f"Pricing plan updated: {plan_id} by {user.get('email')}")
        return {"ok": True, "data": {"message": "Pricing plan updated successfully", "plan_id": plan_id}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pricing plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pricing")
async def create_pricing_plan(request: Request, body: dict = Body(...)):
    """Create a new pricing plan. Super Admin only."""
    user = require_super_admin(request)
    try:
        required = {"service_type", "name", "price_inr"}
        missing = required - set(body.keys())
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

        service_type = str(body["service_type"]).strip()
        name = str(body["name"]).strip()
        raw_service_key = str(body.get("service_key", "") or "").strip()

        if not service_type or not name:
            raise HTTPException(status_code=400, detail="service_type and name are required")

        service_key = raw_service_key or _make_service_key(service_type, name)

        existing = mysql_service.get_single_record("pricing_plans", {"service_type": service_type, "service_key": service_key})
        if existing:
            raise HTTPException(status_code=409, detail="A pricing plan with this service_type and service_key already exists")

        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": plan_id,
            "service_type": service_type,
            "service_key": service_key,
            "name": name,
            "description": body.get("description", ""),
            "price_inr": int(body["price_inr"]),
            "currency": body.get("currency", "INR"),
            "billing_cycle": body.get("billing_cycle", "one_time"),
            "trial_days": int(body.get("trial_days", 0)),
            "duration": body.get("duration", ""),
            "features": body.get("features", "[]"),
            "is_active": body.get("is_active", True),
            "sort_order": int(body.get("sort_order", 0)),
            # Assessment display fields
            "assessment_format":  body.get("assessment_format") or None,
            "assessment_content": body.get("assessment_content") or None,
            "icon_class":         body.get("icon_class") or None,
            "icon_color":         body.get("icon_color") or None,
            "icon_bg":            body.get("icon_bg") or None,
            "industry_key":       body.get("industry_key") or None,
            "industry_label":     body.get("industry_label") or None,
            "skills_measured":    body.get("skills_measured") or None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mysql_service.insert_record("pricing_plans", payload)

        _write_audit_log(
            user_id=user.get("sub"),
            user_email=user.get("email"),
            role=user.get("role"),
            action="create",
            plan_id=plan_id,
            service_key=service_key,
            old_values={},
            new_values=payload,
        )

        logger.info(f"Pricing plan created: {plan_id} by {user.get('email')}")
        return {"ok": True, "data": {"message": "Pricing plan created", "plan_id": plan_id}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create pricing plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/pricing/{plan_id}/toggle")
async def toggle_pricing_plan(request: Request, plan_id: str):
    """Toggle is_active for a pricing plan. Super Admin only."""
    user = require_super_admin(request)
    try:
        existing = mysql_service.get_single_record("pricing_plans", {"id": plan_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Pricing plan not found")

        new_state = not bool(existing.get("is_active", True))
        mysql_service.update_record("pricing_plans", {"is_active": new_state, "updated_at": datetime.now()}, {"id": plan_id})

        _write_audit_log(
            user_id=user.get("sub"),
            user_email=user.get("email"),
            role=user.get("role"),
            action="toggle",
            plan_id=plan_id,
            service_key=existing.get("service_key"),
            old_values={"is_active": existing.get("is_active")},
            new_values={"is_active": new_state},
        )

        return {"ok": True, "data": {"plan_id": plan_id, "is_active": new_state}}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pricing/{plan_id}")
async def delete_pricing_plan(request: Request, plan_id: str):
    """Permanently delete a pricing plan. Super Admin only."""
    user = require_super_admin(request)
    try:
        existing = mysql_service.get_single_record("pricing_plans", {"id": plan_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Pricing plan not found")

        mysql_service.delete_record("pricing_plans", {"id": plan_id})

        _write_audit_log(
            user_id=user.get("sub"),
            user_email=user.get("email"),
            role=user.get("role"),
            action="delete",
            plan_id=plan_id,
            service_key=existing.get("service_key"),
            old_values={"name": existing.get("name"), "price_inr": existing.get("price_inr")},
            new_values={},
        )

        return {"ok": True, "data": {"plan_id": plan_id, "deleted": True}}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AUDIT LOG
# ============================================================

@router.get("/audit-log")
async def get_audit_log(request: Request, plan_id: str | None = None):
    """Get pricing change audit log. Admin and Super Admin."""
    require_admin(request)
    try:
        filters = {}
        if plan_id:
            filters["plan_id"] = plan_id
        records = mysql_service.get_records("pricing_audit_log", filters, order_by="created_at DESC")
        return {"ok": True, "data": records}
    except Exception as e:
        logger.error(f"Failed to fetch audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_stats(request: Request):
    """Aggregated revenue + activity stats for the admin dashboard."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())

        training = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN payment_status='completed' THEN 1 ELSE 0 END) AS paid,
                SUM(CASE WHEN payment_status='pending'   THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN payment_status='failed'    THEN 1 ELSE 0 END) AS failed,
                COALESCE(SUM(CASE WHEN payment_status='completed' THEN amount ELSE 0 END), 0) AS revenue,
                SUM(CASE WHEN registration_type='college'   THEN 1 ELSE 0 END) AS college_count,
                SUM(CASE WHEN registration_type='corporate' THEN 1 ELSE 0 END) AS corporate_count
            FROM training_registrations
        """)).fetchone()

        subs = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('active','trial') THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN status = 'cancelled'         THEN 1 ELSE 0 END) AS cancelled_count,
                COALESCE(SUM(amount_paid), 0) AS revenue
            FROM user_subscriptions
            WHERE status != 'pending'
        """)).fetchone()

        rev_by_type = db.execute(text("""
            SELECT pp.service_type,
                   COALESCE(SUM(us.amount_paid), 0) AS revenue,
                   COUNT(*) AS count
            FROM user_subscriptions us
            JOIN pricing_plans pp ON pp.id COLLATE utf8mb4_unicode_ci = us.plan_id COLLATE utf8mb4_unicode_ci
            WHERE us.status NOT IN ('pending','cancelled')
            GROUP BY pp.service_type
            ORDER BY revenue DESC
        """)).fetchall()

        train_by_course = db.execute(text("""
            SELECT training_course_name,
                   COUNT(*) AS count,
                   COALESCE(SUM(CASE WHEN payment_status='completed' THEN amount ELSE 0 END), 0) AS revenue
            FROM training_registrations
            GROUP BY training_course_name
            ORDER BY revenue DESC
            LIMIT 8
        """)).fetchall()

        recent_training = db.execute(text("""
            SELECT tr.registration_id, tr.registration_type, tr.training_course_name,
                   tr.payment_status, tr.amount, tr.created_at,
                   CASE
                       WHEN c.first_name IS NOT NULL
                       THEN CONCAT(c.first_name, ' ', COALESCE(c.last_name,''))
                       WHEN corp.contact_name IS NOT NULL THEN corp.contact_name
                       ELSE tr.registration_id
                   END AS name,
                   COALESCE(c.email, corp.contact_email, '') AS email
            FROM training_registrations tr
            LEFT JOIN college_training_registrations c    ON c.registration_id    = tr.registration_id
            LEFT JOIN corporate_training_registrations corp ON corp.registration_id = tr.registration_id
            ORDER BY tr.created_at DESC
            LIMIT 8
        """)).fetchall()

        recent_subs = db.execute(text("""
            SELECT us.id, us.status, us.amount_paid, us.created_at, us.expiry_date,
                   pp.name AS plan_name, pp.service_type,
                   COALESCE(u.full_name, u.email, 'Unknown') AS user_name,
                   u.email
            FROM user_subscriptions us
            JOIN pricing_plans pp ON pp.id COLLATE utf8mb4_unicode_ci = us.plan_id COLLATE utf8mb4_unicode_ci
            LEFT JOIN users u ON u.id COLLATE utf8mb4_unicode_ci = us.user_id COLLATE utf8mb4_unicode_ci
            WHERE us.status != 'pending'
            ORDER BY us.created_at DESC
            LIMIT 8
        """)).fetchall()

        def row_to_dict(row):
            return dict(row._mapping) if row else {}

        total_revenue = float(training.revenue or 0) + float(subs.revenue or 0)

        # Seminar stats (table may not exist yet; safe fallback)
        sem_revenue = 0.0
        sem_total = sem_paid = sem_upcoming = 0
        recent_sem_regs = []
        try:
            sem_stats = db.execute(text("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN payment_status='completed' THEN 1 ELSE 0 END) AS paid,
                    COALESCE(SUM(CASE WHEN payment_status='completed' THEN amount ELSE 0 END), 0) AS revenue
                FROM seminar_registrations
            """)).fetchone()
            sem_upcoming_row = db.execute(text(
                "SELECT COUNT(*) AS cnt FROM seminars WHERE is_active=1 AND seminar_date >= CURDATE()"
            )).fetchone()
            sem_total    = int(sem_stats.total or 0)
            sem_paid     = int(sem_stats.paid or 0)
            sem_revenue  = float(sem_stats.revenue or 0)
            sem_upcoming = int(sem_upcoming_row.cnt or 0) if sem_upcoming_row else 0

            recent_sem_rows = db.execute(text("""
                SELECT sr.registration_id, sr.full_name, sr.email, sr.seminar_title,
                       sr.amount, sr.payment_status, sr.created_at
                FROM seminar_registrations sr
                ORDER BY sr.created_at DESC
                LIMIT 8
            """)).fetchall()
            recent_sem_regs = [row_to_dict(r) for r in recent_sem_rows]
        except Exception as sem_err:
            logger.warning(f"Seminar stats unavailable (table may not exist): {sem_err}")

        total_revenue = float(training.revenue or 0) + float(subs.revenue or 0) + sem_revenue

        return {
            "ok": True,
            "data": {
                "total_revenue": total_revenue,
                "training": {
                    "total": int(training.total or 0),
                    "paid": int(training.paid or 0),
                    "pending": int(training.pending or 0),
                    "failed": int(training.failed or 0),
                    "revenue": float(training.revenue or 0),
                    "college_count": int(training.college_count or 0),
                    "corporate_count": int(training.corporate_count or 0),
                },
                "subscriptions": {
                    "total": int(subs.total or 0),
                    "active": int(subs.active_count or 0),
                    "cancelled": int(subs.cancelled_count or 0),
                    "revenue": float(subs.revenue or 0),
                },
                "seminars": {
                    "total_registrations": sem_total,
                    "paid_registrations":  sem_paid,
                    "upcoming_count":      sem_upcoming,
                    "revenue":             sem_revenue,
                },
                "revenue_by_type": [row_to_dict(r) for r in rev_by_type],
                "training_by_course": [row_to_dict(r) for r in train_by_course],
                "recent_training": [row_to_dict(r) for r in recent_training],
                "recent_subscriptions": [row_to_dict(r) for r in recent_subs],
                "recent_seminar_registrations": recent_sem_regs,
            },
        }
    except Exception as e:
        logger.error(f"Dashboard stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-registrations")
async def list_training_registrations(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    reg_type: str | None = None,
    payment_status: str | None = None,
    q: str | None = None,
):
    """List all training registrations with contact details. Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        offset = (page - 1) * page_size

        where_clauses = ["1=1"]
        params: dict = {"limit": page_size, "offset": offset}

        if reg_type:
            where_clauses.append("tr.registration_type = :reg_type")
            params["reg_type"] = reg_type
        if payment_status:
            where_clauses.append("tr.payment_status = :payment_status")
            params["payment_status"] = payment_status
        if q:
            where_clauses.append(
                "(tr.registration_id LIKE :q OR tr.training_course_name LIKE :q "
                "OR c.first_name LIKE :q OR c.last_name LIKE :q OR c.email LIKE :q "
                "OR corp.contact_name LIKE :q OR corp.company_name LIKE :q OR corp.contact_email LIKE :q)"
            )
            params["q"] = f"%{q}%"

        where_str = " AND ".join(where_clauses)

        rows = db.execute(text(f"""
            SELECT tr.registration_id, tr.registration_type, tr.training_course,
                   tr.training_course_name, tr.payment_status, tr.status,
                   tr.amount, tr.payment_id, tr.created_at, tr.payment_date,
                   CASE
                       WHEN c.first_name IS NOT NULL
                       THEN CONCAT(c.first_name, ' ', COALESCE(c.last_name,''))
                       WHEN corp.contact_name IS NOT NULL THEN corp.contact_name
                       ELSE tr.registration_id
                   END AS name,
                   COALESCE(c.email, corp.contact_email, '') AS email,
                   COALESCE(c.mobile, corp.contact_mobile, '') AS mobile,
                   COALESCE(c.college_name, corp.company_name, '') AS org_name,
                   COALESCE(c.batch_timing, '') AS batch_timing
            FROM training_registrations tr
            LEFT JOIN college_training_registrations c    ON c.registration_id    = tr.registration_id
            LEFT JOIN corporate_training_registrations corp ON corp.registration_id = tr.registration_id
            WHERE {where_str}
            ORDER BY tr.created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total_row = db.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM training_registrations tr
            LEFT JOIN college_training_registrations c    ON c.registration_id    = tr.registration_id
            LEFT JOIN corporate_training_registrations corp ON corp.registration_id = tr.registration_id
            WHERE {where_str}
        """), count_params).fetchone()

        return {
            "ok": True,
            "data": [dict(r._mapping) for r in rows],
            "total": int(total_row.total) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"List training registrations failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions")
async def list_subscriptions_admin(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    service_type: str | None = None,
    q: str | None = None,
):
    """List all user subscriptions with plan and user details. Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        offset = (page - 1) * page_size

        where_clauses = ["us.status != 'pending'"]
        params: dict = {"limit": page_size, "offset": offset}

        if status:
            where_clauses.append("us.status = :status")
            params["status"] = status
        if service_type:
            where_clauses.append("pp.service_type = :service_type")
            params["service_type"] = service_type
        if q:
            where_clauses.append(
                "(u.email LIKE :q OR u.full_name LIKE :q OR pp.name LIKE :q OR us.transaction_id LIKE :q)"
            )
            params["q"] = f"%{q}%"

        where_str = " AND ".join(where_clauses)

        rows = db.execute(text(f"""
            SELECT us.id, us.status, us.amount_paid, us.transaction_id,
                   us.start_date, us.expiry_date, us.created_at,
                   pp.name AS plan_name, pp.service_type, pp.billing_cycle,
                   COALESCE(u.full_name, u.email, 'Unknown') AS user_name,
                   u.email
            FROM user_subscriptions us
            JOIN pricing_plans pp ON pp.id COLLATE utf8mb4_unicode_ci = us.plan_id COLLATE utf8mb4_unicode_ci
            LEFT JOIN users u ON u.id COLLATE utf8mb4_unicode_ci = us.user_id COLLATE utf8mb4_unicode_ci
            WHERE {where_str}
            ORDER BY us.created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total_row = db.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM user_subscriptions us
            JOIN pricing_plans pp ON pp.id COLLATE utf8mb4_unicode_ci = us.plan_id COLLATE utf8mb4_unicode_ci
            LEFT JOIN users u ON u.id COLLATE utf8mb4_unicode_ci = us.user_id COLLATE utf8mb4_unicode_ci
            WHERE {where_str}
        """), count_params).fetchone()

        return {
            "ok": True,
            "data": [dict(r._mapping) for r in rows],
            "total": int(total_row.total) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"List subscriptions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SEMINAR ENQUIRIES
# ============================================================

@router.post("/seminar-enquiry")
async def submit_seminar_enquiry(request: Request):
    """Public endpoint — captures contact interest from the seminars page."""
    try:
        body = await request.json()
        full_name = (body.get("full_name") or "").strip()
        email     = (body.get("email")     or "").strip()
        mobile    = (body.get("mobile")    or "").strip()

        if not full_name or not email or not mobile:
            raise HTTPException(status_code=400, detail="full_name, email, and mobile are required")

        from sqlalchemy import text as _text
        from database import get_db as _get_db
        enquiry_id = "ENQ-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
        now = datetime.now()
        _db = next(_get_db())
        _db.execute(_text("""
            INSERT INTO seminar_enquiries (id, enquiry_id, full_name, email, mobile, company, message, status, source, created_at, updated_at)
            VALUES (:id, :enquiry_id, :full_name, :email, :mobile, :company, :message, 'new', :source, :created_at, :updated_at)
        """), {
            "id":         str(uuid.uuid4()),
            "enquiry_id": enquiry_id,
            "full_name":  full_name,
            "email":      email,
            "mobile":     mobile,
            "company":    (body.get("company") or "").strip() or None,
            "message":    (body.get("message") or "").strip() or None,
            "source":     body.get("source") or "seminars_page",
            "created_at": now,
            "updated_at": now,
        })
        _db.commit()
        logger.info(f"Seminar enquiry submitted: {enquiry_id} from {email}")
        return {"ok": True, "data": {"enquiry_id": enquiry_id, "message": "Enquiry received. We'll be in touch soon."}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Seminar enquiry submission failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not save enquiry. Please try again.")


@router.get("/seminar-enquiries")
async def list_seminar_enquiries(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    q: str | None = None,
):
    """List all seminar enquiries. Admin and Super Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db     = next(get_db())
        offset = (page - 1) * page_size

        where_clauses = ["1=1"]
        params: dict  = {"limit": page_size, "offset": offset}

        if status:
            where_clauses.append("status = :status")
            params["status"] = status
        if q:
            where_clauses.append(
                "(full_name LIKE :q OR email LIKE :q OR mobile LIKE :q "
                "OR company LIKE :q OR enquiry_id LIKE :q)"
            )
            params["q"] = f"%{q}%"

        where_str = " AND ".join(where_clauses)

        rows = db.execute(text(f"""
            SELECT id, enquiry_id, full_name, email, mobile, company,
                   message, status, source, notes, created_at, updated_at
            FROM seminar_enquiries
            WHERE {where_str}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total_row = db.execute(text(f"""
            SELECT COUNT(*) AS total FROM seminar_enquiries WHERE {where_str}
        """), count_params).fetchone()

        return {
            "ok":        True,
            "data":      [dict(r._mapping) for r in rows],
            "total":     int(total_row.total) if total_row else 0,
            "page":      page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"List seminar enquiries failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/seminar-enquiries/{enquiry_id}/status")
async def update_seminar_enquiry_status(request: Request, enquiry_id: str):
    """Update status or notes for a seminar enquiry. Admin and Super Admin only."""
    require_admin(request)
    try:
        body       = await request.json()
        new_status = body.get("status")
        new_notes  = body.get("notes")

        allowed_statuses = {"new", "contacted", "enrolled", "closed"}
        if new_status and new_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"status must be one of {allowed_statuses}")

        from sqlalchemy import text as _text
        from database import get_db as _get_db
        _db  = next(_get_db())
        row  = _db.execute(_text("SELECT id FROM seminar_enquiries WHERE id = :id"), {"id": enquiry_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Enquiry not found")

        set_parts = ["updated_at = :updated_at"]
        params    = {"updated_at": datetime.now(), "id": enquiry_id}
        if new_status:
            set_parts.append("status = :status")
            params["status"] = new_status
        if new_notes is not None:
            set_parts.append("notes = :notes")
            params["notes"] = new_notes

        _db.execute(_text(f"UPDATE seminar_enquiries SET {', '.join(set_parts)} WHERE id = :id"), params)
        _db.commit()
        return {"ok": True, "data": {"id": enquiry_id, "updated": True}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update seminar enquiry failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SEMINAR CRUD (admin manages seminars)
# ============================================================

@router.get("/seminars")
async def list_admin_seminars(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    q: str | None = None,
    is_active: str | None = None,
):
    """List all seminars (active + inactive). Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params: dict = {"limit": page_size, "offset": offset}
        if is_active is not None:
            where_clauses.append("is_active = :is_active")
            params["is_active"] = 1 if is_active == "1" else 0
        if q:
            where_clauses.append("(title LIKE :q OR speaker_name LIKE :q OR city LIKE :q OR seminar_id LIKE :q)")
            params["q"] = f"%{q}%"
        where_str = " AND ".join(where_clauses)
        rows = db.execute(text(f"""
            SELECT s.*,
                   (SELECT COUNT(*) FROM seminar_registrations r
                    WHERE r.seminar_id = s.id AND r.payment_status = 'completed') AS paid_count
            FROM seminars s
            WHERE {where_str}
            ORDER BY s.seminar_date DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        total_row = db.execute(text(
            f"SELECT COUNT(*) AS total FROM seminars WHERE {where_str}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")}
        ).fetchone()
        return {
            "ok": True,
            "data": [dict(r._mapping) for r in rows],
            "total": int(total_row.total) if total_row else 0,
            "page": page, "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"List admin seminars failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seminars")
async def create_admin_seminar(request: Request, body: dict = Body(...)):
    """Create a new seminar. Admin only."""
    require_admin(request)
    import json as _json
    from sqlalchemy import text
    from database import get_db
    try:
        title        = (body.get("title") or "").strip()
        seminar_date = body.get("seminar_date")
        if not title or not seminar_date:
            raise HTTPException(status_code=400, detail="title and seminar_date are required")

        seminar_id = "SEM-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:4].upper()
        topics = body.get("topics")
        if isinstance(topics, list):
            topics = _json.dumps(topics)
        elif isinstance(topics, str) and topics:
            try:
                _json.loads(topics)
            except Exception:
                topics = _json.dumps([t.strip() for t in topics.split(",") if t.strip()])

        new_id = str(uuid.uuid4())
        now    = datetime.now()
        db     = next(get_db())
        db.execute(text("""
            INSERT INTO seminars (
                id, seminar_id, title, short_desc, description,
                seminar_date, seminar_time, end_time, duration_label,
                mode, venue, venue_address, city, meeting_link,
                price_inr, early_bird_price, early_bird_deadline,
                capacity, enrolled_count,
                speaker_name, speaker_bio, speaker_image_url,
                topics, image_url, is_active, is_featured,
                created_at, updated_at
            ) VALUES (
                :id, :seminar_id, :title, :short_desc, :description,
                :seminar_date, :seminar_time, :end_time, :duration_label,
                :mode, :venue, :venue_address, :city, :meeting_link,
                :price_inr, :early_bird_price, :early_bird_deadline,
                :capacity, 0,
                :speaker_name, :speaker_bio, :speaker_image_url,
                :topics, :image_url, :is_active, :is_featured,
                :created_at, :updated_at
            )
        """), {
            "id":                 new_id,
            "seminar_id":         seminar_id,
            "title":              title,
            "short_desc":         (body.get("short_desc") or "").strip() or None,
            "description":        (body.get("description") or "").strip() or None,
            "seminar_date":       seminar_date,
            "seminar_time":       (body.get("seminar_time") or "10:00 AM").strip(),
            "end_time":           (body.get("end_time") or "").strip() or None,
            "duration_label":     (body.get("duration_label") or "").strip() or None,
            "mode":               body.get("mode") or "offline",
            "venue":              (body.get("venue") or "").strip() or None,
            "venue_address":      (body.get("venue_address") or "").strip() or None,
            "city":               (body.get("city") or "").strip() or None,
            "meeting_link":       (body.get("meeting_link") or "").strip() or None,
            "price_inr":          int(body.get("price_inr") or 0),
            "early_bird_price":   int(body.get("early_bird_price")) if body.get("early_bird_price") else None,
            "early_bird_deadline": body.get("early_bird_deadline") or None,
            "capacity":           int(body.get("capacity")) if body.get("capacity") else None,
            "speaker_name":       (body.get("speaker_name") or "").strip() or None,
            "speaker_bio":        (body.get("speaker_bio") or "").strip() or None,
            "speaker_image_url":  (body.get("speaker_image_url") or "").strip() or None,
            "topics":             topics or None,
            "image_url":          (body.get("image_url") or "").strip() or None,
            "is_active":          1 if body.get("is_active", True) else 0,
            "is_featured":        1 if body.get("is_featured", False) else 0,
            "created_at":         now,
            "updated_at":         now,
        })
        db.commit()
        logger.info(f"Seminar created: {seminar_id} — {title}")
        return {"ok": True, "data": {"seminar_id": seminar_id, "id": new_id, "title": title}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create seminar failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/seminars/{seminar_id}")
async def update_admin_seminar(request: Request, seminar_id: str, body: dict = Body(...)):
    """Update a seminar by its UUID id. Admin only."""
    require_admin(request)
    import json as _json
    from sqlalchemy import text
    from database import get_db
    try:
        db  = next(get_db())
        row = db.execute(text("SELECT id FROM seminars WHERE id = :id"), {"id": seminar_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Seminar not found")

        allowed = {
            "title", "short_desc", "description", "seminar_date", "seminar_time", "end_time",
            "duration_label", "mode", "venue", "venue_address", "city", "meeting_link",
            "price_inr", "early_bird_price", "early_bird_deadline", "capacity",
            "speaker_name", "speaker_bio", "speaker_image_url", "topics", "image_url",
            "is_active", "is_featured",
        }
        payload = {k: v for k, v in body.items() if k in allowed}
        if "topics" in payload and isinstance(payload["topics"], list):
            payload["topics"] = _json.dumps(payload["topics"])
        if "price_inr" in payload:
            payload["price_inr"] = int(payload["price_inr"] or 0)

        set_parts = ", ".join(f"{k} = :{k}" for k in payload)
        payload["updated_at"] = datetime.now()
        payload["_id"] = seminar_id
        db.execute(text(f"UPDATE seminars SET {set_parts}, updated_at = :updated_at WHERE id = :_id"), payload)
        db.commit()
        return {"ok": True, "data": {"id": seminar_id, "updated": True}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update seminar failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/seminars/{seminar_id}/toggle")
async def toggle_admin_seminar(request: Request, seminar_id: str):
    """Toggle is_active for a seminar. Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db  = next(get_db())
        row = db.execute(text("SELECT id, is_active FROM seminars WHERE id = :id"), {"id": seminar_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Seminar not found")
        new_state = 0 if row.is_active else 1
        db.execute(text(
            "UPDATE seminars SET is_active = :s, updated_at = :now WHERE id = :id"
        ), {"s": new_state, "now": datetime.now(), "id": seminar_id})
        db.commit()
        return {"ok": True, "data": {"id": seminar_id, "is_active": bool(new_state)}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/seminars/{seminar_id}")
async def delete_admin_seminar(request: Request, seminar_id: str):
    """Delete a seminar (only if no confirmed registrations). Super Admin only."""
    require_super_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db  = next(get_db())
        row = db.execute(text("SELECT id FROM seminars WHERE id = :id"), {"id": seminar_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Seminar not found")
        confirmed = db.execute(text(
            "SELECT COUNT(*) AS cnt FROM seminar_registrations WHERE seminar_id = :id AND status = 'confirmed'"
        ), {"id": seminar_id}).fetchone()
        if confirmed and confirmed.cnt > 0:
            raise HTTPException(status_code=400, detail=f"Cannot delete: {confirmed.cnt} confirmed registrations exist. Deactivate instead.")
        db.execute(text("DELETE FROM seminar_registrations WHERE seminar_id = :id"), {"id": seminar_id})
        db.execute(text("DELETE FROM seminars WHERE id = :id"), {"id": seminar_id})
        db.commit()
        return {"ok": True, "data": {"id": seminar_id, "deleted": True}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete seminar failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seminar-registrations")
async def list_seminar_registrations(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    seminar_id: str | None = None,
    payment_status: str | None = None,
    q: str | None = None,
):
    """List all seminar registrations. Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db = next(get_db())
        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params: dict = {"limit": page_size, "offset": offset}
        if seminar_id:
            where_clauses.append("sr.seminar_id = :seminar_id")
            params["seminar_id"] = seminar_id
        if payment_status:
            where_clauses.append("sr.payment_status = :payment_status")
            params["payment_status"] = payment_status
        if q:
            where_clauses.append(
                "(sr.full_name LIKE :q OR sr.email LIKE :q OR sr.mobile LIKE :q "
                "OR sr.company LIKE :q OR sr.registration_id LIKE :q OR sr.seminar_title LIKE :q)"
            )
            params["q"] = f"%{q}%"
        where_str = " AND ".join(where_clauses)
        rows = db.execute(text(f"""
            SELECT sr.registration_id, sr.full_name, sr.email, sr.mobile,
                   sr.company, sr.designation, sr.city,
                   sr.seminar_title, sr.amount, sr.payment_status,
                   sr.payment_id, sr.status, sr.attendance_marked,
                   sr.created_at, sr.payment_date,
                   s.seminar_date, s.seminar_time, s.mode, s.city AS seminar_city,
                   sr.seminar_id
            FROM seminar_registrations sr
            LEFT JOIN seminars s ON s.id = sr.seminar_id
            WHERE {where_str}
            ORDER BY sr.created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total_row = db.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM seminar_registrations sr
            WHERE {where_str}
        """), count_params).fetchone()
        return {
            "ok": True,
            "data": [dict(r._mapping) for r in rows],
            "total": int(total_row.total) if total_row else 0,
            "page": page, "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"List seminar registrations failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/seminar-registrations/{registration_id}/attendance")
async def mark_seminar_attendance(request: Request, registration_id: str):
    """Toggle attendance_marked for a seminar registration. Admin only."""
    require_admin(request)
    from sqlalchemy import text
    from database import get_db
    try:
        db  = next(get_db())
        row = db.execute(text(
            "SELECT attendance_marked FROM seminar_registrations WHERE registration_id = :rid"
        ), {"rid": registration_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registration not found")
        new_val = 0 if row.attendance_marked else 1
        db.execute(text(
            "UPDATE seminar_registrations SET attendance_marked = :v, updated_at = :now WHERE registration_id = :rid"
        ), {"v": new_val, "now": datetime.now(), "rid": registration_id})
        db.commit()
        return {"ok": True, "data": {"registration_id": registration_id, "attendance_marked": bool(new_val)}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _write_audit_log(user_id, user_email, role, action, plan_id, service_key, old_values, new_values):
    """Write an entry to the pricing_audit_log table."""
    try:
        mysql_service.insert_record("pricing_audit_log", {
            "id": str(uuid.uuid4()),
            "plan_id": plan_id,
            "service_key": service_key,
            "action": action,
            "changed_by_user_id": user_id,
            "changed_by_email": user_email,
            "changed_by_role": role,
            "old_values": json.dumps(old_values),
            "new_values": json.dumps(new_values),
            "created_at": datetime.now(),
        })
    except Exception as e:
        logger.warning(f"Audit log write failed (non-critical): {str(e)}")
