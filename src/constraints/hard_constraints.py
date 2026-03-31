"""
Hard constraints handler for the shift scheduling solver.

This module implements non-negotiable constraints that must be satisfied
in any valid solution. All comments are in English to prevent RTL rendering issues.
"""

from typing import Dict, List, Tuple, Set
from ortools.sat.python import cp_model
from ..models.data_models import Worker, Shift, SchedulingRequest


class HardConstraintHandler:
    """
    Manages hard constraints (must-be-satisfied constraints) for the scheduling model.
    
    Hard constraints define rules that cannot be violated. Examples include:
    - A worker cannot work two consecutive shifts
    - Maximum shifts per week must be respected
    - Required skills must be present in every shift
    """

    def __init__(self, model: cp_model.CpModel):
        """
        Initialize the constraint handler.
        
        Args:
            model: The OR-Tools CP-SAT model to add constraints to
        """
        self.model = model
        self.constraint_count = 0

    def apply_all_hard_constraints(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
        shift_coverage: Dict[int, "cp_model.IntVar"],
    ) -> None:
        """
        Apply all hard constraints to the scheduling model.
        
        Args:
            request: The scheduling request containing workers and shifts
            assignments: Dictionary of assignment variables (worker_id, shift_id) -> IntVar
            shift_coverage: Dictionary of shift coverage variables (shift_id -> IntVar)
        """
        self._add_shift_coverage_constraints(request, assignments, shift_coverage)
        self._add_no_consecutive_shifts_constraint(request, assignments)
        self._add_max_shifts_per_week_constraint(request, assignments)
        self._add_worker_availability_constraints(request, assignments)
        self._add_skill_requirement_constraints(request, assignments)

    def _add_shift_coverage_constraints(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
        shift_coverage: Dict[int, "cp_model.IntVar"],
    ) -> None:
        """
        Ensure each shift is covered by exactly the required number of workers.
        
        Args:
            request: The scheduling request
            assignments: Assignment variables
            shift_coverage: Shift coverage variables
        """
        for shift in request.shifts:
            workers_assigned = []
            for worker in request.workers:
                key = (worker.id, shift.id)
                if key in assignments:
                    workers_assigned.append(assignments[key])
            
            if workers_assigned:
                self.model.Add(sum(workers_assigned) == shift_coverage[shift.id])
                self.model.Add(shift_coverage[shift.id] == shift.workers_required)
                self.constraint_count += 1

    def _add_no_consecutive_shifts_constraint(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        """
        Prevent workers from being assigned to consecutive shifts.
        
        This constraint respects the worker's preference setting. If a worker
        has no_consecutive_shifts=True, they cannot work back-to-back shifts.
        
        Args:
            request: The scheduling request
            assignments: Assignment variables
        """
        worker_shifts: Dict[int, List[Shift]] = {w.id: [] for w in request.workers}
        for shift in request.shifts:
            for worker in request.workers:
                worker_shifts[worker.id].append(shift)
        
        for worker in request.workers:
            if not worker.preferences.no_consecutive_shifts:
                continue
            
            shifts = sorted(worker_shifts[worker.id], key=lambda s: (s.date, s.start_time))
            
            for i in range(len(shifts) - 1):
                current_shift = shifts[i]
                next_shift = shifts[i + 1]
                
                if self._are_consecutive(current_shift, next_shift):
                    key1 = (worker.id, current_shift.id)
                    key2 = (worker.id, next_shift.id)
                    
                    if key1 in assignments and key2 in assignments:
                        self.model.Add(
                            assignments[key1] + assignments[key2] <= 1
                        )
                        self.constraint_count += 1

    def _add_max_shifts_per_week_constraint(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        """
        Enforce maximum shifts per week for each worker.
        
        Args:
            request: The scheduling request
            assignments: Assignment variables
        """
        worker_week_shifts: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        
        for worker in request.workers:
            for shift in request.shifts:
                week_number = self._get_iso_week_number(shift.date)
                key = (worker.id, week_number)
                if key not in worker_week_shifts:
                    worker_week_shifts[key] = []
                worker_week_shifts[key].append((worker.id, shift.id))
        
        for (worker_id, week_num), shifts_in_week in worker_week_shifts.items():
            assignment_vars = [
                assignments.get((w_id, s_id))
                for w_id, s_id in shifts_in_week
                if (w_id, s_id) in assignments
            ]
            
            if assignment_vars:
                worker = next(w for w in request.workers if w.id == worker_id)
                self.model.Add(sum(assignment_vars) <= worker.preferences.max_shifts_per_week)
                self.constraint_count += 1

    def _add_worker_availability_constraints(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        """
        Prevent assignment of workers to shifts on their unavailable dates.
        
        Args:
            request: The scheduling request
            assignments: Assignment variables
        """
        for worker in request.workers:
            if not worker.preferences.unavailable_dates:
                continue
            
            unavailable = set(worker.preferences.unavailable_dates)
            
            for shift in request.shifts:
                if shift.date in unavailable:
                    key = (worker.id, shift.id)
                    if key in assignments:
                        self.model.Add(assignments[key] == 0)
                        self.constraint_count += 1

    def _add_skill_requirement_constraints(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        """
        Ensure that for each shift, at least one assigned worker has all required skills.
        
        Args:
            request: The scheduling request
            assignments: Assignment variables
        """
        for shift in request.shifts:
            if not shift.required_skills:
                continue
            
            for skill in shift.required_skills:
                capable_workers = [
                    w for w in request.workers
                    if w.has_skill(skill.name, skill.level)
                ]
                
                if capable_workers:
                    capable_assignments = [
                        assignments.get((w.id, shift.id))
                        for w in capable_workers
                        if (w.id, shift.id) in assignments
                    ]
                    
                    if capable_assignments:
                        self.model.Add(sum(capable_assignments) >= 1)
                        self.constraint_count += 1

    @staticmethod
    def _are_consecutive(shift1: Shift, shift2: Shift) -> bool:
        """
        Check if two shifts are consecutive (same day and back-to-back times).
        
        Args:
            shift1: First shift
            shift2: Second shift
            
        Returns:
            True if shifts are consecutive
        """
        if shift1.date != shift2.date:
            return False
        
        return shift1.end_time == shift2.start_time

    @staticmethod
    def _get_iso_week_number(date_str: str) -> int:
        """
        Get the ISO week number for a date string.
        
        Args:
            date_str: Date in ISO format (YYYY-MM-DD)
            
        Returns:
            ISO week number (1-53)
        """
        from datetime import datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.isocalendar()[1]

    def get_constraint_count(self) -> int:
        """
        Get the total number of constraints added.
        
        Returns:
            Number of constraints
        """
        return self.constraint_count
