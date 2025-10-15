#!/usr/bin/env python3
"""
LOCAL PROJECT API TESTING - STEP BY STEP
Test all APIs in the project flow using local environment
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# API URLs from env.example
APIS = {
    "ALL_AFFILIATE_DETAILS_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetAffiliateBasedDetailForIvrAi",
    "GET_AFFILIATE_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetIvrAiAffiliate", 
    "SEARCH_CLIENT_DATA_API": "https://tgistagingreservationapi.itcurves.us/SearchClientData",
    "ITC_GEOCODE_API": "https://itcmap.itcurves.us/api/Map/geocode",
    "GET_PAYMENT_TYPE_FSID_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetPaymentTypeByFSID",
    "GET_PAYMENT_TPYE_AFFILIATE_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetPaymentTypebyAffiliateID",
    "RIDER_VERIFICATION_API": "https://siveaasapi.itcurves.us/api/common/CheckRiderEligibility",
    "GET_NAME_API": "https://siveaasapi.itcurves.us/api/common/GetRiderProfile",
    "GET_HISTORIC_RIDES_API": "https://tgistagingreservationapi.itcurves.us/GetHistoricRides",
    "GET_DIRECTION": "https://itcmap.itcurves.us/api/Map/directions",
    "GET_FARE_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetFareEstimate",
    "TRIP_STATS_API": "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetTripStatsDataByClient",
    "TRIP_BOOKING_API": "https://tgistagingreservationapi.itcurves.us/BookParatransitTrip",
    "EXISTING_RIDES_API": "https://tgistagingreservationapi.itcurves.us/GetExistingRides"
}

class APITester:
    def __init__(self):
        self.session = None
        self.results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_api(self, name, url, payload, expected_fields=None):
        """Test a single API endpoint"""
        print(f"\n🧪 Testing {name}")
        print(f"📍 URL: {url}")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            async with self.session.post(url, json=payload) as response:
                print(f"📡 Status: {response.status}")
                
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        response_data = json.loads(response_text)
                        print(f"✅ Success! Response: {json.dumps(response_data, indent=2)[:500]}...")
                        
                        # Validate expected fields if provided
                        if expected_fields:
                            missing_fields = []
                            for field in expected_fields:
                                if field not in response_data:
                                    missing_fields.append(field)
                            
                            if missing_fields:
                                print(f"⚠️ Missing expected fields: {missing_fields}")
                            else:
                                print(f"✅ All expected fields present: {expected_fields}")
                        
                        self.results[name] = {
                            "status": "SUCCESS",
                            "status_code": response.status,
                            "response": response_data
                        }
                        
                    except json.JSONDecodeError:
                        print(f"⚠️ Response is not JSON: {response_text[:200]}...")
                        self.results[name] = {
                            "status": "NON_JSON",
                            "status_code": response.status,
                            "response": response_text
                        }
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text[:200]}...")
                    self.results[name] = {
                        "status": "ERROR",
                        "status_code": response.status,
                        "error": error_text
                    }
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            self.results[name] = {
                "status": "EXCEPTION",
                "error": str(e)
            }

async def test_all_apis():
    """Test all APIs step by step according to project flow"""
    
    print("🚀 LOCAL PROJECT API TESTING - STEP BY STEP")
    print("=" * 60)
    
    async with APITester() as tester:
        
        # STEP 1: Phone Number Collection (No API call)
        print("\n📱 STEP 1: Phone Number Collection")
        print("✅ No API call - handled by validation")
        
        # STEP 2: Search Client Data API
        await tester.test_api(
            "SEARCH_CLIENT_DATA_API",
            APIS["SEARCH_CLIENT_DATA_API"],
            {
                "searchCriteria": "CustomerPhone",
                "searchText": "13854156545",
                "bActiveRecords": True,
                "iATSPID": 21,
                "iDTSPID": 1
            },
            expected_fields=["responseCode", "responseJSON"]
        )
        
        # STEP 3: Profile Selection API (reuses Search Client Data)
        print("\n👤 STEP 3: Profile Selection API")
        print("✅ Reuses Search Client Data API - already tested above")
        
        # STEP 4: Rider Verification API
        await tester.test_api(
            "RIDER_VERIFICATION_API", 
            APIS["RIDER_VERIFICATION_API"],
            {
                "riderID": 12345,
                "tspid": 21,
                "programid": 1
            },
            expected_fields=["VerificationSuccess", "message"]
        )
        
        # STEP 4: Get Name API
        await tester.test_api(
            "GET_NAME_API",
            APIS["GET_NAME_API"],
            {
                "riderID": 12345,
                "tspid": 21,
                "programid": 1
            },
            expected_fields=["FirstName", "LastName"]
        )
        
        # STEP 5: Geocode API (Pickup)
        await tester.test_api(
            "ITC_GEOCODE_API_PICKUP",
            APIS["ITC_GEOCODE_API"],
            {
                "address": "123 Main St, Gaithersburg, MD 20878"
            },
            expected_fields=["results"]
        )
        
        # STEP 6: Bounds Check API (Pickup) - uses All Affiliate Details
        await tester.test_api(
            "ALL_AFFILIATE_DETAILS_API",
            APIS["ALL_AFFILIATE_DETAILS_API"],
            {
                "iaffiliateid": 21
            },
            expected_fields=["Table1"]
        )
        
        # STEP 7: Geocode API (Dropoff)
        await tester.test_api(
            "ITC_GEOCODE_API_DROPOFF",
            APIS["ITC_GEOCODE_API"],
            {
                "address": "456 Oak Ave, Rockville, MD 20850"
            },
            expected_fields=["results"]
        )
        
        # STEP 8: Bounds Check API (Dropoff) - reuses All Affiliate Details
        print("\n📍 STEP 8: Bounds Check API (Dropoff)")
        print("✅ Reuses All Affiliate Details API - already tested above")
        
        # STEP 9: Time Selection (No API call)
        print("\n⏰ STEP 9: Time Selection")
        print("✅ No API call - handled by validation")
        
        # STEP 10: Payment IDs API
        await tester.test_api(
            "GET_PAYMENT_TPYE_AFFILIATE_API",
            APIS["GET_PAYMENT_TPYE_AFFILIATE_API"],
            {
                "iaffiliateid": 21
            }
        )
        
        # STEP 11: Copay IDs API (reuses Payment API)
        print("\n💰 STEP 11: Copay IDs API")
        print("✅ Reuses Payment API - already tested above")
        
        # STEP 12: Special Requirements (No API call)
        print("\n🎯 STEP 12: Special Requirements")
        print("✅ No API call - handled by validation")
        
        # STEP 13: Trip Summary & Confirmation (No API call)
        print("\n📋 STEP 13: Trip Summary & Confirmation")
        print("✅ No API call - handled by validation")
        
        # STEP 14-15: Payload Collection (No API calls)
        print("\n📦 STEP 14-15: Payload Collection")
        print("✅ No API calls - handled by validation")
        
        # STEP 16: Trip Booking API (CRITICAL)
        await tester.test_api(
            "TRIP_BOOKING_API",
            APIS["TRIP_BOOKING_API"],
            {
                "generalInfo": {
                    "CompleteUserName": "ncs",
                    "CreatedBy": "NCS, ITCurves",
                    "CreatedByAppID": 26,
                    "CreatedUserId": 2256,
                    "RequestAffiliateID": 21,
                    "ReturnDetailID": "",
                    "FamilyID": 1
                },
                "riderInfo": {
                    "ID": 12345,
                    "PhoneNo": "13854156545",
                    "PickupPerson": "John Doe",
                    "DateOfBirth": "01/01/1900",
                    "RiderID": "12345",
                    "RiderPassword": "",
                    "MedicalID": "12345",
                    "ClientAddress": "123 Main St",
                    "ClientCity": "Gaithersburg",
                    "ClientState": "MD",
                    "ClientZip": "20878",
                    "MedicalId": "12345"
                },
                "addressInfo": {
                    "Trips": [
                        {
                            "Details": [
                                {
                                    "StopType": "pickup",
                                    "Name": "John Doe",
                                    "WaitTime": 0,
                                    "addressDetails": {
                                        "Address": "123 Main St",
                                        "Latitude": 39.1438,
                                        "Longitude": -77.2014,
                                        "City": "Gaithersburg",
                                        "State": "MD",
                                        "Zip": "20878"
                                    }
                                }
                            ]
                        }
                    ]
                }
            },
            expected_fields=["responseCode"]
        )
        
        # STEP 17: Fare API
        await tester.test_api(
            "GET_FARE_API",
            APIS["GET_FARE_API"],
            {
                "pickupLat": 39.1438,
                "pickupLng": -77.2014,
                "dropoffLat": 39.1438,
                "dropoffLng": -77.2014,
                "affiliateId": 21
            }
        )
        
        # STEP 18: Existing Trips API
        await tester.test_api(
            "EXISTING_RIDES_API",
            APIS["EXISTING_RIDES_API"],
            {
                "clientId": 12345,
                "affiliateId": 21
            }
        )
        
        # STEP 19: Historic Trips API
        await tester.test_api(
            "GET_HISTORIC_RIDES_API",
            APIS["GET_HISTORIC_RIDES_API"],
            {
                "clientId": 12345,
                "affiliateId": 21
            }
        )
        
        # STEP 20: Trip Stats API
        await tester.test_api(
            "TRIP_STATS_API",
            APIS["TRIP_STATS_API"],
            {
                "clientId": 12345,
                "affiliateId": 21
            }
        )
        
        # STEP 21: All Affiliates API (already tested above)
        print("\n🏢 STEP 21: All Affiliates API")
        print("✅ Already tested above in Step 6")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 API TESTING SUMMARY")
        print("=" * 60)
        
        success_count = 0
        error_count = 0
        
        for api_name, result in tester.results.items():
            status = result["status"]
            if status == "SUCCESS":
                print(f"✅ {api_name}: SUCCESS")
                success_count += 1
            elif status == "NON_JSON":
                print(f"⚠️ {api_name}: NON_JSON_RESPONSE")
                success_count += 1
            else:
                print(f"❌ {api_name}: {status}")
                error_count += 1
        
        print(f"\n📈 Results: {success_count} successful, {error_count} failed")
        print(f"📊 Success Rate: {(success_count/(success_count+error_count)*100):.1f}%")

if __name__ == "__main__":
    asyncio.run(test_all_apis())

