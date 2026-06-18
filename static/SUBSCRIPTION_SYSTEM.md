# Subscription System - Complete Reference

## Architecture Overview

### 3-Table Design

The subscription system uses a hybrid 3-table approach:

**Users table** — 6 extra columns for fast, join-free premium checks:
| Column | Type | Purpose |
|--------|------|---------|
| `subscription_plan_id` | FK → pricing_plans | Current active plan |
| `subscription_status` | ENUM | free / active / trial / cancelled / expired |
| `subscription_start_date` | DATETIME | When subscription began |
| `subscription_expiry_date` | DATETIME | When it expires |
| `subscription_trial_end_date` | DATETIME | Trial-specific end date |
| `is_premium` | BOOLEAN | Fast flag — no JOIN needed |

```sql
ALTER TABLE users ADD COLUMN (
  `subscription_plan_id` VARCHAR(36) DEFAULT NULL,
  `subscription_status` ENUM('free','active','trial','cancelled','expired') DEFAULT 'free',
  `subscription_start_date` DATETIME DEFAULT NULL,
  `subscription_expiry_date` DATETIME DEFAULT NULL,
  `subscription_trial_end_date` DATETIME DEFAULT NULL,
  `is_premium` BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (`subscription_plan_id`) REFERENCES `pricing_plans`(`id`)
);
ALTER TABLE users ADD INDEX idx_is_premium (is_premium);
ALTER TABLE users ADD INDEX idx_subscription_status (subscription_status);
ALTER TABLE users ADD INDEX idx_subscription_expiry (subscription_expiry_date);
```

**user_subscriptions** — Full audit trail, supports multiple concurrent subscriptions:
```sql
CREATE TABLE user_subscriptions (
  `id` VARCHAR(36) PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL,
  `plan_id` VARCHAR(36) NOT NULL,
  `service_type` VARCHAR(50) NOT NULL,
  `status` ENUM('pending','active','trial','cancelled','expired') NOT NULL,
  `start_date` DATETIME DEFAULT NULL,          -- NULL for pending state
  `expiry_date` DATETIME DEFAULT NULL,
  `trial_end_date` DATETIME DEFAULT NULL,
  `payment_method` VARCHAR(50),
  `transaction_id` VARCHAR(100),
  `amount_paid` DECIMAL(10,2) DEFAULT 0,
  `reason_cancelled` TEXT,
  `cancelled_at` DATETIME,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`),
  FOREIGN KEY (`plan_id`) REFERENCES `pricing_plans`(`id`),
  INDEX (`user_id`, `service_type`),
  INDEX (`status`, `expiry_date`)
);
```

**user_subscription_features** — Granular feature access per subscription:
```sql
CREATE TABLE user_subscription_features (
  `id` VARCHAR(36) PRIMARY KEY,
  `subscription_id` VARCHAR(36) NOT NULL,
  `feature_key` VARCHAR(100) NOT NULL,
  `enabled` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`subscription_id`) REFERENCES `user_subscriptions`(`id`),
  UNIQUE KEY (`subscription_id`, `feature_key`)
);
```

**user_plan_usage** — Tracks remaining count for per-action features:
```sql
CREATE TABLE IF NOT EXISTS user_plan_usage (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `subscription_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `feature_key` VARCHAR(100) NOT NULL,
  `plan_id` VARCHAR(36) NOT NULL,
  `initial_count` INT DEFAULT NULL,
  `remaining_count` INT DEFAULT NULL,
  `usage_logs` JSON DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `expires_at` DATETIME DEFAULT NULL,
  INDEX idx_user_feature (user_id, feature_key),
  INDEX idx_subscription_id (subscription_id),
  INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Data Flow

### Purchase Flow
```
User clicks "Upgrade"
    ↓
POST /api/v1/subscription/create  { plan_id }
    ↓
Backend inserts user_subscriptions with status='pending', start_date=NULL
    ↓
Frontend opens Razorpay modal with subscription_id
    ↓
User pays → Razorpay webhook → POST /api/v1/subscription/webhook
    ↓
Backend:
  - Updates subscription: status='active', populates dates
  - Inserts user_subscription_features rows using plan.service_key
  - Inserts user_plan_usage rows (for counted features)
  - Updates users: is_premium=TRUE, subscription_status='active'
    ↓
PREMIUM UNLOCKED
```

### Access Check Flow
```
User visits premium feature
    ↓
Frontend: GET /user/subscription-status
    ↓
Backend: check users.is_premium AND users.subscription_expiry_date > NOW()
    ↓
Returns: { is_premium, features: [...], expiry_date }
    ↓
Show or lock feature
```

### Expiry Flow
```
Daily cronjob: check_and_handle_expiry()
    ↓
SELECT FROM user_subscriptions WHERE status IN ('active','trial') AND expiry_date < NOW()
    ↓
UPDATE user_subscriptions.status = 'expired'
UPDATE users SET is_premium=FALSE, subscription_status='expired'
    ↓
Premium locked; renewal banner shown on next login
```

### State Transitions
```
FREE → TRIAL (7-day) → ACTIVE (paid) → EXPIRED → (renew) → ACTIVE
                                                → (ignore) → FREE
                      → CANCELLED (admin revoke)
```

---

## Subscription Lifecycle

### Pending State (on checkout)
```python
subscription_payload = {
    "id": subscription_id,
    "user_id": user_id,
    "plan_id": plan_id,
    "service_type": plan.get("service_type"),
    "status": "pending",
    "start_date": None,       # NULL until payment confirmed
    "expiry_date": None,
    "trial_end_date": None,
    "payment_method": None,
    "transaction_id": None,
    "amount_paid": 0,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
}
mysql_service.insert_record("user_subscriptions", subscription_payload)
```

### Active State (after payment webhook)
```python
start_date = datetime.now()
expiry_date = start_date + timedelta(days=duration_days)
trial_end_date = start_date + timedelta(days=trial_days) if trial_days > 0 else None

update_payload = {
    "status": "trial" if trial_days > 0 else "active",
    "start_date": start_date,
    "expiry_date": expiry_date,
    "trial_end_date": trial_end_date,
    "payment_method": "razorpay",
    "transaction_id": txn_id,
    "amount_paid": amount,
}
mysql_service.update_record("user_subscriptions", update_payload, {"id": subscription_id})
```

---

## Feature Extraction — Critical Logic

The `features` field in `pricing_plans` was historically stored in different formats. **Use `service_key` as the authoritative feature identifier**, not the `features` JSON field:

```python
def _extract_feature_keys(plan: dict) -> list:
    """Use service_key from the plan — NOT the features JSON descriptions."""
    service_key = plan.get("service_key")  # e.g., "bpo_versant_pro"
    if service_key:
        return [service_key]
    return []
```

This was fixed in Migration 009 which also cleaned 58 pricing plans that had features fields corrupted with a ` DOCX` suffix.

---

## Issues Found & Fixed (History)

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| 1 | 58 pricing plans had ` DOCX` suffix in features field, breaking JSON parsing | Migration 009: removed suffix | ✅ Fixed |
| 2 | Feature extraction used description text instead of service_key | Updated `_extract_feature_keys()` to use `service_key` | ✅ Fixed |
| 3 | `get_subscription_status()` only checked `status == "active"`, missing "trial" | Changed to `status.in_(["active", "trial"])` in subscription_service.py | ✅ Fixed |
| 4 | `start_date` column was NOT NULL, causing 500 on pending subscription creation | Migration 008: made `start_date` nullable | ✅ Fixed |
| 5 | `user_plan_usage` table missing — crashed `get_subscription_status()` | Migration 010: created table (without FK due to constraint issues) | ✅ Fixed |
| 6 | `user_subscription_features` table missing | Migration 011: created table | ✅ Fixed |

### Migration Chain
```
006_add_subscription_system.sql         – Initial schema
007_user_subscriptions_simple.sql       – Simplified tables
008_fix_user_subscriptions_nullable_dates.sql  – Fix NOT NULL on start_date
009_fix_corrupted_plan_features.sql     – Remove " DOCX" suffix from 58 plans
010_create_user_plan_usage_table.sql    – Create user_plan_usage
011_create_user_subscription_features_table.sql – Create user_subscription_features
```

---

## API Endpoints

### User Endpoints
```
GET  /api/v1/user/subscription-status      → { is_premium, features, expiry_date }
GET  /api/v1/user/subscription-details     → { plan, subscription, all_subscriptions }
POST /api/v1/subscription/create           → { subscription_id, plan_id, amount, ... }
POST /api/v1/subscription/webhook          → Razorpay payment confirmation
```

### Admin Endpoints
```
PUT  /admin/users/{user_id}/subscription
POST /admin/subscription/manual-grant      → { user_id, plan_id, days }
POST /admin/subscription/revoke            → { subscription_id, reason }
POST /admin/subscriptions/check-expiry     → Trigger expiry check
```

### Response Format: GET /user/subscription-status
```json
{
  "is_premium": true,
  "subscription_status": "active",
  "expiry_date": "2024-12-31T23:59:59",
  "features": ["bpo_versant_pro", "general_assessment"],
  "subscription": {
    "plan_id": "plan_applicant_premium_monthly",
    "status": "active",
    "start_date": "2024-05-28T10:30:00",
    "expiry_date": "2024-06-28T10:30:00",
    "trial_end_date": null
  }
}
```

---

## Backend Service Methods

```python
class SubscriptionService:
    def grant_subscription(self, user_id, plan_id, days_duration, is_trial=False)
    def revoke_subscription(self, subscription_id, reason, revoked_by)
    def get_subscription_status(self, user_id) → { is_premium, features, ... }
    def check_feature_access(self, user_id, feature_key) → bool
    def get_available_features(self, user_id, feature_key) → { available, remaining_count, expires_at }
    def consume_feature(self, user_id, feature_key) → { ok, remaining }
    def check_and_handle_expiry(self)  # Daily cronjob
```

---

## Feature Access Control Examples

```python
# Check premium access
@router.get("/premium/versant-questions")
async def get_versant_questions(request: Request):
    user_id = request.user["id"]
    if not subscription_service.check_feature_access(user_id, "bpo_versant_pro"):
        raise HTTPException(403, "Premium feature — upgrade required")
    return get_versant_questions_from_db()

# Check subscription status
status = subscription_service.get_subscription_status(user_id)
if not status['is_premium']:
    raise HTTPException(403, "Premium subscription required")
```

---

## Frontend Troubleshooting

**Symptom:** Subscriptions created in DB but frontend shows failure.

**Diagnostic steps:**
1. Open DevTools → Network tab
2. Find `POST /api/v1/subscription/create`
3. Check response is `{"ok": true, "data": {"subscription_id": "sub_..."}}`
4. Check Console for JS errors

**Common causes:**
- `subscription_id` not extracted from `data.data.subscription_id` (check property path)
- Razorpay script not loaded (`<script src="https://checkout.razorpay.com/v1/checkout.js">`)
- JWT token missing or expired from `Authorization` header
- CORS error — check `Access-Control-Allow-Origin` in response headers

**Correct frontend pattern:**
```javascript
async function createSubscription(planId) {
    const response = await fetch('/api/v1/subscription/create', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ plan_id: planId })
    });
    const data = await response.json();
    if (data.ok && data.data.subscription_id) {
        initializeRazorpay(data.data);  // pass the whole data object
    }
}
```

---

## Useful SQL Queries

```sql
-- Check if user has active subscription
SELECT u.*, p.name as plan_name FROM users u
LEFT JOIN user_subscriptions us ON u.id = us.user_id
LEFT JOIN pricing_plans p ON us.plan_id = p.id
WHERE u.id = ?
  AND us.status IN ('active', 'trial')
  AND NOW() < us.expiry_date;

-- Find subscriptions expiring in 7 days
SELECT u.email, p.name, us.expiry_date FROM user_subscriptions us
JOIN users u ON u.id = us.user_id
JOIN pricing_plans p ON us.plan_id = p.id
WHERE us.status = 'active'
  AND us.expiry_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY);

-- List recent pending subscriptions
SELECT id, user_id, plan_id, status, created_at
FROM user_subscriptions
WHERE status = 'pending'
ORDER BY created_at DESC LIMIT 10;

-- Check user plan usage remaining
SELECT feature_key, remaining_count, expires_at
FROM user_plan_usage
WHERE user_id = ? AND remaining_count > 0 AND (expires_at IS NULL OR expires_at > NOW());
```

---

## Implementation Checklist

- [x] Migration 008 — `start_date` nullable
- [x] Migration 009 — corrupted plan features cleaned
- [x] Migration 010 — `user_plan_usage` table created
- [x] Migration 011 — `user_subscription_features` table created
- [x] `routers/subscription.py` — `_extract_feature_keys()` uses service_key
- [x] `services/subscription_service.py` — includes "trial" in status check
- [ ] End-to-end subscription → booking flow tested
- [ ] Booking endpoints verified to check subscription status
- [ ] Daily cronjob for expiry checks configured
- [ ] Admin subscription management UI
- [ ] Email notifications for expiring subscriptions
