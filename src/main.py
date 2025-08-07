"""
Main FastAPI application for Game Master V3
"""
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import router
from config.settings import settings
from core.world_service import world_service

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")
    # Check if OpenAI API key is loaded
    import os
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OpenAI API key found")
    else:
        print("⚠️  OpenAI API key not found - AI features will be disabled")
else:
    print("No .env file found, using system environment variables")

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    # For reload mode, we need to ensure all child processes are terminated
    import os
    if settings.app_debug:
        logger.info("Debug mode detected, ensuring all child processes terminate...")
        # Send signal to process group to handle uvicorn's child processes
        try:
            os.killpg(os.getpgid(0), signum)
        except (OSError, ProcessLookupError):
            pass
    sys.exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        await world_service.initialize()
        logger.info("All services initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down services...")
        await world_service.shutdown()
        logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered RPG system with persistent world and semantic search",
    debug=settings.app_debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Setup Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_group_untemplated=True,
    should_instrument_requests_inprogress=True,
    should_round_latency_decimals=True,
    excluded_handlers=["/docs", "/redoc", "/openapi.json", "/favicon.ico"],
)
instrumentator.instrument(app).expose(app)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "world_service_initialized": world_service.is_initialized,
    }


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting uvicorn server...")
    try:
        # Pass these signal handling options to uvicorn
        uvicorn.run(
            "main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=settings.app_debug,
            log_level=settings.log_level.lower(),
            reload_excludes=["*.tmp", "*.log"] if settings.app_debug else None,
            # These options help with signal handling
            access_log=True,
            use_colors=True,
            # Important: these help with proper signal propagation in reload mode
            reload_delay=0.25,
            # Ensure proper shutdown in reload mode
            workers=1 if not settings.app_debug else None,
        )
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server shutdown complete")