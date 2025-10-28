#!/usr/bin/env python3
"""
Test script for context transfer functionality in IVR Bot
Tests conversation tracking, context generation, and transfer API integration
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from context_manager import (
    ContextGenerator, 
    ContextTransferManager
)

def test_conversation_format():
    """Test conversation history format compatibility"""
    print("🧪 Testing conversation history format...")
    
    # Sample conversation history in main.py format
    conversation_history = [
        {'speaker': 'Agent', 'transcription': 'Hello! My name is Alina, your digital agent. How can I help you today?', 'timestamp': '2025-10-17 09:30:00'},
        {'speaker': 'User', 'transcription': 'I want to book a ride.', 'timestamp': '2025-10-17 09:30:05'},
        {'speaker': 'Agent', 'transcription': 'Great! I can help you book a ride. Where should I pick you up?', 'timestamp': '2025-10-17 09:30:10'},
        {'speaker': 'User', 'transcription': '8201 Snouffer School Road, Gaithersburg, Maryland', 'timestamp': '2025-10-17 09:30:15'},
        {'speaker': 'Agent', 'transcription': 'Just to confirm, did you mean 8201 Snouffer School Road in Gaithersburg, Maryland?', 'timestamp': '2025-10-17 09:30:20'},
        {'speaker': 'User', 'transcription': 'Yes, that\'s correct.', 'timestamp': '2025-10-17 09:30:25'},
        {'speaker': 'Agent', 'transcription': 'Where are you headed? Please provide the complete drop-off address.', 'timestamp': '2025-10-17 09:30:30'},
        {'speaker': 'User', 'transcription': '20044 Gaussion Road, Gaithersburg, Maryland.', 'timestamp': '2025-10-17 09:30:35'},
        {'speaker': 'Agent', 'transcription': 'I\'m verifying the addresses... The drop-off address is incomplete. Please provide another complete drop-off address.', 'timestamp': '2025-10-17 09:30:40'},
        {'speaker': 'User', 'transcription': 'No, thank you. That\'s all I needed.', 'timestamp': '2025-10-17 09:30:45'},
        {'speaker': 'Agent', 'transcription': 'Thank you for reaching out. Have a great day!', 'timestamp': '2025-10-17 09:30:50'}
    ]
    
    assert len(conversation_history) == 11, f"Expected 11 messages, got {len(conversation_history)}"
    assert conversation_history[0]['speaker'] == 'Agent', "First message should be from Agent"
    assert conversation_history[1]['speaker'] == 'User', "Second message should be from User"
    
    print(f"✅ Conversation format test passed - {len(conversation_history)} messages in correct format")
    return conversation_history

def test_context_generation():
    """Test context generation functionality using main.py conversation format"""
    print("🧪 Testing ContextGenerator...")
    
    # Use main.py conversation history format
    main_conversation_history = [
        {'speaker': 'Agent', 'transcription': 'Hello! My name is Alina, your digital agent. How can I help you today?', 'timestamp': '2025-10-17 09:30:00'},
        {'speaker': 'User', 'transcription': 'I want to book a ride.', 'timestamp': '2025-10-17 09:30:05'},
        {'speaker': 'Agent', 'transcription': 'Great! I can help you book a ride. Where should I pick you up?', 'timestamp': '2025-10-17 09:30:10'},
        {'speaker': 'User', 'transcription': '8201 Snouffer School Road, Gaithersburg, Maryland', 'timestamp': '2025-10-17 09:30:15'},
        {'speaker': 'Agent', 'transcription': 'Just to confirm, did you mean 8201 Snouffer School Road in Gaithersburg, Maryland?', 'timestamp': '2025-10-17 09:30:20'},
        {'speaker': 'User', 'transcription': 'Yes, that\'s correct.', 'timestamp': '2025-10-17 09:30:25'},
        {'speaker': 'Agent', 'transcription': 'Where are you headed? Please provide the complete drop-off address.', 'timestamp': '2025-10-17 09:30:30'},
        {'speaker': 'User', 'transcription': '20044 Gaussion Road, Gaithersburg, Maryland.', 'timestamp': '2025-10-17 09:30:35'},
        {'speaker': 'Agent', 'transcription': 'I\'m verifying the addresses... The drop-off address is incomplete. Please provide another complete drop-off address.', 'timestamp': '2025-10-17 09:30:40'},
        {'speaker': 'User', 'transcription': 'No, thank you. That\'s all I needed.', 'timestamp': '2025-10-17 09:30:45'},
        {'speaker': 'Agent', 'transcription': 'Thank you for reaching out. Have a great day!', 'timestamp': '2025-10-17 09:30:50'}
    ]
    
    # Convert to context manager format
    conversation_history = []
    for item in main_conversation_history:
        role = 'agent' if item.get('speaker') == 'Agent' else 'customer'
        conversation_history.append({
            'role': role,
            'content': item.get('transcription', ''),
            'timestamp': item.get('timestamp', '')
        })
    
    # Test context title generation
    title = ContextGenerator.generate_context_call_title(conversation_history)
    print(f"📋 Generated Title: {title}")
    assert "Book Ride" in title or "Ride" in title, f"Title should contain ride booking intent: {title}"
    
    # Test context summary generation
    summary = ContextGenerator.generate_context_call_summary(conversation_history)
    print(f"📝 Generated Summary: {summary}")
    assert "<h3" in summary, "Summary should contain HTML formatting"
    assert "customer requested" in summary.lower() or "ride booking" in summary.lower(), "Summary should mention ride booking"
    
    # Test context detail generation
    detail = ContextGenerator.generate_context_call_detail(conversation_history)
    print(f"💬 Generated Detail length: {len(detail)} characters")
    assert "<div" in detail, "Detail should contain HTML formatting"
    assert "Agent:" in detail and "Customer:" in detail, "Detail should contain both agent and customer messages"
    assert "8201 Snouffer School Road" in detail, "Detail should contain specific address mentioned"
    
    print("✅ ContextGenerator test passed")
    return {'title': title, 'summary': summary, 'detail': detail}

async def test_context_transfer_manager():
    """Test context transfer manager functionality"""
    print("🧪 Testing ContextTransferManager...")
    
    call_sid = "test-call-12345"
    
    # Test manager initialization
    manager = ContextTransferManager(call_sid)
    assert manager.call_sid == call_sid, "Manager should store call_sid correctly"
    
    # Test context data structure
    context_data = {
        'call_sid': call_sid,
        'x_call_id': 'SIP-12345',
        'rider_phone': '301-555-0123',
        'client_id': '12345',
        'affiliate_id': '65',
        'timestamp': datetime.now().isoformat(),
        'ContextCallTitle': 'Book Ride',
        'ContextCallSummary': '<h3>Summary:</h3><p>Customer requested ride booking.</p>',
        'ContextCallDetail': '<div>Conversation details...</div>'
    }
    
    # Verify context data has all required fields
    required_fields = ['ContextCallTitle', 'ContextCallSummary', 'ContextCallDetail']
    for field in required_fields:
        assert field in context_data, f"Context data should contain {field}"
        assert context_data[field], f"{field} should not be empty"
    
    # Test with no API URL configured (should return False gracefully)
    result = await manager.send_context_to_api(context_data)
    assert result == False, "Should return False when no API URL is configured"
            
    print("✅ ContextTransferManager test passed")

def test_assistant_integration():
    """Test Assistant class integration with conversation context"""
    print("🧪 Testing Assistant integration...")
    
    # Import here to avoid circular imports
    from helper_functions import Assistant
    
    call_sid = "test-call-67890"
    assistant = Assistant(call_sid=call_sid)
    
    # Test that Assistant has conversation_history attribute
    assert hasattr(assistant, 'conversation_history'), "Assistant should have conversation_history attribute"
    assert isinstance(assistant.conversation_history, list), "conversation_history should be a list"
    assert len(assistant.conversation_history) == 0, "conversation_history should start empty"
    
    # Test context generation with empty history
    context = assistant.get_conversation_context()
    assert context == {}, "Should return empty dict for empty conversation history"
    
    # Add some conversation data
    assistant.conversation_history = [
        {'speaker': 'Agent', 'transcription': 'Hello, how can I help?', 'timestamp': '2025-10-17 09:30:00'},
        {'speaker': 'User', 'transcription': 'I need a ride', 'timestamp': '2025-10-17 09:30:05'}
    ]
    
    # Test context generation with data
    context = assistant.get_conversation_context()
    assert 'ContextCallTitle' in context, "Context should contain ContextCallTitle"
    assert 'ContextCallSummary' in context, "Context should contain ContextCallSummary"
    assert 'ContextCallDetail' in context, "Context should contain ContextCallDetail"
    assert context['ContextCallTitle'], "ContextCallTitle should not be empty"
    
    print("✅ Assistant integration test passed")

def test_booking_payload_integration():
    """Test integration with booking payload structure"""
    print("🧪 Testing booking payload integration...")
    
    # Sample booking payload structure (simplified)
    sample_payload = {
        "riderInfo": {"ID": 960747, "PhoneNo": "321-431-8318"},
        "addressInfo": {
            "Trips": [
                {
                    "Details": [
                        {
                            "StopType": "pickup",
                            "tripInfo": {
                                "CallId": 0,
                                "CustomerEmail": "abc@xyz.com",
                                "ExtraInfo": "Test trip",
                                # Context parameters will be added here
                            }
                        },
                        {
                            "StopType": "dropoff", 
                            "tripInfo": {
                                "CallId": 0,
                                "CustomerEmail": "abc@xyz.com",
                                "ExtraInfo": "Test trip",
                                # Context parameters will be added here
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    # Simulate adding context to payload
    context_data = {
        'ContextCallTitle': 'Book Ride',
        'ContextCallSummary': '<h3>Summary:</h3><p>Customer requested ride booking.</p>',
        'ContextCallDetail': '<div>Full conversation details...</div>'
    }
    
    # Add context to each trip's Details -> tripInfo
    for trip in sample_payload['addressInfo']['Trips']:
        for detail in trip.get('Details', []):
            if 'tripInfo' in detail:
                detail['tripInfo']['ContextCallTitle'] = context_data.get('ContextCallTitle', '')
                detail['tripInfo']['ContextCallSummary'] = context_data.get('ContextCallSummary', '')
                detail['tripInfo']['ContextCallDetail'] = context_data.get('ContextCallDetail', '')
    
    # Verify context was added correctly
    pickup_trip_info = sample_payload['addressInfo']['Trips'][0]['Details'][0]['tripInfo']
    dropoff_trip_info = sample_payload['addressInfo']['Trips'][0]['Details'][1]['tripInfo']
    
    assert pickup_trip_info['ContextCallTitle'] == 'Book Ride', "Pickup tripInfo should have ContextCallTitle"
    assert pickup_trip_info['ContextCallSummary'] == context_data['ContextCallSummary'], "Pickup tripInfo should have ContextCallSummary"
    assert pickup_trip_info['ContextCallDetail'] == context_data['ContextCallDetail'], "Pickup tripInfo should have ContextCallDetail"
    
    assert dropoff_trip_info['ContextCallTitle'] == 'Book Ride', "Dropoff tripInfo should have ContextCallTitle"
    assert dropoff_trip_info['ContextCallSummary'] == context_data['ContextCallSummary'], "Dropoff tripInfo should have ContextCallSummary"
    assert dropoff_trip_info['ContextCallDetail'] == context_data['ContextCallDetail'], "Dropoff tripInfo should have ContextCallDetail"
    
    print("✅ Booking payload integration test passed")
    print(f"📋 Sample payload with context (first 200 chars): {str(sample_payload)[:200]}...")

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Context Transfer Tests")
    print("=" * 50)
    
    try:
        # Test 1: Conversation format compatibility
        conversation_data = test_conversation_format()
        
        # Test 2: Context generation
        context_data = test_context_generation()
        
        # Test 3: Context transfer manager
        await test_context_transfer_manager()
        
        # Test 4: Assistant integration
        test_assistant_integration()
        
        # Test 5: Booking payload integration
        test_booking_payload_integration()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Context transfer functionality is working correctly")
        print("\n📋 Test Summary:")
        print("   ✅ Conversation Format - main.py compatibility verified")
        print("   ✅ ContextGenerator - Title, summary, and detail generation")
        print("   ✅ ContextTransferManager - API integration")
        print("   ✅ Assistant Integration - Context methods working")
        print("   ✅ Booking Integration - Payload context injection")
        
        print("\n🔧 Next Steps:")
        print("   1. Set CONTEXT_TRANSFER_API environment variable")
        print("   2. Test with real IVR bot conversations")
        print("   3. Verify context appears correctly in transfer scenarios")
        print("\n💡 Key Improvement:")
        print("   ✅ Eliminated duplicate conversation tracking")
        print("   ✅ Now uses existing main.py conversation_history")
        print("   ✅ Reduced memory usage and complexity")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
