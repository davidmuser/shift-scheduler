"""
Example usage and integration tests for the shift scheduling system.

This module demonstrates how to use the scheduling solver with real-world scenarios.
All comments are in English to prevent RTL rendering issues.
"""

import pytest
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


@pytest.fixture
def sample_workers():
    """Create sample workers for testing."""
    return [
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
                prefer_weekends=False,
            ),
        ),
        Worker(
            id=2,
            name="Bob Smith",
            seniority_level=1,
            skills=[Skill(name="General", level=SkillLevel.INTERMEDIATE)],
            hourly_rate=18.0,
            preferences=WorkerPreference(
                worker_id=2,
                max_shifts_per_week=4,
                no_consecutive_shifts=False,
                prefer_weekends=True,
            ),
        ),
        Worker(
            id=3,
            name="Carol Davis",
            seniority_level=2,
            skills=[
                Skill(name="ICU", level=SkillLevel.INTERMEDIATE),
                Skill(name="Pediatrics", level=SkillLevel.BASIC),
            ],
            hourly_rate=22.0,
            preferences=WorkerPreference(
                worker_id=3,
                max_shifts_per_week=5,
                no_consecutive_shifts=True,
                unavailable_dates={"2026-04-05", "2026-04-12"},
            ),
        ),
    ]


@pytest.fixture
def sample_shifts():
    """Create sample shifts for testing."""
    return [
        Shift(
            id=1,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            required_skills=[Skill(name="General", level=SkillLevel.BASIC)],
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=2,
            date="2026-04-01",
            start_time="16:00",
            end_time="00:00",
            shift_type="evening",
            required_skills=[Skill(name="ICU", level=SkillLevel.INTERMEDIATE)],
            workers_required=2,
            is_weekend=False,
        ),
        Shift(
            id=3,
            date="2026-04-04",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            required_skills=[Skill(name="General", level=SkillLevel.BASIC)],
            workers_required=2,
            is_weekend=True,
        ),
        Shift(
            id=4,
            date="2026-04-05",
            start_time="16:00",
            end_time="00:00",
            shift_type="evening",
            required_skills=[],
            workers_required=1,
            is_weekend=False,
        ),
    ]


class TestDataModels:
    """Tests for data model validation."""

    def test_worker_creation(self):
        """Test creating a worker."""
        worker = Worker(
            id=1,
            name="Test Worker",
            seniority_level=2,
            skills=[],
            hourly_rate=20.0,
            preferences=WorkerPreference(
                worker_id=1,
                max_shifts_per_week=5,
            ),
        )
        assert worker.id == 1
        assert worker.name == "Test Worker"
        assert worker.seniority_level == 2

    def test_shift_creation(self):
        """Test creating a shift."""
        shift = Shift(
            id=1,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            shift_type="morning",
            workers_required=2,
        )
        assert shift.id == 1
        assert shift.date == "2026-04-01"
        assert shift.workers_required == 2

    def test_skill_matching(self):
        """Test worker skill matching."""
        worker = Worker(
            id=1,
            name="Skilled Worker",
            skills=[Skill(name="ICU", level=SkillLevel.ADVANCED)],
            preferences=WorkerPreference(worker_id=1),
        )
        
        assert worker.has_skill("ICU", SkillLevel.BASIC)
        assert worker.has_skill("ICU", SkillLevel.ADVANCED)
        assert not worker.has_skill("ICU", SkillLevel.EXPERT)
        assert not worker.has_skill("Pediatrics")

    def test_shift_duration_calculation(self):
        """Test shift duration calculation."""
        shift = Shift(
            id=1,
            date="2026-04-01",
            start_time="08:00",
            end_time="16:00",
            workers_required=1,
        )
        duration = shift.get_shift_duration_hours()
        assert duration == 8.0

    def test_shift_duration_overnight(self):
        """Test overnight shift duration."""
        shift = Shift(
            id=1,
            date="2026-04-01",
            start_time="20:00",
            end_time="08:00",
            workers_required=1,
        )
        duration = shift.get_shift_duration_hours()
        assert duration == 12.0


class TestSchedulingRequest:
    """Tests for scheduling request validation."""

    def test_duplicate_worker_ids(self, sample_workers):
        """Test validation of duplicate worker IDs."""
        sample_workers[1].id = sample_workers[0].id
        
        with pytest.raises(ValueError, match="Duplicate worker IDs"):
            SchedulingRequest(
                workers=sample_workers,
                shifts=[],
                scheduling_period_start="2026-04-01",
                scheduling_period_end="2026-04-30",
            )

    def test_valid_request(self, sample_workers, sample_shifts):
        """Test creating a valid scheduling request."""
        request = SchedulingRequest(
            workers=sample_workers,
            shifts=sample_shifts,
            scheduling_period_start="2026-04-01",
            scheduling_period_end="2026-04-30",
        )
        
        assert len(request.workers) == 3
        assert len(request.shifts) == 4


class TestObjectiveWeights:
    """Tests for objective weights."""

    def test_default_weights(self):
        """Test default objective weights."""
        weights = ObjectiveWeights()
        
        assert weights.respect_time_off_requests == 10.0
        assert weights.reward_seniority == 5.0
        assert weights.balance_weekend_shifts == 8.0

    def test_custom_weights(self):
        """Test custom objective weights."""
        weights = ObjectiveWeights(
            respect_time_off_requests=20.0,
            reward_seniority=2.0,
        )
        
        assert weights.respect_time_off_requests == 20.0
        assert weights.reward_seniority == 2.0
        assert weights.balance_weekend_shifts == 8.0

    def test_negative_weight_validation(self):
        """Test that negative weights are rejected."""
        with pytest.raises(ValueError):
            ObjectiveWeights(respect_time_off_requests=-5.0)


class TestSolver:
    """Integration tests for the solver."""

    def test_solver_initialization(self):
        """Test solver initialization."""
        solver = ShiftSchedulingSolver(timeout_seconds=30, top_k=3)
        assert solver.timeout_seconds == 30
        assert solver.top_k == 3

    def test_simple_scheduling(self, sample_workers, sample_shifts):
        """Test solving a simple scheduling problem."""
        request = SchedulingRequest(
            workers=sample_workers,
            shifts=sample_shifts,
            scheduling_period_start="2026-04-01",
            scheduling_period_end="2026-04-30",
        )
        
        solver = ShiftSchedulingSolver(timeout_seconds=10, top_k=2)
        response = solver.solve(request, ObjectiveWeights())
        
        assert response is not None
        assert len(response.solutions) > 0
        assert response.total_computation_time_seconds > 0
        
        best_solution = response.solutions[0]
        assert best_solution.solution_rank == 1

    def test_solution_ranking(self, sample_workers, sample_shifts):
        """Test that solutions are properly ranked."""
        request = SchedulingRequest(
            workers=sample_workers,
            shifts=sample_shifts,
            scheduling_period_start="2026-04-01",
            scheduling_period_end="2026-04-30",
        )
        
        solver = ShiftSchedulingSolver(timeout_seconds=10, top_k=3)
        response = solver.solve(request, ObjectiveWeights())
        
        if len(response.solutions) > 1:
            for i, solution in enumerate(response.solutions):
                assert solution.solution_rank == i + 1

    def test_invalid_request_handling(self):
        """Test error handling for invalid requests."""
        request = SchedulingRequest(
            workers=[],
            shifts=[],
            scheduling_period_start="2026-04-01",
            scheduling_period_end="2026-04-30",
        )
        
        solver = ShiftSchedulingSolver()
        
        with pytest.raises(ValueError):
            solver.solve(request, ObjectiveWeights())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
