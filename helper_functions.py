from livekit.agents import llm  # type: ignore
import asyncio
import os
import re
from twilio.rest import Client
from livekit import rtc
from livekit.agents import BackgroundAudioPlayer, BuiltinAudioClip, AudioConfig
from pathlib import Path
from datetime import datetime, timedelta
import json
import requests
from typing import Annotated
from timezone_utils import now_eastern, format_eastern_timestamp, format_eastern_datetime_iso, parse_eastern_datetime
import aiohttp
from aiohttp import BasicAuth
from openai import AsyncOpenAI
from dotenv import load_dotenv
from livekit.agents import Agent, function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.protocol.sip import TransferSIPParticipantRequest
from livekit import api
from livekit.rtc import SipDTMF
from side_functions import *
from pydantic import Field, BaseModel
from models import ReturnTripPayload, MainTripPayload, RiderVerificationParams, ClientNameParams, DistanceFareParams, AccountParams
from logging_config import get_logger, set_session_id
from InitAssistant import InitAssistant

# Load variables from .env file
load_dotenv()

# Initialize logger
logger = get_logger('helper_functions')

App_Directory = Path(__file__).parent

# Twilio credentials (from environment)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_x_call_id(participant_attributes):
    """
    Extract X-Call-ID from SIP headers in participant attributes.
    
    Args:
        participant_attributes (dict): The participant.attributes dictionary containing SIP headers
        
    Returns:
        str: The X-Call-ID value if found, None otherwise
    """
    try:
        # Check for various possible SIP header formats for X-Call-ID
        possible_keys = [
            'sip.X-Call-ID',
            'sip.x-call-id', 
            'X-Call-ID',
            'x-call-id',
            'sip.header.X-Call-ID',
            'sip.header.x-call-id',
            'sip.h.X-Call-ID',
            'sip.h.x-call-id',
            
        ]
        
        logger.debug(f"Searching for X-Call-ID in participant attributes: {participant_attributes}")
        
        for key in possible_keys:
            if key in participant_attributes:
                x_call_id = participant_attributes[key]
                logger.info(f"✅ Found X-Call-ID: {x_call_id} (key: {key})")
                return x_call_id
        
        # If not found in standard locations, search through all attributes for X-Call-ID pattern
        for key, value in participant_attributes.items():
            if 'call-id' in key.lower() or 'callid' in key.lower():
                logger.info(f"✅ Found potential X-Call-ID: {value} (key: {key})")
                return value
                
        logger.warning("❌ X-Call-ID not found in SIP headers")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting X-Call-ID from SIP headers: {e}")
        return None


class Assistant(Agent):
    def __init__(self, call_sid=None, context=None, room=None, affiliate_id=None, instructions=None, main_leg=None, return_leg=None, rider_phone=None, client_id=None, x_call_id=None):
        self.function_call_count = 0
        self.max_function_calls = 50
        self.failed_function_calls = {}
        """Initialize the assistant with a call SID and LiveKit room."""
        self.call_sid = call_sid  # Store the call SID for music control
        self.room = room  # Store the LiveKit room instance
        self.stop_music = False  # Flag to stop music
        self.music_handle = None  # Handle for background audio control
        self.background_audio = None  # Background audio player instance
        self.affiliate_id = affiliate_id
        self.main_leg = main_leg
        self.return_leg = return_leg
        self.x_call_id = x_call_id  # Store the X-Call-ID from SIP headers
        self.update_rider_phone(rider_phone)
        self.update_client_id(client_id)
        self.context = context
        self.conversation_history = []  # Will be populated from main.py event handlers
        self.suggested_return_time = None
        
        # Log the X-Call-ID if provided
        if self.x_call_id:
            logger.info(f"🆔 [ASSISTANT] X-Call-ID initialized: {self.x_call_id}")
        else:
            logger.debug("🆔 [ASSISTANT] No X-Call-ID provided during initialization")
        
        # Try to initialize Agent with increased function call limits if supported
        try:
            super().__init__(
                instructions=instructions,
                max_function_calls=100,
                function_call_timeout=300
            )
        except TypeError:
            logger.warning("Failed to initialize Agent with increased function call limits")
            # If the parameters aren't supported, fall back to basic initialization
            super().__init__(instructions=instructions)

    @function_tool()
    async def compute_return_time_after_main(self, hours_after: int, payload: MainTripPayload, buffer_minutes: int = 0) -> str:
        """
        Compute return pickup time as: main pickup time + main travel duration + hours_after (+ optional buffer).
        Args:
        - hours_after (int): Number of hours after main pickup time to compute return pickup time.
        - buffer_minutes (int): Optional buffer in minutes to add to the computed return pickup time.
        Behavior:
        - Reads main leg pickup datetime and its estimated duration (in minutes).
        - Computes suggested return pickup datetime.
        - If a return payload already exists in memory, updates its dateInfo.PickupDate.
        - Otherwise stores the suggestion in self.suggested_return_time for later use.

        Returns a human-readable string with the computed time (YYYY-MM-DD HH:MM).
        """
        logger.info(f"✅ [ASSISTANT] Computing return time after main trip with hours_after={hours_after} and buffer_minutes={buffer_minutes}")
        
        try:
            # Get actual travel duration from directions API
            url = os.getenv("GET_DIRECTION")
            params = {
                'origin': f'{payload.pickup_lat},{payload.pickup_lng}',
                'destination': f'{payload.dropoff_lat},{payload.dropoff_lng}',
                'AppType': 'FCSTService'
            }

            logger.debug(f"Payload sent for distance and duration retrieval: {params}")

            auth = BasicAuth(os.getenv("GET_DIRECTION_USER"), os.getenv("GET_DIRECTION_PASSWORD"))
            headers = {
                'User-Agent': 'PostmanRuntime/7.43.4',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }

            # Fetch actual travel duration
            duration_minutes = 0
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, auth=auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Response for distance and duration retrieval: {data}")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        
                        distance_miles = await meters_to_miles(distance)
                        duration_minutes = await seconds_to_minutes(duration)
                        
                        logger.debug(f"Distance: {distance_miles} miles, Duration: {duration_minutes} minutes")
                    else:
                        logger.error(f"Failed to get direction data. Status: {response.status}")
                        return "Could not get travel duration from directions API."

        
            # Extract main pickup datetime using utility function
            main_pickup_str = payload.booking_time
            
            # Parse datetime using timezone utility function with flexible format handling
            logger.debug(f"Attempting to parse booking_time: '{main_pickup_str}'")
            dt = None
            try:
                # Try format with seconds first (YYYY-MM-DD HH:MM:SS)
                dt = parse_eastern_datetime(main_pickup_str, "%Y-%m-%d %H:%M:%S")
                logger.debug(f"Successfully parsed with seconds format: {dt}")
            except ValueError:
                try:
                    # Try format without seconds (YYYY-MM-DD HH:MM)
                    dt = parse_eastern_datetime(main_pickup_str, "%Y-%m-%d %H:%M")
                    logger.debug(f"Successfully parsed without seconds format: {dt}")
                except ValueError as e:
                    logger.error(f"Could not parse datetime '{main_pickup_str}' with either format: {e}")
                    return f"Could not parse main trip pickup time: {main_pickup_str}. Expected format: YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS"
            
            if dt is None:
                return f"Could not parse main trip pickup time: {main_pickup_str}"

            # Calculate return time: pickup + travel duration + hours_after + buffer
            computed = dt + timedelta(minutes=duration_minutes + int(buffer_minutes)) + timedelta(hours=int(hours_after))
            
            # Format using utility function (YYYY-MM-DD HH:MM format)
            suggested_str = format_eastern_timestamp(computed, format_str="%Y-%m-%d %H:%M")

            # Save suggestion for later use (do NOT modify payload yet)
            self.suggested_return_time = suggested_str
            logger.info(f"💾 Stored suggested return time: {suggested_str} (will be used later in collect_return_trip_payload)")

            # Do NOT automatically update return_leg payload here
            # The payload should only be set after user confirmation via collect_return_trip_payload()
            
            return f"Suggested return pickup time is {suggested_str} (based on {duration_minutes} min travel time) "
            
        except KeyError as e:
            logger.error(f"Missing key while computing return time: {e}")
            return "Could not compute return time due to missing data in the main trip."
        except Exception as e:
            logger.error(f"Unexpected error computing return time: {e}")
            return "An error occurred while computing the return time."
    

    def update_rider_phone(self, rider_phone):
        """
        Validates and update US-style phone numbers.
        Accepted formats:
        - 301-208-2222
        - 3012082222
        """
        if rider_phone == None:
            return

        pattern = r"^(?:\d{3}-\d{3}-\d{4}|\d{10})$"
        self.rider_phone = rider_phone

        if not bool(re.match(pattern, rider_phone)):
            logger.warning(f"Invalid phone number format: {rider_phone}")
            self.session.say("The phone number is not correct. Let me transfer you to live agent.", allow_interruptions=False)
            self.transfer_call()

    def update_client_id(self, client_id):
        self.client_id = str(client_id)
        logger.info(f"Client ID {self.client_id}")
        if self.client_id and str(self.client_id) not in ["-1", "0", "None", "none"]:
            logger.info(f"✅ Client ID set to: {self.client_id}")
        else:            
            logger.warning(f"❌ Client ID not available (received: {client_id}) - self.client_id will be None")
    
    def update_affliate_id_and_family(self,affiliate_id,family_id):
        self.affiliate_id=affiliate_id
        self.family_id=family_id
    
    # Old messy conversation history methods removed - now using clean InitAssistant approach
    
    def get_conversation_context(self) -> dict:
        """Get conversation context for transfers using InitAssistant (clean approach)"""
        logger.info(f"🔄 Getting conversation context for call {self.call_sid}")
        
        # Use the clean InitAssistant to get context
        context_data = InitAssistant.get_context_for_transfer(self.call_sid)
        
        if not context_data:
            logger.error(f"❌ No context data generated for call {self.call_sid}")
            return {}
        
        logger.info(f"✅ Context retrieved successfully for call {self.call_sid}")
        return context_data
    
    async def _send_context_to_transfer_api(self, payload: dict) -> bool:
        """Send context data to transfer API (clean approach)"""
        try:
            transfer_api_url = os.getenv('CONTEXT_TRANSFER_API')
            if not transfer_api_url:
                logger.info("📝 CONTEXT_TRANSFER_API not configured - skipping API call")
                return True  # Not an error if not configured
            
            logger.info(f"🚀 Sending context to transfer API: {transfer_api_url}")
            
            # Prepare the payload with call metadata
            api_payload = {
                'call_sid': self.call_sid,
                'timestamp': datetime.now().isoformat(),
                'transfer_payload': payload
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'IVR-Bot-Context-Transfer/1.0'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(transfer_api_url, json=api_payload, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        logger.info(f"✅ Context successfully sent to transfer API")
                        return True
                    else:
                        logger.warning(f"⚠️ Transfer API returned status {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error sending context to transfer API: {e}")
            return False
    
    # Removed unused _generate_json_call_history method - now using InitAssistant._generate_json_history()
    
    async def Play_Music(self) -> str:
        """Function to play background audio using LiveKit's built-in audio clips (same as main.py)."""
        if not self.room:
            return "No active room to play music."

        try:
            logger.info(f"🎵 Starting background audio using LiveKit built-in clips...")
            logger.debug(f"Current state: background_audio={self.background_audio}, music_handle={self.music_handle}")
            
            # Create background audio player with built-in clips (same as main.py)
            if self.background_audio is None:
                logger.debug("Creating new BackgroundAudioPlayer...")
                self.background_audio = BackgroundAudioPlayer(thinking_sound=[
                    AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
                    AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.6)
                ])
                
                # Start the background audio player
                logger.debug("Starting background audio player...")
                await self.background_audio.start(room=self.room)
                logger.info("✅ Initialized background audio player")
            else:
                logger.debug("Background audio player already exists")
            
            # Play typing sound in loop (same as main.py)
            if self.music_handle is None:
                logger.debug("Starting typing sounds...")
                self.music_handle = self.background_audio.play(BuiltinAudioClip.KEYBOARD_TYPING, loop=True)
                logger.info("✅ Started continuous typing sounds")
                self.stop_music = False
            else:
                logger.debug("Typing sounds already playing")
            
            return "Background audio is now playing in the room."
            
        except Exception as e:
            logger.error(f"Error starting background audio: {e}")
            return "Failed to start background audio."

    async def Stop_Music(self) -> str:
        """Function to stop playing background audio in the LiveKit room."""
        if not self.room:
            return "No active room to stop music."

        try:
            logger.info("🛑 Stopping background audio in the LiveKit room...")
            self.stop_music = True  # Set flag to stop music
            
            # Stop the music handle if it exists
            if self.music_handle is not None:
                self.music_handle.stop()
                self.music_handle = None
                logger.info("✅ Stopped typing sounds")

            return "Background audio has been stopped."
        except Exception as e:
            logger.error(f"Error stopping background audio: {e}")
            return "Failed to stop background audio."

    @function_tool()
    async def Close_Call(self) -> str:
        """Function to end Twilio call and disconnect from the LiveKit room.
        Whenever conversation ends with a Bye or Thankyou, call this function."""
        logger.info("Called close call function")
        await self.session.say('Thank you for reaching out. Have a great day!')

        # Step 1: End the Twilio call
        # call_closed_msg = "No active call found."
        # if self.call_sid:
        #     try:
        #         logger.info(f"Requested Call Ending for Call SID: {self.call_sid}")
        #         TWILIO_CLIENT.calls(self.call_sid).update(status="completed")
        #         call_closed_msg = f"Call has been ended successfully."
        #     except Exception as e:
        #         call_closed_msg = f"Failed to end call: {str(e)}"
        try:
            await self.context.api.room.delete_room(
                    api.DeleteRoomRequest(room=self.room.name)
                )
            room_closed_msg = f"Room disconnected successfully."
        except Exception as e:
            room_closed_msg = f"Error disconnecting room: {str(e)}"

        return f"{room_closed_msg}"

        # try:
        #     # Asterisk end call
        #     await self.asterisk_call_disconnect()
        #     logger.info("asterisk call disconnected...")
        #     # TWILIO_CLIENT.calls(self.call_sid).update(status="completed")
        #     call_closed_msg = f"Call has been ended successfully."
        # except Exception as e:
        #     call_closed_msg = f"Failed to end call: {str(e)}"

        # Step 2: Disconnect the LiveKit room
        # room_closed_msg = "No active room found."
        # try:
        #     if self.room and hasattr(self.room, "disconnect"):
        #         logger.info(f"Disconnecting room: {self.room.name}")
        #         await self.room.disconnect()
        #         room_closed_msg = f"Room disconnected successfully."
        # except Exception as e:
        #     room_closed_msg = f"Error disconnecting room: {str(e)}"

        # return f"{call_closed_msg} {room_closed_msg}"

    @function_tool()
    async def get_client_name(self
                              ):
        """Function to get rider profiles including their active or existing rides. And their home address
        Returns:
            str: JSON string with rider profile or error message.
        """

        caller_number = self.rider_phone
        family_id=self.family_id

        logger.info(f"Called get_client_name function with caller_number: {caller_number}, family_id: {family_id}")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        
        logger.debug(f"caller number: {caller_number}")
        logger.debug(f"family_id: {family_id}")

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
            logger.debug(f"Payload before sending: {payload}")
            # Define the headers
            headers = {
                "Content-Type": "application/json",
            }

            logger.debug(f"Payload sent by LLM: {payload}")

            # Step 3: Send the data to the API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response = await response.json()

        except Exception as e:
            logger.error(f"Error occurred in getting rider profile: {e}")
            pass

        result = {}
        rider_count = 0

        try:
            if response["responseCode"] == 200:
                client_object = response["responseJSON"]
                logger.debug(f"Client Object: {client_object}")
                client_list = json.loads(client_object)
                for i, client in enumerate(client_list, 1):
                    name = (client['FirstName'] + ' ' + client['LastName']).strip()
                    client_id = client.get('Id', 0)
                    logger.debug(f"Client ID: {client_id}")
                    number_of_existing_trips, trips_data = await get_Existing_Trips_Number(client_id, self.affiliate_id)

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
                        "number_of_existing_trips": number_of_existing_trips,
                        "trips_data": trips_data
                    }

                    result[f"rider_{i}"] = rider_data
                    rider_count += 1
                # result["number_of_riders"] = rider_count
            else:
                logger.warning("Request failed!")
                result["number_of_riders"] = 1
                result["rider_1"] = {
                    "name": "new_rider",
                    "client_id": "-1",
                    "city": "Unknown",
                    "state": "Unknown",
                    "current_location": "Unknown",
                    "rider_id": "-1",
                    "number_of_existing_trips": 0,
                    "trips_data": ""
                }
        except Exception as e:
            logger.error(f"Error occurred in getting client Name: {e}")
            result["number_of_riders"] = rider_count

        logger.debug(f"Result: {result}")

        # await asyncio.sleep(2)
        # await self.Stop_Music()

        logger.info(f"✅ [GET_CLIENT_NAME] rider_count: {rider_count}")
        data = json.dumps(result, indent=2)
        
        # Only set self.client_id if there is exactly one profile
        if rider_count > 1:
            logger.info(f"✅ [GET_CLIENT_NAME] Multiple profiles found ({rider_count}). Use select_rider_profile() to choose one.")
            # return f"Multiple profiles found. count is {rider_count}. detail {data}. When user select profile, call select_rider_profile() function."
        elif rider_count == 1:
            logger.info(f"✅ [GET_CLIENT_NAME] Only one profile found. Setting self.client_id to {result['rider_1']['client_id']}")
            self.client_id = str(result['rider_1']['client_id'])
        else:
            logger.info(f"❌ [GET_CLIENT_NAME] No profiles found or new rider.")

        return data

    @function_tool()
    async def select_rider_profile(self, profile_name: str, profile_number: int = 0) -> str:
        """
        Function to select a specific rider profile when multiple profiles are found and user provides profile name or profile number.
        This updates the self.client_id and self.rider_id with the selected profile's values.
        The profile_name is the primary way to select - profile_number is optional.
        
        Args:
            profile_name (str): The name of the profile to select (REQUIRED)
            profile_number (int): Optional profile number (1, 2, 3, etc.) - will be auto-determined from name if not provided
        Returns:
            str: Confirmation message with selected profile details or error message
        """
        logger.info(f"🔍 [SELECT_RIDER_PROFILE] Called with profile_name: '{profile_name}', profile_number: {profile_number}")
        
        try:
            # Call get_client_name to get all profiles again
            caller_number = self.rider_phone
            family_id = self.family_id
            
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
                'Content-Type': 'application/json'
            }
            
            # Send the data to the API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response = await response.json()
            
            if response["responseCode"] == 200:
                client_object = response["responseJSON"]
                client_list = json.loads(client_object)
                
                # Check if profile_name matches any existing profile
                if profile_name:
                    provided_name_lower = profile_name.strip().lower()
                
                    # Check if this name exists in any of the profiles
                    name_exists = False
                    for client in client_list:
                        existing_name = (client['FirstName'] + ' ' + client['LastName']).strip().lower()
                        
                        if provided_name_lower == existing_name:
                            name_exists = True
                            break
                    # If profile name doesn't match any existing profile, return error only
                    if not name_exists:
                        self.client_id = -1
                        logger.info(f"Client ID {self.client_id}")
                        if self.client_id not in [ "0", "None", "none"]:
                            logger.info(f"✅ Client ID set to: {self.client_id}")
                        else:            
                            logger.warning(f"❌ Client ID not available (received: {client_id}) - self.client_id will be None")
                        return """That profile does not exist in our system. However, if you want to create a new profile you have to book a trip with us first."""
                
                # Check if the requested profile number exists
                if profile_number < 1 or profile_number > len(client_list):
                    return f"Invalid profile number. Please select a number between 1 and {len(client_list)}."
                
                # Get the selected profile (profile_number is 1-indexed)
                selected_client = client_list[profile_number - 1]
                
                # Update self.client_id and self.rider_id with selected profile
                selected_client_id = selected_client.get('Id', 0)
                
                # Get rider_id from MedicalId
                medical_id_raw = selected_client.get("MedicalId", "")
                if medical_id_raw and str(medical_id_raw).isdigit():
                    selected_rider_id = int(medical_id_raw)
                    selected_rider_id = selected_rider_id if selected_rider_id != 0 else "0"
                else:
                    selected_rider_id = "0"
                
                self.rider_id = selected_rider_id
                
                # Get profile details for confirmation
                name = (selected_client['FirstName'] + ' ' + selected_client['LastName']).strip()
                city = selected_client.get("City", "Unknown")
                state = selected_client.get("State", "Unknown")
                address = selected_client.get("Address", "Unknown")
                
                logger.info(f"[PROFILE SELECTION] Updated client_id to: {self.client_id}")
                logger.info(f"[PROFILE SELECTION] Updated rider_id to: {self.rider_id}")
                
                # Also call the existing update_client_id method to ensure consistency
                self.update_client_id(str(selected_client_id))
                
                logger.info(f"🎯 [SELECT_RIDER_PROFILE] Successfully selected profile for {name} - client_id: {self.client_id}, rider_id: {self.rider_id}")
                
                return f"""Profile selected successfully!
                    Selected Profile: {name}
                    Client ID: {self.client_id}
                    Rider ID: {self.rider_id}
                    Location: {city}, {state}
                    Address: {address}
                    I have updated your profile information. You can now proceed with booking trips or checking your ride information."""
                
            else:
                return "Error: Could not retrieve profiles. Please try again."
                
        except Exception as e:
            logger.error(f"Error in select_rider_profile: {e}")
            return f"Error selecting profile: {str(e)}. Please try again."

    @function_tool()
    async def get_ETA(self) -> str:
        """
        Function to get CURRENT/ACTIVE/EXISTING rides and trips:
            - Current active rides status
            - Existing booked trips that are not yet completed
            - Live trip ETA and location
            - Where their current ride/vehicle is right now
            - Active trip pickup/dropoff details
            - Real-time trip information
        
        Use this for: "Where is my ride?", "What's my ETA?", "Do I have any current trips?"
        
        Uses the client_id that was retrieved during initial phone number lookup,
        eliminating the need for LLM to provide client_id (which can cause hallucinations).
        
        Returns:
            str: JSON string with trip details or error message.
        """
        logger.info("Called get_ETA function")

        # Use the stored client_id from initial phone lookup instead of LLM parameter
        if not self.client_id:
            logger.warning("Client ID not available in get_ETA, attempting to retrieve it...")
            # Try to get client info first
            try:
                await self.get_client_name()
                if not self.client_id:
                    logger.warning("❌ Client ID not available after retrieving client info in get_ETA")
                    return "I need to identify you first. Let me search for your profile using your phone number."
            except Exception as e:
                logger.error(f"❌ Error retrieving client info in get_ETA: {e}")
                return "I'm having trouble accessing your profile. Please try again."
        
        logger.debug(f"✅ Using stored client_id get_ETA: {self.client_id}")

        # Start background music task
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("EXISTING_RIDES_API")

        payload = {
            "searchCriteria": "CustomerID",
            "searchText": self.client_id,
            "bActiveRecords": True,
            "iATSPID": int(self.affiliate_id),
            "responseJSON": "string",
            "responseCode": 100
        }

        headers = {
            "Content-Type": "application/json"
        }

        logger.debug(f"Payload Sent for Existing Trips: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    # await asyncio.sleep(2)
                    # await self.Stop_Music()

                    try:
                        response = json.loads(text)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON. Raw response: {text}")
                        return "No data found for ETA!"

                    if response.get("responseCode") == 200:
                        try:
                            data = json.loads(response.get("responseJSON", "{}"))
                            logger.debug(f"Response: {data}")
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

                            logger.debug(f"ETA Response: {existing_trips_data}")
                            return existing_trips_data
                        except json.JSONDecodeError:
                            logger.error("Failed to decode nested responseJSON")
                            return "No data found for ETA!"
                    else:
                        logger.info("No trip ETA Found for the rider")
                        return "No data found for ETA!"

        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()

            logger.error(f"Error occurred in getting client ETA: {e}")
            return "No data found for ETA!"

    @function_tool()
    async def search_web(
        self,
        prompt: Annotated[str, Field(description="Prompt for web search. Keep it as precise and to the point as possible at max 3-4 lines.")]
    ) -> str:
        """
        Function to search web to get knowledge.
        Args:
            prompt (str): Prompt for web search. Pydantic validated.
        Returns:
            str: Output text from web search or error message.
        """
        logger.info("Called search_web function")
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        logger.debug(f"web search payload: {prompt}")

        try:
            # Use the OpenAI API client to make the call
            response = await openai_client.responses.create(
                model="gpt-4o", # do not change this model, this is must for web address search
                tools=[{
                        "type": "web_search_preview",
                        "search_context_size": "low",
                        "user_location": {
                            "type": "approximate",
                            "country": "US",
                            "timezone": "America/New_York"
                        }
                    }],
                input=prompt
            )
            
            # Track token usage for cost calculation
            try:
                from cost_tracker import add_websearch_usage
                logger.debug(f"Response object type: {type(response)}")
                
                if hasattr(response, 'usage') and response.usage:
                    logger.debug(f"Usage object: {response.usage}")
                    # For OpenAI responses API, tokens are in input_tokens/output_tokens, not prompt_tokens/completion_tokens
                    input_tokens = getattr(response.usage, 'input_tokens', 0)
                    output_tokens = getattr(response.usage, 'output_tokens', 0)
                    logger.debug(f"Extracted token values - input: {input_tokens}, output: {output_tokens}")
                    add_websearch_usage(input_tokens, output_tokens, "gpt-4o")
                    logger.debug(f"Web search usage: {input_tokens} input, {output_tokens} output tokens")
                else:
                    logger.warning(f"No usage information available in response. Response type: {type(response)}")
                    # Estimate tokens based on text length as fallback
                    estimated_input = len(prompt.split()) * 1.3  # Rough estimate
                    
                    # Extract text from the response structure for estimation
                    text_content = ""
                    if hasattr(response, 'output') and response.output:
                        for item in response.output:
                            if hasattr(item, 'type') and item.type == 'message':
                                if hasattr(item, 'content') and item.content:
                                    for content_item in item.content:
                                        if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                            text_content = content_item.text
                                            break
                                if text_content:
                                    break
                        # Fallback if structure parsing fails
                        if not text_content:
                            text_content = str(response.output)
                    
                    estimated_output = len(text_content.split()) * 1.3 if text_content else 0
                    logger.info(f"Using estimated tokens - input: {estimated_input:.0f}, output: {estimated_output:.0f}")
                    add_websearch_usage(int(estimated_input), int(estimated_output), "gpt-4o")
            except Exception as usage_error:
                logger.warning(f"Failed to track web search usage: {usage_error}")

            # Output the result
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            
            # Extract text from the response structure
            if hasattr(response, 'output') and response.output:
                # response.output is a list of response objects
                for item in response.output:
                    if hasattr(item, 'type') and item.type == 'message':
                        # This is a ResponseOutputMessage
                        if hasattr(item, 'content') and item.content:
                            for content_item in item.content:
                                if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                    # This is ResponseOutputText with the actual text
                                    return content_item.text
                # Fallback to string representation if structure parsing fails
                return str(response.output)
            else:
                logger.error(f"Could not extract text from response. Available attributes: {dir(response)}")
                return "Unable to extract response text"

        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            logger.error(f"Error in search web: {e}")
            return "Web search failed!"

    @function_tool()
    async def get_valid_addresses(
        self,
        address: Annotated[str, Field(description="Complete Address confirmed by the rider to be validated.")]
    ) -> str:
        """
        Function to search valid addresses based on input address.
        Args:
            address (str): Complete Address confirmed by the rider to be validated. Pydantic validated.
        Returns:
            str: JSON string with valid address information or error message.
        """
        logger.info(f"Called get_valid_address function with address: {address}")
        # await self.session.say('Let me verify if that address is valid. Please wait a moment.')
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        result = {}

        try:
            result = await verify_address(address)
            logger.debug(f"Valid Addresses Result from Web Search: {result}")
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
            logger.error("Error in getting valid address status")

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
                            result[f"Location_{i + 1}"] = {}
                            result[f"Location_{i + 1}"]["Address"] = location["formatted_address"]
                            result[f"Location_{i + 1}"]["Coordinates"] = location['geometry']['location']

                            # Extract latitude and longitude
                            lat = location['geometry']['location']['lat']
                            lng = location['geometry']['location']['lng']
                            is_within_service_area = await self.check_bounds(lat, lng)
                            result[f"Location_{i + 1}"]["isWithinServiceArea"] = is_within_service_area

                    else:
                        logger.error(f"ITC location error: status {resp.status}")
        except Exception as e:
            logger.error(f"ITC location exception: {e}")

        # await asyncio.sleep(2)
        # await self.Stop_Music()
        logger.debug(f"Valid Addresses from ITC MAP API: {result}")
        return str(result)

    @function_tool()
    async def check_bounds(
        self,
        latitude: Annotated[str, Field(description="Latitude of the location to be checked.")],
        longitude: Annotated[str, Field(description="Longitude of the location to be checked.")]
    ) -> bool:
        """
        Function to check if the address is within the service area based on provided coordinates.
        Args:
            latitude (str): Latitude of the location to be checked.
            longitude (str): Longitude of the location to be checked.
        Returns:
            bool: True if within bounds, False otherwise.
        """
        logger.info("Called check_bounds function")
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        bounds, _, _ = await fetch_affiliate_details(self.affiliate_id)

        logger.debug(f"Bounds: {bounds}")

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
    async def get_IDs(
        self,
        params: Annotated[AccountParams, Field(description="Parameters for account and payment method")]
    ) -> str:
        """
        Function to fetch Funding Source Id, Program Id, Payment Type, and Copay Status based on provided account and affiliate details.
        Args:
            params (AccountParams): Contains account parameters:
                - account_ (str): Account name provided by the rider.
                - payment_method (str): Payment method provided by the rider.
        Returns:
            str: Verification summary or error message.
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        logger.info("Called get_IDs function")
        
        # Extract parameters from the model
        account_ = params.account_
        payment_method = params.payment_method

        account = account_.lower()
        pattern = r'\b(cash|card)\b'
        if re.search(pattern, account):
            account = 'self'
        else:
            account = account_
        logger.debug(f"Confirmed Account Name: {account}")

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
            logger.debug(f"Prompt sent for matching funding sources: {prompt}")

            response = await get_match_source(prompt)
            logger.debug(f"Matching Response: {response}")

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

                logger.debug(f"Got Program Id: {program_id}")
                logger.debug(f"Got Funding Source Id: {funding_id}")
                logger.debug(f"Funding Source List: {copay_fs_list}")
                logger.debug(f"Selected Account Name: {account_name}")

                try:
                    funding_id_str = str(funding_id)

                    if funding_id_str == "1":
                        copay_status = False

                    elif funding_id_str in copay_fs_list:
                        copay_status = True

                    logger.debug(f"Got Copay Status: {copay_status}")

                except Exception as e:
                    logger.error(f"Error in getting copay status: {e}")

                try:
                    url = os.getenv("GET_PAYMENT_TPYE_AFFILIATE_API")

                    # Define the payload
                    data = {
                        "iaffiliateid": str(self.affiliate_id)
                    }

                    logger.debug(f"Payload Sent for Payment Type Selection: {data}")

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

                                    Your task is to find the dictionary whose 'PaymentType Name' value closely matches
                                     the account enclosed in double quotes: ``{payment_method}``

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
                                    logger.debug(f"Prompt sent for matching funding sources: {paymenttype_prompt}")

                                    paymenttype_response = await get_match_source(paymenttype_prompt)
                                    logger.debug(f"Matching Response: {paymenttype_response}")

                                    paymenttype_response = json.loads(paymenttype_response)

                                    paymenttype_id = paymenttype_response.get("PaymentType ID", None)

                                except Exception as e:
                                    logger.error(f"Failed to decode JSON from string: {e}")

                except Exception as e:
                    logger.error(f"Error in getting payment type id: {e}")
                    pass

            except Exception as e:
                logger.error(f"Error parsing JSON: {e}")
                pass

        except Exception as e:
            logger.error(f"Error in getting FID and require verification status: {e}")
            pass

        if program_id == -1:
            rider_verification = False
        else:
            rider_verification = True

        # await asyncio.sleep(2)
        # await self.Stop_Music()

        logger.info(f"Verified Account Name is: {account_name}, Funding Source Id is: {funding_id}, "
              f"Requires Rider Verification Status: {rider_verification}, Payment Type Id is: {paymenttype_id}, "
              f"Require Copay Status is: {copay_status}, Program Id is {program_id}")
        return (f"Verified Account Name is: {account_name}, Funding Source Id is: {funding_id},"
                f" Requires Rider Verification Status: {rider_verification}, Payment Type Id is: {paymenttype_id},"
                f" Require Copay Status is: {copay_status}, Program Id is {program_id}")

    @function_tool()
    async def get_copay_ids(
        self,
        copay_account_name: Annotated[str, Field(description="Copay Account Name provided by the rider")]
    ) -> str:
        """
        Function to fetch copay payment type based on affiliate ID and copay account name.
        Args:
            copay_account_name (str): Copay Account Name provided by the rider.
        Returns:
            str: Copay verification summary or error message.
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        logger.info("Called get_copay_payment_type_id function")

        copay_funding_source_id, payment_type_id = -1, -1
        _, funding_sources, _ = await fetch_affiliate_details(self.affiliate_id)

        prompt = f"""
        You are given a list of dictionaries enclosed in triple backticks: ```{funding_sources}```

        Your task is to find the dictionary whose 'FundingSource' value closely matches the account enclosed in
         double quotes: ``{copay_account_name}``. 

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
        logger.debug(f"Prompt sent for matching funding sources: {prompt}")

        response = await get_match_source(prompt)
        logger.debug(f"Matching Response: {response}")

        try:
            parsed_response = json.loads(response)

            copay_funding_source_id = parsed_response.get("FID", None)
            copay_program_id = parsed_response.get("ProgramID", None)
            copay_program_id = int(copay_program_id)
            verified_copay_account_name = parsed_response.get("FundingSource", None)

            logger.debug(f"Got Copay Program Id: {copay_program_id}")
            logger.debug(f"Got Copay Funding Source Id: {copay_funding_source_id}")

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
                        logger.debug(f"Response dict: {response_dict}")
                    except Exception as e:
                        logger.error(f"Failed to decode JSON from string: {e}")

        prompt = f"""
        You are given a list of dictionaries enclosed in triple backticks: ```{response_dict}```

        Your task is to find the dictionary whose 'PaymentType Name' value closely matches the account
         enclosed in double quotes: ``{copay_account_name}``. 

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
        logger.debug(f"Prompt sent for matching funding sources: {prompt}")

        response = await get_match_source(prompt)
        logger.debug(f"Matching Response: {response}")

        try:
            parsed_response = json.loads(response)
            payment_type_id = int(parsed_response["PaymentType ID"])
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            pass

        # await asyncio.sleep(2)
        # await self.Stop_Music()
        logger.debug(f"Copay Funding Source Id: {copay_funding_source_id}")
        logger.debug(f"Copay Payment Type Id: {payment_type_id}")

        return (
            f"Verified Copay Account Name is: {verified_copay_account_name}, Copay Funding Source Id is: {copay_funding_source_id} and"
            f" Copay Payment Type Id: {payment_type_id}")

    @function_tool()
    async def verify_rider(
        self,
        params: Annotated[RiderVerificationParams, Field(description="Parameters for rider verification")]
    ) -> str:
        """
        Function to verify rider based on rider_id, affiliate_id, and program_id.
        Args:
            params (RiderVerificationParams): Contains rider verification parameters:
                - rider_id (str): Rider Id, else -1.
                - program_id (str): Program Id, else -1.
        Returns:
            str: Verification result message.
        """
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        logger.info("Called verify_rider function")
        
        rider_id = params.rider_id
        program_id = params.program_id

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
                            logger.error(f"Failed to decode JSON from string: {e}")

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

                            logger.debug(f"Rider Name Retrieval Result: {response_text}")

                            try:
                                # Try to convert the string to a dictionary
                                response_dict = json.loads(response_text)
                                verified_rider_name += str(response_dict["FirstName"]) + " "
                                verified_rider_name += str(response_dict["LastName"])

                            except Exception as e:
                                logger.error(f"Failed to decode JSON from string: {e}")

            logger.debug(f"Rider Verification Status: {rider_status}")
            logger.debug(f"Verified Rider Name: {verified_rider_name}")
        except Exception as e:
            logger.error(f"Error in verifying_rider_id: {e}")
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
    async def get_Trip_Stats(self) -> str:
        """Function to get detailed statistics and analytics about trips:
        - Trip performance metrics
        - Statistical data about ride patterns
        - Analytics and reporting information
        - Trip statistics and summaries
        
        Use this for analytical queries about trip data, not for current ride status.
        
        Uses the client_id that was retrieved during initial phone number lookup,
        eliminating the need for LLM to provide client_id (which can cause hallucinations).
        
        Returns:
            JSON string if successful, or error string if failed
        """

        logger.info("Called get_Trip_Stats function")
        
        # Use the stored client_id from initial phone lookup instead of LLM parameter
        if not self.client_id:
            logger.warning("Client ID not available in get_Trip_Stats, attempting to retrieve it...")
            # Try to get client info first
            try:
                await self.get_client_name()
                if not self.client_id:
                    logger.warning("❌ Client ID not available after retrieving client info in get_Trip_Stats")
                    return "I need to identify you first. Let me search for your profile using your phone number."
            except Exception as e:
                logger.error(f"❌ Error retrieving client info in get_Trip_Stats: {e}")
                return "I'm having trouble accessing your profile. Please try again."
        
        logger.debug(f"✅ Using stored client_id get_Trip_Stats: {self.client_id}")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        # Define the API endpoint
        url = os.getenv("TRIP_STATS_API")

        # Create the payload (request body)
        payload = {
            "iclientid": self.client_id
        }

        # Define the headers
        headers = {
            "Content-Type": "application/json"
        }

        logger.debug(f"Payload Sent for trip stats: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    logger.debug(f"Status: {resp.status}")
                    logger.debug(f"Headers: {resp.headers}")

                    # Read text response and try to parse as JSON manually
                    text = await resp.text()

                    try:
                        data = json.loads(text)
                        logger.debug(f"Response: {data}")
                        # await asyncio.sleep(2)
                        # await self.Stop_Music()
                        return json.dumps(data, indent=4)
                    except json.JSONDecodeError:
                        # await asyncio.sleep(2)
                        # await self.Stop_Music()
                        logger.error(f"Failed to decode JSON. Raw response: {text}")
                        return "No valid JSON data found!"

        except Exception as e:
            # await asyncio.sleep(2)
            # await self.Stop_Music()
            logger.error(f"Error occurred in getting trip stats: {e}")
            return "No data found!"

    @function_tool()
    async def get_historic_rides(self) -> str:
        """Function to get COMPLETED/PAST/HISTORICAL rides and trips:
        - Previously completed trips
        - Past ride history
        - Historical trip records
        - Finished/performed trips from previous days/weeks
        - Trip history for reference
        - Completed journey records
        
        Use this for: "Show my past trips", "What trips did I take last week?", "My ride history"
        
        Uses the client_id that was retrieved during initial phone number lookup,
        eliminating the need for LLM to provide client_id (which can cause hallucinations).
        
        Returns:
            String with JSON or error message
        """

        logger.info("Called get_historic_rides function")
        
        # Use the stored client_id from initial phone lookup instead of LLM parameter
        if not self.client_id:
            logger.warning("Client ID not available in get_historic_rides, attempting to retrieve it...")
            # Try to get client info first
            try:
                await self.get_client_name()
                if not self.client_id:
                    logger.warning("❌ Client ID not available after retrieving client info in get_historic_rides")
                    return "I need to identify you first. Let me search for your profile using your phone number."
            except Exception as e:
                logger.error(f"❌ Error retrieving client info in get_historic_rides: {e}")
                return "I'm having trouble accessing your profile. Please try again."
        
        logger.debug(f"✅ Using stored client_id get_historic_rides: {self.client_id}")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("GET_HISTORIC_RIDES_API")

        payload = {
            "clientID": str(self.client_id),
            "affiliateID": str(self.affiliate_id),
            "bGetAddressDataOnly": "false",
            "responseCode": 100
        }

        headers = {
            "Content-Type": "application/json"
        }

        historic_trips_data = ""
        logger.debug(f"Payload sent to get frequent addresses: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"Response from FrequentDataAPI: {response_text}")
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
                        logger.error("Failed to parse response as JSON.")
                        logger.error(f"Raw Response: {response_text}")
        except Exception as e:
            logger.error(f"Error occurred in getting historic rides: {e}")

        if historic_trips_data.strip() == "":
            historic_trips_data = "No Data Available"

        historic_trips_data_result = f"""Rider Historic/Past/Completed Trips are: ``{historic_trips_data}``\n
        """
        logger.debug(f"Historic Rides: {historic_trips_data}")
        # await asyncio.sleep(2)
        # await self.Stop_Music()
        return historic_trips_data_result

    @function_tool()
    async def get_frequnt_addresses(self) -> str:
        """Function to get Rider Frequently Used Addresses
        
        Uses the client_id that was retrieved during initial phone number lookup,
        eliminating the need for LLM to provide client_id (which can cause hallucinations).
        
        Returns:
            String with addresses or error message
        """

        logger.info("Called get_frequnt_addresses function")
        
        # Use the stored client_id from initial phone lookup instead of LLM parameter
        if not self.client_id:
            logger.warning("Client ID not available in get_frequnt_addresses, attempting to retrieve it...")
            # Try to get client info first
            try:
                await self.get_client_name()
                if not self.client_id:
                    logger.warning("❌ Client ID not available after retrieving client info in get_frequnt_addresses")
                    return "I need to identify you first. Let me search for your profile using your phone number."
            except Exception as e:
                logger.error(f"❌ Error retrieving client info in get_frequnt_addresses: {e}")
                return "I'm having trouble accessing your profile. Please try again."
        
        logger.debug(f"✅ Using stored client_id get_frequnt_addresses: {self.client_id}")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)

        url = os.getenv("GET_HISTORIC_RIDES_API")

        payload = {
            "clientID": str(self.client_id),
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
        logger.debug(f"Payload sent to get frequent addresses: {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"Response from FrequentDataAPI: {response_text}")
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
                        logger.error("Failed to parse response as JSON.")
                        logger.error(f"Raw Response: {response_text}")
        except Exception as e:
            logger.error(f"Error occurred in getting frequent addresses: {e}")

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
        params: Annotated[DistanceFareParams, Field(description="Parameters for distance and fare calculation")]
    ) -> str:
        """
        Function to get distance and trip duration between two locations.

        Args:
            params (DistanceFareParams): Contains distance and fare parameters:
                - pickup_latitude (str): Pickup Address Latitude in string. If not available, set it to 0.
                - pickup_longitude (str): Pickup Address Longitude in string. If not available, set it to 0.
                - dropoff_latitude (str): Dropoff Address Latitude in string. If not available, set it to 0.
                - dropoff_longitude (str): Dropoff Address Longitude in string. If not available, set it to 0.
                - number_of_wheel_chairs (str): Number of wheel chairs if required by rider else 0. For example if rider is missing leg or specifically says, 'they require wheel chair'.
                - number_of_passengers (str): Number of passengers. If rider mentioned more than 1 passengers, set accordingly otherwise set it to 1.
                - rider_id (str): Rider Id available in the memory either already in the memory or provided by the customer. If not available set it to 0.
        Returns:
            str: Distance, duration, and fare information.
        """

        logger.info("Called get_distance_duration_fare function")

        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        
        # Extract parameters from the model
        pickup_latitude = params.pickup_latitude
        dropoff_latitude = params.dropoff_latitude
        pickup_longitude = params.pickup_longitude
        dropoff_longitude = params.dropoff_longitude
        number_of_wheel_chairs = params.number_of_wheel_chairs
        number_of_passengers = params.number_of_passengers
        rider_id = params.rider_id
        
        # Set default values for fare calculation (since this function doesn't have payment info)
        funding_source_id = "1"  # Default cash payment
        copay_funding_source_id = "-1"  # No copay by default
        pickup_lat = pickup_latitude
        pickup_lng = pickup_longitude

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

            logger.debug(f"Payload Sent for distance and duration retrieval: {params}")

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
                        logger.debug(f"Response for distance and duration retrieval: {data}")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        logger.debug(f"Distance: {distance}")
                        logger.debug(f"Duration: {duration}")

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

                        logger.debug(f"Payload for fare estimation: {data}")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    response_data = await response.json()
                                    logger.debug(f"Response for fare estimation: {response_data}")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    logger.debug(f"Total Cost: {total_cost}")
                                    logger.debug(f"Copay Cost: {copay_cost}")
                                else:
                                    logger.error(f"Request failed with status code: {response.status}")

                    else:
                        logger.error(f"Request failed with status code {response.status_code}")

        except Exception as e:
            logger.error(f"Error in getting distance and duration: {e}")

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
    async def get_client_id(self):
        """
        Function that is used to get the client id.
        Returns:
            str: Client id.
        """
        return self.client_id

    @function_tool()
    async def get_customer_phone_number(self):
        """
        Function that is used to get the customer phone number.
        Returns:
            str: Customer phone number.
        """
        return self.rider_phone

    @function_tool()
    async def collect_main_trip_payload(self, payload: MainTripPayload) -> str:
        """
        Function that is used to collect the payload for the main trip.
        Args:
            payload (MainTripPayload): Pydantic model containing all main trip payload fields.
        Returns:
            str: Confirmation message or error message.
        """
        
        # Enable transfers when main trip booking process starts
        try:
            if hasattr(self, "session") and self.session is not None:
                setattr(self.session, "should_allow_transfer", True)
                # Set transfer status in logging context for visual indicator
                from logging_config import set_transfer_status
                set_transfer_status("ENABLED")
                logger.info("🟢 TRANSFER ENABLED: Main trip booking process started - user can get help")
        except Exception as e:
            logger.warning(f"❌ Failed to enable transfers for main trip booking: {e}")
        # Extract all payload fields to local variables for minimal refactor impact
        pickup_street_address = payload.pickup_street_address
        dropoff_street_address = payload.dropoff_street_address
        pickup_city = payload.pickup_city
        dropoff_city = payload.dropoff_city
        pickup_state = payload.pickup_state
        dropoff_state = payload.dropoff_state
        extra_details = payload.extra_details

        # Use stored client_id instead of LLM-provided one to prevent hallucinations
        logger.debug(f"✅ [MAIN TRIP DEBUG] self.client_id = {self.client_id} (type: {type(self.client_id)})")
        logger.debug(f"✅ [MAIN TRIP DEBUG] payload.client_id = {payload.client_id} (type: {type(payload.client_id)})")

        if (self.client_id and str(self.client_id) not in ["-1", "0", "None", "none"]):
            client_id = str(self.client_id)
            logger.info(f"✅ [MAIN TRIP] Using stored client_id: {client_id} (overriding LLM provided: {payload.client_id})")
        else:
            logger.warning("❌ Client ID not available in collect_main_trip_payload, attempting to retrieve it...")
            client_id = -1
                    
        logger.debug(f"✅ Using stored client_id collect_main_trip_payload: {client_id}")
        funding_source_id = payload.funding_source_id
        rider_name = payload.rider_name
        payment_type_id = payload.payment_type_id
        copay_funding_source_id = payload.copay_funding_source_id
        copay_payment_type_id = payload.copay_payment_type_id
        booking_time = payload.booking_time
        pickup_lat = payload.pickup_lat
        pickup_lng = payload.pickup_lng
        dropoff_lat = payload.dropoff_lat
        dropoff_lng = payload.dropoff_lng
        rider_id = payload.rider_id
        number_of_wheel_chairs = payload.number_of_wheel_chairs
        number_of_passengers = payload.number_of_passengers
        is_schedule = payload.is_schedule
        pickup_city_zip_code = payload.pickup_city_zip_code
        dropoff_city_zip_code = payload.dropoff_city_zip_code
        rider_home_address = payload.rider_home_address
        rider_home_city = payload.rider_home_city
        rider_home_state = payload.rider_home_state
        home_phone = payload.home_phone
        office_phone = payload.office_phone
        total_passengers = payload.total_passengers
        total_wheelchairs = payload.total_wheelchairs
        is_will_call = payload.is_will_call
        will_call_day = payload.will_call_day
        pickup_remarks = payload.pickup_remarks
        pickup_phone_number = payload.pickup_phone_number
        dropoff_remarks = payload.dropoff_remarks
        dropoff_phone_number = payload.dropoff_phone_number
        logger.info(f"Called collect_trip_payload function at: {now_eastern()}")
        phone_number = self.rider_phone
        family_id = self.family_id

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

            logger.debug(f"Payload Sent for distance and duration retrieval: {params}")

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
                        logger.debug(f"Response for distance and duration retrieval: {data}")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        logger.debug(f"Distance: {distance}")
                        logger.debug(f"Duration: {duration}")
                        url = os.getenv("GET_FARE_API")

                        distance_miles = await meters_to_miles(distance)
                        duration_minutes = await seconds_to_minutes(duration)

                        # The JSON body data to be sent in the POST request
                        data = {
                            "distance": distance_miles,
                            "travelTime": duration_minutes,
                            "fundingSourceID": int(funding_source_id) if funding_source_id and funding_source_id.strip() else 1,
                            "copy": 0,
                            "numberOfWheelchairs": int(number_of_wheel_chairs) if number_of_wheel_chairs and number_of_wheel_chairs.strip() else 0,
                            "numberOfPassengers": int(number_of_passengers) if number_of_passengers and number_of_passengers.strip() else 1,
                            "classOfServiceID": 1,
                            "affiliateID": int(self.affiliate_id),
                            "pickupLatitude": float(pickup_lat),
                            "pickupLongitude": float(pickup_lng),
                            "copyFundingSourceID": int(copay_funding_source_id) if copay_funding_source_id and copay_funding_source_id.strip() else -1,
                            "riderID": str(rider_id) if rider_id else "0",
                            "authorizedStaff": "string",
                            "startFareZone": "string",
                            "endFareZone": "string",
                            "tspid": "string",
                            "httpResponseCode": 100
                        }

                        logger.debug(f"Payload for fare estimation: {data}")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    response_data = await response.json()
                                    logger.debug(f"Response for fare estimation: {response_data}")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    logger.debug(f"Total Cost: {total_cost}")
                                    logger.debug(f"Copay Cost: {copay_cost}")
                                else:
                                    logger.error(f"Request failed with status code: {response.status}")

                    else:
                        logger.error(f"Request failed with status code: {response.status}")

        except Exception as e:
            logger.error(f"Error in getting fare: {e}")
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
            logger.error(f"Error in getting schedule status: {e}")
            pass

        try:

            payload_path = os.path.join(App_Directory, "trip_book_payload.json")
            # Step 1: Read the JSON file
            with open(payload_path, 'r') as file:
                data = json.load(file)

            logger.debug(f"Phone number by LLM: {phone_number}")
            phone_number = await format_phone_number(phone_number)
            logger.debug(f"Phone number after formatting: {phone_number}")

            rider_id = await safe_int(rider_id)
            affiliate_id = await safe_int(self.affiliate_id)
            family_id = await safe_int(family_id)
            funding_source_id = await safe_int(funding_source_id)
            payment_type_id = await safe_int(payment_type_id)
            copay_funding_source_id = await safe_int(copay_funding_source_id)
            copay_payment_type_id = await safe_int(copay_payment_type_id)
            if client_id == 0:
                logger.warning(f"✅ [MAIN TRIP] 🚨 Converting client_id from 0 to -1 at line 1748")
                client_id = -1
            
            # Handle two scenarios for riderInfo based on whether rider is new or existing
            # Scenario 1: First ride (no client_id) - New rider
            if self.client_id and str(self.client_id) not in ["-1", "0", "None", "none"]: 
                # Scenario 2: Existing rider (has client_id)
                logger.info(f"🚨 [MAIN TRIP] Existing rider scenario - client_id: {self.client_id}")
                data["riderInfo"]["ID"] = int(self.client_id)
                data["riderInfo"]["MedicalId"] = "0"  # String "0" for existing riders
                data["riderInfo"]["RiderID"] = "0"    # String "0" for existing riders               
            else:
                logger.info("✅[MAIN TRIP] First ride scenario - New rider (no client_id)")
                data["riderInfo"]["ID"] = -1
                data["riderInfo"]["MedicalId"] = ""  # Empty string for new riders
                data["riderInfo"]["RiderID"] = "0"   # String "0" for new riders
            
            if is_will_call:
                is_schedule = True
            
            # Common riderInfo fields for both scenarios
            data["riderInfo"]["PhoneNo"] = phone_number
            data["riderInfo"]["PickupPerson"] = rider_name
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
            data['addressInfo']["Trips"][0]["Details"][0]["Name"] = rider_name
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
            data['addressInfo']["Trips"][0]["Details"][1]["Name"] = rider_name
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
            # data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["WillCallDay"] = will_call_day
            # data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["IsWillCall"] = is_will_call
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

            data['insuranceInfo']['MedicalID'] = rider_id

            # adding payload to agent memory

            # if self.main_leg is None:
            self.main_leg = data
            # elif self.return_leg is None:
            #     self.return_leg = data

            logger.debug(f"Payload collected: {data}")

            return f"Payload for main trip has been collected! Ask the rider if they would like to book a return trip."

        except Exception as e:
            logger.error(f"Error occurred in collecting trip payload: {e}")
            return f"error: {e}"

    @function_tool()
    async def return_trip_started(self) -> str:
        """
        Call this function when user expresses intent to book a return trip,
        BEFORE collecting any return trip information. This enables transfers
        so user can get help during the return trip information collection process.
        """
        # Enable transfers when return trip process starts (before information collection)
        try:
            if hasattr(self, "session") and self.session is not None:
                setattr(self.session, "should_allow_transfer", True)
                # Set transfer status in logging context for visual indicator
                from logging_config import set_transfer_status
                set_transfer_status("ENABLED")
                logger.info("🟢 TRANSFER ENABLED: Return trip process started - user can get help during information collection")
        except Exception as e:
            logger.warning(f"❌ Failed to enable transfers for return trip process: {e}")

        return "Return trip process started! Transfers enabled for user assistance during information collection."

    @function_tool()
    async def collect_return_trip_payload(self, payload: ReturnTripPayload) -> str:
        """
        Function that is used to collect return trip payload.
        Args:
            payload (ReturnTripPayload): Pydantic model containing all return trip payload fields.
        Returns:
            str: Confirmation message or error message.
        """
        
        # Note: Transfers should already be enabled by return_trip_started() function
        # This function is called after information collection is complete
        
        # Extract all payload fields to local variables for minimal refactor impact
        pickup_street_address = payload.pickup_street_address
        dropoff_street_address = payload.dropoff_street_address
        pickup_city = payload.pickup_city
        dropoff_city = payload.dropoff_city
        pickup_state = payload.pickup_state
        dropoff_state = payload.dropoff_state
        # Use stored client_id instead of LLM-provided one to prevent hallucinations
        if self.client_id:
            client_id = str(self.client_id)
            logger.info(f"[RETURN TRIP] ✅ Using stored client_id: {client_id} (overriding LLM provided: {payload.client_id})")
        else:
            client_id = payload.client_id
            logger.warning(f"[RETURN TRIP] ⚠️ Warning: Using LLM-provided client_id: {client_id} (stored client_id not available)")
        extra_details = payload.extra_details
        phone_number = payload.phone_number
        funding_source_id = payload.funding_source_id
        rider_name = payload.rider_name
        payment_type_id = payload.payment_type_id
        copay_funding_source_id = payload.copay_funding_source_id
        copay_payment_type_id = payload.copay_payment_type_id
        booking_time = payload.booking_time
        pickup_lat = payload.pickup_lat
        pickup_lng = payload.pickup_lng
        dropoff_lat = payload.dropoff_lat
        dropoff_lng = payload.dropoff_lng
        rider_id = payload.rider_id
        number_of_wheel_chairs = payload.number_of_wheel_chairs
        number_of_passengers = payload.number_of_passengers
        family_id = payload.family_id
        is_schedule = payload.is_schedule
        pickup_city_zip_code = payload.pickup_city_zip_code
        dropoff_city_zip_code = payload.dropoff_city_zip_code
        rider_home_address = payload.rider_home_address
        rider_home_city = payload.rider_home_city
        rider_home_state = payload.rider_home_state
        home_phone = payload.home_phone
        office_phone = payload.office_phone
        total_passengers = payload.total_passengers
        total_wheelchairs = payload.total_wheelchairs
        is_will_call = payload.is_will_call
        will_call_day = payload.will_call_day
        pickup_remarks = payload.pickup_remarks
        pickup_phone_number = payload.pickup_phone_number
        dropoff_remarks = payload.dropoff_remarks
        dropoff_phone_number = payload.dropoff_phone_number
        logger.info(f"Called collect_return_trip_payload function at: {now_eastern()}")
        # Start playing music asynchronously
        # _ = asyncio.create_task(self.Play_Music())
        # await asyncio.sleep(2)
        if client_id == 0:
            logger.warning(f"[RETURN TRIP] 🚨 Converting client_id from 0 to -1 at line 1924")
            client_id = -1
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

            logger.debug(f"Payload Sent for distance and duration retrieval: {params}")

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
                        logger.debug(f"Response for distance and duration retrieval: {data}")
                        distance = int(data["routes"][0]["legs"][0]["distance"]["value"])
                        duration = int(data["routes"][0]["legs"][0]["duration"]["value"])
                        logger.debug(f"Distance: {distance}")
                        logger.debug(f"Duration: {duration}")
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

                        logger.debug(f"Payload for fare estimation: {data}")

                        # Headers to be used in the request
                        headers = {
                            'Content-Type': 'application/json',  # Ensure that the body is sent as JSON
                            'User-Agent': 'PostmanRuntime/7.43.4',  # Optional, can be omitted if not needed
                        }

                        # Making the POST request
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, json=data, headers=headers) as response:
                                if response.status == 200:
                                    response_data = await response.json()
                                    logger.debug(f"Response for fare estimation: {response_data}")
                                    total_cost = response_data["totalCost"]
                                    copay_cost = response_data["copay"]
                                    logger.debug(f"Total Cost: {total_cost}")
                                    logger.debug(f"Copay Cost: {copay_cost}")
                                else:
                                    logger.error(f"Request failed with status code: {response.status}")

                    else:
                        logger.error(f"Request failed with status code: {response.status}")

        except Exception as e:
            logger.error(f"Error in getting fare: {e}")
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
            logger.error(f"Error in getting schedule status: {e}")
            pass

        try:

            payload_path = os.path.join(App_Directory, "trip_book_payload.json")
            # Step 1: Read the JSON file
            with open(payload_path, 'r') as file:
                data = json.load(file)

            logger.debug(f"Phone number by LLM: {phone_number}")
            phone_number = await format_phone_number(phone_number)
            logger.debug(f"Phone number after formatting: {phone_number}")

            rider_id = await safe_int(rider_id)
            affiliate_id = await safe_int(self.affiliate_id)
            family_id = await safe_int(family_id)
            funding_source_id = await safe_int(funding_source_id)
            payment_type_id = await safe_int(payment_type_id)
            copay_funding_source_id = await safe_int(copay_funding_source_id)
            copay_payment_type_id = await safe_int(copay_payment_type_id)
            if client_id == 0:
                logger.warning(f"[RETURN TRIP] 🚨 Converting client_id from 0 to -1 at line 2072")
                client_id = -1
            
            # Handle two scenarios for riderInfo based on whether rider is new or existing
            # Scenario 1: First ride (no client_id) - New rider
            if not self.client_id or str(self.client_id) == "-1" or str(self.client_id) == "0":
                logger.info("[RETURN TRIP] First ride scenario - New rider (no client_id)")
                data["riderInfo"]["ID"] = -1
                data["riderInfo"]["MedicalId"] = ""  # Empty string for new riders
                data["riderInfo"]["RiderID"] = "0"   # String "0" for new riders
            else:
                # Scenario 2: Existing rider (has client_id)
                logger.info(f"[RETURN TRIP] Existing rider scenario - client_id: {self.client_id}")
                data["riderInfo"]["ID"] = int(self.client_id)
                data["riderInfo"]["MedicalId"] = "0"  # String "0" for existing riders
                data["riderInfo"]["RiderID"] = "0"    # String "0" for existing riders

            if is_will_call:
                is_schedule = True
            
            # Common riderInfo fields for both scenarios
            data["riderInfo"]["PhoneNo"] = phone_number
            data["riderInfo"]["PickupPerson"] = rider_name
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
            data['addressInfo']["Trips"][0]["Details"][0]["Name"] = rider_name
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
            data['addressInfo']["Trips"][0]["Details"][1]["Name"] = rider_name
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
            # data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["WillCallDay"] = will_call_day
            # data['addressInfo']["Trips"][0]["Details"][1]["tripInfo"]["IsWillCall"] = is_will_call
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["WillCallDay"] = will_call_day
            data['addressInfo']["Trips"][0]["Details"][1]["dateInfo"]["IsWillCall"] = is_will_call
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

            data['insuranceInfo']['MedicalID'] = rider_id

            # adding payload to agent memory

            # if self.main_leg is None:
            #     self.main_leg = data
            # if self.return_leg is None:
            self.return_leg = data

            logger.debug(f"Return trip Payload collected: {data}")
            logger.debug(f"return trip payload: {data}")

            return f"Payload for return trip has been collected!"

        except Exception as e:
            logger.error(f"Error occurred in collecting trip payload: {e}")
            return f"error: {e}"

    @function_tool()
    async def book_trips(self) -> str:
        """
        The function books the trip(s) by calling the booking APIs that use the agent's main_leg and return_leg parameters.
        Returns:
            str: Booking confirmation, error message, or API response summary.
        """

        logger.info("book_trips function called...")
        
        # Start playing music during booking process
        try:
            await self.Play_Music()
            logger.info("🎵 Started playing music during trip booking")
        except Exception as e:
            logger.warning(f"Failed to start music during booking: {e}")
        
        try:
            # Check if function is called with empty arguments
            if not hasattr(self, 'main_leg') or not hasattr(self, 'return_leg'):
                logger.warning("book_trips called but no leg attributes exist")
                # Stop music before early return
                try:
                    await self.Stop_Music()
                    logger.info("🔇 Stopped music - no leg attributes")
                except Exception as e:
                    logger.warning(f"Failed to stop music: {e}")
                return "Please provide trip details before booking. You need to specify at least pickup and dropoff locations."
            # Check if legs exist but are empty
            if not self.main_leg and not self.return_leg:
                logger.warning("Both legs are None or empty")
                # Stop music before early return
                try:
                    await self.Stop_Music()
                    logger.info("🔇 Stopped music - no trip details")
                except Exception as e:
                    logger.warning(f"Failed to stop music: {e}")
                return "No trip details found. Please provide pickup and dropoff information before booking."

            # Prepare the payload based on available legs
            if self.return_leg and self.main_leg:
                payload = await combine_payload(self.main_leg, self.return_leg)
            elif self.main_leg:
                payload = self.main_leg
            elif self.return_leg:
                payload = self.return_leg
            else:
                payload = None
                
            if not payload:
                logger.warning("No booking payload available from any source")
                # Stop music before early return
                try:
                    await self.Stop_Music()
                    logger.info("🔇 Stopped music - no payload available")
                except Exception as e:
                    logger.warning(f"Failed to stop music: {e}")
                return "Error: No valid trip details found. Please provide pickup and dropoff information."

            # Step 2: Set the endpoint
            url = os.getenv("TRIP_BOOKING_API")

            # Properly log the payload
            logger.debug(f"Payload Sent for booking: {payload}")
            payload_call_id = self.call_sid
            with open(f"logs/trip_book_payload/final_payload_{payload_call_id}.txt","w") as f:
                f.write(json.dumps(payload, indent=4))

            # Step 3: Send the data to the API with proper error handling
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    # Check if response status is OK before trying to parse JSON
                    if response.status != 200:
                        logger.error(f"Booking API HTTP Error: {response.status}")
                        # Stop music after HTTP error
                        try:
                            await self.Stop_Music()
                            logger.info("🔇 Stopped music after HTTP error")
                        except Exception as e:
                            logger.warning(f"Failed to stop music after HTTP error: {e}")
                        return f"Trip booking failed with HTTP status {response.status}. Please try again later."
                    
                    # Try to parse the response as JSON with better error handling
                    try:
                        response_data = await response.json()
                    except Exception as e:
                        logger.error(f"Booking API JSON Parsing Error: {e}, Content-Type: {response.headers.get('Content-Type')}")
                        # Try to get text response as fallback
                        text_response = await response.text()
                        logger.debug(f"Raw response: {text_response[:200]}...")
                        # Stop music after JSON parsing error
                        try:
                            await self.Stop_Music()
                            logger.info("🔇 Stopped music after JSON parsing error")
                        except Exception as e2:
                            logger.warning(f"Failed to stop music after JSON parsing error: {e2}")
                        return f"Trip booking system returned an invalid response format. Please try again later."

                    # Continue processing if we successfully parsed JSON
                    if response_data.get('responseCode') == 200:

                        irefid_list = [response_data.get('iRefID')]
                        if response_data.get('returnLegsList') is not None:
                            irefid_list.append(response_data.get('returnLegsList'))

                        response_text = ""

                        for trip_data, irefId in zip(payload['addressInfo']["Trips"], irefid_list):
                            estimates = trip_data['Details'][0]['estimatedInfo']
                            pickup_address = trip_data['Details'][0]['addressDetails']
                            dropoff_address = trip_data['Details'][1]['addressDetails']
                            pickup_address_complete = f" {pickup_address['Address']}  {pickup_address['City']}  {pickup_address['State']}"
                            dropoff_address_complete = f" {dropoff_address['Address']}  {dropoff_address['City']} {dropoff_address['State']}"
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
                            logger.debug(f"Weather: {weather}")

                            try:

                                if str(copay_cost) == "0":
                                    response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and distance between your pick up and drop off is {estimate_distance} miles. Estimated cost is {estimate_cost}$. Weather in drop off location is {weather}."
                                else:
                                    response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and distance between your pick up and drop off is {estimate_distance} miles. Estimated cost is {estimate_cost}$ and cost related to copay is {copay_cost}$. Weather in drop off location is {weather}."

                            except Exception as e:
                                logger.error(f"Error occurred in book a trip function: {e}")

                        # Determine what type of booking was made to decide on transfer logic
                        booking_type = "unknown"
                        if self.return_leg and self.main_leg:
                            booking_type = "round_trip"
                        elif self.main_leg:
                            booking_type = "main_trip_only"
                        elif self.return_leg:
                            booking_type = "return_trip_only"
                        
                        logger.info(f"Booking completed for: {booking_type}")
                        
                        self.main_leg = None
                        self.return_leg = None

                        # Transfer disable logic: Disable transfers after ANY successful booking completion
                        # This prevents unnecessary escalations after successful bookings
                        try:
                            if hasattr(self, "session") and self.session is not None:
                                setattr(self.session, "should_allow_transfer", False)
                                # Set transfer status in logging context for visual indicator
                                from logging_config import set_transfer_status
                                set_transfer_status("DISABLED")
                                logger.info(f"🔴 TRANSFER DISABLED: {booking_type} booking completed successfully - no more escalations needed")
                        except Exception as e:
                            logger.warning(f"Unable to disable transfers after booking: {e}")

                        logger.info(f"Booking response: {response_text}")
                        
                        # Stop music after successful booking
                        try:
                            await self.Stop_Music()
                            logger.info("🔇 Stopped music after successful trip booking")
                        except Exception as e:
                            logger.warning(f"Failed to stop music after booking: {e}")
                        
                        return response_text
                    
                    else:
                        error_message = response_data.get("responseMessage", "Unknown error")
                        error_code = response_data.get("responseCode", "Unknown")
                        logger.error(f"Booking API Payload ERROR: Code {error_code} - {error_message}")
                        
                        # Stop music after booking error
                        try:
                            await self.Stop_Music()
                            logger.info("🔇 Stopped music after booking error")
                        except Exception as e:
                            logger.warning(f"Failed to stop music after booking error: {e}")
                        
                        return f"Trip has not been booked. Error: {error_message}"

        except Exception as e:
            logger.error(f"Booking API Server ERROR: {e}")
            
            # Stop music after server error
            try:
                await self.Stop_Music()
                logger.info("🔇 Stopped music after server error")
            except Exception as e2:
                logger.warning(f"Failed to stop music after server error: {e2}")
            
            return f"error in booking:{e}"

    @function_tool()
    async def asterisk_call_disconnect(
        self,
        participant_identity: Annotated[str | None, Field(description="Participant identity to disconnect")] = None,
        room_name: Annotated[str | None, Field(description="Room name for the call")] = None
    ) -> None:
        """
        Function to disconnect a participant from the Asterisk call via LiveKit.
        Args:
            participant_identity (str | None): Participant identity to disconnect. Pydantic validated.
            room_name (str | None): Room name for the call. Pydantic validated.
        Returns:
            None
        """
        try:
            logger.info("Asterisk call disconnect function called...")
            async with api.LiveKitAPI() as livekit_api:
                asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
                transfer_to = f"sip:6000@{str(asterisk_ip)}"
                # transfer_to = "sip:6000@139.64.158.216"
                participant_identity = list(self.room.remote_participants.values())[0].identity
                logger.info(f"participant: {participant_identity}")
                # Create transfer request
                transfer_request = TransferSIPParticipantRequest(
                    participant_identity=participant_identity,
                    room_name=self.room.name,
                    transfer_to=transfer_to,
                    play_dialtone=False,
                    # wait_until_answered=True,
                )
                logger.debug(f"Transfer request: {transfer_request}")

                # Transfer caller
                await livekit_api.sip.transfer_sip_participant(transfer_request)

                
                logger.info(f"Call disconnected ...")
        except Exception as e:
            logger.info(e)

    # @function_tool()
    # async def send_dtmf_code(self, code: int, context: RunContext):
    #     room = context.session.room
    #     await room.local_participant.publish_dtmf(code=code, digit=str(code))

    @function_tool()
    async def transfer_call(self) -> str:
        """
        Function to transfer the call to a live agent using LiveKit and Asterisk SIP transfer.
        Also sends context information to CONTEXT_TRANSFER_API if configured.
        
        Returns:
            str: Success message or error message if transfer fails.
        """
        logger.info("transfer_call_voice function called...")
        
        # Step 0: Context generation is now handled cleanly by InitAssistant
        logger.info(f"🔍 Starting transfer for call {self.call_sid}")
        logger.info(f"   - InitAssistant will handle conversation context generation")
        logger.info(f"   - Active conversations: {InitAssistant.get_active_calls()}")
        
        # Step 1: Send complete booking payload with context to transfer API if available
        try:
            context_data = self.get_conversation_context()
            logger.info(f"🔍 Transfer context debug:")
            logger.info(f"   - context_data type: {type(context_data)}")
            logger.info(f"   - context_data keys: {list(context_data.keys()) if context_data else 'None'}")
            logger.info(f"   - context_data has values: {any(context_data.values()) if context_data else False}")
            
            # Prepare the complete booking payload (same as book_trips function)
            complete_transfer_payload = None
            
            # Check for main_leg and return_leg separately
            main_leg = getattr(self, 'main_leg', None)
            return_leg = getattr(self, 'return_leg', None)
            
            logger.debug(f"Checking for booking payload:")
            logger.debug(f"  main_leg exists: {main_leg is not None}")
            logger.debug(f"  return_leg exists: {return_leg is not None}")
            
            if return_leg and main_leg:
                complete_transfer_payload = await combine_payload(main_leg, return_leg)
                logger.debug("  Using combined payload (main + return)")
            elif main_leg:
                complete_transfer_payload = main_leg
                logger.debug("  Using main_leg payload")
            elif return_leg:
                complete_transfer_payload = return_leg
                logger.debug("  Using return_leg payload")
            
            # Log transfer condition check
            logger.info(f"Transfer payload check: complete_payload={complete_transfer_payload is not None}, context_data={context_data is not None}, main_leg={main_leg is not None}, return_leg={return_leg is not None}")
            
            # Always try to add context information if we have context data
            if complete_transfer_payload and context_data and any(context_data.values()):
                logger.info("✅ Adding context information to existing booking payload")
                # Add context information to the complete booking payload
                for trip in complete_transfer_payload.get('addressInfo', {}).get('Trips', []):
                    for detail in trip.get('Details', []):
                        if 'tripInfo' in detail:
                            # Add context parameters to tripInfo (TRANSFER SCENARIOS ONLY)
                            detail['tripInfo']['ContextCallTitle'] = context_data.get('ContextCallTitle', '')
                            detail['tripInfo']['ContextCallSummary'] = context_data.get('ContextCallSummary', '')
                            detail['tripInfo']['ContextCallDetail'] = context_data.get('ContextCallDetailJson', '')
                            detail['tripInfo']['ContextCallDetailHtml'] = context_data.get('ContextCallDetailHtml', '')
                            logger.debug(f"Added context to {detail.get('StopType', 'unknown')} tripInfo in existing payload")
                
                # Log the complete transfer payload
                logger.debug(f"Complete transfer payload with context: {complete_transfer_payload}")
            
            # If no complete payload exists, load default and add context
            if not complete_transfer_payload:
                # Load default payload from JSON file and update with current rider info
                logger.info("Loading default payload from trip_book_payload.json and updating with current rider info")
                try:
                    # Load the default payload
                    with open("/home/devlab/ivr-directory/temp/trip_book_payload.json", "r") as f:
                        default_payload = json.load(f)
                    
                    # Update rider information with current values
                    if hasattr(self, 'rider_phone') and self.rider_phone:
                        default_payload['riderInfo']['PhoneNo'] = self.rider_phone
                    
                    if hasattr(self, 'client_id') and self.client_id:
                        if self.client_id == "None":
                            default_payload['riderInfo']['ID'] = "-1"
                        else:
                            default_payload['riderInfo']['ID'] = self.client_id
                    
                    # Update rider name in pickup person and dropoff name if available
                    rider_name = getattr(self, 'rider_name', '') or getattr(self, 'pickup_person', '') or "Customer"
                    default_payload['riderInfo']['PickupPerson'] = rider_name
                    
                    # Update names in trip details
                    for trip in default_payload.get('addressInfo', {}).get('Trips', []):
                        for detail in trip.get('Details', []):
                            if detail.get('StopType') == 'pickup':
                                detail['Name'] = rider_name
                            elif detail.get('StopType') == 'dropoff':
                                detail['Name'] = rider_name
                    
                    # Add context information if available (TRANSFER ONLY)
                    logger.info(f"🔍 Transfer context check for default payload:")
                    logger.info(f"   - context_data exists: {context_data is not None}")
                    logger.info(f"   - context_data type: {type(context_data)}")
                    logger.info(f"   - context_data keys: {list(context_data.keys()) if context_data else 'None'}")
                    logger.info(f"   - context_data has values: {any(context_data.values()) if context_data else False}")
                    
                    if context_data and any(context_data.values()):
                        logger.info("✅ Adding context information to default transfer payload")
                        trips_updated = 0
                        for trip in default_payload.get('addressInfo', {}).get('Trips', []):
                            for detail in trip.get('Details', []):
                                if 'tripInfo' in detail:
                                    # Add context parameters to tripInfo (TRANSFER SCENARIOS ONLY)
                                    detail['tripInfo']['ContextCallTitle'] = context_data.get('ContextCallTitle', '')
                                    detail['tripInfo']['ContextCallSummary'] = context_data.get('ContextCallSummary', '')
                                    detail['tripInfo']['ContextCallDetail'] = context_data.get('ContextCallDetailJson', '')
                                    detail['tripInfo']['ContextCallDetailHtml'] = context_data.get('ContextCallDetailHtml', '')
                                    trips_updated += 1
                                    logger.info(f"   ✅ Added context to {detail.get('StopType', 'unknown')} tripInfo")
                        logger.info(f"✅ Successfully added context to {trips_updated} trip details")
                    else:
                        logger.warning("❌ No context data available for default transfer payload")
                        if context_data:
                            logger.warning(f"   - Context data exists but all values are empty: {context_data}")
                        else:
                            logger.warning("   - Context data is None or empty")
                    
                    # Log the updated default payload
                    complete_transfer_payload = default_payload
                    logger.debug(f"Updated transfer payload: {complete_transfer_payload}")
                except Exception as e:
                    logger.error(f"Error loading or updating default payload: {e}")
                    logger.info("No complete booking payload or conversation context available for transfer")
            
            payload_call_id = self.call_sid
            try:
                # Create directory if it doesn't exist
                os.makedirs("logs/context_transfer_payload", exist_ok=True)
                
                # Store the updated payload
                with open(f"logs/context_transfer_payload/context_transfer_{payload_call_id}.txt", "w") as f:
                    f.write(json.dumps(complete_transfer_payload, indent=4))
                logger.info(f"📄 Updated transfer payload saved to logs/context_transfer_payload/context_transfer_{payload_call_id}.txt")
            except Exception as e:
                logger.warning(f"Warning: Could not save updated transfer payload to file: {e}")
            
            # Send updated payload to transfer API (clean approach)
            context_sent = await self._send_context_to_transfer_api(complete_transfer_payload)
            if context_sent:
                logger.info("✅ Updated booking payload with context sent to transfer API successfully")
            else:
                logger.warning("⚠️ Failed to send updated booking payload to transfer API")

        except Exception as e:
            logger.error(f"⚠️ Error sending context to transfer API: {e}")
            # Continue with transfer even if context sending fails
        
        # Step 2: Perform the actual SIP transfer
        try:
            async with api.LiveKitAPI() as livekit_api:
                asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
                transfer_to = f"sip:5000@{str(asterisk_ip)}"
                logger.info(f"transfer sip: {transfer_to}")
                # transfer_to = "sip:5000@139.64.158.216"
                participant_identity = list(self.room.remote_participants.values())[0].identity
                logger.info(f"participant_identity: {participant_identity}")
                # Create transfer request
                transfer_request = TransferSIPParticipantRequest(
                    participant_identity=participant_identity,
                    room_name=self.room.name,
                    transfer_to=transfer_to,
                    play_dialtone=False,
                    # wait_until_answered=True,
                )
                logger.debug(f"Transfer request: {transfer_request}")

                # Transfer caller
                await livekit_api.sip.transfer_sip_participant(transfer_request)
                logger.info(f"Successfully transferred participant {participant_identity} to {transfer_to}")
                
                # Clean up conversation tracker after successful transfer
                self.cleanup_conversation()
                
                return "Call successfully transferred to human agent"
                
        except Exception as e:
            logger.error(f"Error during SIP transfer: {e}")
            return "Issue with call transfer"

    @function_tool()
    async def get_current_date_and_time(self) -> str:
        """
        Get the current date and time for immediate ride booking.

        This should be called when the user says they need to book a ride right now.
        It returns the exact current date and time so the ride can be booked for
        the present moment.

        Returns:
            str: Current date and time in 'YYYY-MM-DD HH:MM' format 
                (e.g., '2025-10-03 19:00').
        """
        logger.info("get_current_date_and_time eastern function called...")
        return format_eastern_timestamp(format_str='%Y-%m-%d %H:%M')

