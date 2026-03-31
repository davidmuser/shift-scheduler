# Shift Scheduling Backend System - Project Summary

## 🎯 Project Overview

Expert-level shift scheduling backend built for constraint programming and optimization. Solves the **Nurse Scheduling Problem** (and generalizations) using Google OR-Tools CP-SAT solver with:

- **Hard Constraints**: Non-negotiable scheduling rules
- **Dynamic Soft Constraints**: UI-configurable weighted objectives  
- **Top-k Solutions**: Returns multiple high-quality options instead of just one
- **Professional Architecture**: Clean, modular, production-ready code

## 📦 What's Included

### Core System
```
src/
├── models/              # Pydantic data models with validation
├── constraints/         # Hard constraint enforcement
├── objectives/          # Dynamic objective function with 7 weighted terms
├── solver/              # CP-SAT solver orchestration + top-k callback
└── api/                 # FastAPI REST endpoints
```

### Key Features
- ✅ Worker skills and seniority levels
- ✅ Worker availability and preferences
- ✅ Shift coverage requirements
- ✅ No consecutive shifts constraint
- ✅ Weekly shift limits per worker
- ✅ Skill requirement validation
- ✅ Dynamic weight-based objective function
- ✅ Top-k solution collection via CpSolverSolutionCallback
- ✅ REST API with validation endpoint
- ✅ Full type hints and Pydantic validation

### Documentation
- `README.md`: Complete usage guide and API reference
- `ARCHITECTURE.md`: System design, constraint formulation, extensibility
- `QUICKSTART.md`: Installation and quick examples
- `examples.py`: 4 comprehensive usage scenarios
- `pyproject.toml`: Dependency management and build config

## 🚀 Quick Start

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run API Server
```bash
python main.py
# Visit http://localhost:8000/docs for interactive API docs
```

### Use as Library
```python
from src.models.data_models import Worker, Shift, SchedulingRequest, ObjectiveWeights
from src.solver.core_solver import ShiftSchedulingSolver

request = SchedulingRequest(workers=[...], shifts=[...], ...)
weights = ObjectiveWeights(reward_seniority=7.0, ...)

solver = ShiftSchedulingSolver(timeout_seconds=60, top_k=5)
response = solver.solve(request, weights)

for solution in response.solutions:
    print(f"Solution {solution.solution_rank}: {solution.objective_value}")
```

## 🎓 Architecture Highlights

### Hard Constraints (Must-Satisfy)
1. **Shift Coverage**: Each shift covered by exactly required workers
2. **No Consecutive Shifts**: Workers can't work back-to-back (configurable)
3. **Max Shifts Per Week**: Respect weekly limits per worker
4. **Worker Availability**: Don't schedule on unavailable dates
5. **Skill Requirements**: Ensure required skills present in every shift

### Soft Constraints (Preferences - Weighted Objective)
| Criterion | Default Weight | Purpose |
|-----------|---|---|
| Time-Off Requests | 10.0 | Respect unavailability preferences |
| Seniority Rewards | 5.0 | Give better shifts to senior workers |
| Weekend Balance | 8.0 | Distribute weekends fairly |
| Skill Matching | 7.0 | Assign skilled workers to specialized shifts |
| Workload Balance | 6.0 | Even distribution of total hours |
| Cost Minimization | 2.0 | Minimize payroll by using junior workers |
| Overstaffing Penalty | 3.0 | Avoid excessive staffing |

### Top-k Solutions
- Uses `CpSolverSolutionCallback` for iterative solution collection
- Each solution ranked by objective value (lower = better)
- Allows users to choose between multiple high-quality options
- Essential for real-world scenarios with subjective preferences

## 🔧 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/schedule` | POST | Generate top-k solutions |
| `/validate-request` | POST | Validate without solving |
| `/objective-weights-defaults` | GET | Get default weights |
| `/health` | GET | Health check |
| `/config/algorithm` | GET | Algorithm info |

## 📊 Data Models

### Worker
```python
Worker(
    id=1,
    name="Alice Johnson",
    seniority_level=3,              # 0=junior, higher=senior
    skills=[Skill(...), ...],       # With proficiency levels
    hourly_rate=28.0,
    preferences=WorkerPreference(
        max_shifts_per_week=5,
        no_consecutive_shifts=True,
        unavailable_dates=set(),
        prefer_weekends=False,
    )
)
```

### Shift
```python
Shift(
    id=1,
    date="2026-04-01",
    start_time="08:00",
    end_time="16:00",
    shift_type="morning",
    required_skills=[Skill(...), ...],
    workers_required=2,
    is_weekend=False,
)
```

### ObjectiveWeights (UI-Configurable)
```python
ObjectiveWeights(
    respect_time_off_requests=10.0,
    reward_seniority=5.0,
    balance_weekend_shifts=8.0,
    minimize_overstaffing=3.0,
    reward_skill_matching=7.0,
    balance_workload=6.0,
    minimize_compensation=2.0,
)
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Specific test
pytest tests/test_scheduling.py::TestSolver::test_simple_scheduling
```

Tests included:
- Data model validation
- Skill matching
- Request validation
- Solver initialization
- Simple scheduling
- Solution ranking
- Error handling

## 📈 Performance

| Instance Size | Typical Time | Quality |
|---|---|---|
| Small (≤20W, ≤50S) | <1s | Optimal |
| Medium (20-50W, 50-200S) | 5-30s | Near-optimal |
| Large (50+W, 200+S) | 30-60s | Feasible |

W = workers, S = shifts

## 🛠️ Development

### Code Style
- PEP 8 with 100-char line limit
- Full type hints throughout
- English-only comments (prevents RTL issues in IDE)
- Black code formatter
- Pytest for testing

### Formatting
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## 🔐 Key Design Principles

1. **Separation of Concerns**: Each module has single responsibility
2. **Type Safety**: Pydantic validation + full type hints
3. **Extensibility**: Easy to add constraints/objectives
4. **Performance**: Efficient constraint representation
5. **Modularity**: Independent, composable components
6. **Documentation**: Comprehensive docstrings and guides

## 🚀 Extensibility

### Add New Hard Constraint
1. Create method in `HardConstraintHandler`
2. Call from `apply_all_hard_constraints()`
3. No changes to other modules

### Add New Soft Constraint Term
1. Create method in `DynamicObjectiveFunction`
2. Call from `build_objective_function()`
3. Add weight field to `ObjectiveWeights`
4. Update documentation

### Add New API Endpoint
1. Create route in `src/api/main.py`
2. Use Pydantic models for validation
3. Leverage existing solver infrastructure

## 📚 Documentation Structure

- **README.md**: User guide, API reference, data model docs
- **ARCHITECTURE.md**: System design, constraint formulation, extensibility patterns
- **QUICKSTART.md**: Installation, running server, basic examples
- **examples.py**: 4 detailed usage scenarios demonstrating key features
- **pyproject.toml**: Dependencies and project metadata

## 🎯 Requirements Met

✅ Accept dynamic worker/shift inputs with validation
✅ Implement hard constraints (no consecutive, max per week, skill requirements)
✅ Dynamic soft constraints with UI-driven JSON weights
✅ Top-k solutions (5 by default, configurable)
✅ Clean, modular Python code
✅ All comments in English (no RTL rendering issues)
✅ Professional OR-Tools CP-SAT integration
✅ Production-ready architecture with tests
✅ Comprehensive documentation

## 🔄 Workflow

1. **Create request** with workers, shifts, period
2. **Set objective weights** (optional - defaults available)
3. **Call solver** with top_k and timeout parameters
4. **Receive top-k solutions** ranked by quality
5. **Choose preferred solution** for implementation

## 📦 Dependencies

- `ortools>=9.8.0`: Constraint programming solver
- `pydantic>=2.0.0`: Data validation
- `fastapi>=0.104.0`: REST API framework
- `uvicorn>=0.24.0`: ASGI server
- `numpy>=1.24.0`: Numerical computing
- `pandas>=2.0.0`: Data manipulation

Development:
- `pytest>=7.4.0`: Testing framework
- `black>=23.10.0`: Code formatter
- `mypy>=1.6.0`: Type checker
- And more (see requirements-dev.txt)

## 🎓 Learning Resources

- **Google OR-Tools**: https://developers.google.com/optimization
- **Pydantic**: https://docs.pydantic.dev
- **FastAPI**: https://fastapi.tiangolo.com
- **Constraint Programming**: See ARCHITECTURE.md

## 🔗 File Organization

```
shift-scheduler/
├── src/
│   ├── models/data_models.py         # Pydantic models
│   ├── constraints/hard_constraints.py # Hard constraints
│   ├── objectives/dynamic_objectives.py # Soft constraints
│   ├── solver/core_solver.py         # Main solving engine
│   └── api/main.py                   # REST API
├── tests/
│   └── test_scheduling.py            # Unit tests
├── main.py                           # Entry point
├── config.py                         # Configuration
├── examples.py                       # Usage examples
├── README.md                         # Full documentation
├── ARCHITECTURE.md                   # System design
├── QUICKSTART.md                     # Quick start guide
├── pyproject.toml                    # Project metadata
├── requirements.txt                  # Dependencies
└── requirements-dev.txt              # Dev dependencies
```

## 💡 Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Start API: `python main.py`
3. Visit http://localhost:8000/docs for interactive API
4. Read ARCHITECTURE.md for system details
5. Run examples.py to see usage patterns
6. Run tests: `pytest tests/`
7. Extend with your own constraints/objectives

---

**Status**: Production-ready initial implementation
**Language**: Python 3.9+
**License**: MIT (modify as needed)
**Author**: Backend Development Team
