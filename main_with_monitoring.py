import os
import pytz
import logging
import pymongo
import uuid
import asyncio
from bson.objectid import ObjectId
from pathlib import Path
from dotenv import load_dotenv
from logging_config import get_logger
from livekit import agents

# Initialize logger
logger = get_logger('main_with_monitoring')
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
from monitoring_agent import MonitoringAgent, ConversationAnalysis
from datetime import datetime
import copy


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

# Collection for monitoring alerts
monitoring_alerts_collection = db.monitoring_alerts

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


# Function to handle confusion detected by monitoring agent
async def handle_confusion_detected(analysis: ConversationAnalysis, call_sid: str, session: AgentSession = None):
    """Handle when the monitoring agent detects confusion in the conversation."""
    logger.warning(f"Confusion detected in call {call_sid}: {analysis.reason}")
    
    # Log the confusion event to MongoDB
    try:
        alert_doc = {
            "call_sid": call_sid,
            "timestamp": datetime.now(),
            "is_confused": analysis.is_confused,
            "confidence_score": analysis.confidence_score,
            "reason": analysis.reason,
            "recommended_action": analysis.recommended_action,
        }
        monitoring_alerts_collection.insert_one(alert_doc)
        logger.info(f"Confusion alert logged to MongoDB for call {call_sid}")
    except Exception as e:
        logger.error(f"Failed to log confusion alert to MongoDB: {e}")
    
    # Optional: Take immediate action if confusion score is very high
    if analysis.confidence_score > 0.85 and session:
        try:
            await session.say(
                "I notice we might be having some difficulty communicating. Let me transfer you to a live agent who can better assist you.", 
                allow_interruptions=True
            )
            # You could add logic here to trigger call transfer
        except Exception as e:
            logger.error(f"Failed to send clarification message: {e}")


async def entrypoint(ctx: agents.JobContext):

    # Store active tasks to prevent garbage collection
    _active_tasks = set()

    await ctx.connect()

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()

    # # Twilio code commented
    # call_sid = participant.attributes.get("sip.twilio.callSid", "Unknown")
    # if call_sid == "Unknown":
    call_sid = 'chat-' + str(uuid.uuid4())
    print(f"\n\nCall SID: {call_sid}\n\n")

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
        "AffiliateName": "Default",
        "ContactName": "",
        "X1": "0",
        "Y1": "0",
        "X2": "0",
        "Y2": "0",
        "Address": "",
        "City": "",
        "State": "",
        "Zipcode": ""
    }

    phone_number = ""
    try:
        phone_number = metadata.get("phonenumber", "")
        if phone_number == "":
            phone_number = "00000000000"
    except:
        phone_number = "00000000000"

    affiliate_id = os.getenv("DEFAULT_AFFILIATE_ID")
    if affiliate_id is None:
        affiliate_id = "1"

    affiliate_name = ""
    try:
        try:
            bounds, _, affiliate_details = await fetch_affiliate_details(affiliate_id)
            affiliate_name = affiliate_details.get("AffiliateName", "")
        except Exception as e:
            print(f"Error in getting affiliate name: {e}")
            affiliate_name = "Default"
    except Exception as e:
        print(f"Error in getting affiliate details: {e}")
        affiliate_name = "Default"

    allow_interruption_status = True

    ivr = False
    try:
        ivr = os.getenv("IVR_MODE", "FALSE")
        ivr = ivr.lower() == "true"
    except Exception as e:
        print(f"Error in getting IVR mode: {e}")
        ivr = False

    agent = None
    curr_prompt = ""

    if ivr:
        try:
            main_leg = {"script": "main_leg", "complete": "no"}
            return_leg = {"script": "return_leg", "complete": "no"}
            agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
            agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                        agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                        agent.notify_driver, agent.cancel_trip]

            with open(os.path.join(App_Directory, "prompts", "prompt_widget_ivr.txt")) as file:
                curr_prompt = file.read()

        except Exception as e:
            print(f"Error in loading prompt: {e}")
            main_leg = {"script": "main_leg", "complete": "no"}
            return_leg = {"script": "return_leg", "complete": "no"}
            agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
            agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                        agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                        agent.notify_driver, agent.cancel_trip]

            with open(os.path.join(App_Directory, "prompts", "prompt_widget_ivr.txt")) as file:
                curr_prompt = file.read()
    else:
        try:
            if all_riders_info["number_of_riders"] == 1:
                rider = all_riders_info["rider_1"]

                if rider["name"] == "new_rider":
                    main_leg = {"script": "main_leg", "complete": "no"}
                    return_leg = {"script": "return_leg", "complete": "no"}
                    agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
                    agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                                agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                                agent.notify_driver, agent.cancel_trip]
                    with open(os.path.join(App_Directory, "prompts", "prompt_new_rider.txt")) as file:
                        curr_prompt = file.read()
                elif rider["name"] == "Unknown":
                    main_leg = {"script": "main_leg", "complete": "no"}
                    return_leg = {"script": "return_leg", "complete": "no"}
                    agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
                    agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                                agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                                agent.notify_driver, agent.cancel_trip]
                    with open(os.path.join(App_Directory, "prompts", "prompt_new_rider.txt")) as file:
                        curr_prompt = file.read()
                elif rider["name"]:
                    main_leg = {"script": "main_leg", "complete": "no"}
                    return_leg = {"script": "return_leg", "complete": "no"}
                    agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
                    agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                                agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                                agent.notify_driver, agent.cancel_trip]
                    with open(os.path.join(App_Directory, "prompts", "prompt_old_rider.txt")) as file:
                        curr_prompt = file.read()

            elif all_riders_info["number_of_riders"] > 1:
                main_leg = {"script": "main_leg", "complete": "no"}
                return_leg = {"script": "return_leg", "complete": "no"}
                agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
                agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                            agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                            agent.notify_driver, agent.cancel_trip]
                with open(os.path.join(App_Directory, "prompts", "prompt_multiple_riders.txt")) as file:
                    curr_prompt = file.read()
            
        except Exception as e:
            print(f"Error in initializing agent: {e}")
            main_leg = {"script": "main_leg", "complete": "no"}
            return_leg = {"script": "return_leg", "complete": "no"}
            agent = Assistant(call_sid=call_sid, room=ctx.room, affiliate_id=affiliate_id, main_leg=main_leg, return_leg=return_leg)
            agent.tools = [agent.get_rider_info, agent.get_IDs, agent.get_rider_profile, agent.get_rider_trips, agent.confirm_address, 
                        agent.book_trip, agent.book_return_trip, agent.transfer_call, agent.transfer_call_driver, agent.Play_Music, agent.Stop_Music, agent.get_fare, 
                        agent.notify_driver, agent.cancel_trip]
            with open(os.path.join(App_Directory, "prompts", "prompt_widget.txt")) as file:
                curr_prompt = file.read()
                
    session = await ctx.create_session(
        agent=agent,
        model="gpt-4",
        instructions=curr_prompt,
        voice_config=AudioConfig(
            default_voice="en-US-Neural2-F",
            # default_voice="en-US-JennyNeural", 
            speech_rate=1.0
        ),
        room_input_options=RoomInputOptions(
            text_enabled=True
        ),
    )

    # Initialize the monitoring agent
    monitoring_agent = MonitoringAgent(confusion_threshold=0.7)
    
    # Register callback for confusion detection
    monitoring_agent.register_callback(
        lambda analysis: handle_confusion_detected(analysis, call_sid, session)
    )
    
    # Start monitoring in the background
    await monitoring_agent.start_monitoring(interval_seconds=10)
    
    # Add monitoring agent to shutdown tasks
    ctx.add_shutdown_callback(lambda: asyncio.create_task(monitoring_agent.stop_monitoring()))

    conversation_history = []
    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        print(f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}")
        if event.item.text_content != '':
            if event.item.role == 'assistant':
                conversation_history.append({
                'speaker': 'Agent',
                'transcription': event.item.text_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # Add to monitoring agent
                monitoring_agent.add_conversation_item('Agent', event.item.text_content)
                
            if event.item.role == 'user':
                conversation_history.append({
                'speaker': 'User',
                'transcription': event.item.text_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # Add to monitoring agent
                monitoring_agent.add_conversation_item('User', event.item.text_content)

    try:
        if ivr:
            greeting = f"""Thank you for contacting {affiliate_name} agency. My name is Alina, your digital agent,
            I can assist you with anything you need regarding your ride reservation, and more."""
        else:
            greeting = f"Thank you for contacting {affiliate_name} agency. My name is Alina, your digital agent"

    except Exception as e:
        greeting = "My name is Alina, your digital agent. How can I help you today?"
        print(f"\n\nError in getting greetings: {e}\n\n")

    try:
        if all_riders_info["number_of_riders"] == 1:
            rider = all_riders_info["rider_1"]
            if rider["name"] == "new_rider":
                await session.say(f"Hello! {greeting}. Can I have your name please?", allow_interruptions=allow_interruption_status)

            elif rider["name"] == "Unknown":
                await session.say(f"Hello! {greeting}. Can I have your phone number please?", allow_interruptions=allow_interruption_status)

            elif rider["name"]:
                try:
                    no_of_trips = rider.get("number_of_existing_trips", "0")
                    if int(no_of_trips) > 0:
                        await session.say(f"Hello {rider['name']}! {greeting}. You have {no_of_trips} existing trips in the system. How can I help you today?", allow_interruptions=allow_interruption_status)
                    else:
                        await session.say(f"Hello {rider['name']}! {greeting}. How can I help you today?", allow_interruptions=allow_interruption_status)
                except:
                    await session.say(f"Hello {rider['name']}! {greeting}. How can I help you today?", allow_interruptions=allow_interruption_status)

        elif all_riders_info["number_of_riders"] > 1:
            await session.say(f"Hello! {greeting}. I have multiple profiles for your number. Can I have your name please?", allow_interruptions=allow_interruption_status)

    except Exception as e:
        print(f"Error occured in starting initial statement: {e}")
        await session.say(f"Hello! {greeting}. How can I help you today?", allow_interruptions=allow_interruption_status)

    # Use the usage collector to aggregate agent usage metrics
    usage_collector = metrics.UsageCollector()

    # Add metrics to usage collector as they are received
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        usage_collector.collect(ev.metrics)

    @ctx.room.on("sip_dtmf_received")
    def handle_dtmf(dtmf: SipDTMF):
        # Enhanced logging for Asterisk debugging
        logger.info(f"[ASTERISK DTMF] Code: {dtmf.code} | Digit: '{dtmf.digit}' | Type: {type(dtmf.digit)}")
        digit = dtmf.digit

        # Check for potential Asterisk-specific DTMF encoding issues
        if digit is None or digit == "":
            logger.warning(f"[ASTERISK DTMF] Empty or None digit received, code was: {dtmf.code}")
            return

        if digit == "0":
            logger.info("[ASTERISK DTMF] Transferring to dispatcher")
            asyncio.create_task(transfer_call_dtmf(agent.room, agent.room.name))
        elif digit == "1":
            logger.info("[ASTERISK DTMF] Transferring to driver")
            asyncio.create_task(transfer_call_dtmf_driver(agent.room, agent.room.name))

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
                "llm_input_cost": cost.get('llm_input_cost', 0),
                "llm_output_cost": cost.get('llm_output_cost', 0),
                "total_cost": cost.get('total_cost', 0)
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
            "cost": cost['total_cost'],
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
