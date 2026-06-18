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
