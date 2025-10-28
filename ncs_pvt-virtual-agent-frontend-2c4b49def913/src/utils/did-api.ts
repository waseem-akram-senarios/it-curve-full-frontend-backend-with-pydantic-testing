// D-ID API integration utilities

const D_ID_API_URL = 'https://api.d-id.com';
// The authorization header should be properly Base64 encoded
const AUTHORIZATION = `Basic ZFcxaGNpNWhiR2xBYzJWdVlYSnBiM011YkdsMlpROk5NSXhSdEQxZk5abUNaUzJSM2s5Nw==`;

// Interface for the response from D-ID API
export interface DIDTalkResponse {
  id: string;
  object: string;
  created_at?: string;
  status: string;
  result_url?: string;
  source_url?: string;
}

// Interface for stream response
export interface DIDStreamResponse {
  id: string;
  offer: {
    type: string;
    sdp: string;
  };
  ice_servers: Array<{
    urls: string[];
    username?: string;
    credential?: string;
  }>;
  session_id: string;
}

// Create a talk session with D-ID
export async function createTalk(source_url: string, text: string, driver_url: string = 'bank://lively/driver-01'): Promise<DIDTalkResponse> {
  try {
    const response = await fetch(`${D_ID_API_URL}/talks`, {
      method: 'POST',
      headers: {
        'Authorization': AUTHORIZATION,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        source_url,
        script: {
          type: 'text',
          input: text,
          subtitles: false,
          provider: { type: 'microsoft', voice_id: 'en-US-AriaNeural' }
        },
        driver_url,
        config: {
          fluent: false,
          align_driver: true,
          auto_match: true,
        },
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error creating D-ID talk:', error);
    throw error;
  }
}

// Get a specific talk by ID
export async function getTalk(talkId: string, sessionId?: string): Promise<DIDTalkResponse> {
  try {
    const headers: HeadersInit = {
      'Authorization': AUTHORIZATION,
      'Accept': 'application/json'
    };
    
    if (sessionId) {
      headers['Cookie'] = sessionId;
    }
    
    const response = await fetch(`${D_ID_API_URL}/talks/${talkId}`, {
      headers
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error getting D-ID talk:', error);
    throw error;
  }
}

// Create a talk stream with D-ID (for realtime streaming)
export async function createTalkStream(source_url: string, driver_url: string = 'bank://lively/driver-01'): Promise<DIDStreamResponse> {
  try {
    const response = await fetch(`${D_ID_API_URL}/talks/streams`, {
      method: 'POST',
      headers: {
        'Authorization': AUTHORIZATION,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        source_url,
        driver_url,
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
    
    return await response.json();
  } catch (error) {
    console.error('Error creating D-ID talk stream:', error);
    throw error;
  }
}

// Send text to a talk stream
export async function streamText(streamId: string, text: string, sessionId?: string): Promise<void> {
  try {
    const headers: HeadersInit = {
      'Authorization': AUTHORIZATION,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    
    if (sessionId) {
      headers['Cookie'] = sessionId;
    }
    
    const response = await fetch(`${D_ID_API_URL}/talks/streams/${streamId}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        script: {
          type: 'text',
          input: text,
          provider: { type: 'microsoft', voice_id: 'en-US-AriaNeural' }
        }
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
  } catch (error) {
    console.error('Error streaming text to D-ID talk:', error);
    throw error;
  }
}

// Delete a talk stream when done
export async function deleteTalkStream(streamId: string, sessionId?: string): Promise<void> {
  try {
    const headers: HeadersInit = {
      'Authorization': AUTHORIZATION,
      'Accept': 'application/json'
    };
    
    if (sessionId) {
      headers['Cookie'] = sessionId;
    }
    
    const response = await fetch(`${D_ID_API_URL}/talks/streams/${streamId}`, {
      method: 'DELETE',
      headers
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
  } catch (error) {
    console.error('Error deleting D-ID talk stream:', error);
    throw error;
  }
}

// Send ICE candidate to D-ID
export async function sendIceCandidate(streamId: string, candidate: RTCIceCandidate, sessionId?: string): Promise<void> {
  try {
    const headers: HeadersInit = {
      'Authorization': AUTHORIZATION,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    
    if (sessionId) {
      headers['Cookie'] = sessionId;
    }
    
    const response = await fetch(`${D_ID_API_URL}/talks/streams/${streamId}/ice`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ candidate })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
  } catch (error) {
    console.error('Error sending ICE candidate to D-ID:', error);
    throw error;
  }
}

// Send SDP to D-ID
export async function sendSDP(streamId: string, sdp: RTCSessionDescriptionInit, sessionId?: string): Promise<any> {
  try {
    const headers: HeadersInit = {
      'Authorization': AUTHORIZATION,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    
    if (sessionId) {
      headers['Cookie'] = sessionId;
    }
    
    const response = await fetch(`${D_ID_API_URL}/talks/streams/${streamId}/sdp`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ sdp })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`D-ID API error: ${errorText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending SDP to D-ID:', error);
    throw error;
  }
} 