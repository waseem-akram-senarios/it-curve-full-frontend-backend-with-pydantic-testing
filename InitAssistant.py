#!/usr/bin/env python3
"""
InitAssistant.py - Clean conversation history management for context transfer

This class provides a centralized, thread-safe way to manage conversation history
and generate context for transfers without the mess of passing instances around.

Key Features:
- Thread-safe conversation storage per call_sid
- Simple setter/getter interface
- Clean context generation using OpenAI
- No complex instance passing between classes
"""

import threading
import json
import openai
from datetime import datetime
from typing import Dict, List, Optional, Any
from logging_config import get_logger

logger = get_logger(__name__)

class InitAssistant:
    """
    Centralized conversation history manager for clean context transfer.
    
    This class stores conversation history per call_sid and provides
    clean methods to set transcriptions from main.py and get context
    from helper_functions.py without messy instance passing.
    """
    
    # Class-level storage for all conversations (thread-safe)
    _conversations: Dict[str, List[Dict]] = {}
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize the InitAssistant"""
        pass
    
    @classmethod
    def set_transcription(cls, call_sid: str, speaker: str, transcription: str, timestamp: str = None) -> None:
        """
        Set/add a transcription entry for a specific call.
        Called from main.py when new messages arrive.
        
        Args:
            call_sid: Unique call identifier
            speaker: 'Agent' or 'User'
            transcription: The actual message text
            timestamp: Optional timestamp (will generate if not provided)
        """
        if not call_sid or not speaker or not transcription:
            logger.warning(f"⚠️ Invalid transcription data: call_sid={call_sid}, speaker={speaker}, transcription={bool(transcription)}")
            return
            
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message_data = {
            'speaker': speaker,
            'transcription': transcription.strip(),
            'timestamp': timestamp
        }
        
        with cls._lock:
            if call_sid not in cls._conversations:
                cls._conversations[call_sid] = []
            
            cls._conversations[call_sid].append(message_data)
            logger.info(f"📝 Added {speaker} message to call {call_sid}: {transcription[:50]}...")
    
    @classmethod
    def get_conversation_history(cls, call_sid: str) -> List[Dict]:
        """
        Get the complete conversation history for a call.
        Called from helper_functions.py when context is needed.
        
        Args:
            call_sid: Unique call identifier
            
        Returns:
            List of conversation messages in the format:
            [{'speaker': 'Agent', 'transcription': '...', 'timestamp': '...'}, ...]
        """
        with cls._lock:
            history = cls._conversations.get(call_sid, [])
            logger.info(f"📖 Retrieved {len(history)} messages for call {call_sid}")
            return history.copy()  # Return a copy to prevent external modification
    
    @classmethod
    def get_context_for_transfer(cls, call_sid: str, client: Any = None) -> Dict[str, str]:
        """
        Generate context data for transfer using OpenAI.
        This is the main method called from helper_functions.py transfer_call().
        
        Args:
            call_sid: Unique call identifier
            client: Optional OpenAI client (will create if not provided)
            
        Returns:
            Dictionary with context data:
            {
                'ContextCallTitle': 'Generated title',
                'ContextCallSummary': 'Generated summary', 
                'ContextCallDetailHtml': 'HTML conversation history',
                'ContextCallDetailJson': 'JSON conversation history'
            }
        """
        logger.info(f"🔄 Generating transfer context for call {call_sid}")
        
        # Get conversation history
        history = cls.get_conversation_history(call_sid)
        
        if not history:
            logger.error(f"❌ No conversation history found for call {call_sid}")
            return {}
        
        try:
            # Generate title and summary in single OpenAI call (more efficient)
            title_and_summary = cls._generate_title_and_summary(history, client)
            context_detail_html = cls._generate_detail_html(history)
            context_detail_json = cls._generate_json_history(call_sid, history)
            
            result = {
                'ContextCallTitle': title_and_summary.get('title', 'Customer Support'),
                'ContextCallSummary': title_and_summary.get('summary', 'Customer contacted support for assistance.'),
                'ContextCallDetailHtml': context_detail_html,
                'ContextCallDetailJson': context_detail_json
            }
            
            logger.info(f"✅ Context generated successfully for call {call_sid}")
            logger.info(f"   - Title: {title_and_summary.get('title', 'N/A')}")
            logger.info(f"   - Summary length: {len(title_and_summary.get('summary', ''))} chars")
            logger.info(f"   - Detail length: {len(context_detail_html)} chars")
            logger.info(f"   - JSON length: {len(str(context_detail_json))} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating context for call {call_sid}: {e}")
            return {}
    
    @classmethod
    def _generate_title_and_summary(cls, history: List[Dict], client: Any = None) -> dict:
        """Generate both title and summary in a single OpenAI call for efficiency"""
        try:
            if not client:
                client = openai.OpenAI()
            
            # Predefined title keywords
            valid_titles = [
                "Customer Support",
                "Return Trip Booking", 
                "Reschedule Trip",
                "Cancel a Ride",
                "Book a Ride",
                "Complaint",
                "Lost and Found"
            ]
            
            # Create conversation text for analysis
            conversation_text = "\n".join([
                f"{msg['speaker']}: {msg['transcription']}" 
                for msg in history
            ])
            
            prompt = f"""Analyze this customer service conversation and provide both a title and summary.

            Conversation:
            {conversation_text}

            1. TITLE: Select the MOST APPROPRIATE title from this exact list:
            {', '.join(valid_titles)}

            Consider:
            - If customer wants to book a new trip: "Book a Ride"
            - If customer wants to book a return trip: "Return Trip Booking"
            - If customer wants to reschedule: "Reschedule Trip"
            - If customer wants to cancel: "Cancel a Ride"
            - If customer has a complaint: "Complaint"
            - If customer lost something: "Lost and Found"
            - If none of the above or general inquiry: "Customer Support"

            2. SUMMARY: Create a brief 2-3 sentence summary focusing on key points, requests, and outcomes.

            Respond in this exact JSON format:
            {{
            "title": "[selected title from list]",
            "summary": "[brief summary]"
            }}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            try:
                result = json.loads(response.choices[0].message.content.strip())
                title = result.get('title', 'Customer Support')
                summary = result.get('summary', 'Customer contacted support for assistance.')
                
                # Validate title is in our list
                if title not in valid_titles:
                    # Try to find a partial match
                    title_lower = title.lower()
                    for valid_title in valid_titles:
                        if any(word in title_lower for word in valid_title.lower().split()):
                            title = valid_title
                            break
                    else:
                        logger.warning(f"Generated title '{title}' not in valid list, using default")
                        title = "Customer Support"
                
                return {'title': title, 'summary': summary}
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, using fallback")
                return {'title': 'Customer Support', 'summary': 'Customer contacted support for assistance.'}
            
        except Exception as e:
            logger.error(f"Error generating title and summary: {e}")
            return {'title': 'Customer Support', 'summary': 'Customer contacted support for assistance.'}
    
    @classmethod
    def _generate_detail_html(cls, history: List[Dict]) -> str:
        """Generate detailed HTML conversation transcript"""
        try:
            html_parts = [
                "<div style='background:#f9f9f9; border:1px solid #ddd; border-radius:8px; padding:15px;'>",
                "<div style='font-weight:bold; color:#333; margin-bottom:10px;'>Conversation Transcript:</div>"
            ]
            
            for msg in history:
                speaker_color = "#2563eb" if msg['speaker'] == 'Agent' else "#059669"
                html_parts.append(
                    f"<div style='margin:8px 0; padding:8px; background:white; border-radius:4px;'>"
                    f"<span style='font-weight:bold; color:{speaker_color};'>{msg['speaker']}:</span> "
                    f"<span style='color:#374151;'>{msg['transcription']}</span>"
                    f"<div style='font-size:11px; color:#6b7280; margin-top:4px;'>{msg['timestamp']}</div>"
                    f"</div>"
                )
            
            html_parts.append("</div>")
            return "".join(html_parts)
            
        except Exception as e:
            logger.error(f"Error generating HTML detail: {e}")
            return "<div>Error generating conversation detail</div>"
    
    @classmethod
    def _generate_json_history(cls, call_sid: str, history: List[Dict]) -> str:
        """Generate structured JSON conversation history"""
        try:
            json_data = {
                "call_metadata": {
                    "call_id": call_sid,
                    "generated_at": datetime.now().isoformat(),
                    "total_messages": len(history),
                    "participants": list(set(msg['speaker'].lower() for msg in history))
                },
                "conversation": [],
                "statistics": {
                    "agent_message_count": 0,
                    "customer_message_count": 0,
                    "total_agent_characters": 0,
                    "total_customer_characters": 0,
                    "conversation_turns": len(history)
                }
            }
            
            for i, msg in enumerate(history, 1):
                role = "agent" if msg['speaker'] == 'Agent' else "customer"
                content = msg['transcription']
                
                json_data["conversation"].append({
                    "sequence": i,
                    "role": role,
                    "content": content,
                    "timestamp": msg['timestamp'],
                    "character_count": len(content)
                })
                
                # Update statistics
                if role == "agent":
                    json_data["statistics"]["agent_message_count"] += 1
                    json_data["statistics"]["total_agent_characters"] += len(content)
                else:
                    json_data["statistics"]["customer_message_count"] += 1
                    json_data["statistics"]["total_customer_characters"] += len(content)
            
            return json_data
            
        except Exception as e:
            logger.error(f"Error generating JSON history: {e}")
            return json.dumps({"error": "Failed to generate history", "call_id": call_sid})
    
    @classmethod
    def clear_conversation(cls, call_sid: str) -> None:
        """
        Clear conversation history for a specific call.
        Called when call ends to free memory.
        
        Args:
            call_sid: Unique call identifier
        """
        with cls._lock:
            if call_sid in cls._conversations:
                message_count = len(cls._conversations[call_sid])
                del cls._conversations[call_sid]
                logger.info(f"🧹 Cleared {message_count} messages for call {call_sid}")
    
    @classmethod
    def get_active_calls(cls) -> List[str]:
        """Get list of active call_sids with conversation history"""
        with cls._lock:
            return list(cls._conversations.keys())
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get statistics about stored conversations"""
        with cls._lock:
            total_calls = len(cls._conversations)
            total_messages = sum(len(history) for history in cls._conversations.values())
            
            return {
                "active_calls": total_calls,
                "total_messages": total_messages,
                "call_ids": list(cls._conversations.keys())
            }
