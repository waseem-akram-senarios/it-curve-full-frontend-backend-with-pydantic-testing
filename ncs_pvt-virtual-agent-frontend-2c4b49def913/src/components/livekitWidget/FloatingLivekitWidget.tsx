import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import LivekitWidget from "./LivekitWidget";
import {
  useChat,
  useTrackTranscription,
  useParticipants,
  useTracks,
  LiveKitRoom,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import { useRef as useClickRef } from "react";
import { removeMarkdownFormatting } from "@/utils/textFormatting";

interface FloatingLivekitWidgetProps {
  affiliateId?: string;
  familyId?: string;
  affiliateName?: string;
  name?: string;
  accentColor?: string;
  typingSpeed?: 'slow' | 'normal' | 'fast';
  phoneNo?: string;
  userID?: string;
  clientID?: string;
}

const defaultAccentColor = "green";

// Helper to get query param or fallback
function getParam(name: string, fallback = "") {
  if (typeof window === "undefined") return fallback;
  const url = new URL(window.location.href);
  return url.searchParams.get(name) || fallback;
}

export default function FloatingLivekitWidget(props: FloatingLivekitWidgetProps) {
  // Dynamic props via query params
  const affiliateId = props.affiliateId || getParam("affiliateId", "65");
  // affiliateType is always "both" now
  const affiliateType = "both";
  const familyId = props.familyId || getParam("familyId", "3");
  const affiliateName = props.affiliateName || getParam("affiliateName", "ARMON");
  const name = props.name || getParam("name", "ARMON");
  const accentColor = props.accentColor || getParam("accentColor", defaultAccentColor);
  const initialTypingSpeed = (props.typingSpeed || getParam("typingSpeed", "fast")) as 'slow' | 'normal' | 'fast';
  const phoneNo = props.phoneNo || getParam("phoneNo", "");
  const userID = props.userID || getParam("userID", "");
  const clientID = props.clientID || getParam("clientID", "");

  // Connection state is managed here
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [lastAgentMessage, setLastAgentMessage] = useState("");
  const [agentIsTyping, setAgentIsTyping] = useState(false);
  const [hasFocus, setHasFocus] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState<'slow' | 'normal' | 'fast'>(initialTypingSpeed);
  // Store user location
  const [userLocation, setUserLocation] = useState<{
    latitude: number | null;
    longitude: number | null;
    accuracy: number | null;
  }>({
    latitude: null,
    longitude: null,
    accuracy: null
  });
  const lastReadTimestamp = useRef(Date.now());
  const unreadRef = useRef(0);
  const prevAgentIsTyping = useRef(false);
  // Track the current/last connected room name
  const [currentRoomName, setCurrentRoomName] = useState<string>("");
  // Track if this is the first time opening the widget
  const isFirstOpen = useRef(true);

  // Settings popover state
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    affiliateId,
    familyId,
    affiliateName,
    name,
    accentColor,
    typingSpeed: initialTypingSpeed,
    phoneNo,
    userID,
    clientID,
  });
  const settingsRef = useClickRef<HTMLDivElement>(null);

  // Get user location when component mounts
  useEffect(() => {
    const getUserLocation = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const { latitude, longitude, accuracy } = position.coords;
            console.log('User location in widget:', { 
              latitude, 
              longitude, 
              accuracy: `${accuracy} meters`,
              timestamp: new Date(position.timestamp).toISOString()
            });
            
            // Store location in state for use in metadata
            setUserLocation({
              latitude,
              longitude,
              accuracy
            });
          },
          (error) => {
            console.error('Geolocation error in widget:', error.message);
          },
          {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
          }
        );
      } else {
        console.error('Geolocation is not supported by this browser');
      }
    };

    getUserLocation();
  }, []);

  // Room name logic
  const generateRandomString = (length: number): string => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
  };
  const computedRoomName = useMemo(() => {
    const randomPart = generateRandomString(5);
    // Always use "both" for affiliateType in room name
    return `both-${affiliateId}-${familyId}-${affiliateName}-${randomPart}`;
  }, [affiliateId, familyId, affiliateName]);

  // Connect to LiveKit on mount
  const handleConnect = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      // Always use the latest settings for room name and participant
      const randomPart = generateRandomString(5);
      // Always use "both" for affiliateType in room name
      const roomName = `both-${settings.affiliateId}-${settings.familyId}-${settings.affiliateName}-${randomPart}`;
      const params = new URLSearchParams();
      params.append("roomName", roomName);
      params.append("participantName", settings.name);
      
      // Add metadata with the new fields including location
      const metadata = JSON.stringify({
        phoneNo: settings.phoneNo,
        clientID: settings.clientID,
        userID: settings.userID,
        affiliateId: settings.affiliateId,
        familyId: settings.familyId,
        affiliateName: settings.affiliateName,
        location: {
          latitude: userLocation.latitude,
          longitude: userLocation.longitude,
          accuracy: userLocation.accuracy
        }
      });
      params.append("metadata", metadata);
      
      const response = await fetch(`/api/token?${params}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch token: ${response.status} ${response.statusText} - ${errorText}`);
      }
      const { accessToken } = await response.json();
      const wsUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL || "";
      if (!wsUrl) {
        throw new Error("LiveKit URL not configured. Please check your environment variables.");
      }
      setToken(accessToken);
      setUrl(wsUrl);
      setConnected(true);
      setCurrentRoomName(roomName);
    } catch (err: any) {
      setError(err.message || "Failed to connect");
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [settings, userLocation]);

  // Only reset unread count when chat is opened
  useEffect(() => {
    if (open) {
      unreadRef.current = 0;
      setUnreadCount(0);
      lastReadTimestamp.current = Date.now();
    }
    // No reset on minimize
  }, [open, setUnreadCount, lastReadTimestamp]);

  // Auto-connect when widget is opened for the first time
  useEffect(() => {
    if (open && isFirstOpen.current && !connected) {
      isFirstOpen.current = false;
      handleConnect();
    }
  }, [open, connected, handleConnect]);

  // Increment unread count when agentIsTyping transitions from true to false and chat is minimized
  useEffect(() => {
    if (!open && prevAgentIsTyping.current && !agentIsTyping) {
      unreadRef.current += 1;
      setUnreadCount(unreadRef.current);
    }
    prevAgentIsTyping.current = agentIsTyping;
  }, [agentIsTyping, open, setUnreadCount]);

  // Disconnect logic
  const handleDisconnect = useCallback(async () => {
    setConnected(false);
    // Do NOT clear token or url here!
    // Call the delete-room API with the current room name
    try {
      const res = await fetch("/api/delete-room", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomName: currentRoomName }),
      });
      if (!res.ok) {
        const err = await res.text();
        console.error("Failed to delete room:", err);
      } else {
        console.log("Room deleted successfully");
      }
    } catch (e) {
      console.error("Error deleting room:", e);
    }
  }, [currentRoomName]);

  // Close popover on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (showSettings && settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    }
    if (showSettings) {
      document.addEventListener("mousedown", handleClick);
    }
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettings]);

  // Update and reconnect logic
  const handleSettingsUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setShowSettings(false);
    // Update the typing speed
    setTypingSpeed(settings.typingSpeed);
    
    // Check if connection params changed - only reconnect if needed
    if (settings.affiliateId !== affiliateId || 
        settings.familyId !== familyId || 
        settings.affiliateName !== affiliateName) {
      
      setConnected(false);
      // Delete old room
      try {
        await fetch("/api/delete-room", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ roomName: currentRoomName }),
        });
      } catch {}
      // Generate new room name
      const randomPart = generateRandomString(5);
      const newRoomName = `both-${settings.affiliateId}-${settings.familyId}-${settings.affiliateName}-${randomPart}`;
      // Fetch new token
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        params.append("roomName", newRoomName);
        params.append("participantName", settings.name);
        
        // Add metadata with the new fields
        const metadata = JSON.stringify({
          phoneNo: settings.phoneNo,
          clientID: settings.clientID,
          userID: settings.userID,
          affiliateId: settings.affiliateId,
          familyId: settings.familyId,
          affiliateName: settings.affiliateName,
          location: {
            latitude: userLocation.latitude,
            longitude: userLocation.longitude,
            accuracy: userLocation.accuracy
          }
        });
        params.append("metadata", metadata);
        
        const response = await fetch(`/api/token?${params}`);
        if (!response.ok) throw new Error(await response.text());
        const { accessToken } = await response.json();
        const wsUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL || "";
        setToken(accessToken);
        setUrl(wsUrl);
        setConnected(true);
        setCurrentRoomName(newRoomName);
      } catch (err: any) {
        setError(err.message || "Failed to connect");
        setConnected(false);
      } finally {
        setLoading(false);
      }
    }
  };

  function LivekitPreviewHooks({
    setAgentIsTyping,
    setLastAgentMessage,
    typingSpeed
  }: {
    setAgentIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
    setLastAgentMessage: React.Dispatch<React.SetStateAction<string>>;
    typingSpeed: 'slow' | 'normal' | 'fast';
  }) {
    const { chatMessages, send: sendChat } = useChat();
    const participants = useParticipants();
    const tracks = useTracks();
    // Track thinking state
    const [isThinking, setIsThinking] = useState(false);
    const lastUserMessageTime = useRef(0);
    const thinkingTimeout = useRef<NodeJS.Timeout | null>(null);
    const typingTimeout = useRef<NodeJS.Timeout | null>(null);
    
    // Find the agent's audio track
    const agentAudioTrack = tracks.find(
      (trackRef) =>
        trackRef.participant?.isAgent &&
        trackRef.publication?.kind === Track.Kind.Audio
    );
    // Use the correct track reference for transcription
    const transcription = useTrackTranscription(agentAudioTrack);

    // Monitor user message sends in the chat object
    useEffect(() => {
      if (chatMessages.length === 0) return;
      
      // Find the agent participant
      const agent = participants.find((p) => p.isAgent);
      
      // Process messages to determine if we should show "Thinking..."
      const lastUserMsg = [...chatMessages]
        .filter(m => m.from && (!agent || m.from.identity !== agent.identity))
        .sort((a, b) => b.timestamp - a.timestamp)[0];
      
      // Most recent agent message
      const lastAgentMsg = [...chatMessages]
        .filter(m => m.from && agent && m.from.identity === agent.identity)
        .sort((a, b) => b.timestamp - a.timestamp)[0];
      
      // If we have a user message
      if (lastUserMsg) {
        // If user message is more recent than last agent message or there's no agent message
        const isUserMostRecent = !lastAgentMsg || lastUserMsg.timestamp > lastAgentMsg.timestamp;
        
        if (isUserMostRecent) {
          // If this is a new user message, show thinking
          if (lastUserMsg.timestamp > lastUserMessageTime.current) {
            console.log("New user message, showing 'Thinking...'");
            lastUserMessageTime.current = lastUserMsg.timestamp;
            setIsThinking(true);
            
            // Auto-hide thinking after 30 seconds
            if (thinkingTimeout.current) {
              clearTimeout(thinkingTimeout.current);
            }
            thinkingTimeout.current = setTimeout(() => {
              console.log("Thinking timeout expired");
              setIsThinking(false);
            }, 30000);
          }
        } else {
          // Agent has already responded to this message
          setIsThinking(false);
        }
      }
    }, [chatMessages, participants]);

    // Check transcription for agent typing or speaking
    useEffect(() => {
      let hasNonFinal = false;
      let lastMsg = "";
      
      // Check if agent is typing (has non-final transcription)
      if (transcription && transcription.segments.length > 0) {
        const lastSeg = transcription.segments[transcription.segments.length - 1];
        if (!lastSeg.final && lastSeg.text) {
          hasNonFinal = true;
          lastMsg = lastSeg.text;
          
          // If agent is actively typing, clear thinking state
          if (isThinking) {
            console.log("Agent is typing, clearing 'Thinking...'");
            setIsThinking(false);
          }
        } else if (lastSeg.final && lastSeg.text) {
          lastMsg = lastSeg.text;
          // Final message, clear thinking state
          setIsThinking(false);
        }
      }
      
      // If no transcription but we have chat messages
      if (!lastMsg && chatMessages.length > 0) {
        const agent = participants.find((p) => p.isAgent);
        const lastAgentMsg = [...chatMessages].reverse().find((m) => m.from && m.from.identity === agent?.identity);
        
        if (lastAgentMsg) {
          lastMsg = lastAgentMsg.message;
          // Agent sent a message, clear thinking state
          setIsThinking(false);
        }
      }
      
      // Update the preview message
      if (isThinking && !hasNonFinal) {
        setLastAgentMessage("Thinking...");
      } else {
        setLastAgentMessage(lastMsg);
      }
      
      // Update typing indicator 
      if (hasNonFinal) {
        // Only set typing to true if we have meaningful text
        const hasTextContent = transcription.segments.some(s => !s.final && s.text.trim().length > 0);
        console.log("Agent typing detected:", { hasTextContent, hasNonFinal });
        setAgentIsTyping(hasTextContent);
      } else if (isThinking) {
        // Show typing indicator for thinking state too
        setAgentIsTyping(true);
      } else {
        // Debounce clearing the typing indicator
        if (typingTimeout.current) {
          clearTimeout(typingTimeout.current);
        }
        
        // Adjust debounce time based on typing speed
        let debounceTime = 1500; // Default (normal)
        if (typingSpeed === 'slow') {
          debounceTime = 2500; // Slower debounce
        } else if (typingSpeed === 'fast') {
          debounceTime = 800; // Faster debounce
        }
        
        typingTimeout.current = setTimeout(() => {
          setAgentIsTyping(false);
        }, debounceTime);
      }
      
      return () => {
        if (typingTimeout.current) {
          clearTimeout(typingTimeout.current);
          typingTimeout.current = null;
        }
      };
    }, [chatMessages, transcription, participants, setAgentIsTyping, setLastAgentMessage, typingSpeed, isThinking]);

    // When component unmounts
    useEffect(() => {
      return () => {
        if (thinkingTimeout.current) {
          clearTimeout(thinkingTimeout.current);
        }
      };
    }, []);

    return null;
  }

  // Animations
  const modalAnim = open ? "animate-fade-in-up" : "";
  const buttonAnim = !open ? "animate-fade-in" : "";

  return (
    <>
      {/* Floating button and preview (always show when not open) */}
      {!open && (
        <div className={`fixed bottom-6 right-6 z-50 flex flex-col items-end transition-all duration-300 ${buttonAnim}`}>
          {unreadCount > 0 && !agentIsTyping && (
            <div className="absolute -top-3 -right-3 bg-red-500 text-white rounded-full min-w-[20px] h-5 flex items-center justify-center text-xs font-bold px-1 z-10">
              {unreadCount > 99 ? '99+' : unreadCount}
            </div>
          )}
          {!connected && (
            <div className="mb-2">
              <div className={`rounded-md px-3 py-2 max-w-[320px] break-words bg-gray-900 border border-gray-800 text-${accentColor}-500 text-sm shadow-md`}>
                <div className="text-xs font-bold text-left mb-1 text-${accentColor}-400 tracking-wide">CHAT</div>
                <div className="whitespace-pre-line">Click to open chat and connect with an agent</div>
              </div>
            </div>
          )}
          {connected && agentIsTyping && (
            <div className={`bg-${accentColor}-700 text-white text-xs rounded-lg p-2 mb-2 shadow-lg`}>
              {lastAgentMessage === "Thinking..." ? "Thinking..." : "Agent is typing..."}
            </div>
          )}
          {connected && !agentIsTyping && lastAgentMessage && (
            <div className="mb-2">
              <div className={`rounded-md px-3 py-2 max-w-[320px] break-words bg-gray-900 border border-gray-800 text-${accentColor}-500 text-sm shadow-md`}>
                <div className="text-xs font-bold text-left mb-1 text-green-400 tracking-wide">AGENT</div>
                <div className="whitespace-pre-line">{removeMarkdownFormatting(lastAgentMessage)}</div>
              </div>
            </div>
          )}
          <button
            onClick={() => {
              setOpen(true);
              unreadRef.current = 0;
              setUnreadCount(0);
              lastReadTimestamp.current = Date.now();
            }}
            className={`w-14 h-14 rounded-full bg-${accentColor}-600 text-white shadow-xl flex items-center justify-center transition-transform hover:scale-110 focus:outline-none`}
            aria-label="Open chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </button>
        </div>
      )}

      {/* Main Widget when Open */}
      {open && (
        <div 
          className={`fixed bottom-0 right-0 z-50 w-full h-full max-w-full max-h-full shadow-2xl rounded-lg bg-white border border-gray-300 flex flex-col animate-fade-in-up transition-all duration-300 ${modalAnim}`}
          tabIndex={0}
          onFocus={() => setHasFocus(true)}
          onBlur={() => setHasFocus(false)}
        >
          <div className="flex justify-between items-center p-2 border-b border-gray-200">
            <button
              onClick={() => setOpen(false)}
              className="text-gray-500 hover:text-gray-900 focus:outline-none"
              aria-label="Close chat"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div className="flex items-center gap-2">
              {/* Typing Speed Dropdown - HIDDEN */}
              {/* <div className="flex items-center">
                <select
                  value={typingSpeed}
                  onChange={(e) => setTypingSpeed(e.target.value as 'slow' | 'normal' | 'fast')}
                  className="text-xs border border-gray-300 rounded px-1 py-0.5 bg-white"
                >
                  <option value="slow">Slow</option>
                  <option value="normal">Normal</option>
                  <option value="fast">Fast</option>
                </select>
                <span className="text-xs text-gray-500 ml-1">Speed</span>
              </div> */}
              <button
                onClick={connected ? handleDisconnect : handleConnect}
                className={`px-3 py-1 rounded text-white ${connected ? 'bg-red-500 hover:bg-red-600' : `bg-${accentColor}-600 hover:bg-${accentColor}-700 font-bold animate-pulse`} ${connected ? 'text-xs' : 'text-sm px-4 py-1.5'}`}
                disabled={loading}
              >
                {loading ? (connected ? 'Disconnecting...' : 'Connecting...') : (connected ? 'Disconnect' : 'Connect')}
              </button>
              {/* Settings icon - HIDDEN */}
              {/* <button
                onClick={() => setShowSettings((v) => !v)}
                className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-900 focus:outline-none"
                aria-label="Settings"
                type="button"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.01c1.527-.878 3.31.905 2.432 2.432a1.724 1.724 0 001.01 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.01 2.573c.878 1.527-.905 3.31-2.432 2.432a1.724 1.724 0 00-2.573 1.01c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.01c-1.527.878-3.31-.905-2.432-2.432a1.724 1.724 0 00-1.01-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.01-2.573c-.878-1.527.905-3.31 2.432-2.432.943.545 2.042-.454 1.497-1.397z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button> */}
              {/* Settings popover - HIDDEN */}
              {/* {showSettings && (
                <div ref={settingsRef} className="absolute top-10 right-2 bg-white border border-gray-300 rounded shadow-lg p-4 z-50 w-72">
                  <form onSubmit={handleSettingsUpdate} className="flex flex-col gap-2">
                    <label className="text-xs font-semibold">Affiliate ID
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.affiliateId} onChange={e => setSettings(s => ({...s, affiliateId: e.target.value}))} />
                    </label>
                    <label className="text-xs font-semibold">Family ID
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.familyId} onChange={e => setSettings(s => ({...s, familyId: e.target.value}))} />
                    </label>
                    <label className="text-xs font-semibold">Affiliate Name
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.affiliateName} onChange={e => setSettings(s => ({...s, affiliateName: e.target.value}))} />
                    </label>
                    <label className="text-xs font-semibold">Typing Speed
                      <select 
                        className="w-full border rounded px-2 py-1 mt-1 text-sm" 
                        value={settings.typingSpeed} 
                        onChange={e => setSettings(s => ({...s, typingSpeed: e.target.value as 'slow' | 'normal' | 'fast'}))}
                      >
                        <option value="slow">Slow</option>
                        <option value="normal">Normal</option>
                        <option value="fast">Fast</option>
                      </select>
                    </label>
                    <label className="text-xs font-semibold">Phone Number
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.phoneNo} onChange={e => setSettings(s => ({...s, phoneNo: e.target.value}))} />
                    </label>
                    <label className="text-xs font-semibold">User ID
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.userID} onChange={e => setSettings(s => ({...s, userID: e.target.value}))} />
                    </label>
                    <label className="text-xs font-semibold">Client ID
                      <input className="w-full border rounded px-2 py-1 mt-1 text-sm" value={settings.clientID} onChange={e => setSettings(s => ({...s, clientID: e.target.value}))} />
                    </label>
                    <button type="submit" className="mt-2 bg-green-600 hover:bg-green-700 text-white rounded px-3 py-1 text-sm font-semibold">Update</button>
                  </form>
                </div>
              )} */}
            </div>
          </div>
          
          <div className="flex-1 min-h-0 overflow-y-auto">
            {connected && token && url ? (
              <LiveKitRoom
                serverUrl={url}
                token={token}
                connect={connected}
                style={{ display: 'contents' }}
              >
                <LivekitPreviewHooks
                  setAgentIsTyping={setAgentIsTyping}
                  setLastAgentMessage={setLastAgentMessage}
                  typingSpeed={typingSpeed}
                />
                <LivekitWidget
                  affiliateId={affiliateId}
                  affiliateType="both"
                  familyId={familyId}
                  affiliateName={affiliateName}
                  name={name}
                  accentColor={accentColor}
                  connected={connected}
                  typingSpeed={typingSpeed}
                />
              </LiveKitRoom>
            ) : (
              <LivekitWidget
                affiliateId={affiliateId}
                affiliateType="both"
                familyId={familyId}
                affiliateName={affiliateName}
                name={name}
                accentColor={accentColor}
                connected={connected}
                typingSpeed={typingSpeed}
              />
            )}
          </div>
        </div>
      )}
      
      {/* LiveKit Room Component - Only mount when connected with valid credentials */}
      {token && url && connected && !open && (
        <LiveKitRoom
          serverUrl={url}
          token={token}
          connect={connected}
          style={{ display: 'contents' }}
        >
          <LivekitPreviewHooks
            setAgentIsTyping={setAgentIsTyping}
            setLastAgentMessage={setLastAgentMessage}
            typingSpeed={typingSpeed}
          />
        </LiveKitRoom>
      )}

      {/* Animations (tailwind or custom) */}
      <style jsx global>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-in-out;
        }
        .animate-fade-in-up {
          animation: fade-in-up 0.3s ease-in-out;
        }
      `}</style>
    </>
  );
}