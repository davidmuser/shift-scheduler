"""
Dynamic objective function handler for soft constraints.

This module implements weighted soft constraints (preferences, not strict rules)
that are dynamically configured via UI inputs. The solver optimizes the objective
function based on these weights. All comments are in English to prevent RTL rendering issues.
"""

from typing import Dict, Tuple, List
from ortools.sat.python import cp_model
from ..models.data_models import (
    Worker,
    Shift,
    SchedulingRequest,
    ObjectiveWeights,
)


class DynamicObjectiveFunction:
    """
    Manages the dynamic objective function with weighted soft constraints.
    """

    def __init__(self, model: cp_model.CpModel, objective_weights: ObjectiveWeights):
        self.model = model
        self.weights = objective_weights
        # scale float weights to integers for CP-SAT
        self.SCALE = 100
        # store (linear_expr_or_var, int_coeff)
        self.objective_terms: List[Tuple[cp_model.IntVar, int]] = []

    def build_objective_function(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        self._add_time_off_request_term(request, assignments)
        self._add_seniority_reward_term(request, assignments)
        self._add_weekend_preference_terms(request, assignments)
        self._add_skill_matching_term(request, assignments)
        self._add_workload_balance_term(request, assignments)
        self._add_compensation_minimization_term(request, assignments)
        self._add_overstaffing_penalty_term(request, assignments)
        self._set_objective()

    def _add_time_off_request_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.respect_time_off_requests == 0:
            return

        coeff = int(round(self.weights.respect_time_off_requests * self.SCALE))
        for worker in request.workers:
            unavailable = set(worker.preferences.unavailable_dates or [])
            if not unavailable:
                continue
            for shift in request.shifts:
                if shift.date in unavailable:
                    key = (worker.id, shift.id)
                    if key in assignments:
                        self.objective_terms.append((assignments[key], coeff))

    def _add_seniority_reward_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.reward_seniority == 0:
            return

        base = self.weights.reward_seniority
        for worker in request.workers:
            if worker.seniority_level <= 0:
                continue
            for shift in request.shifts:
                key = (worker.id, shift.id)
                if key in assignments:
                    coeff = -int(round(base * worker.seniority_level * self.SCALE))
                    if coeff != 0:
                        self.objective_terms.append((assignments[key], coeff))

    def _add_weekend_preference_terms(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.balance_weekend_shifts == 0:
            return
        coeff = int(round(self.weights.balance_weekend_shifts * self.SCALE))
        for worker in request.workers:
            prefer = getattr(worker.preferences, "prefer_weekends", False)
            avoid = getattr(worker.preferences, "avoid_weekends", False)
            if not (prefer or avoid):
                continue
            for shift in request.shifts:
                if not shift.is_weekend:
                    continue
                key = (worker.id, shift.id)
                if key not in assignments:
                    continue
                if prefer:
                    self.objective_terms.append((assignments[key], -coeff))
                if avoid:
                    self.objective_terms.append((assignments[key], coeff))

    def _add_skill_matching_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.reward_skill_matching == 0:
            return
        base = self.weights.reward_skill_matching
        for shift in request.shifts:
            if not shift.required_skills:
                continue
            for worker in request.workers:
                key = (worker.id, shift.id)
                if key not in assignments:
                    continue
                matching_skills = sum(
                    1 for skill in shift.required_skills if worker.has_skill(skill.name, skill.level)
                )
                if matching_skills > 0:
                    coeff = -int(round(base * matching_skills * self.SCALE))
                    if coeff != 0:
                        self.objective_terms.append((assignments[key], coeff))

    def _add_workload_balance_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        """Penalize uneven total workload (in hours) across workers.

        We approximate workload as the sum of shift durations (in minutes)
        assigned to each worker, then minimize the range (max - min) across
        all workers. A higher balance_workload weight will push the solver
        toward schedules where workers have more similar total hours.
        """
        if self.weights.balance_workload == 0:
            return

        if not request.workers or len(request.workers) <= 1:
            # Nothing to balance with a single worker
            return

        # Precompute shift durations in integer minutes
        duration_by_shift: Dict[int, int] = {}
        total_minutes_all_shifts = 0
        for shift in request.shifts:
            minutes = int(round(shift.get_shift_duration_hours() * 60))
            if minutes < 0:
                minutes = 0
            duration_by_shift[shift.id] = minutes
            total_minutes_all_shifts += max(minutes, 0)

        if total_minutes_all_shifts <= 0:
            # If we cannot reliably compute durations, skip this term
            return

        # For each worker, introduce an IntVar for their total workload in minutes
        load_vars: List[cp_model.IntVar] = []
        for worker in request.workers:
            load_var = self.model.NewIntVar(
                0,
                total_minutes_all_shifts,
                f"workload_worker_{worker.id}",
            )

            # Build linear expression: sum(minutes * assignment)
            terms = []
            for shift in request.shifts:
                key = (worker.id, shift.id)
                if key in assignments:
                    minutes = duration_by_shift.get(shift.id, 0)
                    if minutes > 0:
                        terms.append((assignments[key], minutes))

            if terms:
                expr = None
                for var, minutes in terms:
                    term = var * int(minutes)
                    expr = term if expr is None else expr + term
                self.model.Add(load_var == expr)
            else:
                # No assignable shifts for this worker -> zero load
                self.model.Add(load_var == 0)

            load_vars.append(load_var)

        # max_load = max(load_vars), min_load = min(load_vars)
        max_load = self.model.NewIntVar(0, total_minutes_all_shifts, "workload_max")
        min_load = self.model.NewIntVar(0, total_minutes_all_shifts, "workload_min")
        self.model.AddMaxEquality(max_load, load_vars)
        self.model.AddMinEquality(min_load, load_vars)

        # range_var = max_load - min_load
        range_var = self.model.NewIntVar(0, total_minutes_all_shifts, "workload_range")
        self.model.Add(range_var == max_load - min_load)

        coeff = int(round(self.weights.balance_workload * self.SCALE))
        if coeff != 0:
            self.objective_terms.append((range_var, coeff))

    def _add_compensation_minimization_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.minimize_compensation == 0:
            return
        base = self.weights.minimize_compensation
        for worker in request.workers:
            for shift in request.shifts:
                key = (worker.id, shift.id)
                if key not in assignments:
                    continue
                duration = shift.get_shift_duration_hours()
                cost = worker.hourly_rate * duration
                coeff = int(round(cost * base * self.SCALE))
                if coeff != 0:
                    self.objective_terms.append((assignments[key], coeff))

    def _add_overstaffing_penalty_term(
        self,
        request: SchedulingRequest,
        assignments: Dict[Tuple[int, int], "cp_model.IntVar"],
    ) -> None:
        if self.weights.minimize_overstaffing == 0:
            return
        weight = int(round(self.weights.minimize_overstaffing * self.SCALE))
        for shift in request.shifts:
            workers_assigned = [assignments[(w.id, shift.id)] for w in request.workers if (w.id, shift.id) in assignments]
            if not workers_assigned:
                continue
            max_possible = len(workers_assigned)
            over_var = self.model.NewIntVar(0, max_possible, f"overstaff_shift_{shift.id}")
            total_assigned = sum(workers_assigned)
            # constrain: total_assigned - over_var <= required -> over_var >= total_assigned - required
            self.model.Add(total_assigned - over_var <= shift.workers_required)
            self.objective_terms.append((over_var, weight))

    def _set_objective(self) -> None:
        if not self.objective_terms:
            return
        expr = None
        for var, coeff in self.objective_terms:
            term = var * int(coeff)
            expr = term if expr is None else expr + term
        if expr is not None:
            self.model.Minimize(expr)

    def get_weight_summary(self) -> Dict[str, float]:
        return {
            "respect_time_off_requests": self.weights.respect_time_off_requests,
            "reward_seniority": self.weights.reward_seniority,
            "balance_weekend_shifts": self.weights.balance_weekend_shifts,
            "minimize_overstaffing": self.weights.minimize_overstaffing,
            "reward_skill_matching": self.weights.reward_skill_matching,
            "balance_workload": self.weights.balance_workload,
            "minimize_compensation": self.weights.minimize_compensation,
        }
