import { useVoiceAssistant } from "@livekit/components-react";
import { TranscriptionTile } from "@/transcriptions/TranscriptionTile";

interface LivekitWidgetProps {
  affiliateId: string;
  affiliateType: string;
  familyId: string;
  affiliateName: string;
  name: string;
  accentColor?: string;
  typingSpeed?: 'slow' | 'normal' | 'fast';
}

const defaultAccentColor = "green";

// Version with LiveKit hooks - only used when connected
function ConnectedWidgetContent({ 
  accentColor, 
  typingSpeed = 'normal' 
}: { 
  accentColor: string,
  typingSpeed: 'slow' | 'normal' | 'fast'
}) {
  const voiceAssistant = useVoiceAssistant();
  const agentAudioTrack = voiceAssistant?.audioTrack;
  const agent = voiceAssistant?.agent;

  if (!agent) {
    return <div className="text-center text-gray-400 mt-8">Waiting for agent to connect...</div>;
  }

  return (
    <TranscriptionTile 
      agentAudioTrack={agentAudioTrack} 
      accentColor={accentColor} 
      typingSpeed={typingSpeed}
    />
  );
}

// Disconnected version that doesn't use LiveKit hooks
function DisconnectedWidgetContent() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="bg-gray-100 rounded-lg p-6 shadow-inner text-gray-600 max-w-sm">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <p className="text-lg font-semibold mb-2">Not Connected</p>
        <p className="text-sm">Click the Connect button above to start a chat with an agent.</p>
      </div>
    </div>
  );
}

function LivekitWidgetContent({ 
  accentColor, 
  connected, 
  typingSpeed = 'normal' 
}: { 
  accentColor: string, 
  connected: boolean,
  typingSpeed: 'slow' | 'normal' | 'fast'
}) {
  if (!connected) {
    return <DisconnectedWidgetContent />;
  }
  
  return <ConnectedWidgetContent accentColor={accentColor} typingSpeed={typingSpeed} />;
}

export function LivekitWidget({
  affiliateId,
  affiliateType,
  familyId,
  affiliateName,
  name,
  accentColor = defaultAccentColor,
  connected = true,
  typingSpeed = 'normal',
}: LivekitWidgetProps & { connected?: boolean }) {
  return (
    <div className="w-full h-full flex flex-col border rounded shadow bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-gray-50">
        <div className="font-bold text-lg">Chat with Assistant</div>
      </div>
      {/* Main content */}
      <div className="flex-1 flex flex-col p-2 overflow-y-auto">
        <LivekitWidgetContent 
          accentColor={accentColor} 
          connected={connected} 
          typingSpeed={typingSpeed}
        />
      </div>
    </div>
  );
}

export default LivekitWidget; 