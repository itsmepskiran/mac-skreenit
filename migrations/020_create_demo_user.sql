-- ============================================================
-- Migration 020: Create Demo User with All-Access Premium Subscription
-- Demo credentials:  demouser@skreenit.com / Avng@1189
-- Roles:             candidate + recruiter (dual role)
-- Premium access:    all current plans + future features via demo_all_access plan
-- ============================================================

-- ── 1. Demo All-Access plan ──────────────────────────────────────────────────
-- service_type must be 'assessment_bundle' (existing ENUM value).
-- A dedicated check in subscription_service.py grants access to ANY feature key
-- when the user has an active subscription to this plan — future features included.

INSERT INTO pricing_plans (
    id, service_type, service_key, name, description,
    price_inr, currency, billing_cycle, trial_days, duration,
    features, is_active, sort_order, created_at, updated_at
) VALUES (
    'DEMO_ALL_ACCESS001',
    'assessment_bundle',
    'demo_all_access',
    'Demo – All Features Unlimited',
    'Internal demo plan. Grants unrestricted access to all current and future premium features.',
    0, 'INR', 'lifetime', 0, 'Lifetime',
    '["it_adv_coding","it_algorithmic_thinking","it_debugging","it_system_design_lite","it_system_design_pro","it_sql_pro","it_react_skills","it_js_pro","bpo_versant_pro","bpo_accent_neutral","bpo_cust_handling","bpo_objection_handling","bpo_chat_email_etiquette","bpo_call_quality","fin_reasoning","fin_awareness","fin_kyc_aml","fin_rm_simulation","fin_integrity","fin_insurance_product","sales_video_pitch","sales_objection_sim","sales_creativity","sales_digital_mcq","sales_lead_conv","sales_empathy","hc_terminology","hc_communication","hc_ethics","hc_case_handling","retail_video_test","retail_etiquette","retail_complaint","retail_pos_knowledge","mfg_safety","mfg_process","mfg_machine_op","mfg_qc","log_inventory","log_route","log_safety","log_documentation","tel_network","tel_troubleshoot","tel_tech_support","tel_field_safety","av_cabin_comm","av_safety","av_passenger","av_terminology","con_site_safety","con_blueprint","con_material","con_project_coord","edu_teaching_demo","edu_subject_knowledge","edu_classroom_mgmt","edu_delivery","unlimited_jobs","premium_screening","analytics","ai_resume_parsing","versant_assessment","general_assessment","interview_prep","typing_test","applicant_premium","recruiter_pro"]',
    1, 99, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- ── 2. Demo user ─────────────────────────────────────────────────────────────
-- Password: Avng@1189  (bcrypt hash below)
-- Primary role 'candidate'; roles JSON holds both so the user can switch.
-- is_premium=1 and subscription_status='active' satisfy the auth endpoint check.
-- user_metadata.access_level = 'demo_all' is read by subscription_service to
-- bypass the feature-access check for any key not yet in the features JSON.

INSERT INTO users (
    id, email, password_hash, full_name, phone,
    role, roles, location,
    email_confirmed_at, onboarded,
    is_premium, subscription_status,
    subscription_start_date, subscription_expiry_date,
    user_metadata, created_at, updated_at
) VALUES (
    'demo0001-0000-0000-0000-000000000001',
    'demouser@skreenit.com',
    '$2b$12$BFJ1CuKlvllTbQml.RsMOud4z8Tmw3cGrgil7CQBN1VBuifuoSDnG',
    'Skreenit Demo User',
    '+91 9000000000',
    'candidate',
    JSON_ARRAY('candidate', 'recruiter'),
    'Hyderabad, Telangana',
    NOW(), TRUE,
    1, 'active',
    NOW(), NULL,
    JSON_OBJECT('access_level', 'demo_all', 'is_demo', TRUE),
    NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    password_hash            = '$2b$12$BFJ1CuKlvllTbQml.RsMOud4z8Tmw3cGrgil7CQBN1VBuifuoSDnG',
    roles                    = JSON_ARRAY('candidate', 'recruiter'),
    is_premium               = 1,
    subscription_status      = 'active',
    subscription_expiry_date = NULL,
    onboarded                = TRUE,
    user_metadata            = JSON_OBJECT('access_level', 'demo_all', 'is_demo', TRUE),
    updated_at               = NOW();

-- Resolve actual user ID (handle pre-existing account with a different UUID)
SELECT @demo_uid := id FROM users WHERE email = 'demouser@skreenit.com' LIMIT 1;

-- ── 3. Subscription record ───────────────────────────────────────────────────
-- expiry_date = NULL  →  never expires
-- ON DUPLICATE KEY fires on the unique (user_id, plan_id) index

INSERT INTO user_subscriptions (
    id, user_id, plan_id, service_type, status,
    start_date, expiry_date, amount_paid,
    created_at, updated_at
) VALUES (
    'demo0001-0000-0000-0000-000000000003',
    @demo_uid,
    'DEMO_ALL_ACCESS001',
    'assessment_bundle',
    'active',
    NOW(), NULL, 0,
    NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    status      = 'active',
    expiry_date = NULL,
    updated_at  = NOW();

-- ── 4. Demo company (needed for recruiter onboarding check) ──────────────────
INSERT IGNORE INTO companies (
    id, name, description, website, location,
    company_display_id, recruiter_id,
    created_at, updated_at
) VALUES (
    'demo0001-0000-0000-0000-000000000002',
    'Skreenit Demo Company',
    'Demo company for Skreenit platform demonstration',
    'https://skreenit.com',
    'Hyderabad, Telangana',
    'SKREENIT-DEMO',
    @demo_uid,
    NOW(), NOW()
);

-- ── 5. Recruiter profile ─────────────────────────────────────────────────────
-- Onboarding check for recruiter: recruiter_profiles.company_id is set
-- AND companies.company_display_id is set (both satisfied above).

INSERT INTO recruiter_profiles (
    id, user_id, company_id, location,
    contact_name, contact_email,
    created_at, updated_at
) VALUES (
    'demo0001-0000-0000-0000-000000000004',
    @demo_uid,
    'demo0001-0000-0000-0000-000000000002',
    'Hyderabad, Telangana',
    'Skreenit Demo',
    'demouser@skreenit.com',
    NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    company_id = 'demo0001-0000-0000-0000-000000000002',
    updated_at = NOW();

-- ── 6. Candidate profile ─────────────────────────────────────────────────────
-- Onboarding check for candidate: candidate_profiles record exists
-- AND users.onboarded = TRUE (set in step 2).

INSERT INTO candidate_profiles (
    id, user_id, candidate_display_id,
    current_designation, experience_years,
    skills, current_city, current_state, current_country,
    created_at, updated_at
) VALUES (
    'demo0001-0000-0000-0000-000000000005',
    @demo_uid,
    'DEMO-CAND-001',
    'Full Stack Developer', 5,
    '["JavaScript","Python","React","Node.js","SQL","FastAPI"]',
    'Hyderabad', 'Telangana', 'India',
    NOW(), NOW()
)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- ── Verify ───────────────────────────────────────────────────────────────────
SELECT
    u.email,
    u.roles,
    u.is_premium,
    u.subscription_status,
    u.onboarded,
    JSON_UNQUOTE(JSON_EXTRACT(u.user_metadata, '$.access_level')) AS access_level,
    pp.name  AS plan_name,
    us.status AS sub_status,
    us.expiry_date
FROM users u
JOIN user_subscriptions us ON us.user_id = u.id
JOIN pricing_plans pp     ON pp.id = us.plan_id
WHERE u.email = 'demouser@skreenit.com';
