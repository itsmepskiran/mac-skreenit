-- Simplified subscription tables (without stored procedures)

-- Ensure user_subscriptions table exists
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
  
  INDEX idx_user_id (user_id),
  INDEX idx_plan_id (plan_id),
  INDEX idx_service_type (service_type),
  INDEX idx_status_expiry (status, expiry_date),
  INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Ensure user_subscription_features table exists
CREATE TABLE IF NOT EXISTS user_subscription_features (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `subscription_id` VARCHAR(36) NOT NULL,
  `feature_key` VARCHAR(100) NOT NULL,
  `enabled` BOOLEAN DEFAULT TRUE,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_subscription_id (subscription_id),
  INDEX idx_feature_key (feature_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Ensure user_subscription_history table exists
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
