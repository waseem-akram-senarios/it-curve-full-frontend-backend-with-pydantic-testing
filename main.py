import os
import pytz
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
from cost_tracker import get_cost_tracker, reset_cost_tracker, add_agent_usage, add_supervisor_usage, add_stt_usage, add_tts_usage, set_call_context, cleanup_call_tracker
import copy
from supervisor import Supervisor
from universal_stt_detector import detect_any_stt_error
import cache_manager
from logging_config import get_logger, set_session_id, set_x_call_id, set_call_sid, cleanup_call_logs
from recordings.recording_utils import generate_recording_url
load_dotenv()

# Initialize logger using our centralized logging system
logger = get_logger('main')

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
Agent_Directory = Path(__file__).parent

load_dotenv(dotenv_path=".env")
# Logger already initialized above as logger = get_logger('main')


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

    # Enhanced debugging for Asterisk DTMF
    logger.info(f"[ASTERISK DTMF DEBUG] Raw digit received: '{digit}' (ord={ord(digit[0]) if digit else 'empty'})")

    # Map potential Asterisk DTMF representations
    dtmf_map = {
        "11": "#",
        "pound": "#",
        "10": "*",
        "star": "*"
    }

    # Normalize the digit if needed
    normalized_digit = dtmf_map.get(digit.lower(), digit)

    logger.info(f"[ASTERISK DTMF] Original: '{digit}', Normalized: '{normalized_digit}'")

    if normalized_digit == "#":  # CHANGED: # should submit the number
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
    elif normalized_digit == "*":  # CHANGED: * should clear/reset
        # Reset phone number collection
        collector.clear_number()
        await session.generate_reply(
            instructions="Let me clear that. Please enter your phone number again using the keypad and press pound when finished.",
            allow_interruptions=True
        )
    elif normalized_digit.isdigit():
        # Add digit to the current number being collected
        collector.add_digit(normalized_digit)
        logger.info(f"[ASTERISK DTMF] Added digit {normalized_digit}, current number: {collector.current_number}")
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
        # Enhanced logging for Asterisk debugging
        logger.info(f"[ASTERISK DTMF] Received signal - Identity: {dtmf.participant.identity}")
        logger.info(f"[ASTERISK DTMF] Code: {dtmf.code} | Digit: '{dtmf.digit}' | Type: {type(dtmf.digit)}")

        digit = dtmf.digit

        # Check for potential Asterisk-specific DTMF encoding issues
        if digit is None or digit == "":
            logger.warning(f"[ASTERISK DTMF] Empty or None digit received, code was: {dtmf.code}")
            return

        # Only process DTMF when explicitly collecting phone numbers
        if phone_collector.collecting_phone:
            logger.info(f"[ASTERISK DTMF] Processing digit '{digit}' for phone collection")
            asyncio.create_task(handle_phone_dtmf(digit, session, phone_collector))
        else:
            logger.info(f"[ASTERISK DTMF] Digit '{digit}' ignored - not in phone collection mode")
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

    await ctx.connect()

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()

    # # Twilio code commented
    # call_sid = participant.attributes.get("sip.twilio.callSid", "Unknown")
    # if call_sid == "Unknown":
    call_sid = 'chat-' + str(uuid.uuid4())
    logger.info(f"Call SID: {call_sid}")
    
    # Set call context for cost tracking (must be done after call_sid is generated)
    set_call_context(call_sid)
    
    # Reset cost tracker for new call
    reset_cost_tracker(call_sid)
    logger.info(f"Cost tracker initialized for call: {call_sid}")
    
    # Set up per-call logging
    session_id = set_session_id(call_sid)
    set_call_sid(call_sid)  # Set call_sid for automatic per-call logging
    
    logger.info(f"📞 CALL STARTED - Call SID: {call_sid}")
    logger.info(f"📞 Session ID: {session_id}")
    logger.info(f"📞 Room: {ctx.room.name}")
    logger.info(f"📞 Participant: {participant.identity if participant else 'Unknown'}")
    
    # Set up the session and background audio early to prepare for immediate greeting
    background_audio = BackgroundAudioPlayer(thinking_sound=[
        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.6)
    ])
    deepgram_stt_model = "nova-3"
    deepgram_tts_model = "aura-asteria-en"
    session = AgentSession(
        stt=deepgram.STT(
            model=deepgram_stt_model, 
            language="en",
            interim_results=True,  # Enable interim results for faster interruption
            smart_format=True
        ),
        allow_interruptions=True,
        false_interruption_timeout = 2.0,
        resume_false_interruption = True,
        llm=openai.LLM(model="gpt-4.1-mini", temperature=0.1),
        tts=deepgram.TTS(model=deepgram_tts_model),
        vad=silero.VAD.load(min_silence_duration=0.75),
        turn_detection=EnglishModel(),
    )

    # Allow supervisor-initiated transfers until a booking is completed
    session.should_allow_transfer = True
    

    # Simple default prompt to start with - will be updated later
    default_prompt = """You are a Caring, Sympathetic voice assistant helping riders with their queries. Your primary goal is to provide efficient and clear assistance while maintaining casual tone. Keep your responses concise, direct, less talktive and clear since this is a voice interface.
        Your name is Alina and you are an AI assistant for agency whose name is mentioned in the greetings. Keep your tone casual like a human and not extremely professional.
        Service Area in which the company/agency operates are also included in the greetings.
        Remember: You are ONLY here to assist with transportation services for the agency mentioned in the greetings. Stay focused on providing helpful, efficient, and friendly ride assistance."""

    # Create agent with default prompt initially
    initial_agent = Assistant(call_sid=call_sid, context=ctx, room=ctx.room, instructions=default_prompt, affiliate_id=65)
    
    
    # Ensure interruptions are disabled for the initial greeting
    # session.allow_interruptions = False
    
    # Use the existing background audio player created earlier
    logger.info("Using pre-configured background audio player for typing sounds")
    
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
    
    # Enable interruptions for the rest of the conversation after first greeting
    # session.allow_interruptions = True
    logger.info("Interruptions ENABLED after first greeting - user can interrupt the bot now")
    
    # COMPLETELY DISABLE AUDIO INPUT during API fetching
    # This is the key to preventing the agent from processing voice during API calls
    session.input.set_audio_enabled(False)
    logger.info("Audio input DISABLED - agent will not process any speech during API calls")
    
    # Start the background audio player for continuous typing sounds
    try:
        await background_audio.start(room=ctx.room, agent_session=session)
        logger.info("Initialized background audio player")
    except Exception as e:
        logger.warning(f"Warning: Couldn't initialize background audio player: {e}")
    
    # Start a single typing sound that will continue throughout all API calls
    typing_handle = None
    try:
        typing_handle = background_audio.play(BuiltinAudioClip.KEYBOARD_TYPING, loop=True)
        logger.info("Started typing sounds for API fetching phase")
    except Exception as e:
        logger.warning(f"Warning: Couldn't start typing sounds: {e}")
    
    
            
    # ==============================================================================
    # TYPING SOUNDS DURING CONVERSATION API CALLS
    # ==============================================================================
    # This helper function plays typing sounds during any API call that happens 
    # during conversation with the user (after the initial greeting phase).
    # 
    # HOW TO USE:
    # When making API calls during conversation (e.g. address validation, location lookup,
    # booking confirmation), wrap the API call with this function:
    #
    # EXAMPLE:
    # Instead of: result = await verify_address(address)
    # Use: result = await with_typing_during_api(verify_address, address)
    #
    # This will automatically play typing sounds while the API call is processing
    # and stop them when the call completes, providing a better user experience.
    # ==============================================================================
    async def with_typing_during_api(api_func, *args, **kwargs):
        # Start typing sound
        temp_typing_handle = None
        try:
            temp_typing_handle = background_audio.play(BuiltinAudioClip.KEYBOARD_TYPING, loop=True)
            logger.debug(f"Started typing sounds for conversation API call: {api_func.__name__}")
        except Exception as e:
            logger.warning(f"Warning: Couldn't start typing sounds for conversation: {e}")
            
        try:
            # Call the API function
            result = await api_func(*args, **kwargs)
            return result
        finally:
            # Always stop the typing sound
            if temp_typing_handle is not None:
                try:
                    temp_typing_handle.stop()
                    logger.debug(f"Stopped typing sounds for conversation API call: {api_func.__name__}")
                except Exception as e:
                    logger.error(f"Error stopping conversation typing sounds: {e}")

    
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
        logger.debug(f"Metadata: {metadata}")
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
    logger.info(f"Room Name: {room_name}")

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
            #     logger.info(f"Caller: {caller}")
            #     # caller = "+12222222222"
            #     # caller = "+13012082222"
            #     # caller = "+13012082252"
            #     recipient = str(call.to)
            #     # recipient = "+17172007213"
            #     logger.info(f"Recipient: {recipient}")
            # except:

            # For Asterisk
            logger.info(participant.attributes)
            # metadata = participant.metadata
            caller = participant.attributes['sip.phoneNumber']
            recipient = participant.attributes['sip.trunkPhoneNumber']
            
            # Extract X-Call-ID from SIP headers
            x_call_id = extract_x_call_id(participant.attributes)
            if x_call_id:
                logger.info(f"✅ [SIP HEADER] X-Call-ID extracted: {x_call_id}")
                # Set X-Call-ID in logging context for all subsequent logs
                from logging_config import set_x_call_id
                set_x_call_id(x_call_id)
            else:
                logger.warning(f"❌ [SIP HEADER] X-Call-ID not found in headers")
            
            logger.info(f"Caller & Recipient from Asterisk: {caller}, {recipient}")
            logger.info(f"***************Caller & Recipient from Asterisk: {caller} {recipient}")
            logger.info(f"📞 Caller: {caller}")
            logger.info(f"📞 Recipient: {recipient}")
            # Try to get affiliate from cache
            cached_affiliate = cache_manager.get_affiliate_from_cache(recipient)
            logger.debug(f"cached_affiliate: {cached_affiliate}")
            if cached_affiliate:
                affiliate = cached_affiliate
                logger.info(f"Using cached affiliate for {recipient}")
            else:
                # If not in cache, call the original function with logging
                affiliate = await with_typing_during_api(recognize_affiliate, recipient)
                # Store result in cache for future use
                cache_manager.store_affiliate_in_cache(recipient, affiliate)
                
            success = True
            ivr = True
            affiliate_id = affiliate["AffiliateID"]
            family_id = affiliate["AffiliateFamilyID"]
            initial_agent.update_affliate_id_and_family(affiliate_id,family_id)

            phone_number = await with_typing_during_api(extract_phone_number, caller)
            logger.info(f"Phone Number Extracted: {phone_number}")
            initial_agent.update_rider_phone(phone_number)
            
            # Try to get client info from cache
            # cached_client = cache_manager.get_client_from_cache(phone_number, affiliate_id, family_id)
            # if cached_client:
            #     all_riders_info = cached_client
            #     logger.info(f"Using cached client info for {phone_number}")
            # else:
                # If not in cache, call the original function with logging
            all_riders_info = await with_typing_during_api(get_client_name_voice, phone_number, affiliate_id, family_id)
            logger.debug(f"All Riders Info: {all_riders_info}")
            logger.info(f"[RIDER DETECTION] After API call - Number of riders: {all_riders_info.get('number_of_riders', 'MISSING')}")
                # Store result in cache for future use
            # cache_manager.store_client_in_cache(phone_number, affiliate_id, family_id, all_riders_info)

        except Exception as e:
            logger.error(f"Error in recognizing affiliate from number: {e}")

        if not success:
            try:
                family_id = metadata['familyId']
                affiliate_id = metadata['affiliateId']
                
                # Try to get affiliate from cache using IDs
                cache_key = f"ids:{family_id}:{affiliate_id}"
                cached_affiliate = cache_manager.get_affiliate_from_cache(cache_key)
                logger.debug(f"cached_affiliate: {cached_affiliate}")
                if cached_affiliate:
                    affiliate = cached_affiliate
                    logger.info(f"Using cached affiliate for IDs {family_id}:{affiliate_id}")
                else:
                    # If not in cache, call the original function with logging
                    affiliate = await with_typing_during_api(recognize_affiliate_by_ids, family_id, affiliate_id)
                    # Store result in cache for future use
                    cache_manager.store_affiliate_in_cache(cache_key, affiliate)
                
                logger.debug(f"AFFILIATE: {affiliate}")
                phone_number = metadata['phoneNo']
                if phone_number != "":
                    phone_number = await with_typing_during_api(extract_phone_number, phone_number)
                    logger.info(f"Phone Number Extracted: {phone_number}")
                    
                    # Try to get client info from cache
                    # cached_client = cache_manager.get_client_from_cache(phone_number, affiliate_id, family_id)
                    # if cached_client:
                    #     all_riders_info = cached_client
                    #     logger.info(f"Using cached client info for {phone_number}")
                    # else:
                        # If not in cache, call the original function with logging
                    all_riders_info = await with_typing_during_api(get_client_name_voice, phone_number, affiliate_id, family_id)
                    logger.info(f"[RIDER DETECTION] After API call - Number of riders: {all_riders_info.get('number_of_riders', 'MISSING')}")
                        # Store result in cache for future use
                        # cache_manager.store_client_in_cache(phone_number, affiliate_id, family_id, all_riders_info)
                else:
                    all_riders_info["number_of_riders"] = 1
                    all_riders_info["rider_1"] = unknow_rider
                chatbot = True

            except Exception as e:
                logger.error(f"Error in recognizing affiliate from room metadata: {e}")

        if all_riders_info["number_of_riders"] == 0:
            logger.warning("[RIDER DETECTION] WARNING: Found 0 riders, setting to default new rider")
            all_riders_info["number_of_riders"] = 1
            all_riders_info["rider_1"] = new_rider
            all_riders_info["rider_1"]["number_of_existing_trips"] = 0

        logger.debug(f"Rider: {all_riders_info}")
        logger.debug(f"Affiliate: {affiliate}")

    except Exception as e:
        logger.error(f"Error occurred in getting rider name and id: {e}")
        pass

    if all_riders_info["number_of_riders"] == 1 and chatbot is True:

        if all_riders_info["rider_1"]["name"] == "new_rider":
            logger.info("New Rider chatbot Flow Selected")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider.txt")

        elif all_riders_info["rider_1"]["name"] == "Unknown":
            logger.info("Widget Flow chatbot Selected")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_widget.txt")

        else:
            logger.info("Old Rider chatbot Flow Selected")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_old_rider.txt")

    elif all_riders_info["number_of_riders"] == 1 and ivr is True:

        if all_riders_info["rider_1"]["name"] == "new_rider":
            logger.info("New Rider IVR Flow Selected")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider_ivr.txt")

        else:
            logger.info("Old Rider IVR Flow Selected")
            prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_old_rider_ivr.txt")

    elif all_riders_info["number_of_riders"] > 1 and chatbot is True:
        logger.info(f"Multiple Riders chatbot Flow Selected - {all_riders_info['number_of_riders']} riders found")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_multiple_riders.txt")

    elif all_riders_info["number_of_riders"] > 1 and ivr is True:
        logger.info(f"Multiple Riders IVR Flow Selected - {all_riders_info['number_of_riders']} riders found")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_multiple_riders_ivr.txt")

    else:
        logger.error("Error in Selecting Flow")
        prompt_file = os.path.join(Agent_Directory, "prompts", "prompt_new_rider.txt")

    with open(prompt_file, encoding="utf-8") as file:
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
            The rider phone number is "{phone_number}"
            ``Today's date is {today_date} and Current Time is {current_time}``\n\n
            ``Rider's Profile: \n{rider_info}\n\n``
            """

    except Exception as e:
        logger.error(f"Error occurred in getting rider profile: {e}")
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
        logger.error(f"Error occurred in recognizing affiliate: {e}")
        pass

    Servica_Area = ""
    try:
        bounds, _, _ = await with_typing_during_api(fetch_affiliate_details, affiliate_id)
        counties_prompt = f"""What are the counties that lies within these coordinates {bounds}. Only return names of the counties separated by commas. 
        Do not add name of the states. Do not add any other line or comment. I just need the name of the counties
        Sample response would be 'county_1, county_2, ......, county_n'
        DO NOT RETURN MORE THAN 10 COUNTY NAMES
        """
        Servica_Area = await with_typing_during_api(search_web_manual, counties_prompt)
        prompt = f"""{prompt}\n\n
        ``Agency Operate in the following counties: {Servica_Area}``\n\n
        """
    except Exception as e:
        logger.error(f"Error in getting greetings: {e}")

    if all_riders_info["number_of_riders"] == 1:
        rider_info = all_riders_info["rider_1"]
        client_id = rider_info["client_id"]
        initial_agent.update_client_id(client_id)
        frequent_rides = ""
        try:
            frequent_rides = await with_typing_during_api(get_frequnt_addresses_manual, client_id, affiliate_id)
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
            logger.error(f"Error in getting frequent trips: {e}")
            prompt = f"""{prompt}\n\n
            ``Rider Historic/Past/Completed Trips are:
            1. Only use them for address completion
            2. Use [get_ETA] function to get latest/last trip, pickup and dropoff address: No Data Available``
            """
            pass
    elif all_riders_info["number_of_riders"] > 1:
        # For multiple riders, client_id will be set later when user selects a profile via select_rider_profile function
        logger.info(f"[MULTIPLE RIDERS] Client ID will be set after profile selection via select_rider_profile function")
        initial_agent.update_client_id(None)  # Explicitly set to None initially

    # Create user context information that we'll use in both the agent prompt and personalized message
    user_context = ""
    
    # We've already created the session and background audio player earlier
    # First build the user context, then create the full agent
    try:
        # Give a small pause to ensure initial greeting is complete
        await asyncio.sleep(1)
        
        logger.info("Building user context information")
        
        # Create a knowledge base update with key user details to inject into conversation
        user_context = """\n\nIMPORTANT RIDER INFORMATION: Please keep this information in mind for the entire conversation.\n"""
        if phone_number:
                user_context += f"""
                ### Phone Number Verification Notice:
                - You have received a call from the following phone number: +1{phone_number}.\n
                - Please use this number for any future verification purposes: +1{phone_number}.\n
                - Additionally, whenever the user requests to use of same phone number he/she called from you have to use this phone number (+1{phone_number}).\n
                - If user ask to repeat or confirm the phone number, you have to say "The phone number is +1{phone_number}".\n
                - when booking ride or providing any information related to the user, you have to use this phone number (+1{phone_number}).\n
                - Don't forgot to the send phone number in the [book_ride] function when booking ride. Don't send country code in PhoneNo with number in payload\n
                """
        
        # Add affiliate details if available
        if affiliate_name and affiliate_name != "Default":
            user_context += f"Affiliate Name: {affiliate_name}\n"
            user_context += f"Affiliate ID: {affiliate_id}\n"
            if "AffiliateFamilyID" in affiliate:
                user_context += f"Affiliate Family ID: {affiliate['AffiliateFamilyID']}\n"
        client_id = None
        # Add rider information
        if all_riders_info["number_of_riders"] == 1:
            rider = all_riders_info["rider_1"]
            client_id = rider['client_id']
            user_context += f"Rider Name: {rider['name']}\n"
            user_context += f"Rider ID: {rider['rider_id']}\n"
            user_context += f"Client ID: {rider['client_id']}\n"
            user_context += f"Rider Location: {rider.get('city', 'Unknown')}, {rider.get('state', 'Unknown')}\n"
            
            if "number_of_existing_trips" in rider:
                user_context += f"Number of Existing Trips: {rider['number_of_existing_trips']}\n"
            
            # Add phone number if available
            
        
        elif all_riders_info["number_of_riders"] > 1:
            user_context += f"Multiple riders ({all_riders_info['number_of_riders']}) associated with this phone number\n and here are details {all_riders_info}/n"
            
        user_context += "\nPlease maintain this context throughout the conversation, even if the user asks unrelated questions.\n"
        
        logger.info("User context built successfully")
        
        # Update the initial_agent with the enhanced context
        try:
            # Include user context in the final prompt to ensure the agent remembers it
            final_prompt = user_context + "\n\n" + prompt
            
            agent = Assistant(call_sid=call_sid, context=ctx, room=ctx.room, instructions=final_prompt, affiliate_id=affiliate_id, rider_phone=phone_number, client_id=client_id, x_call_id=x_call_id)
            # Set the family_id that's needed for various functions
            agent.update_affliate_id_and_family(affiliate_id, family_id)
            session.update_agent(agent)

            with open(f"logs/prompt/final_prompt_{call_sid}.txt","w") as f:
                f.write(final_prompt)
                
            logger.info("Successfully updated initial_agent with enhanced context")
            
        except Exception as e:
            logger.error(f"Error updating agent instructions: {e}")
            agent = Assistant(call_sid=call_sid, context=ctx, room=ctx.room, instructions=prompt, affiliate_id=affiliate_id, rider_phone=phone_number, client_id=client_id, x_call_id=x_call_id)
            session.update_agent(agent) 
            with open(f"logs/prompt/final_prompt_{call_sid}.txt","w") as f:
                f.write(final_prompt)       
    except Exception as e:
        agent = Assistant(call_sid=call_sid, context=ctx, room=ctx.room, instructions=prompt, affiliate_id=affiliate_id, rider_phone=phone_number, client_id=client_id, x_call_id=x_call_id)
        session.update_agent(agent)
        logger.info("Updated initial_agent with basic prompt as fallback")
        with open(f"logs/prompt/final_prompt_{call_sid}.txt","w") as f:
            f.write(final_prompt)
    # Define the conversation history collection function before we have the session reference
    conversation_history = []
    def setup_conversation_listeners(current_session):
        @current_session.on("conversation_item_added")
        def on_conversation_item_added(event: ConversationItemAddedEvent):
            logger.debug(f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}")
            if event.item.text_content != '':
                if event.item.role == 'assistant':
                    conversation_history.append({
                    'speaker': 'Agent',
                    'transcription': event.item.text_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                if event.item.role == 'user':
                    # Log user transcript for debugging
                    logger.info(f"User transcript received: {event.item.text_content}")
                    
                    # Universal STT Error Detection - handles ANY possible transcription error
                    recent_context = [item['transcription'] for item in conversation_history[-6:]]
                    
                    # Get the most recent bot response for analysis
                    recent_bot_response = ""
                    for item in reversed(conversation_history):
                        if item.get('speaker') == 'Agent':
                            recent_bot_response = item.get('transcription', '')
                            break
                    
                    # Universal STT validation
                    universal_validation = detect_any_stt_error(
                        user_input=event.item.text_content,
                        bot_response=recent_bot_response,
                        conversation_history=recent_context,
                        confidence=None  # LiveKit doesn't expose STT confidence by default
                    )
                    
                    # Log universal validation results
                    if universal_validation['is_likely_stt_error']:
                        confidence_score = universal_validation['confidence_score']
                        error_indicators = universal_validation['error_indicators']
                        
                        logger.warning(f"Universal STT error detected (confidence: {confidence_score:.2f}) - '{event.item.text_content}'")
                        logger.info(f"Error indicators: {error_indicators}")
                        
                        if universal_validation['suggested_corrections']:
                            for correction in universal_validation['suggested_corrections'][:2]:
                                logger.info(f"Suggested: '{correction['corrected_sentence']}' (confidence: {correction['confidence']:.2f}) - {correction['reason']}")
                        
                        if universal_validation['mismatch_analysis'].get('mismatch_detected'):
                            mismatch = universal_validation['mismatch_analysis']
                            logger.info(f"Intent mismatch: {mismatch.get('mismatch_reason', 'Unknown')}")
                    
                    # Store universal validation metadata with conversation history
                    conversation_history.append({
                    'speaker': 'User',
                    'transcription': event.item.text_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'universal_stt_validation': universal_validation
                    })
    
    # Setup initial conversation listeners
    setup_conversation_listeners(session)
    
    # Add additional listeners for debugging interruptions
    @session.on("agent_speech_started")
    def on_agent_speech_started():
        logger.info(" Agent started speaking - interruptions should be possible now")
    
    @session.on("agent_speech_stopped")
    def on_agent_speech_stopped():
        logger.info("Agent stopped speaking")
    
    @session.on("user_speech_started")
    def on_user_speech_started():
        logger.info("User started speaking - should interrupt agent if speaking")
    
    @session.on("user_speech_stopped")
    def on_user_speech_stopped():
        logger.info("User stopped speaking")
    
    # Setup supervisor with the final session
    supervisor = Supervisor(session=session,
                          room=initial_agent.room,
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
                    logger.error(f"Error in personalizing message: {e}")
                    personalized_message += f"I see that you are {rider['name']}. How can I help you today?"
                    
        elif all_riders_info["number_of_riders"] > 1:
            logger.info(f"[RIDER DETECTION] Preparing multiple riders greeting for {all_riders_info['number_of_riders']} riders")
            personalized_message += "I see that I have multiple profiles for your number. Can I confirm your name please?"
        
        # Stop the continuous typing sound before delivering the personalized message
        if typing_handle is not None:
            try:
                typing_handle.stop()
                logger.info("Stopped typing sounds - API fetching complete")
            except Exception as e:
                logger.error(f"Error stopping typing sounds: {e}")
        
        logger.info("Preparing to deliver personalized follow-up message")
        
        # Only send follow-up if we have something meaningful to say
        if personalized_message:
            # Deliver the personalized message with interruptions enabled
            await session.say(personalized_message, allow_interruptions=True)
            
        # Now that all API fetching and personalized greeting is done, re-enable audio input
        # This happens regardless of whether we had a personalized message or not
        session.input.set_audio_enabled(True)  # RE-ENABLE AUDIO INPUT
        # Interruptions were already enabled after the first greeting
        logger.info("APIs fetched and processing complete. Audio input RE-ENABLED.")
            
    except Exception as e:
        logger.error(f"Error in providing personalized follow-up: {e}")
        # Make sure typing sounds are stopped even on errors
        if typing_handle is not None:
            try:
                typing_handle.stop()
                logger.info("Stopped typing sounds due to error")
            except Exception as e:
                logger.error(f"Error stopping typing sounds after error: {e}")
        
        logger.error("Error occurred during API fetching")
        
        # Don't send another message if we fail - the initial greeting is enough
        
        # Make sure audio input is enabled even if we fail
        # (Interruptions were already enabled after the first greeting)
        session.input.set_audio_enabled(True)  # RE-ENABLE AUDIO INPUT
        logger.info("Error occurred, but ensuring audio input is RE-ENABLED.")

    # Use the usage collector to aggregate agent usage metrics
    usage_collector = metrics.UsageCollector()

    # Add metrics to usage collector as they are received
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    @ctx.room.on("sip_dtmf_received")
    def handle_dtmf(dtmf: SipDTMF):
        # Enhanced logging for Asterisk debugging
        logger.info(f"[ASTERISK DTMF - Secondary Handler] Code: {dtmf.code} | Digit: '{dtmf.digit}'")
        digit = dtmf.digit

        if digit == "0":
            logger.info("[ASTERISK DTMF] Transferring to dispatcher")
            asyncio.create_task(transfer_call_dtmf(initial_agent.room, initial_agent.room.name))
        elif digit == "1":
            logger.info("[ASTERISK DTMF] Transferring to driver")
            asyncio.create_task(transfer_call_dtmf_driver(initial_agent.room, initial_agent.room.name))

    # Room and participant disconnect event handlers
    @ctx.room.on("disconnected")
    def on_room_disconnected():
        logger.info(f"🔴[ROOM DISCONNECT] Room {ctx.room.name} disconnected for call {call_sid}")
        logger.info(f"🔴[ROOM DISCONNECT] Disconnect reason: Connection lost or terminated")
        
        # Clean up background audio to prevent generator issues
        try:
            if typing_handle is not None:
                typing_handle.stop()
                logger.info("🔴[ROOM DISCONNECT] Stopped typing sounds")
        except Exception as e:
            logger.warning(f"🔴[ROOM DISCONNECT] Warning during typing sound cleanup: {e}")
        
        try:
            asyncio.create_task(background_audio.stop())
            logger.info("🔴[ROOM DISCONNECT] Initiated background audio cleanup")
        except Exception as e:
            logger.warning(f"🔴[ROOM DISCONNECT] Warning during background audio cleanup: {e}")
        
        # Log disconnect event
        logger.warning(f"🔴 ROOM DISCONNECTED - Connection lost or terminated")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logger.info(f"🔴[PARTICIPANT DISCONNECT] Participant {participant.identity} disconnected from call {call_sid}")
        logger.info(f"🔴[PARTICIPANT DISCONNECT] Participant SID: {participant.sid}")
        logger.info(f"🔴[PARTICIPANT DISCONNECT] Remaining participants: {len(ctx.room.remote_participants)}")
        
        # Check if all participants have left
        if len(ctx.room.remote_participants) == 0:
            logger.info(f"🔴[ALL PARTICIPANTS LEFT] No participants remaining in call {call_sid}")
            logger.info(f"🔴[ALL PARTICIPANTS LEFT] Call session ending")
            
            # Clean up background audio when all participants leave
            try:
                if typing_handle is not None:
                    typing_handle.stop()
                    logger.info("🔴[ALL PARTICIPANTS LEFT] Stopped typing sounds")
            except Exception as e:
                logger.warning(f"🔴[ALL PARTICIPANTS LEFT] Warning during typing sound cleanup: {e}")
            
            try:
                asyncio.create_task(background_audio.stop())
                logger.info("🔴[ALL PARTICIPANTS LEFT] Initiated background audio cleanup")
            except Exception as e:
                logger.warning(f"🔴[ALL PARTICIPANTS LEFT] Warning during background audio cleanup: {e}")
            
            # Log participants left event
            logger.warning(f"🔴 ALL PARTICIPANTS LEFT - Call ending")

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        logger.info(f"🟢[PARTICIPANT CONNECT] Participant {participant.identity} connected to call {call_sid}")
        logger.info(f"🟢[PARTICIPANT CONNECT] Participant SID: {participant.sid}")
        logger.info(f"🟢[PARTICIPANT CONNECT] Total participants: {len(ctx.room.remote_participants) + 1}")  # +1 for agent

    @ctx.room.on("connection_state_changed")
    def on_connection_state_changed(state):
        logger.info(f"🔴[CONNECTION STATE] Room connection state changed to: {state} for call {call_sid}")
        if state == rtc.ConnectionState.DISCONNECTED:
            logger.info(f"🔴[CONNECTION STATE] Room fully disconnected for call {call_sid}")
        elif state == rtc.ConnectionState.FAILED:
            logger.info(f"🔴[CONNECTION STATE] Room connection failed for call {call_sid}")
        elif state == rtc.ConnectionState.CONNECTED:
            logger.info(f"🔴[CONNECTION STATE] Room successfully connected for call {call_sid}")
        elif state == rtc.ConnectionState.RECONNECTING:
            logger.info(f"🔴[CONNECTION STATE] Room reconnecting for call {call_sid}")

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
        # Get agent usage from main usage collector
        agent_summary = usage_collector.get_summary()
        agent_input_tokens = int(agent_summary.llm_prompt_tokens)
        agent_output_tokens = int(agent_summary.llm_completion_tokens)
        stt_audio_seconds = int(agent_summary.stt_audio_duration)
        tts_characters = int(agent_summary.tts_characters_count)
        
        # Add agent usage to cost tracker
        add_agent_usage(agent_input_tokens, agent_output_tokens, "gpt-4.1-mini")
        add_stt_usage(stt_audio_seconds, "deepgram", deepgram_stt_model)
        add_tts_usage(tts_characters, "deepgram", deepgram_tts_model)
        
        # Get supervisor usage from supervisor's usage collector
        supervisor_summary = supervisor.usage_collector.get_summary()
        supervisor_input_tokens = int(supervisor_summary.llm_prompt_tokens)
        supervisor_output_tokens = int(supervisor_summary.llm_completion_tokens)
        
        # Add supervisor usage to cost tracker
        add_supervisor_usage(supervisor_input_tokens, supervisor_output_tokens, "gpt-4.1-mini")
        
        # Get comprehensive cost breakdown from cost tracker
        cost_tracker = get_cost_tracker()
        cost_breakdown = cost_tracker.calculate_total_costs()
        cost_summary = cost_tracker.get_summary_dict()
        
        # Get web search token usage
        websearch_input_tokens = cost_breakdown.websearch_tokens.input_tokens
        websearch_output_tokens = cost_breakdown.websearch_tokens.output_tokens
        
        # Get STT and TTS usage details
        stt_provider = cost_breakdown.stt_usage.provider
        stt_model = cost_breakdown.stt_usage.model
        stt_usage_seconds = cost_breakdown.stt_usage.audio_seconds
        
        tts_provider = cost_breakdown.tts_usage.provider
        tts_model = cost_breakdown.tts_usage.model
        tts_usage_characters = cost_breakdown.tts_usage.characters
        
        # Log token breakdown for transparency
        logger.info(f"Usage breakdown by component:")
        logger.info(f"  Agent (gpt-4.1-mini): {agent_input_tokens} input, {agent_output_tokens} output tokens")
        logger.info(f"  Supervisor (gpt-4.1-mini): {supervisor_input_tokens} input, {supervisor_output_tokens} output tokens")
        logger.info(f"  WebSearch (gpt-4o): {websearch_input_tokens} input, {websearch_output_tokens} output tokens")
        logger.info(f"  STT ({stt_provider} {stt_model}): {stt_usage_seconds} seconds")
        logger.info(f"  TTS ({tts_provider} {tts_model}): {tts_usage_characters} characters")
        logger.info(f"  Total tokens: {agent_input_tokens + supervisor_input_tokens + websearch_input_tokens} input, "
                   f"{agent_output_tokens + supervisor_output_tokens + websearch_output_tokens} output")

        # Specify the US Eastern time zone
        eastern = pytz.timezone('US/Eastern')
        end_date_time = datetime.now(pytz.utc).astimezone(eastern)

        fmt = "%Y-%m-%d %H:%M:%S"
        ending_time = end_date_time.strftime("%Y-%m-%d %H:%M:%S")
        elapsed_time = (datetime.strptime(ending_time, fmt) - datetime.strptime(starting_time, fmt)).total_seconds()
        
        # Legacy cost calculations removed - now using comprehensive cost tracker


        # Format conversation history for MongoDB
        formatted_history = []
        score_history = iter(supervisor.score_history)
        default_score = { "relevance": 'N/A', "completeness": 'N/A', "groundedness": 'N/A', "average": 'N/A' }
        for i, entry in enumerate(conversation_history):
            if i == 0:
                score = None
            elif entry.get('speaker', '') == 'Agent':
                score = next(score_history, default_score)
            else:
                score = None
            i += 1

            # Keep the original speaker label from the conversation history
            formatted_history.append({
                "speaker": entry.get('speaker', ''),
                "transcription": entry.get('transcription', ''),
                "timestamp": entry.get('timestamp', ''),
                "score": score
            })
        logger.debug(f'supervisor score history: {supervisor.score_history}, length: {len(formatted_history)}')
        total_cost = cost_breakdown.agent_cost + cost_breakdown.supervisor_cost + cost_breakdown.websearch_cost + cost_breakdown.stt_cost + cost_breakdown.tts_cost
        # Create MongoDB document
        mongo_doc = {
            "user": ObjectId(DEFAULT_USER_ID),
            "call_sid": f"{call_sid} , (Phone number: {phone_number})",
            "phone_number": phone_number,
            "call_sid_new": call_sid,
            "x_call_id": x_call_id,  # SIP X-Call-ID for correlation with external systems
            "recording_url": generate_reording_path(x_call_id, phone_number),
            "start_time": datetime.strptime(starting_time, "%Y-%m-%d %H:%M:%S"),
            "end_time": datetime.strptime(ending_time, "%Y-%m-%d %H:%M:%S"),
            "duration_seconds": elapsed_time,
            "tokens": {
                "agent": {
                    "input_tokens": agent_input_tokens,
                    "output_tokens": agent_output_tokens,
                    "model": "gpt-4.1-mini"
                },
                "supervisor": {
                    "input_tokens": supervisor_input_tokens,
                    "output_tokens": supervisor_output_tokens,
                    "model": "gpt-4.1-mini"
                },
                "websearch": {
                    "input_tokens": websearch_input_tokens,
                    "output_tokens": websearch_output_tokens,
                    "model": "gpt-4o"
                },
                "total": {
                    "input_tokens": agent_input_tokens + supervisor_input_tokens + websearch_input_tokens,
                    "output_tokens": agent_output_tokens + supervisor_output_tokens + websearch_output_tokens
                }
            },
            "audio_usage": {
                "stt": {
                    "audio_seconds": stt_usage_seconds,
                    "provider": stt_provider,
                    "model": stt_model
                },
                "tts": {
                    "characters": tts_usage_characters,
                    "provider": tts_provider,
                    "model": tts_model
                }
            },
            "cost": {
                "agent_cost": cost_breakdown.agent_cost,
                "supervisor_cost": cost_breakdown.supervisor_cost,
                "websearch_cost": cost_breakdown.websearch_cost,
                "stt_cost": cost_breakdown.stt_cost,
                "tts_cost": cost_breakdown.tts_cost,
                "total_cost": total_cost,
                "detailed_breakdown": cost_summary
            },
            "conversation_history": formatted_history,
            "createdAt": datetime.now()
        }
        logger.debug(f"MongoDB Document: {mongo_doc}")
        # Insert document to MongoDB
        try:
            result = costlogs_collection.insert_one(mongo_doc)
            logger.info(f"Database operation successful: {result}")
        except Exception as e:
            logger.error(f"Database operation failed: {e}")

        # Also send to existing API for backward compatibility
        data = {
            "start_time": starting_time,
            "end_time": ending_time,
            "call_sid": call_sid,
            "cost": total_cost,
            "conversation_history": conversation_history
        }
        logger.debug(f"Payload Sent: {data}")

        url = os.getenv("PYTHON_ANYWHERE_COST_LOGGING")

        # Send the POST request with JSON data using async HTTP
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 201:
                        response_data = await response.json()
                        logger.info(f"Success: {response_data}")
                    else:
                        response_text = await response.text()
                        logger.error(f"Error: {response.status}, {response_text}")
        except Exception as e:
            logger.error(f"Error sending data to API: {e}")

    # At shutdown, generate and log the summary from the usage collector
    async def cleanup_and_log():
        # Stop background audio first to prevent generator cleanup issues
        try:
            if typing_handle is not None:
                typing_handle.stop()
                logger.info("Stopped typing sounds during cleanup")
        except Exception as e:
            logger.warning(f"Warning during typing sound cleanup: {e}")
        
        try:
            await background_audio.stop()
            logger.info("Stopped background audio player during cleanup")
        except Exception as e:
            logger.warning(f"Warning during background audio cleanup: {e}")
        
        await log_usage(starting_time, call_sid, conversation_history)
        # Clean up call-specific cost tracker
        cleanup_call_tracker(call_sid)
        logger.info(f"Cleaned up cost tracker for call: {call_sid}")
        
        # Log call end and cleanup call-specific logs
        try:
            duration = datetime.now() - datetime.strptime(starting_time, '%Y-%m-%d %H:%M:%S')
            logger.info(f"📞 CALL ENDED - Total duration: {duration}")
            logger.info(f"📞 Final cleanup completed")
            cleanup_call_logs(call_sid)
            logger.info(f"Cleaned up call-specific logs for: {call_sid}")
        except Exception as e:
            logger.warning(f"Warning during call end logging: {e}")
    
    ctx.add_shutdown_callback(cleanup_and_log)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, port=int(os.getenv("PORT"))))
