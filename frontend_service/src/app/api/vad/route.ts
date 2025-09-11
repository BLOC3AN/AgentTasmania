import { NextRequest } from 'next/server';
import { WebSocketServer, WebSocket } from 'ws';

// Global WebSocket server instance
let wss: WebSocketServer | null = null;

// Initialize WebSocket server
function initWebSocketServer() {
  if (!wss) {
    wss = new WebSocketServer({ 
      port: 8080,
      perMessageDeflate: false 
    });

    wss.on('connection', (ws: WebSocket) => {
      console.log('🔌 New WebSocket connection established');
      
      // Send welcome message
      ws.send(JSON.stringify({
        type: 'connected',
        message: 'WebSocket VAD server connected'
      }));

      // Handle incoming messages
      ws.on('message', async (data: Buffer) => {
        try {
          const message = JSON.parse(data.toString());
          await handleWebSocketMessage(ws, message);
        } catch (error) {
          console.error('❌ WebSocket message error:', error);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Invalid message format'
          }));
        }
      });

      // Handle audio chunks (binary data)
      ws.on('message', async (data: Buffer) => {
        if (data.length > 100) { // Assume binary audio data
          await handleAudioChunk(ws, data);
        }
      });

      ws.on('close', () => {
        console.log('🔌 WebSocket connection closed');
      });

      ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
      });
    });

    console.log('🚀 WebSocket VAD server started on port 8080');
  }
}

// Handle WebSocket messages
async function handleWebSocketMessage(ws: WebSocket, message: { type: string; data?: unknown }) {
  console.log('📨 Received message:', message.type);

  switch (message.type) {
    case 'start_recording':
      ws.send(JSON.stringify({
        type: 'recording_started',
        message: 'VAD recording started'
      }));
      break;

    case 'stop_recording':
      ws.send(JSON.stringify({
        type: 'recording_stopped',
        message: 'VAD recording stopped'
      }));
      break;

    case 'audio_chunk':
      // Handle base64 encoded audio
      if (message.data) {
        const audioBuffer = Buffer.from(message.data, 'base64');
        await processAudioChunk(ws, audioBuffer);
      }
      break;

    case 'ping':
      ws.send(JSON.stringify({
        type: 'pong',
        timestamp: Date.now()
      }));
      break;

    default:
      ws.send(JSON.stringify({
        type: 'error',
        message: `Unknown message type: ${message.type}`
      }));
  }
}

// Handle binary audio chunks
async function handleAudioChunk(ws: WebSocket, audioData: Buffer) {
  console.log(`🎵 Received audio chunk: ${audioData.length} bytes`);
  
  try {
    // Process audio with VAD
    const vadResult = await processVAD(audioData);
    
    // Send VAD result back to client
    ws.send(JSON.stringify({
      type: 'vad_result',
      data: {
        isSpeech: vadResult.isSpeech,
        confidence: vadResult.confidence,
        timestamp: Date.now(),
        audioLength: audioData.length
      }
    }));

    // If speech detected, process for STT
    if (vadResult.isSpeech) {
      ws.send(JSON.stringify({
        type: 'speech_detected',
        message: 'Speech activity detected'
      }));
    }

  } catch (error) {
    console.error('❌ Audio processing error:', error);
    ws.send(JSON.stringify({
      type: 'error',
      message: 'Audio processing failed'
    }));
  }
}

// VAD processing function (placeholder for actual VAD implementation)
async function processVAD(audioData: Buffer): Promise<{isSpeech: boolean, confidence: number}> {
  // TODO: Implement actual VAD processing
  // For now, simulate VAD based on audio energy
  
  // Convert buffer to audio samples (assuming 16-bit PCM)
  const samples = new Int16Array(audioData.buffer, audioData.byteOffset, audioData.length / 2);
  
  // Calculate RMS energy
  let sum = 0;
  for (let i = 0; i < samples.length; i++) {
    sum += samples[i] * samples[i];
  }
  const rms = Math.sqrt(sum / samples.length);
  const normalizedRMS = rms / 32768; // Normalize to 0-1
  
  // Simple threshold-based VAD
  const threshold = 0.01;
  const isSpeech = normalizedRMS > threshold;
  const confidence = Math.min(normalizedRMS / threshold, 1.0);
  
  console.log(`🎤 VAD: RMS=${normalizedRMS.toFixed(4)}, Speech=${isSpeech}, Confidence=${confidence.toFixed(2)}`);
  
  return {
    isSpeech,
    confidence
  };
}

// Process audio chunk for STT
async function processAudioChunk(ws: WebSocket, audioData: Buffer) {
  console.log(`🔄 Processing audio chunk: ${audioData.length} bytes`);
  
  try {
    // TODO: Implement actual STT processing
    // For now, simulate STT response
    
    setTimeout(() => {
      ws.send(JSON.stringify({
        type: 'transcription',
        data: {
          text: `Demo transcription at ${new Date().toLocaleTimeString()}`,
          confidence: 0.95,
          isFinal: true
        }
      }));
    }, 500);

  } catch (error) {
    console.error('❌ STT processing error:', error);
    ws.send(JSON.stringify({
      type: 'error',
      message: 'STT processing failed'
    }));
  }
}

// HTTP GET handler - for WebSocket upgrade
export async function GET() {
  // Initialize WebSocket server if not already done
  initWebSocketServer();
  
  return new Response(JSON.stringify({
    message: 'WebSocket VAD server is running on port 8080',
    endpoint: 'ws://localhost:8080',
    status: 'ready'
  }), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

// HTTP POST handler - for direct audio processing
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File;
    
    if (!audioFile) {
      return new Response(JSON.stringify({
        error: 'No audio file provided'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const audioBuffer = Buffer.from(await audioFile.arrayBuffer());
    console.log(`📤 Received audio file: ${audioBuffer.length} bytes`);

    // Process with VAD
    const vadResult = await processVAD(audioBuffer);
    
    // TODO: If speech detected, process with STT
    let transcription = null;
    if (vadResult.isSpeech) {
      transcription = {
        text: `Demo transcription from file at ${new Date().toLocaleTimeString()}`,
        confidence: 0.95
      };
    }

    return new Response(JSON.stringify({
      vad: vadResult,
      transcription: transcription,
      audioLength: audioBuffer.length,
      timestamp: Date.now()
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('❌ POST processing error:', error);
    return new Response(JSON.stringify({
      error: 'Audio processing failed'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
