-- ============================================================
-- FIX SUBSCRIPTION DATES - Allow NULL for pending subscriptions
-- File: 008_fix_user_subscriptions_nullable_dates.sql
-- Purpose: Make start_date nullable to support pending subscriptions
--          Pending subscriptions are just reservations awaiting payment
-- ============================================================

-- Alter user_subscriptions table to make start_date nullable
-- This allows creating pending subscriptions that don't have a start date yet
ALTER TABLE user_subscriptions 
MODIFY COLUMN `start_date` DATETIME DEFAULT NULL;

-- ============================================================
-- END OF MIGRATION
-- ============================================================
