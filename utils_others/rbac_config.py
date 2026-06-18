# Role-Based Access Control Configuration

# The system expects a simple dictionary: "role": ["list", "of", "permissions"]
ROLES_PERMISSIONS = {
    "recruiter": [
        "jobs:view","jobs:create","jobs:edit","jobs:update","jobs:delete", "jobs:read",
        "profile:read","profile:edit","profile:update", "profile:view",
        "applications:read","applications:view","applications:edit","applications:delete","applications:analyze","application:create",
        "dashboard:read","notifications:create","analytics:view"
    ],
    "candidate": [
        "jobs:view","jobs:apply",
        "profile:read","profile:edit","profile:update","profile:avatar","profile:delete",
        "applications:create","applications:view","applications:read","applications:edit","applications:update","applications:delete",
        "dashboard:read","video:upload","notifications:view"
    ],
    "admin": ["*"]
}