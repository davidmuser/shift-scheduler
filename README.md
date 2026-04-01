
# Shift Scheduler SaaS

Expert-level shift scheduling backend using Google OR-Tools CP-SAT solver with dynamic soft constraints and top-k solutions.

## Features

### Core Capabilities
- **CP-SAT Solver Integration**: Uses Google OR-Tools Constraint Programming SAT solver for optimal solution finding
- **Hard Constraints**: Enforces non-negotiable scheduling rules
  - No consecutive shifts for workers
  - Maximum shifts per week limits
  - Worker availability restrictions
  - Skill requirement fulfillment
  - Shift coverage requirements
  
- **Dynamic Soft Constraints**: UI-driven objective function with weighted criteria
  - Respect time-off requests
  - Reward seniority in shift allocation
  - Balance weekend shifts fairly
  - Minimize overstaffing
  - Reward skill matching
  - Balance workload distribution
  - Minimize compensation costs

- **Top-k Solutions**: Returns multiple high-quality solutions for user selection
    - Uses iterative re-solving with no-good constraints to collect distinct schedules
    - Ranks solutions by objective value
    - Lets users compare and choose between different scheduling options

### Architecture

```
src/
├── models/                  # Pydantic data models
│   └── data_models.py       # Worker, Shift, Request, Response definitions
├── constraints/             # Hard constraint handlers
│   └── hard_constraints.py  # Constraint enforcement logic
├── objectives/              # Soft constraint handlers
│   └── dynamic_objectives.py # Weighted objective function
├── solver/                  # Core solving engine
│   └── core_solver.py       # ShiftSchedulingSolver + TopKSolutionCollector
└── api/                     # FastAPI REST endpoints
    └── main.py              # API routes and application setup
```

## Installation

### Prerequisites
- Python 3.9+
- pip or conda package manager

### Setup

1. **Clone or create the project directory**
```bash
cd shift-scheduler
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

## Usage

### As a Library

```python
from src.models.data_models import (
    Worker,
    Shift,
    SchedulingRequest,
    ObjectiveWeights,
    Skill,
    SkillLevel,
    WorkerPreference,
)
from src.solver.core_solver import ShiftSchedulingSolver

# Create workers
workers = [
    Worker(
        id=1,
        name="Alice Johnson",
        seniority_level=3,
        skills=[Skill(name="ICU", level=SkillLevel.ADVANCED)],
        hourly_rate=25.0,
        preferences=WorkerPreference(
            worker_id=1,
            max_shifts_per_week=5,
            no_consecutive_shifts=True,
        )
    ),
    # ... more workers
]

# Create shifts
shifts = [
    Shift(
        id=1,
        date="2026-04-01",
        start_time="08:00",
        end_time="16:00",
        shift_type="morning",
        required_skills=[Skill(name="ICU", level=SkillLevel.INTERMEDIATE)],
        workers_required=2,
        is_weekend=False,
    ),
    # ... more shifts
]

# Create scheduling request
request = SchedulingRequest(
    workers=workers,
    shifts=shifts,
    scheduling_period_start="2026-04-01",
    scheduling_period_end="2026-04-30",
)

# Set custom objective weights (optional)
weights = ObjectiveWeights(
    respect_time_off_requests=10.0,
    reward_seniority=7.0,
    balance_weekend_shifts=8.0,
)

# Solve with top-k solutions
solver = ShiftSchedulingSolver(timeout_seconds=60, top_k=5)
response = solver.solve(request, weights)

# Access solutions
for solution in response.solutions:
    print(f"Solution {solution.solution_rank}: {solution.objective_value}")
    for assignment in solution.assignments:
        print(f"  Worker {assignment.worker_id} -> Shift {assignment.shift_id}")
```

### As a REST API

1. **Start the server**
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Example API Call**
```bash
curl -X POST "http://localhost:8000/schedule?top_k=5&timeout_seconds=60" \
    -H "Content-Type: application/json" \
    -d '{
        "workers": [...],
        "shifts": [...],
        "scheduling_period_start": "2026-04-01",
        "scheduling_period_end": "2026-04-30"
    }'
```

## API Endpoints

### POST `/schedule`
Generate top-k scheduling solutions.

**Parameters:**
- `request` (body): SchedulingRequest with workers and shifts
- `objective_weights` (body, optional): Custom weights for soft constraints
- `top_k` (query): Number of solutions to return (1-100, default: 5)
- `timeout_seconds` (query): Solver timeout (1-600, default: 60)

**Response:** SchedulingResponse with top-k solutions

### GET `/objective-weights-defaults`
Get default objective weights.

**Response:** ObjectiveWeights with default values

### POST `/validate-request`
Validate a scheduling request without solving.

**Response:** Validation result with warnings/errors

### GET `/health`
Health check endpoint.

**Response:** Service status

### GET `/config/algorithm`
Get algorithm configuration details.

**Response:** Algorithm information

## Data Models

### Worker
Represents a worker (nurse, staff member, etc.)

```python
Worker(
    id: int,                              # Unique identifier
    name: str,                            # Full name
    seniority_level: int,                 # 0=junior, higher=senior
    skills: List[Skill],                  # List of skills
    hourly_rate: float,                   # Hourly compensation
    preferences: WorkerPreference,        # Preferences and constraints
)
```

### Shift
Represents a shift to be staffed.

```python
Shift(
    id: int,                              # Unique identifier
    date: str,                            # ISO format (YYYY-MM-DD)
    start_time: str,                      # HH:MM format
    end_time: str,                        # HH:MM format
    shift_type: str,                      # e.g., "morning", "evening", "night"
    required_skills: List[Skill],         # Skills required
    workers_required: int,                # Number of workers needed
    is_weekend: bool,                     # Weekend flag
)
```

### ObjectiveWeights
Dynamic weights for soft constraints (UI-configurable).

```python
ObjectiveWeights(
    respect_time_off_requests: float,     # Default: 10.0
    reward_seniority: float,              # Default: 5.0
    balance_weekend_shifts: float,        # Default: 8.0
    minimize_overstaffing: float,         # Default: 3.0
    reward_skill_matching: float,         # Default: 7.0
    balance_workload: float,              # Default: 6.0
    minimize_compensation: float,         # Default: 2.0
)
```

## Hard Constraints

1. **Shift Coverage**: Each shift must be covered by exactly the required number of workers
2. **No Consecutive Shifts**: Workers cannot work back-to-back shifts (configurable per worker)
3. **Max Shifts Per Week**: Respects per-worker maximum shifts per calendar week
4. **Worker Availability**: Prevents assignment on unavailable dates
5. **Skill Requirements**: Ensures shifts have workers with required skills

## Soft Constraints (Objective Function Terms)

The objective function is dynamically weighted based on UI inputs:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Time-Off Requests | 10.0 | Respect worker unavailability preferences |
| Seniority Rewards | 5.0 | Give better shifts to senior workers |
| Weekend Balance | 8.0 | Distribute weekend shifts fairly |
| Skill Matching | 7.0 | Assign skilled workers to specialized shifts |
| Workload Balance | 6.0 | Even distribution of total hours |
| Cost Minimization | 2.0 | Minimize payroll by using junior workers when possible |
| Overstaffing Penalty | 3.0 | Penalize excessive staffing |

## Algorithm Details

### Solver: Google OR-Tools CP-SAT
- **Type**: Constraint Programming with Satisfiability (SAT) solving
- **Performance**: Handles large-scale combinatorial optimization
- **Top-k Collection**: Iteratively re-solves the model with no-good constraints to collect multiple high-quality, distinct solutions
- **Timeout**: Configurable solver runtime limit

### Solution Quality Ranking
Solutions are ranked by their objective value:
- Lower objective = better solution (minimization problem)
- Rank 1 = best solution found
- Subsequent ranks = alternative high-quality solutions

## Testing

Run unit tests:
```bash
pytest tests/
```

With coverage:
```bash
pytest --cov=src tests/
```

## Development

Code style and formatting:
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## Coding Standards

- **Language**: English only for all comments (prevents RTL rendering issues)
- **Style**: PEP 8 with line length of 100 characters
- **Type Hints**: Full type annotations for all functions
- **Documentation**: Comprehensive docstrings for all public classes and methods
- **Testing**: Unit tests for all core functionality

## Architecture Principles

1. **Separation of Concerns**: Models, constraints, objectives, and solver are modular
2. **Extensibility**: Easy to add new constraint types or objective terms
3. **Type Safety**: Pydantic validation for all inputs
4. **Error Handling**: Graceful error messages and validation
5. **Performance**: Efficient constraint representation and solving

## Performance Characteristics

- **Small instances** (≤20 workers, ≤50 shifts): <1 second
- **Medium instances** (20-50 workers, 50-200 shifts): 5-30 seconds
- **Large instances** (50+ workers, 200+ shifts): 30-60 seconds (configurable timeout)

## Extending the System

### Adding New Constraint Types

1. Create new method in `HardConstraintHandler` or create a new handler class
2. Call from `apply_all_hard_constraints()`
3. Add validation to `SchedulingRequest` if needed

### Adding New Objective Terms

1. Create new method in `DynamicObjectiveFunction`
2. Call from `build_objective_function()`
3. Add weight field to `ObjectiveWeights` model

### Adding API Endpoints

1. Add new route function in `src/api/main.py`
2. Use Pydantic models for request/response validation
3. Add appropriate error handling

## Troubleshooting

### "No valid schedule found"
- Check worker availability and shift coverage requirements
- Validate skill requirements are achievable
- Increase timeout if running large instances

### "ImportError: No module named 'ortools'"
- Ensure OR-Tools is installed: `pip install ortools`

### "Validation errors"
- Ensure all worker/shift IDs are unique
- Check date formats (ISO format: YYYY-MM-DD)
- Verify time formats (HH:MM format)

## References

- [Google OR-Tools Documentation](https://developers.google.com/optimization)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
