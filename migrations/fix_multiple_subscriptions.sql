-- Migration: Fix unique constraint on user_subscriptions table
-- Allow multiple active subscriptions per user for different plans
-- Drop the old constraint that prevented multiple subscriptions per service_type
-- Add new constraint that only prevents duplicate (user_id, plan_id) combinations

-- First, drop the old unique constraint
ALTER TABLE user_subscriptions DROP INDEX uk_user_plan_active;

-- Add new unique constraint on (user_id, plan_id) to prevent duplicate subscriptions for same plan
-- but allow multiple subscriptions with different plans
ALTER TABLE user_subscriptions ADD UNIQUE INDEX idx_user_plan_unique (user_id, plan_id);

-- Add helpful indexes for querying
ALTER TABLE user_subscriptions ADD INDEX idx_user_active_status (user_id, status);
ALTER TABLE user_subscriptions ADD INDEX idx_plan_service (plan_id, service_type);

-- Verify the constraints
-- SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_NAME = 'user_subscriptions' AND CONSTRAINT_NAME LIKE 'idx%' OR CONSTRAINT_NAME LIKE 'uk%';
