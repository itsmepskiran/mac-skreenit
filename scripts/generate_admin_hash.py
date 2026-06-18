#!/usr/bin/env python3
"""
Simple script to create master admin user with proper password hash
"""
import bcrypt

# Generate password hash for 'Skreenit@2024!'
password = "Skreenit@2024!"
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print("=== MASTER ADMIN USER ===")
print(f"Email: support@skreenit.com")
print(f"Password: {password}")
print(f"Password Hash: {password_hash}")
print("\n=== SQL TO EXECUTE ===")
print("-- Update or insert admin user")
print("INSERT INTO users (")
print("    id, email, password_hash, full_name, role,")
print("    created_at, updated_at, onboarded, email_confirmed_at")
print(") VALUES (")
print(f"    'master-admin-001',")
print(f"    'support@skreenit.com',")
print(f"    '{password_hash}',")
print(f"    'Master Admin',")
print(f"    'admin',")
print(f"    NOW(), NOW(), 1, NOW()")
print(") ON DUPLICATE KEY UPDATE")
print(f"    password_hash = '{password_hash}',")
print("    role = 'admin',")
print("    full_name = 'Master Admin',")
print("    updated_at = NOW();")
