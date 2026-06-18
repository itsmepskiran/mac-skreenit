# Backend Integration Plan - Training Sessions

## 🎯 Objective
Integrate frontend training session changes with backend API endpoints and ensure database is properly configured for location data, training registrations, and payment processing.

---

## 📊 Current Status

### ✅ Backend Infrastructure Ready
- [x] FastAPI application structure in place
- [x] Database connections configured
- [x] Router files created and registered (training_registration.py, locations.py)
- [x] Training endpoints defined (/training/courses, /training/register-college, /training/register-corporate)
- [x] Location endpoints defined (/locations/countries, /locations/states, /locations/cities, etc.)
- [x] Payment endpoints defined (/training/create-order)

### ⚠️ Critical Database Issues (From CRITICAL_ISSUES_FOUND.md)
- [x] Migration 010 exists - Create user_plan_usage table
- [x] Migration 011 exists - Create user_subscription_features table
- [ ] Migrations need to be **applied** to database
- [ ] Location tables need to be populated with data

### ✅ Code Fixes Applied
- [x] Feature extraction logic fixed (uses service_key)
- [x] Trial status recognition updated
- [x] Corrupted plan features cleaned (Migration 009)

### ❌ Still Needed
- [ ] Database migrations execution
- [ ] Location data population
- [ ] End-to-end testing of training → payment flow
- [ ] Training database tables creation

---

## 🔧 Phase 1: Database Setup & Migrations

### Step 1: Verify MySQL Connection
```bash
# Check MySQL is running
mysql -u root -p -h 127.0.0.1 -e "SELECT 1;"

# Verify database exists
mysql -u root -p -h 127.0.0.1 -e "SHOW DATABASES LIKE 'skreenit';"

# Check existing tables
mysql -u root -p skreenit -e "SHOW TABLES;"
```

### Step 2: Apply Critical Migrations
```bash
cd /Users/skreenit/Projects/Skreenit/backend-integration

# Apply migrations (if using automatic migration runner)
python run_migrations.py

# OR apply manually:
mysql -u root -p skreenit < migrations/010_create_user_plan_usage_table.sql
mysql -u root -p skreenit < migrations/011_create_user_subscription_features_table.sql
```

### Step 3: Verify Tables Created
```bash
# Verify user_plan_usage table
mysql -u root -p skreenit -e "DESC user_plan_usage;"

# Verify user_subscription_features table
mysql -u root -p skreenit -e "DESC user_subscription_features;"

# Check if tables exist
mysql -u root -p skreenit -e "SHOW TABLES LIKE 'user_%';"
```

### Step 4: Create Training Database Tables
If not existing, create:
- `training_registrations` - Main training registration records
- `college_training_registrations` - College-specific data
- `corporate_training_registrations` - Corporate-specific data

**SQL Script:**
```sql
-- Training Registrations Table
CREATE TABLE IF NOT EXISTS training_registrations (
    id VARCHAR(36) PRIMARY KEY,
    registration_id VARCHAR(50) UNIQUE NOT NULL,
    registration_type ENUM('college', 'corporate') NOT NULL,
    training_course VARCHAR(100) NOT NULL,
    training_course_name VARCHAR(200) NOT NULL,
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    payment_status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    amount DECIMAL(10, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_registration_type (registration_type),
    INDEX idx_status (status),
    INDEX idx_payment_status (payment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- College Training Registrations
CREATE TABLE IF NOT EXISTS college_training_registrations (
    id VARCHAR(36) PRIMARY KEY,
    registration_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    college_name VARCHAR(200) NOT NULL,
    university_name VARCHAR(200) NOT NULL,
    college_address TEXT,
    roll_number VARCHAR(50),
    course VARCHAR(100),
    year_of_study VARCHAR(50),
    passing_year INT,
    batch_timing VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (registration_id) REFERENCES training_registrations(registration_id),
    INDEX idx_email (email),
    INDEX idx_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Corporate Training Registrations
CREATE TABLE IF NOT EXISTS corporate_training_registrations (
    id VARCHAR(36) PRIMARY KEY,
    registration_id VARCHAR(50) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    company_hq TEXT,
    company_headcount VARCHAR(50),
    industry VARCHAR(100),
    company_type VARCHAR(50),
    company_website VARCHAR(200),
    contact_name VARCHAR(100) NOT NULL,
    contact_designation VARCHAR(100),
    contact_email VARCHAR(100) NOT NULL,
    contact_mobile VARCHAR(20) NOT NULL,
    employee_count INT,
    training_mode VARCHAR(50),
    preferred_date DATE,
    duration VARCHAR(50),
    additional_requirements TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (registration_id) REFERENCES training_registrations(registration_id),
    INDEX idx_email (contact_email),
    INDEX idx_company (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 🌍 Phase 2: Location Data Population

### Step 1: Verify Location Tables Exist
```bash
mysql -u root -p skreenit -e "SHOW TABLES LIKE '%countries%';"
mysql -u root -p skreenit -e "SHOW TABLES LIKE '%states%';"
mysql -u root -p skreenit -e "SHOW TABLES LIKE '%cities%';"
```

### Step 2: Populate Location Data (If Empty)

**Option A: Use Database Seeder Script**
```bash
python /Users/skreenit/Projects/Skreenit/backend-integration/scripts/seed_locations.py
```

**Option B: Provide Sample Data**

Sample countries:
```sql
INSERT INTO countries (id, name, iso2, iso3, phonecode, region) VALUES
('1', 'India', 'IN', 'IND', '91', 'Asia'),
('2', 'United States', 'US', 'USA', '1', 'North America'),
('3', 'United Kingdom', 'GB', 'GBR', '44', 'Europe');
```

Sample states (India):
```sql
INSERT INTO states (id, name, country_id, country_code) VALUES
('1', 'Telangana', '1', 'IN'),
('2', 'Tamil Nadu', '1', 'IN'),
('3', 'Karnataka', '1', 'IN');
```

Sample cities:
```sql
INSERT INTO cities (id, name, state_id, state_name, country_id, country_name) VALUES
('1', 'Hyderabad', '1', 'Telangana', '1', 'India'),
('2', 'Chennai', '2', 'Tamil Nadu', '1', 'India'),
('3', 'Bangalore', '3', 'Karnataka', '1', 'India');
```

### Step 3: Populate Education Data

Universities:
```sql
INSERT INTO universities (id, name, state_id, country_id) VALUES
('1', 'Anna University', '2', '1'),
('2', 'University of Hyderabad', '1', '1'),
('3', 'Bangalore University', '3', '1');
```

Colleges:
```sql
INSERT INTO colleges (id, name, university_id, city_id, state_id, country_id) VALUES
('1', 'College of Engineering Guindy', '1', '2', '2', '1'),
('2', 'IIIT Hyderabad', '2', '1', '1', '1'),
('3', 'PESIT Bangalore', '3', '3', '3', '1');
```

---

## 🚀 Phase 3: Backend Server Setup

### Step 1: Install Dependencies
```bash
cd /Users/skreenit/Projects/Skreenit/backend-integration

# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Check .env file
cat .env

# Key variables to verify:
# - MYSQL_HOST=127.0.0.1
# - MYSQL_USER=root
# - MYSQL_DATABASE=skreenit
# - PORT=8080
```

### Step 3: Start Backend Server
```bash
# From backend-integration directory
python main.py

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8080
# INFO:     Application startup complete
```

### Step 4: Verify API Endpoints
```bash
# Test training endpoints
curl http://127.0.0.1:8080/api/v1/training/courses

# Test location endpoints
curl "http://127.0.0.1:8080/api/v1/locations/countries?search=India&limit=5"

# Check health
curl http://127.0.0.1:8080/docs
```

---

## 🔌 Phase 4: API Integration Testing

### Test Location Endpoints
```bash
# 1. Get countries
curl "http://127.0.0.1:8080/api/v1/locations/countries?search=India" \
  -H "Content-Type: application/json"

# 2. Get states for country
curl "http://127.0.0.1:8080/api/v1/locations/states?country_id=1&search=Tamil" \
  -H "Content-Type: application/json"

# 3. Get cities for state
curl "http://127.0.0.1:8080/api/v1/locations/cities?state_id=2&search=Chen" \
  -H "Content-Type: application/json"
```

### Test Training Registration Endpoints
```bash
# 1. Register college student
curl -X POST http://127.0.0.1:8080/api/v1/training/register-college \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "mobile": "+919876543210",
    "collegeName": "College of Engineering",
    "universityName": "Anna University",
    "collegeAddress": "Chennai, Tamil Nadu",
    "rollNumber": "2024001",
    "course": "B.Tech CSE",
    "yearOfStudy": "3",
    "passingYear": 2025,
    "trainingCourse": "behavioral",
    "batchTiming": "morning"
  }'

# 2. Register company
curl -X POST http://127.0.0.1:8080/api/v1/training/register-company \
  -H "Content-Type: application/json" \
  -d '{
    "companyName": "Tech Corp",
    "companyHQ": "Hyderabad, India",
    "company_country": "India",
    "company_state": "Telangana",
    "company_city": "Hyderabad",
    "companyHC": "100-500",
    "industry": "it",
    "companyType": "startup",
    "contactName": "Alice Smith",
    "contactDesignation": "HR Manager",
    "contactEmail": "alice@techcorp.com",
    "contactMobile": "+919876543210",
    "trainingCourse": "corporate",
    "employeeCount": 25,
    "trainingMode": "online",
    "duration": "1_week"
  }'
```

### Test Payment Flow
```bash
# 1. Create payment order
curl -X POST http://127.0.0.1:8080/api/v1/training/create-order \
  -H "Content-Type: application/json" \
  -d '{
    "registration_id": "STU<generated_id>",
    "amount": 5000,
    "currency": "INR"
  }'
```

---

## ✅ Phase 5: End-to-End Testing Checklist

### Backend Tests
- [ ] MySQL connection verified
- [ ] All migrations applied successfully
- [ ] Training tables created
- [ ] Location data populated
- [ ] Backend server starts without errors
- [ ] API endpoints accessible

### API Tests
- [ ] GET /training/courses returns course list
- [ ] GET /training/payment-config returns Razorpay key
- [ ] GET /locations/countries returns countries
- [ ] GET /locations/states returns states
- [ ] GET /locations/cities returns cities
- [ ] POST /training/register-college creates registration
- [ ] POST /training/register-company creates registration
- [ ] POST /training/create-order creates Razorpay order

### Frontend-Backend Integration
- [ ] Training registration page loads
- [ ] Country dropdown API calls succeed
- [ ] Cascading dropdowns work (country → state → city)
- [ ] Form submission sends data to backend
- [ ] Backend saves registration to database
- [ ] Redirect to bookings.html with correct data
- [ ] Bookings page pre-fills from registration data
- [ ] Payment flow completes successfully

### Database Verification
- [ ] training_registrations table has records
- [ ] college_training_registrations table has records
- [ ] corporate_training_registrations table has records
- [ ] Payment status updates correctly
- [ ] User subscriptions created

---

## 🛠️ Troubleshooting Guide

### Issue: MySQL Connection Refused
```
Error: (2003, "Can't connect to MySQL server on '127.0.0.1' (111)")
```
**Solution:**
```bash
# Verify MySQL is running
ps aux | grep mysql

# Start MySQL if not running (Mac)
brew services start mysql

# Or manually
mysql.server start
```

### Issue: Table Already Exists
```
Error: Table 'user_plan_usage' already exists
```
**Solution:**
```bash
# The migration has IF NOT EXISTS, so it should be safe
# Just rerun the migration
```

### Issue: Foreign Key Constraint Error
```
Error: Cannot add or update a child row
```
**Solution:**
- Ensure parent tables exist first
- Apply migrations in order: 010 before 011
- Check data references valid parent records

### Issue: Location API Returns No Results
```
Error: GET /locations/countries returns empty list
```
**Solution:**
1. Verify location tables are populated
2. Check if data was inserted correctly
3. Run populate script again

---

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All migrations applied
- [ ] Database tables verified
- [ ] Backend server tested locally
- [ ] All API endpoints working
- [ ] Location data populated
- [ ] Training data seeded (if needed)

### Database
- [ ] Backups created
- [ ] Migrations logged
- [ ] Data integrity verified
- [ ] Indexes created for performance

### Backend
- [ ] Environment variables configured
- [ ] Error handling in place
- [ ] Logging configured
- [ ] Performance optimized

### Monitoring
- [ ] Error tracking enabled
- [ ] API monitoring configured
- [ ] Database monitoring enabled
- [ ] Alerts set up

---

## 📚 Related Documentation

- See `/Users/skreenit/Projects/Skreenit/sql-skreenit/INTEGRATION_CHECKLIST.md` - Frontend integration checklist
- See `/Users/skreenit/Projects/Skreenit/sql-skreenit/IMPLEMENTATION_SUMMARY.md` - Frontend implementation details
- See `CRITICAL_ISSUES_FOUND.md` - Known issues and fixes
- See `requirements.txt` - Python dependencies

---

## 🎯 Success Criteria

✅ **Backend Ready When:**
- All migrations applied to database
- All tables created with correct schema
- Location data populated
- Training tables ready
- Backend server running on port 8080
- All API endpoints returning correct responses

✅ **Integration Complete When:**
- Frontend can fetch location data
- Training registration saves to database
- Payment flow works end-to-end
- All tests passing
- No console errors

---

## 📞 Next Steps

1. **Apply Database Migrations**
   - Execute migrations 010 and 011
   - Verify tables created

2. **Populate Location Data**
   - Run population script or use SQL inserts
   - Verify data with SELECT queries

3. **Start Backend Server**
   - Ensure MySQL is running
   - Execute `python main.py`
   - Verify startup in console

4. **Test API Endpoints**
   - Use curl commands to test each endpoint
   - Check responses are correct format

5. **Test End-to-End Flow**
   - Frontend registration → Backend save → Database record
   - Payment → Database update

6. **Deploy**
   - Once all tests pass, ready for production

