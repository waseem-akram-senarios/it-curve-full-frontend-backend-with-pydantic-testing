import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Image from "next/image";
import Head from "next/head";
import { BackToHome } from "@/components/BackToHome";
import { 
  LiveKitRoom, 
  useChat, 
  useParticipants, 
  useTracks, 
  useLocalParticipant, 
  useTrackTranscription,
  VideoTrack,
  BarVisualizer,
  useVoiceAssistant,
  RoomAudioRenderer,
  StartAudio,
  TrackToggle,
  useConnectionState
} from "@livekit/components-react";
import { ConnectionState, Track, LocalTrack, createLocalAudioTrack } from "livekit-client";
import { AudioInputTile } from "@/components/config/AudioInputTile";
import { PlaygroundDeviceSelector } from "@/components/playground/PlaygroundDeviceSelector";
import { PlaygroundTile } from "@/components/playground/PlaygroundTile";
import { TranscriptionTile } from "@/transcriptions/TranscriptionTile";
import { Button } from "@/components/button/Button";
import { LoadingSVG } from "@/components/button/LoadingSVG";

// Define SpeechRecognition for TypeScript
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: ((event: Event) => void) | null;
}

// Define SpeechRecognition constructor
interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}

// Define browser-specific SpeechRecognition
declare global {
  var SpeechRecognition: SpeechRecognitionConstructor | undefined;
  var webkitSpeechRecognition: SpeechRecognitionConstructor | undefined;
}

// Define chat message type
type ChatMessage = {
  name: string;
  message: string;
  timestamp: number;
  isSelf: boolean;
  isTyping?: boolean;
};

// Connection parameter types
type ConnectionParams = {
  token: string;
  url: string;
  roomName: string;
  participantName: string;
  accentColor: string;
  connect: boolean;
};

// Form parameter types
type FormParams = {
  affiliateId: string;
  affiliateType?: string; // Optional, will use "both" by default
  familyId: string;
  affiliateName: string;
  phoneNo?: string;
  userID?: string;
  clientID?: string;
};

// Function to generate random alphanumeric string for room names
const generateRandomString = (length: number): string => {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  const charactersLength = characters.length;
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
};

// Component to handle transcription
const TranscriptionHandler = ({ 
  transcription, 
  onMessageUpdate,
  typingSpeed = 'normal' // Add typingSpeed parameter with default 'normal'
}: { 
  transcription: any;
  onMessageUpdate: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  typingSpeed?: 'slow' | 'normal' | 'fast'; // Add typing speed option
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
            m.name === "Alina" && 
            m.message === latestFinalSegment.text
          );
          
          if (!finalExists) {
            nonTypingMessages.push({
              name: "Alina",
              message: latestFinalSegment.text,
              timestamp: Date.now(),
              isSelf: false
            });
          }
        }
        
        // Add typing indicator if there is one with a fixed message
        if (latestTypingSegment) {
          // Use a larger chunk of text for faster typing speed
          let textLength = 80; // Default for normal speed
          if (typingSpeed === 'slow') {
            textLength = 40; // Show less text per update for slower typing
          } else if (typingSpeed === 'fast') {
            textLength = 200; // Show more text per update for faster typing
          }
          
          // Using a consistent typing message helps prevent scroll jumping
          return [...nonTypingMessages, {
            name: "Alina",
            message: latestTypingSegment.text.substr(0, textLength), // Adjust length based on speed
            timestamp: Date.now(),
            isSelf: false,
            isTyping: true
          }].sort((a: ChatMessage, b: ChatMessage) => a.timestamp - b.timestamp);
        }
        
        return nonTypingMessages.sort((a: ChatMessage, b: ChatMessage) => a.timestamp - b.timestamp);
      });
    } catch (error) {
      console.error('[bot-chat] Error processing transcription segments:', error);
    }
  }, [transcription?.segments, onMessageUpdate, typingSpeed]);

  return null;
};

// Connection form overlay component
const ConnectionForm = ({ onConnect, accentColor }: { onConnect: (params: FormParams) => void, accentColor: string }) => {
  const [formParams, setFormParams] = useState<FormParams>({
    affiliateId: "65",
    affiliateType: "both", // Fixed as "both"
    familyId: "3",
    affiliateName: "",
    phoneNo: "",
    userID: "",
    clientID: ""
  });
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConnect(formParams);
  };
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormParams(prev => ({ ...prev, [name]: value }));
  };
  
  return (
    <div className="absolute inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-8 shadow-2xl max-w-md w-full border border-gray-800">
        <h2 className="text-2xl font-bold mb-6 text-green-400 text-center">Connect to Chat</h2>
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Affiliate ID</label>
            <input
              type="text"
              name="affiliateId"
              value={formParams.affiliateId}
              onChange={handleChange}
              required
              placeholder="Enter Affiliate ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Family ID</label>
            <input
              type="text"
              name="familyId"
              value={formParams.familyId}
              onChange={handleChange}
              required
              placeholder="Enter Family ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Affiliate Name</label>
            <input
              type="text"
              name="affiliateName"
              value={formParams.affiliateName}
              onChange={handleChange}
              required
              placeholder="Enter Affiliate Name"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
            <input
              type="text"
              name="phoneNo"
              value={formParams.phoneNo || ""}
              onChange={handleChange}
              placeholder="Enter Phone Number"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">User ID</label>
            <input
              type="text"
              name="userID"
              value={formParams.userID || ""}
              onChange={handleChange}
              placeholder="Enter User ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Client ID</label>
            <input
              type="text"
              name="clientID"
              value={formParams.clientID || ""}
              onChange={handleChange}
              placeholder="Enter Client ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <button 
            type="submit"
            className={`w-full bg-${accentColor}-600 hover:bg-${accentColor}-500 text-white rounded-md py-3 font-medium text-lg mt-6 transition-colors duration-200`}
          >
            Connect
          </button>
        </form>
      </div>
    </div>
  );
};

// Header component with connect/disconnect button
const ChatHeader = ({ 
  accentColor, 
  onConnectClicked,
  onSettingsClicked,
  typingSpeed,
  onTypingSpeedChange
}: { 
  accentColor: string;
  onConnectClicked: () => void;
  onSettingsClicked: () => void;
  typingSpeed: 'slow' | 'normal' | 'fast';
  onTypingSpeedChange: (speed: 'slow' | 'normal' | 'fast') => void;
}) => {
  const roomState = useConnectionState();
  
  return (
    <div className={`flex gap-4 py-4 px-6 text-${accentColor}-500 justify-between items-center shrink-0 border-b border-gray-800`}>
      <div className="flex items-center gap-3">
        <div className="text-white text-lg font-semibold">Chat with Assistant</div>
      </div>
      <div className="flex justify-end items-center gap-2">
        {/* Typing Speed Control */}
        <div className="flex items-center mr-2">
          <span className="text-xs text-gray-400 mr-2">Typing Speed:</span>
          <select 
            value={typingSpeed}
            onChange={(e) => onTypingSpeedChange(e.target.value as 'slow' | 'normal' | 'fast')}
            className="bg-gray-800 text-white text-xs rounded px-2 py-1 border border-gray-700"
          >
            <option value="slow">Slow</option>
            <option value="normal">Normal</option>
            <option value="fast">Fast</option>
          </select>
        </div>
        <button
          onClick={onSettingsClicked}
          className="p-2 rounded-md hover:bg-gray-800"
          title="Settings"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
        </button>
        <Button
          accentColor={
            roomState === ConnectionState.Connected ? "red" : accentColor
          }
          disabled={roomState === ConnectionState.Connecting}
          onClick={onConnectClicked}
        >
          {roomState === ConnectionState.Connecting ? (
            <LoadingSVG />
          ) : roomState === ConnectionState.Connected ? (
            "Disconnect"
          ) : (
            "Connect"
          )}
        </Button>
      </div>
    </div>
  );
};

// Settings Modal component
const SettingsModal = ({ 
  isOpen, 
  onClose, 
  onSave,
  accentColor,
  currentSettings
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onSave: (settings: FormParams) => void;
  accentColor: string;
  currentSettings: {
    affiliateId: string;
    affiliateType: string;
    familyId: string;
    affiliateName: string;
    phoneNo: string;
    userID: string;
    clientID: string;
  };
}) => {
  const [settings, setSettings] = useState({
    ...currentSettings
  });

  useEffect(() => {
    if (isOpen) {
      setSettings({
        ...currentSettings
      });
    }
  }, [isOpen, currentSettings]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Always set affiliateType to "both" regardless of what was in the form
    onSave({...settings, affiliateType: "both"});
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-8 shadow-xl max-w-md w-full border border-gray-800">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Connection Settings</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Affiliate ID</label>
            <input
              type="text"
              name="affiliateId"
              value={settings.affiliateId}
              onChange={handleChange}
              required
              placeholder="Enter Affiliate ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Family ID</label>
            <input
              type="text"
              name="familyId"
              value={settings.familyId}
              onChange={handleChange}
              required
              placeholder="Enter Family ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Affiliate Name</label>
            <input
              type="text"
              name="affiliateName"
              value={settings.affiliateName}
              onChange={handleChange}
              required
              placeholder="Enter Affiliate Name"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
            <input
              type="text"
              name="phoneNo"
              value={settings.phoneNo}
              onChange={handleChange}
              placeholder="Enter Phone Number"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">User ID</label>
            <input
              type="text"
              name="userID"
              value={settings.userID}
              onChange={handleChange}
              placeholder="Enter User ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Client ID</label>
            <input
              type="text"
              name="clientID"
              value={settings.clientID}
              onChange={handleChange}
              placeholder="Enter Client ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-md px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
          
          <div className="flex justify-end gap-3 mt-6">
            <button 
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md"
            >
              Cancel
            </button>
            <button 
              type="submit"
              className={`px-4 py-2 bg-${accentColor}-600 hover:bg-${accentColor}-500 text-white rounded-md`}
            >
              Update & Reconnect
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Chat component with LiveKit integration
const LiveChat = ({ accentColor, chatKey, typingSpeed = 'fast' }: { accentColor: string; chatKey: number; typingSpeed?: 'slow' | 'normal' | 'fast' }) => {
  const voiceAssistant = useVoiceAssistant();
  return (
    <div className="w-full h-full flex flex-col">
      <PlaygroundTile 
        title="Chat" 
        className="h-full w-full chat-custom flex-1"
      >
        <TranscriptionTile 
          key={chatKey}
          agentAudioTrack={voiceAssistant.audioTrack} 
          accentColor={accentColor}
          typingSpeed={typingSpeed}
        />
      </PlaygroundTile>
    </div>
  );
};

// Wrapper component for the chat interface
const ChatInterface = ({ 
  accentColor, 
  onDisconnect,
  isConnected,
  messages,
  chatKey,
  onSettingsUpdate,
  currentSettings,
  typingSpeed,
  onTypingSpeedChange
}: { 
  accentColor: string;
  onDisconnect: () => void;
  isConnected: boolean;
  messages: ChatMessage[];
  chatKey: number;
  onSettingsUpdate: (settings: FormParams) => void;
  currentSettings: {
    affiliateId: string;
    affiliateType: string;
    familyId: string;
    affiliateName: string;
    phoneNo: string;
    userID: string;
    clientID: string;
  };
  typingSpeed: 'slow' | 'normal' | 'fast';
  onTypingSpeedChange: (speed: 'slow' | 'normal' | 'fast') => void;
}) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleSettingsClick = () => {
    setIsSettingsOpen(true);
  };

  return (
    <div className="flex flex-col h-full w-full">
      <ChatHeader 
        accentColor={accentColor} 
        onConnectClicked={onDisconnect}
        onSettingsClicked={handleSettingsClick}
        typingSpeed={typingSpeed}
        onTypingSpeedChange={onTypingSpeedChange}
      />
      <div className="flex-1 flex w-full overflow-hidden">
        {/* Left side - Video and Audio */}
        <div className="w-1/2 flex flex-col bg-gray-950 p-6">
          <div className="flex flex-col h-full w-full gap-4">
            {/* Visualization Tile */}
            <div className="flex-1 w-full border border-gray-800 rounded-sm bg-black relative">
              <div className="h-full w-full flex items-center justify-center bg-black">
                <video 
                  src="/preview(1).mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>
            
            {/* Audio Tile */}
            <div className="h-36 w-full border border-gray-800 rounded-sm bg-gray-900 flex items-center justify-center">
              <AudioControlsContainer />
            </div>
          </div>
        </div>
        
        {/* Right side - Chat */}
        <div className="w-1/2 flex flex-col">
          <LiveChat accentColor={accentColor} chatKey={chatKey} typingSpeed={typingSpeed} />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSave={onSettingsUpdate}
        accentColor={accentColor}
        currentSettings={currentSettings}
      />
    </div>
  );
};

export default function BotChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageInput, setMessageInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const accentColor = "green";
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [chatKey, setChatKey] = useState(0);
  // Set the typing speed - change this to modify transcription typing speed
  const [typingSpeed, setTypingSpeed] = useState<'slow' | 'normal' | 'fast'>('fast');
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
  
  // Store current connection settings
  const [currentSettings, setCurrentSettings] = useState<{
    affiliateId: string;
    affiliateType: string;
    familyId: string;
    affiliateName: string;
    phoneNo: string;
    userID: string;
    clientID: string;
  }>({
    affiliateId: "65",
    affiliateType: "both",
    familyId: "3",
    affiliateName: "ARMON",
    phoneNo: "",
    userID: "",
    clientID: ""
  });
  
  // Connection parameters
  const [connectionParams, setConnectionParams] = useState<ConnectionParams>({
    token: "",
    url: "",
    roomName: "",
    participantName: "",
    accentColor: accentColor,
    connect: false
  });

  // Get user location when component mounts
  useEffect(() => {
    const getUserLocation = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const { latitude, longitude, accuracy } = position.coords;
            console.log('User location:', { 
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
            console.error('Geolocation error:', error.message);
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

  // Simple scroll to bottom that always executes
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'auto' });
    }
  }, [messages]);

  // Function to fetch LiveKit token
  const fetchToken = async (roomName: string, participantName: string): Promise<{ token: string, url: string }> => {
    console.log('[bot-chat] Fetching token for:', { roomName, participantName });
    const params = new URLSearchParams();
    params.append('roomName', roomName);
    params.append('participantName', participantName);
    
    // Add metadata with all required fields including location
    const metadata = JSON.stringify({
      phoneNo: currentSettings.phoneNo,
      clientID: currentSettings.clientID,
      userID: currentSettings.userID,
      affiliateId: currentSettings.affiliateId,
      familyId: currentSettings.familyId,
      affiliateName: currentSettings.affiliateName
    });
    params.append('metadata', metadata);
    
    try {
      const response = await fetch(`/api/token?${params}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch token: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      const { accessToken } = await response.json();
      console.log('[bot-chat] Token received successfully');
      
      const url = process.env.NEXT_PUBLIC_LIVEKIT_URL || "";
      if (!url) {
        throw new Error("LiveKit URL not configured. Please check your environment variables.");
      }
      
      return { token: accessToken, url };
    } catch (error) {
      console.error("[bot-chat] Token fetch error:", error);
      throw error;
    }
  };

  // Handle form submission
  const handleConnect = async (params: FormParams) => {
    try {
      setLoading(true);
      
      // Update stored settings
      setCurrentSettings({
        affiliateId: params.affiliateId,
        affiliateType: "both", // Always set to "both"
        familyId: params.familyId,
        affiliateName: params.affiliateName,
        phoneNo: params.phoneNo || "",
        userID: params.userID || "",
        clientID: params.clientID || ""
      });
      
      // Generate room name with affiliateName, always using "both" for affiliateType
      const randomPart = generateRandomString(5);
      const roomName = `both-${params.affiliateId}-${params.familyId}-${params.affiliateName}-${randomPart}`;
      // Fetch token
      const { token, url } = await fetchToken(roomName, params.affiliateName);
      
      // If already connected, disconnect first
      if (isConnected) {
        setConnectionParams(prev => ({
          ...prev,
          token: "",
          url: "",
          roomName: "",
          connect: false
        }));
        setMessages([]);
        
        // Small delay to ensure disconnect completes before reconnecting
        setTimeout(() => {
          setConnectionParams({
            token,
            url,
            roomName,
            participantName: params.affiliateName,
            accentColor,
            connect: true
          });
          setIsConnected(true);
          setChatKey(prev => prev + 1); // Force remount
        }, 500);
      } else {
        // First time connecting
        setConnectionParams({
          token,
          url,
          roomName,
          participantName: params.affiliateName,
          accentColor,
          connect: true
        });
        setIsConnected(true);
      }
      
      setLoading(false);
    } catch (error) {
      console.error("Connection error:", error);
      setError("Failed to connect. Please try again.");
      setLoading(false);
    }
  };

  const handleConnectClick = () => {
    if (!isConnected) {
      handleConnect({
        affiliateId: currentSettings.affiliateId,
        affiliateType: "both", // Always set to "both" regardless of what's in currentSettings
        familyId: currentSettings.familyId,
        affiliateName: currentSettings.affiliateName,
        phoneNo: currentSettings.phoneNo,
        userID: currentSettings.userID,
        clientID: currentSettings.clientID
      });
    } else {
      setConnectionParams(prev => ({
        ...prev,
        token: "",
        url: "",
        roomName: "",
        connect: false
      }));
      setIsConnected(false);
      setMessages([]);
      setChatKey(prev => prev + 1); // Increment chatKey to force remount
    }
  };

  return (
    <>
      <Head>
        <title>Chat with Assistant</title>
        <meta name="description" content="Chat with our AI assistant" />
      </Head>
      
      {/* <BackToHome /> */}
      
      <div className="flex flex-col h-screen bg-gray-900 text-white">
        {loading && (
          <div className="absolute inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
            <div className="text-white flex flex-col items-center">
              <div className="mb-4">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500"></div>
              </div>
              <div>Connecting...</div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
            <div className="bg-gray-900 rounded-lg p-6 shadow-xl max-w-md w-full">
              <h2 className="text-xl font-semibold mb-4 text-red-500 text-center">Error</h2>
              <p className="text-white text-center mb-4">{error}</p>
              <button 
                onClick={() => {
                  setError("");
                }}
                className={`w-full bg-${accentColor}-700 hover:bg-${accentColor}-600 text-white rounded-md py-2 font-medium`}
              >
                Try Again
              </button>
            </div>
          </div>
        )}
        
        {/* Debug section - collapsible */}
        {/* <details className="bg-gray-800 border-b border-gray-700 p-2 text-xs">
          <summary className="cursor-pointer font-medium">Debug Info - Metadata Sent to LiveKit</summary>
          <div className="mt-2 p-2 bg-gray-900 rounded overflow-auto">
            <pre className="text-green-400 whitespace-pre-wrap">
              {JSON.stringify({
                phoneNo: currentSettings.phoneNo,
                clientID: currentSettings.clientID,
                userID: currentSettings.userID,
                affiliateId: currentSettings.affiliateId,
                familyId: currentSettings.familyId,
                affiliateName: currentSettings.affiliateName
              }, null, 2)}
            </pre>
          </div>
        </details> */}
        
        <main className="flex flex-1 overflow-hidden">
          <LiveKitRoom
            style={{
              width: '100%',
              display: 'flex'
            }}
            serverUrl={connectionParams.url}
            token={connectionParams.token}
            connect={connectionParams.connect}
            onDisconnected={() => {
              setIsConnected(false);
            }}
            onError={(e) => {
              console.error("LiveKit connection error:", e);
              setError(`Connection error: ${e.message}`);
            }}
          >
            <ChatInterface 
              accentColor={accentColor}
              onDisconnect={handleConnectClick}
              isConnected={isConnected}
              messages={messages}
              chatKey={chatKey}
              onSettingsUpdate={(settings) => {
                handleConnect(settings);
              }}
              currentSettings={currentSettings}
              typingSpeed={typingSpeed}
              onTypingSpeedChange={(speed) => {
                setTypingSpeed(speed);
              }}
            />
            <RoomAudioRenderer />
            <StartAudio label="Click to enable audio" />
          </LiveKitRoom>
        </main>
        
        {/* Footer with company logo */}
        <footer className="p-4 bg-white border-t border-gray-800 flex items-center">
          <div className="container mx-auto flex justify-between items-center">
            {/* Logo on the left */}
            <div className="w-32">
              <Image 
                src="/logo.png" 
                alt="Company Logo" 
                width={164} 
                height={32} 
                className="w-full h-auto"
              />
            </div>
            
            {/* Text in the middle */}
            <div className="text-center text-gray-700 text-2xl font-bold">
              It listens, It learns, It takes decisions. The future is here
            </div>
            
            {/* Empty div for balance */}
            <div className="w-32"></div>
          </div>
        </footer>
      </div>
    </>
  );
} 

// Modify the AudioVisualizerContainer to become AudioControlsContainer
const AudioControlsContainer = () => {
  const { localParticipant } = useLocalParticipant();
  const tracks = useTracks();
  
  // Find local microphone track
  const localMicTrack = tracks.find(
    (trackRef) => 
      trackRef.source === Track.Source.Microphone &&
      trackRef.participant === localParticipant
  );
  
  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex justify-between items-center py-2 px-4 text-xs uppercase tracking-wider border-b border-gray-800">
        <h3>Microphone</h3>
        <div className="flex items-center gap-2">
          <TrackToggle
            className="px-2 py-1 bg-gray-900 text-gray-300 border border-gray-800 rounded-sm hover:bg-gray-800"
            source={Track.Source.Microphone}
          />
          <PlaygroundDeviceSelector kind="audioinput" />
        </div>
      </div>
      <div className="flex-1 px-4 py-2">
        {localMicTrack ? (
          <AudioInputTile trackRef={localMicTrack} />
        ) : (
          <div className="flex items-center justify-center text-gray-700 text-center w-full h-full">
            Enable microphone to see audio levels
          </div>
        )}
      </div>
    </div>
  );
}; 