"""
Centralized cost tracking module for IVR Directory Bot.
Tracks costs for agent, supervisor, and web search operations.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional
import threading
from logging_config import get_logger

logger = get_logger('cost_tracker')

@dataclass
class TokenUsage:
    """Represents token usage for a specific operation."""
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = ""
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """Add token usage to current totals."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

@dataclass
class AudioUsage:
    """Represents audio/TTS usage for a specific provider and model."""
    audio_seconds: float = 0.0  # For STT
    characters: int = 0  # For TTS
    provider: str = ""
    model: str = ""
    
    def add_stt_usage(self, audio_seconds: float):
        """Add STT audio usage."""
        self.audio_seconds += audio_seconds
    
    def add_tts_usage(self, characters: int):
        """Add TTS character usage."""
        self.characters += characters

@dataclass
class CostBreakdown:
    """Detailed cost breakdown for all operations."""
    agent_cost: float = 0.0
    supervisor_cost: float = 0.0
    websearch_cost: float = 0.0
    stt_cost: float = 0.0
    tts_cost: float = 0.0
    total_cost: float = 0.0
    
    # Token usage details
    agent_tokens: TokenUsage = field(default_factory=TokenUsage)
    supervisor_tokens: TokenUsage = field(default_factory=TokenUsage)
    websearch_tokens: TokenUsage = field(default_factory=TokenUsage)
    
    # Audio/TTS usage with provider and model tracking
    stt_usage: AudioUsage = field(default_factory=AudioUsage)
    tts_usage: AudioUsage = field(default_factory=AudioUsage)
    
    # Legacy fields for backward compatibility
    stt_audio_seconds: float = 0.0
    tts_characters: int = 0.0

class CostTracker:
    """Centralized cost tracker for all IVR operations."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()
        
        # Model pricing per 1M tokens
        self.model_pricing = {
            "gpt-4.1-mini": {
                "input_cost_per_million": 0.4,
                "output_cost_per_million": 1.6
            },
            "gpt-4o-mini": {
                "input_cost_per_million": 0.15,
                "output_cost_per_million": 0.6
            },
            "gpt-4o": {
                "input_cost_per_million": 2.5,
                "output_cost_per_million": 10.0
            }
        }
        
        # STT and TTS pricing by provider and model (Updated from Deepgram STREAMING pricing table)
        self.audio_pricing = {
            "deepgram": {
                # Nova models (Streaming prices)
                "nova-2": {
                    "stt_cost_per_minute": 0.0058,  # Nova-1 & 2 streaming
                    "tts_cost_per_million_character": 15.0
                },
                "nova-2-phonecall": {
                    "stt_cost_per_minute": 0.0058,  # Nova-1 & 2 streaming
                    "tts_cost_per_million_character": 15.0
                },
                "nova-3": {
                    "stt_cost_per_minute": 0.0077,  # Nova-3 Monolingual streaming
                    "tts_cost_per_million_character": 15.0
                },
                "nova-3-phonecall": {
                    "stt_cost_per_minute": 0.0077,  # Nova-3 Monolingual streaming
                    "tts_cost_per_million_character": 15.0
                },
                "nova-3-multilingual": {
                    "stt_cost_per_minute": 0.0092,  # Nova-3 Multilingual streaming
                    "tts_cost_per_million_character": 15.0
                },
                # Legacy models
                "nova-1": {
                    "stt_cost_per_minute": 0.0058,  # Nova-1 & 2 streaming
                    "tts_cost_per_million_character": 15.0
                },
                # Enhanced models (Streaming prices)
                "enhanced": {
                    "stt_cost_per_minute": 0.0165,  # Enhanced streaming
                    "tts_cost_per_million_character": 15.0
                },
                # Base model (Streaming prices)
                "base": {
                    "stt_cost_per_minute": 0.0145,  # Base streaming
                    "tts_cost_per_million_character": 15.0
                },
                # Add-on features (same for streaming)
                "redaction": {
                    "stt_cost_per_minute": 0.0020,  # Add-on cost
                    "tts_cost_per_million_character": 15.0
                },
                "keyterm-prompting": {
                    "stt_cost_per_minute": 0.0013,  # Add-on cost
                    "tts_cost_per_million_character": 15.0
                },
                "speaker-diarization": {
                    "stt_cost_per_minute": 0.0020,  # Add-on cost
                    "tts_cost_per_million_character": 15.0
                }
            }
        }
        
        # Legacy pricing for backward compatibility
        self.stt_cost_per_minute = 0.0058
        self.tts_cost_per_million_character = 15.0
    
    def reset(self):
        """Reset all cost tracking data."""
        with self._lock:
            self.breakdown = CostBreakdown()
            logger.debug("Cost tracker reset")
    
    def add_agent_usage(self, input_tokens: int, output_tokens: int, model_name: str = "gpt-4.1-mini"):
        """Add agent token usage."""
        with self._lock:
            self.breakdown.agent_tokens.add_usage(input_tokens, output_tokens)
            self.breakdown.agent_tokens.model_name = model_name
            logger.debug(f"Added agent usage: {input_tokens} input, {output_tokens} output tokens ({model_name})")
    
    def add_supervisor_usage(self, input_tokens: int, output_tokens: int, model_name: str = "gpt-4.1-mini"):
        """Add supervisor token usage."""
        with self._lock:
            self.breakdown.supervisor_tokens.add_usage(input_tokens, output_tokens)
            self.breakdown.supervisor_tokens.model_name = model_name
            logger.debug(f"Added supervisor usage: {input_tokens} input, {output_tokens} output tokens ({model_name})")
    
    def add_websearch_usage(self, input_tokens: int, output_tokens: int, model_name: str = "gpt-4o"):
        """Add web search token usage."""
        with self._lock:
            self.breakdown.websearch_tokens.add_usage(input_tokens, output_tokens)
            self.breakdown.websearch_tokens.model_name = model_name
            logger.debug(f"Added websearch usage: {input_tokens} input, {output_tokens} output tokens ({model_name})")
    
    def add_stt_usage(self, audio_seconds: float, provider: str = "deepgram", model: str = "nova-3-phonecall"):
        """Add STT audio usage with provider and model tracking."""
        with self._lock:
            self.breakdown.stt_usage.add_stt_usage(audio_seconds)
            self.breakdown.stt_usage.provider = provider
            self.breakdown.stt_usage.model = model
            # Update legacy field for backward compatibility
            self.breakdown.stt_audio_seconds += audio_seconds
            logger.debug(f"Added STT usage: {audio_seconds} seconds ({provider} {model})")
    
    def add_tts_usage(self, characters: int, provider: str = "deepgram", model: str = "nova-3-phonecall"):
        """Add TTS character usage with provider and model tracking."""
        with self._lock:
            self.breakdown.tts_usage.add_tts_usage(characters)
            self.breakdown.tts_usage.provider = provider
            self.breakdown.tts_usage.model = model
            # Update legacy field for backward compatibility
            self.breakdown.tts_characters += characters
            logger.debug(f"Added TTS usage: {characters} characters ({provider} {model})")
    
    def _calculate_llm_cost(self, tokens: TokenUsage) -> float:
        """Calculate cost for LLM token usage."""
        if not tokens.model_name or tokens.input_tokens == 0 and tokens.output_tokens == 0:
            return 0.0
            
        pricing = self.model_pricing.get(tokens.model_name, self.model_pricing["gpt-4.1-mini"])
        
        input_cost = (tokens.input_tokens / 1000000) * pricing["input_cost_per_million"]
        output_cost = (tokens.output_tokens / 1000000) * pricing["output_cost_per_million"]
        
        return input_cost + output_cost
    
    def calculate_total_costs(self) -> CostBreakdown:
        """Calculate all costs and return detailed breakdown."""
        with self._lock:
            # Calculate LLM costs
            self.breakdown.agent_cost = self._calculate_llm_cost(self.breakdown.agent_tokens)
            self.breakdown.supervisor_cost = self._calculate_llm_cost(self.breakdown.supervisor_tokens)
            self.breakdown.websearch_cost = self._calculate_llm_cost(self.breakdown.websearch_tokens)
            
            # Calculate STT cost using provider-specific pricing
            stt_pricing = self._get_audio_pricing(self.breakdown.stt_usage.provider, self.breakdown.stt_usage.model)
            self.breakdown.stt_cost = (self.breakdown.stt_usage.audio_seconds / 60) * stt_pricing["stt_cost_per_minute"]
            
            # Calculate TTS cost using provider-specific pricing
            tts_pricing = self._get_audio_pricing(self.breakdown.tts_usage.provider, self.breakdown.tts_usage.model)
            self.breakdown.tts_cost = (self.breakdown.tts_usage.characters / 1000000) * tts_pricing["tts_cost_per_million_character"]
            
            # Calculate total cost
            self.breakdown.total_cost = (
                self.breakdown.agent_cost +
                self.breakdown.supervisor_cost +
                self.breakdown.websearch_cost +
                self.breakdown.stt_cost +
                self.breakdown.tts_cost
            )
            
            logger.info(f"Total cost calculated: ${self.breakdown.total_cost:.6f}")
            return self.breakdown
    
    def _get_audio_pricing(self, provider: str, model: str) -> Dict:
        """Get pricing for audio provider and model, with fallback to legacy pricing."""
        if provider in self.audio_pricing and model in self.audio_pricing[provider]:
            return self.audio_pricing[provider][model]
        else:
            # Fallback to legacy pricing
            logger.warning(f"No pricing found for {provider} {model}, using legacy pricing")
            return {
                "stt_cost_per_minute": self.stt_cost_per_minute,
                "tts_cost_per_million_character": self.tts_cost_per_million_character
            }
    
    def get_summary_dict(self) -> Dict:
        """Get cost summary as dictionary for logging/storage."""
        breakdown = self.calculate_total_costs()
        
        return {
            "agent_cost": breakdown.agent_cost,
            "supervisor_cost": breakdown.supervisor_cost,
            "websearch_cost": breakdown.websearch_cost,
            "stt_cost": breakdown.stt_cost,
            "tts_cost": breakdown.tts_cost,
            "total_cost": breakdown.total_cost,
            "token_usage": {
                "agent": {
                    "input_tokens": breakdown.agent_tokens.input_tokens,
                    "output_tokens": breakdown.agent_tokens.output_tokens,
                    "model": breakdown.agent_tokens.model_name
                },
                "supervisor": {
                    "input_tokens": breakdown.supervisor_tokens.input_tokens,
                    "output_tokens": breakdown.supervisor_tokens.output_tokens,
                    "model": breakdown.supervisor_tokens.model_name
                },
                "websearch": {
                    "input_tokens": breakdown.websearch_tokens.input_tokens,
                    "output_tokens": breakdown.websearch_tokens.output_tokens,
                    "model": breakdown.websearch_tokens.model_name
                }
            },
            "audio_usage": {
                "stt_seconds": breakdown.stt_audio_seconds,
                "tts_characters": breakdown.tts_characters
            }
        }

# Per-call cost tracker instances
_call_cost_trackers = {}
_cost_tracker_lock = threading.Lock()
_local = threading.local()

def set_call_context(call_id: str):
    """Set the current call context for this thread."""
    _local.call_id = call_id
    logger.debug(f"Set call context to: {call_id}")

def get_current_call_id() -> Optional[str]:
    """Get the current call ID for this thread."""
    return getattr(_local, 'call_id', None)

def get_cost_tracker(call_id: Optional[str] = None) -> CostTracker:
    """Get the cost tracker instance for a specific call."""
    if call_id is None:
        call_id = get_current_call_id()
    
    if call_id is None:
        # Fallback to a default tracker for backward compatibility
        call_id = "default"
        logger.warning("No call ID set, using default cost tracker")
    
    with _cost_tracker_lock:
        if call_id not in _call_cost_trackers:
            _call_cost_trackers[call_id] = CostTracker()
            logger.debug(f"Created new cost tracker for call: {call_id}")
        return _call_cost_trackers[call_id]

def reset_cost_tracker(call_id: Optional[str] = None):
    """Reset the cost tracker for a specific call."""
    if call_id is None:
        call_id = get_current_call_id()
    
    if call_id is None:
        logger.warning("No call ID provided for reset, using default")
        call_id = "default"
    
    tracker = get_cost_tracker(call_id)
    tracker.reset()
    logger.debug(f"Reset cost tracker for call: {call_id}")

def cleanup_call_tracker(call_id: str):
    """Clean up cost tracker for completed call."""
    with _cost_tracker_lock:
        if call_id in _call_cost_trackers:
            del _call_cost_trackers[call_id]
            logger.debug(f"Cleaned up cost tracker for call: {call_id}")

# Convenience functions that use current call context
def add_agent_usage(input_tokens: int, output_tokens: int, model_name: str = "gpt-4.1-mini"):
    """Add agent token usage to current call's tracker."""
    get_cost_tracker().add_agent_usage(input_tokens, output_tokens, model_name)

def add_supervisor_usage(input_tokens: int, output_tokens: int, model_name: str = "gpt-4.1-mini"):
    """Add supervisor token usage to current call's tracker."""
    get_cost_tracker().add_supervisor_usage(input_tokens, output_tokens, model_name)

def add_websearch_usage(input_tokens: int, output_tokens: int, model_name: str = "gpt-4o"):
    """Add web search token usage to current call's tracker."""
    get_cost_tracker().add_websearch_usage(input_tokens, output_tokens, model_name)

def add_stt_usage(audio_seconds: float, provider: str = "deepgram", model: str = "nova-3-phonecall"):
    """Add STT usage to current call's tracker."""
    get_cost_tracker().add_stt_usage(audio_seconds, provider, model)

def add_tts_usage(characters: int, provider: str = "deepgram", model: str = "nova-3-phonecall"):
    """Add TTS usage to current call's tracker."""
    get_cost_tracker().add_tts_usage(characters, provider, model)

def get_cost_summary() -> Dict:
    """Get complete cost summary for current call."""
    return get_cost_tracker().get_summary_dict()
