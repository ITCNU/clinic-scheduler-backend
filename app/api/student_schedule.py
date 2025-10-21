from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..database import get_db
from ..models.student_schedule import (
    StudentSchedule, StudentPair, OperationSchedule, 
    ScheduleWeekSchedule, ScheduleAssignment, OperationTracking, AppSettings
)
from ..core.permissions import require_admin, require_faculty_or_admin, require_staff_or_admin, get_current_user
from ..schemas.student_schedule import (
    StudentScheduleCreate, StudentScheduleResponse,
    StudentPairCreate, StudentPairResponse,
    OperationScheduleCreate, OperationScheduleResponse,
    ScheduleWeekCreate, ScheduleWeekResponse,
    ScheduleAssignmentCreate, ScheduleAssignmentResponse, ScheduleAssignmentUpdate,
    OperationTrackingResponse
)

router = APIRouter(prefix="/student-schedule", tags=["student-schedule"])


# Students endpoints
@router.post("/students/", response_model=StudentScheduleResponse)
def create_student(
    student: StudentScheduleCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create a new student"""
    db_student = StudentSchedule(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/students/", response_model=List[StudentScheduleResponse])
def get_students(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(require_faculty_or_admin)
):
    """Get all students"""
    students = db.query(StudentSchedule).offset(skip).limit(limit).all()
    return students


@router.get("/students/{student_id}", response_model=StudentScheduleResponse)
def get_student(
    student_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(require_faculty_or_admin)
):
    """Get a specific student"""
    student = db.query(StudentSchedule).filter(StudentSchedule.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# Student pairs endpoints
@router.post("/pairs/", response_model=StudentPairResponse)
def create_student_pair(
    pair: StudentPairCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create a new student pair"""
    db_pair = StudentPair(**pair.dict())
    db.add(db_pair)
    db.commit()
    db.refresh(db_pair)
    return db_pair


@router.get("/pairs/", response_model=List[StudentPairResponse])
def get_student_pairs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(require_faculty_or_admin)
):
    """Get all student pairs"""
    pairs = db.query(StudentPair).offset(skip).limit(limit).all()
    return pairs


# Operations endpoints
@router.post("/operations/", response_model=OperationScheduleResponse)
def create_operation(
    operation: OperationScheduleCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create a new operation"""
    db_operation = OperationSchedule(**operation.dict())
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation


@router.put("/operations/{operation_id}", response_model=OperationScheduleResponse)
def update_operation(
    operation_id: int,
    operation_update: OperationScheduleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Update an existing operation (rename/description)."""
    db_operation = db.query(OperationSchedule).filter(OperationSchedule.id == operation_id).first()
    if not db_operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    for field, value in operation_update.dict().items():
        setattr(db_operation, field, value)

    db.commit()
    db.refresh(db_operation)
    return db_operation


@router.delete("/operations/{operation_id}")
def delete_operation(
    operation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Delete an operation."""
    db_operation = db.query(OperationSchedule).filter(OperationSchedule.id == operation_id).first()
    if not db_operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    db.delete(db_operation)
    db.commit()
    return {"message": "Operation deleted"}

@router.get("/operations/")
def get_operations(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(require_staff_or_admin)
):
    """Get all operations"""
    print("DEBUG: Endpoint called")
    operations = db.query(OperationSchedule).offset(skip).limit(limit).all()
    print(f"DEBUG: Found {len(operations)} operations")
    result = []
    for op in operations:
        result.append({
            "id": op.id,
            "name": op.name,
            "description": op.description,
            "created_at": op.created_at.isoformat() if op.created_at else None
        })
    print(f"DEBUG: Returning {len(result)} operations")
    return result


# Schedule weeks endpoints
@router.post("/weeks/", response_model=ScheduleWeekResponse)
def create_schedule_week(
    week: ScheduleWeekCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create a new schedule week"""
    db_week = ScheduleWeekSchedule(**week.dict())
    db.add(db_week)
    db.commit()
    db.refresh(db_week)
    return db_week


@router.get("/weeks/", response_model=List[ScheduleWeekResponse])
def get_schedule_weeks(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user = Depends(require_staff_or_admin)
):
    """Get all schedule weeks"""
    weeks = db.query(ScheduleWeekSchedule).offset(skip).limit(limit).all()
    return weeks


# Schedule assignments endpoints
@router.post("/assignments/", response_model=ScheduleAssignmentResponse)
def create_schedule_assignment(
    assignment: ScheduleAssignmentCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_staff_or_admin)
):
    """Create a new schedule assignment"""
    db_assignment = ScheduleAssignment(**assignment.dict())
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


@router.get("/assignments/", response_model=List[ScheduleAssignmentResponse])
def get_schedule_assignments(
    skip: int = 0, 
    limit: int = 100, 
    week_id: int = None,
    pair_id: int = None,
    student_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all schedule assignments with optional filtering"""
    from sqlalchemy.orm import selectinload
    query = db.query(ScheduleAssignment).options(
        selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student1),
        selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student2),
        selectinload(ScheduleAssignment.operation),
        selectinload(ScheduleAssignment.week)
    )
    
    # If the user is a student, restrict results to their assignments only
    if current_user and getattr(current_user, 'role', None) == 'student':
        # Find this student's record by username (stored as student_id)
        student = db.query(StudentSchedule).filter(StudentSchedule.student_id == current_user.username).first()
        if student:
            pair_ids = [p.id for p in db.query(StudentPair).filter(
                (StudentPair.student1_id == student.id) | (StudentPair.student2_id == student.id)
            ).all()]
            if pair_ids:
                query = query.filter(ScheduleAssignment.pair_id.in_(pair_ids))
            else:
                return []
        else:
            return []
    
    if week_id:
        query = query.filter(ScheduleAssignment.week_id == week_id)
    if pair_id:
        query = query.filter(ScheduleAssignment.pair_id == pair_id)
    if student_id:
        # Filter by student ID - find pairs where the student is either student1 or student2
        query = query.join(StudentPair).join(StudentSchedule, 
            (StudentPair.student1_id == StudentSchedule.id) | 
            (StudentPair.student2_id == StudentSchedule.id)
        ).filter(StudentSchedule.student_id == student_id)
    
    assignments = query.offset(skip).limit(limit).all()
    return assignments

@router.get("/assignments/student/{student_id}", response_model=List[ScheduleAssignmentResponse])
def get_student_assignments(
    student_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get schedule assignments for a specific student"""
    # Students can only see their own assignments
    if current_user.role == 'student' and current_user.username != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only view their own assignments"
        )
    
    # Find the student record
    student = db.query(StudentSchedule).filter(StudentSchedule.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Find pairs where this student is either student1 or student2
    pairs = db.query(StudentPair).filter(
        (StudentPair.student1_id == student.id) | 
        (StudentPair.student2_id == student.id)
    ).all()
    
    if not pairs:
        return []
    
    # Get assignments for these pairs
    pair_ids = [pair.id for pair in pairs]
    assignments = db.query(ScheduleAssignment).filter(
        ScheduleAssignment.pair_id.in_(pair_ids)
    ).all()
    
    return assignments


@router.put("/assignments/{assignment_id}", response_model=ScheduleAssignmentResponse)
def update_schedule_assignment(
    assignment_id: int,
    assignment_data: ScheduleAssignmentUpdate, 
    db: Session = Depends(get_db),
    current_user = Depends(require_staff_or_admin)
):
    """Update a schedule assignment"""
    db_assignment = db.query(ScheduleAssignment).filter(ScheduleAssignment.id == assignment_id).first()
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Update assignment fields (only non-None values)
    update_data = assignment_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(db_assignment, key):
            setattr(db_assignment, key, value)
    
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


# Operation tracking endpoints
@router.get("/operation-tracking/", response_model=List[OperationTrackingResponse])
def get_operation_tracking(
    skip: int = 0, 
    limit: int = 100, 
    pair_id: int = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_faculty_or_admin)
):
    """Get operation tracking data"""
    query = db.query(OperationTracking)
    
    if pair_id:
        query = query.filter(OperationTracking.pair_id == pair_id)
    
    tracking = query.offset(skip).limit(limit).all()
    return tracking


# Bulk operations for importing data from Excel
@router.post("/import/students")
def import_students(
    students: List[StudentScheduleCreate], 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Import multiple students from Excel data"""
    created_students = []
    for student_data in students:
        db_student = StudentSchedule(**student_data.dict())
        db.add(db_student)
        created_students.append(db_student)
    
    db.commit()
    for student in created_students:
        db.refresh(student)
    
    return {"message": f"Successfully imported {len(created_students)} students"}


@router.post("/import/schedule")
def import_schedule(
    assignments: List[ScheduleAssignmentCreate], 
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Import schedule assignments from Excel data"""
    created_assignments = []
    for assignment_data in assignments:
        db_assignment = ScheduleAssignment(**assignment_data.dict())
        db.add(db_assignment)
        created_assignments.append(db_assignment)
    
    db.commit()
    for assignment in created_assignments:
        db.refresh(assignment)
    
    return {"message": f"Successfully imported {len(created_assignments)} schedule assignments"}


# Initialize default operations
@router.post("/initialize/default-operations")
def initialize_default_operations(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Initialize the default operations - REMOVED: No default operations"""
    # No default operations - operations are created as needed from uploaded data
    return {"message": "No default operations to initialize - operations are created as needed from uploaded data"}


# Get app settings
@router.get("/settings/{key}")
def get_app_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Get an app setting by key"""
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value, "description": setting.description}


# Update app settings
@router.put("/settings/{key}")
def update_app_setting(
    key: str,
    value: str,
    description: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Update an app setting"""
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = AppSettings(key=key, value=value, description=description)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": setting.value, "description": setting.description}
