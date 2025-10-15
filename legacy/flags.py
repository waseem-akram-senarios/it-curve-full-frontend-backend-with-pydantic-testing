"""
Feature Flags Configuration for NEMT Validation Migration

This module manages feature flags for controlling validation behavior
during the migration from legacy to NEMT schema validation.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Literal


class ValidationMode(str, Enum):
    """Validation mode enumeration"""
    LEGACY = "legacy"
    HYBRID = "hybrid" 
    NEW = "new"


def get_validation_mode() -> ValidationMode:
    """
    Get the current validation mode from environment variables.
    
    Returns:
        ValidationMode enum value
        
    Environment Variables:
        VALIDATION_MODE: One of 'legacy', 'hybrid', 'new' (default: 'legacy')
    """
    mode_str = os.getenv("VALIDATION_MODE", "legacy").lower().strip()
    
    try:
        return ValidationMode(mode_str)
    except ValueError:
        # Invalid mode, default to legacy for safety
        return ValidationMode.LEGACY


def get_validation_fallback() -> bool:
    """
    Get the validation fallback setting.
    
    Returns:
        bool: True if fallback to legacy validation is enabled
        
    Environment Variables:
        VALIDATION_FALLBACK: 'true' or 'false' (default: 'true')
    """
    fallback_str = os.getenv("VALIDATION_FALLBACK", "true").lower().strip()
    return fallback_str in ("true", "1", "yes", "on")


def get_validation_config() -> dict[str, any]:
    """
    Get complete validation configuration.
    
    Returns:
        dict: Configuration dictionary with all validation settings
    """
    return {
        "mode": get_validation_mode(),
        "fallback_enabled": get_validation_fallback(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")
    }


def is_legacy_mode() -> bool:
    """Check if current mode is legacy"""
    return get_validation_mode() == ValidationMode.LEGACY


def is_hybrid_mode() -> bool:
    """Check if current mode is hybrid"""
    return get_validation_mode() == ValidationMode.HYBRID


def is_new_mode() -> bool:
    """Check if current mode is new"""
    return get_validation_mode() == ValidationMode.NEW


def should_run_nemt_validation() -> bool:
    """
    Determine if NEMT validation should be run.
    
    Returns:
        bool: True if NEMT validation should be executed
    """
    mode = get_validation_mode()
    return mode in (ValidationMode.HYBRID, ValidationMode.NEW)


def should_fallback_on_error() -> bool:
    """
    Determine if system should fallback to legacy validation on NEMT errors.
    
    Returns:
        bool: True if fallback should occur
    """
    return get_validation_mode() == ValidationMode.NEW and get_validation_fallback()


# Configuration validation
def validate_config() -> tuple[bool, str]:
    """
    Validate the current configuration.
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    try:
        mode = get_validation_mode()
        fallback = get_validation_fallback()
        
        # Validate mode
        if mode not in ValidationMode:
            return False, f"Invalid VALIDATION_MODE: {mode}"
        
        # Validate fallback logic
        if mode == ValidationMode.LEGACY and fallback:
            return False, "VALIDATION_FALLBACK should be false in legacy mode"
        
        return True, ""
        
    except Exception as e:
        return False, f"Configuration validation error: {str(e)}"


# Runtime configuration info
def get_config_info() -> dict[str, any]:
    """
    Get human-readable configuration information.
    
    Returns:
        dict: Configuration summary
    """
    config = get_validation_config()
    
    return {
        "validation_mode": config["mode"].value,
        "fallback_enabled": config["fallback_enabled"],
        "nemt_validation_active": should_run_nemt_validation(),
        "fallback_on_error": should_fallback_on_error(),
        "environment": config["environment"],
        "debug_mode": config["debug_mode"]
    }


# Exports
__all__ = [
    "ValidationMode",
    "get_validation_mode",
    "get_validation_fallback", 
    "get_validation_config",
    "is_legacy_mode",
    "is_hybrid_mode",
    "is_new_mode",
    "should_run_nemt_validation",
    "should_fallback_on_error",
    "validate_config",
    "get_config_info"
]
