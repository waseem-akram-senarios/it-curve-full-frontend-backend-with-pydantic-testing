"""
Universal STT Error Detection System
Detects ANY possible STT transcription error, not just predefined confusion pairs.
Uses semantic analysis, intent matching, and context coherence.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from logging_config import get_logger
import difflib

logger = get_logger('universal_stt_detector')

class UniversalSTTDetector:
    def __init__(self):
        # Core transportation intents and their keywords
        self.transportation_intents = {
            'booking': ['book', 'schedule', 'reserve', 'arrange', 'get', 'need', 'want'],
            'ride_types': ['ride', 'trip', 'transportation', 'taxi', 'uber', 'lyft', 'car', 'vehicle'],
            'locations': ['pickup', 'drop', 'from', 'to', 'address', 'street', 'avenue', 'place', 'location'],
            'time': ['now', 'later', 'tomorrow', 'today', 'time', 'when', 'schedule'],
            'history': ['history', 'past', 'previous', 'before', 'earlier', 'last'],
            'status': ['status', 'where', 'track', 'check', 'update', 'progress'],
            'payment': ['pay', 'payment', 'cost', 'price', 'fare', 'charge', 'bill', 'cash', 'card'],
            'cancel': ['cancel', 'stop', 'end', 'terminate', 'abort', 'quit']
        }
        
        # Common non-transportation words that might be STT errors
        self.non_transport_words = [
            'date', 'food', 'eat', 'burger', 'pizza', 'restaurant', 'dinner', 'lunch',
            'movie', 'film', 'show', 'watch', 'entertainment', 'game', 'play',
            'medicine', 'pill', 'doctor', 'hospital', 'pharmacy', 'health',
            'shop', 'buy', 'purchase', 'store', 'mall', 'clothes'
        ]
        
        # Phonetically similar word patterns
        self.phonetic_patterns = {
            'ride': ['date', 'right', 'wide', 'side', 'hide', 'guide'],
            'book': ['look', 'took', 'cook', 'hook', 'nook'],
            'trip': ['tip', 'grip', 'ship', 'slip', 'flip'],
            'pick': ['tick', 'kick', 'sick', 'quick', 'thick'],
            'drop': ['stop', 'shop', 'top', 'hop', 'crop'],
            'fare': ['fair', 'fear', 'hair', 'care', 'dare'],
            'car': ['bar', 'far', 'jar', 'star', 'tar'],
            'taxi': ['tacky', 'text', 'task'],
            'uber': ['over', 'under', 'upper'],
            'when': ['then', 'ten', 'win', 'pen'],
            'where': ['wear', 'were', 'here', 'there'],
            'time': ['dime', 'lime', 'mime', 'crime'],
            'now': ['how', 'cow', 'wow', 'bow'],
            'pay': ['way', 'day', 'say', 'may'],
            'cost': ['lost', 'most', 'post', 'host'],
            'check': ['deck', 'neck', 'wreck', 'tech']
        }

    def detect_universal_stt_error(self, 
                                 user_input: str, 
                                 bot_response: str,
                                 conversation_history: List[str] = None,
                                 confidence: Optional[float] = None) -> Dict:
        """
        Universal STT error detection that works for ANY possible transcription error.
        
        Args:
            user_input: What STT transcribed
            bot_response: How the bot responded
            conversation_history: Recent conversation context
            confidence: STT confidence if available
            
        Returns:
            Dict with error detection results and suggestions
        """
        
        result = {
            'original_input': user_input,
            'bot_response': bot_response,
            'is_likely_stt_error': False,
            'confidence_score': 0.0,
            'error_indicators': [],
            'suggested_corrections': [],
            'mismatch_analysis': {},
            'should_clarify': False,
            'clarification_type': None
        }
        
        if not user_input.strip() or not bot_response.strip():
            return result
        
        # Analysis 1: Semantic Intent Mismatch
        intent_mismatch = self._analyze_intent_mismatch(user_input, bot_response, conversation_history)
        if intent_mismatch['mismatch_detected']:
            result['error_indicators'].append('intent_mismatch')
            result['mismatch_analysis'] = intent_mismatch
            result['confidence_score'] += 0.3
        
        # Analysis 2: Context Coherence Check
        context_coherence = self._analyze_context_coherence(user_input, bot_response, conversation_history)
        if not context_coherence['is_coherent']:
            result['error_indicators'].append('context_incoherence')
            result['confidence_score'] += 0.2
        
        # Analysis 3: Response Relevance Analysis
        relevance_analysis = self._analyze_response_relevance(user_input, bot_response)
        if relevance_analysis['relevance_score'] < 0.4:
            result['error_indicators'].append('low_relevance')
            result['confidence_score'] += 0.2
        
        # Analysis 4: Phonetic Similarity Check
        phonetic_suggestions = self._find_phonetic_alternatives(user_input, bot_response)
        if phonetic_suggestions:
            result['error_indicators'].append('phonetic_confusion')
            result['suggested_corrections'].extend(phonetic_suggestions)
            result['confidence_score'] += 0.3
        
        # Analysis 5: Domain Vocabulary Mismatch
        domain_mismatch = self._analyze_domain_vocabulary_mismatch(user_input, bot_response)
        if domain_mismatch['mismatch_detected']:
            result['error_indicators'].append('domain_mismatch')
            result['confidence_score'] += 0.2
        
        # Analysis 6: STT Confidence Integration
        if confidence and confidence < 0.6:
            result['error_indicators'].append('low_stt_confidence')
            result['confidence_score'] += 0.4
        
        # Determine if this is likely an STT error
        result['is_likely_stt_error'] = result['confidence_score'] >= 0.5
        
        # Determine clarification strategy
        if result['is_likely_stt_error']:
            result['should_clarify'] = True
            result['clarification_type'] = self._determine_clarification_type(result)
        
        logger.info(f"[UNIVERSAL STT] Input: '{user_input}' | Error Likelihood: {result['confidence_score']:.2f} | Indicators: {result['error_indicators']}")
        
        return result

    def _analyze_intent_mismatch(self, user_input: str, bot_response: str, context: List[str]) -> Dict:
        """Analyze if user intent matches bot response intent."""
        
        user_lower = user_input.lower()
        bot_lower = bot_response.lower()
        
        # Extract intents from user input
        user_intents = []
        for intent_type, keywords in self.transportation_intents.items():
            if any(keyword in user_lower for keyword in keywords):
                user_intents.append(intent_type)
        
        # Extract intents from bot response
        bot_intents = []
        for intent_type, keywords in self.transportation_intents.items():
            if any(keyword in bot_lower for keyword in keywords):
                bot_intents.append(intent_type)
        
        # Check for non-transport words in user input
        non_transport_detected = [word for word in self.non_transport_words if word in user_lower]
        
        mismatch_detected = False
        mismatch_reason = None
        
        # Case 1: User mentions non-transport words but bot responds with transport
        if non_transport_detected and bot_intents:
            mismatch_detected = True
            mismatch_reason = f"User mentioned non-transport words {non_transport_detected} but bot responded with transport intent"
        
        # Case 2: No common intents between user and bot
        elif user_intents and bot_intents and not set(user_intents).intersection(set(bot_intents)):
            mismatch_detected = True
            mismatch_reason = f"User intents {user_intents} don't match bot intents {bot_intents}"
        
        return {
            'mismatch_detected': mismatch_detected,
            'mismatch_reason': mismatch_reason,
            'user_intents': user_intents,
            'bot_intents': bot_intents,
            'non_transport_words': non_transport_detected
        }

    def _analyze_context_coherence(self, user_input: str, bot_response: str, context: List[str]) -> Dict:
        """Check if the conversation flow is coherent."""
        
        if not context:
            return {'is_coherent': True, 'reason': 'No context to analyze'}
        
        # Get recent context (last 3 exchanges)
        recent_context = ' '.join(context[-3:]).lower()
        user_lower = user_input.lower()
        bot_lower = bot_response.lower()
        
        # Check if context is about transportation
        transport_context = any(
            any(keyword in recent_context for keyword in keywords)
            for keywords in self.transportation_intents.values()
        )
        
        # Check if user input fits the context
        user_fits_context = any(
            any(keyword in user_lower for keyword in keywords)
            for keywords in self.transportation_intents.values()
        )
        
        # Check if bot response fits the context
        bot_fits_context = any(
            any(keyword in bot_lower for keyword in keywords)
            for keywords in self.transportation_intents.values()
        )
        
        # Coherence analysis
        is_coherent = True
        reason = "Context is coherent"
        
        if transport_context and not user_fits_context and bot_fits_context:
            is_coherent = False
            reason = "User input doesn't fit established transport context, but bot assumes transport"
        
        return {
            'is_coherent': is_coherent,
            'reason': reason,
            'transport_context': transport_context,
            'user_fits_context': user_fits_context,
            'bot_fits_context': bot_fits_context
        }

    def _analyze_response_relevance(self, user_input: str, bot_response: str) -> Dict:
        """Analyze how relevant the bot response is to user input."""
        
        user_words = set(user_input.lower().split())
        bot_words = set(bot_response.lower().split())
        
        # Calculate word overlap
        common_words = user_words.intersection(bot_words)
        word_overlap_score = len(common_words) / max(len(user_words), 1)
        
        # Calculate semantic relevance using keyword matching
        user_transport_score = sum(
            1 for word in user_words 
            if any(word in keywords for keywords in self.transportation_intents.values())
        ) / max(len(user_words), 1)
        
        bot_transport_score = sum(
            1 for word in bot_words 
            if any(word in keywords for keywords in self.transportation_intents.values())
        ) / max(len(bot_words), 1)
        
        # Overall relevance score
        relevance_score = (word_overlap_score * 0.3 + 
                          min(user_transport_score, bot_transport_score) * 0.7)
        
        return {
            'relevance_score': relevance_score,
            'word_overlap_score': word_overlap_score,
            'user_transport_score': user_transport_score,
            'bot_transport_score': bot_transport_score,
            'common_words': list(common_words)
        }

    def _find_phonetic_alternatives(self, user_input: str, bot_response: str) -> List[Dict]:
        """Find phonetically similar alternatives that would make bot response more relevant."""
        
        suggestions = []
        user_words = user_input.lower().split()
        bot_lower = bot_response.lower()
        
        for i, word in enumerate(user_words):
            # Check if this word has phonetic alternatives
            for transport_word, alternatives in self.phonetic_patterns.items():
                if word in alternatives and transport_word in bot_lower:
                    # Create corrected sentence
                    corrected_words = user_words.copy()
                    corrected_words[i] = transport_word
                    corrected_sentence = ' '.join(corrected_words)
                    
                    # Calculate confidence based on how well it matches bot response
                    confidence = self._calculate_phonetic_confidence(transport_word, bot_response)
                    
                    suggestions.append({
                        'original_word': word,
                        'suggested_word': transport_word,
                        'corrected_sentence': corrected_sentence,
                        'confidence': confidence,
                        'reason': f"Phonetic similarity: '{word}' sounds like '{transport_word}'"
                    })
        
        # Sort by confidence and return top 3
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]

    def _calculate_phonetic_confidence(self, suggested_word: str, bot_response: str) -> float:
        """Calculate confidence for a phonetic suggestion."""
        
        bot_lower = bot_response.lower()
        base_confidence = 0.5
        
        # Boost if suggested word appears in bot response
        if suggested_word in bot_lower:
            base_confidence += 0.3
        
        # Boost if related transport words appear in bot response
        related_words = self.transportation_intents.get('ride_types', []) + \
                       self.transportation_intents.get('booking', [])
        
        related_count = sum(1 for word in related_words if word in bot_lower)
        base_confidence += min(related_count * 0.1, 0.2)
        
        return min(base_confidence, 1.0)

    def _analyze_domain_vocabulary_mismatch(self, user_input: str, bot_response: str) -> Dict:
        """Analyze if there's a domain vocabulary mismatch."""
        
        user_lower = user_input.lower()
        bot_lower = bot_response.lower()
        
        # Count non-transport words in user input
        non_transport_count = sum(1 for word in self.non_transport_words if word in user_lower)
        
        # Count transport words in bot response
        transport_count = sum(
            1 for keywords in self.transportation_intents.values()
            for word in keywords if word in bot_lower
        )
        
        mismatch_detected = non_transport_count > 0 and transport_count > 0
        
        return {
            'mismatch_detected': mismatch_detected,
            'non_transport_count': non_transport_count,
            'transport_count': transport_count,
            'severity': 'high' if non_transport_count >= 2 else 'medium'
        }

    def _determine_clarification_type(self, analysis_result: Dict) -> str:
        """Determine the best type of clarification based on analysis."""
        
        indicators = analysis_result['error_indicators']
        
        if 'phonetic_confusion' in indicators and analysis_result['suggested_corrections']:
            return 'phonetic_clarification'
        elif 'intent_mismatch' in indicators:
            return 'intent_clarification'
        elif 'domain_mismatch' in indicators:
            return 'domain_clarification'
        elif 'low_stt_confidence' in indicators:
            return 'confidence_clarification'
        else:
            return 'general_clarification'

    def generate_universal_clarification(self, analysis_result: Dict) -> str:
        """Generate appropriate clarification message for any STT error."""
        
        clarification_type = analysis_result.get('clarification_type', 'general_clarification')
        
        if clarification_type == 'phonetic_clarification' and analysis_result['suggested_corrections']:
            top_correction = analysis_result['suggested_corrections'][0]
            return f"Just to confirm, did you say '{top_correction['suggested_word']}' or '{top_correction['original_word']}'?"
        
        elif clarification_type == 'intent_clarification':
            return "I want to make sure I understand what you need. Are you looking for help with transportation services like booking a ride, checking trip history, or something else?"
        
        elif clarification_type == 'domain_clarification':
            return "I specialize in transportation services. Are you looking to book a ride, check your trip history, or get help with transportation?"
        
        elif clarification_type == 'confidence_clarification':
            return "I want to make sure I heard you correctly. Could you please repeat what you need help with?"
        
        else:
            return "I want to make sure I understand what you're looking for. Could you please clarify what you need help with?"

# Global instance
universal_stt_detector = UniversalSTTDetector()

def detect_any_stt_error(user_input: str, 
                        bot_response: str,
                        conversation_history: List[str] = None,
                        confidence: Optional[float] = None) -> Dict:
    """Convenience function for universal STT error detection."""
    return universal_stt_detector.detect_universal_stt_error(
        user_input, bot_response, conversation_history, confidence
    )
