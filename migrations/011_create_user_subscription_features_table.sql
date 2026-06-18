-- ============================================================
-- CREATE USER_SUBSCRIPTION_FEATURES TABLE
-- File: 011_create_user_subscription_features_table.sql
-- Purpose: Track which features are enabled for a subscription
-- ============================================================

CREATE TABLE IF NOT EXISTS user_subscription_features (
    id VARCHAR(36) PRIMARY KEY NOT NULL,
    subscription_id VARCHAR(36) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id) ON DELETE CASCADE,

    INDEX idx_subscription (subscription_id),
    INDEX idx_feature_key (feature_key),
    UNIQUE KEY unique_subscription_feature (subscription_id, feature_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Verify table creation
-- ============================================================
SHOW TABLES LIKE 'user_subscription_features';
DESC user_subscription_features;

-- ============================================================
-- END OF MIGRATION
-- ============================================================
