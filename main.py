import os
import pytz
import logging
import pymongo
import uuid
from bson.objectid import ObjectId
from pathlib import Path
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AgentSession,
    RoomInputOptions,
    metrics,
    ConversationItemAddedEvent,
    BackgroundAudioPlayer,
    BuiltinAudioClip,
    AudioConfig,
    MetricsCollectedEvent
)
from livekit.plugins import (
    openai,
    deepgram,
    silero,
)
from livekit import api
from livekit.rtc import SipDTMF
from livekit.protocol.sip import TransferSIPParticipantRequest
from livekit.plugins.turn_detector.english import EnglishModel
from helper_functions import *
from side_functions import *
from datetime import datetime
import copy
from supervisor import Supervisor
import cache_manager


load_dotenv()

# Configure logging to suppress pymongo debug messages
logging.getLogger('pymongo').setLevel(logging.WARNING)
LOG_FILENAME = "application.log"

logging.basicConfig(
    level=logging.DEBUG,  # Capture all log levels
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILENAME, mode='a')
    ]
)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client.costlogger
costlogs_collection = db.costlogs

# Default user ID - replace with actual user ID when available
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
# print(os.getenv('LIVEKIT_API_SECRET'))
Agent_Directory = Path(__file__).parent

load_dotenv(dotenv_path=".env")
logger = logging.getLogger("voice-agent")


async def transfer_call_dtmf(participant, room, participant_identity: str = None, room_name: str = None) -> None:
    try:
        logger.info("In call transfer dtmf function....")
        async with api.LiveKitAPI() as livekit_api:
            asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
            transfer_to = f"sip:5000@{str(asterisk_ip)}"
            # transfer_to = "sip:5000@139.64.158.216"
            participant_identity = list(participant.remote_participants.values())[0].identity
            # Create transfer request
            transfer_request = TransferSIPParticipantRequest(
                participant_identity=participant_identity,
                room_name=room,
                transfer_to=transfer_to,
                play_dialtone=False,
                # wait_until_answered=True,
            )
            logger.debug(f"Transfer request: {transfer_request}")

            # Transfer caller
            await livekit_api.sip.transfer_sip_participant(transfer_request)
            logger.info(f"User Pressed 0 and Call transferred to: {transfer_to}")
    except Exception as e:
        logger.info(e)


async def transfer_call_dtmf_driver(participant, room, participant_identity: str = None, room_name: str = None) -> None:
    try:
        async with api.LiveKitAPI() as livekit_api:
            asterisk_ip = os.getenv("ASTERISK_SERVER_IP")
            transfer_to = f"sip:5001@{str(asterisk_ip)}"
            # transfer_to = "sip:5001@139.64.158.216"
            participant_identity = list(participant.remote_participants.values())[0].identity
            # Create transfer request
            transfer_request = TransferSIPParticipantRequest(
                participant_identity=participant_identity,
                room_name=room,
                transfer_to=transfer_to,
                play_dialtone=False,
                # wait_until_answered=True,
            )
            logger.debug(f"Transfer request: {transfer_request}")

            # Transfer caller
            await livekit_api.sip.transfer_sip_participant(transfer_request)
            logger.info(f"Successfully transferred  to {transfer_to}")
    except Exception as e:
        logger.info(e)

class PhoneNumberCollector:
    """Handle phone number collection via voice and DTMF"""
    def __init__(self):
        self.collecting_phone = False
        self.current_number = ""
        self.collection_start_time = None
        
    def start_collection(self):
        """Start collecting a phone number"""
        self.collecting_phone = True
        self.current_number = ""
        self.collection_start_time = datetime.now()
        logger.info("Started phone number collection")
        
    def add_digit(self, digit: str):
        """Add a digit to the current number"""
        if digit.isdigit():
            self.current_number += digit
            logger.info(f"Added digit {digit}, current number: {self.current_number}")
            
    def clear_number(self):
        """Clear the current number being collected"""
        self.current_number = ""
        logger.info("Cleared phone number")
        
    def finish_collection(self):
        """Finish collection and return the number"""
        self.collecting_phone = False
        number = self.current_number
        self.current_number = ""
        logger.info(f"Finished phone collection: {number}")
        return number
        
    def is_valid_phone(self, number: str) -> bool:
        """Check if the collected number is valid (10 digits)"""
        digits_only = re.sub(r'\D', '', number)
        return len(digits_only) >= 10
        
    def format_phone(self, number: str) -> str:
        """Format phone number for display"""
        digits_only = re.sub(r'\D', '', number)
        if len(digits_only) == 10:
            return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only[0] == '1':
            return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        else:
            return number
async def handle_phone_dtmf(digit: str, session, collector: PhoneNumberCollector):
    """Handle DTMF during phone number collection"""
    
    if digit == "*":
        
        # Finalize phone number collection
        number = collector.finish_collection()
        if collector.is_valid_phone(number):
            formatted_number = collector.format_phone(number)
            await session.generate_reply(
                instructions=f"Customer entered {formatted_number} via keypad. Say 'I have {formatted_number} for your phone number. Is that correct?' and wait for confirmation.",
                allow_interruptions=True
            )
        else:
            await session.generate_reply(
                instructions="The number seems too short. Please enter your complete 10-digit phone number and press pound when finished.",
                allow_interruptions=True
            )
    elif digit == "#":
        # Reset phone number collection
        collector.clear_number()
        await session.generate_reply(
            instructions="Let me get your phone number again. Please enter it using the keypad and press pound when finished.",
            allow_interruptions=True
        )
    elif digit.isdigit():
        # Add digit to the current number being collected
        collector.add_digit(digit)
        # Optional: provide feedback after every few digits
        #if len(collector.current_number) % 3 == 0 and len(collector.current_number) > 0:
         #   await session.generate_reply(
          #      instructions=f"I have {len(collector.current_number)} digits so far. Continue entering your number and press pound when finished.",
           #     allow_interruptions=False
            #)

def setup_room_dtmf_handler(room: rtc.Room, session, phone_collector, agent):
    """Setup the SIP DTMF handler for the room"""
    
    @room.on("sip_dtmf_received")
    def dtmf_received(dtmf: rtc.SipDTMF):
        logger.info(f"DTMF received from {dtmf.participant.identity}: {dtmf.code} / {dtmf.digit}")
        
        digit = dtmf.digit
        
        # Only process DTMF when explicitly collecting phone numbers
        if phone_collector.collecting_phone:
            logger.info(f"Processing DTMF {digit} for phone collection")
            asyncio.create_task(handle_phone_dtmf(digit, session, phone_collector))
        else:
            logger.info(f"DTMF {digit} ignored - not in phone collection mode")
            # Don't process DTMF if not collecting phone numbers

async def entrypoint(ctx: agents.JobContext):
    """
    Main entry point for the IT Curves Bot application.
    
    Key features:
    1. Immediate greeting for quick user engagement
    2. Background processing of API calls with caching
    3. Personalized follow-up after data is loaded
    """
    # Store active tasks to prevent garbage collection
    _active_tasks = set()

    # async def async_handle_text_stream(reader, participant_identity):
    #     info = reader.info
    #
    #     print(
    #         f'Text stream received from {participant_identity}\n'
    #         f'  Topic: {info.topic}\n'
    #         f'  Timestamp: {info.timestamp}\n'
    #         f'  ID: {info.id}\n'
    #         f'  Size: {info.size}'  # Optional, only available if the stream was sent with `send_text`
    #     )
    #
    #     # Option 1: Process the stream incrementally using an async for loop.
    #     async for chunk in reader:
    #         print(f"Next chunk: {chunk}")
    #
    #     # Option 2: Get the entire text after the stream completes.
    #     text = await reader.read_all()
    #     print(f"Received text: {text}")

    # def handle_text_stream(reader, participant_identity):
    #     task = asyncio.create_task(async_handle_text_stream(reader, participant_identity))
    #     _active_tasks.add(task)
    #     task.add_done_callback(lambda t: _active_tasks.remove(t))
    #
    # ctx.room.register_text_stream_handler(
    #     "my-topic",
    #     handle_text_stream
    # )

    await ctx.connect()

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()

    # # Twilio code commented
    # call_sid = participant.attributes.get("sip.twilio.callSid", "Unknown")
    # if call_sid == "Unknown":
    call_sid = 'chat-' + str(uuid.uuid4())
    print(f"\n\nCall SID: {call_sid}\n\n")
    
    # Set up the session and background audio early to prepare for immediate greeting
    background_audio = BackgroundAudioPlayer(thinking_sound=[
        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.6)
    ])
    
    allow_interruption_status = False
    
    session = AgentSession(
        stt=deepgram.STT(model="nova-2-phonecall", language="en"),
        allow_interruptions=allow_interruption_status,
        llm=openai.LLM(model="gpt-4.1-mini", temperature=0.5),
        tts=deepgram.TTS(model="aura-asteria-en"),
        vad=silero.VAD.load(min_silence_duration=0.75),
        turn_detection=EnglishModel(),
    )
    
    # Simple default prompt to start with - will be updated later
    default_prompt = """You are a Caring, Sympathetic voice assistant helping riders with their queries. Your primary goal is to provide efficient and clear assistance while maintaining casual tone. Keep your responses concise and clear since this is a voice interface.
Your name is Alina and you are an AI assistant for agency whose name is mentioned in the greetings. Keep your tone casual like a human and not extremely professional.
Service Area in which the company/agency operates are also included in the greetings.."""
    
    
    # Create agent with default prompt initially
    initial_agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=default_prompt, affiliate_id=65)
    
    # Set a simple flag we can use to track interruption state
    interruptions_enabled = False
    
    # Ensure interruptions are disabled for the initial greeting
    session.allow_interruptions = False
    
    # Use the existing background audio player created earlier
    print("Using pre-configured background audio player for typing sounds")
    
    await session.start(
        room=ctx.room,
        agent=initial_agent,
        room_input_options=RoomInputOptions(
            text_enabled=True
        )
        # allow_interruptions is set on the session object, not the start method
    )
    
    # Provide immediate generic greeting with interruptions disabled
    await session.say(f"Hello! My name is Alina, your digital agent. I'm retrieving your information. Please wait", allow_interruptions=False)
    
    # COMPLETELY DISABLE AUDIO INPUT during API fetching
    # This is the key to preventing the agent from processing voice during API calls
    session.input.set_audio_enabled(False)
    print("Audio input DISABLED - agent will not process any speech during API calls")
    
    # Start the background audio player only - we'll play sounds during each API call
    await background_audio.start(room=ctx.room, agent_session=session)
    print("Initialized background audio for API call typing sounds")
    
    # Create a helper function to play typing sounds during API calls
    async def with_typing_sound(api_func, *args, **kwargs):
        # Start typing sound
        typing_handle = background_audio.play(BuiltinAudioClip.KEYBOARD_TYPING, loop=True)
        print(f"Started typing sounds for API call: {api_func.__name__}")
        
        try:
            # Call the API function
            result = await api_func(*args, **kwargs)
            return result
        finally:
            # Stop typing sound regardless of success or failure
            typing_handle.stop()
            print(f"Stopped typing sounds for API call: {api_func.__name__}")

    
    # We'll re-enable audio input after APIs are fetched and personalized greeting is delivered

    # Specify the US Eastern time zone
    eastern = pytz.timezone('US/Eastern')
    date_time = datetime.now(pytz.utc).astimezone(eastern)
    today_date = date_time.strftime("%Y-%m-%d")
    current_time = date_time.strftime("%I:%M %p")  # 12-hour format with AM/PM

    try:
        # metadata = eval(participant.metadata)
        meta_data = participant.metadata
        metadata = json.loads(meta_data)
        print(f"\n\nMetadata: {metadata}\n\n")
    except:
        pass

    starting_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

    # all_riders_info = {}
    all_riders_info = {"number_of_riders":0}

    unknow_rider = {
        "name": "Unknown",
        "client_id": "-1",
        "city": "Unknown",
        "state": "Unknown",
        "current_location": "Unknown",
        "rider_id": "-1"
    }

    new_rider = {
        "name": "new_rider",
        "client_id": "-1",
        "city": "Unknown",
        "state": "Unknown",
        "current_location": "Unknown",
        "rider_id": "-1"
    }

    affiliate = {
        "AffiliateID": "-1",
        "AffiliateFamilyID": "-1",
        "TypeForIVRAI": "Unknown",
        "AffiliateName": "Unknown"
    }

    room_name = ctx.room.name
    # room_name = "both-65-3-ARMON"
    print(f"\n\n\nRoom Name: {room_name}\n\n\n")

    chatbot = False
    ivr = False

    try:
        success = False

        try:
            # For Twillio or Asterisk calls
            # try:
            #     # Twillio
            #     # Fetch call details using CallSid
            #     call = TWILIO_CLIENT.calls(call_sid).fetch()
            #
            #     # Access caller and recipient information
            #     caller = call._from
            #     print(f"\n\n\nCaller: {caller}\n\n\n")
            #     # caller = "+12222222222"
            #     # caller = "+13012082222"
            #     # caller = "+13012082252"
            #     recipient = str(call.to)
            #     # recipient = "+17172007213"
            #     print(f"\n\nRecipient: {recipient}\n\n")
            # except:

            # For Asterisk
            logger.info(participant.attributes)
            # metadata = participant.metadata
            caller = participant.attributes['sip.phoneNumber']
            recipient = participant.attributes['sip.trunkPhoneNumber']
            
            # Try to get affiliate from cache
            cached_affiliate = cache_manager.get_affiliate_from_cache(recipient)
            if cached_affiliate:
                affiliate = cached_affiliate
                logger.info(f"Using cached affiliate for {recipient}")
            else:
                # If not in cache, call the original function with typing sound
                affiliate = await with_typing_sound(recognize_affiliate, recipient)
                # Store result in cache for future use
                cache_manager.store_affiliate_in_cache(recipient, affiliate)
                
            success = True
            ivr = True
            affiliate_id = affiliate["AffiliateID"]
            family_id = affiliate["AffiliateFamilyID"]

            phone_number = await extract_phone_number(caller)
            # print(f"\n\nPhone Number: {phone_number}")
            
            # Try to get client info from cache
            cached_client = cache_manager.get_client_from_cache(phone_number, affiliate_id, family_id)
            if cached_client:
                all_riders_info = cached_client
                logger.info(f"Using cached client info for {phone_number}")
            else:
                # If not in cache, call the original function with typing sound
                all_riders_info = await with_typing_sound(get_client_name_voice, phone_number, affiliate_id, family_id)
                # Store result in cache for future use
                cache_manager.store_client_in_cache(phone_number, affiliate_id, family_id, all_riders_info)

        except Exception as e:
            print(f"Error in recognizing affiliate from number: {e}")

        if not success:
            try:
                family_id = metadata['familyId']
                affiliate_id = metadata['affiliateId']
                
                # Try to get affiliate from cache using IDs
                cache_key = f"ids:{family_id}:{affiliate_id}"
                cached_affiliate = cache_manager.get_affiliate_from_cache(cache_key)
                if cached_affiliate:
                    affiliate = cached_affiliate
                    logger.info(f"Using cached affiliate for IDs {family_id}:{affiliate_id}")
                else:
                    # If not in cache, call the original function with typing sound
                    affiliate = await with_typing_sound(recognize_affiliate_by_ids, family_id, affiliate_id)
                    # Store result in cache for future use
                    cache_manager.store_affiliate_in_cache(cache_key, affiliate)
                
                print("*************AFFILIATE*******:\n", affiliate)
                phone_number = metadata['phoneNo']
                if phone_number != "":
                    phone_number = await extract_phone_number(phone_number)
                    # print(f"\n\nPhone Number: {phone_number}")
                    
                    # Try to get client info from cache
                    cached_client = cache_manager.get_client_from_cache(phone_number, affiliate_id, family_id)
                    if cached_client:
                        all_riders_info = cached_client
                        logger.info(f"Using cached client info for {phone_number}")
                    else:
                        # If not in cache, call the original function with typing sound
                        all_riders_info = await with_typing_sound(get_client_name_voice, phone_number, affiliate_id, family_id)
                        # Store result in cache for future use
                        cache_manager.store_client_in_cache(phone_number, affiliate_id, family_id, all_riders_info)
                else:
                    all_riders_info["number_of_riders"] = 1
                    all_riders_info["rider_1"] = unknow_rider
                chatbot = True

            except Exception as e:
                print(f"Error in recognizing affiliate from room matadata: {e}")

        if all_riders_info["number_of_riders"] == 0:
            all_riders_info["number_of_riders"] = 1
            all_riders_info["rider_1"] = new_rider
            all_riders_info["rider_1"]["number_of_existing_trips"] = 0

        print(f"\n\nRider: {all_riders_info}\n\n")
        print(f"\n\nAffiliate: {affiliate}\n\n")

    except Exception as e:
        print(f"Error occured in getting rider name and id: {e}")
        pass

    if all_riders_info["number_of_riders"] == 1 and chatbot is True:

        if all_riders_info["rider_1"]["name"] == "new_rider":
            print("\n\n****************New Rider chatbot Flow Selected****************\n\n")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider.txt")

        elif all_riders_info["rider_1"]["name"] == "Unknown":
            print("\n\n****************Widget Flow chatbot Selected****************\n\n")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_widget.txt")

        else:
            print("\n\n****************Old Rider chatbot Flow Selected****************\n\n")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_old_rider.txt")

    elif all_riders_info["number_of_riders"] == 1 and ivr is True:

        if all_riders_info["rider_1"]["name"] == "new_rider":
            print("\n\n****************New Rider IVR Flow Selected****************\n\n")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider_ivr.txt")

        else:
            print("\n\n****************Old Rider IVR Flow Selected****************\n\n")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_old_rider_ivr.txt")

    elif all_riders_info["number_of_riders"] > 1 and chatbot is True:
        print("\n\n****************Multiple Riders chatbot Flow Selected****************\n\n")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_multiple_riders.txt")

    elif all_riders_info["number_of_riders"] > 1 and ivr is True:
        print("\n\n****************Multiple Riders IVR Flow Selected****************\n\n")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_multiple_riders_ivr.txt")

    else:
        print("\n\n****************Error in Selecting Flow****************\n\n")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider.txt")

    with open(prompt_file) as file:
        system_prompt = file.read()
    try:
        if all_riders_info["number_of_riders"] == 1:
            rider_info = all_riders_info["rider_1"]

            try:
                # for chatbot only
                rider_info["phone_number"] = metadata['phoneNo']
                rider_info["userID"] = metadata['userID']
            except: pass

            rider_info = json.dumps(rider_info, indent=4)
            prompt = f"""{system_prompt}\n\n
            ``Today's date is {today_date} and Current Time is {current_time}``\n\n
            ``Rider's Profile: \n{rider_info}\n\n``
            ``Caller's phone no:{phone_number}\n\n``
            """

        elif all_riders_info["number_of_riders"] > 1:
            riders_data_without_tally = copy.deepcopy(all_riders_info)
            del riders_data_without_tally["number_of_riders"]
            riders_data_without_tally["phone_number"] = phone_number
            try:
                # for chatbot only
                riders_data_without_tally["userID"] = metadata["userID"]
            except: pass

            rider_info = json.dumps(riders_data_without_tally, indent=4)
            prompt = f"""{system_prompt}\n\n
            ``Today's date is {today_date} and Current Time is {current_time}``\n\n
            ``Rider's Profile: \n{rider_info}\n\n``
            """

    except Exception as e:
        print(f"Error occured in getting rider profile: {e}")
        # Include today's date in the system prompt

        prompt = f"""{system_prompt}\n\n
        Today's date is {today_date} and Current Time is {current_time}\n\n
        """

    try:
        if not isinstance(affiliate, str):
            affiliate_id = affiliate["AffiliateID"]
            family_id = affiliate["AffiliateFamilyID"]
            affiliate_type = affiliate["TypeForIVRAI"].lower()
            affiliate_name = affiliate["AffiliateName"]
            prompt = f"""{prompt}\n\n
            ``Affiliate/Agency/Company Name is {affiliate_name}, Family Id is {family_id}, Affiliate Id is {affiliate_id} and Affiliate Type is {affiliate_type}``
            """
        else:
            pass

    except Exception as e:
        print(f"Error occured in recognizing affiliate: {e}")
        pass

    Servica_Area = ""
    try:
        bounds, _, _ = await with_typing_sound(fetch_affiliate_details, affiliate_id)
        counties_prompt = f"""What are the counties that lies within these coordinates {bounds}. Only return names of the counties separated by commas. 
        Do not add name of the states. Do not add any other line or comment. I just need the name of the counties
        Sample response would be 'county_1, county_2, ......, county_n'
        DO NOT RETURN MORE THAN 10 COUNTY NAMES
        """
        Servica_Area = await with_typing_sound(search_web_manual, counties_prompt)
        prompt = f"""{prompt}\n\n
        ``Agency Operate in the following counties: {Servica_Area}``\n\n
        """
    except Exception as e:
        print(f"\n\nError in getting greetings: {e}\n\n")

    if all_riders_info["number_of_riders"] == 1:
        rider_info = all_riders_info["rider_1"]
        client_id = rider_info["client_id"]
        frequent_rides = ""
        try:
            frequent_rides = await with_typing_sound(get_frequnt_addresses_manual, client_id, affiliate_id)
            if frequent_rides.strip() != "":
                prompt = f"""{prompt}\n\n
                {frequent_rides}
                """
            else:
                prompt = f"""{prompt}\n\n
                ``Rider Historic/Past/Completed Trips are:
                1. Only use them for address completion
                2. Use [get_ETA] function to get latest/last trip, pickup and dropoff address: No Data Available``
                """
        except Exception as e:
            print(f"\n\nError in getting frequent trips: {e}\n\n")
            prompt = f"""{prompt}\n\n
            ``Rider Historic/Past/Completed Trips are:
            1. Only use them for address completion
            2. Use [get_ETA] function to get latest/last trip, pickup and dropoff address: No Data Available``
            """
            pass

    # print(f"\n\nPrompt: {prompt}\n\n")

    # Create user context information that we'll use in both the agent prompt and personalized message
    user_context = ""
    
    # We've already created the session and background audio player earlier
    # First build the user context, then create the full agent
    try:
        # Give a small pause to ensure initial greeting is complete
        await asyncio.sleep(1)
        
        print("Building user context information")
        
        # Create a knowledge base update with key user details to inject into conversation
        user_context = """\n\nIMPORTANT RIDER INFORMATION: Please keep this information in mind for the entire conversation.\n"""
        
        # Add affiliate details if available
        if affiliate_name and affiliate_name != "Default":
            user_context += f"Affiliate Name: {affiliate_name}\n"
            user_context += f"Affiliate ID: {affiliate_id}\n"
            if "AffiliateFamilyID" in affiliate:
                user_context += f"Affiliate Family ID: {affiliate['AffiliateFamilyID']}\n"
        
        # Add rider information
        if all_riders_info["number_of_riders"] == 1:
            rider = all_riders_info["rider_1"]
            user_context += f"Rider Name: {rider['name']}\n"
            user_context += f"Rider ID: {rider['rider_id']}\n"
            user_context += f"Client ID: {rider['client_id']}\n"
            user_context += f"Rider Location: {rider.get('city', 'Unknown')}, {rider.get('state', 'Unknown')}\n"
            
            if "number_of_existing_trips" in rider:
                user_context += f"Number of Existing Trips: {rider['number_of_existing_trips']}\n"
            
            # Add phone number if available
            if phone_number:
                user_context += f"Phone Number: {phone_number}\n"
        
        elif all_riders_info["number_of_riders"] > 1:
            user_context += f"Multiple riders ({all_riders_info['number_of_riders']}) associated with this phone number\n"
            
        user_context += "\nPlease maintain this context throughout the conversation, even if the user asks unrelated questions.\n"
        
        print("User context built successfully")
        
        # Now create the final agent with the full context
        try:
            # Include user context in the final prompt to ensure the agent remembers it
            final_prompt = prompt + "\n\n" + user_context
            agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=final_prompt, affiliate_id=int(affiliate_id))
        except Exception as e:
            print(f"\n\n\nError in generating agent object: {e}\n\n")
            agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=prompt, affiliate_id=65)
        
    except Exception as e:
        print(f"Error building user context: {e}")
        # Create a basic agent if we failed to build the context
        agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=prompt, affiliate_id=int(affiliate_id))
    # Define the conversation history collection function before we have the session reference
    conversation_history = []
    def setup_conversation_listeners(current_session):
        @current_session.on("conversation_item_added")
        def on_conversation_item_added(event: ConversationItemAddedEvent):
            print(f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}")
            if event.item.text_content != '':
                if event.item.role == 'assistant':
                    conversation_history.append({
                    'speaker': 'Agent',
                    'transcription': event.item.text_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                if event.item.role == 'user':
                    conversation_history.append({
                    'speaker': 'User',
                    'transcription': event.item.text_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
    
    # Setup initial conversation listeners
    setup_conversation_listeners(session)
    
    # Setup supervisor with the final session
    supervisor = Supervisor(session=session,
                          room=agent.room,
                          llm=openai.LLM(model="gpt-4o-mini"))
    await supervisor.start()

    # User information is now loaded, so we can provide a personalized follow-up message
    # This will only run after the API calls are complete and we've already given an initial greeting
    try:
        # Create a simple personalized message based on what we know
        personalized_message = ""
        
        # Add affiliate information if available
        if affiliate_name and affiliate_name != "Default":
            personalized_message += f"I now have your information from {affiliate_name} agency. "
        
        # Add personalized greeting based on rider info
        if all_riders_info["number_of_riders"] == 1:
            rider = all_riders_info["rider_1"]
            if rider["name"] == "new_rider":
                personalized_message += "Can I have your name please?"
                
            elif rider["name"] == "Unknown":
                personalized_message += "Can I have your phone number please?"
                
            elif rider["name"]:
                try:
                    no_of_trips = rider.get("number_of_existing_trips", "0")
                    if int(no_of_trips) > 0:
                        personalized_message += f"I see that you are {rider['name']} and you have {no_of_trips} existing trips. How can I help you today?"
                    else:
                        personalized_message += f"I see that you are {rider['name']}. How can I help you today?"
                except Exception as e:
                    print(f"Error in personalizing message: {e}")
                    personalized_message += f"I see that you are {rider['name']}. How can I help you today?"
                    
        elif all_riders_info["number_of_riders"] > 1:
            personalized_message += "I see that I have multiple profiles for your number. Can I confirm your name please?"
        
        # All typing sounds are already stopped after each API call
        print("Preparing to deliver personalized follow-up message")
        
        # Only send follow-up if we have something meaningful to say
        if personalized_message:
            # First deliver the personalized message with interruptions still disabled
            await session.say(personalized_message, allow_interruptions=False)
            
        # Now that all API fetching and personalized greeting is done, re-enable audio input and allow interruptions
        # This happens regardless of whether we had a personalized message or not
        session.input.set_audio_enabled(True)  # RE-ENABLE AUDIO INPUT
        session.allow_interruptions = True
        interruptions_enabled = True
        print("APIs fetched and processing complete. Audio input RE-ENABLED and interruptions now allowed.")
            
    except Exception as e:
        print(f"Error in providing personalized follow-up: {e}")
        # No need to stop typing sounds here - they're stopped after each API call
        print("Error occurred during API fetching")
        
        # Don't send another message if we fail - the initial greeting is enough
        
        # Make sure audio input and interruptions are enabled even if we fail
        session.input.set_audio_enabled(True)  # RE-ENABLE AUDIO INPUT
        session.allow_interruptions = True
        interruptions_enabled = True
        print("Error occurred, but ensuring audio input is RE-ENABLED and interruptions are allowed.")

    # Use the usage collector to aggregate agent usage metrics
    usage_collector = metrics.UsageCollector()

    # Add metrics to usage collector as they are received
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    @ctx.room.on("sip_dtmf_received")
    def handle_dtmf(dtmf: SipDTMF):
        digit = dtmf.digit
        logger.info(f"DTMF received from sip: {digit}")
        if digit == "0":
            asyncio.create_task(transfer_call_dtmf(agent.room, agent.room.name))
        if digit == "1":
            asyncio.create_task(transfer_call_dtmf_driver(agent.room, agent.room.name))

    phone_collector = PhoneNumberCollector()
    phone_collector.start_collection()

    def on_dtmf_received(event):
        digit = event.digit
        logger.info(f"Session DTMF digit received: {digit}")
        
        if phone_collector.collecting_phone:
            asyncio.create_task(handle_phone_dtmf(digit, session, phone_collector))
        # else:
        #     asyncio.create_task(handle_regular_dtmf(digit, session, agent))

    # Log aggregated summary of usage metrics generated by usage collector
    async def log_usage(starting_time, call_sid, conversation_history):
        summary = usage_collector.get_summary()
        llm_input_tokens = int(summary.llm_prompt_tokens)
        llm_output_tokens = int(summary.llm_completion_tokens)
        stt_audio_seconds = int(summary.stt_audio_duration)
        tts_characters = int(summary.tts_characters_count)

        # Specify the US Eastern time zone
        eastern = pytz.timezone('US/Eastern')
        end_date_time = datetime.now(pytz.utc).astimezone(eastern)

        ending_time = end_date_time.strftime("%Y-%m-%d %H:%M:%S")

        cost = calculate_cost(llm_input_tokens, llm_output_tokens, stt_audio_seconds, tts_characters)
        supervisor_cost = calculate_supervisor_cost(supervisor.usage_collector)

        # Format conversation history for MongoDB
        formatted_history = []
        for entry in conversation_history:
            # Keep the original speaker label from the conversation history
            formatted_history.append({
                "speaker": entry.get('speaker', ''),
                "transcription": entry.get('transcription', ''),
                "timestamp": entry.get('timestamp', '')
            })

        # Create MongoDB document
        mongo_doc = {
            "user": ObjectId(DEFAULT_USER_ID),
            "call_sid": f"{call_sid} , (Phone number: {phone_number})",
            "start_time": datetime.strptime(starting_time, "%Y-%m-%d %H:%M:%S"),
            "end_time": datetime.strptime(ending_time, "%Y-%m-%d %H:%M:%S"),
            "cost": {
                "stt_cost": cost.get('stt_cost', 0),
                "tts_cost": cost.get('tts_cost', 0),
                "llm_input_cost": cost.get('llm_input_cost', 0) + supervisor_cost.get('llm_input_cost', 0),
                "llm_output_cost": cost.get('llm_output_cost', 0) + supervisor_cost.get('llm_output_cost', 0),
                "total_cost": cost.get('total_cost', 0) + supervisor_cost.get('total_cost', 0)
            },
            "conversation_history": formatted_history,
            "createdAt": datetime.now()
        }

        # Insert document to MongoDB
        try:
            result = costlogs_collection.insert_one(mongo_doc)
            print(f"\n\nDatabase operation successful: {result}\n\n")
        except Exception as e:
            print(f"\n\n\n\nDatabase operation failed: {e}\n\n\n\n")

        # Also send to existing API for backward compatibility
        data = {
            "start_time": starting_time,
            "end_time": ending_time,
            "call_sid": call_sid,
            "cost": cost['total_cost'] + supervisor_cost.get('total_cost', 0),
            "conversation_history": conversation_history
        }
        print(f"\n\n\nPayload Sent: {data}\n\n\n")

        url = os.getenv("PYTHON_ANYWHERE_COST_LOGGING")

        # Send the POST request with JSON data
        try:
            response = requests.post(url, json=data)
            if response.status_code == 201:
                print(f"Success: {response.json()}")
            else:
                print(f"Error: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error sending data to API: {e}")

    # At shutdown, generate and log the summary from the usage collector
    ctx.add_shutdown_callback(lambda: asyncio.create_task(log_usage(starting_time, call_sid, conversation_history)))

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, port=int(os.getenv("PORT"))))
