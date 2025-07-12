from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import sys
from typing import Optional
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import route handlers
from routes.step1_diagrams import router as step1_router
from routes.step2_mapping import router as step2_router
from routes.step3_marks import router as step3_router
from routes.step4_questions import router as step4_router
from routes.step5_cards import router as step5_router
from routes.pipeline import router as pipeline_router

# Import dependency checks
from end_to_end import check_dependencies, DEPENDENCIES_OK, GEMINI_CLIENT_OK

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CBSE Question Parser API",
    description="API for processing CBSE Mathematics exam papers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dependency check
@app.on_event("startup")
async def startup_event():
    """Check dependencies on startup"""
    logger.info("Starting CBSE Question Parser API...")
    
    if not DEPENDENCIES_OK:
        logger.error("Missing required dependencies!")
        # Could still start but endpoints will return errors
    
    if not GEMINI_CLIENT_OK:
        logger.error("Gemini client not initialized!")
        # Could still start but endpoints will return errors
    
    logger.info("API startup complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "dependencies_ok": DEPENDENCIES_OK,
        "gemini_client_ok": GEMINI_CLIENT_OK,
        "message": "CBSE Question Parser API is running"
    }

# System status endpoint
@app.get("/status")
async def system_status():
    """Detailed system status"""
    return {
        "api_version": "1.0.0",
        "dependencies": {
            "pytorch": DEPENDENCIES_OK,
            "gemini": GEMINI_CLIENT_OK,
            "message": "All systems operational" if (DEPENDENCIES_OK and GEMINI_CLIENT_OK) else "Some dependencies missing"
        },
        "available_endpoints": [
            "/api/v1/extract-diagrams",
            "/api/v1/map-diagrams", 
            "/api/v1/extract-marks",
            "/api/v1/extract-questions",
            "/api/v1/generate-cards",
            "/api/v1/process-pipeline"
        ]
    }

# Include routers
app.include_router(step1_router, prefix="/api/v1", tags=["Step 1 - Diagram Extraction"])
app.include_router(step2_router, prefix="/api/v1", tags=["Step 2 - Diagram Mapping"])
app.include_router(step3_router, prefix="/api/v1", tags=["Step 3 - Marks Extraction"])
app.include_router(step4_router, prefix="/api/v1", tags=["Step 4 - Question Extraction"])
app.include_router(step5_router, prefix="/api/v1", tags=["Step 5 - Question Cards"])
app.include_router(pipeline_router, prefix="/api/v1", tags=["End-to-End Pipeline"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "details": str(exc) if app.debug else None
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 