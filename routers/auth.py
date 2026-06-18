import traceback
import os
from fastapi import APIRouter, Request, HTTPException, Form
from typing import Optional

from models.auth_models import LoginRequest
from services.auth_service import AuthService
from services.mysql_service import UserService, ValidationError, DuplicateUserError, DatabaseError
from utils_others.logger import logger

router = APIRouter(tags=["Authentication"])
_auth_service: Optional[AuthService] = None
_user_service: Optional[UserService] = None

def create_error_response(detail: str, status_code: int = 400):
    """Helper to create consistent error responses."""
    raise HTTPException(status_code=status_code, detail=detail)

def get_auth_service() -> AuthService:
    """Get custom auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

def get_user_service() -> UserService:
    """Get user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@router.post("/login")
async def login(request: Request):
    """Login user with custom authentication - accepts JSON body."""
    auth_service = get_auth_service()
    user_service = get_user_service()
    
    try:
        # Parse JSON body
        body = await request.json()
        login_id = body.get("login_id", "").strip()  # Can be email or user_id (display_id)
        password = body.get("password", "").strip()
        
        if not login_id or not password:
            create_error_response("Email/User ID and password are required")
        
        # Authenticate with custom auth service
        result = auth_service.login(login_id, password)
        
        logger.info(
            "User logged in successfully",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )

        return {"ok": True, "data": result}

    except ValueError as e:
        logger.error(
            f"Login failed: {str(e)}",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )
        create_error_response("Invalid credentials", 401)
    except Exception as e:
        logger.error(
            f"Login failed: {str(e)}",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )
        create_error_response("Login failed. Please try again.", 500)

# ---------------------------------------------------------
# GET CURRENT USER
# ---------------------------------------------------------
@router.get("/me")
async def get_current_user_me(request: Request):
    """Get current authenticated user data."""
    auth_service = get_auth_service()
    
    try:
        # Get user from request state (set by middleware)
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get full user data from database
        user_service = get_user_service()
        full_user = user_service.get_user(user["user_id"])
        if not full_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info("Current user fetched", extra={"user_id": user["user_id"]})
        return {"ok": True, "data": full_user}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user data")

# ---------------------------------------------------------
# MARK USER AS ONBOARDED
# ---------------------------------------------------------
@router.post("/mark-onboarded")
async def mark_onboarded(request: Request):
    """Mark user as onboarded after completing profile setup."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_service = get_user_service()
        success = user_service.mark_as_onboarded(user["sub"])
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info("User marked as onboarded", extra={"user_id": user["sub"]})
        return {"ok": True, "message": "User onboarded successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark user as onboarded: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update onboarding status")

# ---------------------------------------------------------
# SWITCH ACTIVE ROLE (Dual-Role Support)
# ---------------------------------------------------------
@router.post("/switch-role")
async def switch_role(request: Request):
    """Switch active role for dual-role users. Returns new tokens with updated role."""
    # Verify user is authenticated
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Parse request body
        body = await request.json()
        target_role = body.get("role", "").strip().lower()
        
        if not target_role:
            raise HTTPException(status_code=400, detail="Role is required")
        
        if target_role not in ["candidate", "recruiter"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'candidate' or 'recruiter'")
        
        # Get services
        user_service = get_user_service()
        auth_service = get_auth_service()
        
        # Switch the active role
        updated_user = user_service.switch_active_role(user["sub"], target_role)
        
        if not updated_user:
            raise HTTPException(status_code=400, detail="Failed to switch role. User may not have this role assigned.")
        
        # Generate new tokens with updated role
        tokens = auth_service._generate_tokens(updated_user)
        
        logger.info(
            f"User switched role to {target_role}",
            extra={"user_id": user["sub"], "new_role": target_role, "onboarded": updated_user["onboarded"]}
        )
        
        return {
            "ok": True,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": updated_user["id"],
                "email": updated_user["email"],
                "full_name": updated_user["full_name"],
                "role": updated_user["role"],
                "roles": updated_user["roles"],
                "has_multiple_roles": len(updated_user["roles"]) > 1,
                "onboarded": updated_user["onboarded"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch role: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to switch role")

# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------
@router.post("/register")
async def register(request: Request):
    """Register a new user with custom authentication - accepts JSON."""
    try:
        # Parse JSON body
        body = await request.json()
        
        # Extract fields
        full_name = body.get("full_name", "").strip()
        email = body.get("email", "").strip().lower()
        password = body.get("password", "").strip()
        mobile = body.get("mobile", "").strip()
        location = body.get("location", "").strip()
        role = body.get("role", "").strip()
        email_redirect_to = body.get("email_redirect_to")
        
        logger.info(f"Registration attempt for email: {email}", extra={
            "request_id": getattr(request.state, "request_id", None)
        })
        
        # Validate required fields
        if not all([full_name, email, password, mobile, location, role]):
            missing = [k for k, v in [("full_name", full_name), ("email", email), 
                       ("password", password), ("mobile", mobile), ("location", location), 
                       ("role", role)] if not v]
            create_error_response(f"Missing fields: {', '.join(missing)}")
        
        auth_service = get_auth_service()
        
        result = await auth_service.register(
            full_name=full_name, 
            email=email, 
            password=password, 
            mobile=mobile, 
            location=location, 
            role=role,
            email_redirect_to=email_redirect_to
        )
        
        logger.info(
            "User registered successfully",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )

        return {"ok": True, "data": result}

    except ValidationError as e:
        logger.error(f"Registration validation failed: {str(e)}")
        create_error_response(f"Validation error: {str(e)}", 400)
    except DuplicateUserError as e:
        logger.error(f"Registration failed - duplicate user: {str(e)}")
        create_error_response("Email already registered", 409)
    except DatabaseError as e:
        logger.error(f"Registration database error: {str(e)}")
        create_error_response("Registration failed. Please try again.", 500)
    except ValueError as e:
        # Re-raised from auth_service with specific messages (e.g. duplicate email)
        msg = str(e).lower()
        if 'already registered' in msg or 'already exists' in msg:
            create_error_response("Email already registered", 409)
        else:
            logger.error(f"Registration failed: {str(e)}")
            create_error_response(f"Registration failed: {str(e)}", 500)
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}\n{traceback.format_exc()}")
        # Check for DB connection errors to return 503 instead of 500
        err_msg = str(e)
        if 'Can\'t connect' in err_msg or 'connection' in err_msg.lower() and 'refused' in err_msg.lower():
            create_error_response("Service temporarily unavailable. Please try again later.", 503)
        create_error_response(f"Registration failed: {str(e)}", 500)

# ---------------------------------------------------------
# UPDATE PASSWORD
# ---------------------------------------------------------
@router.post("/update-password")
async def update_password(request: Request, new_password: str = Form(...)):
    """Update user password."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        auth_service = get_auth_service()
        auth_service.update_password(user["user_id"], new_password)
        return {"ok": True, "message": "Password updated successfully"}

    except Exception as e:
        logger.error(f"Password update failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update password")

# ---------------------------------------------------------
# CONFIRM EMAIL
# ---------------------------------------------------------
@router.post("/confirm-email")
async def confirm_email(request: Request):
    """Confirm user email address."""
    try:
        # Parse JSON data
        body = await request.json()
        token = body.get("token", "").strip()
        email = body.get("email", "").strip().lower()
        
        if not token or not email:
            create_error_response("Missing token or email")
        
        # Verify token and update user
        auth_service = get_auth_service()
        
        # Verify token using centralized auth service
        payload = auth_service.verify_confirmation_token(token)
        
        # Update user email confirmation
        user_service = get_user_service()
        user = user_service.get_user_by_email(email)
        
        if user and not user.get("email_confirmed_at"):
            # Mark email as confirmed
            user_service.update_user_email_confirmed(user["id"])
            logger.info(f"Email confirmed for user: {email}")
            
            # Get updated user data with role
            updated_user = user_service.get_user_by_email(email)
            
            return {
                "ok": True,
                "message": "Email confirmed successfully! You can now login to your account.",
                "data": {
                    "user": {
                        "id": updated_user["id"],
                        "email": updated_user["email"],
                        "role": updated_user["role"],
                        "full_name": updated_user["full_name"],
                        "mobile": updated_user["phone"],
                        "onboarded": updated_user["onboarded"],
                        "email_verified": True
                    }
                }
            }
        elif user and user.get("email_confirmed_at"):
            return {
                "ok": True,
                "message": "Email already confirmed. You can login to your account."
            }
        else:
            create_error_response("Invalid token or user not found")
            
    except ValueError as e:
        logger.error(f"Email confirmation failed: {str(e)}")
        create_error_response(str(e))
    except Exception as e:
        logger.error(f"Email confirmation failed: {str(e)}")
        create_error_response("Email confirmation failed")

# ---------------------------------------------------------
# RESEND CONFIRMATION EMAIL
# ---------------------------------------------------------
@router.post("/resend-confirmation")
async def resend_confirmation(request: Request):
    """Resend email confirmation link to user."""
    try:
        body = await request.json()
        login_id = body.get("login_id", "").strip()
        
        if not login_id:
            return {"ok": False, "message": "Email or User ID is required"}
        
        # Get user service
        user_service = get_user_service()
        auth_service = get_auth_service()
        
        # Check if user exists (can lookup by email or display_id)
        user = user_service.get_user_for_auth(login_id)
        
        if not user:
            # Don't reveal if email exists for security
            logger.info(f"Resend confirmation requested for non-existent login_id: {login_id}")
            return {"ok": True, "message": "If an account exists with this login ID, a confirmation link has been sent"}
        
        # Check if email is already confirmed
        if user.get("email_confirmed_at"):
            return {"ok": True, "message": "Your email is already confirmed. You can login to your account."}
        
        # Generate new confirmation token and send email
        confirmation_token = auth_service.generate_confirmation_token(user["id"], user["email"])
        base_url = os.getenv("FRONTEND_BASE_URL", "https://login.skreenit.com")
        confirmation_url = f"{base_url}/confirm-email.html?token={confirmation_token}&email={user['email']}"
        
        # Use await with the instance method
        await auth_service.email_service.send_verification_email(user["email"], user.get("full_name", "User"), confirmation_url)
        logger.info(f"Resent confirmation email to: {user['email']}")
        
        return {"ok": True, "message": "Confirmation email sent! Please check your inbox and spam folder."}
        
    except Exception as e:
        logger.error(f"Resend confirmation failed: {str(e)}")
        # Still return generic success to prevent email enumeration
        return {"ok": True, "message": "If an account exists with this email, a confirmation link has been sent"}


# ---------------------------------------------------------
# FORGOT PASSWORD
# ---------------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...)):
    """Handle forgot password request - send reset email if user exists."""
    try:
        user_service = get_user_service()
        auth_service = get_auth_service()
        
        # Check if user exists (don't reveal if email exists for security)
        user = user_service.get_user_by_email(email.strip().lower())
        
        if user:
            # Generate reset token and send email
            reset_token = auth_service.generate_password_reset_token(email)
            await auth_service.send_password_reset_email(email, reset_token)
            logger.info(f"Password reset email sent to: {email}")
        else:
            # Log for debugging but don't expose to user
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        # Always return success to prevent email enumeration
        return {"ok": True, "message": "If an account exists, a reset link has been sent to your email"}

    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        # Still return success to prevent email enumeration
        return {"ok": True, "message": "If an account exists, a reset link has been sent to your email"}

# ---------------------------------------------------------
# VERIFY RESET TOKEN
# ---------------------------------------------------------
@router.post("/verify-reset-token")
async def verify_reset_token(request: Request):
    """Verify if a password reset token is valid."""
    try:
        body = await request.json()
        token = body.get("token", "").strip()
        
        if not token:
            create_error_response("Token is required")
        
        auth_service = get_auth_service()
        email = auth_service.verify_password_reset_token(token)
        
        return {"ok": True, "email": email, "message": "Token is valid"}
        
    except ValueError as e:
        logger.error(f"Token verification failed: {str(e)}")
        create_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        create_error_response("Invalid token", 400)

# ---------------------------------------------------------
# RESET PASSWORD
# ---------------------------------------------------------
@router.post("/reset-password")
async def reset_password(request: Request):
    """Reset password using reset token."""
    try:
        body = await request.json()
        token = body.get("token", "").strip()
        new_password = body.get("password", "").strip()
        
        if not token or not new_password:
            create_error_response("Token and password are required")
        
        if len(new_password) < 8:
            create_error_response("Password must be at least 8 characters", 400)
        
        auth_service = get_auth_service()
        result = auth_service.reset_password(token, new_password)
        
        logger.info("Password reset successfully")
        return result
        
    except ValueError as e:
        logger.error(f"Password reset failed: {str(e)}")
        create_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        create_error_response("Failed to reset password", 500)

# ---------------------------------------------------------
# REFRESH TOKEN
# ---------------------------------------------------------
@router.post("/refresh-token")
async def refresh_token(request: Request, refresh_token: str = Form(...)):
    """Refresh access token using refresh token."""
    try:
        auth_service = get_auth_service()
        tokens = auth_service.refresh_access_token(refresh_token)
        
        return {"ok": True, "data": tokens}

    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/debug-email")
async def debug_email():
    """Debug endpoint to test email connectivity"""
    try:
        from services.email_service import EmailService
        email_service = EmailService()
        
        # Test Resend connectivity
        connectivity_result = email_service.test_resend_connectivity()
        
        # Test actual email send
        email_result = await email_service.send_verification_email(
            to_email="test@example.com",
            full_name="Debug Test",
            confirmation_url="https://test.com"
        )
        
        return {
            "connectivity": connectivity_result,
            "email_result": email_result,
            "email_service": "Resend API",
            "from_email": email_service.from_email,
            "api_configured": bool(email_service.api_key)
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@router.post("/logout")
async def logout(request: Request):
    """Logout user (client-side token removal)."""
    user = getattr(request.state, "user", None)
    if user:
        logger.info(f"User logged out", extra={"user_id": user.get("sub", "unknown")})

    return {"ok": True, "message": "Logged out successfully"}


# ---------------------------------------------------------
# USER SUBSCRIPTION STATUS
# ---------------------------------------------------------
@router.get("/user/subscription-status")
async def get_user_subscription_status(request: Request):
    """
    Get current subscription status for the authenticated user.
    This is called by frontend premium-manager.js to check access.
    """
    try:
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = user.get("sub") or user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user credentials")

        user_service = get_user_service()
        user_data = user_service.get_single_record("users", {"id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        is_premium = user_data.get("is_premium", False)
        subscription_status = user_data.get("subscription_status", "free")
        subscription_expiry = user_data.get("subscription_expiry_date")

        # Check if subscription is expired
        if is_premium and subscription_expiry:
            from datetime import datetime
            if subscription_expiry < datetime.now():
                is_premium = False
                subscription_status = "expired"

        return {
            "ok": True,
            "data": {
                "is_premium": is_premium,
                "premium": is_premium,
                "subscription_status": subscription_status,
                "expiry_date": subscription_expiry.isoformat() if subscription_expiry else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
