from utils_others.rbac_config import ROLES_PERMISSIONS

def has_permission(role: str, permission: str) -> bool:
    """
    Checks if a given role has the required permission.
    
    Args:
        role (str): The user's role (e.g., 'admin', 'recruiter', 'candidate').
        permission (str): The permission string to check (e.g., 'jobs:create').
        
    Returns:
        bool: True if authorized, False otherwise.
    """
    if not role:
        return False
        
    role_key = role.lower()
    
    # Check if role exists in configuration
    if role_key not in ROLES_PERMISSIONS:
        return False
        
    allowed_perms = ROLES_PERMISSIONS[role_key]
    
    # Check for direct permission or wildcard
    return (permission in allowed_perms) or ("*" in allowed_perms)