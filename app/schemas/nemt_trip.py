"""
NEMT Trip Payload Schema - Pydantic v2 Implementation

A comprehensive schema for Non-Emergency Medical Transportation (NEMT) trip payloads
with business rule validation, cross-field dependencies, and error handling.

Usage:
    from app.schemas.nemt_trip import validate_payload, try_validate, NEMTTripPayload
    
    # Validate and get model
    payload = validate_payload(data)
    
    # Try validation with error handling
    ok, model, error = try_validate(data)
    if not ok:
        return JSONResponse(status_code=422, content=error)

Examples:
    # Valid payload
    valid_data = VALID_PAYLOAD_EXAMPLE
    
    # Invalid payload
    invalid_data = INVALID_PAYLOAD_EXAMPLE
    
    ok, model, error = try_validate(invalid_data)
    print(error)  # Shows validation errors in spec format
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    conint,
    field_validator,
    model_validator,
)


# Type Aliases
PhoneStr = str
ZipCodeStr = str
StateCodeStr = str
AgeInt = int


# Enumerations & Codebooks
class USPSState(str, Enum):
    """USPS 2-letter state codes"""
    AL = "AL"  # Alabama
    AK = "AK"  # Alaska
    AZ = "AZ"  # Arizona
    AR = "AR"  # Arkansas
    CA = "CA"  # California
    CO = "CO"  # Colorado
    CT = "CT"  # Connecticut
    DE = "DE"  # Delaware
    FL = "FL"  # Florida
    GA = "GA"  # Georgia
    HI = "HI"  # Hawaii
    ID = "ID"  # Idaho
    IL = "IL"  # Illinois
    IN = "IN"  # Indiana
    IA = "IA"  # Iowa
    KS = "KS"  # Kansas
    KY = "KY"  # Kentucky
    LA = "LA"  # Louisiana
    ME = "ME"  # Maine
    MD = "MD"  # Maryland
    MA = "MA"  # Massachusetts
    MI = "MI"  # Michigan
    MN = "MN"  # Minnesota
    MS = "MS"  # Mississippi
    MO = "MO"  # Missouri
    MT = "MT"  # Montana
    NE = "NE"  # Nebraska
    NV = "NV"  # Nevada
    NH = "NH"  # New Hampshire
    NJ = "NJ"  # New Jersey
    NM = "NM"  # New Mexico
    NY = "NY"  # New York
    NC = "NC"  # North Carolina
    ND = "ND"  # North Dakota
    OH = "OH"  # Ohio
    OK = "OK"  # Oklahoma
    OR = "OR"  # Oregon
    PA = "PA"  # Pennsylvania
    RI = "RI"  # Rhode Island
    SC = "SC"  # South Carolina
    SD = "SD"  # South Dakota
    TN = "TN"  # Tennessee
    TX = "TX"  # Texas
    UT = "UT"  # Utah
    VT = "VT"  # Vermont
    VA = "VA"  # Virginia
    WA = "WA"  # Washington
    WV = "WV"  # West Virginia
    WI = "WI"  # Wisconsin
    WY = "WY"  # Wyoming
    DC = "DC"  # District of Columbia


class ServiceCodeID(str, Enum):
    """Service code types for NEMT"""
    AMBULATORY = "AMBULATORY"
    WHEELCHAIR = "WHEELCHAIR"
    STRETCHER = "STRETCHER"
    BARIATRIC = "BARIATRIC"


# Helper Validators
def validate_phone_e164(value: str) -> PhoneStr:
    """Validate E.164 phone format"""
    if not value:
        raise ValueError("Phone number cannot be empty")
    
    # E.164 format: + followed by 7-15 digits total
    # Must start with + and have country code (1-3 digits) + number (4-12 digits)
    pattern = r'^\+[1-9]\d{6,14}$'
    if not re.match(pattern, value):
        raise ValueError("Must be E.164 format with 7-15 digits total (+13015551234)")
    
    # Additional check: total length should be 8-16 characters (+ plus 7-15 digits)
    if len(value) < 8 or len(value) > 16:
        raise ValueError("Phone number must be 7-15 digits after + (total 8-16 characters)")
    
    # Practical validation: require at least 10 digits total for real phone numbers
    digits_only = value[1:]  # Remove the +
    if len(digits_only) < 10:
        raise ValueError("Phone number must have at least 10 digits total (including country code)")
    
    return value


def validate_zip_code(value: str, state: Optional[str] = None) -> ZipCodeStr:
    """Validate US ZIP code format"""
    if not value:
        raise ValueError("ZIP code cannot be empty")
    
    # US ZIP format: 12345 or 12345-6789
    pattern = r'^\d{5}(-\d{4})?$'
    if not re.match(pattern, value):
        raise ValueError("Must be US ZIP format (12345 or 12345-6789)")
    
    # Maryland ZIP code validation (placeholder - would need actual ZIP ranges)
    if state == "MD":
        # Placeholder: MD ZIP codes typically start with 206-219
        zip_prefix = value[:3]
        if not (206 <= int(zip_prefix) <= 219):
            raise ValueError("ZIP code does not match Maryland range")
    
    return value


def validate_age_bounds(value: date) -> date:
    """Validate age is within reasonable bounds (0-120 years)"""
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    
    if not (0 <= age <= 120):
        raise ValueError("Age must be between 0 and 120 years")
    
    return value


def validate_ride_time_bounds(value: int, min_ride_time: Optional[int] = None) -> int:
    """Validate ride time constraints"""
    if value < 0:
        raise ValueError("Ride time cannot be negative")
    
    if value > 1440:  # 24 hours in minutes
        raise ValueError("Ride time cannot exceed 1440 minutes (24 hours)")
    
    if min_ride_time is not None and value < min_ride_time:
        raise ValueError("Must be >= MinRideTime")
    
    return value


def validate_service_time_wheelchair(value: int, service_code: Optional[str] = None) -> int:
    """Validate wheelchair service time"""
    if value < 0:
        raise ValueError("Service time cannot be negative")
    
    if value > 1440:  # 24 hours in minutes
        raise ValueError("Service time cannot exceed 1440 minutes (24 hours)")
    
    # If service code indicates wheelchair, service time must be > 0
    if service_code == ServiceCodeID.WHEELCHAIR and value <= 0:
        raise ValueError("ServiceTimeWC must be > 0 for wheelchair service")
    
    return value


# Schema Models
class GeneralInfo(BaseModel):
    """General trip information"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    CompleteUserName: str = Field(..., min_length=1, max_length=255)
    CreatedBy: str = Field(..., min_length=1, max_length=255)
    CreatedByAppID: conint(ge=0) = 0  # 0 = system default
    CreatedUserId: conint(ge=0) = 0   # 0 = system user
    RequestAffiliateID: conint(ge=0)
    ReturnDetailID: str = ""  # Empty string allowed
    FamilyID: conint(ge=0) = 0
    
    @model_validator(mode='after')
    def validate_user_dependencies(self) -> 'GeneralInfo':
        """Cross-field validation: CompleteUserName and CreatedUserId dependency"""
        # Placeholder rule: If CreatedUserId is 0, CompleteUserName should be system default
        # This is a business rule that may need client confirmation
        if self.CreatedUserId == 0 and self.CompleteUserName.lower() not in ['system', 'admin']:
            # Comment: May need to adjust this rule based on client requirements
            pass
        return self


class RiderInfo(BaseModel):
    """Rider information and demographics"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    ID: conint(ge=0)
    PhoneNo: PhoneStr
    PickupPerson: str = Field(..., min_length=1, max_length=255)
    DateOfBirth: date
    RiderID: str = Field(..., min_length=1, max_length=50)
    RiderPassword: str = ""  # Empty = no login access
    MedicalID: str = Field(..., min_length=1, max_length=50)  # MedicalID/MedicalId unified
    ClientAddress: str = Field(..., min_length=1, max_length=500)
    ClientCity: str = Field(..., min_length=1, max_length=100)
    ClientState: USPSState
    ClientZip: ZipCodeStr
    
    @field_validator('PhoneNo')
    @classmethod
    def validate_phone(cls, v: str) -> PhoneStr:
        return validate_phone_e164(v)
    
    @field_validator('DateOfBirth')
    @classmethod
    def validate_dob(cls, v: Union[str, date]) -> date:
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)  # YYYY-MM-DD format
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return validate_age_bounds(v)
    
    @field_validator('ClientZip')
    @classmethod
    def validate_zip(cls, v: str) -> ZipCodeStr:
        return validate_zip_code(v)
    
    @model_validator(mode='after')
    def validate_state_zip_coherence(self) -> 'RiderInfo':
        """Validate state and ZIP code coherence"""
        validate_zip_code(self.ClientZip, self.ClientState.value)
        return self


class InsuranceInfo(BaseModel):
    """Insurance and authorization information"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    AgencyID: conint(ge=0)
    InsuranceID: conint(ge=0)  # 0 = no insurance
    CaseWorkerID: conint(ge=0) = 0
    AuthID: str = ""  # Required if InsuranceID != 0
    ServiceCodeID: ServiceCodeID
    MedicalID: str = Field(..., min_length=1, max_length=50)
    
    @model_validator(mode='after')
    def validate_insurance_dependencies(self) -> 'InsuranceInfo':
        """Validate insurance dependencies"""
        if self.InsuranceID != 0:
            if not self.AuthID:
                raise ValueError("AuthID is required when InsuranceID is not 0")
            # ServiceCodeID is already required via field definition
        return self


class RouteSettingInfo(BaseModel):
    """Route and timing configuration"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    TimeWindow: conint(ge=0, le=1440) = 30  # minutes
    EndTimeWindow: conint(ge=0, le=1440) = 30  # minutes
    MinRideTime: conint(ge=0, le=1440) = 15  # minutes
    MaxRideTime: conint(ge=0, le=1440) = 120  # minutes
    ServiceTimeAmb: conint(ge=0, le=1440) = 5  # minutes
    ServiceTimeWC: conint(ge=0, le=1440) = 10  # minutes
    ApptTimeWindow: conint(ge=0, le=1440) = 15  # minutes
    AdditionalSameLocAm: conint(ge=0, le=1440) = 0  # minutes
    AdditionalSameLocWC: conint(ge=0, le=1440) = 0  # minutes
    
    @model_validator(mode='after')
    def validate_ride_time_bounds(self) -> 'RouteSettingInfo':
        """Validate ride time relationships"""
        if self.MaxRideTime < self.MinRideTime:
            raise ValueError("MaxRideTime must be >= MinRideTime")
        return self
    
    @field_validator('ServiceTimeWC')
    @classmethod
    def validate_wheelchair_service_time(cls, v: int) -> int:
        return validate_service_time_wheelchair(v)


class SystemConfigInfo(BaseModel):
    """System configuration settings"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    DefaultCustomerShowPhoneNo: bool = False
    IsSkipPaymentProcessOnSD: bool = False
    Ta01: conint(ge=0) = 0
    UseHTMLFormatEmail: bool = True
    Web_Shuttle_SendEmailFromSASCode: bool = False
    SRDuplicateCallDelay: conint(ge=0, le=3600) = 300  # seconds, max 1 hour
    ServiceHoursViolation: bool = False
    
    @model_validator(mode='after')
    def validate_service_hours_config(self) -> 'SystemConfigInfo':
        """Validate service hours configuration"""
        if self.ServiceHoursViolation:
            # Placeholder: Would include hours window configuration
            # This would need additional fields for start/end hours
            pass
        return self


class NEMTTripPayload(BaseModel):
    """Complete NEMT Trip Payload Schema"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=False, validate_assignment=True)
    
    # Optional schema version for future compatibility
    schemaVersion: Optional[str] = None
    
    generalInfo: GeneralInfo
    riderInfo: RiderInfo
    insuranceInfo: InsuranceInfo
    routeSettingInfo: RouteSettingInfo
    systemConfigInfo: SystemConfigInfo
    
    @model_validator(mode='after')
    def validate_cross_section_dependencies(self) -> 'NEMTTripPayload':
        """Validate dependencies across different sections"""
        # Ensure wheelchair service time is properly set if service code is wheelchair
        if (self.insuranceInfo.ServiceCodeID == ServiceCodeID.WHEELCHAIR and 
            self.routeSettingInfo.ServiceTimeWC <= 0):
            raise ValueError("ServiceTimeWC must be > 0 for wheelchair service")
        
        return self


# Error Handling
def format_validation_error(error: ValidationError) -> Dict[str, Any]:
    """Convert Pydantic ValidationError to spec-compliant error format"""
    details = []
    
    for err in error.errors():
        details.append({
            "loc": list(err["loc"]),
            "msg": err["msg"],
            "type": err["type"]
        })
    
    return {
        "error": "ValidationError",
        "details": details
    }


# Validation Functions
def validate_payload(data: Dict[str, Any]) -> NEMTTripPayload:
    """Validate payload and return NEMTTripPayload model"""
    return NEMTTripPayload.model_validate(data)


def try_validate(data: Dict[str, Any]) -> Tuple[bool, Optional[NEMTTripPayload], Optional[Dict[str, Any]]]:
    """Try to validate payload, return (success, model, error) tuple"""
    try:
        model = validate_payload(data)
        return True, model, None
    except ValidationError as e:
        return False, None, format_validation_error(e)


# Example Payloads for Testing
VALID_PAYLOAD_EXAMPLE = {
    "schemaVersion": "1.0",
    "generalInfo": {
        "CompleteUserName": "John Doe",
        "CreatedBy": "System Admin",
        "CreatedByAppID": 1,
        "CreatedUserId": 1001,
        "RequestAffiliateID": 2001,
        "ReturnDetailID": "",
        "FamilyID": 3001
    },
    "riderInfo": {
        "ID": 4001,
        "PhoneNo": "+13015551234",
        "PickupPerson": "Jane Smith",
        "DateOfBirth": "1980-05-15",
        "RiderID": "RIDER001",
        "RiderPassword": "",
        "MedicalID": "MED001",
        "ClientAddress": "123 Main St",
        "ClientCity": "Baltimore",
        "ClientState": "MD",
        "ClientZip": "21201"
    },
    "insuranceInfo": {
        "AgencyID": 5001,
        "InsuranceID": 6001,
        "CaseWorkerID": 7001,
        "AuthID": "AUTH001",
        "ServiceCodeID": "AMBULATORY",
        "MedicalID": "MED001"
    },
    "routeSettingInfo": {
        "TimeWindow": 30,
        "EndTimeWindow": 30,
        "MinRideTime": 15,
        "MaxRideTime": 120,
        "ServiceTimeAmb": 5,
        "ServiceTimeWC": 10,
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

INVALID_PAYLOAD_EXAMPLE = {
    "generalInfo": {
        "CompleteUserName": "",  # Invalid: empty name
        "CreatedBy": "System Admin",
        "CreatedByAppID": -1,  # Invalid: negative ID
        "CreatedUserId": 1001,
        "RequestAffiliateID": 2001,
        "ReturnDetailID": "",
        "FamilyID": 3001
    },
    "riderInfo": {
        "ID": 4001,
        "PhoneNo": "3015551234",  # Invalid: not E.164 format
        "PickupPerson": "Jane Smith",
        "DateOfBirth": "1800-01-01",  # Invalid: age > 120
        "RiderID": "RIDER001",
        "RiderPassword": "",
        "MedicalID": "MED001",
        "ClientAddress": "123 Main St",
        "ClientCity": "Baltimore",
        "ClientState": "MD",
        "ClientZip": "00000"  # Invalid: not valid MD ZIP
    },
    "insuranceInfo": {
        "AgencyID": 5001,
        "InsuranceID": 6001,
        "CaseWorkerID": 7001,
        "AuthID": "",  # Invalid: required when InsuranceID != 0
        "ServiceCodeID": "WHEELCHAIR",
        "MedicalID": "MED001"
    },
    "routeSettingInfo": {
        "TimeWindow": 30,
        "EndTimeWindow": 30,
        "MinRideTime": 120,  # Invalid: > MaxRideTime
        "MaxRideTime": 60,
        "ServiceTimeAmb": 5,
        "ServiceTimeWC": 0,  # Invalid: must be > 0 for wheelchair service
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


# Exports
__all__ = [
    "NEMTTripPayload",
    "GeneralInfo",
    "RiderInfo", 
    "InsuranceInfo",
    "RouteSettingInfo",
    "SystemConfigInfo",
    "USPSState",
    "ServiceCodeID",
    "validate_payload",
    "try_validate",
    "format_validation_error",
    "VALID_PAYLOAD_EXAMPLE",
    "INVALID_PAYLOAD_EXAMPLE"
]


# Self-test
if __name__ == "__main__":
    print("🧪 NEMT Trip Schema Self-Test")
    print("=" * 50)
    
    # Test valid payload
    print("\n✅ Testing valid payload...")
    ok, model, error = try_validate(VALID_PAYLOAD_EXAMPLE)
    if ok:
        print(f"✅ Valid payload passed: {model.generalInfo.CompleteUserName}")
    else:
        print(f"❌ Valid payload failed: {error}")
    
    # Test invalid payload
    print("\n❌ Testing invalid payload...")
    ok, model, error = try_validate(INVALID_PAYLOAD_EXAMPLE)
    if not ok:
        print(f"✅ Invalid payload correctly rejected with {len(error['details'])} errors:")
        for detail in error['details'][:3]:  # Show first 3 errors
            print(f"  - {detail['loc']}: {detail['msg']}")
    else:
        print("❌ Invalid payload incorrectly accepted")
    
    print("\n🎉 Self-test completed!")
