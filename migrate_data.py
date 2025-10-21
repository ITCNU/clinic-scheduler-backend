import os
import sys
import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule
from app.core.security import get_password_hash

def migrate_data_from_local_postgres():
    """Migrate all data from local PostgreSQL to Render PostgreSQL"""
    
    # Get database URLs
    local_db_url = os.getenv("LOCAL_DATABASE_URL", "postgresql://username:password@localhost:5432/clinic_scheduler")
    render_db_url = os.getenv("DATABASE_URL")
    
    if not render_db_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to local database
        print("🔗 Connecting to local PostgreSQL database...")
        local_engine = create_engine(local_db_url)
        local_session = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)
        local_db = local_session()
        
        # Connect to Render database
        print("🔗 Connecting to Render PostgreSQL database...")
        render_engine = create_engine(render_db_url)
        render_session = sessionmaker(autocommit=False, autoflush=False, bind=render_engine)
        render_db = render_session()
        
        # Check if Render database already has data
        existing_users = render_db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Render database already has {existing_users} users")
            response = input("Do you want to continue and add more data? (y/n): ")
            if response.lower() != 'y':
                return True
        
        print("📊 Starting data migration...")
        
        # 1. Migrate Users
        print("👥 Migrating users...")
        local_users = local_db.query(User).all()
        migrated_users = 0
        for user in local_users:
            # Check if user already exists in Render DB
            existing_user = render_db.query(User).filter(User.username == user.username).first()
            if not existing_user:
                new_user = User(
                    username=user.username,
                    email=user.email,
                    password_hash=user.password_hash,
                    role=user.role,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_active=user.is_active,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
                render_db.add(new_user)
                migrated_users += 1
                print(f"  ✅ Migrated user: {user.username}")
            else:
                print(f"  ⏭️  User already exists: {user.username}")
        
        render_db.commit()
        print(f"👥 Migrated {migrated_users} users")
        
        # 2. Migrate Student Schedules
        print("🎓 Migrating student schedules...")
        local_students = local_db.query(StudentSchedule).all()
        migrated_students = 0
        for student in local_students:
            existing_student = render_db.query(StudentSchedule).filter(
                StudentSchedule.student_id == student.student_id
            ).first()
            if not existing_student:
                new_student = StudentSchedule(
                    student_id=student.student_id,
                    first_name=student.first_name,
                    last_name=student.last_name,
                    grade_level=student.grade_level,
                    externship_start_date=student.externship_start_date,
                    externship_end_date=student.externship_end_date,
                    created_at=student.created_at,
                    updated_at=student.updated_at
                )
                render_db.add(new_student)
                migrated_students += 1
                print(f"  ✅ Migrated student: {student.student_id}")
            else:
                print(f"  ⏭️  Student already exists: {student.student_id}")
        
        render_db.commit()
        print(f"🎓 Migrated {migrated_students} students")
        
        # 3. Migrate Student Pairs
        print("👫 Migrating student pairs...")
        local_pairs = local_db.query(StudentPair).all()
        migrated_pairs = 0
        for pair in local_pairs:
            existing_pair = render_db.query(StudentPair).filter(
                StudentPair.pair_id == pair.pair_id
            ).first()
            if not existing_pair:
                # Find the corresponding students in Render DB
                student1 = render_db.query(StudentSchedule).filter(
                    StudentSchedule.student_id == pair.student1.student_id
                ).first()
                student2 = render_db.query(StudentSchedule).filter(
                    StudentSchedule.student_id == pair.student2.student_id
                ).first()
                
                if student1 and student2:
                    new_pair = StudentPair(
                        pair_id=pair.pair_id,
                        student1_id=student1.id,
                        student2_id=student2.id,
                        created_at=pair.created_at,
                        updated_at=pair.updated_at
                    )
                    render_db.add(new_pair)
                    migrated_pairs += 1
                    print(f"  ✅ Migrated pair: {pair.pair_id}")
                else:
                    print(f"  ⚠️  Could not find students for pair: {pair.pair_id}")
            else:
                print(f"  ⏭️  Pair already exists: {pair.pair_id}")
        
        render_db.commit()
        print(f"👫 Migrated {migrated_pairs} pairs")
        
        # 4. Migrate Operation Schedules
        print("🦷 Migrating operation schedules...")
        local_operations = local_db.query(OperationSchedule).all()
        migrated_operations = 0
        for operation in local_operations:
            existing_operation = render_db.query(OperationSchedule).filter(
                OperationSchedule.name == operation.name
            ).first()
            if not existing_operation:
                new_operation = OperationSchedule(
                    name=operation.name,
                    cdt_code=operation.cdt_code,
                    created_at=operation.created_at,
                    updated_at=operation.updated_at
                )
                render_db.add(new_operation)
                migrated_operations += 1
                print(f"  ✅ Migrated operation: {operation.name}")
            else:
                print(f"  ⏭️  Operation already exists: {operation.name}")
        
        render_db.commit()
        print(f"🦷 Migrated {migrated_operations} operations")
        
        # 5. Migrate Schedule Weeks
        print("📅 Migrating schedule weeks...")
        local_weeks = local_db.query(ScheduleWeekSchedule).all()
        migrated_weeks = 0
        for week in local_weeks:
            existing_week = render_db.query(ScheduleWeekSchedule).filter(
                ScheduleWeekSchedule.week_label == week.week_label
            ).first()
            if not existing_week:
                new_week = ScheduleWeekSchedule(
                    week_label=week.week_label,
                    start_date=week.start_date,
                    end_date=week.end_date,
                    created_at=week.created_at,
                    updated_at=week.updated_at
                )
                render_db.add(new_week)
                migrated_weeks += 1
                print(f"  ✅ Migrated week: {week.week_label}")
            else:
                print(f"  ⏭️  Week already exists: {week.week_label}")
        
        render_db.commit()
        print(f"📅 Migrated {migrated_weeks} weeks")
        
        # 6. Migrate Schedule Assignments
        print("📋 Migrating schedule assignments...")
        local_assignments = local_db.query(ScheduleAssignment).all()
        migrated_assignments = 0
        for assignment in local_assignments:
            # Find corresponding records in Render DB
            pair = None
            operation = None
            week = None
            
            if assignment.pair:
                pair = render_db.query(StudentPair).filter(
                    StudentPair.pair_id == assignment.pair.pair_id
                ).first()
            
            if assignment.operation:
                operation = render_db.query(OperationSchedule).filter(
                    OperationSchedule.name == assignment.operation.name
                ).first()
            
            if assignment.week:
                week = render_db.query(ScheduleWeekSchedule).filter(
                    ScheduleWeekSchedule.week_label == assignment.week.week_label
                ).first()
            
            if pair and operation and week:
                new_assignment = ScheduleAssignment(
                    week_id=week.id,
                    pair_id=pair.id,
                    operation_id=operation.id,
                    day=assignment.day,
                    time_slot=assignment.time_slot,
                    chair=assignment.chair,
                    patient_name=assignment.patient_name,
                    patient_id=assignment.patient_id,
                    status=assignment.status,
                    notes=assignment.notes,
                    created_at=assignment.created_at,
                    updated_at=assignment.updated_at
                )
                render_db.add(new_assignment)
                migrated_assignments += 1
                print(f"  ✅ Migrated assignment: {assignment.day} {assignment.time_slot}")
            else:
                print(f"  ⚠️  Could not find related records for assignment")
        
        render_db.commit()
        print(f"📋 Migrated {migrated_assignments} assignments")
        
        # Close connections
        local_db.close()
        render_db.close()
        
        print("\n🎉 Data migration completed successfully!")
        print(f"📊 Summary:")
        print(f"  - Users: {migrated_users}")
        print(f"  - Students: {migrated_students}")
        print(f"  - Pairs: {migrated_pairs}")
        print(f"  - Operations: {migrated_operations}")
        print(f"  - Weeks: {migrated_weeks}")
        print(f"  - Assignments: {migrated_assignments}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate_data_from_local_postgres()
    sys.exit(0 if success else 1)
