# NEMT Trip Schema Usage

## FastAPI Route Example

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas.nemt_trip import try_validate

app = FastAPI()

@app.post("/trips/validate")
def validate_trip(payload: dict):
    ok, model, err = try_validate(payload)
    if not ok:
        return JSONResponse(status_code=422, content=err)
    return {"ok": True, "trip_id": model.riderInfo.ID}
```

## Plain Python Usage

```python
from app.schemas.nemt_trip import validate_payload, try_validate, VALID_PAYLOAD_EXAMPLE

# Method 1: Direct validation (raises ValidationError)
try:
    trip = validate_payload(VALID_PAYLOAD_EXAMPLE)
    print(f"Valid trip: {trip.generalInfo.CompleteUserName}")
except ValidationError as e:
    print(f"Validation failed: {e}")

# Method 2: Safe validation with error handling
ok, model, error = try_validate(VALID_PAYLOAD_EXAMPLE)
if ok:
    print(f"Valid trip: {model.generalInfo.CompleteUserName}")
else:
    print(f"Validation errors: {error}")
```

