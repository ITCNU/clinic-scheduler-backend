from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Student schemas
class StudentScheduleBase(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    grade_level: int
    externship: bool = False
    pair_id: Optional[str] = None
    group_number: Optional[int] = None


class StudentScheduleCreate(StudentScheduleBase):
    pass


class StudentScheduleResponse(StudentScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Student pair schemas
class StudentPairBase(BaseModel):
    pair_id: str
    student1_id: int
    student2_id: int
    group_number: int


class StudentPairCreate(StudentPairBase):
    pass


class StudentPairResponse(StudentPairBase):
    id: int
    created_at: datetime
    student1: Optional[StudentScheduleResponse] = None
    student2: Optional[StudentScheduleResponse] = None

    class Config:
        from_attributes = True


# Operation schemas
class OperationScheduleBase(BaseModel):
    name: Optional[str] = None  # Allow null treatment names
    description: Optional[str] = None
    cdt_code: Optional[str] = None  # CDT code like D2740, D4567, etc.


class OperationScheduleCreate(OperationScheduleBase):
    pass


class OperationScheduleResponse(OperationScheduleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schedule week schemas
class ScheduleWeekBase(BaseModel):
    week_label: str
    week_number: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ScheduleWeekCreate(ScheduleWeekBase):
    pass


class ScheduleWeekResponse(ScheduleWeekBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schedule assignment schemas
class ScheduleAssignmentBase(BaseModel):
    week_id: int
    day: str
    time_slot: str
    chair: str
    operation_id: Optional[int] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    pair_id: Optional[int] = None
    status: str = 'empty'


class ScheduleAssignmentCreate(ScheduleAssignmentBase):
    pass


class ScheduleAssignmentUpdate(BaseModel):
    week_id: Optional[int] = None
    day: Optional[str] = None
    time_slot: Optional[str] = None
    chair: Optional[str] = None
    operation_id: Optional[int] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    pair_id: Optional[int] = None
    status: Optional[str] = None


class ScheduleAssignmentResponse(ScheduleAssignmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    week: Optional[ScheduleWeekResponse] = None
    operation: Optional[OperationScheduleResponse] = None
    pair: Optional[StudentPairResponse] = None

    class Config:
        from_attributes = True


# Operation tracking schemas
class OperationTrackingBase(BaseModel):
    pair_id: int
    operation_id: int
    count: int = 0


class OperationTrackingCreate(OperationTrackingBase):
    pass


class OperationTrackingResponse(OperationTrackingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    pair: Optional[StudentPairResponse] = None
    operation: Optional[OperationScheduleResponse] = None

    class Config:
        from_attributes = True


# App settings schemas
class AppSettingsBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class AppSettingsCreate(AppSettingsBase):
    pass


class AppSettingsResponse(AppSettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Bulk import schemas
class BulkStudentImport(BaseModel):
    students: List[StudentScheduleCreate]


class BulkScheduleImport(BaseModel):
    assignments: List[ScheduleAssignmentCreate]


# Schedule summary schemas
class ScheduleSummary(BaseModel):
    total_students: int
    total_pairs: int
    total_operations: int
    total_weeks: int
    total_assignments: int
    unassigned_slots: int


# Pair assignment summary
class PairAssignmentSummary(BaseModel):
    pair_id: str
    student1_name: str
    student2_name: str
    group_number: int
    total_assignments: int
    operations_count: dict
    assigned_slots: List[str]  # List of slot identifiers like "Week1-Monday-8:00–9:20-Chair1"


# Operation distribution summary
class OperationDistributionSummary(BaseModel):
    operation_name: str
    total_assignments: int
    assigned_pairs: int
    average_per_pair: float
    min_assignments: int
    max_assignments: int
