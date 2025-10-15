#!/bin/bash
# LOCAL PROJECT API TESTING - CURL VERSION
# Test APIs step by step using curl commands

echo "🚀 LOCAL PROJECT API TESTING - CURL VERSION"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to test API with curl
test_api() {
    local name="$1"
    local url="$2"
    local payload="$3"
    
    echo -e "\n${BLUE}🧪 Testing $name${NC}"
    echo -e "${BLUE}📍 URL: $url${NC}"
    echo -e "${BLUE}📦 Payload: $payload${NC}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$url")
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✅ Success! Status: $http_code${NC}"
        echo -e "${GREEN}Response: $response_body${NC}"
    else
        echo -e "${RED}❌ Error! Status: $http_code${NC}"
        echo -e "${RED}Response: $response_body${NC}"
    fi
}

# STEP 1: Phone Number Collection (No API call)
echo -e "\n${YELLOW}📱 STEP 1: Phone Number Collection${NC}"
echo -e "${GREEN}✅ No API call - handled by validation${NC}"

# STEP 2: Search Client Data API
test_api "SEARCH_CLIENT_DATA_API" \
    "https://tgistagingreservationapi.itcurves.us/SearchClientData" \
    '{
        "searchCriteria": "CustomerPhone",
        "searchText": "13854156545",
        "bActiveRecords": true,
        "iATSPID": 21,
        "iDTSPID": 1
    }'

# STEP 3: Profile Selection API (reuses Search Client Data)
echo -e "\n${YELLOW}👤 STEP 3: Profile Selection API${NC}"
echo -e "${GREEN}✅ Reuses Search Client Data API - already tested above${NC}"

# STEP 4: Rider Verification API
test_api "RIDER_VERIFICATION_API" \
    "https://siveaasapi.itcurves.us/api/common/CheckRiderEligibility" \
    '{
        "riderID": 12345,
        "tspid": 21,
        "programid": 1
    }'

# STEP 4: Get Name API
test_api "GET_NAME_API" \
    "https://siveaasapi.itcurves.us/api/common/GetRiderProfile" \
    '{
        "riderID": 12345,
        "tspid": 21,
        "programid": 1
    }'

# STEP 5: Geocode API (Pickup)
test_api "ITC_GEOCODE_API_PICKUP" \
    "https://itcmap.itcurves.us/api/Map/geocode" \
    '{
        "address": "123 Main St, Gaithersburg, MD 20878"
    }'

# STEP 6: Bounds Check API (Pickup) - YOUR REQUESTED API
echo -e "\n${YELLOW}📍 STEP 6: Bounds Check API (Pickup) - YOUR REQUESTED API${NC}"
test_api "ALL_AFFILIATE_DETAILS_API" \
    "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetAffiliateBasedDetailForIvrAi" \
    '{
        "iaffiliateid": 21
    }'

# STEP 7: Geocode API (Dropoff)
test_api "ITC_GEOCODE_API_DROPOFF" \
    "https://itcmap.itcurves.us/api/Map/geocode" \
    '{
        "address": "456 Oak Ave, Rockville, MD 20850"
    }'

# STEP 8: Bounds Check API (Dropoff) - reuses All Affiliate Details
echo -e "\n${YELLOW}📍 STEP 8: Bounds Check API (Dropoff)${NC}"
echo -e "${GREEN}✅ Reuses All Affiliate Details API - already tested above${NC}"

# STEP 9: Time Selection (No API call)
echo -e "\n${YELLOW}⏰ STEP 9: Time Selection${NC}"
echo -e "${GREEN}✅ No API call - handled by validation${NC}"

# STEP 10: Payment IDs API
test_api "GET_PAYMENT_TPYE_AFFILIATE_API" \
    "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetPaymentTypebyAffiliateID" \
    '{
        "iaffiliateid": 21
    }'

# STEP 11: Copay IDs API (reuses Payment API)
echo -e "\n${YELLOW}💰 STEP 11: Copay IDs API${NC}"
echo -e "${GREEN}✅ Reuses Payment API - already tested above${NC}"

# STEP 12: Special Requirements (No API call)
echo -e "\n${YELLOW}🎯 STEP 12: Special Requirements${NC}"
echo -e "${GREEN}✅ No API call - handled by validation${NC}"

# STEP 13: Trip Summary & Confirmation (No API call)
echo -e "\n${YELLOW}📋 STEP 13: Trip Summary & Confirmation${NC}"
echo -e "${GREEN}✅ No API call - handled by validation${NC}"

# STEP 14-15: Payload Collection (No API calls)
echo -e "\n${YELLOW}📦 STEP 14-15: Payload Collection${NC}"
echo -e "${GREEN}✅ No API calls - handled by validation${NC}"

# STEP 16: Trip Booking API (CRITICAL)
echo -e "\n${YELLOW}🚗 STEP 16: Trip Booking API (CRITICAL)${NC}"
test_api "TRIP_BOOKING_API" \
    "https://tgistagingreservationapi.itcurves.us/BookParatransitTrip" \
    '{
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
    }'

# STEP 17: Fare API
test_api "GET_FARE_API" \
    "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetFareEstimate" \
    '{
        "pickupLat": 39.1438,
        "pickupLng": -77.2014,
        "dropoffLat": 39.1438,
        "dropoffLng": -77.2014,
        "affiliateId": 21
    }'

# STEP 18: Existing Trips API
test_api "EXISTING_RIDES_API" \
    "https://tgistagingreservationapi.itcurves.us/GetExistingRides" \
    '{
        "clientId": 12345,
        "affiliateId": 21
    }'

# STEP 19: Historic Trips API
test_api "GET_HISTORIC_RIDES_API" \
    "https://tgistagingreservationapi.itcurves.us/GetHistoricRides" \
    '{
        "clientId": 12345,
        "affiliateId": 21
    }'

# STEP 20: Trip Stats API
test_api "TRIP_STATS_API" \
    "https://tgistagingreservationapi.itcurves.us/api/ParatransitCT/GetTripStatsDataByClient" \
    '{
        "clientId": 12345,
        "affiliateId": 21
    }'

# STEP 21: All Affiliates API (already tested above)
echo -e "\n${YELLOW}🏢 STEP 21: All Affiliates API${NC}"
echo -e "${GREEN}✅ Already tested above in Step 6${NC}"

echo -e "\n${GREEN}🎉 API TESTING COMPLETED!${NC}"
echo -e "${BLUE}Check the results above for each API endpoint.${NC}"

