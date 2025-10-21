from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class StudentSchedule(Base):
    """Student model matching the original app structure"""
    __tablename__ = "student_schedule_students"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    grade_level = Column(Integer, nullable=False)
    externship = Column(Boolean, default=False)
    externship_start_date = Column(Date)
    externship_end_date = Column(Date)
    pair_id = Column(String(20))  # e.g., "G1P1", "G2P3"
    group_number = Column(Integer)  # 1 or 2
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pair_student1 = relationship("StudentPair", foreign_keys="StudentPair.student1_id", back_populates="student1")
    pair_student2 = relationship("StudentPair", foreign_keys="StudentPair.student2_id", back_populates="student2")


class StudentPair(Base):
    """Pair model matching the original app structure"""
    __tablename__ = "student_pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(String(20), unique=True, nullable=False)  # e.g., "G1P1", "G2P3"
    student1_id = Column(Integer, ForeignKey('student_schedule_students.id'), nullable=False)
    student2_id = Column(Integer, ForeignKey('student_schedule_students.id'), nullable=False)
    group_number = Column(Integer, nullable=False)  # 1 or 2
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    student1 = relationship("StudentSchedule", foreign_keys=[student1_id], back_populates="pair_student1")
    student2 = relationship("StudentSchedule", foreign_keys=[student2_id], back_populates="pair_student2")
    schedule_assignments = relationship("ScheduleAssignment", back_populates="pair")
    operation_tracking = relationship("OperationTracking", back_populates="pair")


class OperationSchedule(Base):
    """Operation model matching the original app operations list"""
    __tablename__ = "student_schedule_operations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=True)  # Allow null treatment names
    description = Column(Text)
    cdt_code = Column(String(20))  # CDT code like D2740, D4567, etc.
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    schedule_assignments = relationship("ScheduleAssignment", back_populates="operation")
    operation_tracking = relationship("OperationTracking", back_populates="operation")


class ScheduleWeekSchedule(Base):
    """Schedule week model"""
    __tablename__ = "student_schedule_weeks"
    
    id = Column(Integer, primary_key=True, index=True)
    week_label = Column(String(50), nullable=False)  # e.g., "Week 1", "10/27/2025-10/31/2025"
    week_number = Column(Integer)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    schedule_assignments = relationship("ScheduleAssignment", back_populates="week")


class ScheduleAssignment(Base):
    """Schedule assignment model matching the original app structure"""
    __tablename__ = "schedule_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    week_id = Column(Integer, ForeignKey('student_schedule_weeks.id'), nullable=False)
    day = Column(String(20), nullable=False)  # Monday, Tuesday, etc.
    time_slot = Column(String(20), nullable=False)  # e.g., "8:00–9:20"
    chair = Column(String(20), nullable=False)  # e.g., "Chair 1"
    operation_id = Column(Integer, ForeignKey('student_schedule_operations.id'))
    patient_id = Column(String(50))
    patient_name = Column(String(100))
    pair_id = Column(Integer, ForeignKey('student_pairs.id'))  # Assigned pair
    status = Column(String(20), default='empty')  # empty, assigned, completed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    week = relationship("ScheduleWeekSchedule", back_populates="schedule_assignments")
    operation = relationship("OperationSchedule", back_populates="schedule_assignments")
    pair = relationship("StudentPair", back_populates="schedule_assignments")


class OperationTracking(Base):
    """Operation tracking model matching the original app structure"""
    __tablename__ = "operation_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(Integer, ForeignKey('student_pairs.id'), nullable=False)
    operation_id = Column(Integer, ForeignKey('student_schedule_operations.id'), nullable=False)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pair = relationship("StudentPair", back_populates="operation_tracking")
    operation = relationship("OperationSchedule", back_populates="operation_tracking")


class AppSettings(Base):
    """App settings model for storing configuration"""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
