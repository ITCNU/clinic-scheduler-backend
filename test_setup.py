#!/usr/bin/env python3
"""
Test script to verify the backend setup
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported"""
    try:
        from app.main import app
        from app.config import settings
        from app.database import engine, get_db
        from app.models import User, Student, Group, ScheduleWeek, ScheduleSlot, Operation, Pair
        from app.schemas import UserCreate, StudentCreate, ScheduleSlotCreate
        from app.core.security import verify_password, get_password_hash, create_access_token
        from app.core.permissions import get_current_user, require_admin
        print("SUCCESS: All imports successful")
        return True
    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        from app.database import engine
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            print("SUCCESS: Database connection successful")
            return True
    except Exception as e:
        print(f"ERROR: Database connection error: {e}")
        print("   Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False

def test_fastapi_app():
    """Test FastAPI app creation"""
    try:
        from app.main import app
        print(f"SUCCESS: FastAPI app created: {app.title}")
        print(f"   Version: {app.version}")
        return True
    except Exception as e:
        print(f"ERROR: FastAPI app error: {e}")
        return False

def main():
    print("Testing CNU Dental Clinic Scheduler Backend Setup")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Database Connection", test_database_connection),
        ("FastAPI App", test_fastapi_app),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed! Backend is ready to run.")
        print("\nNext steps:")
        print("1. Run: python run.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Test the API endpoints")
    else:
        print("\nSome tests failed. Please fix the issues before running the server.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
