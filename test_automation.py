#!/usr/bin/env python3
"""
Automated Test Suite for Voice Agent Bot
Tests all critical functionality after merge
"""
import requests
import time
import sys

def test_system():
    print("=" * 60)
    print("🧪 AUTOMATED VOICE AGENT TEST SUITE")
    print("=" * 60)
    print()
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0
    }
    
    # Test 1: Backend Health
    print("Test 1: Backend Health Check")
    print("-" * 60)
    try:
        response = requests.get("http://localhost:11000", timeout=5)
        if response.status_code == 200 or response.text == "OK":
            print("✅ PASS: Backend is responding")
            results["passed"] += 1
        else:
            print(f"❌ FAIL: Backend returned {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        print(f"❌ FAIL: Backend not responding - {e}")
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # Test 2: Frontend Health
    print("Test 2: Frontend Health Check")
    print("-" * 60)
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200 and "Chat with Assistant" in response.text:
            print("✅ PASS: Frontend is responding")
            results["passed"] += 1
        else:
            print(f"❌ FAIL: Frontend returned unexpected content")
            results["failed"] += 1
    except Exception as e:
        print(f"❌ FAIL: Frontend not responding - {e}")
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # Test 3: Git Status
    print("Test 3: Git Status Check")
    print("-" * 60)
    import subprocess
    try:
        result = subprocess.run(
            ["cd /home/senarios/VoiceAgent8.1/IT_Curves_Bot && git status -uno"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        if "up to date" in result.stdout.lower() or "monitor-agent" in result.stdout:
            print("✅ PASS: Git is up to date with monitor-agent branch")
            results["passed"] += 1
        else:
            print(f"❌ FAIL: Git status unclear")
            results["failed"] += 1
    except Exception as e:
        print(f"❌ FAIL: Git check failed - {e}")
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # Test 4: Port Check
    print("Test 4: Port Availability Check")
    print("-" * 60)
    import socket
    ports_to_check = [
        (11000, "Backend"),
        (3000, "Frontend")
    ]
    all_ports_ok = True
    for port, name in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                print(f"✅ Port {port} ({name}) is open")
            else:
                print(f"❌ Port {port} ({name}) is not accessible")
                all_ports_ok = False
        except Exception as e:
            print(f"❌ Port {port} ({name}) check failed: {e}")
            all_ports_ok = False
    
    if all_ports_ok:
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # Test 5: File Existence Check
    print("Test 5: Critical Files Check")
    print("-" * 60)
    import os
    critical_files = [
        "IT_Curves_Bot/main.py",
        "IT_Curves_Bot/helper_functions.py",
        "IT_Curves_Bot/models.py",
        "IT_Curves_Bot/side_functions.py",
        "IT_Curves_Bot/context_manager.py"
    ]
    all_files_exist = True
    for file_path in critical_files:
        full_path = os.path.join("/home/senarios/VoiceAgent8.1", file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} NOT FOUND")
            all_files_exist = False
    
    if all_files_exist:
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["total"] += 1
    print()
    
    # Final Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    print()
    
    if results["failed"] == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ System is ready for end-to-end testing")
        print()
        print("Next Steps:")
        print("1. Open http://localhost:3000 in your browser")
        print("2. Follow the test scenario in END_TO_END_TEST.md")
        return 0
    else:
        print("⚠️ SOME TESTS FAILED")
        print("Review the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(test_system())

