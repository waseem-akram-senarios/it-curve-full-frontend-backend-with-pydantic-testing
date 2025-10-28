import { ChatMessageType, ChatTile } from "@/components/chat/ChatTile";
import {
  TrackReferenceOrPlaceholder,
  useChat,
  useLocalParticipant,
  useTrackTranscription,
  useConnectionState,
} from "@livekit/components-react";
import {
  LocalParticipant,
  Participant,
  Track,
  TranscriptionSegment,
} from "livekit-client";
import { useEffect, useState, useRef } from "react";

export function TranscriptionTile({
  agentAudioTrack,
  accentColor,
  typingSpeed = 'normal'
}: {
  agentAudioTrack?: TrackReferenceOrPlaceholder;
  accentColor: string;
  typingSpeed?: 'slow' | 'normal' | 'fast';
}) {
  const agentMessages = useTrackTranscription(agentAudioTrack || undefined);
  const localParticipant = useLocalParticipant();
  const connectionState = useConnectionState();
  const localMessages = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });

  const [transcripts, setTranscripts] = useState<Map<string, ChatMessageType>>(
    new Map()
  );
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [showThinking, setShowThinking] = useState(false);
  const [lastUserMessageTime, setLastUserMessageTime] = useState(0);
  const [hasAgentResponded, setHasAgentResponded] = useState(false);
  const [agentIsTyping, setAgentIsTyping] = useState(false);
  const { chatMessages, send: sendChat } = useChat();

  // References to track state between renders
  const lastUserMessageRef = useRef(0);
  const isWaitingForResponse = useRef(false);

  // Custom send function to track user messages
  const handleSend = async (message: string) => {
    console.log("User sent message, setting thinking state");
    
    // Check if we're connected before attempting to send
    if (connectionState !== 'connected') {
      console.warn("Cannot send message: not connected to room");
      // Return a rejected promise instead of throwing to handle gracefully
      return Promise.reject(new Error("Not connected to room. Please connect first."));
    }
    
    const currentTime = Date.now();
    setLastUserMessageTime(currentTime);
    lastUserMessageRef.current = currentTime;
    setShowThinking(true);
    isWaitingForResponse.current = true;
    setHasAgentResponded(false);
    
    try {
      return await sendChat(message);
    } catch (error) {
      console.error("Error sending chat message:", error);
      // Reset thinking state on error
      setShowThinking(false);
      isWaitingForResponse.current = false;
      setHasAgentResponded(true);
      throw error;
    }
  };

  // Process update rate based on typing speed
  useEffect(() => {
    if (agentAudioTrack) {
      // Check if agent has started responding
      const hasAgentTyping = agentMessages.segments.some(s => !s.final && s.text);
      const hasAgentFinal = agentMessages.segments.some(s => s.final && s.text);
      
      // Set agent typing state - ONLY when there are actual non-final segments with text
      const isActivelyTyping = hasAgentTyping && agentMessages.segments.some(s => !s.final && s.text.trim().length > 0);
      setAgentIsTyping(isActivelyTyping);
      
      // If agent is typing or has sent a final message, hide thinking indicator
      if ((hasAgentTyping || hasAgentFinal) && isWaitingForResponse.current) {
        console.log("Agent responded, hiding thinking indicator");
        setShowThinking(false);
        setHasAgentResponded(true);
        isWaitingForResponse.current = false;
      }
      
      agentMessages.segments.forEach((s) =>
        transcripts.set(
          s.id,
          segmentToChatMessage(
            s,
            transcripts.get(s.id),
            agentAudioTrack.participant,
            typingSpeed
          )
        )
      );
    } else {
      setAgentIsTyping(false);
    }
    
    localMessages.segments.forEach((s) =>
      transcripts.set(
        s.id,
        segmentToChatMessage(
          s,
          transcripts.get(s.id),
          localParticipant.localParticipant,
          typingSpeed
        )
      )
    );

    const allMessages = Array.from(transcripts.values());
    for (const msg of chatMessages) {
      const isAgent = agentAudioTrack
        ? msg.from?.identity === agentAudioTrack.participant?.identity
        : msg.from?.identity !== localParticipant.localParticipant.identity;
      const isSelf =
        msg.from?.identity === localParticipant.localParticipant.identity;
      let name = msg.from?.name;
      if (!name) {
        if (isAgent) {
          name = "Agent";
        } else if (isSelf) {
          name = "You";
        } else {
          name = "Unknown";
        }
      }
      
      // If we got a chat message from the agent, hide thinking indicator
      if (isAgent && isWaitingForResponse.current) {
        console.log("Agent chat message received, hiding thinking indicator");
        setShowThinking(false);
        setHasAgentResponded(true);
        isWaitingForResponse.current = false;
      }
      
      // If this is a user message, update the timestamp
      if (isSelf) {
        setLastUserMessageTime(msg.timestamp);
        lastUserMessageRef.current = msg.timestamp;
        // If this is a new user message after previous response, show thinking again
        if (!isWaitingForResponse.current && msg.timestamp > lastUserMessageRef.current) {
          console.log("New user message after response, showing thinking again");
          setShowThinking(true);
          isWaitingForResponse.current = true;
          setHasAgentResponded(false);
        }
      }
      
      allMessages.push({
        name,
        message: msg.message,
        timestamp: msg.timestamp,
        isSelf: isSelf,
      });
    }
    allMessages.sort((a, b) => a.timestamp - b.timestamp);
    setMessages(allMessages);
  }, [
    transcripts,
    chatMessages,
    localParticipant.localParticipant,
    agentAudioTrack?.participant,
    agentMessages.segments,
    localMessages.segments,
    agentAudioTrack,
    typingSpeed
  ]);

  // Force showing thinking indicator immediately after sending a message
  useEffect(() => {
    console.log("Thinking state:", { showThinking, isWaiting: isWaitingForResponse.current });
  }, [showThinking]);

  // Automatically hide thinking indicator after 30 seconds if no response
  useEffect(() => {
    if (showThinking && lastUserMessageTime > 0) {
      console.log("Setting timeout to hide thinking indicator");
      const timeout = setTimeout(() => {
        console.log("Timeout reached, hiding thinking indicator");
        setShowThinking(false);
        isWaitingForResponse.current = false;
      }, 30000);
      
      return () => clearTimeout(timeout);
    }
  }, [showThinking, lastUserMessageTime]);

  // Monitor the agent typing state
  useEffect(() => {
    console.log("Agent is typing state changed:", agentIsTyping);
  }, [agentIsTyping]);

  return (
    <ChatTile 
      messages={messages} 
      accentColor={accentColor} 
      onSend={handleSend}
      showThinking={showThinking && isWaitingForResponse.current}
      agentIsTyping={agentIsTyping}
      isConnected={connectionState === 'connected'}
    />
  );
}

function segmentToChatMessage(
  s: TranscriptionSegment,
  existingMessage: ChatMessageType | undefined,
  participant: Participant,
  typingSpeed: 'slow' | 'normal' | 'fast' = 'normal'
): ChatMessageType {
  // If this is the same segment and it's final, don't change it
  if (existingMessage && s.final && existingMessage.message === s.text) {
    return existingMessage;
  }

  // Adjust text length based on typing speed for non-final segments
  let text = s.text;
  const isAgentMessage = !(participant instanceof LocalParticipant);

  // Only apply typing speed to agent messages
  if (!s.final && isAgentMessage) {
    // Calculate visible length based on typing speed
    let visibleLength = text.length; // Initialize with full length as default
    
    // For non-final segments, control how much text is shown based on speed
    if (typingSpeed === 'slow') {
      // Slow: show max 40 chars or 40% of text, whichever is smaller
      visibleLength = Math.min(Math.floor(text.length * 0.4), 40);
    } else if (typingSpeed === 'normal') {
      // Normal: show max 80 chars or 75% of text
      visibleLength = Math.min(Math.floor(text.length * 0.75), 80);
    } else if (typingSpeed === 'fast') {
      // Fast: show the whole text
      visibleLength = text.length;
    }
    
    // If there was a previous message for this segment, show more text progressively
    if (existingMessage && !existingMessage.message.endsWith("...")) {
      const prevLength = existingMessage.message.length;
      // Increment visible text based on speed
      const increment = typingSpeed === 'slow' ? 5 : typingSpeed === 'normal' ? 15 : 50;
      visibleLength = Math.min(prevLength + increment, text.length);
    }
    
    if (visibleLength < text.length) {
      text = `${text.substring(0, visibleLength)}...`;
    }
  }

  const msg: ChatMessageType = {
    message: text,
    name: participant instanceof LocalParticipant ? "You" : "Agent",
    isSelf: participant instanceof LocalParticipant,
    timestamp: existingMessage?.timestamp ?? Date.now(),
  };
  return msg;
}
