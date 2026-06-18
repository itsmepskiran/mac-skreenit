from database import create_tables, engine
from sqlalchemy import text

def setup_database():
    """Create all database tables and verify connection."""
    try:
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        print("Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully")
        
        # List all tables
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"\nTables created: {len(tables)}")
            for table in tables:
                print(f"  - {table}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    setup_database()
