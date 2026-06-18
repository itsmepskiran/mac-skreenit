-- ============================================================
-- CREATE TRAINING REGISTRATION TABLES
-- File: 012_create_training_tables.sql
-- Purpose: Store college and corporate training registrations
-- ============================================================

-- Main Training Registrations Table
CREATE TABLE IF NOT EXISTS training_registrations (
    id VARCHAR(36) PRIMARY KEY NOT NULL,
    registration_id VARCHAR(50) UNIQUE NOT NULL,
    registration_type ENUM('college', 'corporate') NOT NULL,
    training_course VARCHAR(100) NOT NULL,
    training_course_name VARCHAR(200) NOT NULL,
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    payment_status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    amount DECIMAL(10, 2) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_registration_type (registration_type),
    INDEX idx_status (status),
    INDEX idx_payment_status (payment_status),
    INDEX idx_created_at (created_at),
    INDEX idx_registration_id (registration_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- College Training Registrations Table
CREATE TABLE IF NOT EXISTS college_training_registrations (
    id VARCHAR(36) PRIMARY KEY NOT NULL,
    registration_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    college_name VARCHAR(200) NOT NULL,
    college_name_id VARCHAR(36) NULL COMMENT 'Reference to colleges table',
    university_name VARCHAR(200) NOT NULL,
    university_name_id VARCHAR(36) NULL COMMENT 'Reference to universities table',
    college_address TEXT NULL,
    roll_number VARCHAR(50) NOT NULL,
    course VARCHAR(100) NOT NULL,
    year_of_study VARCHAR(50) NOT NULL,
    passing_year INT NOT NULL,
    batch_timing VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (registration_id) REFERENCES training_registrations(registration_id) ON DELETE CASCADE,
    INDEX idx_email (email),
    INDEX idx_mobile (mobile),
    INDEX idx_registration_id (registration_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Corporate Training Registrations Table
CREATE TABLE IF NOT EXISTS corporate_training_registrations (
    id VARCHAR(36) PRIMARY KEY NOT NULL,
    registration_id VARCHAR(50) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    company_hq TEXT NOT NULL,
    company_country VARCHAR(100) NULL,
    company_state VARCHAR(100) NULL,
    company_city VARCHAR(100) NULL,
    company_headcount VARCHAR(50) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    company_type VARCHAR(50) NOT NULL,
    company_website VARCHAR(200) NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_designation VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    contact_mobile VARCHAR(20) NOT NULL,
    employee_count INT NOT NULL,
    training_mode VARCHAR(50) NOT NULL,
    preferred_date DATE NULL,
    duration VARCHAR(50) NOT NULL,
    additional_requirements TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (registration_id) REFERENCES training_registrations(registration_id) ON DELETE CASCADE,
    INDEX idx_contact_email (contact_email),
    INDEX idx_company_name (company_name),
    INDEX idx_registration_id (registration_id),
    INDEX idx_contact_mobile (contact_mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Verify table creation
-- ============================================================
SHOW TABLES LIKE 'training_%';
SHOW TABLES LIKE 'college_%';
SHOW TABLES LIKE 'corporate_%';

-- ============================================================
-- END OF MIGRATION
-- ============================================================
