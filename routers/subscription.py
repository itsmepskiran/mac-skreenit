"""
Subscription Router
Handles subscription creation, order initialization, and pricing plan queries for applicants
"""

from fastapi import APIRouter, Request, HTTPException, Body, Depends
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import uuid
import json

from services.mysql_service import MySQLService
from services.subscription_service import SubscriptionService
from services.payment_service import PaymentService
from database import get_db
from sqlalchemy.orm import Session
from pydantic import BaseModel

logger = logging.getLogger(__name__)

mysql_service = MySQLService()
payment_service = PaymentService()
router = APIRouter(prefix="/subscription", tags=["Subscription"])

# Pydantic schemas for data validation
class OrderCreateSchema(BaseModel):
    amount: int
    currency: str = "INR"
    subscription_id: str
    service_type: str


# ============================================================
# PUBLIC PRICING ENDPOINTS (No Authentication Required)
# ============================================================

@router.get("/pricing/plans")
async def list_public_pricing_plans(request: Request, service_type: str | None = None):
    """
    List active pricing plans for public access.
    Optionally filter by service_type (e.g., 'applicant_plan', 'training').
    This endpoint does not require authentication.
    """
    try:
        filters = {"is_active": True}
        if service_type:
            filters["service_type"] = service_type

        records = mysql_service.get_records("pricing_plans", filters, order_by="sort_order, price_inr")

        public_records = []
        for record in records:
            public_records.append({
                "id": record.get("id"),
                "service_type": record.get("service_type"),
                "service_key": record.get("service_key"),
                "name": record.get("name"),
                "description": record.get("description"),
                "price_inr": record.get("price_inr"),
                "currency": record.get("currency"),
                "billing_cycle": record.get("billing_cycle"),
                "trial_days": record.get("trial_days"),
                "duration": record.get("duration"),
                "features": record.get("features"),
                "sort_order": record.get("sort_order"),
                # Assessment display fields (populated via admin UI or migration)
                "assessment_format": record.get("assessment_format"),
                "icon_class":        record.get("icon_class"),
                "icon_color":        record.get("icon_color"),
                "icon_bg":           record.get("icon_bg"),
                "industry_key":      record.get("industry_key"),
                "industry_label":    record.get("industry_label"),
                "skills_measured":   record.get("skills_measured"),
            })

        if not public_records and service_type == "applicant_plan":
            logger.warning("No applicant plans found in pricing_plans table, using fallback")
            public_records = [{
                "id": "plan_applicant_premium_monthly",
                "service_type": "applicant_plan",
                "service_key": "applicant_premium",
                "name": "Premium Applicant Access",
                "description": "Access to Versant, General Assessment, and all premium features",
                "price_inr": 299,
                "currency": "INR",
                "billing_cycle": "monthly",
                "trial_days": 7,
                "duration": "1 Month",
                "features": '["versant_assessment", "general_assessment", "interview_prep", "typing_test"]',
                "sort_order": 2
            }]

        return {"ok": True, "data": public_records}
    except Exception as e:
        logger.error(f"Failed to list public pricing plans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# USER SUBSCRIPTION STATUS ENDPOINTS
# ============================================================

@router.get("/active")
async def get_active_subscriptions(request: Request, db: Session = Depends(get_db)):
    """
    Get all active subscriptions for the authenticated user.
    Returns list of active/trial subscriptions with plan details.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        subscriptions = mysql_service.get_records(
            "user_subscriptions",
            {"user_id": user_id, "status": "active"}
        )

        # Also get trial subscriptions
        trial_subs = mysql_service.get_records(
            "user_subscriptions",
            {"user_id": user_id, "status": "trial"}
        )

        all_subs = subscriptions + trial_subs

        result = []
        for sub in all_subs:
            plan = mysql_service.get_single_record("pricing_plans", {"id": sub.get("plan_id")})
            if plan:
                result.append({
                    "subscription_id": sub.get("id"),
                    "plan_id": sub.get("plan_id"),
                    "plan_name": plan.get("name"),
                    "plan_label": plan.get("name"),
                    "service_key": plan.get("service_key"),
                    "service_type": sub.get("service_type"),
                    "status": sub.get("status"),
                    "start_date": sub.get("start_date"),
                    "expiry_date": sub.get("expiry_date"),
                    "trial_end_date": sub.get("trial_end_date"),
                    "features": plan.get("features")
                })

        return {"ok": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_user_subscription_status(request: Request, db: Session = Depends(get_db)):
    """
    Get current subscription status for the authenticated user.
    This is called by frontend premium-manager.js to check access.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        # Session context passed into constructor loop safely
        subscription_service = SubscriptionService(db)
        status = subscription_service.get_subscription_status(user_id)
        return {"ok": True, "data": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/subscription-status")
async def get_user_subscription_status_alias(request: Request, db: Session = Depends(get_db)):
    """
    Get current subscription status for the authenticated user.
    This is an alias for /status to match frontend expectations.
    """
    return await get_user_subscription_status(request, db)


@router.get("/payment-config")
async def get_payment_config():
    """Get Razorpay public configuration for frontend."""
    try:
        config = payment_service.get_public_config()
        return {"ok": True, "data": config}
    except Exception as e:
        logger.error(f"Failed to get payment config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}")
async def get_subscription_details(subscription_id: str, request: Request):
    """
    Get subscription details by ID for payment/checkout display.
    No authentication required - subscription_id is randomly generated.
    """
    try:
        subscription = mysql_service.get_single_record("user_subscriptions", {"id": subscription_id})
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get plan details
        plan = mysql_service.get_single_record("pricing_plans", {"id": subscription.get("plan_id")})
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Get user details
        user = mysql_service.get_single_record("users", {"id": subscription.get("user_id")})

        return {
            "ok": True,
            "data": {
                "id": subscription.get("id"),
                "planLabel": plan.get("name"),
                "amount": plan.get("price_inr"),
                "currency": "INR",
                "fullName": user.get("full_name") if user else "Subscriber",
                "email": user.get("email") if user else None,
                "status": subscription.get("status"),
                "serviceType": subscription.get("service_type"),
                "billingCycle": plan.get("billing_cycle"),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SUBSCRIPTION CREATION & ORDER GATEWAY ENDPOINTS
# ============================================================

@router.post("/create")
async def create_subscription(request: Request, body: dict = Body(...)):
    """
    Create a subscription record for premium upgrade.
    This creates a pending subscription tracking footprint.
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")
        
        required_fields = {"plan_id"}
        missing = required_fields - set(body.keys())
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
        
        plan_id = body.get("plan_id")
        feature_id = body.get("feature_id")
        return_to = body.get("return_to")

        plan = mysql_service.get_single_record("pricing_plans", {"id": plan_id, "is_active": True})
        if not plan:
            raise HTTPException(status_code=404, detail="Pricing plan not found or inactive")

        # Allow multiple subscriptions - no restriction on active subscriptions
        # Users can have multiple active subscriptions for different plans/services

        subscription_id = f"sub_{uuid.uuid4().hex[:16]}"

        subscription_payload = {
            "id": subscription_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "service_type": plan.get("service_type"),
            "status": "pending",
            "start_date": None,
            "expiry_date": None,
            "trial_end_date": None,
            "payment_method": None,
            "transaction_id": None,
            "amount_paid": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mysql_service.insert_record("user_subscriptions", subscription_payload)
        logger.info(f"Created pending subscription: {subscription_id} for user {user_id}, plan {plan_id}")
        
        return {
            "ok": True,
            "data": {
                "subscription_id": subscription_id,
                "plan_id": plan_id,
                "plan_name": plan.get("name"),
                "amount": plan.get("price_inr"),
                "currency": plan.get("currency"),
                "billing_cycle": plan.get("billing_cycle"),
                "feature_id": feature_id,
                "return_to": return_to
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/create-order")
async def create_razorpay_order_signature(payload: OrderCreateSchema):
    """
    Creates a real Razorpay order and returns order details.
    """
    try:
        receipt = f"sub_{payload.subscription_id[:8]}"
        notes = {
            "subscription_id": payload.subscription_id,
            "service_type": payload.service_type
        }

        order = payment_service.create_order(
            amount_inr=payload.amount,
            receipt=receipt,
            notes=notes
        )

        return {
            "ok": True,
            "data": {
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"]
            }
        }
    except Exception as e:
        logger.error(f"Failed to initialize order via transaction gateway: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def subscription_payment_webhook(request: Request):
    """
    Handle Razorpay webhooks for subscription payments.
    Validates signature and activates subscription on payment.captured/order.paid/payment.authorized.
    """
    try:
        raw_body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")

        if not payment_service.verify_webhook_signature(raw_body, signature):
            logger.warning("Webhook signature verification failed")
            return {"ok": False, "error": "Invalid signature"}

        payload = json.loads(raw_body)
        event = payload.get("event")
        data = payload.get("payload", {})

        logger.info(f"Subscription webhook received: {event}")

        if event in ["payment.captured", "order.paid", "payment.authorized"]:
            order_id = data.get("order", {}).get("entity", {}).get("id")
            payment_entity = data.get("payment", {}).get("entity", {})
            payment_id = payment_entity.get("id") or payment_entity.get("id", "")

            if not order_id and payment_entity:
                order_id = payment_entity.get("order_id", "")

            if order_id:
                order = payment_service.fetch_order(order_id)
                notes = order.get("notes", {})
                subscription_id = notes.get("subscription_id")

                if subscription_id:
                    subscription = mysql_service.get_single_record("user_subscriptions", {"id": subscription_id})
                    if subscription:
                        amount_paid = order.get("amount", 0) / 100  # Convert from paise
                        result = _confirm_subscription(subscription, "razorpay", payment_id, amount_paid)
                        logger.info(f"Subscription {subscription_id} activated via webhook ({event})")
                        return {"ok": True, "data": result}

        elif event == "payment.failed":
            return _handle_payment_failed(data)

        return {"ok": True, "message": "Webhook processed"}

    except Exception as e:
        logger.error(f"Subscription webhook error: {str(e)}")
        return {"ok": False, "error": str(e)}


@router.post("/confirm")
async def confirm_subscription(request: Request, body: dict = Body(...)):
    """
    Confirm a subscription after successful payment (manual verification path).
    Populates usage counters for individual assessment testing suites automatically.
    """
    try:
        subscription_id = body.get("subscription_id")
        payment_method = body.get("payment_method")
        transaction_id = body.get("transaction_id")
        amount_paid = body.get("amount_paid", 0)
        
        if not subscription_id:
            raise HTTPException(status_code=400, detail="subscription_id is required")
        
        subscription = mysql_service.get_single_record("user_subscriptions", {"id": subscription_id})
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        result = _confirm_subscription(subscription, payment_method or "razorpay", transaction_id, amount_paid)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




def _handle_payment_failed(payload: dict) -> dict:
    """
    Handle payment.failed webhook event.
    Mark subscription as failed and clean up.
    """
    try:
        payment_data = payload.get("payment", {})
        payment_id = payment_data.get("id", "")
        reason = payment_data.get("description", "Payment failed")
        
        if not payment_id:
            raise ValueError("Missing payment_id in webhook")
        
        subscription = mysql_service.get_single_record("user_subscriptions", {"transaction_id": payment_id})
        
        if subscription and subscription.get("status") == "pending":
            mysql_service.update_record(
                "user_subscriptions",
                {
                    "status": "cancelled",
                    "reason_cancelled": reason,
                    "cancelled_at": datetime.now(),
                    "updated_at": datetime.now(),
                },
                {"id": subscription.get("id")}
            )
            logger.info(f"Marked subscription {subscription.get('id')} as cancelled due to payment failure")
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error handling payment.failed: {str(e)}")
        return {"ok": False, "error": str(e)}


def _confirm_subscription(subscription: dict, payment_method: str, transaction_id: str, amount_paid: float) -> dict:
    """
    Activate a pending subscription after payment verification.
    Extracted as helper to be called from both /confirm endpoint and webhook.
    
    Args:
        subscription: The pending subscription record
        payment_method: Payment method (e.g., 'razorpay', 'manual')
        transaction_id: Transaction ID from payment gateway
        amount_paid: Amount paid in rupees
    """
    if subscription.get("status") != "pending":
        return {
            "ok": True, 
            "message": "Subscription is already active.", 
            "data": {"subscription_id": subscription.get("id"), "status": subscription.get("status")}
        }
    
    subscription_id = subscription.get("id")
    plan = mysql_service.get_single_record("pricing_plans", {"id": subscription.get("plan_id")})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    start_date = datetime.now()
    trial_days = plan.get("trial_days", 0)
    duration_days = 30

    billing_cycle = plan.get("billing_cycle", "monthly")
    if billing_cycle == "yearly":
        duration_days = 365
    elif billing_cycle == "quarterly":
        duration_days = 90
    elif billing_cycle == "one_time":
        duration_days = 365

    expiry_date = start_date + timedelta(days=duration_days)
    trial_end_date = start_date + timedelta(days=trial_days) if trial_days > 0 else None
    
    update_payload = {
        "status": "trial" if trial_days > 0 else "active",
        "start_date": start_date,
        "expiry_date": expiry_date,
        "trial_end_date": trial_end_date,
        "payment_method": payment_method,
        "transaction_id": transaction_id,
        "amount_paid": amount_paid,
        "updated_at": datetime.now(),
    }
    
    mysql_service.update_record("user_subscriptions", update_payload, {"id": subscription_id})
    
    user_update = {
        "subscription_plan_id": subscription.get("plan_id"),
        "subscription_status": "trial" if trial_days > 0 else "active",
        "subscription_start_date": start_date,
        "subscription_expiry_date": expiry_date,
        "is_premium": True,
        "updated_at": datetime.now(),
    }
    mysql_service.update_record("users", user_update, {"id": subscription.get("user_id")})

    if plan:
        _add_plan_features(subscription_id, plan)

        try:
            feature_keys = _extract_feature_keys(plan)

            for feature_key in feature_keys:
                allotment_count = 1
                plan_id_lower = str(plan.get("id")).lower()

                if "x5" in plan_id_lower or "bundle_5" in plan_id_lower:
                    allotment_count = 5
                elif "x10" in plan_id_lower or "bundle_10" in plan_id_lower:
                    allotment_count = 10

                usage_record = {
                    "id": str(uuid.uuid4()),
                    "subscription_id": subscription_id,
                    "user_id": subscription.get("user_id"),
                    "feature_key": feature_key,
                    "plan_id": plan.get("id"),
                    "initial_count": allotment_count,
                    "remaining_count": allotment_count,
                    "created_at": datetime.now(),
                    "expires_at": expiry_date
                }
                mysql_service.insert_record("user_plan_usage", usage_record)
        except Exception as e:
            logger.error(f"Failed to populate per-action usage blocks: {str(e)}")
    
    logger.info(f"Confirmed subscription: {subscription_id} for user {subscription.get('user_id')}")
    
    return {
        "ok": True,
        "data": {
            "subscription_id": subscription_id,
            "status": "trial" if trial_days > 0 else "active",
            "expiry_date": expiry_date.isoformat(),
            "trial_end_date": trial_end_date.isoformat() if trial_end_date else None
        }
    }


def _extract_feature_keys(plan: dict) -> list:
    """
    Extract feature keys from plan using service_key as the primary identifier.
    The 'features' JSON field contains descriptions, not feature keys.
    """
    try:
        # The service_key is the actual feature identifier
        service_key = plan.get("service_key")
        if service_key:
            return [service_key]
        return []
    except Exception as e:
        logger.error(f"Error extracting feature keys: {str(e)}")
        return []


def _add_plan_features(subscription_id: str, plan: dict) -> None:
    """
    Add features from plan to user_subscription_features table.
    Uses the plan's service_key as the feature key.
    """
    try:
        feature_keys = _extract_feature_keys(plan)

        for feature_key in feature_keys:
            feature_record = {
                "id": str(uuid.uuid4()),
                "subscription_id": subscription_id,
                "feature_key": feature_key,
                "enabled": True,
                "created_at": datetime.now(),
            }
            mysql_service.insert_record("user_subscription_features", feature_record)

    except Exception as e:
        logger.error(f"Error adding features to subscription: {str(e)}")