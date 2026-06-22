import os
from unittest import result
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.mysql_service import UserService
from utils_others.logger import logger
from services.email_service import EmailService

class AuthService:
    """
    Custom Authentication Service replacing Supabase.
    Handles JWT, Password Hashing, and User Session Management.
    """

    def __init__(self):
        self.user_service = UserService()
        # Strictly pull from environment; validator in config.py handles missing keys
        self.jwt_secret = os.getenv("JWT_SECRET_KEY")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        self.refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))
        self.email_service = EmailService()

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    def _generate_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate JWT access and refresh tokens including onboarding status."""
        now = datetime.utcnow()
        
        # Access token payload - Inclusion of 'onboarded' is critical for frontend redirects
        access_payload = {
            "sub": str(user_data["id"]),
            "email": user_data["email"],
            "role": user_data.get("role", "candidate"),
            "full_name": user_data.get("full_name", ""),
            "onboarded": user_data.get("onboarded", False),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes)
        }
        
        refresh_payload = {
            "sub": str(user_data["id"]),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days)
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def register(self, full_name: str, email: str, password: str, 
                 mobile: str, location: str, role: str, 
                 email_redirect_to: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user and return user data with tokens."""
        try:
            existing_user = self.user_service.get_user_by_email(email)
            if existing_user:
                # Check if user already has the requested role
                current_roles = existing_user.get("roles", [existing_user.get("role", "candidate")])
                logger.info(f"Registration attempt - Existing user: {email}, Current roles: {current_roles}, Requested role: {role}")
                
                if role not in current_roles:
                    # Add new role to existing user
                    updated_user = self.user_service.add_role_to_user(existing_user["id"], role)
                    logger.info(f"Role addition result: {updated_user}")
                    if not updated_user:
                        raise ValueError("Failed to add role to existing user")
                    
                    # Generate tokens for updated user with new role
                    tokens = self._generate_tokens(updated_user)
                    
                    # Send verification email for the new role registration only if email not already verified
                    if not updated_user.get("email_verified", False):
                        try:
                            await self._send_verification_email(updated_user, tokens['access_token'], email_redirect_to)
                        except Exception as email_err:
                            logger.error(f"Failed to send verification email for role addition: {str(email_err)}")
                            # Continue with registration even if email fails
                    else:
                        logger.info(f"Email already verified for user {email}, skipping verification email for role addition")
                    
                    user_roles_new = updated_user.get("roles") or [updated_user["role"]]
                    return {
                        "ok": True,
                        "user": {
                            "id": updated_user["id"],
                            "email": updated_user["email"],
                            "role": updated_user["role"],  # This will be the new role
                            "roles": user_roles_new,
                            "has_multiple_roles": len(user_roles_new) > 1,
                            "full_name": updated_user["full_name"],
                            "onboarded": updated_user["onboarded"]
                        },
                        "access_token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"]
                    }
                else:
                    # User already has this role, proceed as normal
                    raise ValueError(f"This email is already registered with {role} role")

            user_data = {
                "email": email,
                "full_name": full_name,
                "password": self._hash_password(password),
                "phone": mobile,
                "location": location,
                "role": role,
                "onboarded": False,
                "email_verified": False,
                "metadata": {"registration_source": "web", "onboarded": False}
            }

            created_user = self.user_service.create_user(user_data)
            if not created_user:
                raise ValueError("Failed to create user account")

            tokens = self._generate_tokens(created_user)

            # Verification email logic - NON-BLOCKING
            # Fire and forget - don't let email failures break registration
            try:
                await self._send_verification_email(created_user, tokens['access_token'], email_redirect_to)
            except Exception as email_err:
                logger.error(f"Failed to send verification email for {email}: {str(email_err)}")
                # Continue with registration even if email fails
                # User can request resend later

            return {
                "ok": True,
                "user": {
                    "id": created_user["id"],
                    "email": created_user["email"],
                    "role": created_user["role"],
                    "full_name": created_user["full_name"],
                    "onboarded": created_user["onboarded"]
                },
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"]
            }
        except Exception as e:
            logger.error(f"Registration failed for {email}: {str(e)}")
            raise ValueError(str(e))

    async def _send_verification_email(self, user, token, redirect_url):
        try:
            base_url = redirect_url or os.getenv("FRONTEND_BASE_URL") or "https://login.skreenit.com"
            confirmation_link = f"{base_url}/confirm-email.html?token={token}&email={user['email']}"
            full_name = user.get('full_name', 'User')
            
            # Send verification email
            email_service = EmailService()
            result = await email_service.send_verification_email(
                to_email=user['email'],
                full_name=full_name,
                confirmation_url=confirmation_link
            )
            if result.get("status") == "error":
                raise ValueError(result.get("message", "Failed to send verification email"))
            logger.info("Verification email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            raise ValueError(str(e))

    def login(self, login_id: str, password: str) -> Dict[str, Any]:
        """Verify credentials and return user session."""
        user = self.user_service.get_user_for_auth(login_id)  # Use secure auth method
        if not user:
            raise ValueError("Invalid credentials")
        
        
        if not self._verify_password(password, user["password"]):
            raise ValueError("Invalid credentials")

        # Check if email is confirmed
        if not user.get("email_verified"):
            raise ValueError("Please confirm your email before logging in. Check your inbox for the verification link.")
        

        # Compute onboarded for the active role so dual-role users see the correct
        # onboarding state for whichever role they are signing into.
        user["onboarded"] = self.user_service.is_role_onboarded(user["id"], user["role"])

        tokens = self._generate_tokens(user)
        self.user_service.update_last_login(user["id"])

        # Handle legacy users without roles array (use role as single-item list)
        user_roles = user.get("roles") or [user["role"]]
        has_multiple_roles = len(user_roles) > 1
        
        logger.info(f"Login debug - User: {user['email']}, Active Role: {user['role']}, All Roles: {user_roles}, Has Multiple: {has_multiple_roles}, Onboarded (active role): {user['onboarded']}")
        return {
            "ok": True,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "roles": user_roles,
                "has_multiple_roles": has_multiple_roles,
                "onboarded": user["onboarded"]
            }
        }

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")
            
            return payload # Returns the decoded claims (sub, role, onboarded, etc.)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    def generate_confirmation_token(self, user_id: str, email: str) -> str:
        """Generate a short-lived JWT token for email confirmation."""
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "email_confirmation",
            "iat": now,
            "exp": now + timedelta(hours=24)  # 24 hours expiration
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_confirmation_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token for email confirmation (no type check)."""
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Confirmation token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid confirmation token")

    def generate_password_reset_token(self, email: str) -> str:
        """Generate a short-lived JWT token for password reset."""
        now = datetime.utcnow()
        payload = {
            "sub": email,
            "type": "password_reset",
            "iat": now,
            "exp": now + timedelta(hours=1)  # 1 hour expiration
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_password_reset_token(self, token: str) -> str:
        """Verify password reset token and return the associated email."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            if payload.get("type") != "password_reset":
                raise ValueError("Invalid token type")
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise ValueError("Password reset link has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid password reset token")

    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Reset user password using reset token."""
        email = self.verify_password_reset_token(token)
        if not email:
            raise ValueError("Invalid token")
        
        user = self.user_service.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")
        
        # Hash and update password
        hashed_password = self._hash_password(new_password)
        success = self.user_service.update_user_password(user["id"], hashed_password)
        if not success:
            raise ValueError("Failed to update password")
        
        return {"ok": True, "message": "Password updated successfully"}

    async def send_password_reset_email(self, email: str, reset_token: str, redirect_url: Optional[str] = None):
        """Send password reset email with reset link."""
        try:
            base_url = redirect_url or os.getenv("FRONTEND_BASE_URL") or "https://login.skreenit.com"
            reset_link = f"{base_url}/update-password.html?token={reset_token}"
            
            user = self.user_service.get_user_by_email(email)
            full_name = user.get('full_name', 'User') if user else 'User'
            
            result = await self.email_service.send_password_reset_email(
                to_email=email,
                full_name=full_name,
                reset_url=reset_link
            )
            
            if result.get("status") == "error":
                raise ValueError(result.get("message", "Failed to send password reset email"))
            
            logger.info(f"Password reset email sent to {email}")
            return {"ok": True, "message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            raise ValueError(str(e))

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Generate new access and refresh tokens using a valid refresh token."""
        try:
            # Verify the refresh token
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token payload")
            
            # Get user data
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Recompute onboarded for the active role so the refreshed token reflects the
            # current per-role onboarding state.
            user["onboarded"] = self.user_service.is_role_onboarded(user["id"], user["role"])

            # Generate new tokens
            tokens = self._generate_tokens(user)
            
            logger.info(f"Token refreshed for user {user_id}")
            return tokens
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")

# FastAPI Dependency Setup
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to inject the authenticated user into routes."""
    token = credentials.credentials
    auth_service = AuthService() # Corrected class name
    try:
        return auth_service.verify_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))