#!/usr/bin/env python3
"""
Script to create/upgrade master admin user.
Run from backend root: python scripts/create_master_admin.py
"""
import os
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from services.mysql_service import MySQLService
import bcrypt

ADMIN_EMAIL    = "support@skreenit.com"
ADMIN_PASSWORD = "Skreenit@2024!"
ADMIN_ROLE     = "super_admin"   # master admin gets highest privileges


def create_master_admin():
    """Create or upgrade master admin user in admin_users table."""
    mysql = MySQLService()
    existing = mysql.get_single_record("admin_users", {"email": ADMIN_EMAIL})

    if existing:
        print(f"Admin user already exists: {existing['email']} | Role: {existing['role']}")
        if existing["role"] != ADMIN_ROLE:
            mysql.update_record("admin_users", {"role": ADMIN_ROLE}, {"email": ADMIN_EMAIL})
            print(f"Role upgraded to {ADMIN_ROLE}")
        else:
            print("Role is already super_admin. Nothing to do.")
        return True

    # New admin user — hash password and insert
    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        with SessionLocal() as db:
            from sqlalchemy import text
            db.execute(text(
                """
                INSERT INTO admin_users (
                    id, email, password_hash, full_name, role, is_active, created_at, updated_at
                ) VALUES (
                    :id, :email, :password_hash, :full_name, :role, :is_active, NOW(), NOW()
                )
                """
            ), {
                "id": "master-admin-001",
                "email": ADMIN_EMAIL,
                "password_hash": password_hash,
                "full_name": "Master Admin",
                "role": ADMIN_ROLE,
                "is_active": True,
            })
            db.commit()

        print("Master admin created successfully!")
        print(f"  Email   : {ADMIN_EMAIL}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print(f"  Role    : {ADMIN_ROLE}")
        print("IMPORTANT: Change the password after first login.")
        return True

    except Exception as e:
        print(f"Failed: {str(e)}")
        return False


if __name__ == "__main__":
    create_master_admin()
