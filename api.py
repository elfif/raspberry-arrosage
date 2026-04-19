#!/usr/bin/env python3
"""
Minimalistic FastAPI for Arrosage System

This API provides endpoints to interact with the watering system mode.
No authentication or HTTPS - simple HTTP endpoints for mode management.
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import logging
import time
import traceback as tb
from typing import Callable

# Add current directory to path to import data modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("arrosage_api")

from data.mode import get_mode, set_mode, VALID_MODES, MODE_SEMI_AUTO, MODE_MANUAL
from data.status import get_status
try:
    from commands.pause import pause
    from commands.resume import resume
    from commands.reset import reset
    from commands.start import start
    from commands.relay import (
        open_relay_manual,
        close_relays_manual,
        build_relay_status,
    )
except Exception as e:
    logger.error(f"❌ Error importing commands: {e}")
    logger.error(tb.format_exc())

# Create FastAPI app
app = FastAPI(
    title="Arrosage API",
    description="Simple API for controlling the watering system",
    version="1.0.0"
)

# Configure CORS to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (localhost)
        "http://127.0.0.1:5173",  # Vite dev server (127.0.0.1)
        "http://192.168.1.46:5173",  # Vite dev server (LAN IP)
        # Add production origins here when deploying
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Log all incoming requests and responses with timing."""
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"➡️  {request.method} {request.url.path} - Client: {request.client.host}")
    
    try:
        # Process the request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"⬅️  {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s"
        )
        
        return response
        
    except Exception as e:
        # Log any unhandled exceptions
        duration = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Duration: {duration:.3f}s"
        )
        logger.error(f"Traceback:\n{tb.format_exc()}")
        
        # Re-raise to let FastAPI handle it
        raise

# Exception handler for better error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log all unhandled exceptions."""
    logger.error(f"🔥 Unhandled exception for {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Traceback:\n{tb.format_exc()}")
    
    # Return a proper error response
    return Response(
        content=f'{{"detail": "Internal server error: {str(exc)}"}}',
        status_code=500,
        media_type="application/json"
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

class RelayOpenRequest(BaseModel):
    relay_id: int  # 0..7

class RelayState(BaseModel):
    relay_id: int
    is_open: bool

class RelayStatusResponse(BaseModel):
    success: bool
    message: str
    current_mode: str | None
    relays: list[RelayState]

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
            "POST /start": "Start sequence (SEMI_AUTO mode only)",
            "POST /relay/open": "Open a single relay (MANUAL mode only)",
            "POST /relay/close": "Close all relays (MANUAL mode only)",
            "GET /relays": "Get current per-relay status",
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
        logger.info(f"POST /mode called with mode: {request.mode}")
        
        # Validate the mode
        logger.debug(f"Validating mode '{request.mode}' against valid modes: {VALID_MODES}")
        if request.mode not in VALID_MODES:
            logger.warning(f"Invalid mode requested: '{request.mode}'")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode '{request.mode}'. Valid modes are: {VALID_MODES}"
            )
        
        logger.info(f"Mode validation passed, setting mode to: {request.mode}")
        
        # Set the mode
        success = set_mode(request.mode)
        logger.debug(f"set_mode() returned: {success}")

        if not success:
            logger.error("Failed to set mode in Redis")
            raise HTTPException(status_code=500, detail="Failed to set mode in Redis")
        
        # Return the updated mode
        logger.debug("Retrieving current mode from Redis to confirm")
        current_mode = get_mode()
        logger.info(f"Mode successfully set to: {current_mode}")
        
        return ModeResponse(
            current=current_mode,
            valid_modes=VALID_MODES
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in POST /mode: {e}")
        logger.error(f"Request data: mode={request.mode}")
        logger.error(tb.format_exc())
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
        logger.info("Pause endpoint called")
        success = pause()
        current_mode = get_mode()
        
        if success:
            logger.info("System paused successfully")
            return ActionResponse(
                success=True,
                message="System paused successfully",
                current_mode=current_mode
            )
        else:
            logger.warning("Failed to pause system")
            return ActionResponse(
                success=False,
                message="Failed to pause system",
                current_mode=current_mode
            )
    except Exception as e:
        logger.error(f"Exception in pause endpoint: {e}")
        logger.error(tb.format_exc())
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
            logger.info("System reset successfully")
            response = ActionResponse(
                success=True,
                message="System reset successfully",
                current_mode=current_mode
            )
            return response
        else:
            logger.warning("Failed to reset system")
            response = ActionResponse(
                success=False,
                message="Failed to reset system",
                current_mode=current_mode
            )
            return response
            
    except Exception as e:
        logger.error(f"Unexpected error in reset endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/start", response_model=ActionResponse)
async def start_system():
    """Start a watering sequence (only works in SEMI_AUTO mode)."""
    try:
        logger.info("Start endpoint called")
        
        # Get current mode first
        current_mode = get_mode()
        
        # Check if in SEMI_AUTO mode
        if current_mode != MODE_SEMI_AUTO:
            logger.warning(f"Cannot start sequence. System is not in SEMI_AUTO mode (current: {current_mode})")
            return ActionResponse(
                success=False,
                message=f"Cannot start sequence. System must be in SEMI_AUTO mode (current mode: {current_mode})",
                current_mode=current_mode
            )
        
        # Call the start function
        success = start()
        
        if success:
            logger.info("Sequence started successfully")
            return ActionResponse(
                success=True,
                message="Sequence started successfully",
                current_mode=current_mode
            )
        else:
            logger.warning("Failed to start sequence")
            return ActionResponse(
                success=False,
                message="Failed to start sequence",
                current_mode=current_mode
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in start endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _current_opened_relay() -> int | None:
    """Read the currently opened relay (0-7) from Redis status, or None."""
    status = get_status()
    if status is None:
        return None
    opened = status.get('opened_relay')
    if not isinstance(opened, int) or opened < 0 or opened > 7:
        return None
    return opened


@app.post("/relay/open", response_model=RelayStatusResponse)
async def open_relay_endpoint(request: RelayOpenRequest):
    """Open a single relay (only works in MANUAL mode). relay_id is 0..7."""
    try:
        logger.info(f"POST /relay/open called with relay_id={request.relay_id}")

        if not isinstance(request.relay_id, int) or request.relay_id < 0 or request.relay_id > 7:
            logger.warning(f"Invalid relay_id: {request.relay_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relay_id '{request.relay_id}'. Must be an integer between 0 and 7."
            )

        current_mode = get_mode()

        if current_mode != MODE_MANUAL:
            logger.warning(
                f"Cannot open relay. System is not in MANUAL mode (current: {current_mode})"
            )
            return RelayStatusResponse(
                success=False,
                message=f"Cannot open relay. System must be in MANUAL mode (current mode: {current_mode})",
                current_mode=current_mode,
                relays=build_relay_status(_current_opened_relay()),
            )

        success = open_relay_manual(request.relay_id)

        if success:
            logger.info(f"Relay {request.relay_id} opened successfully")
            return RelayStatusResponse(
                success=True,
                message=f"Relay {request.relay_id} opened successfully",
                current_mode=current_mode,
                relays=build_relay_status(request.relay_id),
            )
        else:
            logger.warning(f"Failed to open relay {request.relay_id}")
            return RelayStatusResponse(
                success=False,
                message=f"Failed to open relay {request.relay_id}",
                current_mode=current_mode,
                relays=build_relay_status(_current_opened_relay()),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /relay/open endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/relay/close", response_model=RelayStatusResponse)
async def close_relay_endpoint():
    """Close all relays (only works in MANUAL mode)."""
    try:
        logger.info("POST /relay/close called")

        current_mode = get_mode()

        if current_mode != MODE_MANUAL:
            logger.warning(
                f"Cannot close relays. System is not in MANUAL mode (current: {current_mode})"
            )
            return RelayStatusResponse(
                success=False,
                message=f"Cannot close relays. System must be in MANUAL mode (current mode: {current_mode})",
                current_mode=current_mode,
                relays=build_relay_status(_current_opened_relay()),
            )

        success = close_relays_manual()

        if success:
            logger.info("All relays closed successfully")
            return RelayStatusResponse(
                success=True,
                message="All relays closed successfully",
                current_mode=current_mode,
                relays=build_relay_status(None),
            )
        else:
            logger.warning("Failed to close relays")
            return RelayStatusResponse(
                success=False,
                message="Failed to close relays",
                current_mode=current_mode,
                relays=build_relay_status(_current_opened_relay()),
            )

    except Exception as e:
        logger.error(f"Unexpected error in /relay/close endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/relays", response_model=RelayStatusResponse)
async def get_relays_status():
    """Return the current per-relay status. Works in any mode."""
    try:
        current_mode = get_mode()
        opened = _current_opened_relay()
        return RelayStatusResponse(
            success=True,
            message="Current relay status",
            current_mode=current_mode,
            relays=build_relay_status(opened),
        )
    except Exception as e:
        logger.error(f"Unexpected error in /relays endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/settings")
async def get_current_settings():
    """Get the current settings."""
    try:
        logger.info("Settings endpoint called")
        
        # Get settings from Redis
        logger.debug("Getting settings from Redis...")
        from data.redis import get_json_from_redis
        settings = get_json_from_redis('settings')
        logger.debug(f"Settings retrieved: {settings}")
        
        if settings is None:
            logger.warning("No settings found in Redis")
            raise HTTPException(status_code=404, detail="Settings not found in Redis")
        
        logger.info("Returning settings successfully")
        return settings
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in settings endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/settings")
async def update_settings(request: SettingsRequest):
    """Update the system settings."""
    try:
        logger.info("Update settings endpoint called")
        logger.debug(f"Received settings: {request}")
        
        # Validate start_at format (HH:MM)
        import re
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(time_pattern, request.start_at):
            logger.warning(f"Invalid start_at format: {request.start_at}")
            raise HTTPException(
                status_code=422, 
                detail=f"Invalid start_at format '{request.start_at}'. Must be HH:MM (24-hour format)"
            )
        
        # Validate sequence array (must have exactly 8 integers)
        if len(request.sequence) != 8:
            logger.warning(f"Invalid sequence length: {len(request.sequence)}")
            raise HTTPException(
                status_code=422,
                detail=f"Sequence must contain exactly 8 integers, got {len(request.sequence)}"
            )
        
        # Validate all sequence values are non-negative integers
        for i, duration in enumerate(request.sequence):
            if not isinstance(duration, int) or duration < 0:
                logger.warning(f"Invalid sequence value at index {i}: {duration}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Sequence value at index {i} must be a non-negative integer, got {duration}"
                )
        
        # Validate schedule array (must have exactly 7 booleans)
        if len(request.schedule) != 7:
            logger.warning(f"Invalid schedule length: {len(request.schedule)}")
            raise HTTPException(
                status_code=422,
                detail=f"Schedule must contain exactly 7 booleans, got {len(request.schedule)}"
            )
        
        # Validate all schedule values are booleans
        for i, day_enabled in enumerate(request.schedule):
            if not isinstance(day_enabled, bool):
                logger.warning(f"Invalid schedule value at index {i}: {day_enabled}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Schedule value at index {i} must be a boolean, got {type(day_enabled).__name__}"
                )
        
        logger.info("All validation passed")
        
        # Create settings object
        settings_data = {
            "start_at": request.start_at,
            "sequence": request.sequence,
            "schedule": request.schedule
        }
        
        
        # Save to Redis
        logger.info("Saving settings to Redis...")
        from data.redis import set_json_to_redis
        success = set_json_to_redis('settings', settings_data)
        
        if not success:
            logger.error("Failed to save settings to Redis")
            raise HTTPException(status_code=500, detail="Failed to save settings to Redis")
        
        logger.info("Settings saved successfully")
        
        # Return the saved settings
        return settings_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update settings endpoint: {e}")
        logger.error(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Arrosage API...")
    logger.info("📡 Available endpoints:")
    logger.info("   GET  / - API information")
    logger.info("   GET  /mode - Get current mode")
    logger.info("   POST /mode - Set new mode")
    logger.info("   GET  /status - Get sequence status")
    logger.info("   POST /pause - Pause system")
    logger.info("   POST /resume - Resume system")
    logger.info("   POST /reset - Reset system")
    logger.info("   POST /start - Start sequence (SEMI_AUTO mode only)")
    logger.info("   POST /relay/open - Open a single relay (MANUAL mode only)")
    logger.info("   POST /relay/close - Close all relays (MANUAL mode only)")
    logger.info("   GET  /relays - Get current per-relay status")
    logger.info("   GET  /settings - Get current settings")
    logger.info("   POST /settings - Update settings")
    logger.info("💡 Example usage:")
    logger.info("   curl http://localhost:8000/mode")
    logger.info("   curl http://localhost:8000/status")
    logger.info("   curl http://localhost:8000/settings")
    logger.info("   curl -X POST http://localhost:8000/pause")
    logger.info("   curl -X POST http://localhost:8000/resume")
    logger.info("   curl -X POST http://localhost:8000/reset")
    logger.info("   curl -X POST http://localhost:8000/start")
    logger.info("   curl -X POST http://localhost:8000/mode -H 'Content-Type: application/json' -d '{\"mode\": \"auto\"}'")
    logger.info("   curl -X POST http://localhost:8000/settings -H 'Content-Type: application/json' -d '{\"start_at\": \"20:00\", \"sequence\": [3600,3600,3600,3600,3600,3600,3600,0], \"schedule\": [false,false,false,false,false,false,true]}'")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
