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


async def entrypoint(ctx: agents.JobContext):

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

            affiliate = await recognize_affiliate(recipient)
            success = True
            ivr = True
            affiliate_id = affiliate["AffiliateID"]
            family_id = affiliate["AffiliateFamilyID"]

            phone_number = await extract_phone_number(caller)
            # print(f"\n\nPhone Number: {phone_number}")
            all_riders_info = await get_client_name_voice(phone_number, affiliate_id, family_id)

        except Exception as e:
            print(f"Error in recognizing affiliate from number: {e}")

        if not success:
            try:
                family_id = metadata['familyId']
                affiliate_id = metadata['affiliateId']
                affiliate = await recognize_affiliate_by_ids(family_id, affiliate_id)
                print("*************AFFILIATE*******:\n", affiliate)
                phone_number = metadata['phoneNo']
                if phone_number != "":
                    phone_number = await extract_phone_number(phone_number)
                    # print(f"\n\nPhone Number: {phone_number}")
                    all_riders_info = await get_client_name_voice(phone_number, affiliate_id, family_id)
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
        bounds, _, _ = await fetch_affiliate_details(affiliate_id)
        counties_prompt = f"""What are the counties that lies within these coordinates {bounds}. Only return names of the counties separated by commas. 
        Do not add name of the states. Do not add any other line or comment. I just need the name of the counties
        Sample response would be 'county_1, county_2, ......, county_n'
        DO NOT RETURN MORE THAN 10 COUNTY NAMES
        """
        Servica_Area = await search_web_manual(counties_prompt)
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
            frequent_rides = await get_frequnt_addresses_manual(client_id, affiliate_id)
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

    print(f"\n\nPrompt: {prompt}\n\n")

    background_audio = BackgroundAudioPlayer(thinking_sound=[
                        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
                        AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING,volume=0.6)
                    ])

    allow_interruption_status = False

    session = AgentSession(
        # stt = deepgram.STT(model="nova-3",language="en-US",keyterms=["snouffer"]),
        stt=openai.STT(model='gpt-4o-transcribe',language="en", use_realtime=True),
        allow_interruptions=allow_interruption_status,
        llm=openai.LLM(model="gpt-4.1", temperature=0.5),
        tts=deepgram.TTS(model="aura-asteria-en"),
        vad=silero.VAD.load(min_silence_duration=0.75),
        # min_interruption_duration=1.0,
        # min_endpointing_delay = 1.0,
        turn_detection=EnglishModel(),
        # turn_detection="vad",
    )
    try:
        agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=prompt, affiliate_id=int(affiliate_id))
    except Exception as e:
        print(f"\n\n\nError in generating agent object: {e}\n\n")
        agent = Assistant(call_sid=call_sid, room=ctx.room, instructions=prompt, affiliate_id=65)

    await background_audio.start(room=ctx.room, agent_session=session)

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            text_enabled=True
        ),
    )
    supervisor = Supervisor(session=session,
                            room=agent.room,
                            llm=openai.LLM(model="gpt-4o-mini"))
    await supervisor.start()

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
            if event.item.role == 'user':
                conversation_history.append({
                'speaker': 'User',
                'transcription': event.item.text_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

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
        digit = dtmf.digit
        logger.info(f"DTMF received from sip: {digit}")
        if digit == "0":
            asyncio.create_task(transfer_call_dtmf(agent.room, agent.room.name))
        if digit == "1":
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
