# Pricing System Guide

## Overview

All monetization lives in the **single `pricing_plans` table** and supports three models:

| Model | Example | billing_cycle | duration |
|-------|---------|---------------|----------|
| Subscription (recurring) | ₹299/month premium | `monthly` | `1 Month` |
| Per-action (one-time) | ₹49 per report | `one_time` | `One-Time` |
| Bundle/pack | ₹99 for 5 assessments | `one_time` | `5 Assessments` |

**No code changes needed to add new plans** — add a row to `pricing_plans` via SQL, API, or admin UI.

---

## Service Types

Currently defined:
- `training` — training course plans
- `recruiter_subscription` — recurring recruiter plans
- `applicant_plan` — recurring applicant/candidate plans
- `job_posting` — job posting bundles
- `feature_addon` — per-action features for either user type

---

## Adding Plans

### Method 1: Admin UI (fastest)
Go to `/assets/pricing.html` → click "+ Create Plan" → fill the form.

### Method 2: SQL INSERT
```sql
INSERT INTO pricing_plans (
  id, service_type, service_key, name, description,
  price_inr, currency, billing_cycle, trial_days,
  duration, features, is_active, sort_order
) VALUES (
  'plan_report_detailed_49', 'feature_addon', 'detailed_report',
  'Detailed Analysis Report', 'AI-powered profile analysis',
  49, 'INR', 'one_time', 0,
  'One-Time', '["detailed_report"]',
  1, 1
);
```

### Method 3: API
```bash
curl -X POST https://your-domain/admin/pricing \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "feature_addon",
    "service_key": "detailed_report",
    "name": "Detailed Analysis Report",
    "price_inr": 49,
    "billing_cycle": "one_time",
    "duration": "One-Time Report",
    "features": ["detailed_report", "ai_insights"]
  }'
```

---

## Candidate Per-Action Plans (Reference SQL)

```sql
-- Detailed Analysis Reports
INSERT INTO pricing_plans VALUES 
('plan_report_basic_29', 'feature_addon', 'detailed_report_basic', 'Basic Analysis Report', 'Quick profile analysis', 29, 'INR', 'one_time', 0, 'One-Time', '["basic_report"]', 1, 1),
('plan_report_premium_49', 'feature_addon', 'detailed_report_premium', 'Premium Analysis Report', 'Comprehensive AI-powered analysis', 49, 'INR', 'one_time', 0, 'One-Time', '["detailed_report", "ai_insights"]', 1, 2),
('plan_report_pro_99', 'feature_addon', 'detailed_report_pro', '5 Reports Bundle', 'Get 5 detailed reports', 99, 'INR', 'one_time', 0, 'One-Time', '["detailed_report_x5"]', 1, 3);

-- Versant Assessments
INSERT INTO pricing_plans VALUES 
('plan_versant_single_29', 'feature_addon', 'versant_single', 'Single Versant Assessment', 'Take 1 Versant test', 29, 'INR', 'one_time', 0, 'One-Time', '["versant"]', 1, 4),
('plan_versant_5pack_99', 'feature_addon', 'versant_5pack', 'Versant 5-Pack', '5 Versant assessments (save ₹46)', 99, 'INR', 'one_time', 0, 'One-Time', '["versant_x5"]', 1, 5);

-- Other Assessments
INSERT INTO pricing_plans VALUES 
('plan_general_assess_19', 'feature_addon', 'general_assessment_single', 'General Assessment', 'General aptitude test', 19, 'INR', 'one_time', 0, 'One-Time', '["general_assessment"]', 1, 6),
('plan_tech_assess_39', 'feature_addon', 'tech_assessment_single', 'Technical Assessment', 'Coding/tech skills test', 39, 'INR', 'one_time', 0, 'One-Time', '["tech_assessment"]', 1, 7),
('plan_typing_test_9', 'feature_addon', 'typing_single', 'Typing Speed Test', 'Single typing test', 9, 'INR', 'one_time', 0, 'One-Time', '["typing_test"]', 1, 8);

-- Mock Interviews
INSERT INTO pricing_plans VALUES 
('plan_interview_prep_49', 'feature_addon', 'mock_interview_single', 'Single Mock Interview', '1 mock interview with AI feedback', 49, 'INR', 'one_time', 0, 'One-Time', '["mock_interview", "ai_feedback"]', 1, 10),
('plan_interview_prep_5pack_199', 'feature_addon', 'mock_interview_5pack', 'Interview Prep 5-Pack', '5 mock interviews', 199, 'INR', 'one_time', 0, 'One-Time', '["mock_interview_x5"]', 1, 11);
```

---

## Recruiter Per-Action Plans (Reference SQL)

```sql
-- Job Postings
INSERT INTO pricing_plans VALUES 
('plan_jobs_5_49', 'job_posting', 'jobs_bundle_5', '5 Job Postings', 'Post 5 jobs (valid 30 days)', 49, 'INR', 'one_time', 0, '30 Days', '["job_postings_5"]', 1, 1),
('plan_jobs_10_99', 'job_posting', 'jobs_bundle_10', '10 Job Postings', 'Post 10 jobs (valid 30 days)', 99, 'INR', 'one_time', 0, '30 Days', '["job_postings_10"]', 1, 2),
('plan_jobs_20_179', 'job_posting', 'jobs_bundle_20', '20 Job Postings', 'Post 20 jobs (valid 30 days)', 179, 'INR', 'one_time', 0, '30 Days', '["job_postings_20"]', 1, 3),
('plan_jobs_unlimited_499', 'job_posting', 'jobs_unlimited', 'Unlimited Postings (30 Days)', 'Unlimited job postings for 1 month', 499, 'INR', 'one_time', 0, '30 Days', '["job_postings_unlimited"]', 1, 4);

-- AI Resume Parsing
INSERT INTO pricing_plans VALUES 
('plan_parsing_10_49', 'feature_addon', 'ai_parsing_10', 'AI Resume Parsing (10)', 'Parse 10 resumes with AI', 49, 'INR', 'one_time', 0, 'One-Time', '["ai_parsing_x10"]', 1, 5),
('plan_parsing_50_199', 'feature_addon', 'ai_parsing_50', 'AI Resume Parsing (50)', 'Parse 50 resumes with AI', 199, 'INR', 'one_time', 0, 'One-Time', '["ai_parsing_x50"]', 1, 6),
('plan_parsing_unlimited_999', 'feature_addon', 'ai_parsing_unlimited', 'AI Parsing Unlimited (30 days)', 'Unlimited parsing for 1 month', 999, 'INR', 'one_time', 0, '30 Days', '["ai_parsing_unlimited"]', 1, 7);

-- Messaging & Video Screening
INSERT INTO pricing_plans VALUES 
('plan_messages_100_29', 'feature_addon', 'bulk_messages_100', 'Bulk Messages (100)', 'Send 100 messages to candidates', 29, 'INR', 'one_time', 0, 'One-Time', '["bulk_messages_100"]', 1, 8),
('plan_messages_500_99', 'feature_addon', 'bulk_messages_500', 'Bulk Messages (500)', 'Send 500 messages to candidates', 99, 'INR', 'one_time', 0, 'One-Time', '["bulk_messages_500"]', 1, 9),
('plan_video_screening_10_49', 'feature_addon', 'video_screening_10', 'Video Screening (10)', 'Review 10 video responses', 49, 'INR', 'one_time', 0, 'One-Time', '["video_screening_x10"]', 1, 10);
```

---

## Usage Tracking for Counted Features

When a user buys a bundle (e.g., "5 Versant assessments"), insert a `user_plan_usage` row:

```
User buys "Versant 5-Pack" (₹99)
    ↓
INSERT user_plan_usage:
  subscription_id: sub_123
  feature_key: versant_x5
  initial_count: 5
  remaining_count: 5
  expires_at: NOW + 30 days
    ↓
User takes first assessment
    ↓
UPDATE user_plan_usage SET remaining_count = 4
    ↓
When remaining_count = 0 → "Buy more assessments"
```

### Service methods
```python
# Check how many uses remain
available = subscription_service.get_available_features(user_id, "versant_x5")
# Returns: { available: True, remaining_count: 4, expires_at: "..." }

# Consume one use
result = subscription_service.consume_feature(user_id, "versant_x5")
# Returns: { ok: True, remaining: 3 }
```

### API endpoints for per-action features
```
GET  /user/feature/{feature_key}/available  → { available, remaining_count, expires_at }
POST /user/feature/{feature_key}/consume    → { ok, remaining }
GET  /user/available-features               → [ { feature_key, remaining, expires_at }, ... ]
```

---

## Quick Price Reference

### Candidates
| Feature | Price | Type |
|---------|-------|------|
| Detailed Analysis Report | ₹49 | One-time |
| Basic Report | ₹29 | One-time |
| 5-Report Bundle | ₹99 | One-time |
| Versant Assessment (single) | ₹29 | One-time |
| Versant 5-Pack | ₹99 | One-time |
| General Assessment | ₹19 | One-time |
| Technical Assessment | ₹39 | One-time |
| Typing Speed Test | ₹9 | One-time |
| Mock Interview | ₹49 | One-time |
| Interview Prep 5-Pack | ₹199 | One-time |

### Recruiters
| Feature | Price | Type |
|---------|-------|------|
| 5 Job Postings | ₹49 | 30 days |
| 10 Job Postings | ₹99 | 30 days |
| 20 Job Postings | ₹179 | 30 days |
| Unlimited Postings | ₹499 | 30 days |
| AI Resume Parsing (10) | ₹49 | One-time |
| AI Resume Parsing (50) | ₹199 | One-time |
| Bulk Messages (100) | ₹29 | One-time |
| Bulk Messages (500) | ₹99 | One-time |
| Video Screening (10) | ₹49 | One-time |

---

## FAQ

**Q: Can I add more plans later?**  
A: Yes — add via SQL, API, or admin UI. Zero downtime, no code changes.

**Q: Can users buy multiple features simultaneously?**  
A: Yes. A user can have an active recruiter_subscription PLUS 10 job postings PLUS AI parsing credits all at once.

**Q: How do I change a plan's price?**  
A: `UPDATE pricing_plans SET price_inr = 99 WHERE id = 'plan_id';`

**Q: How do I disable a plan?**  
A: `UPDATE pricing_plans SET is_active = 0 WHERE id = 'plan_id';`
