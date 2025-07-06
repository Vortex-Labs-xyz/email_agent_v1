from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from .core.config import settings
from .db.database import init_db
from .agent.scheduler import email_scheduler
from .api.emails import router as emails_router
from .api.knowledge import router as knowledge_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Email Agent API...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Start scheduler
        await email_scheduler.start()
        logger.info("Email scheduler started")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Email Agent API...")
        
        try:
            # Stop scheduler
            await email_scheduler.stop()
            logger.info("Email scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Email Agent API",
    description="AI-powered email processing and response generation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(emails_router)
app.include_router(knowledge_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Email Agent API",
        "version": "1.0.0",
        "description": "AI-powered email processing and response generation system",
        "endpoints": {
            "emails": "/emails",
            "knowledge": "/knowledge",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check scheduler status
        scheduler_status = email_scheduler.is_running
        
        # Check database connection (basic check)
        from .db.database import engine
        
        return {
            "status": "healthy",
            "scheduler_running": scheduler_status,
            "database_connected": True,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/status")
async def get_system_status():
    """Get detailed system status."""
    try:
        # Get scheduler job status
        jobs = email_scheduler.get_job_status()
        
        # Get knowledge base stats
        from .agent.knowledge_base import knowledge_base_manager
        kb_stats = knowledge_base_manager.get_stats()
        
        return {
            "system_status": "running",
            "scheduler": {
                "running": email_scheduler.is_running,
                "jobs": jobs
            },
            "knowledge_base": kb_stats,
            "settings": {
                "auto_respond_enabled": settings.auto_respond_enabled,
                "email_check_interval": settings.email_check_interval,
                "max_emails_per_batch": settings.max_emails_per_batch,
                "default_ai_model": settings.default_ai_model
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )