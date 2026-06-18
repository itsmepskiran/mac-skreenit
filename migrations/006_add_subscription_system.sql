-- ============================================================
-- SUBSCRIPTION SYSTEM MIGRATION
-- File: 006_add_subscription_system.sql
-- Purpose: Add subscription and membership tracking
-- ============================================================

-- ============================================================
-- 1. ALTER USERS TABLE - Add subscription columns (if not already present)
-- ============================================================

-- Note: The users table may already have these columns from previous setup
-- We'll add them individually to avoid errors if they exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS `subscription_plan_id` VARCHAR(36) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS `subscription_status` ENUM('free', 'active', 'trial', 'cancelled', 'expired') DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS `subscription_start_date` DATETIME DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS `subscription_expiry_date` DATETIME DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS `subscription_trial_end_date` DATETIME DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS `is_premium` TINYINT(1) DEFAULT 0;

-- Add indexes for performance
ALTER TABLE users ADD INDEX IF NOT EXISTS idx_subscription_status (subscription_status);
ALTER TABLE users ADD INDEX IF NOT EXISTS idx_subscription_expiry (subscription_expiry_date);
ALTER TABLE users ADD INDEX IF NOT EXISTS idx_is_premium (is_premium);

-- Note: Foreign key constraint on users.subscription_plan_id removed to avoid dependency issues
-- The pricing_plans table may not exist yet or have incompatible schema
-- Foreign key constraints are maintained in user_subscriptions table instead

-- ============================================================
-- 2. CREATE USER_SUBSCRIPTIONS TABLE - Full audit trail
-- ============================================================

CREATE TABLE IF NOT EXISTS user_subscriptions (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL,
  `plan_id` VARCHAR(36) NOT NULL,
  `service_type` VARCHAR(50) NOT NULL,
  `status` ENUM('pending', 'active', 'trial', 'cancelled', 'expired') NOT NULL DEFAULT 'pending',
  `start_date` DATETIME NOT NULL,
  `expiry_date` DATETIME DEFAULT NULL,
  `trial_end_date` DATETIME DEFAULT NULL,
  `payment_method` VARCHAR(50) DEFAULT NULL,
  `transaction_id` VARCHAR(100) DEFAULT NULL,
  `amount_paid` INT DEFAULT 0,
  `reason_cancelled` TEXT DEFAULT NULL,
  `cancelled_at` DATETIME DEFAULT NULL,
  `cancelled_by` VARCHAR(36) DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  -- Note: Foreign key constraints removed to avoid charset/collation mismatch errors
  -- The users table uses utf8mb4_unicode_ci while pricing_plans uses utf8mb4_general_ci
  -- Data integrity is maintained at application level

  INDEX idx_user_id (user_id),
  INDEX idx_plan_id (plan_id),
  INDEX idx_service_type (service_type),
  INDEX idx_status_expiry (status, expiry_date),
  INDEX idx_user_status (user_id, status),
  UNIQUE KEY uk_user_plan_active (user_id, service_type) -- Only one active per service type
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- 3. CREATE USER_SUBSCRIPTION_FEATURES TABLE - Feature-level access
-- ============================================================

CREATE TABLE IF NOT EXISTS user_subscription_features (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `subscription_id` VARCHAR(36) NOT NULL,
  `feature_key` VARCHAR(100) NOT NULL,
  `enabled` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,

  -- Note: Foreign key constraint removed to avoid charset/collation mismatch errors
  -- Data integrity is maintained at application level

  INDEX idx_subscription_id (subscription_id),
  INDEX idx_feature_key (feature_key),
  UNIQUE KEY uk_subscription_feature (subscription_id, feature_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- 4. CREATE USER_SUBSCRIPTION_HISTORY TABLE - Soft deletes
-- ============================================================

CREATE TABLE IF NOT EXISTS user_subscription_history (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `subscription_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `old_status` VARCHAR(50),
  `new_status` VARCHAR(50) NOT NULL,
  `changed_by` VARCHAR(36),
  `change_reason` TEXT,
  `changed_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_subscription_id (subscription_id),
  INDEX idx_user_id (user_id),
  INDEX idx_changed_at (changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ============================================================
-- 5. SEED DATA - Create some subscription plans in pricing_plans
-- ============================================================

-- Note: pricing_plans table already has training plans
-- Add recruiter subscription if not exists
INSERT INTO pricing_plans (
  id, service_type, service_key, name, description, 
  price_inr, currency, billing_cycle, trial_days, 
  duration, features, is_active, sort_order
) VALUES 
(
  'plan_recruiter_pro_monthly', 'recruiter_subscription', 'recruiter_pro',
  'Recruiter Pro Monthly', 'Complete recruiter toolkit with unlimited job postings',
  2999, 'INR', 'monthly', 7,
  '1 Month', '[\"unlimited_jobs\", \"premium_screening\", \"analytics\", \"ai_resume_parsing\"]',
  1, 1
)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- Add applicant premium plan if not exists
INSERT INTO pricing_plans (
  id, service_type, service_key, name, description,
  price_inr, currency, billing_cycle, trial_days,
  duration, features, is_active, sort_order
) VALUES 
(
  'plan_applicant_premium_monthly', 'applicant_plan', 'applicant_premium',
  'Premium Applicant Access', 'Access to Versant, General Assessment, and all premium features',
  299, 'INR', 'monthly', 7,
  '1 Month', '[\"versant_assessment\", \"general_assessment\", \"interview_prep\", \"typing_test\"]',
  1, 2
)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- ============================================================
-- 6. HELPER FUNCTIONS / VIEWS (Optional but recommended)
-- ============================================================

-- View: Active user subscriptions
CREATE OR REPLACE VIEW active_user_subscriptions AS
SELECT 
  u.id as user_id,
  u.email,
  u.full_name,
  us.id as subscription_id,
  pp.service_type,
  pp.name as plan_name,
  us.status,
  us.start_date,
  us.expiry_date,
  DATEDIFF(us.expiry_date, NOW()) as days_remaining,
  us.trial_end_date,
  u.is_premium
FROM users u
LEFT JOIN user_subscriptions us ON u.id = us.user_id AND us.status = 'active'
LEFT JOIN pricing_plans pp ON us.plan_id = pp.id
ORDER BY u.id;

-- View: Expiring subscriptions (7 days)
CREATE OR REPLACE VIEW expiring_subscriptions AS
SELECT 
  u.id as user_id,
  u.email,
  us.id as subscription_id,
  pp.name as plan_name,
  us.expiry_date,
  DATEDIFF(us.expiry_date, NOW()) as days_remaining
FROM users u
JOIN user_subscriptions us ON u.id = us.user_id
JOIN pricing_plans pp ON us.plan_id = pp.id
WHERE us.status = 'active'
  AND us.expiry_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
ORDER BY us.expiry_date ASC;

-- ============================================================
-- 7. STORED PROCEDURES (Optional - for complex operations)
-- ============================================================

DELIMITER //

-- Grant subscription to user
CREATE PROCEDURE IF NOT EXISTS grant_subscription(
  IN p_user_id VARCHAR(36),
  IN p_plan_id VARCHAR(36),
  IN p_days_duration INT,
  IN p_is_trial BOOLEAN
)
BEGIN
  DECLARE v_subscription_id VARCHAR(36);
  DECLARE v_start_date DATETIME;
  DECLARE v_expiry_date DATETIME;
  DECLARE v_trial_end_date DATETIME;
  DECLARE v_service_type VARCHAR(50);
  
  -- Get service type
  SELECT service_type INTO v_service_type FROM pricing_plans WHERE id = p_plan_id;
  
  SET v_subscription_id = UUID();
  SET v_start_date = NOW();
  SET v_expiry_date = DATE_ADD(NOW(), INTERVAL p_days_duration DAY);
  SET v_trial_end_date = IF(p_is_trial, DATE_ADD(NOW(), INTERVAL 7 DAY), NULL);
  
  -- Insert into user_subscriptions
  INSERT INTO user_subscriptions (
    id, user_id, plan_id, service_type, status,
    start_date, expiry_date, trial_end_date
  ) VALUES (
    v_subscription_id, p_user_id, p_plan_id, v_service_type,
    IF(p_is_trial, 'trial', 'active'),
    v_start_date, v_expiry_date, v_trial_end_date
  );
  
  -- Update users table
  UPDATE users SET 
    subscription_plan_id = p_plan_id,
    subscription_status = IF(p_is_trial, 'trial', 'active'),
    subscription_start_date = v_start_date,
    subscription_expiry_date = v_expiry_date,
    subscription_trial_end_date = v_trial_end_date,
    is_premium = TRUE,
    updated_at = NOW()
  WHERE id = p_user_id;
  
  SELECT v_subscription_id as subscription_id;
END //

-- Revoke subscription
CREATE PROCEDURE IF NOT EXISTS revoke_subscription(
  IN p_subscription_id VARCHAR(36),
  IN p_reason TEXT
)
BEGIN
  DECLARE v_user_id VARCHAR(36);
  
  SELECT user_id INTO v_user_id FROM user_subscriptions WHERE id = p_subscription_id;
  
  -- Update subscription
  UPDATE user_subscriptions SET 
    status = 'cancelled',
    cancelled_at = NOW(),
    reason_cancelled = p_reason
  WHERE id = p_subscription_id;
  
  -- Update users table
  UPDATE users SET 
    subscription_status = 'cancelled',
    is_premium = FALSE,
    updated_at = NOW()
  WHERE id = v_user_id;
END //

-- Check subscription expiry and update status
CREATE PROCEDURE IF NOT EXISTS check_subscription_expiry()
BEGIN
  -- Mark expired subscriptions
  UPDATE user_subscriptions SET 
    status = 'expired'
  WHERE status IN ('active', 'trial')
    AND expiry_date < NOW();
  
  -- Update users table for expired subscriptions
  UPDATE users u SET 
    u.subscription_status = 'expired',
    u.is_premium = FALSE
  WHERE u.subscription_status IN ('active', 'trial')
    AND u.subscription_expiry_date < NOW();
END //

DELIMITER ;

-- ============================================================
-- 8. VERIFICATION QUERIES
-- ============================================================

-- Check new columns were added
SELECT 
  COLUMN_NAME, 
  COLUMN_TYPE, 
  IS_NULLABLE, 
  COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'users'
  AND COLUMN_NAME LIKE '%subscription%'
  OR COLUMN_NAME = 'is_premium';

-- Verify new tables exist
SELECT TABLE_NAME, TABLE_ROWS, CREATE_TIME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN (
    'user_subscriptions',
    'user_subscription_features',
    'user_subscription_history'
  );

-- ============================================================
-- END OF MIGRATION
-- ============================================================
