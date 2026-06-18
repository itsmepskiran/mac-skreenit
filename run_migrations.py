#!/usr/bin/env python
"""
Migration Runner - Execute all SQL migration files sequentially
Applies migrations in numerical order: 001, 002, 003, etc.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Get backend directory
BACKEND_DIR = Path(__file__).parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"

def get_mysql_config():
    """Get MySQL connection parameters from environment or defaults"""
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "skreenit"),
        "port": os.getenv("DB_PORT", "3306"),
    }

def run_migration(file_path, config):
    """Execute a single SQL migration file"""
    try:
        print(f"\n{'='*70}")
        print(f"▶ Running: {file_path.name}")
        print(f"{'='*70}")
        
        # Build mysql command
        cmd = [
            "mysql",
            f"-h{config['host']}",
            f"-u{config['user']}",
            f"-p{config['password']}" if config['password'] else "-p",
            f"-P{config['port']}",
            config['database'],
            f"< {file_path}"
        ]
        
        # Alternative: Use Python mysql connector
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                port=int(config['port'])
            )
            cursor = conn.cursor()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            # Handle DELIMITER statements
            current_delimiter = ';'
            statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                line_stripped = line.strip()
                
                # Handle DELIMITER changes
                if line_stripped.startswith('DELIMITER'):
                    if current_statement.strip():
                        statements.append(current_statement)
                        current_statement = ""
                    current_delimiter = line_stripped.split()[-1]
                    continue
                
                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith('--'):
                    continue
                
                current_statement += line + "\n"
                
                # Check if statement ends with current delimiter
                if line_stripped.endswith(current_delimiter):
                    statements.append(current_statement)
                    current_statement = ""
            
            if current_statement.strip():
                statements.append(current_statement)
            
            for statement in statements:
                clean_stmt = statement.strip()
                if clean_stmt and not clean_stmt.startswith('--'):
                    try:
                        print(f"  ✓ Executing: {clean_stmt[:60]}...")
                        cursor.execute(clean_stmt)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            raise
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Successfully completed: {file_path.name}")
            return True
            
        except ImportError:
            print("❌ mysql-connector-python not found. Install with: pip install mysql-connector-python")
            return False
            
    except Exception as e:
        print(f"❌ Error running migration {file_path.name}:")
        print(f"   {str(e)}")
        return False

def main():
    """Main migration runner"""
    config = get_mysql_config()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║           SKREENIT DATABASE MIGRATION RUNNER                      ║
║                  Database: {config['database']:35}║
║                  Host: {config['host']:43}║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    # Find all migration files
    if not MIGRATIONS_DIR.exists():
        print(f"❌ Migrations directory not found: {MIGRATIONS_DIR}")
        sys.exit(1)
    
    migration_files = sorted([f for f in MIGRATIONS_DIR.glob("*.sql")])
    
    if not migration_files:
        print(f"⚠️  No migration files found in {MIGRATIONS_DIR}")
        sys.exit(0)
    
    print(f"📋 Found {len(migration_files)} migration file(s):\n")
    for i, f in enumerate(migration_files, 1):
        print(f"   {i}. {f.name}")
    
    # Run migrations
    successful = 0
    failed = 0
    
    for migration_file in migration_files:
        if run_migration(migration_file, config):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 MIGRATION SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 All migrations completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
