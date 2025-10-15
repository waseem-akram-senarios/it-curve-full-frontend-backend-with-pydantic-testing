import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatMessageInput } from "@/components/chat/ChatMessageInput";
import { ChatMessage as ComponentsChatMessage } from "@livekit/components-react";
import { useEffect, useRef, useState } from "react";

const inputHeight = 48;

export type ChatMessageType = {
  name: string;
  message: string;
  isSelf: boolean;
  timestamp: number;
  isTyping?: boolean;
  isThinking?: boolean;
};

type ChatTileProps = {
  messages: ChatMessageType[];
  accentColor: string;
  onSend?: (message: string) => Promise<ComponentsChatMessage>;
  showThinking?: boolean;
  agentIsTyping?: boolean;
};

export const ChatTile = ({ 
  messages, 
  accentColor, 
  onSend,
  showThinking = false,
  agentIsTyping = false
}: ChatTileProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [lastSentTime, setLastSentTime] = useState(0);
  
  // Scroll to bottom when messages change or when thinking state changes
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [containerRef, messages, showThinking]);

  // Log thinking state for debugging
  useEffect(() => {
    console.log("ChatTile showThinking state:", showThinking);
    console.log("Agent is typing:", agentIsTyping);
  }, [showThinking, agentIsTyping]);

  // Handle message sending with thinking state
  const handleSend = async (message: string) => {
    if (!onSend) return;
    
    // Update last sent time
    const currentTime = Date.now();
    setLastSentTime(currentTime);
    console.log("Message sent, timestamp:", currentTime);
    
    // Send the message to LiveKit
    return onSend(message);
  };

  // Check if we should show the thinking indicator
  const shouldShowThinking = (): boolean => {
    // If explicitly told to show thinking, always show it
    if (showThinking) {
      return true;
    }
    
    // Legacy logic as fallback
    if (!lastSentTime) return false;
    
    // Don't show thinking if there's no recent user message
    if (messages.length === 0) return false;
    
    // Find the last message - if it's from the agent, don't show thinking
    const lastMessage = [...messages].sort((a, b) => b.timestamp - a.timestamp)[0];
    if (lastMessage && !lastMessage.isSelf && !lastMessage.isTyping) return false;
    
    // If there's an agent typing, don't show thinking
    const messageAgentIsTyping = messages.some(m => !m.isSelf && m.isTyping);
    if (messageAgentIsTyping) return false;
    
    // Only show thinking if the last sent time is recent (within 30 seconds)
    return (Date.now() - lastSentTime) < 30000;
  };

  // Determine whether to show the thinking indicator
  const displayThinking = shouldShowThinking();

  // Determine if we should disable the input - ONLY disable if agent is actively typing
  // Not when just showing the thinking indicator
  const isInputDisabled = agentIsTyping;

  // Log thinking state and input disabled state for debugging
  useEffect(() => {
    console.log("ChatTile states:", { 
      showThinking, 
      agentIsTyping, 
      inputDisabled: isInputDisabled 
    });
  }, [showThinking, agentIsTyping, isInputDisabled]);

  return (
    <div className="flex flex-col gap-4 w-full h-full">
      <div
        ref={containerRef}
        className="overflow-y-auto"
        style={{
          height: `calc(100% - ${inputHeight}px)`,
        }}
      >
        <div className="flex flex-col min-h-full justify-end">
          {messages.map((message, index, allMsg) => {
            const hideName =
              index >= 1 && allMsg[index - 1].name === message.name;

            return (
              <ChatMessage
                key={index}
                hideName={hideName}
                name={message.name}
                message={message.message}
                isSelf={message.isSelf}
                accentColor={accentColor}
              />
            );
          })}
          
          {/* Thinking indicator */}
          {displayThinking && (
            <div className="flex items-start gap-1 mb-2 pl-2 mt-2">
              <div className={`rounded-lg px-4 py-3 bg-gray-300 text-white border-gray-700 max-w-[80%] flex items-center shadow-md`}>
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "0ms" }}></div>
                  <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "150ms" }}></div>
                  <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "300ms" }}></div>
                </div>
                <span className="ml-2 text-black">Thinking...</span>
              </div>
            </div>
          )}
        </div>
      </div>
      <ChatMessageInput
        height={inputHeight}
        placeholder="Type a message"
        accentColor={accentColor}
        onSend={handleSend}
        inputTextColor={typeof window !== 'undefined' && window.location.pathname === '/bot-chat-page' ? 'white' : undefined}
        disabled={isInputDisabled}
        disabledText="Please wait while the agent is typing..."
      />
    </div>
  );
};
