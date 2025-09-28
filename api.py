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
try:
    print("📦 Importing commands...")
    from commands.semi_auto import setup_semi_auto_settings
    print("✅ semi_auto imported")
    from commands.pause import pause
    print("✅ pause imported")
    from commands.resume import resume
    print("✅ resume imported")
    from commands.reset import reset
    print("✅ reset imported")
except Exception as e:
    print(f"❌ Error importing commands: {e}")
    import traceback
    traceback.print_exc()

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

class SettingsRequest(BaseModel):
    start_at: str
    sequence: list[int]
    schedule: list[bool]

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
            "POST /resume": "Resume the system",
            "POST /reset": "Reset the system",
            "GET /settings": "Get current settings",
            "POST /settings": "Update settings"
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

@app.post("/reset", response_model=ActionResponse)
async def reset_system():
    """Reset the watering system to initial state."""
    try:
        
        # Call the reset function
        success = reset()
        
        # Get current mode
        current_mode = get_mode()
        
        if success:
            response = ActionResponse(
                success=True,
                message="System reset successfully",
                current_mode=current_mode
            )
            return response
        else:
            response = ActionResponse(
                success=False,
                message="Failed to reset system",
                current_mode=current_mode
            )
            return response
            
    except Exception as e:
        print(f"❌ API: Unexpected error in reset endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/settings")
async def get_current_settings():
    """Get the current settings."""
    try:
        print("🌐 API: Settings endpoint called")
        
        # Get settings from Redis
        print("📖 API: Getting settings from Redis...")
        from data.redis import get_json_from_redis
        settings = get_json_from_redis('settings')
        print(f"📖 API: Settings retrieved: {settings}")
        
        if settings is None:
            print("⚠️  API: No settings found in Redis")
            raise HTTPException(status_code=404, detail="Settings not found in Redis")
        
        print("✅ API: Returning settings successfully")
        return settings
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ API: Unexpected error in settings endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/settings")
async def update_settings(request: SettingsRequest):
    """Update the system settings."""
    try:
        print("🌐 API: Update settings endpoint called")
        print(f"📥 API: Received settings: {request}")
        
        # Validate start_at format (HH:MM)
        import re
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(time_pattern, request.start_at):
            print(f"❌ API: Invalid start_at format: {request.start_at}")
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid start_at format '{request.start_at}'. Must be HH:MM (24-hour format)"
            )
        
        # Validate sequence array (must have exactly 8 integers)
        if len(request.sequence) != 8:
            print(f"❌ API: Invalid sequence length: {len(request.sequence)}")
            raise HTTPException(
                status_code=422,
                detail=f"Sequence must contain exactly 8 integers, got {len(request.sequence)}"
            )
        
        # Validate all sequence values are non-negative integers
        for i, duration in enumerate(request.sequence):
            if not isinstance(duration, int) or duration < 0:
                print(f"❌ API: Invalid sequence value at index {i}: {duration}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Sequence value at index {i} must be a non-negative integer, got {duration}"
                )
        
        # Validate schedule array (must have exactly 7 booleans)
        if len(request.schedule) != 7:
            print(f"❌ API: Invalid schedule length: {len(request.schedule)}")
            raise HTTPException(
                status_code=422,
                detail=f"Schedule must contain exactly 7 booleans, got {len(request.schedule)}"
            )
        
        # Validate all schedule values are booleans
        for i, day_enabled in enumerate(request.schedule):
            if not isinstance(day_enabled, bool):
                print(f"❌ API: Invalid schedule value at index {i}: {day_enabled}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Schedule value at index {i} must be a boolean, got {type(day_enabled).__name__}"
                )
        
        print("✅ API: All validation passed")
        
        # Create settings object
        settings_data = {
            "start_at": request.start_at,
            "sequence": request.sequence,
            "schedule": request.schedule
        }
        
        
        # Save to Redis
        print("💾 API: Saving settings to Redis...")
        from data.redis import set_json_to_redis
        success = set_json_to_redis('settings', settings_data)
        
        if not success:
            print("❌ API: Failed to save settings to Redis")
            raise HTTPException(status_code=500, detail="Failed to save settings to Redis")
        
        print("✅ API: Settings saved successfully")
        
        # Return the saved settings
        return settings_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ API: Unexpected error in update settings endpoint: {e}")
        import traceback
        traceback.print_exc()
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
    print("   POST /reset - Reset system")
    print("   GET  /settings - Get current settings")
    print("   POST /settings - Update settings")
    print("💡 Example usage:")
    print("   curl http://localhost:8000/mode")
    print("   curl http://localhost:8000/status")
    print("   curl http://localhost:8000/settings")
    print("   curl -X POST http://localhost:8000/pause")
    print("   curl -X POST http://localhost:8000/resume")
    print("   curl -X POST http://localhost:8000/reset")
    print("   curl -X POST http://localhost:8000/mode -H 'Content-Type: application/json' -d '{\"mode\": \"auto\"}'")
    print("   curl -X POST http://localhost:8000/settings -H 'Content-Type: application/json' -d '{\"start_at\": \"20:00\", \"sequence\": [3600,3600,3600,3600,3600,3600,3600,0], \"schedule\": [false,false,false,false,false,false,true]}'")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
