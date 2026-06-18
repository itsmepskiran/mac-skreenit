"""
Seed reference data into MySQL database using backend's database connection.
Run: python backend/scripts/seed_reference_data.py
"""

import sys
import os
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def seed_departments():
    """Seed departments table."""
    departments = [
        ('HR & Payroll', 'hr-payroll', 1),
        ('Insurance Services', 'insurance-services', 2),
        ('Consulting & Advisory', 'consulting-advisory', 3),
        ('Tech & AI', 'tech-ai', 4),
        ('Creative & Branding', 'creative-branding', 5),
        ('Operations', 'operations', 6),
        ('Admin & Compliance', 'admin-compliance', 7),
        ('Finance', 'finance', 8),
        ('Sales & Partnerships', 'sales-partnerships', 9),
    ]
    
    with engine.connect() as conn:
        # Check if already populated
        result = conn.execute(text("SELECT COUNT(*) FROM departments"))
        count = result.scalar()
        if count > 0:
            print(f"Departments already seeded ({count} records)")
            return
        
        for name, slug, sort_order in departments:
            dept_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO departments (id, name, slug, sort_order, is_active)
                VALUES (:id, :name, :slug, :sort_order, TRUE)
            """), {"id": dept_id, "name": name, "slug": slug, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(departments)} departments")

def seed_roles():
    """Seed roles table."""
    roles = [
        ('Executive', 'executive', 1, 1),
        ('Senior Executive', 'senior-executive', 2, 2),
        ('Lead', 'lead', 3, 3),
        ('Assistant Manager', 'assistant-manager', 4, 4),
        ('Manager', 'manager', 5, 5),
        ('Senior Manager', 'senior-manager', 6, 6),
        ('Head of Department', 'head-of-department', 7, 7),
        ('Director', 'director', 8, 8),
    ]
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM roles"))
        count = result.scalar()
        if count > 0:
            print(f"Roles already seeded ({count} records)")
            return
        
        for name, slug, level, sort_order in roles:
            role_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO roles (id, name, slug, level, sort_order, is_active)
                VALUES (:id, :name, :slug, :level, :sort_order, TRUE)
            """), {"id": role_id, "name": name, "slug": slug, "level": level, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(roles)} roles")

def seed_employment_types():
    """Seed employment_types table."""
    types = [
        ('Full-Time', 'full-time', 1),
        ('Part-Time', 'part-time', 2),
        ('Contract', 'contract', 3),
        ('Freelance', 'freelance', 4),
        ('Internship', 'internship', 5),
        ('Temporary', 'temporary', 6),
    ]
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM employment_types"))
        count = result.scalar()
        if count > 0:
            print(f"Employment types already seeded ({count} records)")
            return
        
        for name, slug, sort_order in types:
            type_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO employment_types (id, name, slug, sort_order, is_active)
                VALUES (:id, :name, :slug, :sort_order, TRUE)
            """), {"id": type_id, "name": name, "slug": slug, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(types)} employment types")

def seed_job_types():
    """Seed job_types table."""
    types = [
        ('On-site', 'onsite', 1),
        ('Remote', 'remote', 2),
        ('Hybrid', 'hybrid', 3),
    ]
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM job_types"))
        count = result.scalar()
        if count > 0:
            print(f"Job types already seeded ({count} records)")
            return
        
        for name, slug, sort_order in types:
            type_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO job_types (id, name, slug, sort_order, is_active)
                VALUES (:id, :name, :slug, :sort_order, TRUE)
            """), {"id": type_id, "name": name, "slug": slug, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(types)} job types")

def seed_industries():
    """Seed industries table."""
    industries = [
        ('IT / Software', 'it', 1),
        ('Finance / Banking', 'finance', 2),
        ('Healthcare', 'healthcare', 3),
        ('Education', 'education', 4),
        ('Manufacturing', 'manufacturing', 5),
        ('Retail / E-commerce', 'retail', 6),
        ('Consulting', 'consulting', 7),
        ('Other', 'other', 99),
    ]
    
    with engine.connect() as conn:
        # Check if table exists
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM industries"))
            count = result.scalar()
            if count > 0:
                print(f"Industries already seeded ({count} records)")
                return
        except:
            print("Industries table does not exist, skipping")
            return
        
        for name, slug, sort_order in industries:
            ind_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO industries (id, name, slug, sort_order, is_active)
                VALUES (:id, :name, :slug, :sort_order, TRUE)
            """), {"id": ind_id, "name": name, "slug": slug, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(industries)} industries")

def seed_education_levels():
    """Seed education_levels table."""
    levels = [
        ('High School', 'high-school', 1, 1),
        ('Diploma', 'diploma', 2, 2),
        ('Bachelors Degree', 'bachelors', 4, 4),
        ('Masters Degree', 'masters', 5, 5),
        ('PhD / Doctorate', 'phd', 6, 6),
        ('Any Education', 'any', 0, 99),
    ]
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM education_levels"))
            count = result.scalar()
            if count > 0:
                print(f"Education levels already seeded ({count} records)")
                return
        except:
            print("Education levels table does not exist, skipping")
            return
        
        for name, slug, level, sort_order in levels:
            edu_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO education_levels (id, name, slug, level, sort_order, is_active)
                VALUES (:id, :name, :slug, :level, :sort_order, TRUE)
            """), {"id": edu_id, "name": name, "slug": slug, "level": level, "sort_order": sort_order})
        conn.commit()
        print(f"Seeded {len(levels)} education levels")

def main():
    print("=" * 50)
    print("Seeding Reference Data")
    print("=" * 50 + "\n")
    
    try:
        seed_departments()
        seed_roles()
        seed_employment_types()
        seed_job_types()
        seed_industries()
        seed_education_levels()
        print("\nAll reference data seeded successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
