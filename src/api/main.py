"""
FastAPI application for the shift scheduling backend.

This module provides REST endpoints for scheduling requests and configuration.
All comments are in English to prevent RTL rendering issues.
"""

from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError, BaseModel
from datetime import datetime

from ..models.data_models import (
    SchedulingRequest,
    ObjectiveWeights,
    SchedulingResponse,
    Worker,
    Shift,
)
from ..solver.core_solver import ShiftSchedulingSolver
from uuid import uuid4

from uuid import uuid4



# Pydantic models for request bodies
class CreateWorkerRequest(BaseModel):
    name: str
    business_id: int
    seniority_level: int = 1
    skills: Optional[List[str]] = None
    staff_id: Optional[str] = None
    hourly_rate: Optional[float] = None

class CreateShiftRequest(BaseModel):
    name: str
    business_id: int
    start_time: datetime
    end_time: datetime
    required_workers: int = 1
    required_skills: Optional[List[str]] = None


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title="Shift Scheduling API",
        description="Expert shift scheduling backend using OR-Tools CP-SAT solver",
        version="1.0.0",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Custom exception handler for Pydantic validation errors.
        
        Formats the error into a user-friendly JSON response.
        """
        error_messages = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"] if str(loc) not in ["body", "query"])
            message = error["msg"]
            error_messages.append(f"Validation error in field '{field}': {message}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Your request could not be processed due to invalid data.", "errors": error_messages},
        )

    # In-memory worker and shift template stores for demo (replace with DB in production)
    # Scoped by business_id
    workers_store: Dict[int, List] = {}
    worker_id_counters: Dict[int, int] = {}  # business_id -> next worker id
    shift_templates_store: Dict[int, List] = {}
    from fastapi import Request

    class WorkerModel:
        def __init__(self, business_id, name, seniority_level=1, skills=None, staff_id=None, hourly_rate=None):
            # Assign integer ID unique per business
            if business_id not in worker_id_counters:
                worker_id_counters[business_id] = 1
            self.id = worker_id_counters[business_id]
            worker_id_counters[business_id] += 1
            self.name = name
            self.seniority_level = int(seniority_level) if seniority_level is not None else 1
            if isinstance(skills, str):
                self.skills = [s.strip() for s in skills.split(",") if s.strip()]
            else:
                self.skills = skills or []
            self.staff_id = staff_id
            self.hourly_rate = hourly_rate

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "seniority_level": self.seniority_level,
                "skills": self.skills,
                "staff_id": self.staff_id,
                "hourly_rate": self.hourly_rate,
            }

    class ShiftTemplateModel:
        def __init__(self, name, start_time, end_time, required_workers=1, required_skills=None):
            self.id = str(uuid4())
            self.name = name
            self.start_time = start_time
            self.end_time = end_time
            self.required_workers = required_workers
            self.required_skills = required_skills or []

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "required_workers": self.required_workers,
                "required_skills": self.required_skills,
            }

    @app.get("/api/{business_id}/workers", tags=["Workers"])
    async def list_workers(business_id: int):
        return [w.to_dict() for w in workers_store.get(business_id, [])]

    @app.post("/api/{business_id}/workers", tags=["Workers"])
    async def add_worker(business_id: int, request: Request):
        worker_data = await request.json()
        name = worker_data.get("name")
        if not name:
            return JSONResponse(status_code=400, content={"error": "Name is required"})
        
        w = WorkerModel(
            business_id=business_id,
            name=name,
            seniority_level=worker_data.get("seniority_level", 1),
            skills=worker_data.get("skills"),
            staff_id=worker_data.get("staff_id"),
            hourly_rate=worker_data.get("hourly_rate")
        )
        if business_id not in workers_store:
            workers_store[business_id] = []
        workers_store[business_id].append(w)
        return w.to_dict()

    @app.delete("/api/{business_id}/workers/{worker_id}", tags=["Workers"])
    async def delete_worker(business_id: int, worker_id: str):
        if business_id not in workers_store:
            return JSONResponse(status_code=404, content={"error": "Business not found"})
        for i, w in enumerate(workers_store[business_id]):
            if w.id == worker_id:
                workers_store[business_id].pop(i)
                return {"success": True}
        return JSONResponse(status_code=404, content={"error": "Worker not found"})

    # Shift template endpoints
    @app.get("/api/{business_id}/shift-templates", tags=["Shifts"])
    async def list_shift_templates(business_id: int):
        return [t.to_dict() for t in shift_templates_store.get(business_id, [])]

    @app.post("/api/{business_id}/shift-templates", tags=["Shifts"])
    async def add_shift_template(business_id: int, request: Request):
        data = await request.json()
        name = data.get("name")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if not name or not start_time or not end_time:
            return JSONResponse(status_code=400, content={"error": "Name, start_time, and end_time are required"})
        
        t = ShiftTemplateModel(
            name=name,
            start_time=start_time,
            end_time=end_time,
            required_workers=data.get("required_workers", 1),
            required_skills=data.get("required_skills", [])
        )
        if business_id not in shift_templates_store:
            shift_templates_store[business_id] = []
        shift_templates_store[business_id].append(t)
        return t.to_dict()

    @app.delete("/api/{business_id}/shift-templates", tags=["Shifts"])
    async def delete_all_shift_templates(business_id: int):
        if business_id in shift_templates_store:
            shift_templates_store[business_id] = []
            return {"success": True, "message": "All shift templates for this business have been deleted."}
        return JSONResponse(status_code=404, content={"error": "Business not found or no shifts to delete"})

    @app.delete("/api/{business_id}/shift-templates/{template_id}", tags=["Shifts"])
    async def delete_shift_template(business_id: int, template_id: str):
        if business_id not in shift_templates_store:
            return JSONResponse(status_code=404, content={"error": "Business not found"})
        for i, t in enumerate(shift_templates_store[business_id]):
            if t.id == template_id:
                shift_templates_store[business_id].pop(i)
                return {"success": True}
        return JSONResponse(status_code=404, content={"error": "Template not found"})

    @app.get("/health", tags=["Health Check"])
    async def health_check() -> dict:
        """
        Health check endpoint.
        
        Returns:
            Status of the API
        """
        return {"status": "healthy", "service": "shift-scheduler"}

    @app.post(
        "/schedule/{business_id}",
        response_model=SchedulingResponse,
        tags=["Scheduling"],
        summary="Generate top-k scheduling solutions for a business",
    )
    async def generate_schedule(
        business_id: int,
        request: SchedulingRequest,
        objective_weights: Optional[ObjectiveWeights] = None,
        top_k: int = 5,
        timeout_seconds: float = 60.0,
    ) -> SchedulingResponse:
        """
        Generate top-k scheduling solutions for a given request.
        
        This endpoint accepts worker and shift data, along with optional
        objective weights for customizing the optimization criteria. The
        solver will return the top k solutions ranked by their objective value.
        
        Args:
            business_id: The ID of the business for this request
            request: The scheduling request with workers and shifts
            objective_weights: Optional weights for soft constraints (uses defaults if not provided)
            top_k: Number of top solutions to return (default: 5)
            timeout_seconds: Maximum solver runtime (default: 60 seconds)
            
        Returns:
            SchedulingResponse with top-k solutions
            
        Raises:
            HTTPException: If scheduling fails or request is invalid
        """
        try:
            if request.business_id != business_id:
                raise ValueError("Business ID in URL does not match business ID in request body")

            if objective_weights is None:
                objective_weights = ObjectiveWeights()
            
            if top_k < 1 or top_k > 100:
                raise ValueError("top_k must be between 1 and 100")
            
            if timeout_seconds < 1 or timeout_seconds > 600:
                raise ValueError("timeout_seconds must be between 1 and 600")
            
            solver = ShiftSchedulingSolver(
                timeout_seconds=timeout_seconds,
                top_k=top_k,
            )
            
            response = solver.solve(request, objective_weights)
            
            return response
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid request: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Solver error: {str(e)}",
            )

    @app.get(
        "/objective-weights-defaults",
        response_model=ObjectiveWeights,
        tags=["Configuration"],
        summary="Get default objective weights",
    )
    async def get_default_weights() -> ObjectiveWeights:
        """
        Get the default objective weights used by the solver.
        
        These defaults can be overridden in scheduling requests to customize
        optimization behavior.
        
        Returns:
            ObjectiveWeights with default values
        """
        return ObjectiveWeights()

    @app.post(
        "/validate-request",
        tags=["Validation"],
        summary="Validate a scheduling request",
    )
    async def validate_request(request: SchedulingRequest) -> dict:
        """
        Validate a scheduling request without running the solver.
        
        This endpoint checks the request for common errors and provides
        feedback on potential issues.
        
        Args:
            request: The scheduling request to validate
            
        Returns:
            Validation result with any warnings or errors
        """
        try:
            validation_result = {
                "valid": True,
                "warnings": [],
                "workers_count": len(request.workers),
                "shifts_count": len(request.shifts),
            }
            
            total_required_coverage = sum(s.workers_required for s in request.shifts)
            total_workers = len(request.workers)
            
            if total_workers < total_required_coverage:
                validation_result["warnings"].append(
                    f"Not enough workers ({total_workers}) to cover required positions "
                    f"({total_required_coverage})"
                )
            
            for shift in request.shifts:
                if shift.required_skills:
                    capable_workers = [
                        w for w in request.workers
                        for skill in shift.required_skills
                        if w.has_skill(skill.name, skill.level)
                    ]
                    if not capable_workers:
                        validation_result["warnings"].append(
                            f"No workers capable of covering required skills for shift {shift.id}"
                        )
            
            return validation_result
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}",
            )

    @app.get(
        "/config/algorithm",
        tags=["Configuration"],
        summary="Get algorithm configuration",
    )
    async def get_algorithm_config() -> dict:
        """
        Get information about the underlying optimization algorithm.
        
        Returns:
            Dictionary with algorithm details
        """
        return {
            "solver": "Google OR-Tools CP-SAT",
            "algorithm": "Constraint Programming with Satisfiability solving",
            "supports_top_k": True,
            "supports_dynamic_weights": True,
            "description": "Expert-level constraint programming solver for combinatorial optimization",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
