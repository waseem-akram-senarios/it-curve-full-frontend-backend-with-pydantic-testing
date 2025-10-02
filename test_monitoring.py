import asyncio
import json
from monitoring_agent import MonitoringAgent, ConversationAnalysis
from logging_config import get_logger

# Initialize logger
logger = get_logger('test_monitoring')

async def test_monitoring_agent():
    """Test the monitoring agent functionality with sample conversation."""
    logger.info("Testing monitoring agent functionality...")
    
    # Load configuration
    with open('monitoring_config.json', 'r') as f:
        config = json.load(f)
    
    # Create monitoring agent with config
    monitor = MonitoringAgent(confusion_threshold=config['confusion_threshold'])
    
    # Register a callback for confusion detection
    async def on_confusion_detected(analysis: ConversationAnalysis):
        logger.warning("\n========== CONFUSION DETECTED ==========")
        logger.warning(f"Score: {analysis.confidence_score}")
        logger.warning(f"Reason: {analysis.reason}")
        if analysis.recommended_action:
            logger.info(f"Recommended action: {analysis.recommended_action}")
        logger.warning("=======================================\n")
    
    monitor.register_callback(on_confusion_detected)
    
    # Start monitoring
    logger.info("Starting monitoring agent...")
    await monitor.start_monitoring(interval_seconds=config['monitoring_interval_seconds'])
    
    # Test normal conversation flow
    logger.info("\n>>> Testing normal conversation flow...")
    monitor.add_conversation_item("User", "I'd like to book a ride for tomorrow at 3 PM")
    monitor.add_conversation_item("Agent", "I'd be happy to help you book a ride for tomorrow at 3 PM. Where would you like to be picked up from?")
    
    await asyncio.sleep(2)  # Wait for processing
    
    monitor.add_conversation_item("User", "From my home at 123 Main Street")
    monitor.add_conversation_item("Agent", "Great, and what's your destination?")
    
    logger.info("Normal conversation items added. Waiting for analysis...")
    await asyncio.sleep(15)  # Wait for analysis to run
    
    # Test confused conversation flow
    logger.info("\n>>> Testing confused conversation flow...")
    monitor.add_conversation_item("User", "I need to go to the airport for my flight to Chicago")
    monitor.add_conversation_item("Agent", "I'm sorry, could you please tell me where you'd like to go?")
    
    await asyncio.sleep(2)
    
    monitor.add_conversation_item("User", "The airport. I just told you.")
    monitor.add_conversation_item("Agent", "I apologize, but I'm not sure which location you're referring to. Could you provide the specific address or name of the destination?")
    
    await asyncio.sleep(2)
    
    monitor.add_conversation_item("User", "JFK Airport!")
    monitor.add_conversation_item("Agent", "I'm still having trouble understanding your destination. Could you please clarify where you'd like to go?")
    
    logger.info("Confusion conversation items added. Waiting for analysis...")
    await asyncio.sleep(15)  # Wait for analysis to run
    
    # Stop monitoring
    logger.info("\nStopping monitoring agent...")
    await monitor.stop_monitoring()
    logger.info("Monitoring agent stopped. Test complete.")

if __name__ == "__main__":
    asyncio.run(test_monitoring_agent())
