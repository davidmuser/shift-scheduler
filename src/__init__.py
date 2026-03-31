"""Shift Scheduler - Expert shift scheduling backend using Google OR-Tools CP-SAT."""

__version__ = "1.0.0"
__author__ = "Backend Team"

from .models.data_models import (
    Worker,
    Shift,
    SchedulingRequest,
    ObjectiveWeights,
    SchedulingResponse,
)
from .solver.core_solver import ShiftSchedulingSolver

__all__ = [
    "Worker",
    "Shift",
    "SchedulingRequest",
    "ObjectiveWeights",
    "SchedulingResponse",
    "ShiftSchedulingSolver",
]
