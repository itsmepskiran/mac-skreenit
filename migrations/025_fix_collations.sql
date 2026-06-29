-- ============================================================
-- Migration 025: Standardise table collations to utf8mb4_unicode_ci
-- Root cause: pricing_plans, user_subscriptions, and related tables
-- were created with utf8mb4_general_ci while users table uses
-- utf8mb4_unicode_ci. JOINs between them throw:
--   "Illegal mix of collations ... for operation '='"
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

ALTER TABLE `pricing_plans`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `user_subscriptions`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `user_plan_usage`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `training_registrations`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `college_training_registrations`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `corporate_training_registrations`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- seminar tables (may not exist on all environments; safe to ignore errors)
ALTER TABLE `seminars`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `seminar_registrations`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE `seminar_enquiries`
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
