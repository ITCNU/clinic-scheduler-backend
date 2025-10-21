from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
from datetime import datetime, timedelta
import re

from ..database import get_db
from ..models.user import User
from ..models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule
from ..core.permissions import require_admin, require_faculty_or_admin

router = APIRouter(prefix="/api", tags=["schedule-generation"])

def _is_pair_available_for_week(pair, week_obj):
    """Check if a pair is available for assignment during a specific week (not on externship)."""
    # Parse dates from week_label if start_date/end_date are not set
    week_start = None
    week_end = None
    
    if week_obj.start_date and week_obj.end_date:
        # Use database dates if available
        week_start = week_obj.start_date.date() if hasattr(week_obj.start_date, 'date') else week_obj.start_date
        week_end = week_obj.end_date.date() if hasattr(week_obj.end_date, 'date') else week_obj.end_date
    elif week_obj.week_label:
        # Parse dates from week_label (e.g., "10/27/2025-10/31/2025")
        try:
            from datetime import datetime
            date_parts = week_obj.week_label.split('-')
            if len(date_parts) == 2:
                week_start = datetime.strptime(date_parts[0].strip(), '%m/%d/%Y').date()
                week_end = datetime.strptime(date_parts[1].strip(), '%m/%d/%Y').date()
        except:
            # If parsing fails, assume pair is available
            return True
    
    if not week_start or not week_end:
        # If we can't determine week dates, assume pair is available
        return True
    
    # Get externship dates for both students
    externship_start1 = pair.student1.externship_start_date if pair.student1 else None
    externship_end1 = pair.student1.externship_end_date if pair.student1 else None
    externship_start2 = pair.student2.externship_start_date if pair.student2 else None
    externship_end2 = pair.student2.externship_end_date if pair.student2 else None
    
    # Check if both students are available during this week
    student1_available = True
    student2_available = True
    
    # Student 1 availability check
    if externship_start1 and externship_end1:
        # Student has externship dates - check if this week overlaps with externship period
        # If week overlaps with externship, student is NOT available
        if not (externship_end1 < week_start or externship_start1 > week_end):
            student1_available = False
    
    # Student 2 availability check  
    if externship_start2 and externship_end2:
        # Student has externship dates - check if this week overlaps with externship period
        # If week overlaps with externship, student is NOT available
        if not (externship_end2 < week_start or externship_start2 > week_end):
            student2_available = False
    
    # Both students must be available for the pair to be assigned
    return student1_available and student2_available

def _get_week_date_range(week_num: int):
    """Generate date range for a week number (Monday-Friday)."""
    start_date = datetime(2025, 10, 27)  # Monday, October 27, 2025
    week_monday = start_date + timedelta(weeks=week_num - 1)
    week_friday = week_monday + timedelta(days=4)
    # Use consistent formatting: MM/DD/YYYY-MM/DD/YYYY
    return f"{week_monday.strftime('%m/%d/%Y')}-{week_friday.strftime('%m/%d/%Y')}"

def _is_pair_allowed_for_slot(pair, day, slot, db, week_obj=None):
    """Check if a pair is allowed for a specific day and time slot based on grade level restrictions and externship dates."""
    student1 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student1_id).first()
    student2 = db.query(StudentSchedule).filter(StudentSchedule.id == pair.student2_id).first()
    
    if not student1 or not student2:
        return False
    
    student1_grade = student1.grade_level
    student2_grade = student2.grade_level
    
    # Normalize slot to handle different dash characters
    norm_slot = _normalize_time_slot(slot)
    AM_SLOTS_NORM = ["8:00-9:20", "9:20-10:40", "10:40-12:00"]
    PM_SLOTS_NORM = ["13:00-14:20", "14:20-15:40", "15:40-17:00"]

    # Check externship date availability if week_obj is provided
    if week_obj and week_obj.start_date and week_obj.end_date:
        # Get externship dates for both students
        externship_start1 = student1.externship_start_date
        externship_end1 = student1.externship_end_date
        externship_start2 = student2.externship_start_date
        externship_end2 = student2.externship_end_date
        
        # Convert week dates to date objects for comparison
        week_start = week_obj.start_date.date() if hasattr(week_obj.start_date, 'date') else week_obj.start_date
        week_end = week_obj.end_date.date() if hasattr(week_obj.end_date, 'date') else week_obj.end_date
        
        # Check if both students are available during this week
        student1_available = True
        student2_available = True
        
        # Student 1 availability check
        if externship_start1 and externship_end1:
            # Student has externship dates - check if they overlap with this week
            if externship_end1 < week_start or externship_start1 > week_end:
                student1_available = False
        # If no externship dates, student is available
        
        # Student 2 availability check  
        if externship_start2 and externship_end2:
            # Student has externship dates - check if they overlap with this week
            if externship_end2 < week_start or externship_start2 > week_end:
                student2_available = False
        # If no externship dates, student is available
        
        # Both students must be available for the pair to be assigned
        if not student1_available or not student2_available:
            return False

    # Monday morning restriction: REMOVED - Clinic operations now allowed on Monday AM
    
    # Thursday morning restriction: No Grade 3 students
    if day == "Thursday" and norm_slot in AM_SLOTS_NORM:
        if student1_grade == 3 or student2_grade == 3:
            return False
            
    # Friday afternoon restriction: No Grade 3 or Grade 4 students
    if day == "Friday" and norm_slot in PM_SLOTS_NORM:
        if student1_grade == 3 or student2_grade == 3 or student1_grade == 4 or student2_grade == 4:
            return False
            
    return True

def _pick_pairs_for_period_chairs(week_name, day, period, pairs, pair_period_assignments, pair_assignment_counts, db, week_obj=None):
    """Pick pairs for each chair in a specific period (AM or PM)."""
    am_slots = ["8:00–9:20", "9:20–10:40", "10:40–12:00"]
    pm_slots = ["13:00–14:20", "14:20–15:40", "15:40–17:00"]
    
    period_slots = am_slots if period == 'am' else pm_slots
    
    # Separate pairs by group
    group1_candidates = []
    group2_candidates = []
    
    for pair in pairs:
        # Skip if already assigned to this period on this day
        period_key = 'am_days' if period == 'am' else 'pm_days'
        if (week_name, day) in pair_period_assignments.get(pair.pair_id, {}).get(period_key, set()):
            continue
            
        # Check grade level restrictions and externship availability for any slot in this period
        period_allowed = True
        for slot in period_slots:
            if not _is_pair_allowed_for_slot(pair, day, slot, db, week_obj):
                period_allowed = False
                break
        
        if not period_allowed:
            continue
        
        # Determine which group this pair belongs to
        if pair.group_number == 1:
            group1_candidates.append(pair)
        else:
            group2_candidates.append(pair)
    
    # Sort candidates by assignment count (fairness)
    group1_candidates.sort(key=lambda x: pair_assignment_counts.get(x.pair_id, 0))
    group2_candidates.sort(key=lambda x: pair_assignment_counts.get(x.pair_id, 0))
    
    # Select up to 34 pairs total (17 for Group 1, 17 for Group 2)
    selected_pairs = []
    used_pair_ids = set()
    
    # Calculate how many pairs we need for each group
    group1_needed = min(17, len(group1_candidates))
    group2_needed = min(17, len(group2_candidates))
    
    # Add Group 1 pairs (for chairs 1-17)
    for i in range(group1_needed):
        pair = group1_candidates[i]
        if pair.pair_id not in used_pair_ids:
            selected_pairs.append(pair)
            used_pair_ids.add(pair.pair_id)
    
    # Add Group 2 pairs (for chairs 18-34)
    for i in range(group2_needed):
        pair = group2_candidates[i]
        if pair.pair_id not in used_pair_ids:
            selected_pairs.append(pair)
            used_pair_ids.add(pair.pair_id)
    
    # If we don't have enough pairs from the target groups, fill with available pairs
    remaining_needed = 34 - len(selected_pairs)
    if remaining_needed > 0:
        all_available = group1_candidates + group2_candidates
        all_available.sort(key=lambda x: pair_assignment_counts.get(x.pair_id, 0))
        
        for pair in all_available:
            if pair.pair_id not in used_pair_ids and len(selected_pairs) < 34:
                selected_pairs.append(pair)
                used_pair_ids.add(pair.pair_id)
    
    return selected_pairs

def _get_chair_number(chair_name):
    """Extract chair number from chair name (e.g., 'Chair 15' -> 15)"""
    try:
        return int(chair_name.split()[-1])
    except:
        return 0

def _normalize_time_slot(slot: str) -> str:
    """Normalize time slot string by converting various dashes to a simple hyphen and trimming whitespace."""
    if not slot:
        return ""
    return re.sub(r'[â€"–—]', '-', slot).strip()

def _is_am_time_slot(slot: str) -> bool:
    norm = _normalize_time_slot(slot)
    return norm in ["8:00-9:20", "9:20-10:40", "10:40-12:00"]

def _is_pm_time_slot(slot: str) -> bool:
    norm = _normalize_time_slot(slot)
    return norm in ["13:00-14:20", "14:20-15:40", "15:40-17:00"]

def _is_pair_allowed_for_chair(pair, chair_name):
    """
    Check if a pair is allowed for a specific chair based on group assignment.
    
    Rules:
    - Group 1 pairs: Chairs 1-17
    - Group 2 pairs: Chairs 18-34
    """
    chair_number = _get_chair_number(chair_name)
    pair_group = pair.group_number
    
    # Group 1 pairs can only be assigned to chairs 1-17
    if pair_group == 1:
        if chair_number >= 1 and chair_number <= 17:
            return True
        else:
            print(f"DEBUG: REJECTED pair {pair.pair_id} (Group 1) for {chair_name} (Group 1 only chairs 1-17)")
            return False
    
    # Group 2 pairs can only be assigned to chairs 18-34
    elif pair_group == 2:
        if chair_number >= 18 and chair_number <= 34:
            return True
        else:
            print(f"DEBUG: REJECTED pair {pair.pair_id} (Group 2) for {chair_name} (Group 2 only chairs 18-34)")
            return False
    
    return False

def _is_pair_allowed_for_time_slot(pair, day, time_period, week_obj=None):
    """
    Check if a pair is allowed for a specific day and time period based on grade restrictions and externship dates.
    
    Rules:
    - Thursday AM: No Grade 3 students allowed
    - Friday PM: No Grade 3 or Grade 4 students allowed
    - Externship dates: Both students must be available during the week
    """
    # Get student grades from the pair
    student1_grade = pair.student1.grade_level if pair.student1 else None
    student2_grade = pair.student2.grade_level if pair.student2 else None
    
    # Debug logging
    print(f"DEBUG: Checking pair {pair.pair_id} for {day} {time_period}: grades {student1_grade}, {student2_grade}")
    
    # Check externship date availability if week_obj is provided
    if week_obj and week_obj.start_date and week_obj.end_date:
        # Get externship dates for both students
        externship_start1 = pair.student1.externship_start_date if pair.student1 else None
        externship_end1 = pair.student1.externship_end_date if pair.student1 else None
        externship_start2 = pair.student2.externship_start_date if pair.student2 else None
        externship_end2 = pair.student2.externship_end_date if pair.student2 else None
        
        # Convert week dates to date objects for comparison
        week_start = week_obj.start_date.date() if hasattr(week_obj.start_date, 'date') else week_obj.start_date
        week_end = week_obj.end_date.date() if hasattr(week_obj.end_date, 'date') else week_obj.end_date
        
        # Check if both students are available during this week
        student1_available = True
        student2_available = True
        
        # Student 1 availability check
        if externship_start1 and externship_end1:
            # Student has externship dates - check if this week overlaps with externship period
            # If week overlaps with externship, student is NOT available
            if not (externship_end1 < week_start or externship_start1 > week_end):
                student1_available = False
                print(f"DEBUG: REJECTED pair {pair.pair_id} - Student1 is on externship ({externship_start1} to {externship_end1}) during week ({week_start} to {week_end})")
        # If no externship dates, student is available
        
        # Student 2 availability check  
        if externship_start2 and externship_end2:
            # Student has externship dates - check if this week overlaps with externship period
            # If week overlaps with externship, student is NOT available
            if not (externship_end2 < week_start or externship_start2 > week_end):
                student2_available = False
                print(f"DEBUG: REJECTED pair {pair.pair_id} - Student2 is on externship ({externship_start2} to {externship_end2}) during week ({week_start} to {week_end})")
        # If no externship dates, student is available
        
        # Both students must be available for the pair to be assigned
        if not student1_available or not student2_available:
            return False
    
    # Thursday AM restriction: No Grade 3 students
    if day == "Thursday" and time_period == "AM":
        if student1_grade == 3 or student2_grade == 3:
            print(f"DEBUG: REJECTED pair {pair.pair_id} for Thursday AM (has Grade 3 student)")
            return False
    
    # Friday PM restriction: No Grade 3 or Grade 4 students  
    if day == "Friday" and time_period == "PM":
        if student1_grade == 3 or student2_grade == 3 or student1_grade == 4 or student2_grade == 4:
            print(f"DEBUG: REJECTED pair {pair.pair_id} for Friday PM (has Grade 3 or Grade 4 student)")
            return False
    
    print(f"DEBUG: ACCEPTED pair {pair.pair_id} for {day} {time_period}")
    return True

@router.post("/schedule/generate")
async def generate_clinic_schedule(
    weeks: int = 7,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Generate a complete clinic schedule for the specified number of weeks"""
    try:
        print("=" * 50)
        print("SCHEDULE GENERATION STARTED!")
        print("DEBUG: Enhanced grade constraint checking is ACTIVE!")
        print("DEBUG: NEW CODE WITH BACKUP CHAIR EXCLUSION AND FALLBACK LOGIC!")
        print("=" * 50)
        # Get all pairs with eager loading for student data
        from sqlalchemy.orm import selectinload
        pairs = db.query(StudentPair).options(
            selectinload(StudentPair.student1),
            selectinload(StudentPair.student2)
        ).all()
        if not pairs:
            raise HTTPException(status_code=400, detail="No pairs available. Please create pairs first.")
        
        # Debug: Show first few pairs and their grades
        print(f"DEBUG: Found {len(pairs)} pairs total")
        for i, pair in enumerate(pairs[:5]):  # Show first 5 pairs
            student1_grade = pair.student1.grade_level if pair.student1 else None
            student2_grade = pair.student2.grade_level if pair.student2 else None
            print(f"DEBUG: Pair {pair.pair_id}: Student1 Grade {student1_grade}, Student2 Grade {student2_grade}")
        
        # Get all operations
        operations = db.query(OperationSchedule).all()
        if not operations:
            raise HTTPException(status_code=400, detail="No operations available. Please initialize operations first.")
        
        # Keep existing slots from uploaded file, but clear pair assignments
        # Only clear pair assignments, not the slots themselves
        existing_assignments = db.query(ScheduleAssignment).all()
        print(f"DEBUG: Found {len(existing_assignments)} existing assignments")
        
        # Clear pair assignments from existing slots (preserve patient data)
        for assignment in existing_assignments:
            assignment.pair_id = None
            assignment.status = 'empty'
        
        db.commit()
        print(f"DEBUG: Cleared pair assignments from existing slots")
        
        # Define time slots and days
        time_slots = ["8:00–9:20", "9:20–10:40", "10:40–12:00", "13:00–14:20", "14:20–15:40", "15:40–17:00"]
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        am_slots = ["8:00–9:20", "9:20–10:40", "10:40–12:00"]
        pm_slots = ["13:00–14:20", "14:20–15:40", "15:40–17:00"]
        
        assignments_created = 0
        
        # Get all existing weeks from the uploaded file
        existing_weeks = db.query(ScheduleWeekSchedule).all()
        print(f"DEBUG: Found {len(existing_weeks)} existing weeks")
        print(f"DEBUG: Found {len(pairs)} pairs available for assignment")
        
        # Fairness: track per-pair assignment counts during generation
        pair_assignment_counts = {p.id: 0 for p in pairs}
        
        # Assign pairs to ALL existing slots from uploaded file
        for week_obj in existing_weeks:
            week_name = week_obj.week_label
            print(f"DEBUG: Processing week {week_name}")
            
            # Filter pairs that are available for this week (not on externship)
            available_pairs = []
            for pair in pairs:
                if _is_pair_available_for_week(pair, week_obj):
                    available_pairs.append(pair)
                else:
                    print(f"DEBUG: Pair {pair.pair_id} not available for week {week_name} (on externship)")
            
            print(f"DEBUG: {len(available_pairs)} pairs available for week {week_name} out of {len(pairs)} total")
            
            # Get all assignments for this week
            week_assignments = db.query(ScheduleAssignment).filter(
                ScheduleAssignment.week_id == week_obj.id
            ).all()
            
            print(f"DEBUG: Found {len(week_assignments)} total assignments for week {week_name}")
            
            # Group assignments by day
            assignments_by_day = {}
            for assignment in week_assignments:
                if assignment.day not in assignments_by_day:
                    assignments_by_day[assignment.day] = []
                assignments_by_day[assignment.day].append(assignment)
            
            print(f"DEBUG: Assignments by day: {[(day, len(assignments)) for day, assignments in assignments_by_day.items()]}")
            
            # Assign pairs to chairs following the rules:
            # 1. One pair per chair for entire AM period (all 3 AM slots in same chair)
            # 2. One pair per chair for entire PM period (all 3 PM slots in same chair)
            # 3. Pairs stay in same chair for their entire AM or PM period
            # 4. Each pair can only be assigned to ONE chair per day
            
            pair_index = 0
            total_slots_processed = 0
            
            for day in weekdays:
                if day not in assignments_by_day:
                    continue
                    
                day_assignments = assignments_by_day[day]
                print(f"DEBUG: Processing {day} with {len(day_assignments)} assignments")
                
                # Group assignments by chair
                assignments_by_chair = {}
                for assignment in day_assignments:
                    if assignment.chair not in assignments_by_chair:
                        assignments_by_chair[assignment.chair] = []
                    assignments_by_chair[assignment.chair].append(assignment)
                
                print(f"DEBUG: Found {len(assignments_by_chair)} chairs for {day}")
                
                # Track which pairs are already assigned on this day and period (prevent multi-chair same period)
                used_pairs_am = set()
                used_pairs_pm = set()
                
                # Assign pairs to each chair (AM and PM separately)
                # Skip backup chairs 11 and 27 (for X-ray backup)
                slots_assigned_this_day = 0
                for chair_name in sorted(assignments_by_chair.keys()):
                    # Skip backup chairs (Chair 11 and Chair 27 for X-ray backup)
                    chair_number = _get_chair_number(chair_name)
                    if chair_number in [11, 27]:
                        print(f"DEBUG: Skipping backup chair {chair_name} (X-ray backup)")
                        continue
                        
                    chair_assignments = assignments_by_chair[chair_name]
                    
                    # Separate AM and PM slots for this chair (robust to dash variants)
                    am_slots_in_chair = [a for a in chair_assignments if _is_am_time_slot(a.time_slot)]
                    pm_slots_in_chair = [a for a in chair_assignments if _is_pm_time_slot(a.time_slot)]
                    
                    # Assign pair to AM slots (if chair has AM slots)
                    if am_slots_in_chair:
                        # Find next available AM pair that meets grade restrictions, prefer lowest assignment count
                        am_pair = None
                        print(f"DEBUG: Looking for AM pair for {chair_name} on {day}")
                        candidates = []
                        for i in range(len(available_pairs)):
                            candidate_pair = available_pairs[(pair_index + i) % len(available_pairs)]
                            print(f"DEBUG: Checking candidate pair {candidate_pair.pair_id} (already used: {candidate_pair.id in used_pairs_am})")
                            if (candidate_pair.id not in used_pairs_am and 
                                _is_pair_allowed_for_chair(candidate_pair, chair_name) and
                                _is_pair_allowed_for_time_slot(candidate_pair, day, "AM", week_obj)):
                                candidates.append(candidate_pair)
                        if candidates:
                            min_count = min(pair_assignment_counts[p.id] for p in candidates)
                            fair_candidates = [p for p in candidates if pair_assignment_counts[p.id] == min_count]
                            am_pair = random.choice(fair_candidates)
                        
                        if am_pair:
                            used_pairs_am.add(am_pair.id)
                            
                            for assignment in am_slots_in_chair:
                                if assignment.pair_id is None:
                                    assignment.pair_id = am_pair.id
                                    assignment.status = 'assigned'
                                    assignments_created += 1
                                    slots_assigned_this_day += 1
                                # Increment fairness counter once per period assignment
                                pair_assignment_counts[am_pair.id] += 1
                            # Mark pair as used for AM period on this day
                            used_pairs_am.add(am_pair.id)
                            
                            print(f"DEBUG: Assigned AM pair {am_pair.pair_id} to {chair_name} for {len(am_slots_in_chair)} AM slots")
                        else:
                            print(f"DEBUG: No suitable AM pair found for {chair_name} on {day} (grade restrictions)")
                            # Fallback tier 1: allow reusing a pair within AM (still enforce grade/time + chair group)
                            candidates = []
                            for p in available_pairs:
                                if (p.id not in used_pairs_am and
                                    _is_pair_allowed_for_chair(p, chair_name) and
                                    _is_pair_allowed_for_time_slot(p, day, "AM", week_obj)):
                                    candidates.append(p)
                            if candidates:
                                candidates.sort(key=lambda p: pair_assignment_counts[p.id])
                                am_pair = candidates[0]
                                used_pairs_am.add(am_pair.id)
                                for assignment in am_slots_in_chair:
                                    if assignment.pair_id is None:
                                        assignment.pair_id = am_pair.id
                                        assignment.status = 'assigned'
                                        assignments_created += 1
                                        slots_assigned_this_day += 1
                                pair_assignment_counts[am_pair.id] += 1
                                used_pairs_am.add(am_pair.id)
                                print(f"DEBUG: EXT-FALLBACK(AM reuse): Assigned {am_pair.pair_id} to {chair_name}")
                            else:
                                # No cross-group fallback allowed per policy
                                print(f"DEBUG: Unable to fill AM for {chair_name} on {day} without violating group or grade rules")
                    
                    # Assign different pair to PM slots (if chair has PM slots)
                    if pm_slots_in_chair:
                        # Find next available PM pair that meets grade restrictions, prefer lowest assignment count
                        pm_pair = None
                        print(f"DEBUG: Looking for PM pair for {chair_name} on {day}")
                        candidates = []
                        for i in range(len(available_pairs)):
                            candidate_pair = available_pairs[(pair_index + i) % len(available_pairs)]
                            print(f"DEBUG: Checking candidate pair {candidate_pair.pair_id} (already used: {candidate_pair.id in used_pairs_pm})")
                            if (candidate_pair.id not in used_pairs_pm and 
                                _is_pair_allowed_for_chair(candidate_pair, chair_name) and
                                _is_pair_allowed_for_time_slot(candidate_pair, day, "PM", week_obj)):
                                candidates.append(candidate_pair)
                        if candidates:
                            min_count = min(pair_assignment_counts[p.id] for p in candidates)
                            fair_candidates = [p for p in candidates if pair_assignment_counts[p.id] == min_count]
                            pm_pair = random.choice(fair_candidates)
                        
                        if pm_pair:
                            used_pairs_pm.add(pm_pair.id)
                            
                            for assignment in pm_slots_in_chair:
                                if assignment.pair_id is None:
                                    assignment.pair_id = pm_pair.id
                                    assignment.status = 'assigned'
                                    assignments_created += 1
                                    slots_assigned_this_day += 1
                                pair_assignment_counts[pm_pair.id] += 1
                            # Mark pair as used for PM period on this day
                            used_pairs_pm.add(pm_pair.id)
                            
                            print(f"DEBUG: Assigned PM pair {pm_pair.pair_id} to {chair_name} for {len(pm_slots_in_chair)} PM slots")
                        else:
                            print(f"DEBUG: No suitable PM pair found for {chair_name} on {day} (grade restrictions)")
                            # Fallback tier 1: allow reusing a pair within PM (still enforce grade/time + chair group)
                            candidates = []
                            for p in available_pairs:
                                if (p.id not in used_pairs_pm and
                                    _is_pair_allowed_for_chair(p, chair_name) and
                                    _is_pair_allowed_for_time_slot(p, day, "PM", week_obj)):
                                    candidates.append(p)
                            if candidates:
                                candidates.sort(key=lambda p: pair_assignment_counts[p.id])
                                pm_pair = candidates[0]
                                used_pairs_pm.add(pm_pair.id)
                                for assignment in pm_slots_in_chair:
                                    if assignment.pair_id is None:
                                        assignment.pair_id = pm_pair.id
                                        assignment.status = 'assigned'
                                        assignments_created += 1
                                        slots_assigned_this_day += 1
                                pair_assignment_counts[pm_pair.id] += 1
                                used_pairs_pm.add(pm_pair.id)
                                print(f"DEBUG: EXT-FALLBACK(PM reuse): Assigned {pm_pair.pair_id} to {chair_name}")
                            else:
                                # No cross-group fallback allowed per policy
                                print(f"DEBUG: Unable to fill PM for {chair_name} on {day} without violating group or grade rules")
                
                print(f"DEBUG: Assigned pairs to {slots_assigned_this_day} slots on {day}")
            
            print(f"DEBUG: Processed {total_slots_processed} total slots for week {week_name}")
        
        db.commit()
        
        print(f"DEBUG: Total assignments created: {assignments_created}")
        
        print("=" * 50)
        print(f"SCHEDULE GENERATION COMPLETED!")
        print(f"Total assignments created: {assignments_created}")
        print("=" * 50)
        
        return {
            "message": "Clinic schedule generated successfully",
            "count": assignments_created,
            "weeks": weeks,
            "statistics": {
                "total_assignments": assignments_created,
                "pairs_used": len(set(assignment.pair_id for assignment in db.query(ScheduleAssignment).all() if assignment.pair_id)),
                "operations_distributed": len(set(assignment.operation_id for assignment in db.query(ScheduleAssignment).all() if assignment.operation_id))
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating schedule: {str(e)}")

@router.post("/schedule/assign")
async def assign_pairs_to_patient_slots(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Assign student pairs to existing patient schedule slots"""
    try:
        # Get all pairs
        pairs = db.query(StudentPair).all()
        if not pairs:
            raise HTTPException(status_code=400, detail="No pairs available. Please create pairs first.")
        
        # Get all empty assignments (patient slots without pairs)
        empty_assignments = db.query(ScheduleAssignment).filter(ScheduleAssignment.status == 'empty').all()
        if not empty_assignments:
            raise HTTPException(status_code=400, detail="No empty patient slots found. Please upload patient schedule first.")
        
        # Initialize tracking
        pair_assignment_counts = {}
        operation_tracking = {}
        
        for pair in pairs:
            pair_assignment_counts[pair.pair_id] = 0
            # Get existing operation counts for this pair
            existing_assignments = db.query(ScheduleAssignment).filter(ScheduleAssignment.pair_id == pair.id).all()
            operation_tracking[pair.pair_id] = {}
            for assignment in existing_assignments:
                if assignment.operation:
                    op_name = assignment.operation.name
                    operation_tracking[pair.pair_id][op_name] = operation_tracking[pair.pair_id].get(op_name, 0) + 1
        
        assignments_updated = 0
        
        # Assign pairs to empty slots
        for assignment in empty_assignments:
            # Find the best pair for this slot
            best_pair = _find_best_pair_for_slot(assignment, pairs, pair_assignment_counts, operation_tracking, db)
            
            if best_pair:
                # Update assignment
                assignment.pair_id = best_pair.id
                assignment.status = 'assigned'
                assignments_updated += 1
                
                # Update tracking
                pair_assignment_counts[best_pair.pair_id] += 1
                if assignment.operation:
                    op_name = assignment.operation.name
                    operation_tracking[best_pair.pair_id][op_name] = operation_tracking[best_pair.pair_id].get(op_name, 0) + 1
        
        db.commit()
        
        return {
            "message": "Pairs assigned to patient slots successfully",
            "count": assignments_updated
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error assigning pairs: {str(e)}")

def _get_fair_operation(pair_id, operation_tracking, operations):
    """Pick an operation for this pair with maximum fairness."""
    pair_tracking = operation_tracking.get(pair_id, {})
    
    # Calculate minimum threshold for each operation
    min_thresholds = {}
    for operation in operations:
        counts = [tracking.get(operation.name, 0) for tracking in operation_tracking.values()]
        if counts:
            min_thresholds[operation.name] = min(counts)
    
    # First priority: Operations with 0 assignments
    zero_operations = [op for op in operations if pair_tracking.get(op.name, 0) == 0]
    if zero_operations:
        return random.choice(zero_operations)
    
    # Second priority: Operations where this pair is below minimum threshold
    below_threshold_operations = []
    for operation in operations:
        count = pair_tracking.get(operation.name, 0)
        threshold = min_thresholds.get(operation.name, 0)
        if count < threshold:
            below_threshold_operations.append(operation)
    
    if below_threshold_operations:
        return random.choice(below_threshold_operations)
    
    # Third priority: Operations with minimum assignments
    min_count = min(pair_tracking.get(op.name, 0) for op in operations)
    min_operations = [op for op in operations if pair_tracking.get(op.name, 0) == min_count]
    return random.choice(min_operations)

def _find_best_pair_for_slot(assignment, pairs, pair_assignment_counts, operation_tracking, db):
    """Find the best pair for a specific slot based on fairness and restrictions."""
    candidates = []
    
    for pair in pairs:
        # Check grade level restrictions
        if not _is_pair_allowed_for_slot(pair, assignment.day, assignment.time_slot, db):
            continue
        
        # Check if pair is already assigned to this time slot
        existing_assignment = db.query(ScheduleAssignment).filter(
            ScheduleAssignment.day == assignment.day,
            ScheduleAssignment.time_slot == assignment.time_slot,
            ScheduleAssignment.pair_id == pair.id
        ).first()
        
        if existing_assignment:
            continue
        
        candidates.append(pair)
    
    if not candidates:
        return None
    
    # Sort by assignment count (fairness)
    candidates.sort(key=lambda x: pair_assignment_counts.get(x.pair_id, 0))
    
    # If there's a desired operation, prioritize pairs with fewer of that operation
    if assignment.operation:
        min_operation_count = min(
            operation_tracking.get(p.pair_id, {}).get(assignment.operation.name, 0)
            for p in candidates
        )
        operation_candidates = [
            p for p in candidates
            if operation_tracking.get(p.pair_id, {}).get(assignment.operation.name, 0) == min_operation_count
        ]
        if operation_candidates:
            candidates = operation_candidates
    
    # Return the pair with minimum total assignments
    min_count = min(pair_assignment_counts.get(p.pair_id, 0) for p in candidates)
    best_candidates = [p for p in candidates if pair_assignment_counts.get(p.pair_id, 0) == min_count]
    
    return random.choice(best_candidates) if best_candidates else None
