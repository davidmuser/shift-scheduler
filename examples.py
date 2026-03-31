"""
Comprehensive examples demonstrating the shift scheduling system.

This module shows various usage patterns and scenarios. All comments
are in English to prevent RTL rendering issues.
"""

from datetime import datetime, timedelta
from src.models.data_models import (
    Worker,
    Shift,
    WorkerPreference,
    Skill,
    SkillLevel,
    SchedulingRequest,
    ObjectiveWeights,
)
from src.solver.core_solver import ShiftSchedulingSolver


def example_1_basic_scheduling():
    """
    Example 1: Basic shift scheduling for a small team.
    
    Simple scenario with 3 workers and 4 shifts over one week.
    No special skills required.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Shift Scheduling")
    print("=" * 70)
    
    # Create workers
    workers = [
        Worker(
            id=1,
            name="Alice",
            seniority_level=2,
            skills=[],
            hourly_rate=20.0,
            preferences=WorkerPreference(
                worker_id=1,
                max_shifts_per_week=5,
                no_consecutive_shifts=True,
            ),
        ),
        Worker(
            id=2,
            name="Bob",
            seniority_level=1,
            skills=[],
            hourly_rate=18.0,
            preferences=WorkerPreference(
                worker_id=2,
                max_shifts_per_week=4,
                no_consecutive_shifts=False,
            ),
        ),
        Worker(
            id=3,
            name="Carol",
            seniority_level=3,
            skills=[],
            hourly_rate=25.0,
            preferences=WorkerPreference(
                worker_id=3,
                max_shifts_per_week=5,
                no_consecutive_shifts=True,
            ),
        ),
    ]
    
    # Create shifts for one week
    shifts = [
        Shift(
            id=1,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=2,
            date="2026-04-02",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=3,
            date="2026-04-03",
            start_time="16:00",
            end_time="00:00",
            shift_type="evening",
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=4,
            date="2026-04-04",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            workers_required=2,
            is_weekend=True,
        ),
    ]
    
    # Create request
    request = SchedulingRequest(
        workers=workers,
        shifts=shifts,
        scheduling_period_start="2026-04-01",
        scheduling_period_end="2026-04-04",
    )
    
    # Solve with default weights
    solver = ShiftSchedulingSolver(timeout_seconds=10, top_k=3)
    response = solver.solve(request, ObjectiveWeights())
    
    print(f"\nFound {response.total_solutions_found} solutions in {response.total_computation_time_seconds:.2f}s\n")
    
    for solution in response.solutions:
        print(f"Solution {solution.solution_rank} (Score: {solution.objective_value:.2f}):")
        for assignment in solution.assignments:
            worker_name = next(w.name for w in workers if w.id == assignment.worker_id)
            shift_date = next(s.date for s in shifts if s.id == assignment.shift_id)
            print(f"  - {worker_name} -> {shift_date}")
        print()


def example_2_specialized_skills():
    """
    Example 2: Scheduling with specialized skill requirements.
    
    Hospital ICU scenario with workers having different skill levels.
    ICU shifts require experienced staff.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Specialized Skills (Hospital ICU)")
    print("=" * 70)
    
    # Workers with varying ICU experience
    workers = [
        Worker(
            id=1,
            name="Dr. Smith",
            seniority_level=5,
            skills=[
                Skill(name="ICU", level=SkillLevel.EXPERT),
                Skill(name="Emergency", level=SkillLevel.ADVANCED),
            ],
            hourly_rate=45.0,
            preferences=WorkerPreference(
                worker_id=1,
                max_shifts_per_week=4,
            ),
        ),
        Worker(
            id=2,
            name="Nurse Johnson",
            seniority_level=3,
            skills=[Skill(name="ICU", level=SkillLevel.INTERMEDIATE)],
            hourly_rate=28.0,
            preferences=WorkerPreference(
                worker_id=2,
                max_shifts_per_week=5,
            ),
        ),
        Worker(
            id=3,
            name="Nurse Davis",
            seniority_level=2,
            skills=[
                Skill(name="General", level=SkillLevel.INTERMEDIATE),
                Skill(name="Pediatrics", level=SkillLevel.BASIC),
            ],
            hourly_rate=22.0,
            preferences=WorkerPreference(
                worker_id=3,
                max_shifts_per_week=5,
            ),
        ),
    ]
    
    # ICU and general ward shifts
    shifts = [
        Shift(
            id=1,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            shift_type="ICU",
            required_skills=[Skill(name="ICU", level=SkillLevel.INTERMEDIATE)],
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=2,
            date="2026-04-02",
            start_time="16:00",
            end_time="00:00",
            shift_type="ICU",
            required_skills=[Skill(name="ICU", level=SkillLevel.INTERMEDIATE)],
            workers_required=1,
            is_weekend=False,
        ),
        Shift(
            id=3,
            date="2026-04-03",
            start_time="08:00",
            end_time="16:00",
            shift_type="General",
            required_skills=[],
            workers_required=1,
            is_weekend=False,
        ),
    ]
    
    request = SchedulingRequest(
        workers=workers,
        shifts=shifts,
        scheduling_period_start="2026-04-01",
        scheduling_period_end="2026-04-03",
    )
    
    # Custom weights favoring skill matching
    weights = ObjectiveWeights(
        reward_skill_matching=15.0,
        reward_seniority=5.0,
        minimize_compensation=8.0,
    )
    
    solver = ShiftSchedulingSolver(timeout_seconds=10, top_k=2)
    response = solver.solve(request, weights)
    
    print(f"\nFound {response.total_solutions_found} solutions\n")
    
    for solution in response.solutions:
        print(f"Solution {solution.solution_rank} (Score: {solution.objective_value:.2f}):")
        for assignment in solution.assignments:
            worker = next(w for w in workers if w.id == assignment.worker_id)
            shift = next(s for s in shifts if s.id == assignment.shift_id)
            print(f"  - {worker.name} ({worker.seniority_level}★) -> {shift.shift_type} on {shift.date}")
        print()


def example_3_worker_preferences():
    """
    Example 3: Respecting worker preferences and time-off requests.
    
    Shows how to handle worker unavailability and preferred shift types.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Worker Preferences & Time-Off")
    print("=" * 70)
    
    workers = [
        Worker(
            id=1,
            name="Morning Person",
            seniority_level=2,
            skills=[],
            hourly_rate=20.0,
            preferences=WorkerPreference(
                worker_id=1,
                preferred_shift_types=["morning"],
                max_shifts_per_week=5,
                no_consecutive_shifts=True,
            ),
        ),
        Worker(
            id=2,
            name="Night Owl",
            seniority_level=2,
            skills=[],
            hourly_rate=21.0,
            preferences=WorkerPreference(
                worker_id=2,
                preferred_shift_types=["evening", "night"],
                max_shifts_per_week=5,
                unavailable_dates={"2026-04-05", "2026-04-12"},  # Time-off requests
            ),
        ),
        Worker(
            id=3,
            name="Weekend Lover",
            seniority_level=1,
            skills=[],
            hourly_rate=19.0,
            preferences=WorkerPreference(
                worker_id=3,
                prefer_weekends=True,
                max_shifts_per_week=4,
            ),
        ),
    ]
    
    # Mix of shifts across all days and types
    shifts = []
    dates = ["2026-04-01", "2026-04-05", "2026-04-12"]  # Some conflict with time-off
    shift_id = 1
    
    for date in dates:
        is_weekend = date in ["2026-04-04", "2026-04-05"]
        
        shifts.append(Shift(
            id=shift_id,
            date=date,
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            workers_required=2,
            is_weekend=is_weekend,
        ))
        shift_id += 1
        
        shifts.append(Shift(
            id=shift_id,
            date=date,
            start_time="16:00",
            end_time="00:00",
            shift_type="evening",
            workers_required=1,
            is_weekend=is_weekend,
        ))
        shift_id += 1
    
    request = SchedulingRequest(
        workers=workers,
        shifts=shifts,
        scheduling_period_start="2026-04-01",
        scheduling_period_end="2026-04-12",
    )
    
    # High weight on time-off requests
    weights = ObjectiveWeights(
        respect_time_off_requests=20.0,
        balance_weekend_shifts=10.0,
    )
    
    solver = ShiftSchedulingSolver(timeout_seconds=15, top_k=2)
    response = solver.solve(request, weights)
    
    print(f"\nFound {response.total_solutions_found} solutions\n")
    
    for solution in response.solutions:
        print(f"Solution {solution.solution_rank}:")
        for assignment in solution.assignments:
            worker = next(w for w in workers if w.id == assignment.worker_id)
            shift = next(s for s in shifts if s.id == assignment.shift_id)
            print(f"  - {worker.name} -> {shift.shift_type} on {shift.date}")
        print()


def example_4_custom_weights():
    """
    Example 4: Demonstrating dynamic weight adjustment for different objectives.
    
    Shows how the same problem can produce different solutions with different weights.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Dynamic Weight Customization")
    print("=" * 70)
    
    # Simple scenario
    workers = [
        Worker(
            id=1,
            name="Senior (Rate: $30)",
            seniority_level=4,
            skills=[],
            hourly_rate=30.0,
            preferences=WorkerPreference(worker_id=1, max_shifts_per_week=3),
        ),
        Worker(
            id=2,
            name="Junior (Rate: $15)",
            seniority_level=1,
            skills=[],
            hourly_rate=15.0,
            preferences=WorkerPreference(worker_id=2, max_shifts_per_week=5),
        ),
    ]
    
    shifts = [
        Shift(
            id=i,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            workers_required=1,
            is_weekend=False,
        )
        for i in range(1, 4)
    ]
    
    request = SchedulingRequest(
        workers=workers,
        shifts=shifts,
        scheduling_period_start="2026-04-01",
        scheduling_period_end="2026-04-01",
    )
    
    # Scenario 1: Prioritize seniority
    print("\nScenario A: High seniority weight (Reward senior workers)")
    weights_a = ObjectiveWeights(
        reward_seniority=20.0,
        minimize_compensation=1.0,
    )
    
    solver = ShiftSchedulingSolver(timeout_seconds=5, top_k=1)
    response_a = solver.solve(request, weights_a)
    
    if response_a.solutions:
        sol = response_a.solutions[0]
        print(f"  Result: {len(sol.assignments)} assignments")
        for a in sol.assignments:
            w = next(w for w in workers if w.id == a.worker_id)
            print(f"    - {w.name}")
    
    # Scenario 2: Minimize cost
    print("\nScenario B: High cost minimization weight (Use cheaper workers)")
    weights_b = ObjectiveWeights(
        reward_seniority=1.0,
        minimize_compensation=20.0,
    )
    
    response_b = solver.solve(request, weights_b)
    
    if response_b.solutions:
        sol = response_b.solutions[0]
        print(f"  Result: {len(sol.assignments)} assignments")
        for a in sol.assignments:
            w = next(w for w in workers if w.id == a.worker_id)
            print(f"    - {w.name}")
    
    print("\nDemonstrates how weights dramatically change solution characteristics!")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SHIFT SCHEDULING SYSTEM - COMPREHENSIVE EXAMPLES")
    print("=" * 70)
    
    try:
        example_1_basic_scheduling()
        example_2_specialized_skills()
        example_3_worker_preferences()
        example_4_custom_weights()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
