#!/usr/bin/env python3
"""
COMPREHENSIVE STEP-BY-STEP VERIFICATION OF ALL PYDANTIC IMPLEMENTATIONS
"""

import asyncio
import sys
import os
import subprocess
import time

# Add the VoiceAgent3/IT_Curves_Bot directory to the path
sys.path.append('/home/senarios/VoiceAgent5withFeNew/VoiceAgent3/IT_Curves_Bot')

def run_test_file(test_file):
    """Run a test file and return success status"""
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Test timed out"
    except Exception as e:
        return False, "", str(e)

async def comprehensive_verification():
    """Comprehensive step-by-step verification of all Pydantic implementations"""
    
    print("🔍 COMPREHENSIVE PYDANTIC VERIFICATION - STEP BY STEP")
    print("=" * 80)
    
    # Test files and their descriptions
    test_files = [
        ("verify_step_1_phone.py", "STEP 1: Phone Number Validation"),
        ("verify_step_2_search.py", "STEP 2: Client Search API"),
        ("verify_step_3_profile.py", "STEP 3: Profile Selection"),
        ("verify_step_4_get_name.py", "STEP 4: Get Name API"),
        ("verify_step_7_dropoff_geocode.py", "STEP 7: Dropoff Geocoding"),
        ("verify_step_8_dropoff_bounds.py", "STEP 8: Dropoff Bounds Check"),
        ("verify_step_10_payment.py", "STEP 10: Payment IDs"),
        ("verify_step_11_copay.py", "STEP 11: Copay IDs"),
        ("verify_step_17_fare.py", "STEP 17: Fare Calculation"),
        ("verify_step_18_existing_trips.py", "STEP 18: Existing Trips"),
        ("verify_step_19_historic_trips.py", "STEP 19: Historic Trips"),
        ("verify_step_20_trip_stats.py", "STEP 20: Trip Statistics"),
        ("verify_step_21_affiliates.py", "STEP 21: All Affiliates"),
    ]
    
    # Existing test files
    existing_tests = [
        ("test_rider_verification.py", "Rider Verification"),
        ("test_geocode_response.py", "Geocoding Response"),
        ("test_bounds_check_response.py", "Bounds Check Response"),
    ]
    
    results = []
    total_tests = len(test_files) + len(existing_tests)
    
    print(f"\n📊 Running {total_tests} verification tests...")
    print("-" * 80)
    
    # Run new test files
    for test_file, description in test_files:
        print(f"\n🧪 {description}")
        print(f"📁 File: {test_file}")
        
        if os.path.exists(test_file):
            success, stdout, stderr = run_test_file(test_file)
            if success:
                print(f"✅ PASSED - {description}")
                results.append(("✅", description, "PASSED"))
            else:
                print(f"❌ FAILED - {description}")
                print(f"📄 Output: {stdout[:200]}...")
                if stderr:
                    print(f"⚠️ Error: {stderr[:200]}...")
                results.append(("❌", description, "FAILED"))
        else:
            print(f"⚠️ FILE NOT FOUND - {test_file}")
            results.append(("⚠️", description, "FILE NOT FOUND"))
    
    # Run existing test files
    for test_file, description in existing_tests:
        print(f"\n🧪 {description}")
        print(f"📁 File: {test_file}")
        
        if os.path.exists(test_file):
            success, stdout, stderr = run_test_file(test_file)
            if success:
                print(f"✅ PASSED - {description}")
                results.append(("✅", description, "PASSED"))
            else:
                print(f"❌ FAILED - {description}")
                print(f"📄 Output: {stdout[:200]}...")
                if stderr:
                    print(f"⚠️ Error: {stderr[:200]}...")
                results.append(("❌", description, "FAILED"))
        else:
            print(f"⚠️ FILE NOT FOUND - {test_file}")
            results.append(("⚠️", description, "FILE NOT FOUND"))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for status, _, _ in results if status == "✅")
    failed = sum(1 for status, _, _ in results if status == "❌")
    missing = sum(1 for status, _, _ in results if status == "⚠️")
    
    print(f"\n📈 Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️ Missing: {missing}")
    print(f"   📊 Total: {total_tests}")
    print(f"   🎯 Success Rate: {(passed/total_tests)*100:.1f}%")
    
    print(f"\n📋 Detailed Results:")
    for status, description, result in results:
        print(f"   {status} {description}: {result}")
    
    # Check project services
    print(f"\n🔍 PROJECT SERVICES STATUS:")
    print("-" * 40)
    
    # Check if services are running
    try:
        # Check validation API
        import requests
        try:
            response = requests.get("http://localhost:8000/docs", timeout=5)
            if response.status_code == 200:
                print("✅ Validation API: Running (port 8000)")
            else:
                print("❌ Validation API: Not responding")
        except:
            print("❌ Validation API: Not running")
        
        # Check voice agent (port 11000)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 11000))
            if result == 0:
                print("✅ Voice Agent: Running (port 11000)")
            else:
                print("❌ Voice Agent: Not running")
            sock.close()
        except:
            print("❌ Voice Agent: Not running")
        
        # Check frontend (port 3000)
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend: Running (port 3000)")
            else:
                print("❌ Frontend: Not responding")
        except:
            print("❌ Frontend: Not running")
            
    except ImportError:
        print("⚠️ Cannot check services (requests not available)")
    
    # Final assessment
    print(f"\n🎯 FINAL ASSESSMENT:")
    print("-" * 40)
    
    if passed >= total_tests * 0.9:  # 90% success rate
        print("🎉 EXCELLENT - Pydantic implementation is comprehensive and working!")
        print("✅ Ready for production deployment")
    elif passed >= total_tests * 0.8:  # 80% success rate
        print("✅ GOOD - Most implementations are working correctly")
        print("⚠️ Some minor issues to address")
    elif passed >= total_tests * 0.7:  # 70% success rate
        print("⚠️ FAIR - Several implementations need attention")
        print("🔧 Review failed tests and fix issues")
    else:
        print("❌ POOR - Significant issues with implementation")
        print("🚨 Major review and fixes required")
    
    print(f"\n📁 All test files and results are available for review.")
    print(f"🎯 Pydantic verification process completed!")

if __name__ == "__main__":
    asyncio.run(comprehensive_verification())


