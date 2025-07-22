from livekit.agents import llm  # type: ignore
import asyncio
import os
import re
import wave
from twilio.rest import Client
from livekit import rtc
from pathlib import Path
from datetime import datetime
import json
import requests
from typing import Annotated
import aiohttp
from aiohttp import BasicAuth
from openai import AsyncOpenAI
from dotenv import load_dotenv
from livekit.agents import Agent, function_tool
import logging
from side_functions import *
import logging
# Load variables from .env file
load_dotenv()

App_Directory = Path(__file__).parent

# Twilio credentials (from environment)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

MUSIC_PATH = os.path.join(App_Directory, "music.wav")

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Assistant(Agent):
    def __init__(self, call_sid=None, room=None, affiliate_id=None, instructions=None, main_leg=None, return_leg=None):
        """Initialize the assistant with a call SID and LiveKit room."""
        self.call_sid = call_sid  # Store the call SID for music control
        self.room = room  # Store the LiveKit room instance
        self.stop_music = False  # Flag to stop music
        self.affiliate_id = affiliate_id
        self.main_leg = main_leg
        self.return_leg = return_leg
        super().__init__(instructions=instructions)  # Initialize Agent with the instructions argument

    async def Play_Music(self):
        """Function to publish an audio track in the LiveKit room with stoppable music."""
        if not self.room:
            return "No active room to play music."

        try:
            print(f"🎵 Publishing music track in the LiveKit room...")
            self.stop_music = False  # Reset stop flag

            # Open the WAV file
            with wave.open(MUSIC_PATH, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                num_channels = wav_file.getnchannels()
                samples_per_channel = 480  # 10ms of audio at 48kHz

                # Create an AudioSource
                source = rtc.AudioSource(sample_rate, num_channels)
                audio_track = rtc.LocalAudioTrack.create_audio_track("music", source)

                # Publish the track to the room
                await self.room.local_participant.publish_track(audio_track)

                # Read and publish audio frames while checking stop condition
                while not self.stop_music:
                    frames = wav_file.readframes(samples_per_channel)
                    if not frames:
                        break  # Stop when no more frames

                    # Create an AudioFrame
                    audio_frame = rtc.AudioFrame(
                        data=frames,
                        sample_rate=sample_rate,
                        num_channels=num_channels,
                        samples_per_channel=len(frames) // (2 * num_channels)  # 2 bytes per sample (16-bit audio)
                    )

                    # Capture the frame
                    await source.capture_frame(audio_frame)

                    # Sleep to simulate real-time streaming
                    await asyncio.sleep(samples_per_channel / sample_rate)

            return "Music is now playing in the room."
        except Exception as e:
            print(f"\n\nError publishing music: {e}\n\n")
            return "Failed to play music."

    async def Stop_Music(self):
        """Function to stop playing music in the LiveKit room."""
        if not self.room:
            return "No active room to stop music."

        try:
            print("🛑 Stopping music track in the LiveKit room...")
            self.stop_music = True  # Set flag to stop music

            return "Music has been stopped."
        except Exception as e:
            print(f"\n\nError stopping music: {e}\n\n")
            return "Failed to stop music."
    
    @function_tool()
    async def Close_Call(self):
        """Function to end Twilio call and disconnect from the LiveKit room."""
        print(f"\n\n\ncalled close call function\n\n\n")
        await self.session.say('Thank you for reaching out. Have a great day!')
        
        # Step 1: End the Twilio call
        call_closed_msg = "No active call found."
        if self.call_sid:
            try:
                print(f"Requested Call Ending for Call SID: {self.call_sid}")
                TWILIO_CLIENT.calls(self.call_sid).update(status="completed")
                call_closed_msg = f"Call has been ended successfully."
            except Exception as e:
                call_closed_msg = f"Failed to end call: {str(e)}"

        # Step 2: Disconnect the LiveKit room
        room_closed_msg = "No active room found."
        try:
            if self.room and hasattr(self.room, "disconnect"):
                print(f"Disconnecting room: {self.room.name}")
                await self.room.disconnect()
                room_closed_msg = f"Room disconnected successfully."
        except Exception as e:
            room_closed_msg = f"Error disconnecting room: {str(e)}"

        return f"{call_closed_msg} {room_closed_msg}"

        
    @function_tool()
    async def get_client_name(self,
        caller_number: str, 
        family_id: str,                     
        ):
        """Function to get Rider Profile
        Args:
            caller_number: Rider Phone Number in digits
            family_id: Family id of the rider else 1. Only a number so that it can be converted into integer"""

        print(f"\n\nCalled get_client_name function\n\n")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        print(f"caller number: {caller_number}")
        print(f"family_id: {family_id}")

        try:

            # Define the API endpoint
            url = os.getenv("SEARCH_CLIENT_DATA_API")

            phone_number = await extract_phone_number(caller_number)

            # Create the payload (request body)
            payload = {
                "searchCriteria": "CustomerPhone",
                "searchText": phone_number,
                "bActiveRecords": True,
                "iATSPID": int(self.affiliate_id),
                "iDTSPID": int(family_id)
            }

            # Define the headers
            headers = {
                "Content-Type": "application/json",  
            }

            print(f"\n\nPayload sent by LLM: {payload}\n\n")

            # Step 3: Send the data to the API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response = await response.json()

        except Exception as e:
            print(f"\n\nError occured in getting rider profile: {e}\n\n")
            pass
        
        result = {}
        rider_count = 0
        
        try:
            if response["responseCode"] == 200: 
                client_object = response["responseJSON"]
                # print(type(client_object))
                client_list = json.loads(client_object)
                for i, client in enumerate(client_list, 1):
                    name = (client['FirstName'] + ' ' + client['LastName']).strip()
                    client_id = client.get('Id', 0)
                    number_of_existing_trips = await get_Existing_Trips_Number(client_id, self.affiliate_id)

                    medical_id_raw = client.get("MedicalId", "")
                    if medical_id_raw and str(medical_id_raw).isdigit():
                        rider_id = int(medical_id_raw)
                        rider_id = rider_id if rider_id != 0 else "Unknown"
                    else:
                        rider_id = "Unknown"
                    
                    rider_data = {
                        "name": name,
                        "client_id": int(client['Id']),
                        "city": client["City"],
                        "state": client["State"],
                        "current_location/home_address": client["Address"],
                        "rider_id": rider_id,
                        "number_of_existing_trips" : number_of_existing_trips
                    }

                    result[f"rider_{i}"] = rider_data
                    rider_count += 1
                # result["number_of_riders"] = rider_count
            else:
                print("Request failed!")
                result["number_of_riders"] = 1
                result["rider_1"] = {
                    "name" : "new_rider",
                    "client_id" : "-1",
                    "city" : "Unknown",
                    "state" : "Unknown",
                    "current_location" : "Unknown",
                    "rider_id" : "-1",
                    "number_of_existing_trips" : 0
                }
        except Exception as e:
            print(f"Error occurred in getting client Name: {e}")
            result["number_of_riders"] = rider_count
        
        print(f"\n\nResult: {result}\n\n")

        # await asyncio.sleep(2)
        # await self.Stop_Music()

        return json.dumps(result, indent=2)
        
    # @function_tool()
    # async def Book_a_Trip(self,
    #     pickup_street_address: str,
    #     dropoff_street_address: str,
    #     pickup_city: str,
    #     dropoff_city: str,
    #     pickup_state: str,
    #     dropoff_state: str,
    #     extra_details: str,
    #     phone_number: str,
    #     client_id: str,
    #     funding_source_id: str,
    #     rider_name: str,
    #     payment_type_id: str,
    #     copay_funding_source_id: str,
    #     copay_payment_type_id: str,
    #     booking_time: str,
    #     pickup_lat: str,
    #     pickup_lng: str,
    #     dropoff_lat: str,
    #     dropoff_lng: str,
    #     rider_id: str,
    #     number_of_wheel_chairs: str,
    #     number_of_passengers: str,
    #     family_id: str,
    #     is_schedule: str,
    #     pickup_city_zip_code: str,
    #     dropoff_city_zip_code: str,
    #     rider_home_address: str,
    #     rider_home_city: str,
    #     rider_home_state: str,
    #     home_phone: str,
    #     office_phone: str,
    #     total_passengers: int,
    #     total_wheelchairs: int,
    #     is_will_call: bool,
    #     will_call_day: str,
    #     pickup_remarks: str,
    #     pickup_phone_number: str,
    #     dropoff_remarks: str,
    #     dropoff_phone_number: str,
    #     ):
    #     """"Function that is used to book a new trip.
    #     Args:
    #         pickup_street_address: Pickup Street Address confirmed by rider. Do not include city, state, country
    #         dropoff_street_address: Dropoff Street Address confirmed by rider. Do not include city, state, country
    #         pickup_city: Pickup city confirmed by rider else ''
    #         dropoff_city: Dropoff city confirmed by rider else ''
    #         pickup_state: Pickup State confirmed by rider else ''
    #         dropoff_state: Dropoff State confirmed by rider else ''
    #         pickup_city_zip_code: Pick Up City Zip Code else ''
    #         dropoff_city_zip_code: Drop Off City Zip Code else ''
    #         extra_details: Additional Notes if mentioned by rider for the driver else ''
    #         phone_number: Phone number of rider else -1
    #         client_id: Client Id else -1. I am applying  python int() so generate value accordingly
    #         funding_source_id: Funding Source Id else -1. I am applying  python int() so generate value accordingly
    #         affilaite_id: Affiliate Id else -1. I am applying  python int() so generate value accordingly
    #         rider_name: Complete verified name of the rider if available. If you do not have verified name, use Complete Name of the rider used in conversation. If you do not have nane in your memory set it to ''
    #         payment_type_id: Payment Type Id else -1. I am applying  python int() so generate value accordingly
    #         copay_funding_source_id: Copay Funding Source Id else -1. I am applying  python int() so generate value accordingly
    #         copay_payment_type_id: Copay Payment Type Id else -1. I am applying  python int() so generate value accordingly
    #         booking_time: Booking Time if mentioned by rider in this format 'Year-Month-Date HH:MM' for the driver else ''. If the rider wants to book for now, get current time from memory. if is_will_call is true, set it to date today.
    #         pickup_lat: Pickup address latitude else 0. I am applying  python float() so generate value accordingly
    #         pickup_lng: Pickup address longitude else 0. I am applying  python float() so generate value accordingly
    #         dropoff_lat: Drop off address latitude else 0. I am applying  python float() so generate value accordingly
    #         dropoff_lng: Drop off address longitude else 0. I am applying  python float() so generate value accordingly
    #         number_of_wheel_chairs: Number of wheelchairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying  python int() so generate value accordingly
    #         number_of_passengers: Number of passengers. If rider mentioned more than 1 passenger, set accordingly otherwise set it to 1. I am applying  python int() so generate value accordingly
    #         family_id: Family Id else 0. I am applying  python int() so generate value accordingly
    #         is_schedule: 1 if the trip is scheduled for 20+ minutes from current time,also 1 if is_will_call true , else 0 if the trip is scheduled for now. I am applying  python int() so generate value accordingly,or if
    #         rider_id: Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to -1. I am applying  python int() so generate value accordingly
    #         rider_home_address: Home location of the rider present in the memory. If not available, set it to "".
    #         rider_home_city: City of rider's home address. If not available, set it to "".
    #         rider_home_state: State of rider's home address. If not available, set it to "".
    #         home_phone: Rider's home phone no. If not available, set it to "".
    #         office_phone: Rider's Office Phone no. if not available, set it to "".
    #         total_passengers: total passenger count if not available, set it to 1.
    #         total_wheelchairs: total wheelchair count if not available, set it to 0.
    #         is_will_call: true if booking time is not provided or booking time is will call else fasle.
    #         will_call_day:Booking Date if mentioned by rider in this format 'Year-Month-Date 00:00:00' for the driver else get current date from memory, applicable only if is_will_call is true.
    #         pickup_remarks: any remarks given explicitly for pickup address else "".
    #         pickup_phone_number: if pickup phone number is explicitly provided else "".
    #         dropoff_remarks: any remarks given explicitly for drop off address else "".
    #         dropoff_phone_number: if drop off  phone number is explicitly provided else "".
    #
    #     """
    #     print(f"\n\n\nCalled Book a new trip function at: {datetime.now()}\n\n\n")
    #     # Start playing music asynchronously
    #     # _ = asyncio.create_task(self.Play_Music())
    #     # await asyncio.sleep(2)
    #
    #     # Check Pickup Address
    #     pickup_error = await check_address_validity(pickup_lat, pickup_lng, "Pick Up")
    #     if pickup_error:
    #         # await asyncio.sleep(2)
    #         # await self.Stop_Music()
    #         return pickup_error
    #
    #     # Check Dropoff Address
    #     dropoff_error = await check_address_validity(dropoff_lat, dropoff_lng, "Drop Off")
    #     if dropoff_error:
    #         # await asyncio.sleep(2)
    #         # await self.Stop_Music()
    #         return dropoff_error
    #
    #     distance = 0
    #     duration = 0
    #     distance_miles = 0
    #     duration_minutes = 0
    #     total_cost = 0
    #     copay_cost = 0
    #
    #     try:
    #         # Define the API URL and parameters
    #         url = os.getenv("GET_DIRECTION")
    #
    #         params = {
    #             'origin': f'{pickup_lat},{pickup_lng}',  # Origin coordinates
    #             'destination': f'{dropoff_lat},{dropoff_lng}',  # Destination coordinates
    #             'AppType': 'FCSTService'
    #         }
    #
    #         logging.info(f"\n\n\nPayload Sent for distance and duration retrieval: {params}\n\n\n")
    #
    #         # Define your Basic Authentication credentials
    #         auth = BasicAuth(os.getenv("GET_DIRECTION_USER"), os.getenv("GET_DIRECTION_PASSWORD"))  # Replace with your actual password
    #
    #         # Add headers to mimic Postman headers if needed
    #         headers = {
    #             'User-Agent': 'PostmanRuntime/7.43.4',  # Use the User-Agent as seen in Postman
    #             'Accept': '*/*',
    #             'Accept-Encoding': 'gzip, deflate, br',
    #             'Connection': 'keep-alive'
    #         }
    #
    #         # Make the request
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(url, params=params, headers=headers, auth=auth) as response:
    #                 if response.status == 200:
    #                     data = await response.json()
    #                     logging.info(f"\n\n\nResponse for distance and duration retrieval: {data}\n\n\n")
    #                     distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
    #                     duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
    #                     print(f"Distance: {distance}")
    #                     print(f"Duration: {duration}")
    #                     url = os.getenv("GET_FARE_API")
    #
    #                     distance_miles = await meters_to_miles(distance)
    #                     duration_minutes = await seconds_to_minutes(duration)
    #
    #                     # The JSON body data to be sent in the POST request
    #                     data = {
    #                         "distance": distance_miles,
    #                         "travelTime": duration_minutes,
    #                         "fundingSourceID": int(funding_source_id),
    #                         "copy": 0,
    #                         "numberOfWheelchairs": int(number_of_wheel_chairs),
    #                         "numberOfPassengers": int(number_of_passengers),
    #                         "classOfServiceID": 1,
    #                         "affiliateID": int(self.affiliate_id),
    #                         "pickupLatitude": float(pickup_lat),
    #                         "pickupLongitude": float(pickup_lng),
    #                         "copyFundingSourceID": int(copay_funding_source_id),
    #                         "riderID": str(rider_id),
    #                         "authorizedStaff": "string",
    #                         "startFareZone": "string",
    #                         "endFareZone": "string",
    #                         "tspid": "string",
    #                         "httpResponseCode": 100
    #                     }
    #
    #                     logging.info(f"\n\n\nPayload for fare estimation: {data}\n\n\n")
    #
    #                     # Headers to be used in the request
    #                     headers = {
    #                         'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
    #                         'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
    #                     }
    #
    #                     # Making the POST request
    #                     async with aiohttp.ClientSession() as session:
    #                         async with session.post(url, json=data, headers=headers) as response:
    #                             if response.status == 200:
    #                                 # If successful, print the JSON response
    #                                 response_data = await response.json()
    #                                 logging.info(f"\n\n\nResponse for fare estimation: {response_data}\n\n\n")
    #                                 total_cost = response_data["totalCost"]
    #                                 copay_cost = response_data["copay"]
    #                                 print(f"Total Cost: {total_cost}")
    #                                 print(f"Copay Cost: {copay_cost}")
    #                             else:
    #                                 print(f"Request failed with status code: {response.status}")
    #
    #                 else:
    #                     print(f"Request failed with status code: {response.status}")
    #
    #     except Exception as e:
    #         print(f"Error in getting fare: {e}")
    #         pass
    #
    #     pickup_lat = await safe_float(pickup_lat)
    #     pickup_lng = await safe_float(pickup_lng)
    #     dropoff_lat = await safe_float(dropoff_lat)
    #     dropoff_lng = await safe_float(dropoff_lng)
    #
    #     try:
    #         if str(is_schedule) == "1":
    #             is_schedule = True
    #         else:
    #             is_schedule = False
    #
    #     except Exception as e:
    #         print(f"Error in getting schedule status: {e}")
    #         pass
    #
    #     try:
    #
    #         payload_path = os.path.join(App_Directory, "trip_book_payload.json")
    #         # Step 1: Read the JSON file
    #         with open(payload_path, 'r') as file:
    #             data = json.load(file)
    #
    #         print(f"Phone number by LLM: {phone_number}")
    #         phone_number = await format_phone_number(phone_number)
    #         print(f"Phone number after formatting: {phone_number}")
    #
    #         client_id = await safe_int(client_id)
    #         rider_id = await safe_int(rider_id)
    #         affiliate_id = await safe_int(self.affiliate_id)
    #         family_id = await safe_int(family_id)
    #         funding_source_id = await safe_int(funding_source_id)
    #         payment_type_id = await safe_int(payment_type_id)
    #         copay_funding_source_id = await safe_int(copay_funding_source_id)
    #         copay_payment_type_id = await safe_int(copay_payment_type_id)
    #
    #         # Rider and Affiliate Information
    #         data["riderInfo"]["ID"] = client_id
    #         data["riderInfo"]["PhoneNo"] = phone_number
    #         data["riderInfo"]["PickupPerson"] = rider_name
    #         data["riderInfo"]["RiderID"] = rider_id
    #         data["riderInfo"]["ClientAddress"] = rider_home_address
    #         data["riderInfo"]["ClientCity"] = rider_home_city
    #         data["riderInfo"]["ClientState"] = rider_home_state
    #
    #         data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["AffiliateID"] = affiliate_id
    #         data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["AffiliateID"] = affiliate_id
    #         data['generalInfo']['RequestAffiliateID'] = affiliate_id
    #         data['generalInfo']['FamilyID'] = family_id
    #
    #         # Pickup Payment Method Information
    #         data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["FundingSourceID"] = funding_source_id
    #         data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["PaymentTypeID"] = payment_type_id
    #         data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["iCopayFundingSourceID"] = copay_funding_source_id
    #         data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id
    #
    #         # Drop off Payment Method Information
    #         data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["FundingSourceID"] = funding_source_id
    #         data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["PaymentTypeID"] = payment_type_id
    #         data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["iCopayFundingSourceID"] = copay_funding_source_id
    #         data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id
    #
    #         # Pickup Address Information
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Address"] = pickup_street_address
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["City"] = pickup_city
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Latitude"] = pickup_lat
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Longitude"] = pickup_lng
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["State"] = pickup_state
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Zip"] = pickup_city_zip_code
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Phone"] = pickup_phone_number
    #         data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Remarks"] = pickup_remarks
    #         data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["ExtraInfo"] = extra_details
    #         data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["CallBackInfo"] = phone_number
    #         data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["PickupDate"] = booking_time
    #         data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsScheduled"] = is_schedule
    #         data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["WillCallDay"] = will_call_day
    #         data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsWillCall"] = is_will_call
    #         data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalPassengers"] = total_passengers
    #         data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs
    #
    #         # Drop off Address Information
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Address"] = dropoff_street_address
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["City"] = dropoff_city
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Latitude"] = dropoff_lat
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Longitude"] = dropoff_lng
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["State"] = dropoff_state
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Zip"] = dropoff_city_zip_code
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Phone"] = dropoff_phone_number
    #         data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Remarks"] = dropoff_remarks
    #         data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["PickupDate"] = booking_time
    #         data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["IsScheduled"] = is_schedule
    #         data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["CallBackInfo"] = phone_number
    #         data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["WillCallDay"] = will_call_day
    #         data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["IsWillCall"] = is_will_call
    #         data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalPassengers"] = total_passengers
    #         data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs
    #
    #         # Pickup Cost Information
    #         data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedDistance"] = distance_miles
    #         data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedTime"] = duration_minutes
    #         data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedCost"] = total_cost
    #         data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["CoPay"] = copay_cost
    #
    #         # Drop off Cost Information
    #         data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedDistance"] = distance
    #         data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedTime"] = duration
    #         data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedCost"] = total_cost
    #         data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["CoPay"] = copay_cost
    #
    #         # Step 2: Set the endpoint
    #         url = os.getenv("TRIP_BOOKING_API")
    #
    #         print(f"\n\n\nPayload Sent for booking: {data}\n\n\n")
    #         logging.info(f"\n\n\nPayload Sent for booking: {data}\n\n\n")
    #
    #         # Step 3: Send the data to the API
    #         async with aiohttp.ClientSession() as session:
    #             async with session.post(url, json=data) as response:
    #                 response = await response.json()
    #
    #     except Exception as e:
    #         print(f"\n\nError occured in booking trip: {e}\n\n")
    #         pass
    #
    #     dropoff_complete_address = dropoff_street_address + ' ' + dropoff_city + ' ' + dropoff_state + ' ' + dropoff_city_zip_code
    #     prompt = f"""What is the current weather in {dropoff_complete_address}? Provide a concise response with exactly two lines:
    #
    #     Line 1: State the temperature in Fahrenheit (numbers only, no unit) and current sky conditions.
    #     Line 2: Give relevant weather-appropriate advice.
    #
    #     Format example:
    #     "The temperature is 72 and the sky is clear. It's a perfect day for a ride."
    #
    #     Requirements:
    #     - Temperature in Fahrenheit without the °F unit
    #     - Current sky conditions (clear, cloudy, rainy, etc.)
    #     - Practical advice based on the weather conditions
    #     - Keep response to exactly two lines
    #     """
    #     weather = await search_web_manual(prompt)
    #     print(f"\n\nWeather: {weather}\n\n")
    #
    #     # await asyncio.sleep(2)
    #     # await self.Stop_Music()
    #
    #     try:
    #
    #         # Step 4: Process the response
    #         if response["responseCode"] == 200:
    #             print(f"\n\nResponse: {response}\n\n\n")
    #             irefId = response['iRefID']
    #             if irefId == 0:
    #                 return "Your trip could not be booked!"
    #
    #             if str(copay_cost) == "0":
    #                 return f"Trip has been booked! Your Trip Number is {irefId}. It will take around {duration_minutes} minutes and distance between your pick up and drop off is {distance_miles} miles. Total Cost is {total_cost}$. Weather in drop off location is {weather}."
    #             else:
    #                 return f"Trip has been booked! Your Trip Number is {irefId}. It will take around {duration_minutes} minutes and distance between your pick up and drop off is {distance_miles} miles. Total Cost is {total_cost}$ and cost related to copay is {copay_cost}$. Weather in drop off location is {weather}."
    #
    #         else:
    #             return "Trip has not been booked!"
    #
    #     except Exception as e:
    #         print(f"\n\nError occured in book a trip function: {e}\n\n")
    #         return "Trip has not been booked!"
        
    @function_tool()
    async def get_ETA(self, client_id: str):
        """
        Function to get
        - Last pickup/Last drop off Address
        - Last trip details
        - Latest/Recent trip that was booked
        - Their current trip ETA 
        - Where their ride/vehicle/trip is
        - Existing rides/trips status

        Args:
            client_id: Client Id in digits (string or convertible to string)
        """
        print(f"\n\nCalled get_ETA function\n\n")

        # Start background music task
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("EXISTING_RIDES_API")
        client_id = str(client_id)

        payload = {
            "searchCriteria": "CustomerID",
            "searchText": client_id,
            "bActiveRecords": True,
            "iATSPID": int(self.affiliate_id),
            "responseJSON": "string",
            "responseCode": 100
        }

        headers = {
            "Content-Type": "application/json"
        }

        print(f"\n\n\nPayload Sent for booking: {payload}\n\n\n")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    # await asyncio.sleep(2)
                    # await self.Stop_Music()

                    try:
                        response = json.loads(text)
                    except json.JSONDecodeError:
                        print(f"\n\nFailed to decode JSON. Raw response:\n{text}\n\n")
                        return "No data found for ETA!"

                    if response.get("responseCode") == 200:
                        try:
                            data = json.loads(response.get("responseJSON", "{}"))
                            print(f"\n\nResponse: {data}\n\n")
                            existing_trips_data = json.dumps(data, indent=4)
                            if data:
                                latest_trip = max(data, key=lambda x: x['iRefId'])
                                latest_refid = latest_trip.get('iRefId')
                            else:
                                latest_refid = None

                            if latest_refid:
                                result = {
                                    "trips": data,
                                    "latest_trip": latest_refid
                                }

                                existing_trips_data = json.dumps(result, indent=4)
                            
                            print(f"\n\nETA Reponse: {existing_trips_data}\n\n")
                            return existing_trips_data
                        except json.JSONDecodeError:
                            print(f"\n\nFailed to decode nested responseJSON\n\n")
                            return "No data found for ETA!"
                    else:
                        print(f"\n\nNo trip ETA Found for the rider\n\n")
                        return "No data found for ETA!"

        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()

            print(f"\n\nError occurred in getting client ETA: {e}\n\n")
            return "No data found for ETA!"
    
    @function_tool()
    async def search_web(self,
        prompt: str,
        ):

        """Function to search web to get knowledge.
        Args:
            prompt: Prompt for web search. Keep it as precise and to the point as possible. 
        """
        print("\n\nCalled search_web function\n\n")
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        logging.info(f"web search payload: {prompt}")

        try:
            # Use the OpenAI API client to make the call
            response = await openai_client.responses.create(
                model="gpt-4o",
                tools=[{"type": "web_search_preview"}],
                input=prompt
            )
        
            # Output the result
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return response.output_text
        
        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            print(f"Error in search web: {e}")
            return "Web search failed!"
        
    @function_tool()
    async def get_address(self,
        prompt: str,
        country: str,
        city: str,
        state: str
        ):
        """Function to search the web for an address based on location details.
        Args:
            prompt: Prompt to search addresses and latitude and longitude of a location. Include the name of the location. e.g. To find nearest cinema to 20 pitts court prompt will be, 'Nearest cinema to 20 pitts court'
            country: Country of the rider in ISO 3166-1 code For example for United States of America it is 'US'
            city: City of the rider.
            state: State of the rider.
        """
        print("\n\nCalled search_address function\n\n")
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        prompt = f"""{prompt}.\n\nKeep your response as small and precise as possible."""
        logging.info(f"\n\nPrompt for Address Search: {prompt}")
        print(f"\n\nPrompt for Address Search: {prompt}")
        print(f"\n\nCity: {city}")
        print(f"\n\nRegion: {state}")
        print(f"\n\nCountry: {country}")

        try:
            # Use the OpenAI API client to search for the address
            completion = await openai_client.chat.completions.create(
                model="gpt-4o-search-preview",
                web_search_options={
                    "user_location": {
                        "type": "approximate",
                        "approximate": {
                            "country": country,
                            "city": city,
                            "region": state
                        }
                    }
                },
                messages=[{"role": "user", "content": prompt}]
            )

            web_result = completion.choices[0].message.content
            print(f"\n\nResult from Address Search: {web_result}\n\n")
            
            # Summarize the result
            result = await summarize_address_results(web_result)
            print(f"\n\nResult after summarization: {result}\n\n")

            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return result

        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            print(f"Error in address search: {e}")
            return "Address retrieval failed!"
        
    
    @function_tool()
    async def get_valid_addresses(self, 
        address: str
        ):
        """Function to search valid addresses based on input address.
        Args:
            address: Complete Address confirmed by the rider to be validated.
        """
        print(f"\n\nCalled get_valid_address function with address: {address}\n\n")
        # await self.session.say('Let me verify if that address is valid. Please wait a moment.')
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        result = {}

        try:
            result = await verify_address(address)
            print(f"\n\nValid Addresses Result from Web Search: {result}\n\n")
            if result["valid"]:
                 # Extract latitude and longitude
                lat = result["latitude"]
                lng = result["longitude"]
                is_within_service_area = await self.check_bounds(lat, lng)
                result["isWithinServiceArea"] = is_within_service_area
                result_str = json.dumps(result, indent=2)
                # await asyncio.sleep(2)
                # await self.Stop_Music()
                return result_str
        except Exception as e:
            print(f"Error in getting valid address status")

        url = os.getenv("ITC_GEOCODE_API")
        headers = {
            'Authorization': 'Basic U0lWOmJhcndvb2RwYXNz',
            'Host': 'itcmap.itcurves.us',
            'User-Agent': 'PostmanRuntime/7.43.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

        result = {}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={'address': address}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        locations = data['results']
                        for i, location in enumerate(locations):
                            # Initialize the dictionary for each location
                            result[f"Location_{i+1}"] = {}
                            result[f"Location_{i+1}"]["Address"] = location["formatted_address"]
                            result[f"Location_{i+1}"]["Coordinates"] = location['geometry']['location']

                            # Extract latitude and longitude
                            lat = location['geometry']['location']['lat']
                            lng = location['geometry']['location']['lng']
                            is_within_service_area = await self.check_bounds(lat, lng)
                            result[f"Location_{i+1}"]["isWithinServiceArea"] = is_within_service_area

                    else:
                        print(f"ITC location error: status {resp.status}")
        except Exception as e:
            print(f"ITC location exception: {e}")
        
        # await asyncio.sleep(2)
        # await self.Stop_Music()
        print(f"\n\nValid Addresses from ITC MAP API: {result}\n\n")
        return str(result)
    
    @function_tool()
    async def check_bounds(self,
        latitude: str,
        longitude: str
        ):
        """Function to check if the address is within the service area based on provided coordinates.
        Args:
            latitude: Latitude of the location to be checked.
            longitude: Longitude of the location to be checked.
        """
        print(f"\n\nCalled check_bounds function\n\n")
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        bounds, _, _ = await fetch_affiliate_details(self.affiliate_id)

        print("\n\n\n")
        print(f"Bounds: {bounds}")
        print("\n\n\n")

        try:
            # Convert bounds to float for accurate comparison
            x1, y1 = float(bounds['x1']), float(bounds['y1'])
            x2, y2 = float(bounds['x2']), float(bounds['y2'])

            if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
                # await asyncio.sleep(2)
                # await self.Stop_Music()
                return True

            # Latitude and Longitude of the point to check
            point_lat = float(latitude)
            point_lon = float(longitude)

            # await asyncio.sleep(2)
            # await self.Stop_Music()

            if point_lat == 0 and point_lon == 0:
                return True

            # Check if the point is inside the bounds
            if x1 <= point_lat <= x2 and y1 <= point_lon <= y2:
                return True
            else:
                return False
        
        except:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return True
        
    @function_tool()
    async def get_IDs(self, 
        account_: str,
        ):
        """Function to fetch Funding Source Id, Program Id, Payment Type, and Copay Status based on provided account and affiliate details.
        Args:
            account_: Account name provided by the rider, else None
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        print("\n\n\nCalled get_IDs function\n\n\n")

        account = account_.lower()
        pattern = r'\b(cash|card)\b'
        if re.search(pattern, account):
            account = 'self'
        else:
            account = account_
        print(f"Confirmed Account Name: {account}")

        funding_id, program_id, paymenttype_id, copay_status = 1, -1, 1, False
        _, funding_sources, _ = await fetch_affiliate_details(self.affiliate_id)
        try:

            prompt = f"""
            You are given a list of dictionaries enclosed in triple backticks: ```{funding_sources}```

            Your task is to find the dictionary whose 'FundingSource' value closely matches the account enclosed in double quotes: ``{account}``. 

            Return the matching dictionary in JSON format with the following fields:

            {{
                "FundingSource": "Source Name",
                "FID": FID Value,
                "ProgramID": ProgramID Value
            }}

            Instructions:
            1. If a match is found, return the corresponding dictionary in the specified JSON format.
            2. If no match is found, return the following JSON:
                
            {{
                "FundingSource": "None",
                "FID": 1,
                "ProgramID": -1
            }}

            # Instructions
            ## Make sure the response contains only the JSON output, with nothing else.
            ## Take care of spelling mistakes by STT as well. For example 'Vomata' refers to 'WMATA'.
            ## Do not add backticks or 'json'. I am parsing the response with json.loads(). Make it compatible.
            """
            print(f"Prompt sent for matching funding sources: {prompt}")

            response = await get_match_source(prompt)
            print(f"Matching Response: {response}")

            _, _, copay_fs_list = await fetch_affiliate_details(self.affiliate_id)

            try:
                parsed_response = json.loads(response)
                
                funding_id = parsed_response.get("FID", None)
                program_id = parsed_response.get("ProgramID", None)
                program_id = int(program_id)
                account_name = parsed_response.get("FundingSource", None)

                if str(account_name).lower() == "none":
                    # await asyncio.sleep(2)
                    # await self.Stop_Music()
                    return "The account you provided is not valid!"

                print(f"Got Program Id: {program_id}")
                print(f"Got Funding Source Id: {funding_id}")
                print(f"Funding Source List: {copay_fs_list}")
                print(f"Selected Account Name: {account_name}")

                try:
                    funding_id_str = str(funding_id)

                    if funding_id_str == "1":
                        copay_status = False

                    elif funding_id_str in copay_fs_list:
                        copay_status = True
                
                    print(f"Got Copay Status: {copay_status}")

                except Exception as e:
                    print(f"Error in getting copay status: {e}")

                try:
                    url = os.getenv("GET_PAYMENT_TPYE_AFFILIATE_API")

                    # Define the payload
                    data = {
                        "iaffiliateid":str(self.affiliate_id)
                    }
                   

                    print(f"\n\n\nPayload Sent for Payment Type Selection: {data}\n\n\n")

                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=data) as response:
                            # Check for a successful response
                            if response.status == 200:
                                # If it's not JSON, handle it as plain text
                                response_text = await response.text()

                                try:
                                    response_dict = json.loads(response_text)
                                    paymenttype_prompt = f"""
                                    You are given a list of dictionaries enclosed in triple backticks: ```{response_dict}```

                                    Your task is to find the dictionary whose 'PaymentType Name' value closely matches the account enclosed in double quotes: ``{account_}``

                                    Return the matching dictionary in JSON format with the following fields:

                                    {{
                                        "PaymentType ID": Payment Type ID Value,
                                        "PaymentType Name": "Payment Type Name",
                                        "Affiliate ID": Affiliate ID Value
                                    }}

                                    Instructions:
                                    1. If a match is found, return the corresponding dictionary in the specified JSON format.
                                    2. If no match is found, return the following JSON:
                                        
                                    {{
                                        "PaymentType ID": 1,
                                        "PaymentType Name": "None",
                                        "Affiliate ID": -1
                                    }}

                                    # Instructions
                                    ## Make sure the response contains only the JSON output, with nothing else.
                                    ## Take care of spelling mistakes by STT as well. For example 'Vomata' refers to 'WMATA'.
                                    ## Do not add backticks or 'json'. I am parsing the response with json.loads(). Make it compatible.
                                    """
                                    print(f"Prompt sent for matching funding sources: {paymenttype_prompt}")

                                    paymenttype_response = await get_match_source(paymenttype_prompt)
                                    print(f"Matching Response: {paymenttype_response}")

                                    paymenttype_response = json.loads(paymenttype_response)
                
                                    paymenttype_id = paymenttype_response.get("PaymentType ID", None)
 
                                except Exception as e:
                                    print(f"Failed to decode JSON from string: {e}")

                except Exception as e:
                    print(f"Error in getting payment type id: {e}")
                    pass

            except Exception as e:
                print(f"Error parsing JSON: {e}")
                pass

        except Exception as e:
            print(f"Error in getting FID and require verification status: {e}")
            pass

        if program_id == -1:
            rider_verification = False
        else:
            rider_verification = True
        
        # await asyncio.sleep(2)
        # await self.Stop_Music()
        
        print("\n\n")
        print(f"Verified Account Name is: {account_name}, Funding Source Id is: {funding_id}, Requires Rider Verification Status: {rider_verification}, Payment Type Id is: {paymenttype_id}, Require Copay Status is: {copay_status}, Program Id is {program_id}")
        print("\n\n")
        return f"Verified Account Name is: {account_name}, Funding Source Id is: {funding_id}, Requires Rider Verification Status: {rider_verification}, Payment Type Id is: {paymenttype_id}, Require Copay Status is: {copay_status}, Program Id is {program_id}"
    
    @function_tool()
    async def get_copay_ids(self,
        copay_account_name: str
        ):
        """Function to fetch copay payment type based on affiliate ID and copay account name.
        Args:
            affiliate_id: Affiliate Id of the rider, else None.
            copay_account_name: Copay Account Name provided by the rider, else None.
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        print("\n\n\nCalled get_copay_payment_type_id function\n\n\n")

        copay_funding_source_id, payment_type_id = -1, -1
        _, funding_sources, _ = await fetch_affiliate_details(self.affiliate_id)

        prompt = f"""
        You are given a list of dictionaries enclosed in triple backticks: ```{funding_sources}```

        Your task is to find the dictionary whose 'FundingSource' value closely matches the account enclosed in double quotes: ``{copay_account_name}``. 

        Return the matching dictionary in JSON format with the following fields:

        {{
            "FundingSource": "Source Name",
            "FID": FID Value,
            "ProgramID": ProgramID Value
        }}

        Instructions:
        1. If a match is found, return the corresponding dictionary in the specified JSON format.
        2. If no match is found, return the following JSON:

        {{
            "FundingSource": "None",
            "FID": 1,
            "ProgramID": -1
        }}

        # Instructions
        ## Make sure the response contains only the JSON output, with nothing else.
        ## Take care of spelling mistakes by STT as well. For example 'Vomata' refers to 'WMATA'.
        ## Do not add backticks or 'json'. I am parsing the response with json.loads(). Make it compatible.
        """
        print(f"Prompt sent for matching funding sources: {prompt}")

        response = await get_match_source(prompt)
        print(f"Matching Response: {response}")

        try:
            parsed_response = json.loads(response)
            
            copay_funding_source_id = parsed_response.get("FID", None)
            copay_program_id = parsed_response.get("ProgramID", None)
            copay_program_id = int(copay_program_id)
            verified_copay_account_name = parsed_response.get("FundingSource", None)

            print(f"Got Copay Program Id: {copay_program_id}")
            print(f"Got Copay Funding Source Id: {copay_funding_source_id}")

            if str(verified_copay_account_name.lower()) == "None":
                # await asyncio.sleep(2)
                # await self.Stop_Music()
                return "Copay Account was not verified!"

        except:
            pass

        url = os.getenv("GET_PAYMENT_TPYE_AFFILIATE_API")
        payload = {
            "iaffiliateid": str(self.affiliate_id)  # Make sure affiliate_id is sent as a string
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                # Check for a successful response
                if response.status == 200:
                    # If it's not JSON, handle it as plain text
                    response_text = await response.text()

                    try:
                        # Try to convert the string to a dictionary
                        response_dict = json.loads(response_text)
                        print(response_dict)
                    except Exception as e:
                        print(f"Failed to decode JSON from string: {e}")

        prompt = f"""
        You are given a list of dictionaries enclosed in triple backticks: ```{response_dict}```

        Your task is to find the dictionary whose 'PaymentType Name' value closely matches the account enclosed in double quotes: ``{copay_account_name}``. 

        Return the matching dictionary in JSON format with the following fields:

        {{
            "PaymentType ID": PaymentType ID Value,
            "PaymentType Name": "PaymentType Name Value",
            "Affiliate ID": Affilaite ID Value
        }}

        Instructions:
        1. If a match is found, return the corresponding dictionary in the specified JSON format.
        2. If no match is found, return the following JSON:

        {{
            "PaymentType ID": -1,
            "PaymentType Name": "None",
            "Affiliate ID": -1
        }}

        Make sure the response contains only the JSON output, with nothing else.
        Do not add backticks or 'json'. I am parsing the response with json.loads(). Make it compatible.
        In case of multiple matching accounts, return the first one.
        """
        print(f"Prompt sent for matching funding sources: {prompt}")

        response = await get_match_source(prompt)
        print(f"Matching Response: {response}")

        try:
            parsed_response = json.loads(response)
            payment_type_id = int(parsed_response["PaymentType ID"])
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            pass

        # await asyncio.sleep(2)
        # await self.Stop_Music()
        print(f"\n\n\nCopay Funding Source Id: {copay_funding_source_id}\n\n\n")
        print(f"\n\n\nCopay Payment Type Id: {payment_type_id}\n\n\n")

        return f"Verified Copay Account Name is: {verified_copay_account_name}, Copay Funding Source Id is: {copay_funding_source_id} and Copay Payment Type Id: {payment_type_id}"
    
    @function_tool()
    async def verify_rider(self,
        rider_id: str,
        program_id: str
        ):
        """Function to verify rider based on rider_id, affiliate_id, and program_id.
        Args:
            rider_id: Rider Id, else -1.
            affiliate_id: Affiliate Id of the rider, else None.
            program_id: Program Id, else -1.
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        print("\n\n\nCalled verify_rider function\n\n\n")

        program_id_int = int(program_id)
        if program_id_int == -1:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return "Rider does not need verification!"

        url = os.getenv("RIDER_VERIFICATION_API")

        payload = {
            "riderID": int(rider_id),
            "tspid": int(self.affiliate_id),
            "programid": program_id_int
        }

        rider_status = True

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    # Check for a successful response
                    if response.status == 200:
                        # If it's not JSON, handle it as plain text
                        response_text = await response.text()

                        try:
                            # Try to convert the string to a dictionary
                            response_dict = json.loads(response_text)
                            rider_status = response_dict["VerificationSuccess"]
                        except Exception as e:
                            print(f"Failed to decode JSON from string: {e}")
            
            verified_rider_name = ""
            
            if rider_status:
                get_name_url = os.getenv("GET_NAME_API")

                headers = {
                    "Content-Type": "application/json"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(get_name_url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            # If it's not JSON, handle it as plain text
                            response_text = await response.text()

                            print(f"\n\nRider Name Retrieval Result: {response_text}\n\n")

                            try:
                                # Try to convert the string to a dictionary
                                response_dict = json.loads(response_text)
                                verified_rider_name += str(response_dict["FirstName"]) + " "
                                verified_rider_name += str(response_dict["LastName"])
                                
                            except Exception as e:
                                print(f"Failed to decode JSON from string: {e}")
            
            print(f"Rider Verification Status: {rider_status}")
            print(f"Verified Rider Name: {verified_rider_name}")
        except Exception as e:
            print(f"\n\nError in verifying_rider_id: {e}\n\n")
        # await asyncio.sleep(2)
        # await self.Stop_Music()

        if not rider_status:
            return "Rider is not verified!"
        else:
            if verified_rider_name.strip() == "":
                return "Rider is Verifed!"
            else:
                return f"Rider is Verified! Verified Rider Name is {verified_rider_name}"


    @function_tool()
    async def get_Trip_Stats(self,
        client_id: str
        ):
        """Function to get Trip ETA or to know where is rider's current ride.
        Args:
            client_id: Client Id in digits
        """

        print(f"\n\nCalled get_Trip_Stats function\n\n")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        
        # Define the API endpoint
        url = os.getenv("TRIP_STATS_API")

        client_id = int(client_id)

        # Create the payload (request body)
        payload = {
        "iclientid": client_id
        }

        # Define the headers
        headers = {
            "Content-Type": "application/json"
        }

        print(f"\n\n\nPayload Sent for trip stats: {payload}\n\n\n")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    print(f"\n\nStatus: {resp.status}")
                    print(f"Headers: {resp.headers}\n\n")

                    # Read text response and try to parse as JSON manually
                    text = await resp.text()

                    try:
                        data = json.loads(text)
                        print(f"\n\nResponse: {data}\n\n")
                        # await asyncio.sleep(2)
                        # await self.Stop_Music()
                        return json.dumps(data, indent=4)
                    except json.JSONDecodeError:
                        # await asyncio.sleep(2)
                        # await self.Stop_Music()
                        print("\n\nFailed to decode JSON. Raw response:\n", text)
                        return "No valid JSON data found!"
                    
        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            print(f"\n\nError occurred in getting trip stats: {e}\n\n")
            return "No data found!"
        
    @function_tool()
    async def get_historic_rides(self,
        client_id: str
        ):
        """Function to get
        - Performed trips
        - Latest/Last Historic trip
        - Latest/Last Performed trip
        - Latest/Last Past trip
        - Number of trips completed in last few days
        - Past trips
        - Historic trips
        Args:
            client_id: Client Id in digits
        """
        
        print(f"\n\nCalled get_historic_rides function\n\n")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("GET_HISTORIC_RIDES_API")

        payload = {
            "clientID": str(client_id),
            "affiliateID": str(self.affiliate_id),
            "bGetAddressDataOnly": "false",
            "responseCode": 100
        }

        headers = {
            "Content-Type": "application/json"
        }

        historic_trips_data = ""
        print(f"\n\nPayload sent to get frequent addresses: {payload}\n\n")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                # print(f"Status Code: {response.status}")
                response_text = await response.text()
                print(f"\n\nResponse from FrequentDataAPI: {response_text}\n\n")
                try:
                    response_json = json.loads(response_text)
                    historic_trips = json.loads(response_json["responseJSON"])  # this is the list

                    if historic_trips:
                        last_historic_trip = max(historic_trips, key=lambda x: int(x['iRefId']))
                        last_historic_refid = last_historic_trip.get('iRefId')
                    else:
                        last_historic_refid = None

                    if last_historic_refid:
                        result = {
                            "trips": historic_trips,
                            "latest_historic_trip": last_historic_refid
                        }
                        historic_trips_data = json.dumps(result, indent=4)
                    else:
                        historic_trips_data = json.dumps(historic_trips, indent=4)

                except json.JSONDecodeError:
                    print("Failed to parse response as JSON.")
                    print("Raw Response:", response_text)

        if historic_trips_data.strip() == "":
            historic_trips_data = "No Data Available"
        
        historic_trips_data_result = f"""Rider Historic/Past/Completed Trips are: ``{historic_trips_data}``\n
        """
        print(f"\n\nHistoric Rides: {historic_trips_data}\n\n")
        # await asyncio.sleep(2)
        # await self.Stop_Music()
        return historic_trips_data_result
    
    @function_tool()
    async def get_frequnt_addresses(self, client_id: str):

        """Function to get Rider Frequently Used Addresses
        Args:
            client_id: Client Id in digits
        """

        print(f"\n\nCalled get_frequnt_addresses function\n\n")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("GET_HISTORIC_RIDES_API")

        payload = {
            "clientID": str(client_id),
            "affiliateID": str(self.affiliate_id),
            "bIncludeClientAddress": "",
            "bGetAddressDataOnly": "",
            "bGetCompletedHistoricRides": "",
            "responseJSON": "",
            "responseCode": 100
        }

        headers = {
            "Content-Type": "application/json"
        }

        frequent_addresses = ""
        print(f"\n\nPayload sent to get frequent addresses: {payload}\n\n")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                # print(f"Status Code: {response.status}")
                response_text = await response.text()
                print(f"\n\nResponse from FrequentDataAPI: {response_text}\n\n")
                try:
                    response_json = json.loads(response_text)
                    if response_json.get("responseCode") == 200:
                        address_data = response_json.get("responseJSON", "[]")
                        address_data_json = json.loads(address_data)

                        for trip in address_data_json:
                            pickup_address = trip.get("PUAddress", "") + trip.get("PUCity", "") + trip.get("PUState", "")
                            dropoff_address = trip.get("DOAddress", "") + trip.get("DOCity", "") + trip.get("DOState", "")
                            frequent_addresses += pickup_address + "\n" + dropoff_address + "\n"
                    else:
                        frequent_addresses = ""
                    
                except json.JSONDecodeError:
                    print("Failed to parse response as JSON.")
                    print("Raw Response:", response_text)

        if frequent_addresses.strip() == "":
            frequent_addresses = "No Data Available"
        
        frequent_addresses_result = f"""Rider Frequently Used Addresses are: ``{frequent_addresses}``\n
        Only use these addresses for address completion. Use [get_ETA] function to get Last/Latest trip details
        """
        # await asyncio.sleep(2)
        # await self.Stop_Music()
        return frequent_addresses_result

    @function_tool()
    async def get_distance_duration_fare(self,
        pickup_latitude: str,
        dropoff_latitude: str,
        pickup_longitude: str,
        dropoff_longitude: str,
        number_of_wheel_chairs: str,
        number_of_passengers: str,
        rider_id: str,
        ):
        """Function to Distance and Trip Duration between two locations
        Args:
            pickup_latitude: Pickup Address Latitude in string. If not available, set it to 0.
            pickup_longitude: Pickup Address Longitude in string. If not available, set it to 0.
            dropoff_latitude: Dropoff Address Latitude in string. If not available, set it to 0.
            dropoff_longitude: Dropoff Address Longitude in string. If not available, set it to 0.
            rider_id: Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to 0. I am applying  python int() so generate value accordingly
            number_of_wheel_chairs: Number of wheel chairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying  python int() so generate value accordingly
            number_of_passengers: Number of passengers. If rider mentioned more than 1 passengers, set accordingly otherwise set it to 1. I am applying  python int() so generate value accordingly
        """

        print(f"\n\nCalled get_distance_duration_fare function\n\n")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        if pickup_latitude == "0" or pickup_longitude == "0":
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return "Pick Up address is not verified. Use [get_valid_addresses] function to verify it first"
        
        if dropoff_latitude == "0" or dropoff_longitude == "0":
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return "Drop Off address is not verified. Use [get_valid_addresses] function to verify it first"

        distance_miles = 0
        duration_minutes = 0
        total_cost = 0
        copay_cost = 0

        try:

            # Define the API URL and parameters
            url = os.getenv("GET_DIRECTION")
            
            params = {
                'origin': f'{pickup_latitude},{pickup_longitude}',  # Origin coordinates
                'destination': f'{dropoff_latitude},{dropoff_longitude}',  # Destination coordinates
                'AppType': 'FCSTService'
            }

            logging.info(f"\n\n\nPayload Sent for distance and duration retrieval: {params}\n\n\n")
            
            # Define your Basic Authentication credentials
            auth = BasicAuth(os.getenv("GET_DIRECTION_USER"), os.getenv("GET_DIRECTION_PASSWORD"))  # Replace with your actual password

            # Add headers to mimic Postman headers if needed
            headers = {
                'User-Agent': 'PostmanRuntime/7.43.4',  # Use the User-Agent as seen in Postman
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, auth=auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"\n\n\nResponse for distance and duration retrieval: {data}\n\n\n")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"]) 
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        print(f"Distance: {distance}")
                        print(f"Duration: {duration}")

                        url = os.getenv("GET_FARE_API")

                        distance_miles = await meters_to_miles(distance)
                        duration_minutes = await seconds_to_minutes(duration)
            
                        # The JSON body data to be sent in the POST request
                        data = {
                            "distance": distance_miles,
                            "travelTime": duration_minutes,
                            "fundingSourceID": 1,
                            "copy": 0,
                            "numberOfWheelchairs": int(number_of_wheel_chairs),
                            "numberOfPassengers": int(number_of_passengers),
                            "classOfServiceID": 1,
                            "affiliateID": int(self.affiliate_id),
                            "pickupLatitude": float(pickup_latitude),
                            "pickupLongitude": float(pickup_longitude),
                            "copyFundingSourceID": -1,
                            "riderID": str(rider_id),
                            "authorizedStaff": "string",
                            "startFareZone": "string",
                            "endFareZone": "string",
                            "tspid": "string",
                            "httpResponseCode": 100
                        }

                        logging.info(f"\n\n\nPayload for fare estimation: {data}\n\n\n")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    # If successful, print the JSON response
                                    response_data = await response.json()
                                    logging.info(f"\n\n\nResponse for fare estimation: {response_data}\n\n\n")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    print(f"Total Cost: {total_cost}")
                                    print(f"Copay Cost: {copay_cost}")
                                else:
                                    print(f"Request failed with status code: {response.status}")

                    else:
                        print(f"Request failed with status code {response.status_code}")

        except Exception as e:
            logging.ERROR(f"Error in getting distance and duration: {e}")

        # await asyncio.sleep(2)
        # await self.Stop_Music()

        if distance_miles == 0 and duration_minutes == 0:
            return "Could not get distance and duration from API!"
        
        return f"""Distance between two locations is {distance_miles} miles, it will take around {duration_minutes} minutes while Cost is ${total_cost}
        """

    # @function_tool()
    # async def pause_for_a_while(self):
    #     await asyncio.sleep(0.5)
    #     return "Paused for a while"

    @function_tool()
    async def collect_main_trip_payload(self,
                          pickup_street_address: str,
                          dropoff_street_address: str,
                          pickup_city: str,
                          dropoff_city: str,
                          pickup_state: str,
                          dropoff_state: str,
                          extra_details: str,
                          phone_number: str,
                          client_id: str,
                          funding_source_id: str,
                          rider_name: str,
                          payment_type_id: str,
                          copay_funding_source_id: str,
                          copay_payment_type_id: str,
                          booking_time: str,
                          pickup_lat: str,
                          pickup_lng: str,
                          dropoff_lat: str,
                          dropoff_lng: str,
                          rider_id: str,
                          number_of_wheel_chairs: str,
                          number_of_passengers: str,
                          family_id: str,
                          is_schedule: str,
                          pickup_city_zip_code: str,
                          dropoff_city_zip_code: str,
                          rider_home_address: str,
                          rider_home_city: str,
                          rider_home_state: str,
                          home_phone: str,
                          office_phone: str,
                          total_passengers: int,
                          total_wheelchairs: int,
                          is_will_call: bool,
                          will_call_day: str,
                          pickup_remarks: str,
                          pickup_phone_number: str,
                          dropoff_remarks: str,
                          dropoff_phone_number: str,
                          ):
        """"Function that is used to collect the payload for the trips.
        Args:
            pickup_street_address: Pickup Street Address confirmed by rider. Do not include city, state, country
            dropoff_street_address: Dropoff Street Address confirmed by rider. Do not include city, state, country
            pickup_city: Pickup city confirmed by rider else ''
            dropoff_city: Dropoff city confirmed by rider else ''
            pickup_state: Pickup State confirmed by rider else ''
            dropoff_state: Dropoff State confirmed by rider else ''
            pickup_city_zip_code: Pick Up City Zip Code else ''
            dropoff_city_zip_code: Drop Off City Zip Code else ''
            extra_details: Additional Notes if mentioned by rider for the driver else ''
            phone_number: Phone number of rider else -1
            client_id: Client Id else -1. I am applying  python int() so generate value accordingly
            funding_source_id: Funding Source Id else -1. I am applying  python int() so generate value accordingly
            affilaite_id: Affiliate Id else -1. I am applying  python int() so generate value accordingly
            rider_name: Complete verified name of the rider if available. If you do not have verified name, use Complete Name of the rider used in conversation. If you do not have nane in your memory set it to ''
            payment_type_id: Payment Type Id else -1. I am applying  python int() so generate value accordingly
            copay_funding_source_id: Copay Funding Source Id else -1. I am applying  python int() so generate value accordingly
            copay_payment_type_id: Copay Payment Type Id else -1. I am applying  python int() so generate value accordingly
            booking_time: Booking Time if mentioned by rider in this format 'Year-Month-Date HH:MM' for the driver else ''. If the rider wants to book for now, get current time from memory. if is_will_call is true, set it to date today.
            pickup_lat: Pickup address latitude else 0. I am applying  python float() so generate value accordingly
            pickup_lng: Pickup address longitude else 0. I am applying  python float() so generate value accordingly
            dropoff_lat: Drop off address latitude else 0. I am applying  python float() so generate value accordingly
            dropoff_lng: Drop off address longitude else 0. I am applying  python float() so generate value accordingly
            number_of_wheel_chairs: Number of wheelchairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying  python int() so generate value accordingly
            number_of_passengers: Number of passengers. If rider mentioned more than 1 passenger, set accordingly otherwise set it to 1. I am applying  python int() so generate value accordingly
            family_id: Family Id else 0. I am applying  python int() so generate value accordingly
            is_schedule: 1 if the trip is scheduled for 20+ minutes from current time,also 1 if is_will_call true , else 0 if the trip is scheduled for now. I am applying  python int() so generate value accordingly,or if
            rider_id: Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to -1. I am applying  python int() so generate value accordingly
            rider_home_address: Home location of the rider present in the memory. If not available, set it to "".
            rider_home_city: City of rider's home address. If not available, set it to "".
            rider_home_state: State of rider's home address. If not available, set it to "".
            home_phone: Rider's home phone no. If not available, set it to "".
            office_phone: Rider's Office Phone no. if not available, set it to "".
            total_passengers: total passenger count if not available, set it to 1.
            total_wheelchairs: total wheelchair count if not available, set it to 0.
            is_will_call: true if booking time is not provided or booking time is will call else fasle.
            will_call_day:Booking Date if mentioned by rider in this format 'Year-Month-Date 00:00:00' for the driver else get current date from memory, applicable only if is_will_call is true.
            pickup_remarks: any remarks given explicitly for pickup address else "".
            pickup_phone_number: if pickup phone number is explicitly provided else "".
            dropoff_remarks: any remarks given explicitly for drop off address else "".
            dropoff_phone_number: if drop off  phone number is explicitly provided else "".

        """
        # print(f"\n\n\nCalled collect_trip_payload function at: {datetime.now()}\n\n\n")
        logging.info(f"\n\n\nCalled collect_trip_payload function at: {datetime.now()}\n\n\n")
        # Start playing music asynchronously
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        # Check Pickup Address
        pickup_error = await check_address_validity(pickup_lat, pickup_lng, "Pick Up")
        if pickup_error:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return pickup_error

        # Check Dropoff Address
        dropoff_error = await check_address_validity(dropoff_lat, dropoff_lng, "Drop Off")
        if dropoff_error:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return dropoff_error

        distance = 0
        duration = 0
        distance_miles = 0
        duration_minutes = 0
        total_cost = 0
        copay_cost = 0

        try:
            # Define the API URL and parameters
            url = os.getenv("GET_DIRECTION")

            params = {
                'origin': f'{pickup_lat},{pickup_lng}',  # Origin coordinates
                'destination': f'{dropoff_lat},{dropoff_lng}',  # Destination coordinates
                'AppType': 'FCSTService'
            }

            logging.info(f"\n\n\nPayload Sent for distance and duration retrieval: {params}\n\n\n")

            # Define your Basic Authentication credentials
            auth = BasicAuth(os.getenv("GET_DIRECTION_USER"),
                             os.getenv("GET_DIRECTION_PASSWORD"))  # Replace with your actual password

            # Add headers to mimic Postman headers if needed
            headers = {
                'User-Agent': 'PostmanRuntime/7.43.4',  # Use the User-Agent as seen in Postman
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, auth=auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"\n\n\nResponse for distance and duration retrieval: {data}\n\n\n")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        print(f"Distance: {distance}")
                        print(f"Duration: {duration}")
                        url = os.getenv("GET_FARE_API")

                        distance_miles = await meters_to_miles(distance)
                        duration_minutes = await seconds_to_minutes(duration)

                        # The JSON body data to be sent in the POST request
                        data = {
                            "distance": distance_miles,
                            "travelTime": duration_minutes,
                            "fundingSourceID": int(funding_source_id),
                            "copy": 0,
                            "numberOfWheelchairs": int(number_of_wheel_chairs),
                            "numberOfPassengers": int(number_of_passengers),
                            "classOfServiceID": 1,
                            "affiliateID": int(self.affiliate_id),
                            "pickupLatitude": float(pickup_lat),
                            "pickupLongitude": float(pickup_lng),
                            "copyFundingSourceID": int(copay_funding_source_id),
                            "riderID": str(rider_id),
                            "authorizedStaff": "string",
                            "startFareZone": "string",
                            "endFareZone": "string",
                            "tspid": "string",
                            "httpResponseCode": 100
                        }

                        logging.info(f"\n\n\nPayload for fare estimation: {data}\n\n\n")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    # If successful, print the JSON response
                                    response_data = await response.json()
                                    logging.info(f"\n\n\nResponse for fare estimation: {response_data}\n\n\n")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    print(f"Total Cost: {total_cost}")
                                    print(f"Copay Cost: {copay_cost}")
                                else:
                                    print(f"Request failed with status code: {response.status}")

                    else:
                        print(f"Request failed with status code: {response.status}")

        except Exception as e:
            print(f"Error in getting fare: {e}")
            pass

        pickup_lat = await safe_float(pickup_lat)
        pickup_lng = await safe_float(pickup_lng)
        dropoff_lat = await safe_float(dropoff_lat)
        dropoff_lng = await safe_float(dropoff_lng)

        try:
            if str(is_schedule) == "1":
                is_schedule = True
            else:
                is_schedule = False

        except Exception as e:
            print(f"Error in getting schedule status: {e}")
            pass

        try:

            payload_path = os.path.join(App_Directory, "trip_book_payload.json")
            # Step 1: Read the JSON file
            with open(payload_path, 'r') as file:
                data = json.load(file)

            print(f"Phone number by LLM: {phone_number}")
            phone_number = await format_phone_number(phone_number)
            print(f"Phone number after formatting: {phone_number}")

            client_id = await safe_int(client_id)
            rider_id = await safe_int(rider_id)
            affiliate_id = await safe_int(self.affiliate_id)
            family_id = await safe_int(family_id)
            funding_source_id = await safe_int(funding_source_id)
            payment_type_id = await safe_int(payment_type_id)
            copay_funding_source_id = await safe_int(copay_funding_source_id)
            copay_payment_type_id = await safe_int(copay_payment_type_id)

            # Rider and Affiliate Information
            data["riderInfo"]["ID"] = client_id
            data["riderInfo"]["PhoneNo"] = phone_number
            data["riderInfo"]["PickupPerson"] = rider_name
            data["riderInfo"]["RiderID"] = rider_id
            data["riderInfo"]["ClientAddress"] = rider_home_address
            data["riderInfo"]["ClientCity"] = rider_home_city
            data["riderInfo"]["ClientState"] = rider_home_state

            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["AffiliateID"] = affiliate_id
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["AffiliateID"] = affiliate_id
            data['generalInfo']['RequestAffiliateID'] = affiliate_id
            data['generalInfo']['FamilyID'] = family_id

            # Pickup Payment Method Information
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["FundingSourceID"] = funding_source_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["PaymentTypeID"] = payment_type_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"][
                "iCopayFundingSourceID"] = copay_funding_source_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id

            # Drop off Payment Method Information
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["FundingSourceID"] = funding_source_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["PaymentTypeID"] = payment_type_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"][
                "iCopayFundingSourceID"] = copay_funding_source_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id

            # Pickup Address Information
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Address"] = pickup_street_address
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["City"] = pickup_city
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Latitude"] = pickup_lat
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Longitude"] = pickup_lng
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["State"] = pickup_state
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Zip"] = pickup_city_zip_code
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Phone"] = pickup_phone_number
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Remarks"] = pickup_remarks
            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["ExtraInfo"] = extra_details
            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["CallBackInfo"] = phone_number
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["PickupDate"] = booking_time
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsScheduled"] = is_schedule
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalPassengers"] = total_passengers
            data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs

            # Drop off Address Information
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Address"] = dropoff_street_address
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["City"] = dropoff_city
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Latitude"] = dropoff_lat
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Longitude"] = dropoff_lng
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["State"] = dropoff_state
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Zip"] = dropoff_city_zip_code
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Phone"] = dropoff_phone_number
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Remarks"] = dropoff_remarks
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["PickupDate"] = booking_time
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["IsScheduled"] = is_schedule
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["CallBackInfo"] = phone_number
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalPassengers"] = total_passengers
            data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs

            # Pickup Cost Information
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedDistance"] = distance_miles
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedTime"] = duration_minutes
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedCost"] = total_cost
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["CoPay"] = copay_cost

            # Drop off Cost Information
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedDistance"] = distance
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedTime"] = duration
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedCost"] = total_cost
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["CoPay"] = copay_cost

            # adding payload to agent memory

            if self.main_leg is None:
                self.main_leg = data
            # elif self.return_leg is None:
            #     self.return_leg = data

            # print(f"\n\n\nPayload collected: {data}\n\n\n")
            logging.info(f"\n\n\nPayload collected: {data}\n\n\n")

            return f"The collected payload for trip is :{data}"

        except Exception as e:
            print(f"\n\nError occurred in collecting trip payload: {e}\n\n")
            return f"error: {e}"

    @function_tool()
    async def collect_return_trip_payload(self,
                                        pickup_street_address: str,
                                        dropoff_street_address: str,
                                        pickup_city: str,
                                        dropoff_city: str,
                                        pickup_state: str,
                                        dropoff_state: str,
                                        extra_details: str,
                                        phone_number: str,
                                        client_id: str,
                                        funding_source_id: str,
                                        rider_name: str,
                                        payment_type_id: str,
                                        copay_funding_source_id: str,
                                        copay_payment_type_id: str,
                                        booking_time: str,
                                        pickup_lat: str,
                                        pickup_lng: str,
                                        dropoff_lat: str,
                                        dropoff_lng: str,
                                        rider_id: str,
                                        number_of_wheel_chairs: str,
                                        number_of_passengers: str,
                                        family_id: str,
                                        is_schedule: str,
                                        pickup_city_zip_code: str,
                                        dropoff_city_zip_code: str,
                                        rider_home_address: str,
                                        rider_home_city: str,
                                        rider_home_state: str,
                                        home_phone: str,
                                        office_phone: str,
                                        total_passengers: int,
                                        total_wheelchairs: int,
                                        is_will_call: bool,
                                        will_call_day: str,
                                        pickup_remarks: str,
                                        pickup_phone_number: str,
                                        dropoff_remarks: str,
                                        dropoff_phone_number: str,
                                        ):
        """"Function that is used to collect return trip payload.
        Args:
            pickup_street_address: Pickup Street Address confirmed by rider. Do not include city, state, country
            dropoff_street_address: Dropoff Street Address confirmed by rider. Do not include city, state, country
            pickup_city: Pickup city confirmed by rider else ''
            dropoff_city: Dropoff city confirmed by rider else ''
            pickup_state: Pickup State confirmed by rider else ''
            dropoff_state: Dropoff State confirmed by rider else ''
            pickup_city_zip_code: Pick Up City Zip Code else ''
            dropoff_city_zip_code: Drop Off City Zip Code else ''
            extra_details: Additional Notes if mentioned by rider for the driver else ''
            phone_number: Phone number of rider else -1
            client_id: Client Id else -1. I am applying  python int() so generate value accordingly
            funding_source_id: Funding Source Id else -1. I am applying  python int() so generate value accordingly
            affilaite_id: Affiliate Id else -1. I am applying  python int() so generate value accordingly
            rider_name: Complete verified name of the rider if available. If you do not have verified name, use Complete Name of the rider used in conversation. If you do not have nane in your memory set it to ''
            payment_type_id: Payment Type Id else -1. I am applying  python int() so generate value accordingly
            copay_funding_source_id: Copay Funding Source Id else -1. I am applying  python int() so generate value accordingly
            copay_payment_type_id: Copay Payment Type Id else -1. I am applying  python int() so generate value accordingly
            booking_time: Booking Time if mentioned by rider in this format 'Year-Month-Date HH:MM' for the driver else ''. If the rider wants to book for now, get current time from memory. if is_will_call is true, set it to date today.
            pickup_lat: Pickup address latitude else 0. I am applying  python float() so generate value accordingly
            pickup_lng: Pickup address longitude else 0. I am applying  python float() so generate value accordingly
            dropoff_lat: Drop off address latitude else 0. I am applying  python float() so generate value accordingly
            dropoff_lng: Drop off address longitude else 0. I am applying  python float() so generate value accordingly
            number_of_wheel_chairs: Number of wheelchairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'. I am applying  python int() so generate value accordingly
            number_of_passengers: Number of passengers. If rider mentioned more than 1 passenger, set accordingly otherwise set it to 1. I am applying  python int() so generate value accordingly
            family_id: Family Id else 0. I am applying  python int() so generate value accordingly
            is_schedule: 1 if the trip is scheduled for 20+ minutes from current time,also 1 if is_will_call true , else 0 if the trip is scheduled for now. I am applying  python int() so generate value accordingly,or if
            rider_id: Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to -1. I am applying  python int() so generate value accordingly
            rider_home_address: Home location of the rider present in the memory. If not available, set it to "".
            rider_home_city: City of rider's home address. If not available, set it to "".
            rider_home_state: State of rider's home address. If not available, set it to "".
            home_phone: Rider's home phone no. If not available, set it to "".
            office_phone: Rider's Office Phone no. if not available, set it to "".
            total_passengers: total passenger count if not available, set it to 1.
            total_wheelchairs: total wheelchair count if not available, set it to 0.
            is_will_call: true if booking time is not provided or booking time is will call else fasle.
            will_call_day:Booking Date if mentioned by rider in this format 'Year-Month-Date 00:00:00' for the driver else get current date from memory, applicable only if is_will_call is true.
            pickup_remarks: any remarks given explicitly for pickup address else "".
            pickup_phone_number: if pickup phone number is explicitly provided else "".
            dropoff_remarks: any remarks given explicitly for drop off address else "".
            dropoff_phone_number: if drop off  phone number is explicitly provided else "".

        """
        # print(f"\n\n\nCalled collect_return_trip_payload function at: {datetime.now()}\n\n\n")
        logging.info(f"\n\n\nCalled collect_return_trip_payload function at: {datetime.now()}\n\n\n")
        # Start playing music asynchronously
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        # Check Pickup Address
        pickup_error = await check_address_validity(pickup_lat, pickup_lng, "Pick Up")
        if pickup_error:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return pickup_error

        # Check Dropoff Address
        dropoff_error = await check_address_validity(dropoff_lat, dropoff_lng, "Drop Off")
        if dropoff_error:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            return dropoff_error

        distance = 0
        duration = 0
        distance_miles = 0
        duration_minutes = 0
        total_cost = 0
        copay_cost = 0

        try:
            # Define the API URL and parameters
            url = os.getenv("GET_DIRECTION")

            params = {
                'origin': f'{pickup_lat},{pickup_lng}',  # Origin coordinates
                'destination': f'{dropoff_lat},{dropoff_lng}',  # Destination coordinates
                'AppType': 'FCSTService'
            }

            logging.info(f"\n\n\nPayload Sent for distance and duration retrieval: {params}\n\n\n")

            # Define your Basic Authentication credentials
            auth = BasicAuth(os.getenv("GET_DIRECTION_USER"),
                             os.getenv("GET_DIRECTION_PASSWORD"))  # Replace with your actual password

            # Add headers to mimic Postman headers if needed
            headers = {
                'User-Agent': 'PostmanRuntime/7.43.4',  # Use the User-Agent as seen in Postman
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, auth=auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        logging.info(f"\n\n\nResponse for distance and duration retrieval: {data}\n\n\n")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        print(f"Distance: {distance}")
                        print(f"Duration: {duration}")
                        url = os.getenv("GET_FARE_API")

                        distance_miles = await meters_to_miles(distance)
                        duration_minutes = await seconds_to_minutes(duration)

                        # The JSON body data to be sent in the POST request
                        data = {
                            "distance": distance_miles,
                            "travelTime": duration_minutes,
                            "fundingSourceID": int(funding_source_id),
                            "copy": 0,
                            "numberOfWheelchairs": int(number_of_wheel_chairs),
                            "numberOfPassengers": int(number_of_passengers),
                            "classOfServiceID": 1,
                            "affiliateID": int(self.affiliate_id),
                            "pickupLatitude": float(pickup_lat),
                            "pickupLongitude": float(pickup_lng),
                            "copyFundingSourceID": int(copay_funding_source_id),
                            "riderID": str(rider_id),
                            "authorizedStaff": "string",
                            "startFareZone": "string",
                            "endFareZone": "string",
                            "tspid": "string",
                            "httpResponseCode": 100
                        }

                        logging.info(f"\n\n\nPayload for fare estimation: {data}\n\n\n")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    # If successful, print the JSON response
                                    response_data = await response.json()
                                    logging.info(f"\n\n\nResponse for fare estimation: {response_data}\n\n\n")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    print(f"Total Cost: {total_cost}")
                                    print(f"Copay Cost: {copay_cost}")
                                else:
                                    print(f"Request failed with status code: {response.status}")

                    else:
                        print(f"Request failed with status code: {response.status}")

        except Exception as e:
            print(f"Error in getting fare: {e}")
            pass

        pickup_lat = await safe_float(pickup_lat)
        pickup_lng = await safe_float(pickup_lng)
        dropoff_lat = await safe_float(dropoff_lat)
        dropoff_lng = await safe_float(dropoff_lng)

        try:
            if str(is_schedule) == "1":
                is_schedule = True
            else:
                is_schedule = False

        except Exception as e:
            print(f"Error in getting schedule status: {e}")
            pass

        try:

            payload_path = os.path.join(App_Directory, "trip_book_payload.json")
            # Step 1: Read the JSON file
            with open(payload_path, 'r') as file:
                data = json.load(file)

            print(f"Phone number by LLM: {phone_number}")
            phone_number = await format_phone_number(phone_number)
            print(f"Phone number after formatting: {phone_number}")

            client_id = await safe_int(client_id)
            rider_id = await safe_int(rider_id)
            affiliate_id = await safe_int(self.affiliate_id)
            family_id = await safe_int(family_id)
            funding_source_id = await safe_int(funding_source_id)
            payment_type_id = await safe_int(payment_type_id)
            copay_funding_source_id = await safe_int(copay_funding_source_id)
            copay_payment_type_id = await safe_int(copay_payment_type_id)

            # Rider and Affiliate Information
            data["riderInfo"]["ID"] = client_id
            data["riderInfo"]["PhoneNo"] = phone_number
            data["riderInfo"]["PickupPerson"] = rider_name
            data["riderInfo"]["RiderID"] = rider_id
            data["riderInfo"]["ClientAddress"] = rider_home_address
            data["riderInfo"]["ClientCity"] = rider_home_city
            data["riderInfo"]["ClientState"] = rider_home_state

            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["AffiliateID"] = affiliate_id
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["AffiliateID"] = affiliate_id
            data['generalInfo']['RequestAffiliateID'] = affiliate_id
            data['generalInfo']['FamilyID'] = family_id

            # Pickup Payment Method Information
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["FundingSourceID"] = funding_source_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["PaymentTypeID"] = payment_type_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"][
                "iCopayFundingSourceID"] = copay_funding_source_id
            data['addressInfo']["Trips"][0]["Details"][0]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id

            # Drop off Payment Method Information
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["FundingSourceID"] = funding_source_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["PaymentTypeID"] = payment_type_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"][
                "iCopayFundingSourceID"] = copay_funding_source_id
            data['addressInfo']["Trips"][0]["Details"][1]["paymentInfo"]["iActualPaymentTypeID"] = copay_payment_type_id

            # Pickup Address Information
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Address"] = pickup_street_address
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["City"] = pickup_city
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Latitude"] = pickup_lat
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Longitude"] = pickup_lng
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["State"] = pickup_state
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Zip"] = pickup_city_zip_code
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Phone"] = pickup_phone_number
            data['addressInfo']["Trips"][0]["Details"][0]["addressDetails"]["Remarks"] = pickup_remarks
            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["ExtraInfo"] = extra_details
            data['addressInfo']["Trips"][0]["Details"][0]["tripInfo"]["CallBackInfo"] = phone_number
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["PickupDate"] = booking_time
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsScheduled"] = is_schedule
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][0]["dateInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalPassengers"] = total_passengers
            data['addressInfo']["Trips"][0]["Details"][0]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs

            # Drop off Address Information
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Address"] = dropoff_street_address
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["City"] = dropoff_city
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Latitude"] = dropoff_lat
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Longitude"] = dropoff_lng
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["State"] = dropoff_state
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Zip"] = dropoff_city_zip_code
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Phone"] = dropoff_phone_number
            data['addressInfo']["Trips"][0]["Details"][1]["addressDetails"]["Remarks"] = dropoff_remarks
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["PickupDate"] = booking_time
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["IsScheduled"] = is_schedule
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["CallBackInfo"] = phone_number
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalPassengers"] = total_passengers
            data['addressInfo']["Trips"][0]["Details"][1]["passengerInfo"]["TotalWheelChairs"] = total_wheelchairs

            # Pickup Cost Information
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedDistance"] = distance_miles
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedTime"] = duration_minutes
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["EstimatedCost"] = total_cost
            data['addressInfo']["Trips"][0]["Details"][0]["estimatedInfo"]["CoPay"] = copay_cost

            # Drop off Cost Information
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedDistance"] = distance
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedTime"] = duration
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["EstimatedCost"] = total_cost
            data['addressInfo']["Trips"][0]["Details"][1]["estimatedInfo"]["CoPay"] = copay_cost

            # adding payload to agent memory

            # if self.main_leg is None:
            #     self.main_leg = data
            if self.return_leg is None:
                self.return_leg = data

            # print(f"\n\n\n Return trip Payload collected: {data}\n\n\n")
            logging.info(f"\n\n\n Return trip Payload collected: {data}\n\n\n")

            return f"The collected payload for return trip is :{data}"

        except Exception as e:
            print(f"\n\nError occurred in collecting trip payload: {e}\n\n")
            return f"error: {e}"

    @function_tool()
    async def book_trips(self):
        """The function book the trip(s) by calling the booking API's that
         uses agent's main_leg and return leg parameter."""

        logging.info("book_trips function called...")

        if self.return_leg:
            payload = await combine_payload(self.main_leg,self.return_leg)
        else:
            payload = self.main_leg

        # Step 2: Set the endpoint
        url = os.getenv("TRIP_BOOKING_API")

        # print(f"\n\n\nPayload Sent for booking: {payload}\n\n\n")
        logging.info("\n\n\nPayload Sent for booking:",payload)

        # Step 3: Send the data to the API
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response = await response.json()

                if response['responseCode'] == 200:

                    irefid_list = [response['iRefID']]
                    if not response['iRefID'] is None:
                        irefid_list.extend(response['returnLegsList'])

                    response_text = ""

                    for trip_data, irefId in zip(payload['addressInfo']["Trips"],irefid_list):
                        estimates = trip_data['Details'][0]['estimatedInfo']
                        pickup_address = trip_data['Details'][0]['addressDetails']
                        dropoff_address = trip_data['Details'][1]['addressDetails']
                        pickup_address_complete = pickup_address['Address'] + pickup_address['City'] + pickup_address['State']
                        dropoff_address_complete = dropoff_address['Address'] + dropoff_address['City'] + dropoff_address['State']
                        estimate_distance = estimates["EstimatedDistance"]
                        estimate_time = estimates['EstimatedTime']
                        estimate_cost = estimates['EstimatedCost']
                        copay_cost = estimates['CoPay']

                        prompt = f"""What is the current weather in {dropoff_address_complete}? Provide a concise response with exactly two lines:
                
                            Line 1: State the temperature in Fahrenheit (numbers only, no unit) and current sky conditions.
                            Line 2: Give relevant weather-appropriate advice.
                
                            Format example:
                            "The temperature is 72 and the sky is clear. It's a perfect day for a ride."
                
                            Requirements:
                            - Temperature in Fahrenheit without the °F unit
                            - Current sky conditions (clear, cloudy, rainy, etc.)
                            - Practical advice based on the weather conditions
                            - Keep response to exactly two lines
                            """
                        weather = await search_web_manual(prompt)
                        print(f"\n\nWeather: {weather}\n\n")

                        # await asyncio.sleep(2)
                        # await self.Stop_Music()

                        try:

                            # Step 4: Process the response
                            if response["responseCode"] == 200:
                                print(f"\n\nResponse: {response}\n\n\n")
                                irefId = response['iRefID']
                                if irefId == 0:
                                    return "Your trip could not be booked!"

                                if str(copay_cost) == "0":
                                    response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and distance between your pick up and drop off is {estimate_distance} miles. Total Cost is {estimate_cost}$. Weather in drop off location is {weather}."
                                else:
                                    response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and distance between your pick up and drop off is {estimate_distance} miles. Total Cost is {estimate_cost}$ and cost related to copay is {copay_cost}$. Weather in drop off location is {weather}."

                            else:
                                response_text += "Trip has not been booked!"

                            return response_text

                        except Exception as e:
                            print(f"\n\nError occured in book a trip function: {e}\n\n")
                            return "Trip has not been booked!"

