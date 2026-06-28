-- ============================================================
-- Migration 021: Create Seminar Enquiries Table
-- Purpose: Capture contact interest from the seminars page
--          Visible to admin/super_admin via the enquiries dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS seminar_enquiries (
    id          VARCHAR(36)  PRIMARY KEY NOT NULL,
    enquiry_id  VARCHAR(20)  UNIQUE NOT NULL,

    -- Contact details
    full_name   VARCHAR(150) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    mobile      VARCHAR(20)  NOT NULL,
    company     VARCHAR(200) NULL COMMENT 'Company / organisation name (optional)',
    message     TEXT         NULL COMMENT 'What the person is interested in',

    -- Admin workflow
    status      ENUM('new','contacted','enrolled','closed') NOT NULL DEFAULT 'new',
    notes       TEXT NULL COMMENT 'Internal admin notes',
    source      VARCHAR(100) NOT NULL DEFAULT 'seminars_page',

    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_status     (status),
    INDEX idx_email      (email),
    INDEX idx_created_at (created_at),
    INDEX idx_enquiry_id (enquiry_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
