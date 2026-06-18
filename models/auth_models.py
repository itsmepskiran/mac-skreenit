# backend/models/auth_models.py

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


# ---------------------------------------------------------
# LOGIN REQUEST
# ---------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# REGISTER REQUEST
# ---------------------------------------------------------
class RegisterRequest(BaseModel):
    full_name: str  # ✅ FIXED: Changed from 'fullname' to 'full_name' (matches frontend)
    email: EmailStr
    password: str
    role: str  # "recruiter" or "candidate"

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# FORGOT PASSWORD REQUEST
# ---------------------------------------------------------
class PasswordResetRequest(BaseModel):
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# UPDATE PASSWORD REQUEST
# ---------------------------------------------------------
class PasswordUpdateRequest(BaseModel):
    token: str
    new_password: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# PASSWORD CHANGED NOTIFICATION (Optional)
# ---------------------------------------------------------
class PasswordChangedRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None # ✅ FIXED: Consistent naming

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# AUTH RESPONSE
# ---------------------------------------------------------
class AuthResponse(BaseModel):
    ok: bool = True
    user_id: str
    email: EmailStr
    role: str
    access_token: str
    refresh_token: Optional[str] = None