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

# Load variables from .env file
load_dotenv()

App_Directory = Path(__file__).parent

# Twilio credentials (from environment)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

MUSIC_PATH = os.path.join(App_Directory, "music.wav")

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def check_address_validity(latitude: str, longitude: str, address_type: str):
    """Helper function to check if the address is valid."""
    if latitude == "0" or longitude == "0" or latitude == "" or longitude == "":
        return f"{address_type} address is missing latitude or longitude"
    return None

async def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

async def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

async def create_address_verification_prompt(address):
    """Creates a clear prompt for address verification with explicit JSON format instructions."""
    return f"""Verify if this address is valid or not: 
```
{address}
```

Please respond ONLY with a valid JSON object in the following format:
{{
    "valid": true/false,
    "confidence": 0-100,
    "normalized_address": "full normalized address if valid",
    "latitude": numeric value if valid (e.g., 38.9072),
    "longitude": numeric value if valid (e.g., -77.0369),
    "error": "reason if invalid or empty string if valid"
}}

Ensure your response contains ONLY the JSON object with no additional text, explanation, or formatting."""

async def verify_address(address):
    """Verify an address and parse the JSON response."""
    prompt = await create_address_verification_prompt(address)
    
    try:
        # Get the response from the web search function
        response = await search_web_manual(prompt)
        
        # Extract the JSON object from the response
        # This handles cases where the response might contain extra text
        json_match = re.search(r'({[\s\S]*})', response)
        if json_match:
            json_str = json_match.group(1)
            # Parse the JSON response
            result = json.loads(json_str)
            # Ensure coordinates are numbers, not strings if they exist
            if result.get("valid") and "latitude" in result and "longitude" in result:
                try:
                    result["latitude"] = float(result["latitude"])
                    result["longitude"] = float(result["longitude"])
                except (ValueError, TypeError):
                    # If coordinates can't be converted to float, leave as is
                    pass
            return result
        else:
            return {"valid": False, "confidence": 0, "normalized_address": "", 
                    "error": "Could not parse JSON from response"}
    except json.JSONDecodeError as e:
        return {"valid": False, "confidence": 0, "normalized_address": "", 
                "latitude": None, "longitude": None,
                "error": f"JSON parsing error: {str(e)}. Raw response: {response[:100]}..."}
    except Exception as e:
        return {"valid": False, "confidence": 0, "normalized_address": "", 
                "latitude": None, "longitude": None,
                "error": f"Verification error: {str(e)}"}


async def recognize_affiliate_by_ids(family_id, affiliate_id):
    url = os.getenv("GET_AFFILIATE_API")

    recognized_affiliate = {
        "AffiliateID": "1",
        "AffiliateFamilyID": "1",
        "TypeForIVRAI": "both",
        "AffiliateName": "Agency"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    raw_text = await response.text()
                    data = json.loads(raw_text)  # manual parse
                    print(data)
                    for affiliate_data in data:
                        if str(affiliate_data["AffiliateFamilyID"]) == family_id and str(affiliate_data["AffiliateID"]) == affiliate_id:
                            recognized_affiliate = affiliate_data
                else:
                    return f"GetIVRAIAffiliate API failed with status: {response.status}"
    except Exception as e:
        return f"Error in getting response from GetIVRAIAffiliate API: {e}"

    return recognized_affiliate

async def meters_to_miles(meters):
    try:
        meters = float(meters)
        miles = meters / 1609.344
        return miles
    except ValueError:
        return meters

async def seconds_to_minutes(seconds):
    try:
        seconds = float(seconds)
        minutes = seconds / 60
        return minutes
    except ValueError:
        return seconds

async def search_web_manual(prompt: str):

    print(f"\n\nCalled search_web_manual function with prompt: {prompt}\n\n")

    try:
        # Use the OpenAI API client to make the call
        response = await openai_client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt
        )
    
        return response.output_text
    
    except Exception as e:
        print(f"Error in search web: {e}")
        return "Web search failed!"

async def get_frequnt_addresses_manual(client_id, affiliate_id):
    url = os.getenv("GET_HISTORIC_RIDES_API")

    payload = {
        "clientID": str(client_id),
        "affiliateID": str(affiliate_id),
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
                address_data = response_json.get("responseJSON", "[]")
                address_data_json = json.loads(address_data)

                for trip in address_data_json:
                    pickup_address = trip.get("PUAddress", "") + trip.get("PUCity", "") + trip.get("PUState", "")
                    dropoff_address = trip.get("DOAddress", "") + trip.get("DOCity", "") + trip.get("DOState", "")
                    frequent_addresses += pickup_address + "\n" + dropoff_address + "\n"
            
            except json.JSONDecodeError:
                print("Failed to parse response as JSON.")
                print("Raw Response:", response_text)

    if frequent_addresses.strip() == "":
        frequent_addresses = "No Data Available"
    
    frequent_addresses_result = f"""Rider Frequently Used Addresses are: ``{frequent_addresses}``\n
    Only use these addresses for address completion. Use [get_ETA] function to get Last/Latest trip details
    """
    
    return frequent_addresses_result

async def get_match_source(prompt):
    model = "gpt-4o"

    user_message = {
        "role": "user",
        "content": prompt
    }

    source = None

    try:
        completion = await openai_client.chat.completions.create(
            model=model,
            messages=[user_message],
            temperature=0,
            max_tokens=100
        )
        source = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI location error: {e}")
    
    return source
    
async def format_phone_number(phone_number):
    try:
        # Remove periods, hyphens, and any non-digit characters from the phone number
        phone_number = re.sub(r'[^0-9]', '', phone_number)

        # Check if the number starts with +1 and remove the +1 prefix if present
        if phone_number.startswith('1') and len(phone_number) == 11:
            phone_number = phone_number[1:]  # Remove the leading 1 if it's present

        # Ensure the phone number is exactly 10 digits
        if len(phone_number) == 10 and phone_number.isdigit():
            # Use regex to format the phone number into xxx-xxx-xxxx
            formatted_number = re.sub(r'(\d{3})(\d{3})(\d{4})$', r'\1-\2-\3', phone_number)
            return formatted_number
        else:
            # If the phone number doesn't meet the criteria, return it as is
            return phone_number
    except:
        return phone_number

async def fetch_affiliate_details(affiliate_id):
    url = os.getenv("ALL_AFFILIATE_DETAILS_API")

    # Define the payload
    data = {
        "iaffiliateid": int(affiliate_id)  # Example payload, adjust as needed
    }

    print(f"\n\n\nPayload Sent for Affiliate Information: {data}\n\n\n")

    bounds = {
        "x1": 0,
        "y1": 0,
        "x2": 0,
        "y2": 0
    }

    funding_sources = []
    copay_fs_list = []

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            # Check for a successful response
            if response.status == 200:
        
                # If it's not JSON, handle it as plain text
                response_text = await response.text()
                try:
                    # Try to convert the string to a dictionary
                    response_dict = json.loads(response_text)

                    try:
                        bounds_str = response_dict["Table1"][0]["AffiliateBounds"]
                        bounds_lower, bounds_upper = bounds_str.split("|")
                        x1, y1 = bounds_lower.split(",")
                        x2, y2 = bounds_upper.split(",")

                        # Assign values to bounds directly
                        bounds["x1"] = x1
                        bounds["y1"] = y1
                        bounds["x2"] = x2
                        bounds["y2"] = y2
                    
                    except: 
                        pass

                    # return bounds
                    try:
                        funding_sources = response_dict["Table2"]
                    except:
                        pass

                    try:
                        copay_fs_str = response_dict["Table"][0]["CopayFSList"]
                        copay_fs_list = copay_fs_str.split(",")
                        copay_fs_list = [str(item).strip() for item in copay_fs_list]
                    except:
                        pass
                    
                    return bounds, funding_sources, copay_fs_list
                except Exception as e:
                    print(f"Failed to decode JSON from string: {e}")
            
    return bounds, funding_sources, copay_fs_list

async def recognize_affiliate(receiver):
    receiver = str(receiver)
    match = re.search(r'sip:(\+\d+)@', receiver)
    if match:
        receiver_number = match.group(1)
        # receiver_number = "+16318022590"
        receiver_number = await extract_phone_number(receiver_number)
    elif receiver:
        receiver_number = await extract_phone_number(receiver)
    else:
        return "Receiver Number not found!"
    
    url = os.getenv("GET_AFFILIATE_API")

    response = requests.post(url)

    try:
        if response.status_code == 200:
            data = response.json()
        else:
            return "GetIVRAIAffiliate API failed!"
    except Exception as e:
        return f"Error in getting response from GetIVRAIAffiliate API: {e}"
    
    try:
        for affiliate in data:
            if affiliate["TwillioPhoneNumber"] == receiver_number:
                return affiliate
        return "Affiliate Not Found!"

    except Exception as e:
        return f"Error in recognizing affiliate: {e}"

async def extract_phone_number(phone_number):

    phone_number = str(phone_number)

    # Dictionary of country codes and their lengths
    country_codes = {
        '1': 1,   # USA, Canada, etc.
        '20': 2,  # Egypt
        '44': 2,  # UK
        '91': 2,  # India
        '33': 2,  # France
        '49': 2,  # Germany
        '61': 2,  # Australia
        '39': 2,  # Italy
        '81': 2,  # Japan
        '34': 2,  # Spain
        '92': 2,  # Pakistan
    }
    # Remove the '+' sign and the country code using the dictionary
    phone_number = phone_number.lstrip('+')
    
    for code, length in country_codes.items():
        if phone_number.startswith(code):
            phone_number = phone_number[length:]  # Remove the country code part
            break  # Exit the loop once the code is found
    
    return phone_number

async def get_client_name_voice(caller_number, affiliate_id, family_id):
    url = os.getenv("SEARCH_CLIENT_DATA_API")
    caller_number = str(caller_number)
    payload = {
        "searchCriteria": "CustomerPhone",
        "searchText": caller_number,
        "bActiveRecords": True,
        "iATSPID": int(affiliate_id),
        "iDTSPID": int(family_id)
    }
    headers = {
        "Content-Type": "application/json"
    }

    result = {}
    rider_count = 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                response = await resp.json()

        if response.get("responseCode") == 200:
            client_list = json.loads(response.get("responseJSON", "[]"))
            for i, client in enumerate(client_list, 1):
                name = (client.get('FirstName', '') + ' ' + client.get('LastName', '')).strip()
                medical_id_raw = client.get("MedicalId", "")
                if medical_id_raw and str(medical_id_raw).isdigit():
                    rider_id = int(medical_id_raw)
                    rider_id = rider_id if rider_id != 0 else "Unknown"
                else:
                    rider_id = "Unknown"
                
                rider_data = {
                    "name": name,
                    "client_id": int(client.get('Id', 0)),
                    "city": client.get("City", ""),
                    "state": client.get("State", ""),
                    "current_location/home_address": client.get("Address", ""),
                    "rider_id": rider_id
                }

                result[f"rider_{i}"] = rider_data
                rider_count += 1

            result["number_of_riders"] = rider_count
        else:
            print("Request failed!")
            result["number_of_riders"] = 0

    except Exception as e:
        print(f"Error occurred in getting client Name: {e}")
        result["number_of_riders"] = rider_count

    return result

def calculate_cost(llm_input_tokens, llm_output_tokens, stt_audio_seconds, tts_characters):
    # Pricing per unit
    llm_input_cost_per_million = 2.50  # $ per 1M tokens
    llm_output_cost_per_million = 10  # $ per 1M tokens
    stt_cost_per_minute = 0.004
    tts_cost_per_million_character = 15  
    
    # Cost calculations
    llm_input_cost = (llm_input_tokens / 1000000) * llm_input_cost_per_million
    llm_output_cost = (llm_output_tokens / 1000000) * llm_output_cost_per_million
    stt_cost = (stt_audio_seconds/60) * stt_cost_per_minute
    tts_cost = (tts_characters / 1000000) * tts_cost_per_million_character
    
    # Total cost
    total_cost = llm_input_cost + llm_output_cost + stt_cost + tts_cost

    cost = {
        'stt_cost': stt_cost,
        'tts_cost': tts_cost,
        'llm_input_cost': llm_input_cost,
        'llm_output_cost': llm_output_cost,
        'total_cost': total_cost
    }
    
    return cost

async def get_location_from_openai_async(address):
    model = "gpt-4o"
    # api_key = os.getenv("OPENAI_API_KEY")
    # client = AsyncOpenAI(api_key=api_key)

    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant that returns only the latitude and longitude of a given address. "
            "Respond ONLY with a JSON object like: {\"lat\": <value>, \"lng\": <value>}."
            "Values must be floating point numbers with as much accuracy as possible."
            "If location is not available return 0 in both values."
        )
    }

    user_message = {
        "role": "user",
        "content": f"What are the coordinates of: {address}?"
    }

    location = {'lat': 0, 'lng': 0}

    try:
        completion = await openai_client.chat.completions.create(
            model=model,
            messages=[system_message, user_message],
            temperature=0.2,
            max_tokens=100
        )
        content = completion.choices[0].message.content.strip()
        location = json.loads(content)
    except Exception as e:
        print(f"OpenAI location error: {e}")
    
    return location

async def summarize_address_results(address):
    model = "gpt-4o"

    system_message = {
        "role": "system",
        "content": (
            """
            Summarize this information so that TTS would pronounce efficiently. Here are the guidelines
            1. Ensure that there are no asterisks used in the response. If any asterisks are present, remove them and ensure proper formatting.
            2. Address details should include street address, city, state, and zip code. 
            3. Store & Pharmacy hours should be presented in a clear format, stating the opening and closing times without additional symbols or marks. If any store or pharmacy is closed for a specific reason (such as a closure date), make sure to mention it.
            4. Links or URLs should be removed.
            5. Respond in bullet points with each bullet representing one address.
            6. Ensure that there are no dash used in the response. If any dash are present, remove them
            """
        )
    }

    user_message = {
        "role": "user",
        "content": f"Summarize this addresses: {address}?"
    }

    result = ""

    try:
        completion = await openai_client.chat.completions.create(
            model=model,
            messages=[system_message, user_message],
            temperature=0.2,
            max_tokens=100
        )
        result = completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"OpenAI summary error: {e}")
    
    return result

async def is_point_out_of_bounds(bounds, location):

    print("\n\n\n")
    print(f"Bounds: {bounds}")
    print(f"Location: {location}")
    print("\n\n\n")
    # Convert bounds to float for accurate comparison
    x1, y1 = float(bounds['x1']), float(bounds['y1'])
    x2, y2 = float(bounds['x2']), float(bounds['y2'])

    if x1 == 0 and y1 == 0 and x2 == 0 and y2 == 0:
        return False

    # Latitude and Longitude of the point to check
    point_lat = location["lat"]
    point_lon = location["lng"]

    if point_lat == 0 and point_lon == 0:
        return False

    # Check if the point is inside the bounds
    if x1 <= point_lat <= x2 and y1 <= point_lon <= y2:
        return False
    else:
        return True