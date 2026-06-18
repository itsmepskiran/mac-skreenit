-- Migration 016: Add assessment display columns to pricing_plans
-- Enables fully dynamic assessments via the admin UI without code changes.
-- Run manually: mysql -u root -p skreenit_db < 016_add_assessment_display_columns.sql

ALTER TABLE pricing_plans
  ADD COLUMN IF NOT EXISTS assessment_format VARCHAR(50)   DEFAULT NULL  COMMENT 'voice_test | voice_scenario | text_writing | coding_test | mcq',
  ADD COLUMN IF NOT EXISTS assessment_content LONGTEXT      DEFAULT NULL  COMMENT 'JSON array of questions/sections for this assessment',
  ADD COLUMN IF NOT EXISTS icon_class         VARCHAR(100)  DEFAULT NULL  COMMENT 'FontAwesome icon class e.g. fas fa-code',
  ADD COLUMN IF NOT EXISTS icon_color         VARCHAR(20)   DEFAULT NULL  COMMENT 'CSS color e.g. #dc2626',
  ADD COLUMN IF NOT EXISTS icon_bg            VARCHAR(30)   DEFAULT NULL  COMMENT 'CSS background e.g. #fee2e2',
  ADD COLUMN IF NOT EXISTS industry_key       VARCHAR(50)   DEFAULT NULL  COMMENT 'Industry slug e.g. it, bpo, finance',
  ADD COLUMN IF NOT EXISTS industry_label     VARCHAR(100)  DEFAULT NULL  COMMENT 'Human-readable industry e.g. IT & Software',
  ADD COLUMN IF NOT EXISTS skills_measured    TEXT          DEFAULT NULL  COMMENT 'Comma-separated skills tested';

-- ──────────────────────────────────────────────────────────
-- UPDATE 9 free (general_plan) assessments with icon data
-- ──────────────────────────────────────────────────────────
UPDATE pricing_plans SET
  assessment_format = 'voice_scenario',
  icon_class = 'fas fa-video',
  icon_color = '#0284c7',
  icon_bg    = '#dbeafe',
  skills_measured = 'Communication, Confidence, Presentation'
WHERE service_key = 'gen_video_intro';

UPDATE pricing_plans SET
  assessment_format = 'coding_test',
  icon_class = 'fas fa-code',
  icon_color = '#16a34a',
  icon_bg    = '#dcfce7',
  skills_measured = 'Programming Logic, Problem Solving, Algorithms'
WHERE service_key = 'gen_coding_basic';

UPDATE pricing_plans SET
  assessment_format = 'text_writing',
  icon_class = 'fas fa-keyboard',
  icon_color = '#7e22ce',
  icon_bg    = '#f3e8ff',
  skills_measured = 'Typing Speed, Accuracy, Data Entry'
WHERE service_key = 'gen_typing';

UPDATE pricing_plans SET
  assessment_format = 'mcq',
  icon_class = 'fas fa-brain',
  icon_color = '#d97706',
  icon_bg    = '#fef3c7',
  skills_measured = 'Numerical Reasoning, Logical Thinking, Pattern Recognition'
WHERE service_key = 'gen_aptitude';

UPDATE pricing_plans SET
  assessment_format = 'mcq',
  icon_class = 'fas fa-user-check',
  icon_color = '#db2777',
  icon_bg    = '#fce7f3',
  skills_measured = 'Behavioral Traits, Workplace Ethics, Situational Judgment'
WHERE service_key = 'gen_psychometric';

UPDATE pricing_plans SET
  assessment_format = 'mcq',
  icon_class = 'fas fa-search-plus',
  icon_color = '#0891b2',
  icon_bg    = '#cffafe',
  skills_measured = 'Data Accuracy, Error Detection, Speed Math'
WHERE service_key = 'gen_attention_detail';

UPDATE pricing_plans SET
  assessment_format = 'mcq',
  icon_class = 'fas fa-shield-alt',
  icon_color = '#475569',
  icon_bg    = '#f1f5f9',
  skills_measured = 'English Grammar, Cyber Security Awareness'
WHERE service_key = 'gen_english_prof';

UPDATE pricing_plans SET
  assessment_format = 'text_writing',
  icon_class = 'fas fa-file-alt',
  icon_color = '#0891b2',
  icon_bg    = '#cffafe',
  skills_measured = 'Professional Writing, CV Crafting, Achievement Statements'
WHERE service_key = 'gen_resume_quiz';

UPDATE pricing_plans SET
  assessment_format = 'mcq',
  icon_class = 'fas fa-user-tie',
  icon_color = '#7c3aed',
  icon_bg    = '#ede9fe',
  skills_measured = 'Interview Etiquette, STAR Method, Professional Conduct'
WHERE service_key = 'gen_interview_prep';

-- ──────────────────────────────────────────────────────────
-- Verify
-- ──────────────────────────────────────────────────────────
SELECT id, service_key, assessment_format, icon_class, icon_color
FROM pricing_plans
WHERE service_type IN ('general_plan', 'assessment_bundle')
ORDER BY service_type, sort_order;
