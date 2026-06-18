"""
Skreenit Payment Service — Razorpay Integration
================================================
Single shared service for ALL payment operations across the platform.
Current consumers: Training Sessions
Future consumers:  Recruiter subscriptions, Applicant premium plans, etc.

Usage:
    from services.payment_service import PaymentService
    payment_service = PaymentService()
"""

import os
import hmac
import hashlib
import razorpay
from typing import Optional
from utils_others.logger import logger


class PaymentService:
    """Centralised Razorpay payment handler for all Skreenit services."""

    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        self.webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        self.currency = "INR"

        if self.key_id and self.key_secret:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            self.client.set_app_details({"title": "Skreenit", "version": "1.0.0"})
        else:
            self.client = None
            logger.warning("PaymentService: Razorpay credentials not configured in environment.")

    # ------------------------------------------------------------------ #
    # ORDER CREATION
    # ------------------------------------------------------------------ #

    def create_order(
        self,
        amount_inr: float,
        receipt: str,
        notes: Optional[dict] = None,
    ) -> dict:
        """
        Create a Razorpay order.  Amount is in rupees (converted to paise internally).

        Args:
            amount_inr: Amount in Indian Rupees (e.g. 4999)
            receipt:    Unique receipt string — use registration_id or order reference
            notes:      Optional key-value pairs attached to the order (visible in dashboard)

        Returns:
            Razorpay order dict containing id, amount, currency, status, etc.
        """
        if not self.client:
            raise RuntimeError("Razorpay client not initialised. Check RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET.")

        amount_paise = int(amount_inr * 100)
        payload = {
            "amount": amount_paise,
            "currency": self.currency,
            "receipt": receipt[:40],  # Razorpay receipt max 40 chars
            "notes": notes or {},
        }

        try:
            order = self.client.order.create(data=payload)
            logger.info(f"Razorpay order created: {order['id']} | receipt={receipt} | amount=₹{amount_inr}")
            return order
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")
            raise RuntimeError(f"Payment order creation failed: {str(e)}")

    # ------------------------------------------------------------------ #
    # SIGNATURE VERIFICATION
    # ------------------------------------------------------------------ #

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verify the HMAC-SHA256 signature returned by Razorpay after checkout.

        Args:
            razorpay_order_id:   order.id returned by create_order()
            razorpay_payment_id: payment id from Razorpay checkout handler response
            razorpay_signature:  signature from Razorpay checkout handler response

        Returns:
            True if signature is valid, False otherwise.
        """
        try:
            params = {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
            self.client.utility.verify_payment_signature(params)
            logger.info(f"Signature verified OK — payment_id={razorpay_payment_id}")
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning(f"Signature verification FAILED — payment_id={razorpay_payment_id}")
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False

    # ------------------------------------------------------------------ #
    # WEBHOOK SIGNATURE VERIFICATION
    # ------------------------------------------------------------------ #

    def verify_webhook_signature(self, raw_body: bytes, razorpay_signature: str) -> bool:
        """
        Verify the X-Razorpay-Signature header on incoming webhook events.

        Args:
            raw_body:           Raw request bytes (do NOT parse JSON before passing)
            razorpay_signature: Value of the X-Razorpay-Signature header

        Returns:
            True if webhook signature is valid, False otherwise.
        """
        if not self.webhook_secret or self.webhook_secret == "YourWebhookSecret":
            logger.warning("Webhook secret not configured — skipping verification (unsafe for production).")
            return True  # Permissive during setup; tighten once secret is set

        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(expected, razorpay_signature)
        if not is_valid:
            logger.warning("Webhook signature verification FAILED.")
        return is_valid

    # ------------------------------------------------------------------ #
    # FETCH ORDER / PAYMENT (for reconciliation)
    # ------------------------------------------------------------------ #

    def fetch_order(self, order_id: str) -> dict:
        """Fetch a Razorpay order by its ID."""
        if not self.client:
            raise RuntimeError("Razorpay client not initialised.")
        try:
            return self.client.order.fetch(order_id)
        except Exception as e:
            logger.error(f"Failed to fetch Razorpay order {order_id}: {str(e)}")
            raise RuntimeError(f"Failed to fetch order: {str(e)}")

    def fetch_payment(self, payment_id: str) -> dict:
        """Fetch a Razorpay payment by its ID."""
        if not self.client:
            raise RuntimeError("Razorpay client not initialised.")
        try:
            return self.client.payment.fetch(payment_id)
        except Exception as e:
            logger.error(f"Failed to fetch Razorpay payment {payment_id}: {str(e)}")
            raise RuntimeError(f"Failed to fetch payment: {str(e)}")

    # ------------------------------------------------------------------ #
    # HELPER
    # ------------------------------------------------------------------ #

    def get_public_config(self, company_name: str = "Skreenit") -> dict:
        """Return public config safe to expose to the frontend."""
        return {
            "key_id": self.key_id,
            "currency": self.currency,
            "company_name": company_name,
        }
