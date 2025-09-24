from pydantic import BaseModel, Field
from typing import Annotated


# Pydantic model for return trip payload
class ReturnTripPayload(BaseModel):
    pickup_street_address: str = Field(
        ..., description="Pickup Street Address confirmed by rider. Do not include city, state, country")
    dropoff_street_address: str = Field(
        ..., description="Dropoff Street Address confirmed by rider. Do not include city, state, country")
    pickup_city: str = Field(...,
                             description="Pickup city confirmed by rider else ''")
    dropoff_city: str = Field(...,
                              description="Dropoff city confirmed by rider else ''")
    pickup_state: str = Field(...,
                              description="Pickup State confirmed by rider else ''")
    dropoff_state: str = Field(...,
                               description="Dropoff State confirmed by rider else ''")
    extra_details: str = Field(
        ..., description="Additional Notes if mentioned by rider for the driver else ''")
    phone_number: str = Field(...,
                              description="Phone number of rider else caller's phone number")
    client_id: str = Field(
        ..., description="Client Id else -1. I am applying python int() so generate value accordingly")
    funding_source_id: str = Field(
        ..., description="Funding Source Id else -1. I am applying python int() so generate value accordingly")
    rider_name: str = Field(..., description="Complete verified name of the rider if available. If you do not have verified name, use Complete Name of the Caller or rider used in conversation. If you do not have name in your memory ask it from caller.")
    payment_type_id: str = Field(
        ..., description="Payment Type Id else -1. I am applying python int() so generate value accordingly")
    copay_funding_source_id: str = Field(
        ..., description="Copay Funding Source Id else -1. I am applying python int() so generate value accordingly")
    copay_payment_type_id: str = Field(
        ..., description="Copay Payment Type Id else -1. I am applying python int() so generate value accordingly")
    booking_time: str = Field(..., description="Booking Time if mentioned by rider in this format 'Year-Month-Date HH:MM' for the driver else ''. If the rider wants to book for now, get current time from memory. if is_will_call is true, set it to date today.")
    pickup_lat: str = Field(
        ..., description="Pickup address latitude else 0. I am applying python float() so generate value accordingly")
    pickup_lng: str = Field(
        ..., description="Pickup address longitude else 0. I am applying python float() so generate value accordingly")
    dropoff_lat: str = Field(
        ..., description="Drop off address latitude else 0. I am applying python float() so generate value accordingly")
    dropoff_lng: str = Field(
        ..., description="Drop off address longitude else 0. I am applying python float() so generate value accordingly")
    rider_id: str = Field(..., description="Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to -1. I am applying python int() so generate value accordingly")
    number_of_wheel_chairs: str = Field(
        ..., description="Number of wheelchairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying python int() so generate value accordingly")
    number_of_passengers: str = Field(
        ..., description="Number of passengers. If rider mentioned more than 1 passenger, set accordingly otherwise set it to 1. I am applying python int() so generate value accordingly")
    family_id: str = Field(
        ..., description="Family Id else 0. I am applying python int() so generate value accordingly")
    is_schedule: str = Field(..., description="1 if the trip is scheduled for 20+ minutes from current time, also 1 if is_will_call true, else 0 if the trip is scheduled for now. I am applying python int() so generate value accordingly, or if")
    pickup_city_zip_code: str = Field(...,
                                      description="Pick Up City Zip Code else ''")
    dropoff_city_zip_code: str = Field(...,
                                       description="Drop Off City Zip Code else ''")
    rider_home_address: str = Field(
        ..., description="Home location of the rider present in the memory. If not available, set it to ''")
    rider_home_city: str = Field(
        ..., description="City of rider's home address. If not available, set it to ''")
    rider_home_state: str = Field(
        ..., description="State of rider's home address. If not available, set it to ''")
    home_phone: str = Field(...,
                            description="Rider's home phone no. If not available, set it to ''")
    office_phone: str = Field(
        ..., description="Rider's Office Phone no. if not available, set it to ''")
    total_passengers: int = Field(
        ..., description="total passenger count if not available, set it to 1")
    total_wheelchairs: int = Field(
        ..., description="total wheelchair count if not available, set it to 0")
    is_will_call: bool = Field(
        ..., description="true if booking time is not provided or booking time is will call else false")
    will_call_day: str = Field(..., description="Booking Date if mentioned by rider in this format 'Year-Month-Date 00:00:00' for the driver else get current date from memory, applicable only if is_will_call is true.")
    pickup_remarks: str = Field(
        ..., description="any remarks given explicitly for pickup address else ''")
    pickup_phone_number: str = Field(
        ..., description="if pickup phone number is explicitly provided else ''")
    dropoff_remarks: str = Field(
        ..., description="any remarks given explicitly for drop off address else ''")
    dropoff_phone_number: str = Field(
        ..., description="if drop off phone number is explicitly provided else ''")


class MainTripPayload(BaseModel):
    pickup_street_address: str
    dropoff_street_address: str
    pickup_city: str
    dropoff_city: str
    pickup_state: str
    dropoff_state: str
    extra_details: str
    phone_number: str
    client_id: str
    funding_source_id: str
    rider_name: str
    payment_type_id: str
    copay_funding_source_id: str
    copay_payment_type_id: str
    booking_time: str
    pickup_lat: str
    pickup_lng: str
    dropoff_lat: str
    dropoff_lng: str
    rider_id: str
    number_of_wheel_chairs: str
    number_of_passengers: str
    family_id: str
    is_schedule: str
    pickup_city_zip_code: str
    dropoff_city_zip_code: str
    rider_home_address: str
    rider_home_city: str
    rider_home_state: str
    home_phone: str
    office_phone: str
    total_passengers: int
    total_wheelchairs: int
    is_will_call: bool
    will_call_day: str
    pickup_remarks: str
    pickup_phone_number: str
    dropoff_remarks: str
    dropoff_phone_number: str


class RiderVerificationParams(BaseModel):
    rider_id: Annotated[str, Field(description="Rider Id, else -1.")]
    program_id: Annotated[str, Field(description="Program Id, else -1.")]


class ClientNameParams(BaseModel):
    caller_number: Annotated[str, Field(
        description="Rider Phone Number in digits")]
    family_id: Annotated[str, Field(
        description="Family id of the rider else 1. Only a number so that it can be converted into integer")]


class DistanceFareParams(BaseModel):
    pickup_latitude: Annotated[str, Field(
        description="Pickup Address Latitude in string. If not available, set it to 0.")]
    dropoff_latitude: Annotated[str, Field(
        description="Dropoff Address Latitude in string. If not available, set it to 0.")]
    pickup_longitude: Annotated[str, Field(
        description="Pickup Address Longitude in string. If not available, set it to 0.")]
    dropoff_longitude: Annotated[str, Field(
        description="Dropoff Address Longitude in string. If not available, set it to 0.")]
    number_of_wheel_chairs: Annotated[str, Field(
        description="Number of wheel chairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying python int() so generate value accordingly")]
    number_of_passengers: Annotated[str, Field(
        description="Number of passengers. If rider mentioned more than 1 passengers, set accordingly otherwise set it to 1. I am applying python int() so generate value accordingly")]
    rider_id: Annotated[str, Field(
        description="Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to 0. I am applying python int() so generate value accordingly")]


class AccountParams(BaseModel):
    account_: Annotated[str, Field(
        description="Account name provided by the rider")]
    payment_method: Annotated[str, Field(
        description="Payment method provided by the rider")]
