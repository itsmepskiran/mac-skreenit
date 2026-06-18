from fastapi import Request, HTTPException
from utils_others.rbac import has_permission

def ensure_permission(request: Request, required_perm: str):
    """
    Dependency/Helper to check if the current user has the required permission.
    Raises 403 if not authorized.
    """
    # 1. Get User from Request State (set by AuthMiddleware)
    user = getattr(request.state, "user", None)
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # 2. Extract Role (Default to 'candidate' if missing)
    # Custom auth stores role directly in user object
    role = user.get("role", "candidate").lower()
    
    # 3. Check Permission using RBAC Utility
    if not has_permission(role, required_perm):
        print(f"⛔ ACCESS DENIED: User Role '{role}' tried to access '{required_perm}'")
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied. Role '{role}' does not have permission '{required_perm}'."
        )

    # 4. Success
    return True