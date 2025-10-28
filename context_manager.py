"""
Context Manager for IVR Bot - Handles conversation tracking and context generation for transfers
"""
import json
import os
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from logging_config import get_logger
from timezone_utils import now_eastern, format_eastern_datetime_iso

logger = get_logger('context_manager')

class ConversationTracker:
    """Tracks conversation history for context generation during transfers"""
    
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.conversation_history: List[Dict] = []
        self.start_time = now_eastern()
        
    def add_message(self, role: str, content: str, timestamp: Optional[datetime] = None):
        """
        Add a message to the conversation history
        
        Args:
            role: 'agent' or 'customer'
            content: The message content
            timestamp: Optional timestamp, defaults to now
        """
        if timestamp is None:
            timestamp = now_eastern()
            
        message = {
            'role': role,
            'content': content,
            'timestamp': format_eastern_datetime_iso(timestamp)
        }
        
        self.conversation_history.append(message)
        logger.debug(f"Added {role} message to conversation history: {content[:50]}...")
        
    def get_conversation_duration(self) -> str:
        """Get the duration of the conversation"""
        duration = now_eastern() - self.start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        return f"{minutes}m {seconds}s"
        
    def get_conversation_history(self) -> List[Dict]:
        """Get the full conversation history"""
        return self.conversation_history.copy()

class ContextGenerator:
    """Generates context information for transfer scenarios"""
    
    @staticmethod
    def generate_context_call_title(conversation_history: List[Dict], booking_scenario: str = "Book Ride") -> str:
        """
        Generate ContextCallTitle based on conversation
        
        Args:
            conversation_history: List of conversation messages
            booking_scenario: Type of booking scenario
            
        Returns:
            str: Context call title
        """
        # Analyze conversation to determine the main intent
        if not conversation_history:
            return booking_scenario
            
        # Look for specific intents in the conversation
        intents = []
        for message in conversation_history:
            if message['role'] == 'customer':
                content = message['content'].lower()
                if 'book' in content and 'ride' in content:
                    intents.append('Book Ride')
                elif 'cancel' in content:
                    intents.append('Cancel Trip')
                elif 'reschedule' in content:
                    intents.append('Reschedule Trip')
                elif 'return' in content and 'trip' in content:
                    intents.append('Return Trip Booking')
                elif 'help' in content or 'support' in content:
                    intents.append('Customer Support')
                    
        # Return the most specific intent or default
        if intents:
            return intents[-1]  # Return the last (most recent) intent
        return booking_scenario
    
    @staticmethod
    def generate_context_call_summary(conversation_history: List[Dict], booking_info: Optional[Dict] = None) -> str:
        """
        Generate ContextCallSummary with HTML formatting
        
        Args:
            conversation_history: List of conversation messages
            booking_info: Optional booking information collected
            
        Returns:
            str: HTML formatted summary
        """
        if not conversation_history:
            return "<h3 style='margin-top:20px; color:#444;'>Summary:</h3><p>No conversation data available.</p>"
            
        # Analyze the conversation for key points
        summary_points = []
        
        # Check for booking attempts
        booking_attempted = False
        pickup_mentioned = False
        dropoff_mentioned = False
        issues_encountered = []
        
        for message in conversation_history:
            content = message['content'].lower()
            if message['role'] == 'customer':
                if 'book' in content and ('ride' in content or 'trip' in content):
                    booking_attempted = True
                if any(addr_word in content for addr_word in ['address', 'street', 'road', 'avenue', 'boulevard']):
                    if not pickup_mentioned:
                        pickup_mentioned = True
                    else:
                        dropoff_mentioned = True
            elif message['role'] == 'agent':
                if 'could not be verified' in content or 'incomplete' in content:
                    issues_encountered.append('Address verification issue')
                if 'error' in content.lower():
                    issues_encountered.append('System error encountered')
        
        # Build summary
        if booking_attempted:
            summary_points.append("The customer requested a ride booking.")
            
        if pickup_mentioned:
            summary_points.append("Pickup address was discussed.")
            
        if dropoff_mentioned:
            summary_points.append("Drop-off address was provided.")
            
        if issues_encountered:
            for issue in set(issues_encountered):  # Remove duplicates
                summary_points.append(f"{issue} was encountered.")
                
        # Check conversation outcome
        last_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        conversation_ended = False
        for message in last_messages:
            if message['role'] == 'customer':
                content = message['content'].lower()
                if any(end_phrase in content for end_phrase in ['no thank you', 'that\'s all', 'goodbye', 'bye']):
                    conversation_ended = True
                    summary_points.append("The customer decided not to proceed further and ended the conversation.")
                    break
                    
        if not conversation_ended and booking_attempted:
            summary_points.append("The conversation is ongoing.")
            
        summary_text = " ".join(summary_points) if summary_points else "Customer contacted support for assistance."
        
        return f"<h3 style='margin-top:20px; color:#444;'>Summary:</h3><p>{summary_text}</p>"
    
    @staticmethod
    def generate_context_call_detail(conversation_history: List[Dict]) -> str:
        """
        Generate ContextCallDetail with full conversation in HTML format
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            str: HTML formatted conversation detail
        """
        if not conversation_history:
            return "<div style='background:#f9f9f9; border:1px solid #ddd; border-radius:8px; padding:15px;'><p>No conversation details available.</p></div>"
            
        html_parts = ["<div style='background:#f9f9f9; border:1px solid #ddd; border-radius:8px; padding:15px;'>"]
        
        for message in conversation_history:
            role = message['role']
            content = message['content']
            
            # Escape single quotes for HTML
            content_escaped = content.replace("'", "\\'")
            
            if role == 'agent':
                html_parts.append(f"<div style='margin-bottom:15px;'><strong style='color:#2a5298;'>Agent:</strong><p>{content_escaped}</p></div>")
            elif role == 'customer':
                html_parts.append(f"<div style='margin-bottom:15px;'><strong style='color:#1d8348;'>Customer:</strong><p>{content_escaped}</p></div>")
                
        html_parts.append("</div>")
        
        return "".join(html_parts)

class ContextTransferManager:
    """Manages context transfer to external API"""
    
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.context_api_url = os.getenv("CONTEXT_TRANSFER_API")
        
    async def send_context_to_api(self, context_data: Dict) -> bool:
        """
        Send context data to the CONTEXT_TRANSFER_API
        
        Args:
            context_data: Dictionary containing context information
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.context_api_url:
            logger.warning("CONTEXT_TRANSFER_API not configured in environment")
            return False
            
        try:
            logger.info(f"Sending context data to API: {self.context_api_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.context_api_url, 
                    json=context_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        logger.info("Context data successfully sent to transfer API")
                        return True
                    else:
                        logger.error(f"Context transfer API returned status {response.status}")
                        response_text = await response.text()
                        logger.error(f"Response: {response_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending context to transfer API: {e}")
            return False

# Global conversation trackers for active calls
_conversation_trackers: Dict[str, ConversationTracker] = {}

def get_conversation_tracker(call_sid: str) -> ConversationTracker:
    """Get or create a conversation tracker for a call"""
    if call_sid not in _conversation_trackers:
        _conversation_trackers[call_sid] = ConversationTracker(call_sid)
        logger.info(f"Created new conversation tracker for call {call_sid}")
    return _conversation_trackers[call_sid]

def cleanup_conversation_tracker(call_sid: str):
    """Clean up conversation tracker for a completed call"""
    if call_sid in _conversation_trackers:
        del _conversation_trackers[call_sid]
        logger.info(f"Cleaned up conversation tracker for call {call_sid}")

def add_conversation_message(call_sid: str, role: str, content: str):
    """Convenience function to add a message to conversation history"""
    tracker = get_conversation_tracker(call_sid)
    tracker.add_message(role, content)
