-- ============================================================
-- CREATE USER_PLAN_USAGE TABLE - Track per-action feature usage
-- File: 010_create_user_plan_usage_table.sql
-- Purpose: Store token/count tracking for per-action features
--          e.g., 5 coding challenges, 10 interviews
-- ============================================================

CREATE TABLE IF NOT EXISTS user_plan_usage (
    id VARCHAR(36) PRIMARY KEY NOT NULL,
    subscription_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,
    plan_id VARCHAR(36) NOT NULL,
    initial_count INT NOT NULL DEFAULT 1,
    remaining_count INT NOT NULL DEFAULT 1,
    usage_logs LONGTEXT NULL COMMENT 'JSON array of usage events',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,

    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES pricing_plans(id),

    INDEX idx_user_feature (user_id, feature_key),
    INDEX idx_subscription (subscription_id),
    INDEX idx_remaining_count (remaining_count),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Verify table creation
-- ============================================================
SHOW TABLES LIKE 'user_plan_usage';
DESC user_plan_usage;

-- ============================================================
-- END OF MIGRATION
-- ============================================================
