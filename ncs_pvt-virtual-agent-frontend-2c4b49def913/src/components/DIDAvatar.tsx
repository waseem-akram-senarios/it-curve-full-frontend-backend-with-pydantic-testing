import React, { useState, useEffect, useRef } from 'react';

// Fix for RTCSessionDescription compatibility
declare global {
  interface Window {
    RTCSessionDescription: any;
  }
}

interface DIDProps {
  isConnected: boolean;
  messages: {
    name: string;
    message: string;
    timestamp: number;
    isSelf: boolean;
    isTyping?: boolean;
  }[];
  avatarUrl?: string;
  driverUrl?: string;
}

// A selection of default avatar URLs from D-ID
const DEFAULT_AVATARS: Record<string, string> = {
  // Female presenters
  noelle: 's3://d-id-images-prod/google-oauth2|106378151444740979126/img_kbUFtOdPe2y8iqYCThWo1/Shakeel_Sial_generate_avatar_of_the_provided_image_that_can_bli_ee562308-085c-434f-b283-0a00c7c4de7c.png',
  natalie: 'https://d-id-public-bucket.s3.us-west-2.amazonaws.com/alice.jpg',
  grace: 'https://create-images-results.d-id.com/DefaultPresenters/grace_f_ai/image.jpeg',
  // Male presenters
  daniel: 'https://create-images-results.d-id.com/DefaultPresenters/Daniel_m_ai/image.jpeg',
  marcus: 'https://create-images-results.d-id.com/DefaultPresenters/Marcus_m_ai/image.jpeg',
  ethan: 'https://create-images-results.d-id.com/DefaultPresenters/Ethan_m_ai/image.jpeg',
};

// A selection of drivers to control avatar movement
const DRIVERS: Record<string, string> = {
  natural1: 'bank://natural/driver-1',
  natural2: 'bank://natural/driver-2',
  lively1: 'bank://lively/driver-01',
  lively2: 'bank://lively/driver-02',
  subtle1: 'bank://subtle/driver-01',
  subtle2: 'bank://subtle/driver-02',
};

// D-ID authorization header
const AUTHORIZATION = `Basic YVc1bWIwQnBkR04xY25abGN5NXVaWFE6Yzg4ZlM3VVRIS0liVV9Gd3VuOUJm`;

const DIDAvatar: React.FC<DIDProps> = ({ 
  isConnected, 
  messages, 
  avatarUrl = 'grace',
  driverUrl = 'lively1'
}) => {
  const [streamId, setStreamId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const lastProcessedMessageRef = useRef<number>(-1);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  
  // Get the actual avatar URL from the lookup table
  const getAvatarUrl = (key: string): string => {
    return DEFAULT_AVATARS[key] || DEFAULT_AVATARS.noelle;
  };
  
  // Get the actual driver URL from the lookup table
  const getDriverUrl = (key: string): string => {
    return DRIVERS[key] || DRIVERS.lively1;
  };
  
  // Initialize WebRTC stream on component mount
  useEffect(() => {
    if (!isConnected) return;
    
    let isMounted = true;
    
    const initStream = async () => {
      try {
        setLoading(true);
        // Create a talk stream with D-ID
        const actualAvatarUrl = getAvatarUrl(avatarUrl);
        const actualDriverUrl = getDriverUrl(driverUrl);
        
        console.log('Initializing D-ID stream with:', {
          avatarUrl: actualAvatarUrl,
          driverUrl: actualDriverUrl
        });
        
        const response = await fetch('https://api.d-id.com/talks/streams', {
          method: 'POST',
          headers: {
            'Authorization': AUTHORIZATION,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            source_url: actualAvatarUrl,
            driver_url: actualDriverUrl,
            config: {
              fluent: false,
              align_driver: true,
              auto_match: true,
              stitch: true,
            },
            voice_config: {
              provider: { type: 'microsoft', voice_id: 'en-US-AriaNeural' }
            }
          })
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`D-ID API error: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('D-ID Stream Response:', data);
        
        if (!isMounted) return;
        
        // Get session_id from the response body
        if (!data.session_id) {
          throw new Error('No session_id received from D-ID API');
        }
        
        setStreamId(data.id);
        setSessionId(data.session_id);
        
        // Initialize WebRTC connection after stream is created
        if (videoRef.current) {
          // Create a new RTCPeerConnection using the ice servers from the response
          const peerConnection = new RTCPeerConnection({
            iceServers: data.ice_servers,
          });
          
          peerConnectionRef.current = peerConnection;
          
          // When we get ICE candidates, send them to D-ID
          peerConnection.onicecandidate = async (event) => {
            if (!event.candidate || !data.id || !data.session_id) return;
            
            try {
              const iceCandidateResponse = await fetch(`https://api.d-id.com/talks/streams/${data.id}/ice`, {
                method: 'POST',
                headers: {
                  'Authorization': AUTHORIZATION,
                  'Content-Type': 'application/json',
                  'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                  candidate: event.candidate,
                  session_id: data.session_id 
                }),
              });
              
              if (!iceCandidateResponse.ok) {
                console.error('ICE candidate error:', await iceCandidateResponse.text());
              }
            } catch (error) {
              console.error('Error sending ICE candidate:', error);
            }
          };
          
          // When we receive tracks, add them to the video element
          peerConnection.ontrack = (event) => {
            if (videoRef.current && event.streams[0]) {
              videoRef.current.srcObject = event.streams[0];
              videoRef.current.onloadedmetadata = () => {
                if (videoRef.current) {
                  videoRef.current.play().catch(err => {
                    console.error('Error playing video:', err);
                  });
                  if (isMounted) {
                    setLoading(false);
                  }
                }
              };
            }
          };
          
          // Set the remote description from the D-ID offer
          await peerConnection.setRemoteDescription({
            type: 'offer',
            sdp: data.offer.sdp,
          });
          
          // Create an answer
          const answer = await peerConnection.createAnswer();
          await peerConnection.setLocalDescription(answer);
          
          // Send the answer to D-ID
          const sdpResponse = await fetch(`https://api.d-id.com/talks/streams/${data.id}/sdp`, {
            method: 'POST',
            headers: {
              'Authorization': AUTHORIZATION,
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            body: JSON.stringify({ 
              answer: answer,
              session_id: data.session_id
            }),
          });
          
          if (!sdpResponse.ok) {
            const sdpErrorText = await sdpResponse.text();
            console.error('SDP response error:', sdpErrorText);
            throw new Error('Failed to establish connection with D-ID');
          }
          
          // Wait a moment for the connection to stabilize
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          if (!isMounted) return;
          
          // Start with an idle animation after connection is established
          await sendTextToStream(data.id, data.session_id, "My name is Alina. What can I do for you today?");
        }
      } catch (err) {
        console.error('Error initializing D-ID stream:', err);
        if (isMounted) {
          setError(`Avatar initialization error: ${err instanceof Error ? err.message : String(err)}`);
          setLoading(false);
        }
      }
    };
    
    initStream();
    
    // Cleanup function
    return () => {
      isMounted = false;
      
      if (streamId && sessionId) {
        // Delete the stream
        fetch(`https://api.d-id.com/talks/streams/${streamId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': AUTHORIZATION,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            session_id: sessionId
          })
        }).catch(error => console.error('Error deleting stream:', error));
      }
      
      // Close peer connection
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }
    };
  }, [isConnected, avatarUrl, driverUrl]);
  
  // Helper function to send text to the stream
  const sendTextToStream = async (id: string, sessionId: string, text: string) => {
    try {
      console.log('Sending text to stream:', { id, text });
      
      const response = await fetch(`https://api.d-id.com/talks/streams/${id}`, {
        method: 'POST',
        headers: {
          'Authorization': AUTHORIZATION,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          script: {
            type: 'text',
            input: text,
            provider: { type: 'microsoft', voice_id: 'en-US-AriaNeural' }
          },
          session_id: sessionId
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error streaming text:', errorText);
      }
    } catch (err) {
      console.error('Error sending text to D-ID stream:', err);
    }
  };
  
  // Process new messages and send them to D-ID
  useEffect(() => {
    if (!streamId || !sessionId || messages.length === 0) return;
    
    const processNewMessages = async () => {
      const lastIndex = messages.length - 1;
      // Only process if there's a new message and it's from the bot
      if (
        lastIndex > lastProcessedMessageRef.current &&
        !messages[lastIndex].isSelf &&
        !messages[lastIndex].isTyping
      ) {
        try {
          // Send the message to D-ID
          await sendTextToStream(streamId, sessionId, messages[lastIndex].message);
          lastProcessedMessageRef.current = lastIndex;
        } catch (err) {
          console.error('Error sending message to D-ID:', err);
        }
      }
    };
    
    processNewMessages();
  }, [messages, streamId, sessionId]);
  
  if (!isConnected) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-4xl font-bold text-green-400">
          AI Assistant
        </div>
      </div>
    );
  }
  
  return (
    <div className="w-full h-full flex items-center justify-center rounded-lg overflow-hidden">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10 bg-black bg-opacity-50">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500"></div>
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-10 bg-black bg-opacity-70">
          <div className="text-red-500 text-center p-4 max-w-md">
            <p className="text-lg font-semibold mb-2">Error</p>
            <p className="break-words">{error}</p>
          </div>
        </div>
      )}
      
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={false}
        className={`w-full h-full object-cover ${loading ? 'opacity-0' : 'opacity-100'}`}
        style={{ transition: 'opacity 0.5s' }}
      />
    </div>
  );
};

export default DIDAvatar; 