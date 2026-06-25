-- Migration 019: Add AI analysis tracking columns to assessment_sessions
-- Run manually: mysql -u <user> -p <database> < migrations/019_add_analysis_columns.sql

ALTER TABLE assessment_sessions
  ADD COLUMN IF NOT EXISTS analysis_status  VARCHAR(20)  NOT NULL DEFAULT 'pending' AFTER reviewer_notes,
  ADD COLUMN IF NOT EXISTS ai_feedback      LONGTEXT     DEFAULT NULL AFTER analysis_status,
  ADD COLUMN IF NOT EXISTS is_free          TINYINT(1)   NOT NULL DEFAULT 0 AFTER ai_feedback;

-- Index for polling queries (status checks from the result page)
CREATE INDEX IF NOT EXISTS idx_as_analysis_status ON assessment_sessions (analysis_status);

-- Verify
SELECT
  COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'assessment_sessions'
  AND COLUMN_NAME IN ('analysis_status', 'ai_feedback', 'is_free')
ORDER BY ORDINAL_POSITION;
