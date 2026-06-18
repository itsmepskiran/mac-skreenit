#!/usr/bin/env python3
"""
Generate JWT Secret Key Script
Run this script to generate a secure JWT secret key for your custom authentication system.
"""

import secrets
import string

def generate_jwt_secret(length=64):
    """Generate a cryptographically secure JWT secret key."""
    # Generate random bytes and convert to URL-safe base64
    random_bytes = secrets.token_bytes(length)
    secret_key = secrets.token_urlsafe(length)
    
    return secret_key

def main():
    print("=" * 60)
    print("🔑 JWT SECRET KEY GENERATOR")
    print("=" * 60)
    print()
    
    # Generate secure key
    jwt_secret = generate_jwt_secret(64)
    
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print()
    print("✅ Copy this key to your .env file")
    print("⚠️  Keep this key secure and never share it!")
    print("🔄 Regenerate this key if it's ever compromised")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
