import { useRef, useState, useEffect, useCallback, useLayoutEffect } from "react";
import { removeMarkdownFormatting } from "@/utils/textFormatting";

export type EmbedChatMessage = {
  name: string;
  message: string;
  isSelf: boolean;
  timestamp: number;
  isTyping?: boolean;
};

type EmbeddableChatTileProps = {
  messages: EmbedChatMessage[];
  accentColor: string;
  onSend?: (message: string) => Promise<any>;
  height?: string;
  showHeader?: boolean;
  headerText?: string;
  floatingButton?: boolean;
  unreadCount?: number;
  onOpen?: () => void;
  onClose?: () => void;
  expanded?: boolean;
  agentIsTyping?: boolean;
};

export const EmbeddableChatTile = ({
  messages,
  accentColor,
  onSend,
  height = "100%",
  showHeader = false,
  headerText = "Chat",
  floatingButton = true,
  unreadCount = 0,
  onOpen,
  onClose,
  expanded = false,
  agentIsTyping = false
}: EmbeddableChatTileProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [messageText, setMessageText] = useState("");
  const lastAgentMessageRef = useRef<HTMLDivElement | null>(null);
  // Ref to store previous scroll state
  const scrollStateRef = useRef({ scrollTop: 0, scrollHeight: 0 });

  const isTyping = messages.some(msg => msg.isTyping && !msg.isSelf);

  // Use useLayoutEffect for synchronous scroll adjustment after DOM updates
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Read the state *after* DOM update but *before* our potential scroll adjustment
    const currentScrollTop = container.scrollTop;
    const currentScrollHeight = container.scrollHeight;
    const containerHeight = container.clientHeight;

    // Get the state from the *previous* layout effect run
    const prevScrollTop = scrollStateRef.current.scrollTop;
    const prevScrollHeight = scrollStateRef.current.scrollHeight;

    // Update the ref *now* with the current state, so the *next* run has the correct previous state
    scrollStateRef.current = { scrollTop: currentScrollTop, scrollHeight: currentScrollHeight };

    // Threshold to determine if user was scrolled near the bottom (e.g., within 50px)
    const SCROLL_THRESHOLD = 50;
    const wasNearBottom = prevScrollTop + containerHeight >= prevScrollHeight - SCROLL_THRESHOLD;

    console.log('[LayoutEffect] Triggered.', {
      prevScrollTop, prevScrollHeight, currentScrollTop, currentScrollHeight, containerHeight, wasNearBottom
    });

    if (currentScrollHeight > prevScrollHeight && wasNearBottom) {
      // If content height increased and user was near bottom, maintain scroll from bottom
      const newScrollTop = currentScrollHeight - containerHeight;
      console.log(`[LayoutEffect] Scrolling to bottom (${newScrollTop}) because height increased [${prevScrollHeight} -> ${currentScrollHeight}] and was near bottom.`);
      // Setting scrollTop directly
      container.scrollTop = newScrollTop;
      // Update ref again *if* we changed scrollTop, to reflect the *final* state for the next cycle?
      // scrollStateRef.current.scrollTop = newScrollTop; // Maybe needed?
    } else {
      console.log(`[LayoutEffect] Not scrolling. Height increased: ${currentScrollHeight > prevScrollHeight}. Was near bottom: ${wasNearBottom}.`);
    }

    // No need to update ref again here, it was updated before the conditional logic
    // scrollStateRef.current = { scrollTop: container.scrollTop, scrollHeight: currentScrollHeight };

  }, [messages]); // Still dependent on messages array changes
  
  // Handle sending messages
  const handleSend = useCallback(() => {
    if (!onSend || !messageText.trim()) return;
    onSend(messageText);
    setMessageText("");
    // Focus input after sending
    inputRef.current?.focus();
  }, [onSend, messageText]);

  // Maintain focus on input during and after typing
  useEffect(() => {
    // Focus input when typing starts or stops
    inputRef.current?.focus();
  }, [isTyping, messages.length]); // Also trigger on new messages

  // Toggle chat expansion
  const toggleChat = useCallback(() => {
    if (expanded) {
      onClose?.();
    } else {
      onOpen?.();
      // Focus input when opening chat
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [expanded, onOpen, onClose]);

  // Typing indicator
  const TypingIndicator = () => (
    <div className="flex items-center space-x-1 mt-2 mb-1">
      <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "0ms" }}></div>
      <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "150ms" }}></div>
      <div className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce`} style={{ animationDelay: "300ms" }}></div>
    </div>
  );

  // Scroll to agent's last message after 100ms when typing stops
  useEffect(() => {
    console.log('[Effect 2] Triggered. Dependency: isTyping', isTyping);
    if (!isTyping) {
      const timer = setTimeout(() => {
        if (lastAgentMessageRef.current) {
          console.log('[Effect 2] Scrolling to last agent message. Ref exists.');
          lastAgentMessageRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); // Use block: nearest?
        } else {
          console.log('[Effect 2] Condition met, but lastAgentMessageRef is null.');
        }
      }, 100);
      return () => clearTimeout(timer);
    } else {
       console.log('[Effect 2] Condition not met (isTyping is true).');
    }
  }, [isTyping]);

  // Floating button
  if (floatingButton && !expanded) {
    return (
      <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end">
        {unreadCount > 0 && (
          <div className="absolute -top-3 -right-3 bg-red-500 text-white rounded-full min-w-[20px] h-5 flex items-center justify-center text-xs font-bold px-1 z-10">
            {unreadCount > 99 ? '99+' : unreadCount}
          </div>
        )}
        {isTyping && (
          <div className="bg-gray-800 text-white text-xs rounded-lg p-2 mb-2">
            Agent is typing...
          </div>
        )}
        <button
          onClick={toggleChat}
          className={`w-14 h-14 rounded-full bg-${accentColor}-600 text-white shadow-lg flex items-center justify-center transition-transform hover:scale-110 focus:outline-none`}
          aria-label="Open chat"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </button>
      </div>
    );
  }

  // Main chat container
  return (
    <div
      className={`flex flex-col ${floatingButton ? 'fixed bottom-4 right-4 z-50 w-80 h-96 shadow-xl' : 'w-full h-full'} bg-white text-gray-200 rounded-md overflow-hidden`}
      style={!floatingButton ? { height } : undefined}
    >
      <div className="bg-gray-800 p-2 text-sm font-medium flex justify-between items-center">
        {headerText}
        {floatingButton && (
          <button
            onClick={toggleChat}
            className="text-gray-400 hover:text-white focus:outline-none"
            aria-label="Close chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-3"
      >
        <div className="flex flex-col gap-2">
          {messages.map((msg, index) => {
            const isLastAgentMessage = !msg.isSelf && !msg.isTyping &&
              index === messages
                .map((m, i) => (!m.isSelf && !m.isTyping ? i : -1))
                .filter(i => i !== -1)
                .pop();

            return (
              <div
                key={msg.timestamp}
                className={`flex flex-col ${msg.isSelf ? 'items-end' : 'items-start'}`}
                ref={isLastAgentMessage ? lastAgentMessageRef : null}
              >
                <div
                  className={`rounded-md px-3 py-2 max-w-[80%] break-words ${
                    msg.isSelf
                      ? `bg-${accentColor}-800 text-white`
                      : 'bg-gray-800 text-gray-200'
                  } ${msg.isTyping ? 'border-l-2 border-' + accentColor + '-500' : ''}`}
                >
                  {!msg.isSelf && (
                    <div className="text-xs font-medium text-gray-400 mb-1">
                      {msg.name}
                    </div>
                  )}
                  <div className={`text-sm ${msg.isTyping ? 'min-h-[1.5rem]' : ''}`}>
                    {msg.isSelf ? msg.message : removeMarkdownFormatting(msg.message)}
                    {msg.isTyping && <TypingIndicator />}
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1 px-1">
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
            );
          })}
          {agentIsTyping && (
            <div className="flex items-center mt-2 mb-1">
              <span className={`w-2 h-2 rounded-full bg-${accentColor}-500 animate-bounce mr-2`}></span>
              <span className="text-xs text-gray-400">Thinking...</span>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-gray-800 p-3">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            className="flex-1 bg-gray-800 text-sm rounded-md px-3 py-2 outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Type a message..."
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={!messageText.trim()}
            className={`px-4 py-2 rounded-md text-sm font-medium bg-${accentColor}-600 text-white disabled:opacity-50 transition-colors`}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};


// sol 1