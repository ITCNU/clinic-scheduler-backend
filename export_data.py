import os
import json
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule

def export_data_to_files():
    """Export all data from PostgreSQL to JSON files"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://app_user:admin123atcnu@localhost:5432/clinic_scheduler")
    
    try:
        # Connect to database
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("Exporting data from PostgreSQL...")
        
        # Export Users
        users = db.query(User).all()
        users_data = []
        for user in users:
            users_data.append({
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        with open("data/users.json", "w") as f:
            json.dump(users_data, f, indent=2)
        print(f"Exported {len(users_data)} users to data/users.json")
        
        # Export Students
        students = db.query(StudentSchedule).all()
        students_data = []
        for student in students:
            students_data.append({
                "student_id": student.student_id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "grade_level": student.grade_level,
                "externship_start_date": student.externship_start_date.isoformat() if student.externship_start_date else None,
                "externship_end_date": student.externship_end_date.isoformat() if student.externship_end_date else None,
                "created_at": student.created_at.isoformat() if student.created_at else None,
                "updated_at": student.updated_at.isoformat() if student.updated_at else None
            })
        
        with open("data/students.json", "w") as f:
            json.dump(students_data, f, indent=2)
        print(f"Exported {len(students_data)} students to data/students.json")
        
        # Export Pairs
        pairs = db.query(StudentPair).all()
        pairs_data = []
        for pair in pairs:
            pairs_data.append({
                "pair_id": pair.pair_id,
                "student1_id": pair.student1_id,
                "student2_id": pair.student2_id,
                "created_at": pair.created_at.isoformat() if pair.created_at else None
            })
        
        with open("data/pairs.json", "w") as f:
            json.dump(pairs_data, f, indent=2)
        print(f"Exported {len(pairs_data)} pairs to data/pairs.json")
        
        # Export Operations
        operations = db.query(OperationSchedule).all()
        operations_data = []
        for operation in operations:
            operations_data.append({
                "name": operation.name,
                "cdt_code": operation.cdt_code,
                "created_at": operation.created_at.isoformat() if operation.created_at else None
            })
        
        with open("data/operations.json", "w") as f:
            json.dump(operations_data, f, indent=2)
        print(f"Exported {len(operations_data)} operations to data/operations.json")
        
        # Export Weeks
        weeks = db.query(ScheduleWeekSchedule).all()
        weeks_data = []
        for week in weeks:
            weeks_data.append({
                "week_label": week.week_label,
                "start_date": week.start_date.isoformat() if week.start_date else None,
                "end_date": week.end_date.isoformat() if week.end_date else None,
                "created_at": week.created_at.isoformat() if week.created_at else None
            })
        
        with open("data/weeks.json", "w") as f:
            json.dump(weeks_data, f, indent=2)
        print(f"Exported {len(weeks_data)} weeks to data/weeks.json")
        
        # Export Assignments
        assignments = db.query(ScheduleAssignment).all()
        assignments_data = []
        for assignment in assignments:
            assignments_data.append({
                "week_id": assignment.week_id,
                "pair_id": assignment.pair_id,
                "operation_id": assignment.operation_id,
                "day": assignment.day,
                "time_slot": assignment.time_slot,
                "chair": assignment.chair,
                "patient_name": assignment.patient_name,
                "patient_id": assignment.patient_id,
                "status": assignment.status,
                "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
                "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None
            })
        
        with open("data/assignments.json", "w") as f:
            json.dump(assignments_data, f, indent=2)
        print(f"Exported {len(assignments_data)} assignments to data/assignments.json")
        
        db.close()
        
        print("\nData export completed successfully!")
        print("All data files are saved in the 'data/' directory")
        print("You can now commit and push these files to GitHub")
        
        return True
        
    except Exception as e:
        print(f"Error exporting data: {e}")
        return False

if __name__ == "__main__":
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    success = export_data_to_files()
    if success:
        print("\nNext steps:")
        print("1. git add data/")
        print("2. git commit -m 'Add exported data files'")
        print("3. git push origin main")
        print("4. Deploy to Render")
    else:
        print("\nExport failed. Please check your database connection.")
