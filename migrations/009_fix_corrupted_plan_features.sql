-- ============================================================
-- FIX CORRUPTED PRICING PLAN FEATURES - Remove " DOCX" suffix
-- File: 009_fix_corrupted_plan_features.sql
-- Purpose: Remove invalid " DOCX" suffix from features column
--          This is preventing JSON parsing and feature population
-- ============================================================

-- First, backup current data by viewing what will be changed
SELECT id, name, features
FROM pricing_plans
WHERE features LIKE '%DOCX%'
LIMIT 5;

-- Fix corrupted features by removing " DOCX" suffix
UPDATE pricing_plans
SET features = TRIM(TRAILING ' DOCX' FROM features)
WHERE features LIKE '%DOCX%';

-- Verify the fix
SELECT id, name, features
FROM pricing_plans
WHERE features LIKE '%DOCX%'
LIMIT 5;

-- ============================================================
-- END OF MIGRATION
-- ============================================================
