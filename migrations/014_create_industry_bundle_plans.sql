-- Migration 014: Add industry full-access bundle plans to pricing_plans
-- Each bundle covers all assessments in that industry at a discounted price
-- Run manually: mysql -u root -p skreenit_db < 014_create_industry_bundle_plans.sql

-- Step 1: Ensure assessment_bundle is a valid service_type value
ALTER TABLE pricing_plans
MODIFY COLUMN service_type ENUM(
    'applicant_plan',
    'posting_plan',
    'general_plan',
    'training_plan',
    'recruiter_plan',
    'assessment_bundle'
) NOT NULL;

-- Step 2: Insert bundle plans
INSERT INTO pricing_plans (id, service_type, service_key, name, description, price_inr, currency, billing_cycle, trial_days, duration, features, is_active, sort_order)
VALUES
('SINBDLIT_001', 'assessment_bundle', 'bundle_it',            'IT & Software Full Access',            'All 8 IT & Software assessments: Coding, Algorithms, Debugging, System Design Lite, System Design Pro, SQL, React, JavaScript', 299, 'INR', 'one_time', 0, 'Lifetime', '["it_adv_coding","it_algorithmic_thinking","it_debugging","it_system_design_lite","it_system_design_pro","it_sql_pro","it_react_skills","it_js_pro"]', 1, 10),
('SINBDLBPO001', 'assessment_bundle', 'bundle_bpo',           'BPO / Customer Support Full Access',   'All 6 BPO assessments: Versant Pro, Accent Neutralization, Customer Handling, Objection Handling, Chat & Email Etiquette, Call Quality', 199, 'INR', 'one_time', 0, 'Lifetime', '["bpo_versant_pro","bpo_accent_neutral","bpo_cust_handling","bpo_objection_handling","bpo_chat_email_etiquette","bpo_call_quality"]', 1, 11),
('SINBDLFIN001', 'assessment_bundle', 'bundle_finance',       'Banking & Finance Full Access',        'All 6 Banking & Finance assessments: Financial Reasoning, Banking Awareness, KYC/AML, RM Simulation, Financial Integrity, Insurance Product', 149, 'INR', 'one_time', 0, 'Lifetime', '["fin_reasoning","fin_awareness","fin_kyc_aml","fin_rm_simulation","fin_integrity","fin_insurance_product"]', 1, 12),
('SINBDLSAL001', 'assessment_bundle', 'bundle_sales',         'Sales & Marketing Full Access',        'All 6 Sales & Marketing assessments: Sales Pitch, Objection Handling, Marketing Creativity, Digital Marketing MCQ, Lead Conversion, Customer Empathy', 169, 'INR', 'one_time', 0, 'Lifetime', '["sales_video_pitch","sales_objection_sim","sales_creativity","sales_digital_mcq","sales_lead_conv","sales_empathy"]', 1, 13),
('SINBDLHC_001', 'assessment_bundle', 'bundle_healthcare',    'Healthcare Full Access',               'All 4 Healthcare assessments: Medical Terminology, Patient Communication, Healthcare Ethics, Case Handling', 119, 'INR', 'one_time', 0, 'Lifetime', '["hc_terminology","hc_communication","hc_ethics","hc_case_handling"]', 1, 14),
('SINBDLRET001', 'assessment_bundle', 'bundle_retail',        'Retail & Hospitality Full Access',     'All 4 Retail & Hospitality assessments: Customer Interaction Video, Service Etiquette, Complaint Handling, POS Knowledge', 119, 'INR', 'one_time', 0, 'Lifetime', '["retail_video_test","retail_etiquette","retail_complaint","retail_pos_knowledge"]', 1, 15),
('SINBDLMFG001', 'assessment_bundle', 'bundle_manufacturing', 'Manufacturing Full Access',            'All 4 Manufacturing assessments: Safety Compliance, Process Understanding, Machine Operation, Quality Control', 99, 'INR', 'one_time', 0, 'Lifetime', '["mfg_safety","mfg_process","mfg_machine_op","mfg_qc"]', 1, 16),
('SINBDLLOG001', 'assessment_bundle', 'bundle_logistics',     'Logistics & Supply Chain Full Access', 'All 4 Logistics assessments: Inventory Management, Route Optimization, Warehouse Safety, Documentation Accuracy', 99, 'INR', 'one_time', 0, 'Lifetime', '["log_inventory","log_route","log_safety","log_documentation"]', 1, 17),
('SINBDLTEL001', 'assessment_bundle', 'bundle_telecom',       'Telecom Full Access',                  'All 4 Telecom assessments: Network Basics, Troubleshooting Simulation, Customer Tech Support, Field Operations Safety', 99, 'INR', 'one_time', 0, 'Lifetime', '["tel_network","tel_troubleshoot","tel_tech_support","tel_field_safety"]', 1, 18),
('SINBDLAV_001', 'assessment_bundle', 'bundle_aviation',      'Aviation Full Access',                 'All 4 Aviation assessments: Cabin Crew Communication, Safety Protocol, Passenger Handling, Terminology', 119, 'INR', 'one_time', 0, 'Lifetime', '["av_cabin_comm","av_safety","av_passenger","av_terminology"]', 1, 19),
('SINBDLCON001', 'assessment_bundle', 'bundle_construction',  'Construction Full Access',             'All 4 Construction assessments: Site Safety, Blueprint Reading, Material Knowledge, Project Coordination', 99, 'INR', 'one_time', 0, 'Lifetime', '["con_site_safety","con_blueprint","con_material","con_project_coord"]', 1, 20),
('SINBDLEDU001', 'assessment_bundle', 'bundle_education',     'Education & Training Full Access',     'All 4 Education assessments: Teaching Demo Video, Subject Knowledge, Classroom Management, Communication & Delivery', 119, 'INR', 'one_time', 0, 'Lifetime', '["edu_teaching_demo","edu_subject_knowledge","edu_classroom_mgmt","edu_delivery"]', 1, 21)
ON DUPLICATE KEY UPDATE updated_at = NOW();
