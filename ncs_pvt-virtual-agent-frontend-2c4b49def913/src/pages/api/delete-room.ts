import { NextApiRequest, NextApiResponse } from 'next';
import { RoomServiceClient } from 'livekit-server-sdk';

const apiKey = process.env.LIVEKIT_API_KEY!;
const apiSecret = process.env.LIVEKIT_API_SECRET!;
const livekitHost = process.env.NEXT_PUBLIC_LIVEKIT_URL!;

const roomService = new RoomServiceClient(livekitHost, apiKey, apiSecret);

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  const { roomName } = req.body;
  if (!roomName) {
    return res.status(400).json({ error: 'Missing roomName' });
  }
  try {
    await roomService.deleteRoom(roomName);
    return res.status(200).json({ success: true });
  } catch (e) {
    return res.status(500).json({ error: (e as Error).message });
  }
} 