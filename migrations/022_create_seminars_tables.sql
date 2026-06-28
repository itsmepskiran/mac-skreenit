-- ============================================================
-- Migration 022: Create Seminars and Seminar Registrations
-- Purpose: Full seminar management — admin creates seminars,
--          users register and pay via Razorpay, revenue tracked.
-- ============================================================

CREATE TABLE IF NOT EXISTS seminars (
    id                  VARCHAR(36)  PRIMARY KEY NOT NULL,
    seminar_id          VARCHAR(30)  UNIQUE NOT NULL COMMENT 'Friendly ID like SEM-20250101-001',

    -- Basic info
    title               VARCHAR(200) NOT NULL,
    short_desc          VARCHAR(500) NULL,
    description         TEXT         NULL,

    -- Schedule
    seminar_date        DATE         NOT NULL,
    seminar_time        VARCHAR(50)  NOT NULL DEFAULT '10:00 AM',
    end_time            VARCHAR(50)  NULL,
    duration_label      VARCHAR(100) NULL COMMENT 'e.g. Full Day, 2 Days, 3 Hours',

    -- Location
    mode                ENUM('online','offline','hybrid') NOT NULL DEFAULT 'offline',
    venue               VARCHAR(300) NULL,
    venue_address       TEXT         NULL,
    city                VARCHAR(100) NULL,
    meeting_link        VARCHAR(500) NULL COMMENT 'Zoom/Meet link for online mode',

    -- Pricing
    price_inr           INT          NOT NULL DEFAULT 0,
    early_bird_price    INT          NULL,
    early_bird_deadline DATE         NULL,

    -- Capacity & enrollment
    capacity            INT          NULL COMMENT 'NULL means unlimited',
    enrolled_count      INT          NOT NULL DEFAULT 0,

    -- Speaker
    speaker_name        VARCHAR(200) NULL,
    speaker_bio         TEXT         NULL,
    speaker_image_url   VARCHAR(500) NULL,

    -- Content
    topics              TEXT         NULL COMMENT 'JSON array of topic strings',
    image_url           VARCHAR(500) NULL,

    -- Flags
    is_active           TINYINT(1)   NOT NULL DEFAULT 1,
    is_featured         TINYINT(1)   NOT NULL DEFAULT 0,

    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_date      (seminar_date),
    INDEX idx_active    (is_active),
    INDEX idx_featured  (is_featured),
    INDEX idx_seminar_id (seminar_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS seminar_registrations (
    id                  VARCHAR(36)  PRIMARY KEY NOT NULL,
    registration_id     VARCHAR(30)  UNIQUE NOT NULL COMMENT 'Friendly ID like SEMREG-...',

    -- Seminar reference
    seminar_id          VARCHAR(36)  NOT NULL,
    seminar_title       VARCHAR(200) NOT NULL,

    -- Attendee details
    full_name           VARCHAR(150) NOT NULL,
    email               VARCHAR(150) NOT NULL,
    mobile              VARCHAR(20)  NOT NULL,
    company             VARCHAR(200) NULL,
    designation         VARCHAR(150) NULL,
    city                VARCHAR(100) NULL,

    -- Payment
    amount              INT          NOT NULL DEFAULT 0,
    payment_status      ENUM('pending','completed','failed') NOT NULL DEFAULT 'pending',
    payment_id          VARCHAR(200) NULL,
    razorpay_order_id   VARCHAR(200) NULL,
    payment_date        DATETIME     NULL,

    -- Status
    status              ENUM('pending','confirmed','cancelled','attended') NOT NULL DEFAULT 'pending',
    attendance_marked   TINYINT(1)   NOT NULL DEFAULT 0,
    notes               TEXT         NULL COMMENT 'Internal admin notes',

    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_seminar_id    (seminar_id),
    INDEX idx_email         (email),
    INDEX idx_payment_status (payment_status),
    INDEX idx_status        (status),
    INDEX idx_created_at    (created_at),
    INDEX idx_reg_id        (registration_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
