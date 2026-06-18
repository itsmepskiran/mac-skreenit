-- Migration: Add roles column to users table for dual-role support
-- Created: 2026-05-16

-- Add roles JSON column to users table
ALTER TABLE users ADD COLUMN roles JSON NULL AFTER role;

-- Add comment explaining the column
ALTER TABLE users MODIFY COLUMN roles JSON NULL COMMENT 'Array of roles for dual-role support (e.g., ["candidate", "recruiter"])';

-- Note: Existing users will have NULL in roles column
-- The application code defaults to [role] when roles is NULL
