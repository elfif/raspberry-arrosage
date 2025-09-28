#!/usr/bin/env python3
"""
Minimalistic FastAPI for Arrosage System

This API provides endpoints to interact with the watering system mode.
No authentication or HTTPS - simple HTTP endpoints for mode management.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# Add current directory to path to import data modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.mode import get_mode, set_mode, VALID_MODES
from data.status import get_status
from commands.semi_auto import setup_semi_auto_settings
from commands.pause import pause
from commands.resume import resume

# Create FastAPI app
app = FastAPI(
    title="Arrosage API",
    description="Simple API for controlling the watering system",
    version="1.0.0"
)

# Pydantic models for request/response
class ModeResponse(BaseModel):
    current: str
    valid_modes: list[str]

class ModeRequest(BaseModel):
    mode: str

class StatusResponse(BaseModel):
    status: dict | None
    has_active_sequence: bool

class ActionResponse(BaseModel):
    success: bool
    message: str
    current_mode: str | None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Arrosage API",
        "version": "1.0.0",
        "endpoints": {
            "GET /mode": "Get current mode",
            "POST /mode": "Set new mode",
            "GET /status": "Get current sequence status",
            "POST /pause": "Pause the system",
            "POST /resume": "Resume the system"
        }
    }

@app.get("/mode", response_model=ModeResponse)
async def get_current_mode():
    """Get the current system mode."""
    try:
        current_mode = get_mode()
        if current_mode is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve mode from Redis")
        
        return ModeResponse(
            current=current_mode,
            valid_modes=VALID_MODES
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/mode", response_model=ModeResponse)
async def set_current_mode(request: ModeRequest):
    """Set a new system mode."""
    try:
        # Validate the mode
        if request.mode not in VALID_MODES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode '{request.mode}'. Valid modes are: {VALID_MODES}"
            )
        
        # Set the mode
        success = set_mode(request.mode)

        if (request.mode == MODE_SEMI_AUTO):
            setup_semi_auto_settings()

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set mode in Redis")
        
        # Return the updated mode
        current_mode = get_mode()
        return ModeResponse(
            current=current_mode,
            valid_modes=VALID_MODES
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/status", response_model=StatusResponse)
async def get_current_status():
    """Get the current sequence status."""
    try:
        status = get_status()
        has_active_sequence = status is not None
        
        return StatusResponse(
            status=status,
            has_active_sequence=has_active_sequence
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/pause", response_model=ActionResponse)
async def pause_system():
    """Pause the watering system."""
    try:
        success = pause()
        current_mode = get_mode()
        
        if success:
            return ActionResponse(
                success=True,
                message="System paused successfully",
                current_mode=current_mode
            )
        else:
            return ActionResponse(
                success=False,
                message="Failed to pause system",
                current_mode=current_mode
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/resume", response_model=ActionResponse)
async def resume_system():
    """Resume the watering system from pause."""
    try:
        success = resume()
        current_mode = get_mode()
        
        if success:
            return ActionResponse(
                success=True,
                message="System resumed successfully",
                current_mode=current_mode
            )
        else:
            return ActionResponse(
                success=False,
                message="Failed to resume system",
                current_mode=current_mode
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Arrosage API...")
    print("📡 Available endpoints:")
    print("   GET  / - API information")
    print("   GET  /mode - Get current mode")
    print("   POST /mode - Set new mode")
    print("   GET  /status - Get sequence status")
    print("   POST /pause - Pause system")
    print("   POST /resume - Resume system")
    print("💡 Example usage:")
    print("   curl http://localhost:8000/mode")
    print("   curl http://localhost:8000/status")
    print("   curl -X POST http://localhost:8000/pause")
    print("   curl -X POST http://localhost:8000/resume")
    print("   curl -X POST http://localhost:8000/mode -H 'Content-Type: application/json' -d '{\"mode\": \"auto\"}'")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
