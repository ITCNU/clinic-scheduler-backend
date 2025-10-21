from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import pandas as pd
import io
import re
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from ..models.user import User
from ..models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule
from ..core.permissions import require_admin, require_faculty_or_admin, require_staff_or_admin

router = APIRouter(prefix="/api", tags=["file-upload"])

def _s(v):
    """Safe string conversion"""
    return "" if pd.isna(v) else str(v).strip()

def _normalize_time_slot(v: str) -> str:
    """Normalize time slot format"""
    s = _s(v)
    if not s:
        return s
    # Normalize hyphen to en dash and trim spaces around dash
    s = s.replace("-", "–")
    s = s.replace(" – ", "–").replace(" –", "–").replace("– ", "–")
    return s

def _normalize_chair(v: str) -> str:
    """Normalize chair format"""
    s = _s(v)
    if not s:
        return s
    # If numeric, prefix with "Chair "
    try:
        n = int(float(s))
        return f"Chair {n}"
    except Exception:
        # If it already starts with Chair, keep
        if s.lower().startswith("chair"):
            return s
        return s

def _week_key(v):
    """Normalize a week value or sheet name to consistent date range format."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return "10/27/2025-10/31/2025"  # Default to first week
    
    s = str(v).strip()
    
    # If label looks like a date range, normalize the format
    date_range_patterns = [
        r"^(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})$",
        r"^(\d{4})-(\d{2})-(\d{2})\s*-\s*(\d{4})-(\d{2})-(\d{2})$"
    ]
    
    for pat in date_range_patterns:
        match = re.match(pat, s)
        if match:
            if len(match.groups()) == 6:  # MM/DD/YYYY-MM/DD/YYYY format
                m1, d1, y1, m2, d2, y2 = match.groups()
                return f"{int(m1):02d}/{int(d1):02d}/{y1}-{int(m2):02d}/{int(d2):02d}/{y2}"
            elif len(match.groups()) == 6:  # YYYY-MM-DD-YYYY-MM-DD format
                y1, m1, d1, y2, m2, d2 = match.groups()
                return f"{int(m1):02d}/{int(d1):02d}/{y1}-{int(m2):02d}/{int(d2):02d}/{y2}"
    
    if s.lower().startswith("week"):
        parts = s.split()
        try:
            n = int(parts[-1])
            # Convert week number to date range
            from datetime import datetime, timedelta
            start_date = datetime(2025, 10, 27)  # Monday, October 27, 2025
            week_monday = start_date + timedelta(weeks=n - 1)
            week_friday = week_monday + timedelta(days=4)
            return f"{week_monday.strftime('%m/%d/%Y')}-{week_friday.strftime('%m/%d/%Y')}"
        except:
            return "10/27/2025-10/31/2025"
    
    try:
        n = int(float(s))
        # Convert week number to date range
        from datetime import datetime, timedelta
        start_date = datetime(2025, 10, 27)  # Monday, October 27, 2025
        week_monday = start_date + timedelta(weeks=n - 1)
        week_friday = week_monday + timedelta(days=4)
        return f"{week_monday.strftime('%m/%d/%Y')}-{week_friday.strftime('%m/%d/%Y')}"
    except:
        return "10/27/2025-10/31/2025"  # Default fallback

def _get_week_date_range(week_num: int):
    """Generate date range for a week number (Monday-Friday)."""
    # Start date: First Monday of the current semester
    start_date = datetime(2025, 10, 27)  # Monday, October 27, 2025
    
    # Calculate the Monday for this week (week_num - 1 weeks from start)
    week_monday = start_date + timedelta(weeks=week_num - 1)
    
    # Calculate Friday (4 days after Monday)
    week_friday = week_monday + timedelta(days=4)
    
    # Format as MM/DD/YYYY-MM/DD/YYYY
    return f"{week_monday.strftime('%m/%d/%Y')}-{week_friday.strftime('%m/%d/%Y')}"

@router.post("/students/upload")
async def upload_student_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Upload and process student data Excel file"""
    try:
        # Read file content
        content = await file.read()
        
        # Parse Excel file
        df = pd.read_excel(io.BytesIO(content))
        required_columns = ['Student ID', 'Last Name', 'First Name', 'Email', 'Grade Level', 'Externship']
        optional_columns = ['Externship Start', 'Externship End']
        
        # Check required columns
        missing_required = [col for col in required_columns if col not in df.columns]
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {missing_required}. Required columns: {required_columns}"
            )
        
        # Check if optional columns are present
        has_externship_dates = all(col in df.columns for col in optional_columns)
        if not has_externship_dates:
            print(f"WARNING: Optional externship date columns not found: {optional_columns}")
            # Add empty columns for externship dates if they don't exist
            for col in optional_columns:
                if col not in df.columns:
                    df[col] = None
        
        # Clear existing data in proper order (due to foreign key constraints)
        
        # Delete in proper order to avoid foreign key constraints
        db.query(ScheduleAssignment).delete()
        db.query(StudentPair).delete()
        db.query(StudentSchedule).delete()
        
        # Force commit to ensure deletion is complete
        db.commit()
        
        
        # Normalize IDs and check duplicates (include externship students)
        seen_ids = set()
        duplicate_ids = set()
        rows_to_import = []
        for _, row in df.iterrows():
            normalized_id = _s(row['Student ID'])
            if normalized_id in seen_ids:
                duplicate_ids.add(normalized_id)
                continue
            seen_ids.add(normalized_id)
            rows_to_import.append(row)

        if duplicate_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate student IDs found in file (after normalization): {sorted(list(duplicate_ids))}"
            )

        # Process students
        students_created = 0
        students_data = []
        
        for row in rows_to_import:
            student_id = _s(row['Student ID'])

            # Parse externship dates (handle missing columns gracefully)
            externship_start = None
            externship_end = None
            
            # Check if externship date columns exist and have values
            if 'Externship Start' in row and pd.notna(row['Externship Start']) and str(row['Externship Start']).strip():
                try:
                    externship_start = pd.to_datetime(row['Externship Start']).date()
                except:
                    externship_start = None
            
            if 'Externship End' in row and pd.notna(row['Externship End']) and str(row['Externship End']).strip():
                try:
                    externship_end = pd.to_datetime(row['Externship End']).date()
                except:
                    externship_end = None

            student = StudentSchedule(
                student_id=student_id,
                first_name=_s(row['First Name']),
                last_name=_s(row['Last Name']),
                grade_level=int(row['Grade Level']),
                externship=bool(row['Externship']),
                externship_start_date=externship_start,
                externship_end_date=externship_end,
                pair_id=None,
                group_number=None
            )
            db.add(student)
            students_data.append(student)
            students_created += 1
        
        db.commit()
        
        return {
            "message": f"Student data uploaded successfully. Created {students_created} students.",
            "count": students_created
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/students/create-pairs")
async def create_student_pairs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create pairs for students and distribute them evenly between two groups"""
    try:
        # Get all students
        all_students = db.query(StudentSchedule).all()
        
        # Get students with externship dates (not already paired)
        students_with_externship = db.query(StudentSchedule).filter(
            StudentSchedule.externship_start_date.isnot(None),
            StudentSchedule.externship_end_date.isnot(None),
            StudentSchedule.pair_id.is_(None)  # Not already paired
        ).all()
        
        # Get students without externship dates (not already paired)
        students_without_externship = db.query(StudentSchedule).filter(
            (StudentSchedule.externship_start_date.is_(None)) |
            (StudentSchedule.externship_end_date.is_(None)),
            StudentSchedule.pair_id.is_(None)  # Not already paired
        ).all()
        
        # Get already paired students for reference
        already_paired_students = db.query(StudentSchedule).filter(
            StudentSchedule.pair_id.isnot(None)
        ).all()
        
        if not students_with_externship and not students_without_externship:
            return {
                "message": "No students found in database.",
                "pairs_created": 0
            }
        
        # Step 1: Create all pairs first (without group assignment)
        all_temp_pairs = []
        
        # Group students by externship start and end dates
        externship_groups = {}
        for student in students_with_externship:
            key = (student.externship_start_date, student.externship_end_date)
            if key not in externship_groups:
                externship_groups[key] = []
            externship_groups[key].append(student)
        
        # Create pairs for students with matching externship dates
        for (start_date, end_date), students in externship_groups.items():
            if len(students) >= 2:
                # Sort students by student_id for consistent pairing
                students.sort(key=lambda s: s.student_id)
                
                # Prioritize same-grade pairs within externship groups
                paired_students = set()
                temp_pairs = []
                
                # First pass: Try to create D4-D4 pairs
                for i, student1 in enumerate(students):
                    if student1.id in paired_students:
                        continue
                    
                    for j, student2 in enumerate(students[i+1:], i+1):
                        if student2.id in paired_students:
                            continue
                        
                        # Check if this is a D4-D4 combination
                        if student1.grade_level == 4 and student2.grade_level == 4:
                            temp_pairs.append((student1, student2))
                            paired_students.add(student1.id)
                            paired_students.add(student2.id)
                            break
                
                # Second pass: Try to create D3-D3 pairs
                for i, student1 in enumerate(students):
                    if student1.id in paired_students:
                        continue
                    
                    for j, student2 in enumerate(students[i+1:], i+1):
                        if student2.id in paired_students:
                            continue
                        
                        # Check if this is a D3-D3 combination
                        if student1.grade_level == 3 and student2.grade_level == 3:
                            temp_pairs.append((student1, student2))
                            paired_students.add(student1.id)
                            paired_students.add(student2.id)
                            break
                
                # Third pass: Pair remaining students of the same grade only
                remaining_students = [s for s in students if s.id not in paired_students]
                
                # Group remaining students by grade
                remaining_by_grade = {}
                for student in remaining_students:
                    grade = student.grade_level
                    if grade not in remaining_by_grade:
                        remaining_by_grade[grade] = []
                    remaining_by_grade[grade].append(student)
                
                # Pair students within each grade
                for grade, grade_students in remaining_by_grade.items():
                    for i in range(0, len(grade_students), 2):
                        if i + 1 < len(grade_students):
                            temp_pairs.append((grade_students[i], grade_students[i + 1]))
                
                all_temp_pairs.extend(temp_pairs)
                
                # Handle odd number of students in externship group
                if len(students) % 2 == 1:
                    remaining_student = students[-1]
        
        # Create pairs for students without externship dates
        if students_without_externship:
            # Sort by student_id for consistent pairing
            students_without_externship.sort(key=lambda s: s.student_id)
            
            # Prioritize same-grade pairs for students without externship dates
            paired_students = set()
            temp_pairs = []
            
            # First pass: Try to create D4-D4 pairs
            for i, student1 in enumerate(students_without_externship):
                if student1.id in paired_students:
                    continue
                
                for j, student2 in enumerate(students_without_externship[i+1:], i+1):
                    if student2.id in paired_students:
                        continue
                    
                    # Check if this is a D4-D4 combination
                    if student1.grade_level == 4 and student2.grade_level == 4:
                        temp_pairs.append((student1, student2))
                        paired_students.add(student1.id)
                        paired_students.add(student2.id)
                        break
            
            # Second pass: Try to create D3-D3 pairs
            for i, student1 in enumerate(students_without_externship):
                if student1.id in paired_students:
                    continue
                
                for j, student2 in enumerate(students_without_externship[i+1:], i+1):
                    if student2.id in paired_students:
                        continue
                    
                    # Check if this is a D3-D3 combination
                    if student1.grade_level == 3 and student2.grade_level == 3:
                        temp_pairs.append((student1, student2))
                        paired_students.add(student1.id)
                        paired_students.add(student2.id)
                        break
            
            # Third pass: Pair remaining students of the same grade only
            remaining_students = [s for s in students_without_externship if s.id not in paired_students]
            
            # Group remaining students by grade
            remaining_by_grade = {}
            for student in remaining_students:
                grade = student.grade_level
                if grade not in remaining_by_grade:
                    remaining_by_grade[grade] = []
                remaining_by_grade[grade].append(student)
            
            # Pair students within each grade
            for grade, grade_students in remaining_by_grade.items():
                for i in range(0, len(grade_students), 2):
                    if i + 1 < len(grade_students):
                        temp_pairs.append((grade_students[i], grade_students[i + 1]))
            
            all_temp_pairs.extend(temp_pairs)
            
            # Handle odd number of students without externship dates
            if len(students_without_externship) % 2 == 1:
                remaining_student = students_without_externship[-1]
        
        
        # Step 2: Distribute pairs evenly between two groups with balanced grade distribution
        total_pairs = len(all_temp_pairs)
        if total_pairs == 0:
            return {
                "message": "No pairs could be created from available students.",
                "pairs_created": 0
            }
        
        # Separate pairs by grade combination
        d4_d4_pairs = []
        d3_d3_pairs = []
        
        for student1, student2 in all_temp_pairs:
            if student1.grade_level == 4 and student2.grade_level == 4:
                d4_d4_pairs.append((student1, student2))
            elif student1.grade_level == 3 and student2.grade_level == 3:
                d3_d3_pairs.append((student1, student2))
        
        
        # Calculate balanced distribution - ensure equal total pairs per group
        group1_pairs = []
        group2_pairs = []
        
        # Combine all pairs and distribute evenly by alternating assignment
        all_pairs = d4_d4_pairs + d3_d3_pairs
        
        # Distribute pairs evenly between groups using alternating assignment
        for i, pair in enumerate(all_pairs):
            if i % 2 == 0:
                group1_pairs.append(pair)  # Even indices → Group 1
            else:
                group2_pairs.append(pair)   # Odd indices → Group 2
        
        
        # Verify equal distribution
        if len(group1_pairs) != len(group2_pairs):
            print(f"WARNING: Unequal pair distribution! Group 1: {len(group1_pairs)}, Group 2: {len(group2_pairs)}")
        else:
            print(f"SUCCESS: Equal pair distribution! Both groups have {len(group1_pairs)} pairs")
        
        # Get existing pair counts for ID generation
        existing_group1_count = len(db.query(StudentPair).filter(StudentPair.group_number == 1).all())
        existing_group2_count = len(db.query(StudentPair).filter(StudentPair.group_number == 2).all())
        
        pairs_created = 0
        
        # Create pairs for Group 1
        for student1, student2 in group1_pairs:
            existing_group1_count += 1
            pair_id = f"G1P{existing_group1_count}"
            group_number = 1
            
            # Create the pair
            pair = StudentPair(
                pair_id=pair_id,
                student1_id=student1.id,
                student2_id=student2.id,
                group_number=group_number
            )
            db.add(pair)
            
            # Update students with pair info
            student1.pair_id = pair_id
            student1.group_number = group_number
            student2.pair_id = pair_id
            student2.group_number = group_number
            
            pairs_created += 1
            grade_combo = f"D{student1.grade_level}-D{student2.grade_level}"
        
        # Create pairs for Group 2
        for student1, student2 in group2_pairs:
            existing_group2_count += 1
            pair_id = f"G2P{existing_group2_count}"
            group_number = 2
            
            # Create the pair
            pair = StudentPair(
                pair_id=pair_id,
                student1_id=student1.id,
                student2_id=student2.id,
                group_number=group_number
            )
            db.add(pair)
            
            # Update students with pair info
            student1.pair_id = pair_id
            student1.group_number = group_number
            student2.pair_id = pair_id
            student2.group_number = group_number
            
            pairs_created += 1
            grade_combo = f"D{student1.grade_level}-D{student2.grade_level}"
        
        db.commit()
        
        # Final verification
        final_group1_count = len(db.query(StudentPair).filter(StudentPair.group_number == 1).all())
        final_group2_count = len(db.query(StudentPair).filter(StudentPair.group_number == 2).all())
        
        return {
            "message": f"Successfully created {pairs_created} pairs and distributed them evenly. Group 1: {final_group1_count} pairs, Group 2: {final_group2_count} pairs. Unpaired students with externship dates: {len(students_with_externship)}, Unpaired students without externship dates: {len(students_without_externship)}, Already paired students: {len(already_paired_students)}",
            "pairs_created": pairs_created,
            "group1_pairs": final_group1_count,
            "group2_pairs": final_group2_count,
            "students_with_externship": len(students_with_externship),
            "students_without_externship": len(students_without_externship),
            "already_paired_students": len(already_paired_students)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating pairs: {str(e)}")

@router.post("/schedule/upload")
async def upload_schedule_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Upload and process patient schedule Excel file"""
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse Excel file
        xls = pd.ExcelFile(io.BytesIO(content))
        
        # Clear existing assignments
        db.query(ScheduleAssignment).delete()
        
        required_core = ['Day', 'Time Slot', 'Chair', 'Operation', 'Patient ID', 'Patient Name']
        assignments_created = 0
        
        # No default operations - operations will be created as needed from uploaded data
        
        for sheet in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet)
            except Exception as e:
                continue
            
            # Normalize headers
            df.columns = [str(c).strip() for c in df.columns]
            
            # Determine week for this sheet
            has_week_col = 'Week' in df.columns
            
            missing = [c for c in required_core if c not in df.columns]
            if missing:
                continue
            
            # Clean data
            for col in (['Week'] if has_week_col else []) + required_core:
                if col in df.columns:
                    df[col] = df[col].apply(_s)
            
            for _, row in df.iterrows():
                week_key = _week_key(row['Week']) if has_week_col else _week_key(sheet)
                
                # Get or create week
                week = db.query(ScheduleWeekSchedule).filter(ScheduleWeekSchedule.week_label == week_key).first()
                if not week:
                    week = ScheduleWeekSchedule(week_label=week_key)
                    db.add(week)
                    db.commit()
                
                day = _s(row['Day'])
                time_slot = _normalize_time_slot(row['Time Slot'])
                chair = _normalize_chair(row['Chair'])
                operation_name = _s(row['Operation'])
                patient_id = _s(row['Patient ID'])
                patient_name = _s(row['Patient Name'])
                
                # Get or create operation
                operation = None
                if operation_name:
                    operation = db.query(OperationSchedule).filter(OperationSchedule.name == operation_name).first()
                    if not operation:
                        operation = OperationSchedule(name=operation_name)
                        db.add(operation)
                        db.commit()
                
                # Create assignment
                assignment = ScheduleAssignment(
                    week_id=week.id,
                    day=day,
                    time_slot=time_slot,
                    chair=chair,
                    operation_id=operation.id if operation else None,
                    patient_id=patient_id,
                    patient_name=patient_name,
                    pair_id=None,
                    status='empty'
                )
                db.add(assignment)
                assignments_created += 1
        
        db.commit()
        
        return {
            "message": "Schedule data uploaded successfully",
            "count": assignments_created
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/operations/initialize")
async def initialize_operations(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Initialize default operations - REMOVED: No default operations"""
    try:
        return {
            "message": "No default operations to initialize - operations are created as needed from uploaded data",
            "count": 0
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error initializing operations: {str(e)}")

@router.get("/students/")
async def get_students(
    current_user: User = Depends(require_faculty_or_admin),
    db: Session = Depends(get_db)
):
    """Get all students"""
    students = db.query(StudentSchedule).all()
    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "grade_level": s.grade_level,
            "externship": s.externship,
            "externship_start_date": s.externship_start_date.isoformat() if s.externship_start_date else None,
            "externship_end_date": s.externship_end_date.isoformat() if s.externship_end_date else None,
            "pair_id": s.pair_id,
            "group_number": s.group_number
        }
        for s in students
    ]

@router.get("/pairs/")
async def get_pairs(
    current_user: User = Depends(require_faculty_or_admin),
    db: Session = Depends(get_db)
):
    """Get all student pairs"""
    from sqlalchemy.orm import selectinload
    
    pairs = db.query(StudentPair).options(
        selectinload(StudentPair.student1),
        selectinload(StudentPair.student2)
    ).all()
    
    # Debug: Print first pair to check student_id
    if pairs:
        first_pair = pairs[0]
    
    return [
        {
            "id": p.id,
            "pair_id": p.pair_id,
            "student1": {
                "id": p.student1_id,
                "student_id": p.student1.student_id,
                "first_name": p.student1.first_name,
                "last_name": p.student1.last_name,
                "grade_level": p.student1.grade_level
            },
            "student2": {
                "id": p.student2_id,
                "student_id": p.student2.student_id,
                "first_name": p.student2.first_name,
                "last_name": p.student2.last_name,
                "grade_level": p.student2.grade_level
            },
            "group_number": p.group_number
        }
        for p in pairs
    ]

@router.get("/operation-tracking/")
async def get_operation_tracking(
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Get operation tracking by pair"""
    print("=== OPERATION TRACKING API CALLED ===")
    from sqlalchemy.orm import selectinload
    
    # Get all pairs with their students
    pairs = db.query(StudentPair).options(
        selectinload(StudentPair.student1),
        selectinload(StudentPair.student2)
    ).all()
    
    # Get ALL assignments (not just those with operations) to count operations from schedule data
    assignments = db.query(ScheduleAssignment).options(
        selectinload(ScheduleAssignment.operation),
        selectinload(ScheduleAssignment.pair)
    ).all()
    
    # Define CDT operation groups
    def classify_cdt(code: str) -> str:
        if not code:
            return "Other"
        code = code.strip().upper()
        if code.startswith("D01"):
            return "D01XX"
        if code.startswith("D1"):
            return "D1XXX"
        if code.startswith("D2"):
            return "D2XXX"
        if code.startswith("D3"):
            return "D3XXX"
        if code.startswith("D4"):
            return "D4XXX"
        if code.startswith("D5"):
            return "D5XXX"
        if code.startswith("D6"):
            return "D6XXX"
        if code.startswith("D7"):
            return "D7XXX"
        return "Other"
    cdt_groups = ["D01XX","D1XXX","D2XXX","D3XXX","D4XXX","D5XXX","D6XXX","D7XXX"]
    
    
    # Count assignments with operations
    assignments_with_ops = [a for a in assignments if a.operation]
    
    # Build operation tracking
    pair_summaries = []
    
    for pair in pairs:
        pair_id = pair.pair_id  # This is the string format like "G1P1"
        pair_db_id = pair.id     # This is the numeric database ID
        
        # Count operations for this pair by CDT group
        operations_count = {grp: 0 for grp in cdt_groups}
        total_operations = 0
        
        # Count operations from ALL assignments (including those with operations from uploaded data)
        for assignment in assignments:
            # Check if this assignment belongs to this pair
            if assignment.pair_id == pair_db_id:
                # If assignment has an operation, count it
                if assignment.operation:
                    # Use CDT code if available, otherwise fall back to operation name
                    if assignment.operation.cdt_code:
                        # Use the CDT code from the operation
                        code = assignment.operation.cdt_code.strip()
                        group = classify_cdt(code)
                        if group in operations_count:
                            operations_count[group] += 1
                            total_operations += 1
                    elif assignment.operation.name:
                        # Fallback: parse operation name for CDT codes
                        # Some cells may contain multiple codes separated by commas, e.g., "D6245,D6740"
                        codes = [c.strip() for c in assignment.operation.name.split(',') if c.strip()]
                        if not codes:
                            # Fallback to single string classify
                            codes = [assignment.operation.name.strip()]
                        for code in codes:
                            group = classify_cdt(code)
                            if group in operations_count:
                                operations_count[group] += 1
                                total_operations += 1
        
        # Debug: Print first pair's operation counts
        if pair_id == "G1P1":
            for op_name, count in operations_count.items():
                if count > 0:
                    print(f"  {op_name}: {count}")
        
        # Build summary
        pair_summary = {
            "pair_id": pair_id,
            "student1_name": f"{pair.student1.first_name} {pair.student1.last_name}",
            "student2_name": f"{pair.student2.first_name} {pair.student2.last_name}",
            "grade_combo": f"Grade {pair.student1.grade_level}-{pair.student2.grade_level}",
            "total_operations": total_operations,
            "operations_breakdown": operations_count
        }
        
        pair_summaries.append(pair_summary)
    
    print(f"=== RETURNING {len(pair_summaries)} PAIR SUMMARIES ===")
    return pair_summaries

@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Get a specific schedule assignment"""
    assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment

@router.put("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    assignment_data: dict,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Update a schedule assignment"""
    assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Update assignment fields
    for key, value in assignment_data.items():
        if hasattr(assignment, key):
            setattr(assignment, key, value)
    
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments/")
async def get_assignments(
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Get all schedule assignments"""
    # Use eager loading to include student data
    from sqlalchemy.orm import selectinload
    
    assignments = db.query(ScheduleAssignment).options(
        selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student1),
        selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student2),
        selectinload(ScheduleAssignment.operation),
        selectinload(ScheduleAssignment.week)
    ).all()
    
    # Build response with error handling
    result = []
    for i, a in enumerate(assignments):
        try:
            assignment_data = {
                "id": a.id,
                "week": {
                    "id": a.week.id,
                    "week_label": a.week.week_label
                } if a.week else None,
                "day": a.day,
                "time_slot": a.time_slot,
                "chair": a.chair,
                "operation": {
                    "id": a.operation.id,
                    "name": a.operation.name
                } if a.operation else None,
                "patient_id": a.patient_id,
                "patient_name": a.patient_name,
                "pair_id": a.pair.pair_id if a.pair else None,
                "student1_name": f"{a.pair.student1.first_name} {a.pair.student1.last_name}" if a.pair and a.pair.student1 else None,
                "student2_name": f"{a.pair.student2.first_name} {a.pair.student2.last_name}" if a.pair and a.pair.student2 else None,
                "grade_combo": f"Grade{a.pair.student1.grade_level}-{a.pair.student2.grade_level}" if a.pair and a.pair.student1 and a.pair.student2 else None,
                "pair": {
                    "id": a.pair.id,
                    "pair_id": a.pair.pair_id,
                    "student1": {
                        "id": a.pair.student1.id,
                        "student_id": a.pair.student1.student_id,
                        "first_name": a.pair.student1.first_name,
                        "last_name": a.pair.student1.last_name
                    },
                    "student2": {
                        "id": a.pair.student2.id,
                        "student_id": a.pair.student2.student_id,
                        "first_name": a.pair.student2.first_name,
                        "last_name": a.pair.student2.last_name
                    }
                } if a.pair else None,
                "status": a.status
            }
            result.append(assignment_data)
        except Exception as e:
            print(f"ERROR: Failed to process assignment {a.id}: {e}")
            # Add a minimal assignment data
            result.append({
                "id": a.id,
                "week": None,
                "day": a.day,
                "time_slot": a.time_slot,
                "chair": a.chair,
                "operation": None,
                "patient_id": a.patient_id,
                "patient_name": a.patient_name,
                "pair_id": None,
                "student1_name": None,
                "student2_name": None,
                "grade_combo": None,
                "pair": None,
                "status": a.status
            })
    
    return result

@router.get("/patient-assignment/{operation_id}")
async def get_patient_assignment_options(
    operation_id: int,
    week: Optional[str] = None,
    day: Optional[str] = None,
    time: Optional[str] = None,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Get prioritized pairs and available slots for patient assignment"""
    from sqlalchemy.orm import selectinload
    
    print(f"Operation ID: {operation_id}")
    print(f"Week filter: {week}")
    print(f"Day filter: {day}")
    print(f"Time filter: {time}")
    print(f"Current user: {current_user.username if current_user else 'None'}")
    print(f"User role: {current_user.role if current_user else 'None'}")
    print(f"API endpoint called successfully!")
    
    # Get the operation
    operation = db.query(OperationSchedule).filter(OperationSchedule.id == operation_id).first()
    if not operation:
        print(f"ERROR: Operation with ID {operation_id} not found")
        raise HTTPException(status_code=404, detail="Operation not found")
    
    print(f"Operation found: {operation.name}")
    
    # Get all pairs with their students
    pairs = db.query(StudentPair).options(
        selectinload(StudentPair.student1),
        selectinload(StudentPair.student2)
    ).all()
    
    print(f"Total pairs found: {len(pairs)}")
    
    # Get all assignments to count operations and find available slots
    assignments = db.query(ScheduleAssignment).options(
        selectinload(ScheduleAssignment.operation),
        selectinload(ScheduleAssignment.pair)
    ).all()
    
    print(f"Total assignments found: {len(assignments)}")
    
    # Debug: Check some sample assignments
    sample_assignments = assignments[:5] if assignments else []
    for i, a in enumerate(sample_assignments):
        print(f"Sample assignment {i+1}: ID={a.id}, pair_id={a.pair_id}, operation_id={a.operation_id}, patient_id='{a.patient_id}', patient_name='{a.patient_name}'")
    
    # Count operations for each pair (both specific and total)
    pair_operation_counts = {}
    pair_total_counts = {}
    
    for pair in pairs:
        pair_db_id = pair.id
        specific_operation_count = 0
        total_operation_count = 0
        
        for assignment in assignments:
            if assignment.pair_id == pair_db_id:
                if assignment.operation_id == operation_id:
                    specific_operation_count += 1
                if assignment.operation_id is not None:  # Any operation
                    total_operation_count += 1
        
        pair_operation_counts[pair.pair_id] = specific_operation_count
        pair_total_counts[pair.pair_id] = total_operation_count
    
    # Sort pairs by priority: first by specific operation count, then by total operation count
    # (ascending - fewer operations = higher priority)
    sorted_pairs = sorted(pairs, key=lambda p: (
        pair_operation_counts.get(p.pair_id, 0),  # Primary: specific operation count
        pair_total_counts.get(p.pair_id, 0)        # Secondary: total operation count
    ))
    
    # Find available slots for each pair, but limit to high priority pairs only
    result = []
    max_pairs_to_show = 10  # Only show top 10 pairs with fewest operations
    
    for i, pair in enumerate(sorted_pairs):
        if i >= max_pairs_to_show:
            break  # Only show high priority pairs
            
        pair_db_id = pair.id
        pair_id = pair.pair_id
        
        # Find available slots for this pair (slots with no operation assigned)
        available_slots = []
        for assignment in assignments:
            if (assignment.pair_id == pair_db_id and 
                assignment.operation_id is None and 
                (assignment.patient_id is None or assignment.patient_id == "") and 
                (assignment.patient_name is None or assignment.patient_name == "")):
                
                # Apply filters
                slot_week = assignment.week.week_label if assignment.week else None
                slot_day = assignment.day
                slot_time = assignment.time_slot
                
                # Debug: Log first few slots being checked
                if len(available_slots) < 3:
                    print(f"  Checking slot: week='{slot_week}', day='{slot_day}', time='{slot_time}'")
                    print(f"  Filters: week='{week}', day='{day}', time='{time}'")
                
                # Check week filter
                if week and week.strip() and slot_week != week:
                    if len(available_slots) < 3:
                        print(f"  -> Filtered out by week filter")
                    continue
                    
                # Check day filter
                if day and day.strip() and slot_day != day:
                    if len(available_slots) < 3:
                        print(f"  -> Filtered out by day filter")
                    continue
                    
                # Check time filter (AM/PM)
                if time and time.strip():
                    if time == "AM" and not slot_time.startswith(("8:", "9:", "10:", "11:")):
                        if len(available_slots) < 3:
                            print(f"  -> Filtered out by AM time filter")
                        continue
                    elif time == "PM" and not slot_time.startswith(("13:", "14:", "15:", "16:")):
                        if len(available_slots) < 3:
                            print(f"  -> Filtered out by PM time filter")
                        continue
                
                if len(available_slots) < 3:
                    print(f"  -> Slot passed all filters")
                
                available_slots.append({
                    "assignment_id": assignment.id,
                    "week": slot_week,
                    "day": slot_day,
                    "time_slot": slot_time,
                    "chair": assignment.chair
                })
        
        # Only include pairs that have available slots
        if available_slots:
            specific_count = pair_operation_counts.get(pair_id, 0)
            total_count = pair_total_counts.get(pair_id, 0)
            print(f"Pair {pair_id} (priority {i+1}) has {len(available_slots)} available slots - Specific: {specific_count}, Total: {total_count}")
            
            # Build response based on user role
            pair_data = {
                "pair_id": pair_id,
                "student1_name": f"{pair.student1.first_name} {pair.student1.last_name}",
                "student2_name": f"{pair.student2.first_name} {pair.student2.last_name}",
                "grade_combo": f"Grade {pair.student1.grade_level}-{pair.student2.grade_level}",
                "available_slots": available_slots
            }
            
            # Only include operation counts for admin and faculty roles
            if current_user.role in ['admin', 'faculty']:
                pair_data["specific_operation_count"] = specific_count
                pair_data["total_operation_count"] = total_count
            
            result.append(pair_data)
        else:
            specific_count = pair_operation_counts.get(pair_id, 0)
            total_count = pair_total_counts.get(pair_id, 0)
            print(f"Pair {pair_id} (priority {i+1}) has NO available slots - Specific: {specific_count}, Total: {total_count}")
    
    print(f"=== FINAL RESULT: {len(result)} pairs with available slots ===")
    return {
        "operation": {
            "id": operation.id,
            "name": operation.name
        },
        "prioritized_pairs": result
    }

class PatientAssignmentRequest(BaseModel):
    assignment_id: int
    patient_id: str
    patient_name: str
    operation_id: int

@router.post("/patient-assignment/assign")
async def assign_patient_to_slot(
    assignment_data: PatientAssignmentRequest,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Assign a patient to a specific slot"""
    
    print(f"Assignment ID: {assignment_data.assignment_id}")
    print(f"Patient ID: {assignment_data.patient_id}")
    print(f"Patient Name: {assignment_data.patient_name}")
    print(f"Operation ID: {assignment_data.operation_id}")
    print(f"Current user: {current_user.username if current_user else 'None'}")
    
    # Get the assignment
    assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.id == assignment_data.assignment_id).first()
    if not assignment:
        print(f"ERROR: Assignment with ID {assignment_data.assignment_id} not found")
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    print(f"Found assignment: ID={assignment.id}, operation_id={assignment.operation_id}, patient_id='{assignment.patient_id}', patient_name='{assignment.patient_name}'")
    
    # Check if slot already has a patient assigned
    if (assignment.patient_id is not None and assignment.patient_id != ""):
        print(f"ERROR: Slot already has a patient assigned")
        raise HTTPException(status_code=400, detail="Slot already has a patient assigned")
    
    # Update the assignment
    assignment.operation_id = assignment_data.operation_id
    assignment.patient_id = assignment_data.patient_id
    assignment.patient_name = assignment_data.patient_name
    assignment.status = "assigned"
    
    print(f"Updated assignment: operation_id={assignment.operation_id}, patient_id='{assignment.patient_id}', patient_name='{assignment.patient_name}'")
    
    try:
        db.commit()
        return {"message": "Patient assigned successfully", "assignment_id": assignment_data.assignment_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign patient: {str(e)}")

@router.get("/operations/")
async def get_operations(
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    """Get all operations"""
    operations = db.query(OperationSchedule).all()
    return [
        {
            "id": o.id,
            "name": o.name,
            "description": o.description,
            "cdt_code": o.cdt_code
        }
        for o in operations
    ]

# Create a new operation (treatment)
@router.post("/operations/")
async def create_operation(
    payload: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    name = (payload.get("name") or "").strip() or None
    description = (payload.get("description") or "").strip() or None
    cdt_code = (payload.get("cdt_code") or "").strip() or None
    
    # At least one of name or cdt_code must be provided
    if not name and not cdt_code:
        raise HTTPException(status_code=400, detail="Either name or CDT code is required")

    # Prevent duplicates by exact name match (only if name is provided)
    if name:
        existing = db.query(OperationSchedule).filter(OperationSchedule.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Treatment with this name already exists")

    op = OperationSchedule(name=name, description=description, cdt_code=cdt_code)
    db.add(op)
    db.commit()
    db.refresh(op)
    return {"id": op.id, "name": op.name, "description": op.description, "cdt_code": op.cdt_code}

# Update an existing operation
@router.put("/operations/{operation_id}")
async def update_operation(
    operation_id: int,
    payload: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    op = db.query(OperationSchedule).filter(OperationSchedule.id == operation_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")

    name = payload.get("name")
    description = payload.get("description")
    cdt_code = payload.get("cdt_code")
    if name is not None:
        name = name.strip() or None
        op.name = name
    if description is not None:
        op.description = description.strip() or None
    if cdt_code is not None:
        op.cdt_code = cdt_code.strip() or None
    
    # Ensure at least one of name or cdt_code is provided after update
    if not op.name and not op.cdt_code:
        raise HTTPException(status_code=400, detail="Either name or CDT code must be provided")

    db.commit()
    db.refresh(op)
    return {"id": op.id, "name": op.name, "description": op.description, "cdt_code": op.cdt_code}

# Delete an operation
@router.delete("/operations/{operation_id}")
async def delete_operation(
    operation_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    op = db.query(OperationSchedule).filter(OperationSchedule.id == operation_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")

    db.delete(op)
    db.commit()
    return {"message": "Operation deleted successfully"}
