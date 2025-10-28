import { useEffect, useState, useCallback, useMemo, memo } from "react";
import { LiveKitRoom, useChat, useParticipants, useTracks, useLocalParticipant, useDataChannel, useTrackTranscription } from "@livekit/components-react";
import { useRouter } from "next/router";
import { EmbeddableChatTile } from "@/components/chat/EmbeddableChatTile";
import Head from "next/head";
import { ConnectionState, Track } from "livekit-client";

// Add CSS for animations
const animationStyles = `
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes fade-in-up {
    from { 
      opacity: 0;
      transform: translateY(10px);
    }
    to { 
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .animate-fade-in {
    animation: fade-in 0.3s ease-in-out;
  }
  
  .animate-fade-in-up {
    animation: fade-in-up 0.3s ease-in-out;
  }
`;

// Define message type
type ChatMessage = {
  name: string;
  message: string;
  timestamp: number;
  isSelf: boolean;
  isTyping?: boolean;
};

// Define types for clearer parameter handling
type EmbedConfig = {
  affiliateId: string;
  affiliateType: string;
  familyId: string;
  affiliateName: string;
  participantName: string;
  accentColor: string;
  roomName: string; // Constructed room name
};

type PostMessageData = {
  type: string;
  token?: string;
  url?: string;
  roomName?: string; // Can be provided directly OR constructed
  participantName?: string;
  affiliateId?: string;
  affiliateType?: string;
  familyId?: string;
  affiliateName?: string;
  accentColor?: string;
  audio?: boolean;
  video?: boolean;
};

// Function to generate random alphanumeric string
const generateRandomString = (length: number): string => {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  const charactersLength = characters.length;
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
};

// Separate component to handle transcription updates
const TranscriptionHandler = ({ 
  transcription, 
  stableTrackRef,
  onMessageUpdate 
}: { 
  transcription: any;
  stableTrackRef: any;
  onMessageUpdate: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
}) => {
  useEffect(() => {
    if (!transcription?.segments?.length) {
      return;
    }
    
    try {
      // Sort segments by ID to get latest ones
      const sortedSegments = [...transcription.segments]
        .sort((a: { id: string }, b: { id: string }) => {
          const aNum = parseInt(a.id, 10);
          const bNum = parseInt(b.id, 10);
          
          if (!isNaN(aNum) && !isNaN(bNum)) {
            return bNum - aNum;
          }
          
          return a.id > b.id ? -1 : 1;
        });
      
      // Find latest final and non-final segments
      const latestFinalSegment = sortedSegments.find(s => s.final && s.text?.trim().length > 0);
      const latestTypingSegment = sortedSegments.find(s => !s.final && s.text?.trim().length > 0);
      
      onMessageUpdate((prev: ChatMessage[]) => {
        // Keep all non-typing messages
        const nonTypingMessages = prev.filter((m: ChatMessage) => !m.isTyping);
        
        // Add final message if it's new
        if (latestFinalSegment) {
          const finalExists = nonTypingMessages.some((m: ChatMessage) => 
            m.name === "Agent" && 
            m.message === latestFinalSegment.text
          );
          
          if (!finalExists) {
            nonTypingMessages.push({
              name: "Agent",
              message: latestFinalSegment.text,
              timestamp: Date.now(),
              isSelf: false
            });
          }
        }
        
        // Add typing indicator if there is one
        if (latestTypingSegment) {
          return [...nonTypingMessages, {
            name: "Agent",
            message: latestTypingSegment.text,
            timestamp: Date.now(),
            isSelf: false,
            isTyping: true
          }].sort((a: ChatMessage, b: ChatMessage) => a.timestamp - b.timestamp);
        }
        
        return nonTypingMessages.sort((a: ChatMessage, b: ChatMessage) => a.timestamp - b.timestamp);
      });
    } catch (error) {
      console.error('[embed-chat] Error processing transcription segments:', error);
    }
  }, [transcription?.segments, onMessageUpdate]);

  return null;
};

TranscriptionHandler.displayName = 'TranscriptionHandler';

// Page component
export default function EmbedChat() {
  const router = useRouter();
  const [connectionParams, setConnectionParams] = useState({
    token: "",
    url: "",
    roomName: "",
    participantName: "",
    accentColor: "white",
    audio: true,
    video: true,
    connect: false
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<Array<ChatMessage>>([]); // Using defined ChatMessage type
  const [agentIsTyping, setAgentIsTyping] = useState(false);

  // Helper to get config and construct room name
  const getConfigParams = (source: URLSearchParams | PostMessageData): EmbedConfig | null => {
    let affiliateId = "";
    let affiliateType = "";
    let familyId = "";
    let affiliateName = "";
    let participantName = "";
    let accentColor = "cyan";
    let roomName = "";

    if (source instanceof URLSearchParams) {
      affiliateId = source.get("affiliateId") || "";
      affiliateType = source.get("affiliateType") || "";
      familyId = source.get("familyId") || "";
      affiliateName = source.get("affiliateName") || "";
      participantName = source.get("name") || ""; // Keep using 'name' param for participant
      accentColor = source.get("color") || "cyan";
    } else { // PostMessageData
      affiliateId = source.affiliateId || "";
      affiliateType = source.affiliateType || "";
      familyId = source.familyId || "";
      affiliateName = source.affiliateName || "";
      participantName = source.participantName || "Guest";
      accentColor = source.accentColor || "cyan";
    }

    // Construct room name only if all parts are present
    if (affiliateType && affiliateId && familyId && affiliateName) {
      const randomPart = generateRandomString(5);
      // Always use "both" for affiliateType in room name
      roomName = `both-${affiliateId}-${familyId}-${affiliateName}-${randomPart}`;
      console.log('[embed-chat] Constructed roomName:', roomName); // Log the generated name
    } else {
        // If we are processing postMessage data, check if roomName was explicitly provided
        if (!(source instanceof URLSearchParams) && source.roomName) {
          // If roomName is provided directly via postMessage, use it as is (might already have random part)
          roomName = source.roomName;
          console.log('[embed-chat] Using provided roomName via postMessage:', roomName);
        } else {
           // If essential parts are missing for construction and not provided directly, return null
           console.warn('[embed-chat] Missing affiliateType, affiliateId, familyId, or affiliateName for room construction.');
           return null;
        }
    }
    
    // Check if participant name is also present
    if (!participantName) {
        console.warn('[embed-chat] Missing participantName.');
        return null;
    }

    return { affiliateId, affiliateType, familyId, affiliateName, participantName, accentColor, roomName };
  };

  // Listen for both URL parameters and postMessage API
  useEffect(() => {
    let processed = false; // Flag to prevent processing both methods

    const handleMessage = (event: MessageEvent) => {
      if (processed) return; // Already processed URL params
      
      try {
        const data: PostMessageData = event.data;
        if (data.type === "CHAT_CONFIG") {
          console.log('[embed-chat] Received postMessage config:', data);
          processed = true; // Mark as processed
          
          const token = data.token || "";
          const url = data.url || "";
          const config = getConfigParams(data);

          if (!config) {
              setError("Invalid configuration: Missing required parameters (affiliateType, affiliateId, familyId, participantName).");
              setLoading(false);
              return;
          }
          
          if (token && url) {
            // If token and URL are provided directly
            setConnectionParams({
              token,
              url,
              roomName: config.roomName, // Use constructed or provided room name
              participantName: config.participantName,
              accentColor: config.accentColor,
              audio: data.audio ?? true,
              video: data.video ?? true,
              connect: true
            });
            setLoading(false);
          } else {
            // Otherwise fetch token from our API using constructed roomName
            fetchToken(config.roomName, config.participantName)
              .then(({ token, url }) => {
                setConnectionParams({
                  token,
                  url,
                  roomName: config.roomName,
                  participantName: config.participantName,
                  accentColor: config.accentColor,
                  audio: data.audio ?? true,
                  video: data.video ?? true,
                  connect: true
                });
                setLoading(false);
              })
              .catch(err => {
                console.error("Error fetching token:", err);
                setError("Failed to generate connection token");
                setLoading(false);
              });
          }
        }
      } catch (e) {
        console.error("Error processing message:", e);
        setError("Invalid configuration data");
        setLoading(false);
      }
    };

    window.addEventListener("message", handleMessage);

    // Check URL parameters if no postMessage received yet
    const checkUrlParams = () => {
        if (processed) return; // Already processed postMessage
        
        const urlParams = new URLSearchParams(window.location.search);
        const config = getConfigParams(urlParams);

        if (config) {
            console.log('[embed-chat] Using URL parameters:', config);
            processed = true; // Mark as processed
            
            fetchToken(config.roomName, config.participantName)
                .then(({ token, url }) => {
                    setConnectionParams({
                        token,
                        url,
                        roomName: config.roomName,
                        participantName: config.participantName,
                        accentColor: config.accentColor,
                        audio: true, // Default audio/video for URL params
                        video: true,
                        connect: true
                    });
                    setLoading(false);
                })
                .catch(err => {
                    console.error("Error fetching token:", err);
                    setError("Failed to generate connection token");
                    setLoading(false);
                });
        } else if (router.isReady && !connectionParams.connect && !processed) {
          // If no valid config from URL or postMessage, and router is ready
          console.log('[embed-chat] No valid config from URL or postMessage received yet.')
          setLoading(false); // Stop loading, will show example embed code
        }
    };

    // Need to wait for router to be ready to access query params reliably
    if (router.isReady) {
      checkUrlParams();
    } else {
      // If router not ready, listen for route change complete
      const handleRouteChange = () => {
        checkUrlParams();
        router.events.off('routeChangeComplete', handleRouteChange);
      };
      router.events.on('routeChangeComplete', handleRouteChange);
      // Add a timeout fallback in case routeChangeComplete doesn't fire
      const timeoutId = setTimeout(() => {
        if (!processed) {
          checkUrlParams();
        }
      }, 1000);
      return () => clearTimeout(timeoutId);
    }

    return () => {
      window.removeEventListener("message", handleMessage);
      // Clean up router event listener if component unmounts before firing
      router.events.off('routeChangeComplete', () => {}); 
    };
  }, [router.isReady, router.events, connectionParams.connect]); // Added router.events

  // Function to fetch LiveKit token
  const fetchToken = async (roomName: string, participantName: string) => {
    console.log('[embed-chat] Fetching token for:', { roomName, participantName });
    const params = new URLSearchParams();
    params.append('roomName', roomName);
    params.append('participantName', participantName);
    
    const response = await fetch(`/api/token?${params}`);
    if (!response.ok) {
      throw new Error("Failed to fetch token");
    }
    
    const { accessToken } = await response.json();
    console.log('[embed-chat] Token received successfully');
    return { 
      token: accessToken, 
      url: process.env.NEXT_PUBLIC_LIVEKIT_URL || ""
    };
  };

  // Chat Component
  const ChatContent = memo(() => {
    // Setup basic hooks
    const { chatMessages, send: sendChat } = useChat();
    const participants = useParticipants();
    const { localParticipant } = useLocalParticipant();
    const tracks = useTracks();
    
    // Find agent audio track specifically - KEY FOR TRANSCRIPTION
    const agentAudioTrack = useMemo(() => {
      return tracks.find(
        trackRef => 
          trackRef?.participant?.isAgent && 
          trackRef?.publication?.kind === Track.Kind.Audio
      );
    }, [tracks]);
    
    // Create a stable reference to the track
    const stableTrackRef = useMemo(() => {
      return agentAudioTrack || null;
    }, [agentAudioTrack]);
    
    // Use LiveKit's transcription hook directly
    const transcription = useTrackTranscription(stableTrackRef === null ? undefined : stableTrackRef);
    
    // Memoize message update handler
    const handleMessageUpdate = useCallback((updater: (prev: ChatMessage[]) => ChatMessage[]) => {
      setMessages(prev => {
        const updatedMessages = updater(prev);
        // If any agent message is present, stop typing indicator
        if (updatedMessages.some(msg => msg.name === "Agent" && !msg.isSelf)) {
          setAgentIsTyping(false);
        }
        // Get all existing non-typing messages
        const existingNonTypingMessages = prev.filter(m => !m.isTyping);
        
        // Find new agent messages that aren't typing indicators
        const newAgentMessages = updatedMessages.filter(newMsg => 
          newMsg.name === "Agent" && 
          !newMsg.isTyping &&
          !existingNonTypingMessages.some(existing => 
            existing.name === "Agent" && 
            existing.message === newMsg.message
          )
        );
        
        // Update unread count when chat is not expanded
        if (newAgentMessages.length > 0 && !expanded) {
          setUnreadCount(count => count + newAgentMessages.length);
        }
        
        // Combine user messages with agent messages but avoid duplicates
        const combinedMessages = [
          ...existingNonTypingMessages,
          ...updatedMessages.filter(newMsg => 
            newMsg.name === "Agent" && 
            !existingNonTypingMessages.some(existing => 
              existing.name === "Agent" && 
              existing.message === newMsg.message &&
              !newMsg.isTyping
            )
          )
        ];
        
        // Sort all messages by timestamp
        return combinedMessages.sort((a, b) => a.timestamp - b.timestamp);
      });
    }, []);
    
    // Memoize chat handlers
    const handleChatOpen = useCallback(() => {
      setUnreadCount(0);
      setExpanded(true);
    }, []);

    const handleChatClose = useCallback(() => {
      setExpanded(false);
    }, []);

    // Handle sending messages
    const handleSend = useCallback(async (message: string) => {
      try {
        setAgentIsTyping(true);
        // Create a new user message
        const userMessage = {
          name: "You",
          message,
          timestamp: Date.now(),
          isSelf: true
        };
        
        // Add it to the chat immediately
        setMessages(prev => [...prev, userMessage]);
        
        // Send to LiveKit in the background
        await sendChat(message);
        
        return userMessage;
      } catch (error) {
        console.error('Error sending message:', error);
        throw error;
      }
    }, [sendChat]);

    // Memoize the chat tile props
    const chatTileProps = useMemo(() => ({
      messages,
      accentColor: connectionParams.accentColor,
      onSend: handleSend,
      showHeader: true,
      headerText: "Chat",
      floatingButton: true,
      unreadCount,
      onOpen: handleChatOpen,
      onClose: handleChatClose,
      expanded,
      agentIsTyping
    }), [
      handleSend,
      handleChatOpen,
      handleChatClose,
      agentIsTyping
    ]);

    return (
      <div style={{ 
        background: 'transparent',
        margin: 0,
        padding: 0,
        position: 'relative'
      }}>
        <TranscriptionHandler
          transcription={transcription}
          stableTrackRef={stableTrackRef}
          onMessageUpdate={handleMessageUpdate}
        />
        <EmbeddableChatTile {...chatTileProps} />
      </div>
    );
  });

  // Add display name to the ChatContent component
  ChatContent.displayName = 'ChatContent';

  // Show loading screen
  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  // Show error screen
  if (error) {
    return <div className="flex items-center justify-center h-screen text-red-500">{error}</div>;
  }

  // Show example embed code if not connected
  if (!connectionParams.token || !connectionParams.url) {
    // Get origin safely
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    return (
      <div className="p-4">
        <h1 className="text-xl mb-4">Chat Widget Embed</h1>
        <p className="mb-2">To use this widget, provide configuration via URL parameters or postMessage.</p>
        <p className="mb-4 text-sm text-red-600">Required parameters: affiliateType, affiliateId, familyId, name (participantName).</p>
        
        <h2 className="text-lg font-semibold mb-2 mt-4">Method 1: URL Parameters</h2>
        <pre className="bg-gray-800 p-4 rounded overflow-x-auto text-xs text-white">
          {`<iframe 
  src="${origin}/embed-chat?affiliateType=YOUR_TYPE&affiliateId=YOUR_AFFILIATE_ID&familyId=YOUR_FAMILY_ID&name=PARTICIPANT_NAME&color=cyan" 
  width="400" 
  height="600" 
  frameBorder="0"
></iframe>`}
        </pre>
        
        <h2 className="text-lg font-semibold mb-2 mt-4">Method 2: postMessage API</h2>
        <p className="mb-2 text-sm">First, load the iframe with the base URL:</p>
        <pre className="bg-gray-800 p-4 rounded overflow-x-auto text-xs text-white">
          {`<iframe id="chat-frame" src="${origin}/embed-chat" width="400" height="600" frameBorder="0"></iframe>`}
        </pre>
        <p className="mb-2 text-sm">Then, send the configuration via postMessage:</p>
        <pre className="bg-gray-800 p-4 rounded overflow-x-auto text-xs text-white">
          {`const iframe = document.getElementById('chat-frame');
iframe.onload = function() {
  iframe.contentWindow.postMessage({
    type: 'CHAT_CONFIG',
    affiliateType: 'YOUR_TYPE',
    affiliateId: 'YOUR_AFFILIATE_ID',
    familyId: 'YOUR_FAMILY_ID',
    participantName: 'PARTICIPANT_NAME',
    accentColor: 'cyan' // Optional
  }, '*');
};`}
        </pre>

        <h2 className="text-lg font-semibold mb-2 mt-4">Method 3: postMessage with Custom Token</h2>
        <p className="mb-2 text-sm">If providing your own LiveKit token and URL:</p>
        <pre className="bg-gray-800 p-4 rounded overflow-x-auto text-xs text-white">
          {`iframe.contentWindow.postMessage({
  type: 'CHAT_CONFIG',
  token: 'YOUR_LIVEKIT_TOKEN',
  url: 'wss://your-livekit-server.com',
  // You can still provide room details if needed, or let the token define it
  affiliateType: 'YOUR_TYPE',
  affiliateId: 'YOUR_AFFILIATE_ID',
  familyId: 'YOUR_FAMILY_ID',
  participantName: 'PARTICIPANT_NAME'
}, '*');`}
        </pre>
      </div>
    );
  }

  // Connected view with chat widget
  return (
    <>
      <Head>
        <title>Chat Widget</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          {`
            body {
              margin: 0;
              padding: 0;
              background: transparent !important;
              overflow: hidden;
            }
            #__next {
              background: transparent !important;
            }
          `}
          {animationStyles}
        </style>
      </Head>
      <main style={{ 
        background: 'transparent',
        margin: 0,
        padding: 0,
        height: 'auto',
        minHeight: 'unset',
        position: 'relative'
      }}>
        <LiveKitRoom
          serverUrl={connectionParams.url}
          token={connectionParams.token}
          connect={connectionParams.connect}
          onError={(e) => {
            console.error("LiveKit connection error:", e);
            setError(`Connection error: ${e.message}`);
          }}
        >
          <ChatContent />
        </LiveKitRoom>
      </main>
    </>
  );
} 