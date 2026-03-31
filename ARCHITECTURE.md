# Architecture Documentation

## System Overview

The Shift Scheduling Backend is a production-ready system designed to solve the Nurse Scheduling Problem (generalized to any worker scheduling scenario) using Google OR-Tools CP-SAT solver.

### Key Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Modularity**: Easy to extend with new constraints or objectives
3. **Type Safety**: Full type hints and Pydantic validation
4. **Performance**: Efficient constraint representation and solver configuration
5. **Scalability**: Handles problems from small (20 workers) to large (100+ workers) instances

## Module Structure

### 1. Data Models (`src/models/data_models.py`)

**Responsibility**: Define all data structures using Pydantic for validation.

**Key Classes**:
- `Worker`: Represents a worker with skills, seniority, and preferences
- `Shift`: Represents a shift with time, skills, and staffing requirements
- `WorkerPreference`: Worker-specific constraints and preferences
- `Skill`: Skill definition with proficiency levels
- `SchedulingRequest`: Complete problem specification
- `ObjectiveWeights`: Dynamic weights for soft constraints
- `SchedulingSolution`: Single solution with assignments and metrics
- `SchedulingResponse`: Top-k solutions container

**Design Rationale**:
- Pydantic provides automatic validation and serialization
- Enums for fixed-value fields (SkillLevel)
- Field validators catch common errors early
- Clear separation between hard constraint data (WorkerPreference) and soft constraint data (ObjectiveWeights)

### 2. Hard Constraints (`src/constraints/hard_constraints.py`)

**Responsibility**: Enforce non-negotiable scheduling rules.

**Key Constraints**:
1. **Shift Coverage**: Each shift covered by exactly required workers
2. **No Consecutive Shifts**: Workers cannot work back-to-back shifts (if configured)
3. **Max Shifts Per Week**: Respect weekly shift limits per worker
4. **Worker Availability**: Don't assign on unavailable dates
5. **Skill Requirements**: Ensure required skills are present per shift

**Design Pattern**:
- `HardConstraintHandler` class encapsulates all constraint logic
- Each constraint type in its own method for clarity
- Helper methods (`_are_consecutive`, `_get_iso_week_number`) for reusability
- Constraint counter for debugging and monitoring

**Key Implementation Details**:
- Uses ISO week numbers for consistent week definition
- Skill validation leverages `Worker.has_skill()` method
- Binary variables (0/1) for assignment decisions simplify constraint formulation

### 3. Dynamic Objectives (`src/objectives/dynamic_objectives.py`)

**Responsibility**: Build weighted objective function with soft constraints.

**Soft Constraint Terms** (all optional, UI-configurable):
1. **Time-Off Requests**: Penalize assignments on unavailable dates
2. **Seniority Rewards**: Reward assigning senior workers
3. **Weekend Balance**: Minimize imbalance in weekend assignments
4. **Skill Matching**: Reward assigning workers with required skills
5. **Workload Balance**: Minimize difference in total hours per worker
6. **Compensation Minimization**: Prefer lower-cost workers when possible
7. **Overstaffing Penalty**: Penalize assigning more than required workers

**Design Pattern**:
- `DynamicObjectiveFunction` class manages objective building
- Each soft constraint in its own method
- Weights come from `ObjectiveWeights` model
- Supports zero weight to disable specific criteria

**Key Implementation Details**:
- All terms are additive to minimize total cost
- Seniority and skill matching use negative weights (rewards = negative costs)
- Workload balance computed using shift duration in hours
- Flexible term accumulation allows easy addition of new criteria

### 4. Core Solver (`src/solver/core_solver.py`)

**Responsibility**: Orchestrate model creation, constraint addition, solving, and solution collection.

**Key Components**:

#### `TopKSolutionCollector`
- Custom callback implementing `CpSolverSolutionCallback`
- Invoked each time solver finds a new solution
- Maintains top-k solutions by objective value
- Preserves solution details (assignments, objective value, timestamp)

**Design Rationale**:
- Callback pattern allows interception of solver progress
- Efficient k-maintenance: keep solutions sorted, trim to size
- Timestamp enables performance analysis

#### `ShiftSchedulingSolver`
- Orchestrates the complete solving process
- Manages model lifecycle (creation → constraints → objective → solve)
- Validates input data before solving
- Builds formatted response from raw solver output

**Solving Pipeline**:
1. `solve()`: Main entry point
2. `_validate_request()`: Check for invalid data
3. `_create_model()`: Initialize CP-SAT model
4. `_create_variables()`: Create assignment variables
5. `_add_constraints()`: Apply hard constraints
6. `_set_objective()`: Build dynamic objective function
7. `_solve_and_collect_top_k()`: Execute solver with callback
8. `_build_response()`: Format solutions for output

### 5. REST API (`src/api/main.py`)

**Responsibility**: Provide HTTP endpoints for scheduling and configuration.

**Key Endpoints**:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/schedule` | Generate top-k scheduling solutions |
| GET | `/objective-weights-defaults` | Get default objective weights |
| POST | `/validate-request` | Validate request without solving |
| GET | `/health` | Health check |
| GET | `/config/algorithm` | Algorithm information |

**Design Pattern**:
- FastAPI with Pydantic validation
- Type-hinted route handlers for IDE support
- Comprehensive error handling with descriptive messages
- Optional parameters for solver tuning (top_k, timeout_seconds)

**Request/Response Flow**:
```
HTTP Request → Pydantic Validation → ShiftSchedulingSolver.solve()
→ Constraint/Objective Building → CP-SAT Solver → Solution Collection
→ Response Building → JSON Serialization → HTTP Response
```

## Data Flow Diagram

```
User/UI
  ↓
HTTP Request (SchedulingRequest + ObjectiveWeights)
  ↓
FastAPI Route (/schedule)
  ↓
ShiftSchedulingSolver.solve()
  ├─ Validate Request
  ├─ Create CP-SAT Model
  ├─ Create Variables (worker × shift binary variables)
  ├─ Apply Hard Constraints
  │  ├─ Shift Coverage Constraints
  │  ├─ No Consecutive Shifts Constraints
  │  ├─ Max Shifts Per Week Constraints
  │  ├─ Worker Availability Constraints
  │  └─ Skill Requirement Constraints
  ├─ Build Dynamic Objective Function
  │  ├─ Time-Off Request Term
  │  ├─ Seniority Reward Term
  │  ├─ Weekend Balance Term
  │  ├─ Skill Matching Term
  │  ├─ Workload Balance Term
  │  ├─ Compensation Minimization Term
  │  └─ Overstaffing Penalty Term
  ├─ Execute Solver with TopKSolutionCollector
  └─ Build Response from Collected Solutions
  ↓
SchedulingResponse (top-k solutions)
  ↓
JSON Serialization
  ↓
HTTP Response
  ↓
User/UI
```

## Constraint Model Formulation

### Decision Variables

For each worker i and shift j:
- `x[i,j] ∈ {0, 1}`: 1 if worker i is assigned to shift j, 0 otherwise

For each shift j:
- `coverage[j] ∈ ℤ⁺`: Number of workers assigned to shift j

### Hard Constraints

**Shift Coverage**:
- For each shift j: `Σ(x[i,j] for all i) = coverage[j] = required[j]`

**No Consecutive Shifts** (if enabled):
- For each worker i and consecutive shifts (j1, j2): `x[i,j1] + x[i,j2] ≤ 1`

**Max Shifts Per Week**:
- For each worker i and week w: `Σ(x[i,j] for j in week w) ≤ max[i]`

**Worker Availability**:
- For each worker i and unavailable date d: `x[i,j] = 0` for all j on date d

**Skill Requirements**:
- For each shift j with required skill s: `Σ(x[i,j] for capable i) ≥ 1`

### Soft Constraints (Objective Function)

**Minimize**: `Σ (weight[k] × cost[k])` where cost[k] are soft constraint terms

Each term k has configurable weight w[k] from ObjectiveWeights.

## Performance Characteristics

### Time Complexity
- **Model Creation**: O(W × S) where W = workers, S = shifts
- **Constraint Addition**: O(W × S) for most constraints, O(S) for skill constraints
- **Solving**: NP-hard problem; solver timeout controls runtime

### Space Complexity
- **Variables**: O(W × S) binary variables
- **Constraints**: O(W × S) individual constraints
- **Memory**: Typically < 500MB for instances up to 100 workers, 500 shifts

### Solver Performance (typical)
- **Small instances** (≤20W, ≤50S): <1 second to optimality
- **Medium instances** (20-50W, 50-200S): 5-30 seconds
- **Large instances** (50+W, 200+S): 30-60 seconds (may not reach optimality)

## Extensibility Points

### Adding New Constraint Types

1. Create new method in `HardConstraintHandler`:
```python
def _add_new_constraint(self, request, assignments):
    # Implementation
    self.constraint_count += 1
```

2. Call from `apply_all_hard_constraints()`:
```python
self._add_new_constraint(request, assignments)
```

### Adding New Soft Constraint Terms

1. Create new method in `DynamicObjectiveFunction`:
```python
def _add_new_term(self, request, assignments):
    # Calculate costs and add to objective_terms
    self.objective_terms.append((term_var, weight))
    self.total_weight += weight
```

2. Call from `build_objective_function()`:
```python
self._add_new_term(request, assignments)
```

3. Add weight field to `ObjectiveWeights`:
```python
new_criterion: float = Field(default=1.0)
```

4. Update API documentation

### Adding New API Endpoints

1. Create route handler in `src/api/main.py`:
```python
@app.post("/new-endpoint", response_model=ResponseModel)
async def new_endpoint(request: RequestModel) -> ResponseModel:
    # Implementation
    pass
```

2. Use Pydantic models for automatic validation
3. Return appropriate HTTP status codes

## Testing Strategy

### Unit Tests (`tests/test_scheduling.py`)

1. **Data Model Tests**:
   - Worker creation and skill matching
   - Shift duration calculation
   - Request validation

2. **Objective Weights Tests**:
   - Default and custom weights
   - Weight validation (non-negative)

3. **Solver Tests**:
   - Initialization and configuration
   - Solution ranking and ordering
   - Error handling for invalid requests

### Integration Tests

- End-to-end scheduling for sample problems
- Solution feasibility verification
- Performance benchmarking

### Testing Approach

- Pytest framework for structure
- Fixtures for reusable test data
- Parametrized tests for multiple scenarios

## Error Handling Strategy

1. **Input Validation** (Pydantic):
   - Type checking
   - Field validators
   - Constraint checking

2. **Logical Validation** (ShiftSchedulingSolver):
   - Duplicate ID detection
   - Empty collections checking
   - Impossible constraint detection

3. **Runtime Errors** (try-catch):
   - Solver exceptions
   - API exceptions

4. **User Feedback**:
   - Clear error messages
   - HTTP status codes
   - Detailed validation reports

## Configuration Management

- Environment-based configuration via `config.py`
- Sensible defaults for all solver parameters
- `.env` file for local overrides
- Type-safe configuration access

## Code Quality Standards

- **Style**: PEP 8 with 100-character line limit
- **Type Hints**: Full type annotations throughout
- **Docstrings**: Google-style docstrings for all public APIs
- **Comments**: English-only to prevent RTL rendering issues
- **Testing**: Unit tests with pytest
- **Linting**: Flake8, mypy, ruff
- **Formatting**: Black code formatter

## Security Considerations

- Input validation via Pydantic
- No SQL injection (no database queries)
- Worker timeout prevents infinite loops
- Error messages don't expose system details
- CORS can be added for frontend integration

## Future Enhancement Opportunities

1. **Persistence**: Add database layer for solution history
2. **Visualization**: Generate Gantt charts or calendar views
3. **Advanced Callbacks**: More granular progress reporting
4. **Hybrid Solving**: Combine CP-SAT with metaheuristics
5. **Batch API**: Process multiple scheduling requests in parallel
6. **WebSocket Support**: Real-time solver progress updates
7. **Constraint Learning**: Learn worker preferences over time
