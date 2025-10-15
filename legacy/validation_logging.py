"""
Validation Logging Infrastructure

This module provides structured logging for validation events, including
counters, metrics, and error pattern analysis for the NEMT migration.
"""

from __future__ import annotations

import logging
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict, Counter
import threading

# Configure logging
logger = logging.getLogger(__name__)

# Thread-safe counters for metrics
_counters_lock = threading.Lock()
_validation_counters = defaultdict(Counter)
_error_patterns = defaultdict(list)
_latency_metrics = defaultdict(list)


def log_validation_event(
    mode: str,
    ok: bool,
    kind: str,
    meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a validation event with structured data and update counters.
    
    Args:
        mode: Validation mode (legacy, hybrid, new)
        ok: Whether validation succeeded
        kind: Type of validation event
        meta: Additional metadata
    """
    if meta is None:
        meta = {}
    
    # Create structured log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "validation",
        "mode": mode,
        "success": ok,
        "kind": kind,
        "meta": meta
    }
    
    # Log to standard logger
    log_level = logging.INFO if ok else logging.WARNING
    logger.log(log_level, f"Validation event: {json.dumps(log_entry)}")
    
    # Update counters (thread-safe)
    with _counters_lock:
        _validation_counters[mode][f"{kind}_{'success' if ok else 'failure'}"] += 1
        
        # Track latency if provided
        if "latency_ms" in meta:
            _latency_metrics[f"{mode}_{kind}"].append(meta["latency_ms"])
            
            # Keep only last 1000 measurements to prevent memory growth
            if len(_latency_metrics[f"{mode}_{kind}"]) > 1000:
                _latency_metrics[f"{mode}_{kind}"] = _latency_metrics[f"{mode}_{kind}"][-1000:]
        
        # Track error patterns
        if not ok and "error" in meta:
            error_key = f"{mode}_{kind}"
            _error_patterns[error_key].append({
                "timestamp": datetime.now().isoformat(),
                "error": meta["error"],
                "details": meta.get("details", [])
            })
            
            # Keep only last 100 error patterns per type
            if len(_error_patterns[error_key]) > 100:
                _error_patterns[error_key] = _error_patterns[error_key][-100:]


def get_validation_metrics() -> Dict[str, Any]:
    """
    Get current validation metrics and counters.
    
    Returns:
        Dict with validation statistics
    """
    with _counters_lock:
        # Calculate success/failure rates by mode
        mode_stats = {}
        for mode, counters in _validation_counters.items():
            total_events = sum(counters.values())
            success_events = sum(count for key, count in counters.items() if key.endswith('_success'))
            failure_events = sum(count for key, count in counters.items() if key.endswith('_failure'))
            
            mode_stats[mode] = {
                "total_events": total_events,
                "success_count": success_events,
                "failure_count": failure_events,
                "success_rate": success_events / total_events if total_events > 0 else 0.0,
                "failure_rate": failure_events / total_events if total_events > 0 else 0.0,
                "counters": dict(counters)
            }
        
        # Calculate latency statistics
        latency_stats = {}
        for key, latencies in _latency_metrics.items():
            if latencies:
                latency_stats[key] = {
                    "count": len(latencies),
                    "avg_ms": sum(latencies) / len(latencies),
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
                    "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0
                }
        
        # Error pattern summary
        error_summary = {}
        for key, patterns in _error_patterns.items():
            if patterns:
                error_summary[key] = {
                    "count": len(patterns),
                    "recent_errors": patterns[-5:],  # Last 5 errors
                    "error_types": Counter(p.get("error", "unknown") for p in patterns)
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "mode_statistics": mode_stats,
            "latency_statistics": latency_stats,
            "error_patterns": error_summary,
            "total_events": sum(sum(counters.values()) for counters in _validation_counters.values())
        }


def reset_metrics() -> None:
    """Reset all validation metrics and counters."""
    with _counters_lock:
        _validation_counters.clear()
        _error_patterns.clear()
        _latency_metrics.clear()
    
    logger.info("Validation metrics reset")


def log_validation_comparison(
    legacy_result: bool,
    nemt_result: bool,
    legacy_error: Optional[Dict[str, Any]],
    nemt_error: Optional[Dict[str, Any]],
    payload_size: int
) -> None:
    """
    Log comparison between legacy and NEMT validation results.
    
    Args:
        legacy_result: Legacy validation success
        nemt_result: NEMT validation success  
        legacy_error: Legacy validation error
        nemt_error: NEMT validation error
        payload_size: Size of payload in characters
    """
    comparison_type = "match" if legacy_result == nemt_result else "divergent"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "validation_comparison",
        "comparison_type": comparison_type,
        "legacy_success": legacy_result,
        "nemt_success": nemt_result,
        "legacy_error_count": len(legacy_error.get("details", [])) if legacy_error else 0,
        "nemt_error_count": len(nemt_error.get("details", [])) if nemt_error else 0,
        "payload_size": payload_size
    }
    
    logger.info(f"Validation comparison: {json.dumps(log_entry)}")
    
    # Update comparison counters
    with _counters_lock:
        _validation_counters["comparison"][f"{comparison_type}_comparisons"] += 1


def log_migration_event(
    event_type: str,
    from_mode: str,
    to_mode: str,
    success: bool,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log migration events (mode changes, rollbacks, etc.).
    
    Args:
        event_type: Type of migration event
        from_mode: Previous validation mode
        to_mode: New validation mode
        success: Whether migration was successful
        details: Additional details
    """
    if details is None:
        details = {}
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": "migration",
        "migration_event": event_type,
        "from_mode": from_mode,
        "to_mode": to_mode,
        "success": success,
        "details": details
    }
    
    log_level = logging.INFO if success else logging.ERROR
    logger.log(log_level, f"Migration event: {json.dumps(log_entry)}")


def get_error_analysis() -> Dict[str, Any]:
    """
    Get analysis of error patterns and trends.
    
    Returns:
        Dict with error analysis
    """
    with _counters_lock:
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_error_patterns": sum(len(patterns) for patterns in _error_patterns.values()),
            "error_patterns_by_type": {}
        }
        
        # Analyze error patterns by type
        for key, patterns in _error_patterns.items():
            if patterns:
                error_types = Counter(p.get("error", "unknown") for p in patterns)
                recent_errors = patterns[-10:]  # Last 10 errors
                
                analysis["error_patterns_by_type"][key] = {
                    "total_errors": len(patterns),
                    "unique_error_types": len(error_types),
                    "most_common_errors": dict(error_types.most_common(5)),
                    "recent_errors": recent_errors
                }
        
        return analysis


# Exports
__all__ = [
    "log_validation_event",
    "get_validation_metrics",
    "reset_metrics",
    "log_validation_comparison",
    "log_migration_event",
    "get_error_analysis"
]
