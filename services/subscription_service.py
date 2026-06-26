import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db, User, UserSubscription, PricingPlan

logger = logging.getLogger(__name__)

class SubscriptionService:
    """
    Subscription and Membership Management Service.
    Handles active packages, per-action premium feature access control, 
    and transaction ledger tracking across candidates and recruiters.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initializes the subscription service.
        If a database session is not explicitly passed, it falls back to 
        the global session generator loop.
        """
        self._db = db_session

    @property
    def db(self) -> Session:
        """Resolves the active database session context safely."""
        if self._db is not None:
            return self._db
        return next(get_db())

    def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves a complete summary of the user's active membership status, 
        including compiled feature flags and package metadata.
        """
        try:
            # 1. Fetch user record to check current snapshot fields
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {
                    "is_premium": False,
                    "premium": False,
                    "subscription_plan": "free",
                    "subscription_status": "free",
                    "expiry_date": None,
                    "features": [],
                    "subscription": None
                }

            # 2. Query for active subscriptions in the tracking table
            active_sub = self.db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status.in_(["active", "trial"])
            ).order_by(text("created_at DESC")).first()

            if not active_sub:
                return {
                    "is_premium": False,
                    "premium": False,
                    "subscription_plan": "free",
                    "subscription_status": "free",
                    "expiry_date": None,
                    "features": [],
                    "subscription": None
                }

            # 3. Check hard mathematical expiration boundary
            if active_sub.expiry_date:
                expiry_dt = active_sub.expiry_date
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                
                if expiry_dt < datetime.now(timezone.utc):
                    return {
                        "is_premium": False,
                        "premium": False,
                        "subscription_plan": "free",
                        "subscription_status": "expired",
                        "expiry_date": active_sub.expiry_date.isoformat(),
                        "features": [],
                        "subscription": None
                    }

            # 4. Fetch the plan properties to compile valid feature sets
            plan = self.db.query(PricingPlan).filter(PricingPlan.id == active_sub.plan_id).first()
            features_list = []
            if plan and plan.features:
                try:
                    if isinstance(plan.features, str):
                        features_list = json.loads(plan.features)
                    elif isinstance(plan.features, list):
                        features_list = plan.features
                    else:
                        features_list = [str(plan.features)]
                except Exception:
                    features_list = [str(plan.features)]

            # 5. Fetch additional per-action usages available to this individual
            usage_records = self.db.execute(
                text("SELECT feature_key FROM user_plan_usage WHERE user_id = :user_id AND remaining_count > 0"),
                {"user_id": user_id}
            ).fetchall()
            
            for row in usage_records:
                if row[0] not in features_list:
                    features_list.append(row[0])

            return {
                "is_premium": True,
                "premium": True,
                "subscription_plan": plan.service_key if plan else "premium",
                "subscription_status": "active",
                "expiry_date": active_sub.expiry_date.isoformat() if active_sub.expiry_date else None,
                "features": features_list,
                "subscription": {
                    "plan_id": active_sub.plan_id,
                    "status": active_sub.status,
                    "start_date": active_sub.start_date.isoformat() if active_sub.start_date else None,
                    "expiry_date": active_sub.expiry_date.isoformat() if active_sub.expiry_date else None,
                    "trial_end_date": active_sub.trial_end_date.isoformat() if active_sub.trial_end_date else None
                }
            }

        except Exception as e:
            logger.error(f"Error compiling subscription status for user {user_id}: {str(e)}")
            return {
                "is_premium": False,
                "premium": False,
                "subscription_plan": "free",
                "subscription_status": "error",
                "expiry_date": None,
                "features": [],
                "subscription": None
            }

    def check_feature_access(self, user_id: str, feature_key: str) -> Dict[str, Any]:
        """
        Validates whether a user has operational access to a specific premium feature
        either through an active core subscription or a per-action unexpired token block.
        """
        try:
            # Demo/unlimited access: user has an active subscription to the demo_all_access plan.
            # This grants access to ANY feature key — including future ones not yet in the features JSON.
            demo_check = self.db.execute(
                text("""
                    SELECT 1 FROM user_subscriptions us
                    JOIN pricing_plans pp ON us.plan_id = pp.id
                    WHERE us.user_id = :user_id
                      AND pp.service_key = 'demo_all_access'
                      AND us.status IN ('active', 'trial')
                      AND (us.expiry_date IS NULL OR us.expiry_date > NOW())
                    LIMIT 1
                """),
                {"user_id": user_id}
            ).fetchone()
            if demo_check:
                return {"accessible": True, "type": "unlimited", "remaining": None}

            # Free assessment check: if the plan belongs to general_plan service_type, grant access to all users.
            free_check = self.db.execute(
                text("""
                    SELECT id FROM pricing_plans
                    WHERE service_key = :feature_key
                      AND service_type = 'general_plan'
                      AND is_active = 1
                    LIMIT 1
                """),
                {"feature_key": feature_key}
            ).fetchone()
            if free_check:
                return {"accessible": True, "type": "general_plan", "remaining": None}

            # Primary check: direct join on user_subscriptions + pricing_plans by service_key.
            # This is the authoritative check — doesn't depend on user_plan_usage being populated.
            direct_sub = self.db.execute(
                text("""
                    SELECT us.id FROM user_subscriptions us
                    JOIN pricing_plans pp ON us.plan_id = pp.id
                    WHERE us.user_id = :user_id
                      AND pp.service_key = :feature_key
                      AND us.status IN ('active', 'trial')
                      AND (us.expiry_date IS NULL OR us.expiry_date > NOW())
                    LIMIT 1
                """),
                {"user_id": user_id, "feature_key": feature_key}
            ).fetchone()
            if direct_sub:
                return {"accessible": True, "type": "subscription", "remaining": None}

            # Bundle subscription check: user has an active assessment_bundle whose features JSON contains this key
            bundle_sub = self.db.execute(
                text("""
                    SELECT us.id FROM user_subscriptions us
                    JOIN pricing_plans pp ON us.plan_id = pp.id
                    WHERE us.user_id = :user_id
                      AND pp.service_type = 'assessment_bundle'
                      AND pp.features LIKE :feature_pattern
                      AND us.status IN ('active', 'trial')
                      AND (us.expiry_date IS NULL OR us.expiry_date > NOW())
                    LIMIT 1
                """),
                {"user_id": user_id, "feature_pattern": f'%"{feature_key}"%'}
            ).fetchone()
            if bundle_sub:
                return {"accessible": True, "type": "subscription", "remaining": None}

            # Secondary check: per-action usage tokens (bundles / top-ups)
            usage_row = self.db.execute(
                text("SELECT id, remaining_count FROM user_plan_usage WHERE user_id = :user_id AND feature_key = :feature_key AND remaining_count > 0 LIMIT 1"),
                {"user_id": user_id, "feature_key": feature_key}
            ).fetchone()
            if usage_row:
                return {"accessible": True, "type": "per_action", "remaining": usage_row.remaining_count}

            return {"accessible": False, "type": "locked", "remaining": 0}

        except Exception as e:
            logger.error(f"Failed to check feature access for user {user_id}: {str(e)}")
            return {"accessible": False, "type": "error", "remaining": 0}

    def consume_feature(self, user_id: str, feature_key: str) -> Dict[str, Any]:
        """
        Decrements and records a single token usage count for per-action features.
        If the access comes from a general unlimited package subscription, counts remain untouched.
        """
        try:
            access = self.check_feature_access(user_id, feature_key)
            if not access["accessible"]:
                return {"ok": False, "error": "Access blocked. Premium feature verification failed."}

            if access["type"] == "subscription":
                return {"ok": True, "message": "Unlimited tier subscription access. No tokens deducted.", "remaining": None}

            usage_row = self.db.execute(
                text("SELECT id, remaining_count, usage_logs FROM user_plan_usage WHERE user_id = :user_id AND feature_key = :feature_key AND remaining_count > 0 LIMIT 1"),
                {"user_id": user_id, "feature_key": feature_key}
            ).fetchone()

            if not usage_row:
                return {"ok": False, "error": "No remaining tokens available to consume."}

            usage_id = usage_row.id
            new_count = usage_row.remaining_count - 1
            
            logs = []
            if usage_row.usage_logs:
                try:
                    logs = json.loads(usage_row.usage_logs) if isinstance(usage_row.usage_logs, str) else usage_row.usage_logs
                except Exception:
                    pass

            logs.append({
                "consumed_at": datetime.utcnow().isoformat(),
                "remaining_before": usage_row.remaining_count,
                "remaining_after": new_count
            })

            self.db.execute(
                text("UPDATE user_plan_usage SET remaining_count = :new_count, usage_logs = :logs WHERE id = :id"),
                {"new_count": new_count, "logs": json.dumps(logs), "id": usage_id}
            )
            self.db.commit()

            return {"ok": True, "message": "Token balance updated successfully.", "remaining": new_count}

        except Exception as e:
            logger.error(f"Error executing feature consumption for user {user_id}: {str(e)}")
            self.db.rollback()
            return {"ok": False, "error": str(e)}

    def grant_subscription(self, user_id: str, plan_id: str, days_duration: int, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Activates a premium pricing plan subscription record for a target user profile.
        Automatically updates fast flags inside the main user table context.
        """
        try:
            plan = self.db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
            if not plan:
                return {"ok": False, "error": "Target system pricing plan not found."}

            import uuid
            now = datetime.utcnow()
            expiry = now + timedelta(days=days_duration) if days_duration > 0 else None

            # Deactivate old plans to prevent overlaps
            self.db.execute(
                text("UPDATE user_subscriptions SET status = 'cancelled' WHERE user_id = :user_id AND status = 'active'"),
                {"user_id": user_id}
            )

            # Insert new tracking entry
            sub_id = str(uuid.uuid4())
            new_sub = UserSubscription(
                id=sub_id,
                user_id=user_id,
                plan_id=plan_id,
                service_type=plan.service_type,
                status="active",
                start_date=now,
                expiry_date=expiry,
                amount_paid=plan.price_inr,
                transaction_id=transaction_id,
                payment_method="razorpay" if transaction_id else "manual"
            )
            self.db.add(new_sub)

            # Synchronize quick lookup values inside the main Users data row
            self.db.execute(
                text("""
                    UPDATE users 
                    SET is_premium = TRUE, 
                        onboarded = TRUE,
                        subscription_plan_id = :plan_id, 
                        subscription_status = 'active', 
                        subscription_start_date = :start, 
                        subscription_expiry_date = :expiry 
                    WHERE id = :user_id
                """),
                {"plan_id": plan_id, "start": now, "expiry": expiry, "user_id": user_id}
            )

            # Handle token allotment if this is a per-action/bundled usage pack
            if plan.billing_cycle == "one_time" or plan.service_type in ["job_posting", "feature_addon"]:
                allotment_count = 1
                plan_id_lower = plan.id.lower()
                if "x5" in plan_id_lower or "bundle_5" in plan_id_lower:
                    allotment_count = 5
                elif "x10" in plan_id_lower or "bundle_10" in plan_id_lower:
                    allotment_count = 10
                elif "x50" in plan_id_lower or "bundle_50" in plan_id_lower:
                    allotment_count = 50

                self.db.execute(
                    text("""
                        INSERT INTO user_plan_usage (id, subscription_id, user_id, feature_key, plan_id, initial_count, remaining_count, created_at, expires_at)
                        VALUES (:id, :sub_id, :user_id, :f_key, :plan_id, :count, :count, :now, :expiry)
                    """),
                    {
                        "id": str(uuid.uuid4()), "sub_id": sub_id, "user_id": user_id,
                        "f_key": plan.service_key, "plan_id": plan_id, "count": allotment_count,
                        "now": now, "expiry": expiry
                    }
                )

            self.db.commit()
            logger.info(f"Successfully granted subscription plan {plan_id} to user {user_id}")
            return {"ok": True, "subscription_id": sub_id, "expiry_date": expiry.isoformat() if expiry else None}

        except Exception as e:
            logger.error(f"Critical failure granting subscription payload: {str(e)}")
            self.db.rollback()
            return {"ok": False, "error": str(e)}

    def check_and_handle_expiry(self) -> Dict[str, Any]:
        """
        Batch operational lifecycle check. Designed to be triggered by a daily background loop
        to clear expired subscription accounts.
        """
        try:
            now = datetime.utcnow()
            
            # Find matching user records that crossed expiration parameters
            expired_users = self.db.execute(
                text("SELECT id FROM users WHERE subscription_status = 'active' AND subscription_expiry_date < :now"),
                {"now": now}
            ).fetchall()

            user_ids = [row[0] for row in expired_users]
            if not user_ids:
                return {"ok": True, "processed": 0}

            # SQLAlchemy 2.0 list-binding tuple expansion parameter resolution mechanics
            self.db.execute(
                text("UPDATE user_subscriptions SET status = 'expired' WHERE user_id IN :ids AND status = 'active'"),
                {"ids": user_ids}
            )
            
            self.db.execute(
                text("UPDATE users SET is_premium = FALSE, subscription_status = 'expired' WHERE id IN :ids"),
                {"ids": user_ids}
            )

            self.db.commit()
            logger.info(f"Subscription background loop complete. Demoted {len(user_ids)} expired profiles.")
            return {"ok": True, "processed": len(user_ids)}

        except Exception as e:
            logger.error(f"Background cron verification loop failed: {str(e)}")
            self.db.rollback()
            return {"ok": False, "error": str(e)}