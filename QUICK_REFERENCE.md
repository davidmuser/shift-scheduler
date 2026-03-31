# 🚀 Quick Reference Card

## One-Minute Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. View dashboard
./dashboard.sh

# 3. Run system check
./check_backend.sh

# 4. Try interactive CLI
python cli.py

# 5. Start API server
python main.py
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/schedule` | Generate top-k solutions |
| POST | `/validate-request` | Validate request |
| GET | `/objective-weights-defaults` | Get default weights |
| GET | `/health` | Health check |
| GET | `/config/algorithm` | Algorithm info |

**Docs**: http://localhost:8000/docs

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Start API server |
| `cli.py` | Interactive menu |
| `examples.py` | Demo scenarios |
| `dashboard.sh` | System overview |
| `check_backend.sh` | Verify system |

## Data Models

### Worker
```python
Worker(
    id=1,
    name="Alice",
    seniority_level=3,
    skills=[Skill(...), ...],
    hourly_rate=28.0,
    preferences=WorkerPreference(...)
)
```

### Shift
```python
Shift(
    id=1,
    date="2026-04-01",
    start_time="08:00",
    end_time="16:00",
    workers_required=2,
    required_skills=[...],
    is_weekend=False
)
```

### Objective Weights
```python
ObjectiveWeights(
    respect_time_off_requests=10.0,
    reward_seniority=5.0,
    balance_weekend_shifts=8.0,
    # ... 4 more terms
)
```

## Constraints (5 Types)

✓ Shift coverage (exact count)
✓ No consecutive shifts
✓ Max shifts per week
✓ Worker availability
✓ Skill requirements

## Soft Objectives (7 Weighted)

⚖️ Time-off respect (10.0)
⚖️ Seniority reward (5.0)
⚖️ Weekend balance (8.0)
⚖️ Skill matching (7.0)
⚖️ Workload balance (6.0)
⚖️ Cost minimization (2.0)
⚖️ Overstaffing penalty (3.0)

## Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Specific test
pytest tests/test_scheduling.py::TestSolver
```

## Documentation

- `START_HERE.md` - Navigation guide
- `README.md` - Feature guide
- `ARCHITECTURE.md` - System design
- `QUICKSTART.md` - Quick setup
- `INSTALLATION.md` - Installation
- `PROJECT_SUMMARY.md` - Overview

## System Status

✅ **Complete**
✅ **Verified** (10/10 checks pass)
✅ **Ready to use**

---

**Next**: `./dashboard.sh` or `python cli.py`
