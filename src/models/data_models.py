"""
Data models for shift scheduling system.

This module defines the core Pydantic models for Workers, Shifts, and scheduling
constraints. All comments are in English to prevent RTL rendering issues.
"""

from enum import Enum
from typing import Optional, Set, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
class UserRole(str, Enum):
    """Roles supported in the SaaS platform."""
    MANAGER = "Manager"
    WORKER = "Worker"


class ShiftStatus(str, Enum):
    """Shift publication status."""
    OPEN = "Open"
    CLOSED = "Closed"


class Business(BaseModel):
    """Tenant (business) entity."""
    id: int = Field(..., description="Primary key for the business")
    name: str = Field(..., description="Display name of the business")
    unique_number: str = Field(..., description="Public join/registration number")


class User(BaseModel):
    """Application user linked to a business."""
    id: int = Field(..., description="Primary key for the user")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="Manager or Worker")
    business_id: int = Field(..., description="Foreign key to Business")


class SkillLevel(str, Enum):
    """Enumeration for worker skill levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Skill(BaseModel):
    """Represents a skill required for shifts or possessed by workers."""
    name: str = Field(..., description="Name of the skill (e.g., 'ICU', 'Pediatrics')")
    level: SkillLevel = Field(default=SkillLevel.BASIC, description="Proficiency level")

    class Config:
        use_enum_values = False


class WorkerPreference(BaseModel):
    """Represents worker preferences and constraints."""
    worker_id: int = Field(..., description="Unique identifier for the worker")
    preferred_shift_types: Optional[List[str]] = Field(
        default=None, description="Preferred shift types (e.g., 'morning', 'evening')"
    )
    unavailable_dates: Optional[Set[str]] = Field(
        default=None, description="Dates when worker is unavailable (ISO format)"
    )
    max_shifts_per_week: int = Field(default=5, description="Maximum shifts per calendar week")
    min_shifts_per_week: int = Field(default=0, description="Minimum shifts per calendar week")
    no_consecutive_shifts: bool = Field(
        default=True, description="If True, worker cannot work consecutive shifts"
    )
    prefer_weekends: bool = Field(default=False, description="Worker prefers weekend shifts")
    avoid_weekends: bool = Field(default=False, description="Worker avoids weekend shifts")

    @field_validator("max_shifts_per_week")
    @classmethod
    def validate_max_shifts(cls, v: int) -> int:
        """Ensure max_shifts_per_week is positive."""
        if v < 0:
            raise ValueError("max_shifts_per_week must be non-negative")
        return v

    @field_validator("min_shifts_per_week")
    @classmethod
    def validate_min_shifts(cls, v: int) -> int:
        """Ensure min_shifts_per_week is non-negative."""
        if v < 0:
            raise ValueError("min_shifts_per_week must be non-negative")
        return v


class Worker(BaseModel):
    """Represents a worker (nurse, staff member, etc.) in the scheduling system."""
    id: int = Field(..., description="Unique identifier for the worker")
    business_id: int = Field(..., description="Business (tenant) id")
    name: str = Field(..., description="Full name of the worker")
    seniority_level: int = Field(
        default=0, description="Seniority level (0=junior, higher=more senior)"
    )
    skills: List[Skill] = Field(default_factory=list, description="List of skills")
    hourly_rate: float = Field(default=15.0, description="Hourly compensation rate")
    preferences: WorkerPreference = Field(..., description="Worker preferences and constraints")
    user_role: Optional[UserRole] = Field(default=UserRole.WORKER, description="Role: Manager or Worker")

    class Config:
        validate_assignment = True

    def has_skill(self, skill_name: str, min_level: SkillLevel = SkillLevel.BASIC) -> bool:
        """
        Check if worker has a specific skill at or above a minimum level.
        
        Args:
            skill_name: Name of the skill to check
            min_level: Minimum required skill level
            
        Returns:
            True if worker has the skill at the required level or higher
        """
        skill_levels = {
            SkillLevel.BASIC: 1,
            SkillLevel.INTERMEDIATE: 2,
            SkillLevel.ADVANCED: 3,
            SkillLevel.EXPERT: 4,
        }
        
        for skill in self.skills:
            if skill.name.lower() == skill_name.lower():
                return skill_levels[skill.level] >= skill_levels[min_level]
        return False


class Shift(BaseModel):
    """Represents a shift that needs to be staffed."""
    id: int = Field(..., description="Unique identifier for the shift")
    business_id: int = Field(..., description="Business (tenant) id")
    date: str = Field(..., description="Date of the shift (ISO format, YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM format)")
    end_time: str = Field(..., description="End time (HH:MM format)")
    shift_type: str = Field(default="standard", description="Type of shift (e.g., 'morning', 'evening', 'night')")
    required_skills: List[Skill] = Field(default_factory=list, description="Skills required for this shift")
    workers_required: int = Field(default=1, description="Number of workers needed for this shift")
    is_weekend: bool = Field(default=False, description="Whether this shift falls on a weekend")
    status: ShiftStatus = Field(default=ShiftStatus.OPEN, description="Shift status: Open or Closed")

    def get_shift_duration_hours(self) -> float:
        """Compute the shift duration in hours based on start and end times.

        Handles simple overnight shifts by rolling end time to the next day
        when it is less than or equal to the start time.
        """
        try:
            # Normalize times to HH:MM and parse
            start_str = self.start_time[:5]
            end_str = self.end_time[:5]
            start_dt = datetime.strptime(start_str, "%H:%M")
            end_dt = datetime.strptime(end_str, "%H:%M")
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            delta = end_dt - start_dt
            return delta.total_seconds() / 3600.0
        except Exception:
            # Fallback to 0 if times are malformed; safer than crashing solver
            return 0.0


class ShiftInterest(BaseModel):
    """Represents a worker expressing interest in a shift."""
    worker_id: int = Field(..., description="Worker who expressed interest")
    shift_id: int = Field(..., description="Target shift")
    business_id: int = Field(..., description="Business (tenant) id")


class ScheduleStatus(str, Enum):
    """Overall status of a schedule."""
    DRAFT = "Draft"
    PUBLISHED = "Published"
    LOCKED = "Locked"


class ScheduleAssignment(BaseModel):
    """Represents a single worker-shift assignment in a schedule solution."""
    worker_id: Optional[int] = Field(default=None, description="ID of the assigned worker")
    worker_name: Optional[str] = Field(default=None, description="Name of the assigned worker")
    shift_id: int = Field(..., description="ID of the shift")
    shift_date: str = Field(..., description="Date of the shift (YYYY-MM-DD)")
    shift_start: str = Field(..., description="Start time of the shift (HH:MM)")
    shift_end: str = Field(..., description="End time of the shift (HH:MM)")
    is_assigned: bool = Field(default=True, description="Whether the assignment is active")


class Schedule(BaseModel):
    """Represents a saved or published schedule."""
    id: Optional[int] = Field(default=None, description="Primary key for the schedule")
    business_id: int = Field(..., description="Business (tenant) id")
    name: str = Field(..., description="Human-readable name for the schedule (e.g., 'Week 15 Schedule')")
    start_date: str = Field(..., description="Start date of the scheduling period (ISO format)")
    end_date: str = Field(..., description="End date of the scheduling period (ISO format)")
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT, description="Publication status of the schedule")
    assignments: List[ScheduleAssignment] = Field(..., description="The full assignment dictionary from the solver")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of creation")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of last update")


class SchedulingRequest(BaseModel):
    """Main request object for the scheduling API."""
    business_id: int = Field(..., description="Business (tenant) id for this request")
    workers: List[Worker] = Field(..., description="List of available workers")
    shifts: List[Shift] = Field(..., description="List of shifts to be scheduled")
    scheduling_period_start: str = Field(..., description="Start date (ISO format)")
    scheduling_period_end: str = Field(..., description="End date (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @field_validator("shifts")
    @classmethod
    def validate_shifts_belong_to_business(cls, v: List[Shift], values) -> List[Shift]:
        """Ensure all shifts belong to the same business as the request."""
        if "business_id" not in values.data:
            return v
        business_id = values.data["business_id"]
        for shift in v:
            if shift.business_id != business_id:
                raise ValueError(f"Shift {shift.id} does not belong to business {business_id}")
        return v

    @field_validator("workers")
    @classmethod
    def validate_workers_belong_to_business(cls, v: List[Worker], values) -> List[Worker]:
        """Ensure all workers belong to the same business as the request."""
        if "business_id" not in values.data:
            return v
        business_id = values.data["business_id"]
        for worker in v:
            if worker.business_id != business_id:
                raise ValueError(f"Worker {worker.id} does not belong to business {business_id}")
        return v
        
    @field_validator("workers")
    @classmethod
    def validate_unique_worker_ids(cls, v: List[Worker]) -> List[Worker]:
        """Ensure all worker IDs are unique."""
        ids = [w.id for w in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate worker IDs detected")
        return v

    @field_validator("shifts")
    @classmethod
    def validate_unique_shift_ids(cls, v: List[Shift]) -> List[Shift]:
        """Ensure all shift IDs are unique."""
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate shift IDs detected")
        return v

class SchedulingSolution(BaseModel):
    """Represents one complete scheduling solution from the solver."""
    rank: int = Field(..., description="Rank of this solution (1 is best)")
    objective_value: float = Field(..., description="Solver's objective function value")
    assignments: List[ScheduleAssignment] = Field(..., description="List of assignments")


class SchedulingResponse(BaseModel):
    """Response object containing multiple scheduling solutions."""
    solutions: List[SchedulingSolution] = Field(..., description="List of top-k solutions")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    workers: List[Worker] = Field(..., description="List of workers for UI rendering")
    interested_by_shift: Dict[str, List[int]] = Field(..., description="Map of shift_id to interested worker_ids")


class ObjectiveWeights(BaseModel):
    """
    Dynamic weights for soft constraints in the objective function.
    These are driven by UI inputs and define the importance of different criteria.
    """
    respect_time_off_requests: float = Field(
        default=10.0, description="Weight for respecting worker time-off requests"
    )
    reward_seniority: float = Field(
        default=5.0, description="Weight for rewarding senior workers with better shifts"
    )
    balance_weekend_shifts: float = Field(
        default=8.0, description="Weight for distributing weekend shifts fairly"
    )
    minimize_overstaffing: float = Field(
        default=3.0, description="Weight for avoiding excessive staffing"
    )
    reward_skill_matching: float = Field(
        default=7.0, description="Weight for assigning workers with required skills"
    )
    balance_workload: float = Field(
        default=6.0, description="Weight for balancing total hours worked per worker"
    )
    minimize_compensation: float = Field(
        default=2.0, description="Weight for minimizing total payroll cost"
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_positive_weights(cls, v: float) -> float:
        """Ensure all weights are non-negative."""
        if v < 0:
            raise ValueError("All weights must be non-negative")
        return v
