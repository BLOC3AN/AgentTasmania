import { NextRequest, NextResponse } from 'next/server';

// TTS API endpoint that connects to the TTS Service
// Use internal Docker network URL for server-side requests
const TTS_SERVICE_URL = 'http://tts:8007';

export async function POST(request: NextRequest) {
  try {
    // Parse the request body
    const body = await request.json();
    
    // Validate required fields
    if (!body.text || typeof body.text !== 'string') {
      return NextResponse.json(
        { error: 'Text is required and must be a string' },
        { status: 400 }
      );
    }

    // Forward the request to TTS service
    const ttsResponse = await fetch(`${TTS_SERVICE_URL}/synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: body.text,
        voice: body.voice || 'coral',
        response_format: body.response_format || 'mp3',
        speed: body.speed || 1.0
      }),
    });

    if (!ttsResponse.ok) {
      console.error('TTS service error:', ttsResponse.status, ttsResponse.statusText);
      return NextResponse.json(
        { error: `TTS service error: ${ttsResponse.status}` },
        { status: ttsResponse.status }
      );
    }

    // Get the audio blob from TTS service
    const audioBlob = await ttsResponse.blob();
    
    // Return the audio blob with proper headers
    return new NextResponse(audioBlob, {
      status: 200,
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': audioBlob.size.toString(),
      },
    });

  } catch (error) {
    console.error('TTS API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Health check endpoint
export async function GET() {
  try {
    const healthResponse = await fetch(`${TTS_SERVICE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 seconds
    });

    const ttsHealthy = healthResponse.ok;

    return NextResponse.json({
      status: 'TTS API is running',
      tts_service: ttsHealthy ? 'connected' : 'disconnected',
      timestamp: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({
      status: 'TTS API is running',
      tts_service: 'disconnected',
      timestamp: new Date().toISOString(),
    });
  }
}
