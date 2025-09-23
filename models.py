from pydantic import BaseModel, Field, field_validator, FieldValidationInfo
from typing import Annotated, Literal


# Pydantic model for return trip payload
class ReturnTripPayload(BaseModel):
    pickup_street_address: str = Field(
        ..., description="Pickup Street Address confirmed by rider. Do not include city, state, country")
    dropoff_street_address: str = Field(
        ..., description="Dropoff Street Address confirmed by rider. Do not include city, state, country")
    pickup_city: str = Field(
        default="", description="Pickup city confirmed by rider else ''")
    dropoff_city: str = Field(
        default="", description="Dropoff city confirmed by rider else ''")
    pickup_state: str = Field(
        default="", description="Pickup State confirmed by rider else ''")
    dropoff_state: str = Field(
        default="", description="Dropoff State confirmed by rider else ''")
    extra_details: str = Field(
        default="", description="Additional Notes if mentioned by rider for the driver else ''")
    phone_number: str = Field(...,
                              description="Phone number of rider else caller's phone number")
    client_id: str = Field(
        default="-1", description="Client Id else -1. I am applying python int() so generate value accordingly")
    funding_source_id: str = Field(
        default="-1", description="Funding Source Id else -1. I am applying python int() so generate value accordingly")
    rider_name: str = Field(..., description="Complete verified name of the rider if available. If you do not have verified name, use Complete Name of the Caller or rider used in conversation. If you do not have name in your memory ask it from caller.")
    payment_type_id: str = Field(
        default="-1", description="Payment Type Id else -1. I am applying python int() so generate value accordingly")
    copay_funding_source_id: str = Field(
        default="-1", description="Copay Funding Source Id else -1. I am applying python int() so generate value accordingly")
    copay_payment_type_id: str = Field(
        default="-1", description="Copay Payment Type Id else -1. I am applying python int() so generate value accordingly")
    booking_time: str = Field(
        default="", description="Booking Time if mentioned by rider in this format 'Year-Month-Date HH:MM' for the driver else ''. If the rider wants to book for now, get current time from memory. if is_will_call is true, set it to date today.")
    pickup_lat: str = Field(
        default="0", description="Pickup address latitude else 0. I am applying python float() so generate value accordingly")
    pickup_lng: str = Field(
        default="0", description="Pickup address longitude else 0. I am applying python float() so generate value accordingly")
    dropoff_lat: str = Field(
        default="0", description="Drop off address latitude else 0. I am applying python float() so generate value accordingly")
    dropoff_lng: str = Field(
        default="0", description="Drop off address longitude else 0. I am applying python float() so generate value accordingly")
    rider_id: str = Field(
        default="-1", description="Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to -1. I am applying python int() so generate value accordingly")
    number_of_wheel_chairs: str = Field(
        default="0", description="Number of wheelchairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying python int() so generate value accordingly")
    number_of_passengers: str = Field(
        default="1", description="Number of passengers. If rider mentioned more than 1 passenger, set accordingly otherwise set it to 1. I am applying python int() so generate value accordingly")
    family_id: str = Field(
        default="0", description="Family Id else 0. I am applying python int() so generate value accordingly")
    is_schedule: str = Field(
        default="0", description="1 if the trip is scheduled for 20+ minutes from current time, also 1 if is_will_call true, else 0 if the trip is scheduled for now. I am applying python int() so generate value accordingly")
    pickup_city_zip_code: str = Field(
        default="", description="Pick Up City Zip Code else ''")
    dropoff_city_zip_code: str = Field(
        default="", description="Drop Off City Zip Code else ''")
    rider_home_address: str = Field(
        default="", description="Home location of the rider present in the memory. If not available, set it to ''")
    rider_home_city: str = Field(
        default="", description="City of rider's home address. If not available, set it to ''")
    rider_home_state: str = Field(
        default="", description="State of rider's home address. If not available, set it to ''")
    home_phone: str = Field(
        default="", description="Rider's home phone no. If not available, set it to ''")
    office_phone: str = Field(
        default="", description="Rider's Office Phone no. if not available, set it to ''")
    total_passengers: int = Field(
        default=1, description="total passenger count if not available, set it to 1")
    total_wheelchairs: int = Field(
        default=0, description="total wheelchair count if not available, set it to 0")
    is_will_call: bool = Field(
        default=False, description="true if booking time is not provided or booking time is will call else false")
    will_call_day: str = Field(
        default="", description="Booking Date if mentioned by rider in this format 'Year-Month-Date 00:00:00' for the driver else get current date from memory, applicable only if is_will_call is true.")
    pickup_remarks: str = Field(
        default="", description="any remarks given explicitly for pickup address else ''")
    pickup_phone_number: str = Field(
        default="", description="if pickup phone number is explicitly provided else ''")
    dropoff_remarks: str = Field(
        default="", description="any remarks given explicitly for drop off address else ''")
    dropoff_phone_number: str = Field(
        default="", description="if drop off phone number is explicitly provided else ''")

    @field_validator('pickup_lat', 'dropoff_lat', 'pickup_lng', 'dropoff_lng', mode='before')
    def validate_coordinates(cls, v, info: FieldValidationInfo):
        """Validate coordinates are within valid ranges"""
        if v not in ["0", "0.0", ""]:
            try:
                float_val = float(v)
                if "lat" in info.field_name and (float_val < -90 or float_val > 90):
                    raise ValueError(
                        f'{info.field_name} must be between -90 and 90 degrees')
                if "lng" in info.field_name and (float_val < -180 or float_val > 180):
                    raise ValueError(
                        f'{info.field_name} must be between -180 and 180 degrees')
            except ValueError:
                raise ValueError(f'{info.field_name} must be a valid number')
        return v

    @field_validator('number_of_wheel_chairs', 'number_of_passengers', mode='before')
    def validate_counts(cls, v, info: FieldValidationInfo):
        """Validate passenger and wheelchair counts are non-negative"""
        if v not in ["", "0"]:
            try:
                int_val = int(v)
                if int_val < 0:
                    raise ValueError(f'{info.field_name} cannot be negative')
                if "passenger" in info.field_name and int_val == 0:
                    return "1"  # Default to 1 passenger if 0
            except ValueError:
                raise ValueError(f'{info.field_name} must be a valid number')
        elif "passenger" in info.field_name and v == "0":
            return "1"  # Default to 1 passenger
        return v

    @field_validator('total_passengers', 'total_wheelchairs', mode='after')
    def validate_total_counts(cls, v):
        """Validate total counts are non-negative integers"""
        if v < 0:
            raise ValueError('total count cannot be negative')
        # specific to passengers
        if v == 0 and 'passenger' in 'total_passengers':
            return 1  # Default to 1 passenger
        return v

    @field_validator('client_id', 'funding_source_id', 'payment_type_id', 'copay_funding_source_id',
                     'copay_payment_type_id', 'rider_id', 'family_id', mode='before')
    def validate_ids(cls, v):
        """Ensure IDs are either valid or -1/0 for defaults"""
        if v not in ["-1", "0", ""]:
            try:
                int_val = int(v)
            except ValueError:
                raise ValueError('ID fields must be valid numbers, -1, or 0')
        return v

    @field_validator('phone_number', 'home_phone', 'office_phone', 'pickup_phone_number', 'dropoff_phone_number', mode='before')
    def validate_phone_numbers(cls, v, info: FieldValidationInfo):
        """Basic validation for phone number format"""
        if v and v not in ["-1", "0", ""]:
            # Remove common separators and spaces
            cleaned = v.replace(' ', '').replace(
                '-', '').replace('(', '').replace(')', '').replace('+', '')
            # Check if the result contains only digits
            if not cleaned.isdigit():
                raise ValueError(
                    f'{info.field_name} should contain only digits and common separators')
            # Check reasonable length (most phone numbers are between 7 and 15 digits)
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValueError(
                    f'{info.field_name} should have a reasonable length (7-15 digits)')
        return v

    @field_validator('is_schedule', mode='before')
    def validate_schedule(cls, v):
        """Validate is_schedule is either 0 or 1"""
        if v not in ["0", "1", ""]:
            try:
                int_val = int(v)
                if int_val not in [0, 1]:
                    raise ValueError('is_schedule must be 0 or 1')
            except ValueError:
                raise ValueError('is_schedule must be 0 or 1')
        return v


class MainTripPayload(BaseModel):
    pickup_street_address: str = Field(
        ..., description="Pickup Street Address confirmed by rider")
    dropoff_street_address: str = Field(
        ..., description="Dropoff Street Address confirmed by rider")
    pickup_city: str = Field(
        default="", description="Pickup city confirmed by rider else ''")
    dropoff_city: str = Field(
        default="", description="Dropoff city confirmed by rider else ''")
    pickup_state: str = Field(
        default="", description="Pickup State confirmed by rider else ''")
    dropoff_state: str = Field(
        default="", description="Dropoff State confirmed by rider else ''")
    extra_details: str = Field(
        default="", description="Additional Notes if mentioned by rider for the driver else ''")
    phone_number: str = Field(...,
                              description="Phone number of rider else caller's phone number")
    client_id: str = Field(default="-1", description="Client Id else -1")
    funding_source_id: str = Field(
        default="-1", description="Funding Source Id else -1")
    rider_name: str = Field(...,
                            description="Complete verified name of the rider if available")
    payment_type_id: str = Field(
        default="-1", description="Payment Type Id else -1")
    copay_funding_source_id: str = Field(
        default="-1", description="Copay Funding Source Id else -1")
    copay_payment_type_id: str = Field(
        default="-1", description="Copay Payment Type Id else -1")
    booking_time: str = Field(
        default="", description="Booking Time if mentioned by rider in format 'Year-Month-Date HH:MM'")
    pickup_lat: str = Field(
        default="0", description="Pickup address latitude else 0")
    pickup_lng: str = Field(
        default="0", description="Pickup address longitude else 0")
    dropoff_lat: str = Field(
        default="0", description="Drop off address latitude else 0")
    dropoff_lng: str = Field(
        default="0", description="Drop off address longitude else 0")
    rider_id: str = Field(
        default="-1", description="Rider Id if available else -1")
    number_of_wheel_chairs: str = Field(
        default="0", description="Number of wheelchairs if required by rider else 0")
    number_of_passengers: str = Field(
        default="1", description="Number of passengers, default to 1")
    family_id: str = Field(default="0", description="Family Id else 0")
    is_schedule: str = Field(
        default="0", description="1 if the trip is scheduled for later, 0 if for now")
    pickup_city_zip_code: str = Field(
        default="", description="Pick Up City Zip Code else ''")
    dropoff_city_zip_code: str = Field(
        default="", description="Drop Off City Zip Code else ''")
    rider_home_address: str = Field(
        default="", description="Home location of the rider if available else ''")
    rider_home_city: str = Field(
        default="", description="City of rider's home address if available else ''")
    rider_home_state: str = Field(
        default="", description="State of rider's home address if available else ''")
    home_phone: str = Field(
        default="", description="Rider's home phone no if available else ''")
    office_phone: str = Field(
        default="", description="Rider's Office Phone no if available else ''")
    total_passengers: int = Field(
        default=1, description="Total passenger count, default to 1")
    total_wheelchairs: int = Field(
        default=0, description="Total wheelchair count, default to 0")
    is_will_call: bool = Field(
        default=False, description="True if booking time is not provided")
    will_call_day: str = Field(
        default="", description="Booking Date in format 'Year-Month-Date 00:00:00' if is_will_call is true")
    pickup_remarks: str = Field(
        default="", description="Any remarks for pickup address else ''")
    pickup_phone_number: str = Field(
        default="", description="Pickup phone number if explicitly provided else ''")
    dropoff_remarks: str = Field(
        default="", description="Any remarks for drop off address else ''")
    dropoff_phone_number: str = Field(
        default="", description="Drop off phone number if explicitly provided else ''")

    @field_validator('pickup_lat', 'dropoff_lat', 'pickup_lng', 'dropoff_lng', mode='before')
    def validate_coordinates(cls, v, info: FieldValidationInfo):
        """Validate coordinates are within valid ranges"""
        if v not in ["0", "0.0", ""]:
            try:
                float_val = float(v)
                if "lat" in info.field_name and (float_val < -90 or float_val > 90):
                    raise ValueError(
                        f'{info.field_name} must be between -90 and 90 degrees')
                if "lng" in info.field_name and (float_val < -180 or float_val > 180):
                    raise ValueError(
                        f'{info.field_name} must be between -180 and 180 degrees')
            except ValueError:
                raise ValueError(f'{info.field_name} must be a valid number')
        return v

    @field_validator('number_of_wheel_chairs', 'number_of_passengers', 'total_passengers', 'total_wheelchairs', mode='before')
    def validate_counts(cls, v, info: FieldValidationInfo):
        """Validate passenger and wheelchair counts are non-negative"""
        if isinstance(v, str) and v not in ["", "0"]:
            try:
                int_val = int(v)
                if int_val < 0:
                    raise ValueError(f'{info.field_name} cannot be negative')
                if "passenger" in info.field_name and int_val == 0:
                    # Default to 1 passenger
                    return "1" if isinstance(v, str) else 1
            except ValueError:
                raise ValueError(f'{info.field_name} must be a valid number')
        elif isinstance(v, int) and v < 0:
            raise ValueError(f'{info.field_name} cannot be negative')
        elif isinstance(v, int) and "passenger" in info.field_name and v == 0:
            return 1  # Default to 1 passenger
        return v

    @field_validator('client_id', 'funding_source_id', 'payment_type_id', 'copay_funding_source_id',
                     'copay_payment_type_id', 'rider_id', 'family_id', mode='before')
    def validate_ids(cls, v):
        """Ensure IDs are either valid or -1/0 for defaults"""
        if v not in ["-1", "0", ""]:
            try:
                int_val = int(v)
            except ValueError:
                raise ValueError('ID fields must be valid numbers, -1, or 0')
        return v

    @field_validator('phone_number', 'home_phone', 'office_phone', 'pickup_phone_number', 'dropoff_phone_number', mode='before')
    def validate_phone_numbers(cls, v, info: FieldValidationInfo):
        """Basic validation for phone number format"""
        if v and v not in ["-1", "0", ""]:
            # Remove common separators and spaces
            cleaned = v.replace(' ', '').replace(
                '-', '').replace('(', '').replace(')', '').replace('+', '')
            # Check if the result contains only digits
            if not cleaned.isdigit():
                raise ValueError(
                    f'{info.field_name} should contain only digits and common separators')
            # Check reasonable length (most phone numbers are between 7 and 15 digits)
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValueError(
                    f'{info.field_name} should have a reasonable length (7-15 digits)')
        return v


class RiderVerificationParams(BaseModel):
    rider_id: Annotated[str, Field(
        description="Rider Id if provided, else defaults to '-1'")] = "-1"
    program_id: Annotated[str, Field(
        description="Program Id if provided, else defaults to '-1'")] = "-1"

    @field_validator('rider_id', 'program_id')
    def validate_ids(cls, v):
        """If no value is explicitly provided, ensure we return '-1'"""
        if not v or v.strip() == "":
            return "-1"
        return v


class ClientNameParams(BaseModel):
    caller_number: Annotated[str, Field(
        description="Rider Phone Number in digits")]
    family_id: Annotated[str, Field(
        description="Family id of the rider else 1. Only a number so that it can be converted into integer")]


class DistanceFareParams(BaseModel):
    pickup_latitude: Annotated[str, Field(
        description="Pickup Address Latitude in string. If not available, set it to 0. Should represent a value between -90 and 90.")]
    dropoff_latitude: Annotated[str, Field(
        description="Dropoff Address Latitude in string. If not available, set it to 0. Should represent a value between -90 and 90.")]
    pickup_longitude: Annotated[str, Field(
        description="Pickup Address Longitude in string. If not available, set it to 0. Should represent a value between -180 and 180.")]
    dropoff_longitude: Annotated[str, Field(
        description="Dropoff Address Longitude in string. If not available, set it to 0. Should represent a value between -180 and 180.")]
    number_of_wheel_chairs: Annotated[str, Field(
        description="Number of wheel chairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying python int() so generate value accordingly")]
    number_of_passengers: Annotated[str, Field(
        description="Number of passengers. If rider mentioned more than 1 passengers, set accordingly otherwise set it to 1. I am applying python int() so generate value accordingly")]
    rider_id: Annotated[str, Field(
        description="Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to 0. I am applying python int() so generate value accordingly")]

    @field_validator('pickup_latitude', 'dropoff_latitude')
    def validate_latitude(cls, v):
        """Validate latitude values are within valid range"""
        if v != "0" and v != "0.0":
            try:
                float_v = float(v)
                if float_v < -90 or float_v > 90:
                    raise ValueError(
                        'Latitude must be between -90 and 90 degrees')
            except ValueError:
                raise ValueError('Latitude must be a valid number')
        return v

    @field_validator('pickup_longitude', 'dropoff_longitude')
    def validate_longitude(cls, v):
        """Validate longitude values are within valid range"""
        if v != "0" and v != "0.0":
            try:
                float_v = float(v)
                if float_v < -180 or float_v > 180:
                    raise ValueError(
                        'Longitude must be between -180 and 180 degrees')
            except ValueError:
                raise ValueError('Longitude must be a valid number')
        return v

    def has_valid_coordinates(self) -> bool:
        """Check if both pickup and dropoff coordinates are provided (non-zero)"""
        return (
            self.pickup_latitude not in ["0", "0.0", ""] and
            self.pickup_longitude not in ["0", "0.0", ""] and
            self.dropoff_latitude not in ["0", "0.0", ""] and
            self.dropoff_longitude not in ["0", "0.0", ""]
        )

    def get_pickup_coordinates(self) -> tuple[str, str]:
        """Get pickup coordinates as a tuple (lat, lng)"""
        return (self.pickup_latitude, self.pickup_longitude)

    def get_dropoff_coordinates(self) -> tuple[str, str]:
        """Get dropoff coordinates as a tuple (lat, lng)"""
        return (self.dropoff_latitude, self.dropoff_longitude)


class AccountParams(BaseModel):
    account_: Annotated[str, Field(
        description="Account name provided by the rider")]
    payment_method: Annotated[Literal["card", "cash"], Field(
        description="Payment method provided by the rider (card or cash)")]
