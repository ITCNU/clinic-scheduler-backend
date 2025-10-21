from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random

from ..database import get_db
from ..models.user import User
from ..models.student_schedule import StudentSchedule, StudentPair
from ..core.permissions import require_admin, require_faculty_or_admin

router = APIRouter(prefix="/api", tags=["pair-management"])

@router.post("/pairs/create")
async def create_pairs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create student pairs based on grade level optimization"""
    try:
        # Get all students (excluding externship)
        students = db.query(StudentSchedule).filter(StudentSchedule.externship == False).all()
        
        if len(students) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 students to create pairs")
        
        # Clear existing pairs
        db.query(StudentPair).delete()
        
        # Reset pair_id and group_number for all students
        for student in students:
            student.pair_id = None
            student.group_number = None
        
        # Group students by grade level
        grade_groups = {}
        for student in students:
            grade = student.grade_level
            if grade not in grade_groups:
                grade_groups[grade] = []
            grade_groups[grade].append(student)
        
        # Shuffle each grade group
        for grade in grade_groups:
            random.shuffle(grade_groups[grade])
        
        # Create two groups optimized for cross-grade pairing
        group1 = []
        group2 = []
        
        # Ensure both groups get Grade 2 students
        if 2 in grade_groups:
            grade2_students = grade_groups[2]
            total_grade2 = len(grade2_students)
            g1_count = total_grade2 // 2
            group1.extend(grade2_students[:g1_count])
            group2.extend(grade2_students[g1_count:])
        
        # Distribute Grade 3 and 4 students
        for grade in [3, 4]:
            if grade in grade_groups:
                students_list = grade_groups[grade]
                g1_count = len(students_list) // 2
                group1.extend(students_list[:g1_count])
                group2.extend(students_list[g1_count:])
        
        # Distribute other grades
        for grade, students_list in grade_groups.items():
            if grade not in [2, 3, 4]:
                g1_count = len(students_list) // 2
                group1.extend(students_list[:g1_count])
                group2.extend(students_list[g1_count:])
        
        # Shuffle groups
        random.shuffle(group1)
        random.shuffle(group2)

        # Ensure both groups have even counts to avoid unpaired leftovers
        if len(group1) % 2 == 1 and len(group2) % 2 == 1:
            # Move one student from the larger group to the other
            if len(group1) >= len(group2) and group1:
                moved_student = group1.pop()
                group2.append(moved_student)
            elif group2:
                moved_student = group2.pop()
                group1.append(moved_student)
        
        # Assign group numbers
        for student in group1:
            student.group_number = 1
        for student in group2:
            student.group_number = 2
        
        # Create pairs within each group
        pairs_created = 0
        pair_counter = {'G1': 1, 'G2': 1}
        
        for group_idx, group_students in enumerate([group1, group2], 1):
            group_id = f"G{group_idx}"
            if len(group_students) < 2:
                continue
            
            # Group by grade level within this group
            group_grade_groups = {}
            for student in group_students:
                grade = student.grade_level
                if grade not in group_grade_groups:
                    group_grade_groups[grade] = []
                group_grade_groups[grade].append(student)
            
            # Create pairs in priority order: 4-4, 3-3 (same-grade only)
            
            # 4-4 pairs
            if 4 in group_grade_groups and len(group_grade_groups[4]) >= 2:
                while len(group_grade_groups[4]) >= 2:
                    pair_id = f"{group_id}P{pair_counter[group_id]}"
                    pair_counter[group_id] += 1
                    
                    student1 = group_grade_groups[4].pop()
                    student2 = group_grade_groups[4].pop()
                    
                    # Create pair record
                    pair = StudentPair(
                        pair_id=pair_id,
                        student1_id=student1.id,
                        student2_id=student2.id,
                        group_number=group_idx
                    )
                    db.add(pair)
                    
                    # Update students with pair_id
                    student1.pair_id = pair_id
                    student2.pair_id = pair_id
                    
                    pairs_created += 1
            
            # 3-3 pairs
            if 3 in group_grade_groups and len(group_grade_groups[3]) >= 2:
                while len(group_grade_groups[3]) >= 2:
                    pair_id = f"{group_id}P{pair_counter[group_id]}"
                    pair_counter[group_id] += 1
                    
                    student1 = group_grade_groups[3].pop()
                    student2 = group_grade_groups[3].pop()
                    
                    pair = StudentPair(
                        pair_id=pair_id,
                        student1_id=student1.id,
                        student2_id=student2.id,
                        group_number=group_idx
                    )
                    db.add(pair)
                    
                    student1.pair_id = pair_id
                    student2.pair_id = pair_id
                    
                    pairs_created += 1
            
            # No leftover pairing - only same-grade pairs allowed
            # Any remaining students will remain unpaired
        
        db.commit()
        
        # Calculate statistics
        g1_pairs = db.query(StudentPair).filter(StudentPair.group_number == 1).count()
        g2_pairs = db.query(StudentPair).filter(StudentPair.group_number == 2).count()
        
        g1_students = db.query(StudentSchedule).filter(StudentSchedule.group_number == 1).count()
        g2_students = db.query(StudentSchedule).filter(StudentSchedule.group_number == 2).count()
        
        return {
            "message": "Student pairs created successfully",
            "count": pairs_created,
            "statistics": {
                "group1_pairs": g1_pairs,
                "group2_pairs": g2_pairs,
                "group1_students": g1_students,
                "group2_students": g2_students,
                "total_pairs": pairs_created
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating pairs: {str(e)}")

@router.get("/pairs/stats")
async def get_pair_statistics(
    current_user: User = Depends(require_faculty_or_admin),
    db: Session = Depends(get_db)
):
    """Get pair creation statistics"""
    try:
        # Get all students
        students = db.query(StudentSchedule).filter(StudentSchedule.externship == False).all()
        pairs = db.query(StudentPair).all()
        
        # Group statistics
        group1_students = [s for s in students if s.group_number == 1]
        group2_students = [s for s in students if s.group_number == 2]
        
        group1_pairs = [p for p in pairs if p.group_number == 1]
        group2_pairs = [p for p in pairs if p.group_number == 2]
        
        # Grade level statistics
        grade_stats = {}
        for student in students:
            grade = student.grade_level
            if grade not in grade_stats:
                grade_stats[grade] = {"total": 0, "group1": 0, "group2": 0, "paired": 0}
            grade_stats[grade]["total"] += 1
            if student.group_number == 1:
                grade_stats[grade]["group1"] += 1
            elif student.group_number == 2:
                grade_stats[grade]["group2"] += 1
            if student.pair_id:
                grade_stats[grade]["paired"] += 1
        
        # Cross-grade pair statistics
        cross_grade_pairs = 0
        for pair in pairs:
            student1 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student1_id).first()
            student2 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student2_id).first()
            if student1 and student2 and student1.grade_level != student2.grade_level:
                cross_grade_pairs += 1
        
        return {
            "total_students": len(students),
            "total_pairs": len(pairs),
            "unpaired_students": len(students) - len(pairs) * 2,
            "group_statistics": {
                "group1": {
                    "students": len(group1_students),
                    "pairs": len(group1_pairs)
                },
                "group2": {
                    "students": len(group2_students),
                    "pairs": len(group2_pairs)
                }
            },
            "grade_statistics": grade_stats,
            "cross_grade_pairs": cross_grade_pairs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.put("/pairs/{pair_id}")
async def update_pair(
    pair_id: int,
    student1_id: int,
    student2_id: int,
    group_number: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update an existing pair's students and group. Also updates students' pair_id fields."""
    pair = db.query(StudentPair).filter(StudentPair.id == pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")

    # Clear old students' pair_id if they change
    if pair.student1_id != student1_id:
        old1 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student1_id).first()
        if old1:
            old1.pair_id = None
    if pair.student2_id != student2_id:
        old2 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student2_id).first()
        if old2:
            old2.pair_id = None

    # Set new values
    pair.student1_id = student1_id
    pair.student2_id = student2_id
    pair.group_number = group_number

    # Update students to point to this pair_id string
    s1 = db.query(StudentSchedule).filter(StudentSchedule.id == student1_id).first()
    s2 = db.query(StudentSchedule).filter(StudentSchedule.id == student2_id).first()
    if not s1 or not s2:
        raise HTTPException(status_code=400, detail="Invalid student IDs")
    s1.pair_id = pair.pair_id
    s2.pair_id = pair.pair_id

    db.commit()
    return {"message": "Pair updated"}


@router.post("/pairs/manual")
async def create_pair_manual(
    student1_id: int,
    student2_id: int,
    group_number: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Manually create one pair from two students."""
    s1 = db.query(StudentSchedule).filter(StudentSchedule.id == student1_id).first()
    s2 = db.query(StudentSchedule).filter(StudentSchedule.id == student2_id).first()
    if not s1 or not s2:
        raise HTTPException(status_code=400, detail="Invalid student IDs")
    if s1.pair_id or s2.pair_id:
        raise HTTPException(status_code=400, detail="One or both students already paired")

    # Build next pair id within group
    prefix = f"G{group_number}"
    existing = db.query(StudentPair).filter(StudentPair.group_number == group_number).all()
    # Reuse the smallest available pair number within the group (fill gaps)
    used_numbers = set()
    for p in existing:
        try:
            used_numbers.add(int(p.pair_id.split('P')[-1]))
        except Exception:
            continue
    next_num = 1
    while next_num in used_numbers:
        next_num += 1
    pair_id_str = f"{prefix}P{next_num}"

    pair = StudentPair(
        pair_id=pair_id_str,
        student1_id=s1.id,
        student2_id=s2.id,
        group_number=group_number
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)

    s1.pair_id = pair.pair_id
    s2.pair_id = pair.pair_id
    db.commit()
    return {"message": "Pair created", "id": pair.id, "pair_id": pair.pair_id}


@router.delete("/pairs/{pair_id}")
async def delete_pair(
    pair_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    pair = db.query(StudentPair).filter(StudentPair.id == pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="Pair not found")

    # Clear students' pair_id
    s1 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student1_id).first()
    s2 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student2_id).first()
    if s1:
        s1.pair_id = None
    if s2:
        s2.pair_id = None

    db.delete(pair)
    db.commit()
    return {"message": "Pair deleted"}
