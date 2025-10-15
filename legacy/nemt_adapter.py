"""
NEMT Schema Adapter - Legacy to NEMT Conversion Layer

This module provides conversion functions between legacy Pydantic v1 models
and the new Pydantic v2 NEMT schema, enabling parallel validation without
breaking existing functionality.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple, Union
from datetime import datetime

from app.schemas.nemt_trip import (
    NEMTTripPayload,
    try_validate,
    format_validation_error,
    ValidationError
)


def from_legacy_to_nemt(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert legacy payload format to NEMT schema format.
    
    Args:
        legacy: Legacy payload dictionary (ReturnTripPayload or MainTripPayload format)
        
    Returns:
        Dict in NEMT schema format
    """
    # Extract common fields from legacy format
    nemt_data = {
        "generalInfo": {
            "CompleteUserName": legacy.get("rider_name", ""),
            "CreatedBy": "VoiceAgent System",
            "CreatedByAppID": 1,
            "CreatedUserId": 1001,
            "RequestAffiliateID": int(legacy.get("client_id", -1)) if legacy.get("client_id", "-1").isdigit() else 1,
            "ReturnDetailID": "",
            "FamilyID": int(legacy.get("family_id", 0)) if str(legacy.get("family_id", "0")).isdigit() else 0
        },
        "riderInfo": {
            "ID": int(legacy.get("rider_id", -1)) if str(legacy.get("rider_id", "-1")).isdigit() else 1,
            "PhoneNo": legacy.get("phone_number", ""),
            "PickupPerson": legacy.get("rider_name", ""),
            "DateOfBirth": "1980-01-01",  # Default - would need actual DOB in real system
            "RiderID": legacy.get("rider_id", ""),
            "RiderPassword": "",
            "MedicalID": f"MED_{legacy.get('rider_id', '001')}",
            "ClientAddress": legacy.get("rider_home_address", ""),
            "ClientCity": legacy.get("rider_home_city", ""),
            "ClientState": legacy.get("rider_home_state", "MD"),
            "ClientZip": legacy.get("pickup_city_zip_code", "21201")
        },
        "insuranceInfo": {
            "AgencyID": int(legacy.get("funding_source_id", -1)) if str(legacy.get("funding_source_id", "-1")).isdigit() else 1,
            "InsuranceID": 6001,  # Default insurance ID
            "CaseWorkerID": 7001,  # Default case worker
            "AuthID": f"AUTH_{legacy.get('rider_id', '001')}",
            "ServiceCodeID": "WHEELCHAIR" if int(legacy.get("number_of_wheel_chairs", "0")) > 0 else "AMBULATORY",
            "MedicalID": f"MED_{legacy.get('rider_id', '001')}"
        },
        "routeSettingInfo": {
            "TimeWindow": 30,
            "EndTimeWindow": 30,
            "MinRideTime": 15,
            "MaxRideTime": 120,
            "ServiceTimeAmb": 5,
            "ServiceTimeWC": 10 if int(legacy.get("number_of_wheel_chairs", "0")) > 0 else 0,
            "ApptTimeWindow": 15,
            "AdditionalSameLocAm": 0,
            "AdditionalSameLocWC": 0
        },
        "systemConfigInfo": {
            "DefaultCustomerShowPhoneNo": False,
            "IsSkipPaymentProcessOnSD": False,
            "Ta01": 0,
            "UseHTMLFormatEmail": True,
            "Web_Shuttle_SendEmailFromSASCode": False,
            "SRDuplicateCallDelay": 300,
            "ServiceHoursViolation": False
        }
    }
    
    return nemt_data


def from_nemt_to_legacy(model: NEMTTripPayload) -> Dict[str, Any]:
    """
    Convert NEMT schema model back to legacy format.
    
    Args:
        model: Validated NEMT schema model
        
    Returns:
        Dict in legacy format for backward compatibility
    """
    legacy_data = {
        "pickup_street_address": "",  # Not in NEMT schema
        "dropoff_street_address": "",  # Not in NEMT schema
        "pickup_city": "",
        "dropoff_city": "",
        "pickup_state": "",
        "dropoff_state": "",
        "extra_details": "",
        "phone_number": model.riderInfo.PhoneNo,
        "client_id": str(model.generalInfo.RequestAffiliateID),
        "funding_source_id": str(model.insuranceInfo.AgencyID),
        "rider_name": model.riderInfo.PickupPerson,
        "payment_type_id": "-1",
        "copay_funding_source_id": "-1",
        "copay_payment_type_id": "-1",
        "booking_time": "",
        "pickup_lat": "0",
        "pickup_lng": "0",
        "dropoff_lat": "0",
        "dropoff_lng": "0",
        "rider_id": str(model.riderInfo.ID),
        "number_of_wheel_chairs": "1" if model.insuranceInfo.ServiceCodeID == "WHEELCHAIR" else "0",
        "number_of_passengers": "1",
        "is_schedule": "0",
        "pickup_city_zip_code": model.riderInfo.ClientZip,
        "dropoff_city_zip_code": "",
        "rider_home_address": model.riderInfo.ClientAddress,
        "rider_home_city": model.riderInfo.ClientCity,
        "rider_home_state": model.riderInfo.ClientState.value,
        "home_phone": model.riderInfo.PhoneNo,
        "office_phone": "",
        "total_passengers": 1,
        "total_wheelchairs": 1 if model.insuranceInfo.ServiceCodeID == "WHEELCHAIR" else 0,
        "is_will_call": False,
        "will_call_day": "",
        "pickup_remarks": "",
        "pickup_phone_number": model.riderInfo.PhoneNo,
        "dropoff_remarks": "",
        "dropoff_phone_number": ""
    }
    
    return legacy_data


def validate_nemt_sidecar(data: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], None]]:
    """
    Validate data using NEMT schema as a sidecar validation.
    
    This function runs NEMT validation without affecting the main flow.
    Used for logging, monitoring, and gradual migration.
    
    Args:
        data: Payload data to validate (legacy format)
        
    Returns:
        Tuple of (success: bool, error_json: dict|None)
        - If validation succeeds: (True, None)
        - If validation fails: (False, error_dict)
    """
    try:
        # Convert legacy to NEMT format
        nemt_data = from_legacy_to_nemt(data)
        
        # Validate using NEMT schema
        ok, model, error = try_validate(nemt_data)
        
        if ok:
            return True, None
        else:
            return False, error
            
    except Exception as e:
        # Handle any conversion or validation errors
        error_dict = {
            "error": "ConversionError",
            "details": [{
                "loc": ["adapter"],
                "msg": f"Failed to convert or validate: {str(e)}",
                "type": "conversion_error"
            }]
        }
        return False, error_dict


def validate_nemt_direct(data: Dict[str, Any]) -> Tuple[bool, Union[NEMTTripPayload, None], Union[Dict[str, Any], None]]:
    """
    Direct NEMT validation without legacy conversion.
    
    Args:
        data: Data already in NEMT format
        
    Returns:
        Tuple of (success: bool, model: NEMTTripPayload|None, error: dict|None)
    """
    return try_validate(data)


# Legacy payload examples for testing
LEGACY_PAYLOAD_EXAMPLE = {
    "pickup_street_address": "123 Main St",
    "dropoff_street_address": "456 Oak Ave",
    "pickup_city": "Baltimore",
    "dropoff_city": "Annapolis",
    "pickup_state": "MD",
    "dropoff_state": "MD",
    "extra_details": "Wheelchair accessible",
    "phone_number": "+13015551234",
    "client_id": "2001",
    "funding_source_id": "5001",
    "rider_name": "John Doe",
    "payment_type_id": "1",
    "copay_funding_source_id": "-1",
    "copay_payment_type_id": "-1",
    "booking_time": "2024-01-15 10:00:00",
    "pickup_lat": "39.2904",
    "pickup_lng": "-76.6122",
    "dropoff_lat": "38.9784",
    "dropoff_lng": "-76.4922",
    "rider_id": "4001",
    "number_of_wheel_chairs": "1",
    "number_of_passengers": "1",
    "is_schedule": "1",
    "pickup_city_zip_code": "21201",
    "dropoff_city_zip_code": "21401",
    "rider_home_address": "789 Pine St",
    "rider_home_city": "Baltimore",
    "rider_home_state": "MD",
    "home_phone": "+13015551234",
    "office_phone": "",
    "total_passengers": 1,
    "total_wheelchairs": 1,
    "is_will_call": False,
    "will_call_day": "",
    "pickup_remarks": "Ring doorbell",
    "pickup_phone_number": "+13015551234",
    "dropoff_remarks": "Main entrance",
    "dropoff_phone_number": ""
}


# Exports
__all__ = [
    "from_legacy_to_nemt",
    "from_nemt_to_legacy", 
    "validate_nemt_sidecar",
    "validate_nemt_direct",
    "LEGACY_PAYLOAD_EXAMPLE"
]
