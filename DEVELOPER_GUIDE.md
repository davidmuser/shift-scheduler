# Shift Scheduler – Developer Guide

This guide is for developers who want to understand, extend, or integrate the
shift scheduling system. It consolidates the existing README, INSTALLATION,
QUICKSTART, and web-interface docs into one technical reference.

---

## 1. Overview

The project provides two main ways to interact with the scheduler:

1. **Python / FastAPI backend** – OR-Tools CP-SAT solver with Pydantic models and
   a REST API.
2. **Flask web interface (`web_interface.py`)** – Non-coder-friendly UI for
   managers and workers with business scoping, interest collection, schedule
   generation, editing, and publish/lock features.

Core technologies:

- Python 3.9+
- Google OR-Tools CP-SAT
- Pydantic models
- FastAPI (API backend in `src/api`)
- Flask (web interface in `web_interface.py`)
- SQLAlchemy (for the web interface DB)

---

## 2. Installation & Environment

From the project root:

```bash
cd shift-scheduler
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

pip install -r requirements.txt
# Optional dev tools
pip install -r requirements-dev.txt
```

Verify core libraries:

```bash
python -c "import ortools, pydantic, fastapi; print('✓ All imports successful')"
```

Environment configuration:

- Copy `.env.example` to `.env` and adjust values as needed.
- Configuration is loaded by `config.py` and/or individual apps.

Example `.env` fragment:

```env
API_PORT=8000
DEFAULT_TIMEOUT_SECONDS=60
DEFAULT_TOP_K_SOLUTIONS=5
WEIGHT_SENIORITY=5.0
```

---

## 3. Project Structure

High-level layout:

```text
shift-scheduler/
├── src/
│   ├── models/
│   │   └── data_models.py
│   ├── constraints/
│   │   └── hard_constraints.py
│   ├── objectives/
│   │   └── dynamic_objectives.py
│   ├── solver/
│   │   └── core_solver.py
│   └── api/
│       └── main.py
├── web_interface.py
├── templates/
│   ├── index.html
│   ├── setup.html
│   ├── schedule.html
│   └── worker_availability.html
├── static/
│   ├── style.css
│   ├── setup.js
│   └── schedule.js
├── tests/
│   └── test_scheduling.py
├── README.md
├── INSTALLATION.md
├── QUICKSTART.md
├── ARCHITECTURE.md
└── USER_GUIDE.md / DEVELOPER_GUIDE.md
```

Key components:

- `src/models/data_models.py` – Pydantic models for `Worker`, `Shift`,
  `WorkerPreference`, `SchedulingRequest`, `ObjectiveWeights`,
  `SchedulingSolution`, etc.
- `src/constraints/hard_constraints.py` – All hard (non-negotiable)
  constraints such as coverage, max shifts per week, availability, skills.
- `src/objectives/dynamic_objectives.py` – Builds the OR-Tools objective from
  dynamic, weighted soft constraints, including workload balance.
- `src/solver/core_solver.py` – Core CP-SAT model creation, constraints,
  objective, and a top-k solution routine using iterative no-good constraints.
- `web_interface.py` – Flask app, SQLAlchemy models, business scoping,
  worker/shift CRUD, shift interest, scheduling, publish/lock, and
  availability endpoints.

---

## 4. Running the Backends

### 4.1 FastAPI backend (library-style API)

From the repo root:

```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

You then get:

- API root: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Endpoints (FastAPI version) include:

- `POST /schedule` – generate top-k solutions
- `POST /validate-request` – validate a scheduling request
- `GET /objective-weights-defaults` – default soft constraint weights
- `GET /health` – health check
- `GET /config/algorithm` – algorithm metadata

### 4.2 Flask web interface

For the “no-code” web UI:

```bash
python web_interface.py
```

This starts a Flask server (default on `http://localhost:5000`) with:

- `/` – home / stats
- `/setup` – workers + shifts management
- `/schedule` – schedule generation UI
- `/availability` – worker availability calendar
- `/join/<business_number>` – business join flow

And numerous JSON APIs under `/api/...` (documented below).

---

## 5. Core Solver (OR-Tools CP-SAT)

### 5.1 Data models

Pydantic models in `src/models/data_models.py` define the in-memory contract
between the database/web layer and the solver.

Key structures:

- `Worker` – id, name, seniority, skills, hourly_rate, preferences.
- `Shift` – id, date, start_time, end_time, required_skills,
  workers_required, is_weekend.
- `WorkerPreference` – unavailable_dates, max_shifts_per_week, flags such as
  no_consecutive_shifts.
- `ObjectiveWeights` – UI-configurable floats for:
  - time-off requests
  - seniority
  - weekend balance
  - skill matching
  - workload balance
  - compensation minimization
  - overstaffing penalty
- `SchedulingRequest` – workers, shifts, period start/end, optional metadata
  (e.g. allowed worker–shift pairs based on interest).
- `SchedulingResponse` / `SchedulingSolution` / `ScheduleAssignment` – solver
  output.

### 5.2 Hard constraints

Implemented in `HardConstraintHandler`:

- Shift coverage: each shift must have exactly the required number of
  assigned workers.
- No consecutive shifts: workers cannot work incompatible back-to-back shifts.
- Max shifts per week: per-worker weekly cap.
- Availability: workers cannot be assigned on dates they are unavailable.
- Skills: worker skills must satisfy required skills for the shift.

### 5.3 Objective function

Implemented in `DynamicObjectiveFunction`:

- Time-off requests: penalize assigning workers on their unavailable dates.
- Seniority rewards: prefer assigning more senior workers to desirable shifts.
- Weekend balance: penalize uneven weekend assignments.
- Skill matching: reward good skill–shift matches.
- Workload balance: create per-worker workload variables and penalize the
  range (max – min) across workers.
- Compensation minimization: encourage cheaper assignments where possible.
- Overstaffing penalty: discourage more staff than required.

All terms are weighted by `ObjectiveWeights` from the UI.

### 5.4 Top-k solutions

`ShiftSchedulingSolver` in `src/solver/core_solver.py`:

- Builds a CP-SAT model once.
- Solves repeatedly (up to `top_k` times) with a **no-good constraint** added
  after each solution: in the next iteration at least one assignment decision
  must flip, so you get distinct schedules.
- Collects solutions and wraps them into `SchedulingResponse`.

You can also see a generic `TopKSolutionCollector` class as an alternative
callback-based collector.

Usage example (library):

```python
from src.models.data_models import Worker, Shift, SchedulingRequest, ObjectiveWeights
from src.solver.core_solver import ShiftSchedulingSolver

request = SchedulingRequest(...)
weights = ObjectiveWeights(...)
solver = ShiftSchedulingSolver(timeout_seconds=60, top_k=5)
response = solver.solve(request, weights)
```

---

## 6. Flask Web Interface Architecture

### 6.1 SQLAlchemy models (in `web_interface.py`)

- `BusinessModel` – businesses, each with a unique join number.
- `UserModel` – login identity, with a `worker_id` foreign key (for worker
  logins) and `business_id`.
- `WorkerModel` – workers scoped to a business, including skills and
  availability JSON blobs.
- `ShiftModel` – shifts, including recurring weekly options and JSON fields
  for weekdays and required skills.
- `ShiftInterestModel` – relations between workers and shifts ("I’m
  interested").
- `PublishedScheduleModel` – stores a **published** schedule per business:
  - `business_id`
  - `period_start`, `period_end`
  - `is_locked`
  - `created_at`, `created_by_user_id`
  - `solution_rank`, `objective_value`
  - `assignments_json` – the final assignments (with edited worker_id/name and
    unresolved markers)
  - `unresolved_comments_json` – per-shift unresolved comments

### 6.2 Session & business scoping

Helpers:

- `_get_business_id()` – read current business from session, enforcing that all
  operations are scoped.
- `_get_worker_id()` / `_require_worker()` – resolve the current worker using
  `UserModel.worker_id`, name matches, and session caching; used by
  worker-facing endpoints.
- `_require_role(role)` – enforce `Manager` vs `Worker` permissions.

### 6.3 Web routes

Key routes:

- `GET /` – index, high-level stats; optionally generates a default
  `index.html` if missing.
- `GET /setup` – setup UI for workers and shifts.
- `GET /schedule` – schedule generation UI.
- `GET /availability` – worker availability calendar UI.
- `GET /join/<business_number>` / `POST /join/<business_number>` – join flow.

### 6.4 JSON APIs

Workers:

- `GET /api/workers` – list workers for current business.
- `POST /api/workers` – create worker (also creates a matching `UserModel`).
- `GET /api/workers/<worker_id>` – get a worker.
- `PUT /api/workers/<worker_id>` – update.
- `DELETE /api/workers/<worker_id>` – delete.

Shifts:

- `GET /api/shifts` – list shifts.
- `POST /api/shifts` – create shift (supports recurring weekly via
  `recurring_weekly` + `weekdays`).
- `DELETE /api/shifts/<shift_id>` – delete.
- `PUT /api/shifts/<shift_id>/status` – open/close a shift for scheduling.

Interests & availability:

- `GET /api/shift-interests` – manager view of interests by shift.
- `GET /api/shift-interests/me` – worker’s own interested shift IDs.
- `POST /api/shifts/<shift_id>/interest` – express interest (legacy per-shift).
- `DELETE /api/shifts/<shift_id>/interest` – withdraw interest.
- `POST /api/shifts/interest` – unified handler to add/remove interest with
  `{shift_id, interested}`.
- `GET /api/shifts/availability` – weekly view of upcoming shifts for the
  current business plus the worker’s current interests and lock metadata.

Scheduling:

- `POST /api/schedule` – run solver for the current business, building
  `SchedulingRequest` + `ObjectiveWeights` and returning top-k solutions,
  workers, and `interested_by_shift` map.

Publishing and lock:

- `POST /api/schedule/publish` – accept a fully edited solution from the UI,
  infer period, **replace** any existing published schedule for that
  business, set `is_locked=True`, and store assignments + unresolved
  comments.
- `GET /api/published-schedule` – return the latest published schedule and the
  `current_worker_id` for worker-centric views.

Lock enforcement:

- Interests and availability changes for shifts **within** a published locked
  period are rejected (HTTP 403) with a clear message.
- `GET /api/shifts/availability` marks each shift with `is_locked` and returns
  top-level `is_locked`, `locked_period_start`, `locked_period_end`.

Other:

- `GET /api/default-weights` – default slider weights for the web UI.
- `GET /api/stats` – business stats (workers, shifts, interests).
- `POST /api/clear-all` – delete workers, shifts, and interests for the
  current business.

---

## 7. Frontend (templates + JS)

### 7.1 Templates

- `templates/index.html` – landing page and navigation.
- `templates/setup.html` – worker and shift CRUD forms.
- `templates/schedule.html` – top-k schedule generation UI, editing controls,
  CSV export, and publish button.
- `templates/worker_availability.html` – weekly calendar for workers and a
  **Published Schedule** section that shows either the current worker’s
  assigned shifts or, for managers, all workers and their shifts.

### 7.2 JavaScript

`static/setup.js`:

- Handles AJAX calls to worker and shift APIs from the setup page.

`static/schedule.js`:

- Manages sliders and form submission to `/api/schedule`.
- Maintains `LAST_SOLUTIONS`, `SELECTED_SOLUTION_INDEX`, `EDIT_MODE`,
  `ALL_WORKERS`, and `INTERESTED_BY_SHIFT`.
- Renders per-solution details grouped by date and a weekly Gantt chart.
- Editing logic:
  - Clickable status pill toggles assigned/unassigned per assignment.
  - Dropdown per shift lets managers reassign to a different worker or mark
    as unresolved with optional comments.
  - `handleWorkerSelectChange` updates the **underlying assignment object**
    (worker_id and worker_name) so publishing and CSV exports reflect the
    new worker.
- "Publish Selected Schedule" button posts the edited solution to
  `/api/schedule/publish` with assignments and unresolved comments.

`worker_availability.html` inline script:

- Fetches weekly availability (`/api/shifts/availability`) and
  `/api/published-schedule` in parallel.
- Renders day columns and checkboxes for interest.
- Shows lock notices and disables checkboxes for locked shifts.
- Renders a **Published Schedule** section:
  - For workers: only their own assigned shifts for the published period.
  - For managers/others: all workers and their assigned shifts, grouped by
    worker.

---

## 8. Testing & Quality

### 8.1 Tests

- Main tests live in `tests/test_scheduling.py`.

Run tests:

```bash
pytest tests/
# or with coverage
pytest --cov=src tests/
```

### 8.2 Linting & formatting

If you installed `requirements-dev.txt`:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

---

## 9. Extending the System

### 9.1 New hard constraints

1. Add logic in `HardConstraintHandler` (e.g. a new method) and wire it into
   `apply_all_hard_constraints`.
2. If constraints need additional data, extend the Pydantic models accordingly.

### 9.2 New objective terms

1. Add fields to `ObjectiveWeights`.
2. Update `DynamicObjectiveFunction.build_objective_function` to create the
   corresponding OR-Tools expressions with those weights.
3. Expose sliders/inputs in the web UI or API.

### 9.3 New web features

- Add SQLAlchemy fields and run lightweight migrations via the
  `_ensure_column` helper in `web_interface.py`.
- Add/modify Flask routes for new APIs.
- Update templates and JS to call new endpoints.

### 9.4 Deploying to production

General guidance:

- Run Flask / FastAPI behind a real WSGI/ASGI server (Gunicorn/Uvicorn) and a
  reverse proxy (Nginx) with HTTPS.
- Use a real database (e.g. PostgreSQL) instead of purely in-memory storage.
- Set secure secrets and disable debug.
- Add authentication and access control as needed.

---

## 10. Troubleshooting

Common issues and quick checks:

- **ImportError (ortools/pydantic/fastapi/flask)** – make sure the virtual
  environment is active and dependencies from `requirements.txt` are
  installed.
- **Port in use** – change the port in `.env`, `main.py`, or `web_interface.py`
  and restart, or free the port using OS tools.
- **No valid schedule** – verify that for each shift there is at least one
  available, appropriately skilled worker; check max shifts per week and
  availability.
- **Workers cannot change availability** – confirm a published schedule is not
  locking the relevant date range; if it is, this is expected behavior.

This guide should give you enough structure to confidently extend or integrate
with the shift scheduler, while the `USER_GUIDE.md` focuses on the
non-technical, day-to-day usage.
