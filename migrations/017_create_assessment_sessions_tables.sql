-- Migration 017: Create assessment_sessions and assessment_responses tables
-- Run manually: mysql -u root -p skreenit_db < 017_create_assessment_sessions_tables.sql

CREATE TABLE IF NOT EXISTS assessment_sessions (
    id                  VARCHAR(36)     NOT NULL PRIMARY KEY,
    user_id             VARCHAR(255)    NOT NULL,
    assessment_key      VARCHAR(100)    NOT NULL,
    assessment_name     VARCHAR(255)    DEFAULT NULL,
    format              VARCHAR(50)     DEFAULT NULL,
    status              VARCHAR(20)     DEFAULT 'completed',
    total_exercises     INT             DEFAULT 0,
    completed_exercises INT             DEFAULT 0,
    mcq_score           INT             DEFAULT NULL,
    mcq_total           INT             DEFAULT NULL,
    overall_score       DECIMAL(5,2)    DEFAULT NULL,
    reviewer_notes      TEXT            DEFAULT NULL,
    time_taken_seconds  INT             DEFAULT NULL,
    completed_at        DATETIME        DEFAULT NULL,
    created_at          DATETIME        DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_as_user        (user_id),
    INDEX idx_as_key         (assessment_key),
    INDEX idx_as_completed   (completed_at)
);

CREATE TABLE IF NOT EXISTS assessment_responses (
    id                  VARCHAR(36)     NOT NULL PRIMARY KEY,
    session_id          VARCHAR(36)     NOT NULL,
    user_id             VARCHAR(255)    NOT NULL,
    section_id          VARCHAR(100)    DEFAULT NULL,
    item_id             VARCHAR(100)    DEFAULT NULL,
    exercise_type       VARCHAR(50)     DEFAULT NULL,
    response_type       VARCHAR(50)     DEFAULT NULL,
    text_response       LONGTEXT        DEFAULT NULL,
    selected_option_idx INT             DEFAULT NULL,
    is_correct          TINYINT(1)      DEFAULT NULL,
    has_recording       TINYINT(1)      DEFAULT 0,
    recording_url       VARCHAR(500)    DEFAULT NULL,
    created_at          DATETIME        DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ar_session (session_id),
    INDEX idx_ar_user    (user_id)
);

-- Verify
SELECT 'assessment_sessions' AS tbl, COUNT(*) AS rows FROM assessment_sessions
UNION ALL
SELECT 'assessment_responses', COUNT(*) FROM assessment_responses;
