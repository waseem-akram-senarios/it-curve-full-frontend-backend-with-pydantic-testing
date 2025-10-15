# NEMT Validation Migration - Phase 1 Implementation

## Overview

This implementation provides a zero-risk, parallel migration system for transitioning from legacy Pydantic v1 validation to the new robust NEMT Pydantic v2 schema validation.

## Features

- **Zero Downtime**: Existing system continues working unchanged
- **Feature Flags**: Controlled rollout via environment variables
- **Side-by-Side Validation**: Run both systems in parallel for comparison
- **Comprehensive Logging**: Metrics, error analysis, and performance monitoring
- **API Endpoints**: Test and monitor validation behavior
- **Rollback Safe**: Can instantly revert to legacy mode

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp env.example .env

# Set validation mode (choose one)
export VALIDATION_MODE=legacy    # Default - no changes to existing behavior
export VALIDATION_MODE=hybrid    # Legacy decides, NEMT runs sidecar
export VALIDATION_MODE=new       # NEMT validation with optional fallback

# Optional: Enable fallback for new mode
export VALIDATION_FALLBACK=true
```

### 2. Run Development Server

```bash
# Start the validation API server
export VALIDATION_MODE=hybrid
uvicorn app.main:app --reload --port 8000
```

### 3. Test Endpoints

```bash
# Test NEMT validation only
curl -s -X POST localhost:8000/api/validate/nemt \
  -H 'content-type: application/json' \
  -d '{"payload": {"rider_name": "John Doe", "phone_number": "+13015551234", "client_id": "123"}}' | jq

# Test hybrid validation (both legacy and NEMT)
curl -s -X POST localhost:8000/api/validate/hybrid \
  -H 'content-type: application/json' \
  -d '{"payload": {"rider_name": "", "phone_number": "invalid", "client_id": "abc"}}' | jq

# Get validation metrics
curl -s localhost:8000/api/validate/metrics | jq

# Get configuration
curl -s localhost:8000/api/validate/config | jq
```

## Validation Modes

### Legacy Mode (`VALIDATION_MODE=legacy`)
- **Behavior**: Unchanged from existing system
- **Validation**: Legacy validation only
- **Impact**: Zero - existing behavior preserved
- **Use Case**: Production default, safe fallback

### Hybrid Mode (`VALIDATION_MODE=hybrid`)
- **Behavior**: Legacy validation decides success/failure
- **Validation**: Legacy primary + NEMT sidecar (logs only)
- **Impact**: Minimal - adds logging and monitoring
- **Use Case**: Testing, monitoring, gradual migration

### New Mode (`VALIDATION_MODE=new`)
- **Behavior**: NEMT validation with optional legacy fallback
- **Validation**: NEMT primary + legacy fallback if enabled
- **Impact**: Higher - uses new validation logic
- **Use Case**: Full migration, enhanced validation

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/validate/nemt` | POST | Pure NEMT validation |
| `/api/validate/hybrid` | POST | Both legacy and NEMT comparison |
| `/api/validate/legacy` | POST | Legacy validation simulation |
| `/api/validate/config` | GET | Current configuration |
| `/api/validate/metrics` | GET | Validation statistics |
| `/api/validate/health` | GET | System health check |
| `/docs` | GET | Interactive API documentation |

## Migration Runbook

### Phase 1: Parallel Implementation ✅
- [x] Create adapter layer for format conversion
- [x] Add feature flags for mode control
- [x] Implement side-by-side validation
- [x] Add comprehensive logging
- [x] Create test API endpoints
- [x] Add unit tests

### Phase 2: Gradual Migration ✅
**Function Tools Integration Complete**

The existing function tools (`collect_main_trip_payload` and `collect_return_trip_payload`) now use the new validation system while maintaining their external contracts.

```bash
# 1. Start in hybrid mode for monitoring
export VALIDATION_MODE=hybrid

# 2. Monitor metrics and logs
curl localhost:8000/api/validate/metrics

# 3. Gradually switch to new mode
export VALIDATION_MODE=new
export VALIDATION_FALLBACK=true

# 4. Monitor for issues, rollback if needed
export VALIDATION_MODE=legacy  # Instant rollback
```

**Phase 2 Behavior:**
- **Legacy Mode**: Unchanged behavior, legacy validation only
- **Hybrid Mode**: Legacy decides success/failure, NEMT runs sidecar for logging
- **New Mode**: NEMT validation first, fallback to legacy if enabled on failure

### Phase 3: Full Migration ✅
**Complete NEMT Schema Migration**

Legacy validation has been completely replaced with the unified NEMT schema (Pydantic v2).

**What Changed:**
- ✅ All function tools now use NEMT schema directly
- ✅ Legacy validation models and adapters removed
- ✅ Feature flags and fallback logic eliminated
- ✅ Unified error flow with `format_validation_error()`
- ✅ API endpoints simplified to use NEMT only
- ✅ Legacy code moved to `/legacy` folder for backup

**Current State:**
- **Single Source of Truth**: `app/schemas/nemt_trip.py`
- **Unified Validation**: All validation uses `try_validate()`
- **Consistent Errors**: All errors use `format_validation_error()`
- **Clean API**: Simplified endpoints with NEMT schema only

## Rollback Plan

### Emergency Rollback
If issues arise with the NEMT migration:

1. **Restore from backup**:
   ```bash
   git checkout v2-migration-backup
   ```

2. **Legacy code available**:
   - All legacy validation code is preserved in `/legacy` folder
   - Can be restored if needed for emergency rollback

3. **Zero-downtime rollback**:
   - Previous commit tagged as `v2-migration-backup`
   - Instant rollback capability maintained

## Current Status

### ✅ Migration Complete
- **Legacy validation removed**
- **NEMT schema is now default**
- **Endpoints unchanged**
- **Unified JSON error structure**

### 📊 Monitoring
```bash
# Check validation health
curl localhost:8000/api/validate/health

# Get validation metrics
curl localhost:8000/api/validate/metrics

# Test validation
curl -X POST localhost:8000/api/validate/nemt \
  -H "Content-Type: application/json" \
  -d @valid.json
```

## Testing

### Run Unit Tests
```bash
# Run NEMT schema tests
python -m pytest tests/test_nemt_trip.py -v

# Run validation endpoint tests
python -m pytest tests/test_validation_endpoints.py -v

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app.schemas
```

### Integration Testing
```bash
# Test NEMT validation
python -c "from app.schemas.nemt_trip import try_validate; print('NEMT OK')"

# Test API endpoints
curl -X POST localhost:8000/api/validate/nemt -H "Content-Type: application/json" -d @valid.json
curl -X POST localhost:8000/api/validate/nemt -H "Content-Type: application/json" -d @invalid.json

# Test function tools integration
python -c "from VoiceAgent3.IT_Curves_Bot.helper_functions import AgentSession; print('Function tools OK')"
```

## Support

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/validate/health
- **Configuration**: http://localhost:8000/api/validate/config
- **Metrics**: http://localhost:8000/api/validate/metrics

---

**✅ Migration Complete**: NEMT schema is now the single source of truth for all validation.
