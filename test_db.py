import os
import sys
from sqlalchemy import create_engine, text

def test_database_connection():
    """Test database connection and check if data exists"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to database
        print(f"🔗 Connecting to database...")
        print(f"Database URL: {database_url[:50]}...")  # Show first 50 chars for security
        
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
            # Check if users table exists and has data
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"👥 Found {user_count} users in database")
                
                if user_count > 0:
                    # Show first few users
                    result = conn.execute(text("SELECT username, role FROM users LIMIT 3"))
                    users = result.fetchall()
                    print("Sample users:")
                    for user in users:
                        print(f"  - {user[0]} ({user[1]})")
                else:
                    print("⚠️  No users found in database")
                    
            except Exception as e:
                print(f"❌ Error checking users table: {e}")
                
            # Check if students table exists and has data
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM student_schedule_students"))
                student_count = result.scalar()
                print(f"🎓 Found {student_count} students in database")
            except Exception as e:
                print(f"❌ Error checking students table: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
