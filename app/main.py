"""
Main FastAPI Application

This is the main FastAPI application that includes the validation router
for testing and monitoring the NEMT validation migration.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.validation import router as validation_router


# Create FastAPI app
app = FastAPI(
    title="NEMT Validation API",
    description="API for NEMT trip validation with legacy and new schema support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include validation router
app.include_router(validation_router)


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "NEMT Validation API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "validation_endpoints": "/api/validate"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "validation_mode": "nemt",
            "schema_version": "v2",
            "pydantic_version": "2.x"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/config")
async def get_app_config():
    """Get application configuration"""
    return {
        "app_config": {
            "validation_mode": "nemt",
            "schema_version": "v2",
            "pydantic_version": "2.x"
        },
        "available_endpoints": {
            "validation": "/api/validate",
            "docs": "/docs",
            "health": "/health",
            "config": "/config"
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "details": [{
                "loc": ["server"],
                "msg": "An unexpected error occurred",
                "type": "server_error"
            }]
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
