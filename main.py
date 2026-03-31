"""
Main entry point for the shift scheduling API server.

This script starts the FastAPI server for the shift scheduling backend.
All comments are in English to prevent RTL rendering issues.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.api.main import create_app

if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    print("=" * 60)
    print("Shift Scheduling API Server")
    print("=" * 60)
    print("Starting server on http://0.0.0.0:8000")
    print("Documentation available at http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
