import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import get_password_hash

def create_initial_users():
    """Create initial users for the clinic scheduler"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Create database connection
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"✅ Database already has {existing_users} users")
            return True
        
        # Create initial users
        initial_users = [
            {
                "username": "admin",
                "email": "admin@cnu.edu",
                "password": "admin123",
                "role": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "is_active": True
            },
            {
                "username": "faculty1",
                "email": "faculty1@cnu.edu", 
                "password": "faculty123",
                "role": "faculty",
                "first_name": "Faculty",
                "last_name": "Member",
                "is_active": True
            },
            {
                "username": "student1",
                "email": "student1@cnu.edu",
                "password": "student123", 
                "role": "student",
                "first_name": "Student",
                "last_name": "One",
                "is_active": True
            },
            {
                "username": "frontdesk1",
                "email": "frontdesk1@cnu.edu",
                "password": "frontdesk123",
                "role": "front_desk",
                "first_name": "Front Desk",
                "last_name": "Staff",
                "is_active": True
            }
        ]
        
        # Add users to database
        for user_data in initial_users:
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hashed_password,
                role=user_data["role"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                is_active=user_data["is_active"]
            )
            db.add(user)
            print(f"✅ Created user: {user_data['username']} ({user_data['role']})")
        
        # Commit changes
        db.commit()
        db.close()
        
        print("\n🎉 Successfully created initial users!")
        print("\n📋 Login Credentials:")
        print("=" * 50)
        for user_data in initial_users:
            print(f"Username: {user_data['username']}")
            print(f"Password: {user_data['password']}")
            print(f"Role: {user_data['role']}")
            print("-" * 30)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        return False

if __name__ == "__main__":
    success = create_initial_users()
    sys.exit(0 if success else 1)
