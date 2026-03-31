# Quick Start Guide

## Installation

### 1. Navigate to Project Directory
```bash
cd shift-scheduler
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

## Running the System

### Option 1: Start REST API Server
```bash
python main.py
```

Then access:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Option 2: Use as Python Library
```python
from src.models.data_models import Worker, Shift, SchedulingRequest, ObjectiveWeights
from src.solver.core_solver import ShiftSchedulingSolver

# Create workers, shifts, request
# ...

solver = ShiftSchedulingSolver(timeout_seconds=60, top_k=5)
response = solver.solve(request, ObjectiveWeights())

for solution in response.solutions:
    print(f"Solution {solution.solution_rank}: {solution.objective_value}")
```

## Running Tests
```bash
pytest tests/
pytest --cov=src tests/  # With coverage
```

## Example Scenario

See README.md for complete example with:
- Worker creation with skills and preferences
- Shift definition with requirements
- Scheduling request setup
- Top-k solution handling

## API Quick Reference

### Schedule Generation
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

### Request Validation
```bash
curl -X POST "http://localhost:8000/validate-request" \
  -H "Content-Type: application/json" \
  -d '{
    "workers": [...],
    "shifts": [...],
    "scheduling_period_start": "2026-04-01",
    "scheduling_period_end": "2026-04-30"
  }'
```

### Get Default Weights
```bash
curl "http://localhost:8000/objective-weights-defaults"
```

## Key Files

- `main.py`: API server entry point
- `src/models/data_models.py`: All data structures
- `src/constraints/hard_constraints.py`: Constraint enforcement
- `src/objectives/dynamic_objectives.py`: Weighted objective function
- `src/solver/core_solver.py`: Main solving engine
- `src/api/main.py`: REST endpoints
- `README.md`: Full documentation
- `ARCHITECTURE.md`: System design details

## Configuration

1. Copy `.env.example` to `.env`
2. Modify parameters as needed
3. Environment variables override defaults

Example `.env`:
```
API_PORT=8000
DEFAULT_TIMEOUT_SECONDS=120
WEIGHT_SENIORITY=7.0
```

## Troubleshooting

### ImportError with ortools/pydantic/fastapi
```bash
pip install --upgrade ortools pydantic fastapi uvicorn
```

### Tests not found
```bash
pip install pytest pytest-cov
```

### Port already in use
```bash
python main.py  # Will use :8000 by default
# Or change API_PORT in .env
```

## Next Steps

1. Review ARCHITECTURE.md for system design
2. Examine example tests in tests/test_scheduling.py
3. Try the API with the Quick Start examples above
4. Customize objective weights for your use case
5. Extend with new constraints or soft terms as needed

For detailed documentation, see README.md and ARCHITECTURE.md.
