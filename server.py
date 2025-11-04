#!/usr/bin/env python3
"""
FGD Stack FastAPI Server – Production-Ready REST API

Features:
- Rate limiting for API endpoints
- Configurable CORS policy
- Health check endpoint
- Better error handling
- Input validation
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
from dotenv import load_dotenv

from mcp_backend import FGDMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fgd_api_server")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="FGD Stack API",
    version="2.0.0",
    description="Production-ready MCP server API with rate limiting and security"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS - restrict in production!
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Serve static files if present
if Path("index.html").exists():
    app.mount("/static", StaticFiles(directory="."), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the main HTML interface."""
        return FileResponse("index.html")

# Global runtime state
RUN = {
    "server": None,
    "watch_dir": None,
    "memory_file": None,
    "log_file": "fgd_runtime.log",
    "config_path": None
}

# ==================== PYDANTIC MODELS ====================

class StartRequest(BaseModel):
    """Request model for starting the MCP server."""
    watch_dir: str = Field(..., description="Directory to watch")
    default_provider: str = Field(default="grok", description="Default LLM provider")

    @validator('default_provider')
    def validate_provider(cls, v):
        """Ensure default provider is grok for reliability."""
        valid_providers = ['grok', 'openai', 'claude', 'ollama']
        if v not in valid_providers:
            logger.warning(f"Invalid provider '{v}', falling back to 'grok'")
            return 'grok'
        return v

    @validator('watch_dir')
    def validate_watch_dir(cls, v):
        """Validate watch directory exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return str(path.resolve())


class LLMQueryRequest(BaseModel):
    """Request model for LLM queries."""
    prompt: str = Field(..., description="Prompt for the LLM")
    provider: Optional[str] = Field(default="grok", description="LLM provider")

    @validator('provider')
    def validate_provider(cls, v):
        """Ensure provider defaults to grok."""
        if v is None:
            return 'grok'
        valid_providers = ['grok', 'openai', 'claude', 'ollama']
        if v not in valid_providers:
            logger.warning(f"Invalid provider '{v}', falling back to 'grok'")
            return 'grok'
        return v


# ==================== API ENDPOINTS ====================

@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """
    Health check endpoint for monitoring.

    Returns server status and basic metrics.
    """
    mcp_running = RUN["server"] is not None
    return JSONResponse({
        "status": "healthy",
        "service": "FGD Stack API",
        "version": "2.0.0",
        "mcp_server_running": mcp_running,
        "watch_dir": RUN.get("watch_dir"),
    })


@app.get("/api/status")
@limiter.limit("60/minute")
async def status(request: Request):
    """
    Get current server status.

    Returns detailed information about the running MCP server.
    """
    try:
        running = RUN["server"] is not None
        return JSONResponse({
            "api": "ok",
            "mcp_running": running,
            "watch_dir": RUN.get("watch_dir"),
            "memory_file": RUN.get("memory_file"),
            "log_file": RUN.get("log_file"),
            "config_path": RUN.get("config_path")
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.get("/api/suggest")
@limiter.limit("30/minute")
async def suggest(request: Request):
    """
    Suggest available directories.

    Returns list of directories in current working directory.
    """
    try:
        base = Path(".")
        dirs = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_dir()]
        # Limit to 100 directories to prevent abuse
        return JSONResponse(dirs[:100])
    except Exception as e:
        logger.error(f"Error in suggest endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list directories: {str(e)}")


@app.post("/api/start")
@limiter.limit("10/minute")
async def start(request: Request, start_req: StartRequest):
    """
    Start the MCP server.

    Creates a new MCP server instance with the specified configuration.
    """
    try:
        # Check if server is already running
        if RUN["server"] is not None:
            return JSONResponse({
                "success": False,
                "error": "MCP server is already running. Stop it first."
            }, status_code=400)

        watch_dir = start_req.watch_dir
        provider = start_req.default_provider

        # Use config.example.yaml as template
        config_path = "config.example.yaml"
        if not Path(config_path).exists():
            return JSONResponse({
                "success": False,
                "error": "Missing config.example.yaml template file"
            }, status_code=500)

        # Create server instance
        try:
            RUN["server"] = FGDMCPServer(config_path)
            RUN["watch_dir"] = watch_dir
            RUN["memory_file"] = str(Path(watch_dir) / ".fgd_memory.json")
            RUN["config_path"] = config_path

            # Start MCP server in background
            asyncio.create_task(RUN["server"].run())

            # Log successful start
            logger.info(f"MCP server started - watching: {watch_dir}, provider: {provider}")

            Path(RUN["log_file"]).write_text(
                f"INFO: MCP server started at {watch_dir} with provider {provider}\n"
            )

            return JSONResponse({
                "success": True,
                "memory_file": RUN["memory_file"],
                "log_file": RUN["log_file"],
                "watch_dir": watch_dir,
                "provider": provider
            })

        except ValueError as e:
            # Pydantic validation error
            return JSONResponse({
                "success": False,
                "error": f"Configuration error: {str(e)}"
            }, status_code=400)

    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        RUN["server"] = None
        return JSONResponse({
            "success": False,
            "error": f"Failed to start server: {str(e)}"
        }, status_code=500)


@app.post("/api/stop")
@limiter.limit("10/minute")
async def stop(request: Request):
    """
    Stop the MCP server.

    Gracefully shuts down the running MCP server.
    """
    try:
        if RUN["server"] is None:
            return JSONResponse({
                "success": False,
                "error": "No server is running"
            }, status_code=400)

        # Stop the server
        RUN["server"].stop()
        RUN["server"] = None
        RUN["watch_dir"] = None
        RUN["memory_file"] = None

        logger.info("MCP server stopped via API")

        return JSONResponse({
            "success": True,
            "message": "MCP server stopped successfully"
        })

    except Exception as e:
        logger.error(f"Error stopping server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop server: {str(e)}")


@app.get("/api/logs", response_class=PlainTextResponse)
@limiter.limit("30/minute")
async def logs(request: Request, file: str):
    """
    Retrieve log file contents.

    Args:
        file: Path to log file

    Returns:
        Log file contents as plain text
    """
    try:
        # Sanitize file path to prevent traversal attacks
        log_path = Path(file).resolve()

        # Only allow reading from specific log directories
        allowed_paths = [
            Path(".").resolve(),
            Path(RUN.get("watch_dir", ".")).resolve()
        ]

        # Check if log file is in an allowed location
        is_allowed = any(
            str(log_path).startswith(str(allowed))
            for allowed in allowed_paths
        )

        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail="Access to this log file is not permitted"
            )

        if not log_path.exists():
            return "No logs yet."

        # Limit log file size to prevent memory issues
        max_size = 10 * 1024 * 1024  # 10 MB
        if log_path.stat().st_size > max_size:
            # Read only last 10MB
            with open(log_path, 'rb') as f:
                f.seek(-max_size, 2)
                content = f.read().decode('utf-8', errors='ignore')
                return f"[Log truncated - showing last 10MB]\n\n{content}"

        return log_path.read_text(encoding="utf-8", errors='ignore')

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@app.get("/api/memory")
@limiter.limit("30/minute")
async def memory(request: Request):
    """
    Retrieve all stored memories.

    Returns the complete memory store from the MCP server.
    """
    try:
        if not RUN["server"]:
            raise HTTPException(status_code=400, detail="Server not running")

        memories = RUN["server"].memory.recall()
        return JSONResponse(memories)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving memory: {str(e)}")


@app.post("/api/llm_query")
@limiter.limit("20/minute")
async def llm_query(request: Request, query_req: LLMQueryRequest):
    """
    Query an LLM through the MCP server.

    Args:
        query_req: LLM query request with prompt and provider

    Returns:
        LLM response
    """
    try:
        if not RUN["server"]:
            raise HTTPException(status_code=400, detail="Server not running")

        prompt = query_req.prompt
        provider = query_req.provider

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        # Query the LLM
        response = await RUN["server"].llm.query(prompt, provider)

        return JSONResponse({
            "success": True,
            "response": response,
            "provider": provider
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LLM query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")


@app.get("/api/conversations")
@limiter.limit("30/minute")
async def get_conversations(request: Request):
    """
    Retrieve all conversation history.

    Returns conversation threads with prompts and responses.
    """
    try:
        if not RUN["server"]:
            raise HTTPException(status_code=400, detail="Server not running")

        conversations = RUN["server"].memory.recall(category="conversations")

        # Sort by timestamp (most recent first)
        sorted_convos = sorted(
            conversations.items(),
            key=lambda x: x[1].get("value", {}).get("timestamp", ""),
            reverse=True
        )

        return JSONResponse({
            "success": True,
            "count": len(sorted_convos),
            "conversations": [
                {
                    "id": key,
                    "prompt": val["value"]["prompt"],
                    "response": val["value"]["response"],
                    "provider": val["value"]["provider"],
                    "timestamp": val["value"]["timestamp"],
                    "context_used": val["value"].get("context_used", 0)
                }
                for key, val in sorted_convos
            ]
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversations: {str(e)}")


@app.get("/api/pending_edits")
@limiter.limit("60/minute")
async def get_pending_edits(request: Request):
    """
    Get pending edit requests awaiting approval.

    Returns pending edits that need user approval.
    """
    try:
        if not RUN["server"]:
            raise HTTPException(status_code=400, detail="Server not running")

        pending_file = Path(RUN["watch_dir"]) / ".fgd_pending_edit.json"

        if not pending_file.exists():
            return JSONResponse({
                "success": True,
                "has_pending": False,
                "pending_edit": None
            })

        pending_data = json.loads(pending_file.read_text())

        return JSONResponse({
            "success": True,
            "has_pending": True,
            "pending_edit": pending_data
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving pending edits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pending edits: {str(e)}")


# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": request.url.path}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Log server startup."""
    logger.info("FGD Stack API Server starting...")
    logger.info(f"CORS origins: {ALLOWED_ORIGINS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown - stop MCP server if running."""
    logger.info("FGD Stack API Server shutting down...")
    if RUN["server"]:
        try:
            RUN["server"].stop()
            logger.info("MCP server stopped during shutdown")
        except Exception as e:
            logger.error(f"Error stopping MCP server during shutdown: {e}")


# ==================== MAIN ====================

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8456"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
