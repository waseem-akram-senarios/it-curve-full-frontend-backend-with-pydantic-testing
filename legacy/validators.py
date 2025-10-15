"""
Side-by-Side Validation System

This module provides validation functions that run both legacy and NEMT validation
in parallel, controlled by feature flags, without changing existing behavior.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple, Union
import time
from datetime import datetime

from app.config.flags import (
    get_validation_mode,
    should_run_nemt_validation,
    should_fallback_on_error,
    is_legacy_mode,
    is_hybrid_mode,
    is_new_mode
)
from app.validation.nemt_adapter import validate_nemt_sidecar, validate_nemt_direct
from app.infra.validation_logging import log_validation_event


def validate_legacy_first(payload: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], None]]:
    """
    Main validation function that respects feature flags and runs appropriate validation.
    
    In legacy mode: Only runs legacy validation (existing behavior)
    In hybrid mode: Runs legacy validation, NEMT runs as sidecar (logs only)
    In new mode: Runs NEMT validation with optional fallback to legacy
    
    Args:
        payload: Payload data to validate (legacy format)
        
    Returns:
        Tuple of (success: bool, error_json: dict|None)
        - Legacy mode: (legacy_result, legacy_error)
        - Hybrid mode: (legacy_result, legacy_error) + NEMT sidecar logs
        - New mode: (nemt_result, nemt_error) with optional fallback
    """
    mode = get_validation_mode()
    start_time = time.time()
    
    try:
        if is_legacy_mode():
            # Legacy mode: Only run legacy validation (existing behavior)
            legacy_ok, legacy_error = _run_legacy_validation(payload)
            
            log_validation_event(
                mode=mode.value,
                ok=legacy_ok,
                kind="legacy_only",
                meta={
                    "latency_ms": (time.time() - start_time) * 1000,
                    "payload_size": len(str(payload))
                }
            )
            
            return legacy_ok, legacy_error
            
        elif is_hybrid_mode():
            # Hybrid mode: Legacy decides, NEMT runs sidecar
            legacy_ok, legacy_error = _run_legacy_validation(payload)
            
            # Run NEMT validation as sidecar (doesn't affect result)
            nemt_ok, nemt_error = validate_nemt_sidecar(payload)
            
            # Log both results
            log_validation_event(
                mode=mode.value,
                ok=legacy_ok,
                kind="legacy_primary",
                meta={
                    "latency_ms": (time.time() - start_time) * 1000,
                    "legacy_result": legacy_ok,
                    "nemt_sidecar_result": nemt_ok,
                    "nemt_sidecar_errors": nemt_error.get("details", []) if nemt_error else [],
                    "payload_size": len(str(payload))
                }
            )
            
            # Legacy validation result determines success/failure
            return legacy_ok, legacy_error
            
        elif is_new_mode():
            # New mode: NEMT validation with optional fallback
            nemt_ok, nemt_error = validate_nemt_sidecar(payload)
            
            if nemt_ok:
                # NEMT validation succeeded
                log_validation_event(
                    mode=mode.value,
                    ok=True,
                    kind="nemt_primary",
                    meta={
                        "latency_ms": (time.time() - start_time) * 1000,
                        "payload_size": len(str(payload))
                    }
                )
                return True, None
                
            else:
                # NEMT validation failed - check fallback
                if should_fallback_on_error():
                    # Fallback to legacy validation
                    legacy_ok, legacy_error = _run_legacy_validation(payload)
                    
                    log_validation_event(
                        mode=mode.value,
                        ok=legacy_ok,
                        kind="nemt_with_fallback",
                        meta={
                            "latency_ms": (time.time() - start_time) * 1000,
                            "nemt_failed": True,
                            "legacy_fallback_result": legacy_ok,
                            "nemt_errors": nemt_error.get("details", []) if nemt_error else [],
                            "payload_size": len(str(payload))
                        }
                    )
                    
                    return legacy_ok, legacy_error
                    
                else:
                    # No fallback - return NEMT error
                    log_validation_event(
                        mode=mode.value,
                        ok=False,
                        kind="nemt_primary_failed",
                        meta={
                            "latency_ms": (time.time() - start_time) * 1000,
                            "nemt_errors": nemt_error.get("details", []) if nemt_error else [],
                            "payload_size": len(str(payload))
                        }
                    )
                    
                    return False, nemt_error
        
        else:
            # Unknown mode - default to legacy for safety
            return _run_legacy_validation(payload)
            
    except Exception as e:
        # Handle any unexpected errors
        log_validation_event(
            mode=mode.value,
            ok=False,
            kind="validation_error",
            meta={
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e),
                "payload_size": len(str(payload))
            }
        )
        
        # Return error in expected format
        error_dict = {
            "error": "ValidationError",
            "details": [{
                "loc": ["system"],
                "msg": f"Unexpected validation error: {str(e)}",
                "type": "system_error"
            }]
        }
        
        return False, error_dict


def _run_legacy_validation(payload: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], None]]:
    """
    Run legacy validation (placeholder implementation).
    
    In a real implementation, this would call the existing legacy validation
    functions. For now, we simulate legacy validation behavior.
    
    Args:
        payload: Payload data to validate
        
    Returns:
        Tuple of (success: bool, error_json: dict|None)
    """
    # Simulate legacy validation logic
    # In real implementation, this would call existing validation functions
    
    # Basic validation checks (simulating legacy behavior)
    required_fields = ["rider_name", "phone_number", "client_id"]
    
    for field in required_fields:
        if field not in payload or not payload[field]:
            error_dict = {
                "error": "ValidationError",
                "details": [{
                    "loc": [field],
                    "msg": f"Field '{field}' is required",
                    "type": "missing_field"
                }]
            }
            return False, error_dict
    
    # Simulate phone number validation (basic)
    phone = payload.get("phone_number", "")
    if phone and not phone.startswith("+"):
        error_dict = {
            "error": "ValidationError", 
            "details": [{
                "loc": ["phone_number"],
                "msg": "Phone number should start with +",
                "type": "format_error"
            }]
        }
        return False, error_dict
    
    # Legacy validation passed
    return True, None


def validate_both_modes(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run both legacy and NEMT validation and return both results.
    
    This is used for testing and comparison purposes.
    
    Args:
        payload: Payload data to validate
        
    Returns:
        Dict with both validation results
    """
    start_time = time.time()
    
    # Run legacy validation
    legacy_ok, legacy_error = _run_legacy_validation(payload)
    
    # Run NEMT validation
    nemt_ok, nemt_error = validate_nemt_sidecar(payload)
    
    result = {
        "legacy": {
            "success": legacy_ok,
            "error": legacy_error,
            "label": "Legacy Validation"
        },
        "nemt": {
            "success": nemt_ok,
            "error": nemt_error,
            "label": "NEMT Validation"
        },
        "comparison": {
            "both_passed": legacy_ok and nemt_ok,
            "both_failed": not legacy_ok and not nemt_ok,
            "divergent": legacy_ok != nemt_ok,
            "latency_ms": (time.time() - start_time) * 1000
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return result


def validate_nemt_only(payload: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], None]]:
    """
    Run only NEMT validation (for testing endpoints).
    
    Args:
        payload: Payload data to validate (should be in NEMT format)
        
    Returns:
        Tuple of (success: bool, error_json: dict|None)
    """
    return validate_nemt_direct(payload)


# Exports
__all__ = [
    "validate_legacy_first",
    "validate_both_modes",
    "validate_nemt_only"
]
