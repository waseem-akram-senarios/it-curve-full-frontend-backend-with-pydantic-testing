"""
Validation API Routes

Read-only API endpoints for NEMT validation using the unified schema.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.schemas.nemt_trip import try_validate, format_validation_error, VALID_PAYLOAD_EXAMPLE, INVALID_PAYLOAD_EXAMPLE


router = APIRouter(prefix="/api/validate", tags=["validation"])


class ValidationRequest(BaseModel):
    """Request model for validation endpoints"""
    payload: Dict[str, Any]


class ValidationResponse(BaseModel):
    """Response model for validation endpoints"""
    success: bool
    error: Dict[str, Any] | None = None
    metadata: Dict[str, Any] | None = None


@router.post("/nemt", response_model=ValidationResponse)
async def validate_nemt_endpoint(request: ValidationRequest) -> ValidationResponse:
    """
    Validate payload using NEMT schema.
    
    This endpoint runs NEMT validation using the unified Pydantic v2 schema.
    """
    try:
        ok, model, error = try_validate(request.payload)
        
        return ValidationResponse(
            success=ok,
            error=error,
            metadata={
                "validation_mode": "nemt",
                "model_type": type(model).__name__ if model else None,
                "payload_size": len(str(request.payload))
            }
        )
        
    except Exception as e:
        error_response = {
            "error": "ValidationError",
            "details": [{
                "loc": ["system"],
                "msg": f"Unexpected error: {str(e)}",
                "type": "system_error"
            }]
        }
        
        return ValidationResponse(
            success=False,
            error=error_response,
            metadata={
                "validation_mode": "nemt",
                "exception": str(e)
            }
        )


@router.post("/test", response_model=ValidationResponse)
async def validate_test_endpoint(request: ValidationRequest) -> ValidationResponse:
    """
    Test endpoint for NEMT validation.
    
    This endpoint provides a simple test interface for NEMT validation.
    """
    try:
        ok, model, error = try_validate(request.payload)
        
        return ValidationResponse(
            success=ok,
            error=error,
            metadata={
                "validation_mode": "nemt_test",
                "model_type": type(model).__name__ if model else None,
                "payload_size": len(str(request.payload))
            }
        )
        
    except Exception as e:
        error_response = {
            "error": "ValidationError",
            "details": [{
                "loc": ["system"],
                "msg": f"Unexpected error: {str(e)}",
                "type": "system_error"
            }]
        }
        
        return ValidationResponse(
            success=False,
            error=error_response,
            metadata={
                "validation_mode": "nemt_test",
                "exception": str(e)
            }
        )


@router.get("/config")
async def get_validation_config() -> Dict[str, Any]:
    """Get current validation configuration."""
    return {
        "validation_mode": "nemt",
        "schema_version": "v2",
        "pydantic_version": "2.x",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/metrics")
async def get_validation_metrics_endpoint() -> Dict[str, Any]:
    """Get validation metrics and statistics."""
    return {
        "status": "active",
        "validation_mode": "nemt",
        "total_validations": 0,  # Would be tracked in real implementation
        "success_rate": 100.0,   # Would be calculated in real implementation
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/examples/valid")
async def get_valid_example() -> Dict[str, Any]:
    """Get example of valid NEMT payload."""
    return {
        "description": "Example valid NEMT payload",
        "payload": VALID_PAYLOAD_EXAMPLE,
        "format": "NEMT Schema v2"
    }


@router.get("/examples/invalid")
async def get_invalid_example() -> Dict[str, Any]:
    """Get example of invalid NEMT payload."""
    return {
        "description": "Example invalid NEMT payload with validation errors",
        "payload": INVALID_PAYLOAD_EXAMPLE,
        "format": "NEMT Schema v2"
    }


@router.get("/health")
async def validation_health_check() -> Dict[str, Any]:
    """Health check endpoint for validation system."""
    try:
        # Test basic NEMT validation functionality
        test_payload = {"test": "data"}
        ok, _, _ = try_validate(test_payload)
        
        return {
            "status": "healthy",
            "validation_mode": "nemt",
            "schema_version": "v2",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }


# Exports
__all__ = ["router"]
