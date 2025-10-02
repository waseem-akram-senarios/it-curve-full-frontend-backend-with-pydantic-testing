#!/usr/bin/env python3
"""
Test script to verify the logging system is working correctly.
"""

from logging_config import get_logger, set_session_id, create_call_logger, cleanup_call_logger

def test_logging():
    print("Testing logging system...")
    
    # Test 1: Main logger
    print("\n1. Testing main logger...")
    main_logger = get_logger('test_main')
    main_logger.info("This is a test INFO message to main logger")
    main_logger.error("This is a test ERROR message to main logger")
    main_logger.debug("This is a test DEBUG message to main logger")
    
    # Test 2: Module logger
    print("\n2. Testing module logger...")
    module_logger = get_logger('helper_functions')
    module_logger.info("This is a test INFO message from helper_functions")
    module_logger.error("This is a test ERROR message from helper_functions")
    module_logger.debug("This is a test DEBUG message from helper_functions")
    
    # Test 3: Call-specific logger
    print("\n3. Testing call-specific logger...")
    call_id = "test-call-123"
    set_session_id(call_id)
    call_logger = create_call_logger(call_id)
    
    call_logger.info("This is a test INFO message to call logger")
    call_logger.error("This is a test ERROR message to call logger")
    call_logger.debug("This is a test DEBUG message to call logger")
    
    # Test 4: Module logger during active call
    print("\n4. Testing module logger during active call...")
    module_logger_during_call = get_logger('side_functions')
    module_logger_during_call.info("This is a test INFO message from side_functions during call")
    module_logger_during_call.error("This is a test ERROR message from side_functions during call")
    
    # Clean up
    cleanup_call_logger(call_id)
    
    print("\nLogging test completed!")
    print("Check the following files:")
    print("- logs/ivr-bot.log (should contain all INFO+ messages)")
    print("- logs/ivr-bot-error.log (should contain only ERROR messages)")
    print(f"- logs/call_{call_id}_*.log (should contain call-specific messages)")

if __name__ == "__main__":
    test_logging()
