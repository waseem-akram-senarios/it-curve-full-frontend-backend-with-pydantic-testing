#!/usr/bin/env python3
"""
Script to fix the book_trips function with proper error handling and retry mechanisms
"""

import re

def fix_book_trips_function():
    """Fix the book_trips function in helper_functions.py"""
    
    file_path = "/home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot/helper_functions.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the book_trips function and replace it with the improved version
    improved_function = '''    @function_tool()
    async def book_trips(self) -> str:
        """
        The function books the trip(s) by calling the booking APIs that use the agent's main_leg and return_leg parameters.
        Enhanced with robust error handling, retry mechanisms, and session stability.
        Returns:
            str: Booking confirmation, error message, or API response summary.
        """

        logger.info("🚀 [BOOK_TRIPS] Starting trip booking process...")
        
        try:
            # Validate trip data availability
            if not hasattr(self, 'main_leg') or not hasattr(self, 'return_leg'):
                logger.warning("❌ [BOOK_TRIPS] No leg attributes exist")
                return "Please provide trip details before booking. You need to specify at least pickup and dropoff locations."
            
            if not self.main_leg and not self.return_leg:
                logger.warning("❌ [BOOK_TRIPS] Both legs are empty")
                return "No trip details found. Please provide pickup and dropoff information before booking."

            # Prepare the payload with error handling
            logger.info("📦 [BOOK_TRIPS] Preparing trip payload...")
            try:
                if self.return_leg and self.main_leg:
                    logger.info("🔄 [BOOK_TRIPS] Processing return trip with main leg")
                    main_payload = await self.convert_pydantic_to_backend_api(self.main_leg)
                    return_payload = await self.convert_pydantic_to_backend_api(self.return_leg)
                    payload = await combine_payload(main_payload, return_payload)
                elif self.main_leg:
                    logger.info("📍 [BOOK_TRIPS] Processing main leg only")
                    payload = await self.convert_pydantic_to_backend_api(self.main_leg)
                elif self.return_leg:
                    logger.info("📍 [BOOK_TRIPS] Processing return leg only")
                    payload = await self.convert_pydantic_to_backend_api(self.return_leg)
                else:
                    logger.error("❌ [BOOK_TRIPS] No valid legs provided")
                    return "Error: No valid trip details found. Please provide pickup and dropoff information."
            except Exception as e:
                logger.error(f"❌ [BOOK_TRIPS] Payload preparation failed: {e}")
                return "I encountered an error while preparing your trip details. Please try again."

            # Validate API endpoint
            url = os.getenv("TRIP_BOOKING_API")
            if not url:
                logger.error("❌ [BOOK_TRIPS] TRIP_BOOKING_API environment variable not set")
                return "Booking service is not configured. Please contact support."

            # Log payload for debugging
            logger.info("📝 [BOOK_TRIPS] Logging trip payload...")
            try:
                payload_call_id = self.call_sid or "unknown"
                os.makedirs("logs/trip_book_payload", exist_ok=True)
                with open(f"logs/trip_book_payload/final_payload_{payload_call_id}.txt", "w") as f:
                    f.write(json.dumps(payload, indent=4))
                logger.info(f"✅ [BOOK_TRIPS] Payload logged successfully")
            except Exception as e:
                logger.warning(f"⚠️ [BOOK_TRIPS] Failed to log payload: {e}")

            # Enhanced API call with retry mechanism
            logger.info("🌐 [BOOK_TRIPS] Sending booking request to API...")
            max_retries = 3
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 [BOOK_TRIPS] Attempt {attempt + 1}/{max_retries}")
                    
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(
                            url, 
                            json=payload, 
                            headers={
                                "Content-Type": "application/json",
                                "User-Agent": "VoiceAgent/1.0"
                            }
                        ) as response:
                            
                            logger.info(f"📡 [BOOK_TRIPS] API Response Status: {response.status}")
                            
                            if response.status == 200:
                                try:
                                    response_data = await response.json()
                                    logger.info(f"✅ [BOOK_TRIPS] API Response received successfully")
                                    
                                    if response_data.get('responseCode') == 200:
                                        return await self._process_successful_booking(response_data, payload)
                                    else:
                                        error_message = response_data.get("responseMessage", "Unknown error")
                                        error_code = response_data.get("responseCode", "Unknown")
                                        logger.error(f"❌ [BOOK_TRIPS] API Error - Code: {error_code}, Message: {error_message}")
                                        return f"I'm sorry, but there was an issue booking your trip. Error: {error_message}. Please try again or contact support."
                                        
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ [BOOK_TRIPS] JSON parsing failed: {e}")
                                    text_response = await response.text()
                                    logger.debug(f"📄 [BOOK_TRIPS] Raw response: {text_response[:200]}...")
                                    if attempt < max_retries - 1:
                                        logger.info(f"🔄 [BOOK_TRIPS] Retrying due to JSON parsing error...")
                                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                        continue
                                    return "I received an invalid response from the booking system. Please try again later."
                                    
                            else:
                                logger.error(f"❌ [BOOK_TRIPS] HTTP Error: {response.status}")
                                if attempt < max_retries - 1:
                                    logger.info(f"🔄 [BOOK_TRIPS] Retrying due to HTTP error...")
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                return f"I'm sorry, but the booking service is currently unavailable (HTTP {response.status}). Please try again later or contact support."
                                
                except asyncio.TimeoutError:
                    logger.error(f"⏰ [BOOK_TRIPS] Request timeout on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 [BOOK_TRIPS] Retrying due to timeout...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return "The booking request is taking too long. Please try again later."
                    
                except aiohttp.ClientError as e:
                    logger.error(f"🌐 [BOOK_TRIPS] Network error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 [BOOK_TRIPS] Retrying due to network error...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return "I'm having trouble connecting to the booking service. Please check your internet connection and try again."

            logger.error("❌ [BOOK_TRIPS] All retry attempts exhausted")
            return "I'm sorry, but I'm unable to complete your booking at this time. Please try again later or contact support."

        except Exception as e:
            logger.error(f"❌ [BOOK_TRIPS] Unexpected error: {e}")
            return "I encountered an unexpected error while trying to book your trip. Please try again later."

    async def _process_successful_booking(self, response_data: dict, payload: dict) -> str:
        """Process successful booking response with enhanced error handling"""
        try:
            logger.info("🎉 [BOOK_TRIPS] Processing successful booking response...")
            
            irefid_list = [response_data.get('iRefID')]
            if response_data.get('returnLegsList') is not None:
                irefid_list.append(response_data.get('returnLegsList'))

            response_text = ""

            for trip_data, irefId in zip(payload['addressInfo']["Trips"], irefid_list):
                try:
                    estimates = trip_data['Details'][0]['estimatedInfo']
                    pickup_address = trip_data['Details'][0]['addressDetails']
                    dropoff_address = trip_data['Details'][1]['addressDetails']
                    pickup_address_complete = f"{pickup_address['Address']}, {pickup_address['City']}, {pickup_address['State']}"
                    dropoff_address_complete = f"{dropoff_address['Address']}, {dropoff_address['City']}, {dropoff_address['State']}"
                    estimate_distance = estimates.get("EstimatedDistance", 0)
                    estimate_time = estimates.get('EstimatedTime', 0)
                    estimate_cost = estimates.get('EstimatedCost', 0)
                    copay_cost = estimates.get('CoPay', 0)

                    # Get weather information with error handling
                    weather = "Weather information is not available at this time."
                    try:
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
                        logger.debug(f"🌤️ [BOOK_TRIPS] Weather: {weather}")
                    except Exception as e:
                        logger.warning(f"⚠️ [BOOK_TRIPS] Weather lookup failed: {e}")

                    # Build confirmation message
                    if str(copay_cost) == "0":
                        response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and the distance between your pickup and dropoff is {estimate_distance} miles. Estimated cost is ${estimate_cost}. Weather at your destination: {weather}"
                    else:
                        response_text += f"Trip has been booked! Your Trip Number is {irefId}. It will take around {estimate_time} minutes and the distance between your pickup and dropoff is {estimate_distance} miles. Estimated cost is ${estimate_cost} and copay amount is ${copay_cost}. Weather at your destination: {weather}"

                except Exception as e:
                    logger.error(f"❌ [BOOK_TRIPS] Error processing trip data: {e}")
                    response_text += f"Trip has been booked! Your Trip Number is {irefId}. Please contact support for additional details."

            # Clear trip data
            self.main_leg = None
            self.return_leg = None

            logger.info(f"✅ [BOOK_TRIPS] Booking completed successfully: {response_text}")
            return response_text
            
        except Exception as e:
            logger.error(f"❌ [BOOK_TRIPS] Error processing successful booking: {e}")
            return "Your trip has been booked successfully, but I'm unable to provide the complete confirmation details at this time. Please contact support for your booking confirmation."'''
    
    # Find and replace the book_trips function
    pattern = r'@function_tool\(\)\s*\n\s*async def book_trips\(self\) -> str:.*?(?=\n    @function_tool\(\)|\n    async def|\nclass|\Z)'
    
    # Use a more specific pattern to match the entire function
    start_pattern = r'@function_tool\(\)\s*\n\s*async def book_trips\(self\) -> str:'
    
    if re.search(start_pattern, content):
        # Find the start and end of the function
        start_match = re.search(start_pattern, content)
        start_pos = start_match.start()
        
        # Find the next function or class definition
        remaining_content = content[start_pos:]
        
        # Look for the next function definition
        next_func_pattern = r'\n    @function_tool\(\)|\n    async def|\nclass '
        next_match = re.search(next_func_pattern, remaining_content[1:])
        
        if next_match:
            end_pos = start_pos + next_match.start() + 1
        else:
            end_pos = len(content)
        
        # Replace the function
        new_content = content[:start_pos] + improved_function + content[end_pos:]
        
        # Write the updated content
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Successfully updated book_trips function with enhanced error handling")
        return True
    else:
        print("❌ Could not find book_trips function to replace")
        return False

if __name__ == "__main__":
    fix_book_trips_function()
