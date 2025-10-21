import os
import json
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule

def import_data_from_files():
    """Import all data from JSON files to PostgreSQL"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to database
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("📊 Importing data from JSON files...")
        
        # Import Users
        if os.path.exists("data/users.json"):
            with open("data/users.json", "r") as f:
                users_data = json.load(f)
            
            imported_users = 0
            for user_data in users_data:
                # Check if user already exists
                existing_user = db.query(User).filter(User.username == user_data["username"]).first()
                if not existing_user:
                    user = User(
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        role=user_data["role"],
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        is_active=user_data["is_active"],
                        created_at=datetime.fromisoformat(user_data["created_at"]) if user_data["created_at"] else None,
                        updated_at=datetime.fromisoformat(user_data["updated_at"]) if user_data["updated_at"] else None
                    )
                    db.add(user)
                    imported_users += 1
                    print(f"  ✅ Imported user: {user_data['username']}")
                else:
                    print(f"  ⏭️  User already exists: {user_data['username']}")
            
            db.commit()
            print(f"👥 Imported {imported_users} users")
        
        # Import Students
        if os.path.exists("data/students.json"):
            with open("data/students.json", "r") as f:
                students_data = json.load(f)
            
            imported_students = 0
            for student_data in students_data:
                existing_student = db.query(StudentSchedule).filter(
                    StudentSchedule.student_id == student_data["student_id"]
                ).first()
                if not existing_student:
                    student = StudentSchedule(
                        student_id=student_data["student_id"],
                        first_name=student_data["first_name"],
                        last_name=student_data["last_name"],
                        grade_level=student_data["grade_level"],
                        externship_start_date=datetime.fromisoformat(student_data["externship_start_date"]) if student_data["externship_start_date"] else None,
                        externship_end_date=datetime.fromisoformat(student_data["externship_end_date"]) if student_data["externship_end_date"] else None,
                        created_at=datetime.fromisoformat(student_data["created_at"]) if student_data["created_at"] else None,
                        updated_at=datetime.fromisoformat(student_data["updated_at"]) if student_data["updated_at"] else None
                    )
                    db.add(student)
                    imported_students += 1
                    print(f"  ✅ Imported student: {student_data['student_id']}")
                else:
                    print(f"  ⏭️  Student already exists: {student_data['student_id']}")
            
            db.commit()
            print(f"🎓 Imported {imported_students} students")
        
        # Import Operations
        if os.path.exists("data/operations.json"):
            with open("data/operations.json", "r") as f:
                operations_data = json.load(f)
            
            imported_operations = 0
            for operation_data in operations_data:
                existing_operation = db.query(OperationSchedule).filter(
                    OperationSchedule.name == operation_data["name"]
                ).first()
                if not existing_operation:
                    operation = OperationSchedule(
                        name=operation_data["name"],
                        cdt_code=operation_data["cdt_code"],
                        created_at=datetime.fromisoformat(operation_data["created_at"]) if operation_data["created_at"] else None,
                        updated_at=datetime.fromisoformat(operation_data["updated_at"]) if operation_data["updated_at"] else None
                    )
                    db.add(operation)
                    imported_operations += 1
                    print(f"  ✅ Imported operation: {operation_data['name']}")
                else:
                    print(f"  ⏭️  Operation already exists: {operation_data['name']}")
            
            db.commit()
            print(f"🦷 Imported {imported_operations} operations")
        
        # Import Weeks
        if os.path.exists("data/weeks.json"):
            with open("data/weeks.json", "r") as f:
                weeks_data = json.load(f)
            
            imported_weeks = 0
            for week_data in weeks_data:
                existing_week = db.query(ScheduleWeekSchedule).filter(
                    ScheduleWeekSchedule.week_label == week_data["week_label"]
                ).first()
                if not existing_week:
                    week = ScheduleWeekSchedule(
                        week_label=week_data["week_label"],
                        start_date=datetime.fromisoformat(week_data["start_date"]) if week_data["start_date"] else None,
                        end_date=datetime.fromisoformat(week_data["end_date"]) if week_data["end_date"] else None,
                        created_at=datetime.fromisoformat(week_data["created_at"]) if week_data["created_at"] else None,
                        updated_at=datetime.fromisoformat(week_data["updated_at"]) if week_data["updated_at"] else None
                    )
                    db.add(week)
                    imported_weeks += 1
                    print(f"  ✅ Imported week: {week_data['week_label']}")
                else:
                    print(f"  ⏭️  Week already exists: {week_data['week_label']}")
            
            db.commit()
            print(f"📅 Imported {imported_weeks} weeks")
        
        # Import Pairs
        if os.path.exists("data/pairs.json"):
            with open("data/pairs.json", "r") as f:
                pairs_data = json.load(f)
            
            imported_pairs = 0
            for pair_data in pairs_data:
                existing_pair = db.query(StudentPair).filter(
                    StudentPair.pair_id == pair_data["pair_id"]
                ).first()
                if not existing_pair:
                    # Find the corresponding students
                    student1 = db.query(StudentSchedule).filter(
                        StudentSchedule.student_id == pair_data["student1_id"]
                    ).first()
                    student2 = db.query(StudentSchedule).filter(
                        StudentSchedule.student_id == pair_data["student2_id"]
                    ).first()
                    
                    if student1 and student2:
                        pair = StudentPair(
                            pair_id=pair_data["pair_id"],
                            student1_id=student1.id,
                            student2_id=student2.id,
                            created_at=datetime.fromisoformat(pair_data["created_at"]) if pair_data["created_at"] else None,
                            updated_at=datetime.fromisoformat(pair_data["updated_at"]) if pair_data["updated_at"] else None
                        )
                        db.add(pair)
                        imported_pairs += 1
                        print(f"  ✅ Imported pair: {pair_data['pair_id']}")
                    else:
                        print(f"  ⚠️  Could not find students for pair: {pair_data['pair_id']}")
                else:
                    print(f"  ⏭️  Pair already exists: {pair_data['pair_id']}")
            
            db.commit()
            print(f"👫 Imported {imported_pairs} pairs")
        
        # Import Assignments
        if os.path.exists("data/assignments.json"):
            with open("data/assignments.json", "r") as f:
                assignments_data = json.load(f)
            
            imported_assignments = 0
            for assignment_data in assignments_data:
                # Find corresponding records
                pair = db.query(StudentPair).filter(StudentPair.id == assignment_data["pair_id"]).first()
                operation = db.query(OperationSchedule).filter(OperationSchedule.id == assignment_data["operation_id"]).first()
                week = db.query(ScheduleWeekSchedule).filter(ScheduleWeekSchedule.id == assignment_data["week_id"]).first()
                
                if pair and operation and week:
                    assignment = ScheduleAssignment(
                        week_id=week.id,
                        pair_id=pair.id,
                        operation_id=operation.id,
                        day=assignment_data["day"],
                        time_slot=assignment_data["time_slot"],
                        chair=assignment_data["chair"],
                        patient_name=assignment_data["patient_name"],
                        patient_id=assignment_data["patient_id"],
                        status=assignment_data["status"],
                        notes=assignment_data["notes"],
                        created_at=datetime.fromisoformat(assignment_data["created_at"]) if assignment_data["created_at"] else None,
                        updated_at=datetime.fromisoformat(assignment_data["updated_at"]) if assignment_data["updated_at"] else None
                    )
                    db.add(assignment)
                    imported_assignments += 1
                    print(f"  ✅ Imported assignment: {assignment_data['day']} {assignment_data['time_slot']}")
                else:
                    print(f"  ⚠️  Could not find related records for assignment")
            
            db.commit()
            print(f"📋 Imported {imported_assignments} assignments")
        
        db.close()
        
        print("\n🎉 Data import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        return False

if __name__ == "__main__":
    success = import_data_from_files()
    sys.exit(0 if success else 1)
