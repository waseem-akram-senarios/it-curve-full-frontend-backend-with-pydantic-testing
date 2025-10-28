import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from timezone_utils import now_eastern
from pydantic import BaseModel, Field
from logging_config import get_logger

load_dotenv()

# Initialize logger
logger = get_logger('monitoring_agent')

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ConversationItem(BaseModel):
    """Represents a single utterance in the conversation."""
    speaker: str
    text: str
    timestamp: datetime

class ConversationAnalysis(BaseModel):
    """Result of analyzing a conversation segment."""
    is_confused: bool = Field(..., description="Whether the agent appears to be confused or misunderstanding the user")
    confidence_score: float = Field(..., description="Confidence score from 0.0-1.0 on how well the conversation is going")
    reason: str = Field(..., description="Reasoning for the confusion assessment")
    recommended_action: Optional[str] = Field(None, description="Recommended action to resolve the confusion")

class MonitoringAgent:
    """Agent that monitors conversations and detects when the main agent is confused."""
    
    def __init__(self, confusion_threshold: float = 0.6):
        """Initialize the monitoring agent.
        
        Args:
            confusion_threshold: Threshold above which to consider the agent confused (0.0-1.0)
        """
        self.conversation_history: List[ConversationItem] = []
        self.confusion_threshold = confusion_threshold
        self.is_monitoring = False
        self._monitor_task = None
        self.callbacks = []
        
    def register_callback(self, callback):
        """Register a callback function to be called when confusion is detected."""
        self.callbacks.append(callback)
        
    def add_conversation_item(self, speaker: str, text: str):
        """Add a new conversation item to the history.
        
        Args:
            speaker: Who spoke ('User' or 'Agent')
            text: The text content of what was said
        """
        item = ConversationItem(
            speaker=speaker,
            text=text,
            timestamp=now_eastern()
        )
        self.conversation_history.append(item)
        logger.debug(f"Added conversation item: {speaker} said: {text}")
        
    async def analyze_conversation(self, window_size: int = 4) -> ConversationAnalysis:
        """Analyze the recent conversation to detect confusion.
        
        Args:
            window_size: Number of recent conversation items to analyze
            
        Returns:
            Analysis result containing confusion assessment
        """
        if len(self.conversation_history) < window_size:
            # Not enough conversation history to analyze
            return ConversationAnalysis(
                is_confused=False, 
                confidence_score=1.0,
                reason="Insufficient conversation history"
            )
            
        # Get the most recent conversation items
        recent_items = self.conversation_history[-window_size:]
        
        # Format conversation for analysis
        conversation_text = "\n".join([
            f"{item.speaker}: {item.text}" for item in recent_items
        ])
        
        # Prepare the prompt for the LLM
        prompt = f"""
        You are analyzing a conversation between a user and an AI voice agent.
        Your task is to determine if the agent is confused or having trouble understanding the user.
        
        Here is the recent conversation:
        
        {conversation_text}
        
        Analyze whether the agent appears to be:
        1. Repeatedly asking for the same information
        2. Misinterpreting what the user is saying
        3. Providing irrelevant responses
        4. Apologizing for not understanding
        5. Asking for clarification multiple times
        
        Return your analysis in JSON format with these fields:
        - is_confused: boolean indicating whether the agent seems confused
        - confidence_score: number between 0.0 and 1.0 indicating how confident you are in your assessment
        - reason: brief explanation of why you think the agent is confused or not
        - recommended_action: suggested action to resolve the confusion (only if confused)
        
        Only include the JSON in your response, no other text.
        """
        
        try:
            # Send to LLM for analysis
            response = await openai_client.chat.completions.create(
                model="gpt-4-turbo",  # Use an appropriate model
                messages=[
                    {"role": "system", "content": "You analyze conversations to detect if an AI agent is confused."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            logger.debug(f"LLM analysis: {analysis_text}")
            
            try:
                # Convert the analysis to a Pydantic model
                import json
                analysis_dict = json.loads(analysis_text)
                analysis = ConversationAnalysis(**analysis_dict)
                return analysis
            except Exception as e:
                logger.error(f"Error parsing analysis response: {e}")
                return ConversationAnalysis(
                    is_confused=False, 
                    confidence_score=1.0,
                    reason=f"Error parsing analysis: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Error during conversation analysis: {e}")
            return ConversationAnalysis(
                is_confused=False, 
                confidence_score=1.0,
                reason=f"Error during analysis: {str(e)}"
            )
    
    async def _monitor_loop(self, interval_seconds: float = 5.0):
        """Background task to periodically analyze the conversation.
        
        Args:
            interval_seconds: How often to analyze the conversation
        """
        logger.info("Starting monitoring loop")
        while self.is_monitoring:
            try:
                analysis = await self.analyze_conversation()
                
                # If the confidence score is below the threshold, trigger the callbacks
                if analysis.is_confused and analysis.confidence_score >= self.confusion_threshold:
                    logger.warning(f"Confusion detected! Score: {analysis.confidence_score}, Reason: {analysis.reason}")
                    for callback in self.callbacks:
                        await callback(analysis)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                
            # Wait before the next analysis
            await asyncio.sleep(interval_seconds)
        
        logger.info("Monitoring loop stopped")
    
    async def start_monitoring(self, interval_seconds: float = 5.0):
        """Start the background monitoring task.
        
        Args:
            interval_seconds: How often to analyze the conversation
        """
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
            
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info(f"Started monitoring with interval of {interval_seconds}s")
        
    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        if not self.is_monitoring:
            logger.warning("Monitoring not active")
            return
            
        self.is_monitoring = False
        if self._monitor_task:
            await self._monitor_task
            self._monitor_task = None
        logger.info("Stopped monitoring")
        
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Cleared conversation history")


# Example usage
async def main():
    # Create a monitoring agent
    monitor = MonitoringAgent(confusion_threshold=0.7)
    
    # Register a callback for when confusion is detected
    async def on_confusion_detected(analysis):
        logger.warning(f"ALERT: Agent confused! Score: {analysis.confidence_score}")
        logger.warning(f"Reason: {analysis.reason}")
        if analysis.recommended_action:
            logger.info(f"Recommended action: {analysis.recommended_action}")
    
    monitor.register_callback(on_confusion_detected)
    
    # Start monitoring in the background
    await monitor.start_monitoring(interval_seconds=10)
    
    # Simulate a conversation
    monitor.add_conversation_item("User", "I need to book a ride for tomorrow")
    monitor.add_conversation_item("Agent", "Sure, I can help you book a ride. What time would you like to be picked up?")
    
    await asyncio.sleep(5)
    
    monitor.add_conversation_item("User", "Around 3 PM to go to the airport")
    monitor.add_conversation_item("Agent", "I'm sorry, can you clarify if you need a pickup at 3 PM?")
    
    await asyncio.sleep(5)
    
    monitor.add_conversation_item("User", "Yes, at 3 PM for the airport")
    monitor.add_conversation_item("Agent", "I'm still not clear on what time you need. Could you please repeat that?")
    
    # This should trigger the confusion detection
    
    await asyncio.sleep(15)  # Wait for analysis to run
    
    # Stop monitoring
    await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
