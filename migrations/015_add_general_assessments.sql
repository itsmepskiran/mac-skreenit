-- Migration 015: Add 7 free general assessments to pricing_plans
-- These assessments are free for all authenticated users (service_type = 'general_plan', price_inr = 0)
-- Run manually: mysql -u root -p skreenit_db < 015_add_general_assessments.sql

INSERT INTO pricing_plans (id, service_type, service_key, name, description, price_inr, currency, billing_cycle, trial_days, duration, features, is_active, sort_order)
VALUES
('SINGEN26060401', 'general_plan', 'gen_video_intro',      'Introduction Test',                        'One-way video introduction: present yourself confidently and clearly',                             0, 'INR', 'free', 0, 'Lifetime', '["gen_video_intro"]',      1, 1),
('SINGEN26060402', 'general_plan', 'gen_coding_basic',     'Basic Coding Challenge',                   'Entry-level coding problems testing fundamental programming logic. No copy-paste allowed.',       0, 'INR', 'free', 0, 'Lifetime', '["gen_coding_basic"]',     1, 2),
('SINGEN26060403', 'general_plan', 'gen_typing',           'Typing Test',                              'Measure typing speed and accuracy with real-world text passages.',                               0, 'INR', 'free', 0, 'Lifetime', '["gen_typing"]',           1, 3),
('SINGEN26060404', 'general_plan', 'gen_aptitude',         'Aptitude & Logical Reasoning',             'Numerical and logical reasoning questions for cognitive ability screening.',                      0, 'INR', 'free', 0, 'Lifetime', '["gen_aptitude"]',         1, 4),
('SINGEN26060405', 'general_plan', 'gen_psychometric',     'Psychometric Test',                        'Situational judgment test assessing workplace behavioral traits and work ethic.',                 0, 'INR', 'free', 0, 'Lifetime', '["gen_psychometric"]',     1, 5),
('SINGEN26060406', 'general_plan', 'gen_attention_detail', 'Attention to Detail & Speed Math',         'Tests data accuracy, error spotting, and basic arithmetic speed under time pressure.',           0, 'INR', 'free', 0, 'Lifetime', '["gen_attention_detail"]', 1, 6),
('SINGEN26060407', 'general_plan', 'gen_english_prof',     'English & Cyber Security Awareness',       'Tests English grammar proficiency and basic cyber security awareness knowledge.',                 0, 'INR', 'free', 0, 'Lifetime', '["gen_english_prof"]',     1, 7),
('SINGEN26060408', 'general_plan', 'gen_resume_quiz',      'Resume Writing Self-Assessment',            'Practise writing professional summaries and achievement statements for your CV.',                0, 'INR', 'free', 0, 'Lifetime', '["gen_resume_quiz"]',      1, 8),
('SINGEN26060409', 'general_plan', 'gen_interview_prep',   'Interview Readiness Quiz',                  'Test your knowledge of interview etiquette, STAR method, and professional conduct.',             0, 'INR', 'free', 0, 'Lifetime', '["gen_interview_prep"]',   1, 9)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- Verify
SELECT id, service_key, name, price_inr, service_type FROM pricing_plans
WHERE service_type = 'general_plan'
ORDER BY sort_order;
