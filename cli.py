"""
Interactive CLI interface for the shift scheduling system.

Provides a pleasant, user-friendly command-line interface with menus,
validation, and interactive feedback. All comments are in English.
"""

import sys
import time
import json
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent))

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


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_menu(title: str, options: List[str]) -> int:
    """
    Display a menu and get user selection.
    
    Args:
        title: Menu title
        options: List of menu options
        
    Returns:
        User's selected option index (0-based)
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}{title}{Colors.ENDC}")
    for i, option in enumerate(options, 1):
        print(f"  {Colors.BLUE}{i}.{Colors.ENDC} {option}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Select option (1-{len(options)}): {Colors.ENDC}")
            choice_int = int(choice)
            if 1 <= choice_int <= len(options):
                return choice_int - 1
            print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Invalid input. Please enter a number.")


def check_backend_health() -> bool:
    """
    Check if the backend system is working correctly.
    
    Returns:
        True if all checks pass, False otherwise
    """
    print_header("🔍 System Health Check")
    
    checks_passed = 0
    checks_total = 5
    
    try:
        print_info("Check 1/5: Importing core modules...")
        from src.models.data_models import Worker, Shift
        from src.solver.core_solver import ShiftSchedulingSolver
        from src.api.main import create_app
        print_success("Core modules imported successfully")
        checks_passed += 1
    except Exception as e:
        print_error(f"Failed to import core modules: {e}")
        return False
    
    try:
        print_info("Check 2/5: Creating sample data...")
        workers = [
            Worker(
                id=1,
                name="Test Worker",
                seniority_level=2,
                skills=[],
                hourly_rate=20.0,
                preferences=WorkerPreference(worker_id=1, max_shifts_per_week=5),
            )
        ]
        
        shifts = [
            Shift(
                id=1,
                date="2026-04-01",
                start_time="08:00",
                end_time="16:00",
                workers_required=1,
            )
        ]
        print_success("Sample data created successfully")
        checks_passed += 1
    except Exception as e:
        print_error(f"Failed to create sample data: {e}")
        return False
    
    try:
        print_info("Check 3/5: Creating scheduling request...")
        request = SchedulingRequest(
            workers=workers,
            shifts=shifts,
            scheduling_period_start="2026-04-01",
            scheduling_period_end="2026-04-30",
        )
        print_success("Scheduling request created successfully")
        checks_passed += 1
    except Exception as e:
        print_error(f"Failed to create request: {e}")
        return False
    
    try:
        print_info("Check 4/5: Initializing solver...")
        solver = ShiftSchedulingSolver(timeout_seconds=5, top_k=2)
        print_success("Solver initialized successfully")
        checks_passed += 1
    except Exception as e:
        print_error(f"Failed to initialize solver: {e}")
        return False
    
    try:
        print_info("Check 5/5: Running solver...")
        response = solver.solve(request, ObjectiveWeights())
        
        if response.solutions:
            print_success(f"Solver executed successfully ({len(response.solutions)} solutions found)")
            checks_passed += 1
        else:
            print_warning("Solver executed but found no solutions")
    except Exception as e:
        print_error(f"Failed to run solver: {e}")
        return False
    
    print()
    print_header(f"Health Check Results: {checks_passed}/{checks_total} Passed")
    
    if checks_passed == checks_total:
        print_success("All system checks passed! Backend is healthy. ✨")
        return True
    else:
        print_error(f"Some checks failed ({checks_total - checks_passed} issues found)")
        return False


def show_demo_solution() -> None:
    """Run a demo scheduling problem and show the solution."""
    print_header("📊 Running Demo Scheduling Problem")
    
    print_info("Setting up demo scenario with 3 workers and 4 shifts...")
    
    workers = [
        Worker(
            id=1,
            name="Alice Johnson",
            seniority_level=3,
            skills=[Skill(name="ICU", level=SkillLevel.ADVANCED)],
            hourly_rate=28.0,
            preferences=WorkerPreference(
                worker_id=1,
                max_shifts_per_week=5,
                no_consecutive_shifts=True,
            ),
        ),
        Worker(
            id=2,
            name="Bob Smith",
            seniority_level=1,
            skills=[],
            hourly_rate=18.0,
            preferences=WorkerPreference(
                worker_id=2,
                max_shifts_per_week=4,
            ),
        ),
        Worker(
            id=3,
            name="Carol Davis",
            seniority_level=2,
            skills=[Skill(name="General", level=SkillLevel.INTERMEDIATE)],
            hourly_rate=22.0,
            preferences=WorkerPreference(
                worker_id=3,
                max_shifts_per_week=5,
            ),
        ),
    ]
    
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
            workers_required=1,
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
    
    request = SchedulingRequest(
        workers=workers,
        shifts=shifts,
        scheduling_period_start="2026-04-01",
        scheduling_period_end="2026-04-04",
    )
    
    weights = ObjectiveWeights(
        reward_seniority=7.0,
        balance_weekend_shifts=10.0,
    )
    
    print_info("Solving scheduling problem...")
    solver = ShiftSchedulingSolver(timeout_seconds=10, top_k=3)
    
    start = time.time()
    response = solver.solve(request, weights)
    elapsed = time.time() - start
    
    print_success(f"Solved in {elapsed:.2f} seconds!\n")
    
    print(f"{Colors.BOLD}📋 Problem Summary:{Colors.ENDC}")
    print(f"  Workers: {len(workers)}")
    print(f"  Shifts: {len(shifts)}")
    print(f"  Period: {request.scheduling_period_start} to {request.scheduling_period_end}")
    print(f"  Solutions Found: {response.total_solutions_found}\n")
    
    for solution in response.solutions:
        print(f"{Colors.BOLD}Solution {solution.solution_rank}:{Colors.ENDC} "
              f"Score={solution.objective_value:.2f}")
        
        for assignment in solution.assignments:
            worker = next(w for w in workers if w.id == assignment.worker_id)
            shift = next(s for s in shifts if s.id == assignment.shift_id)
            seniority_stars = "★" * worker.seniority_level
            print(f"  {Colors.GREEN}→{Colors.ENDC} {worker.name:20} {seniority_stars:4} "
                  f"| {shift.date} {shift.shift_type}")
        print()


def show_api_info() -> None:
    """Show information about the REST API."""
    print_header("🌐 REST API Information")
    
    api_info = {
        "Base URL": "http://localhost:8000",
        "Interactive Docs": "http://localhost:8000/docs",
        "ReDoc": "http://localhost:8000/redoc",
    }
    
    print(f"{Colors.BOLD}API Endpoints:{Colors.ENDC}")
    print(f"  {Colors.GREEN}POST{Colors.ENDC} /schedule ..................... Generate solutions")
    print(f"  {Colors.GREEN}POST{Colors.ENDC} /validate-request ............. Validate request")
    print(f"  {Colors.GREEN}GET{Colors.ENDC}  /objective-weights-defaults ... Get default weights")
    print(f"  {Colors.GREEN}GET{Colors.ENDC}  /health ........................ Health check")
    print(f"  {Colors.GREEN}GET{Colors.ENDC}  /config/algorithm ............. Algorithm info\n")
    
    print(f"{Colors.BOLD}Quick Start:{Colors.ENDC}")
    print(f"  1. Start server: {Colors.CYAN}python main.py{Colors.ENDC}")
    print(f"  2. Visit: {Colors.CYAN}http://localhost:8000/docs{Colors.ENDC}")
    print(f"  3. Try POST /schedule with sample data\n")


def show_feature_overview() -> None:
    """Show overview of system features."""
    print_header("✨ System Features")
    
    print(f"{Colors.BOLD}Hard Constraints (Non-negotiable):{Colors.ENDC}")
    constraints = [
        "Shift coverage - exact worker count",
        "No consecutive shifts (configurable)",
        "Maximum shifts per week",
        "Worker availability (time-off)",
        "Skill requirements",
    ]
    for c in constraints:
        print(f"  {Colors.GREEN}✓{Colors.ENDC} {c}")
    
    print(f"\n{Colors.BOLD}Soft Constraints (Weighted):{Colors.ENDC}")
    soft = [
        "Respect time-off requests (weight: 10.0)",
        "Reward seniority (weight: 5.0)",
        "Balance weekend shifts (weight: 8.0)",
        "Minimize overstaffing (weight: 3.0)",
        "Reward skill matching (weight: 7.0)",
        "Balance workload (weight: 6.0)",
        "Minimize compensation (weight: 2.0)",
    ]
    for s in soft:
        print(f"  {Colors.BLUE}⚖{Colors.ENDC}  {s}")
    
    print(f"\n{Colors.BOLD}Advanced Features:{Colors.ENDC}")
    features = [
        "Top-k solutions (multiple options)",
        "Dynamic weight configuration",
        "Skill proficiency levels",
        "Flexible scheduling periods",
        "REST API with auto-documentation",
    ]
    for f in features:
        print(f"  {Colors.CYAN}◆{Colors.ENDC} {f}")
    
    print()


def main() -> None:
    """Main interactive CLI menu."""
    print_header("🎯 Shift Scheduling System - Interactive CLI")
    
    while True:
        options = [
            "🔍 Run System Health Check",
            "📊 Run Demo Scheduling Problem",
            "✨ Show System Features",
            "🌐 REST API Information",
            "💾 Generate Sample Request JSON",
            "❌ Exit",
        ]
        
        choice = print_menu("Main Menu", options)
        
        if choice == 0:
            check_backend_health()
        elif choice == 1:
            show_demo_solution()
        elif choice == 2:
            show_feature_overview()
        elif choice == 3:
            show_api_info()
        elif choice == 4:
            generate_sample_json()
        elif choice == 5:
            print_success("Thank you for using Shift Scheduler! Goodbye! 👋")
            break


def generate_sample_json() -> None:
    """Generate and display sample JSON request."""
    print_header("📝 Sample API Request (JSON)")
    
    sample_request = {
        "workers": [
            {
                "id": 1,
                "name": "Alice Johnson",
                "seniority_level": 3,
                "skills": [
                    {"name": "ICU", "level": "ADVANCED"}
                ],
                "hourly_rate": 28.0,
                "preferences": {
                    "worker_id": 1,
                    "max_shifts_per_week": 5,
                    "no_consecutive_shifts": True,
                    "unavailable_dates": []
                }
            },
            {
                "id": 2,
                "name": "Bob Smith",
                "seniority_level": 1,
                "skills": [],
                "hourly_rate": 18.0,
                "preferences": {
                    "worker_id": 2,
                    "max_shifts_per_week": 4,
                    "no_consecutive_shifts": False
                }
            }
        ],
        "shifts": [
            {
                "id": 1,
                "date": "2026-04-01",
                "start_time": "08:00",
                "end_time": "16:00",
                "shift_type": "morning",
                "required_skills": [
                    {"name": "ICU", "level": "INTERMEDIATE"}
                ],
                "workers_required": 2,
                "is_weekend": False
            }
        ],
        "scheduling_period_start": "2026-04-01",
        "scheduling_period_end": "2026-04-30"
    }
    
    print(Colors.CYAN + json.dumps(sample_request, indent=2) + Colors.ENDC)
    print()
    print_info("Copy this JSON and use it in POST /schedule request")
    print_info("Visit http://localhost:8000/docs for interactive testing")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program interrupted by user.{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
