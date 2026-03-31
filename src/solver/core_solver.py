"""
Core shift scheduling solver engine using OR-Tools CP-SAT.

This module implements the main solver that combines hard constraints,
dynamic soft constraints, and generates top-k solutions. All comments
are in English to prevent RTL rendering issues.
"""

import time
from typing import Dict, List, Tuple, Optional
from ortools.sat.python import cp_model
from ..models.data_models import (
    Worker,
    Shift,
    SchedulingRequest,
    ObjectiveWeights,
    ScheduleAssignment,
    SchedulingSolution,
    SchedulingResponse,
)
from ..constraints.hard_constraints import HardConstraintHandler
from ..objectives.dynamic_objectives import DynamicObjectiveFunction


class TopKSolutionCollector(cp_model.CpSolverSolutionCallback):
    """
    Custom callback to collect top-k solutions during solver execution.
    
    This callback is invoked each time the solver finds a better solution.
    We collect solutions ranked by their objective value and maintain
    the top k solutions found so far.
    """

    def __init__(self, assignment_vars: Dict[Tuple[int, int], "cp_model.IntVar"], k: int = 5):
        """
        Initialize the solution collector.
        
        Args:
            assignment_vars: Dictionary of assignment variables
            k: Number of top solutions to collect
        """
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.assignment_vars = assignment_vars
        self.k = k
        self.solutions = []
        self.solution_count = 0

    def on_solution_callback(self) -> None:
        """
        Called whenever a new solution is found by the solver.
        
        This method extracts the solution and adds it to our collection
        if it ranks in the top k.
        """
        current_objective = self.ObjectiveValue()
        self.solution_count += 1
        
        solution_data = {
            "objective": current_objective,
            "assignments": {},
            "timestamp": time.time(),
        }
        
        for (worker_id, shift_id), var in self.assignment_vars.items():
            solution_data["assignments"][(worker_id, shift_id)] = self.Value(var)
        
        self.solutions.append(solution_data)
        
        if len(self.solutions) > self.k:
            self.solutions.sort(key=lambda x: x["objective"])
            self.solutions = self.solutions[:self.k]

    def get_top_k_solutions(self) -> List[Dict]:
        """
        Get the top k solutions found so far, sorted by objective value.
        
        Returns:
            List of solution dictionaries sorted by objective (best first)
        """
        self.solutions.sort(key=lambda x: x["objective"])
        return self.solutions[:self.k]


class ShiftSchedulingSolver:
    """
    Main solver engine for the shift scheduling problem.
    
    Orchestrates the creation of the OR-Tools CP-SAT model, adds all constraints,
    sets up the objective function, and solves for top-k solutions.
    """

    def __init__(self, timeout_seconds: float = 60.0, top_k: int = 5):
        """
        Initialize the solver.
        
        Args:
            timeout_seconds: Maximum solver runtime in seconds
            top_k: Number of top solutions to collect
        """
        self.timeout_seconds = timeout_seconds
        self.top_k = top_k
        self.model = None
        self.assignments = {}
        self.shift_coverage = {}

    def solve(
        self,
        request: SchedulingRequest,
        objective_weights: ObjectiveWeights,
    ) -> SchedulingResponse:
        """
        Main solve method that orchestrates the entire scheduling process.
        
        Args:
            request: The scheduling request with workers and shifts
            objective_weights: Weights for dynamic soft constraints
            
        Returns:
            SchedulingResponse containing top-k solutions
            
        Raises:
            ValueError: If the request contains invalid data
        """
        start_time = time.time()
        
        try:
            self._validate_request(request)
            self._create_model()
            self._create_variables(request)
            self._add_constraints(request)
            self._set_objective(request, objective_weights)
            
            solutions = self._solve_and_collect_top_k(request)
            
            elapsed = time.time() - start_time
            
            return self._build_response(request, solutions, elapsed)
        
        except Exception as e:
            raise ValueError(f"Solver error: {str(e)}")

    def _validate_request(self, request: SchedulingRequest) -> None:
        """
        Validate the scheduling request for common issues.
        
        Args:
            request: The scheduling request to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not request.workers:
            raise ValueError("At least one worker is required")
        
        if not request.shifts:
            raise ValueError("At least one shift is required")
        
        unique_worker_ids = set(w.id for w in request.workers)
        if len(unique_worker_ids) != len(request.workers):
            raise ValueError("Duplicate worker IDs detected")
        
        unique_shift_ids = set(s.id for s in request.shifts)
        if len(unique_shift_ids) != len(request.shifts):
            raise ValueError("Duplicate shift IDs detected")

    def _create_model(self) -> None:
        """Create a new CP-SAT model instance."""
        self.model = cp_model.CpModel()

    def _create_variables(self, request: SchedulingRequest) -> None:
        """
        Create decision variables for all worker-shift assignments.
        
        Args:
            request: The scheduling request
        """
        self.assignments = {}
        self.shift_coverage = {}

        # Optional eligibility map from metadata: list of (worker_id, shift_id) pairs allowed
        allowed_pairs = None
        if request.metadata and isinstance(request.metadata, dict):
            ap = request.metadata.get("allowed_pairs")
            if ap:
                allowed_pairs = set((int(w), int(s)) for w, s in ap)

        # Build per-shift allowed worker ids to size coverage bounds sensibly
        allowed_by_shift: Dict[int, List[int]] = {s.id: [] for s in request.shifts}
        if allowed_pairs is None:
            for s in request.shifts:
                allowed_by_shift[s.id] = [w.id for w in request.workers]
        else:
            for (w_id, s_id) in allowed_pairs:
                if s_id in allowed_by_shift:
                    allowed_by_shift[s_id].append(w_id)

        for shift in request.shifts:
            max_cover = len(allowed_by_shift.get(shift.id, [])) or len(request.workers)
            self.shift_coverage[shift.id] = self.model.NewIntVar(
                0,
                max_cover,
                f"coverage_shift_{shift.id}",
            )

        for worker in request.workers:
            for shift in request.shifts:
                if allowed_pairs is not None and (worker.id, shift.id) not in allowed_pairs:
                    # Disallow this combination by skipping variable creation
                    continue
                var = self.model.NewBoolVar(f"assign_worker_{worker.id}_shift_{shift.id}")
                self.assignments[(worker.id, shift.id)] = var

    def _add_constraints(self, request: SchedulingRequest) -> None:
        """
        Add all hard constraints to the model.
        
        Args:
            request: The scheduling request
        """
        constraint_handler = HardConstraintHandler(self.model)
        constraint_handler.apply_all_hard_constraints(
            request,
            self.assignments,
            self.shift_coverage,
        )

    def _set_objective(
        self,
        request: SchedulingRequest,
        objective_weights: ObjectiveWeights,
    ) -> None:
        """
        Set up the dynamic objective function.
        
        Args:
            request: The scheduling request
            objective_weights: Weights for each soft constraint criterion
        """
        objective_fn = DynamicObjectiveFunction(self.model, objective_weights)
        objective_fn.build_objective_function(request, self.assignments)

    def _solve_and_collect_top_k(self, request: SchedulingRequest) -> List[Dict]:
        """
        Execute the solver and collect top-k solutions.
        
        Args:
            request: The scheduling request
            
        Returns:
            List of top-k solutions
        """
        # Instead of relying only on a single search with a callback, we iteratively
        # find a solution, then add a "no-good" constraint to force the next
        # solution to differ in at least one assignment. This guarantees up to
        # top_k distinct schedules when they exist.

        solutions: List[Dict] = []

        for _ in range(self.top_k):
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = self.timeout_seconds
            solver.parameters.log_search_progress = False

            status = solver.Solve(self.model)
            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                break

            current_objective = solver.ObjectiveValue()

            # Extract assignment values for this solution
            assignment_values: Dict[Tuple[int, int], int] = {}
            for key, var in self.assignments.items():
                assignment_values[key] = solver.Value(var)

            solutions.append(
                {
                    "objective": current_objective,
                    "assignments": assignment_values,
                    "timestamp": time.time(),
                }
            )

            # Build a no-good constraint: in the next solution, at least one
            # assignment must flip relative to this one.
            diff_terms = []
            for key, value in assignment_values.items():
                var = self.assignments[key]
                if value == 1:
                    diff_terms.append(1 - var)
                else:
                    diff_terms.append(var)

            # If there are no variables (degenerate case), stop
            if not diff_terms:
                break

            self.model.Add(sum(diff_terms) >= 1)

        # Sort by objective (best first) and return
        solutions.sort(key=lambda x: x["objective"])
        return solutions[: self.top_k]

    def _build_response(
        self,
        request: SchedulingRequest,
        solutions: List[Dict],
        elapsed: float,
    ) -> SchedulingResponse:
        """
        Build the SchedulingResponse from raw solver solutions.
        
        Args:
            request: The scheduling request
            solutions: List of solution dictionaries
            elapsed: Total elapsed time in seconds
            
        Returns:
            SchedulingResponse with formatted solutions
        """
        scheduling_solutions = []
        
        for rank, solution_data in enumerate(solutions, start=1):
            assignments = []
            
            for (worker_id, shift_id), value in solution_data["assignments"].items():
                if value == 1:
                    assignments.append(
                        ScheduleAssignment(worker_id=worker_id, shift_id=shift_id)
                    )
            
            scheduling_solution = SchedulingSolution(
                assignments=assignments,
                objective_value=solution_data["objective"],
                solution_rank=rank,
                computation_time_seconds=elapsed / len(solutions),
            )
            scheduling_solutions.append(scheduling_solution)
        
        return SchedulingResponse(
            solutions=scheduling_solutions,
            total_solutions_found=len(solutions),
            total_computation_time_seconds=elapsed,
        )
