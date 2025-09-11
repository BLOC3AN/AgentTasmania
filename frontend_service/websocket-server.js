const WebSocket = require('ws');
const http = require('http');

// External ASR Configuration
// const EXTERNAL_ASR_URL = 'wss://gxza5pgzegfdme-3000.proxy.runpod.net/ws/asr';
const EXTERNAL_ASR_URL = 'wss://s6rou7ayi3jrzc-3000.proxy.runpod.net/ws/asr';
const USE_EXTERNAL_ASR = true; // Set to false to use local processing only

// Transcription Management
class TranscriptionManager {
  constructor() {
    this.debounceMap = new Map(); // clientId -> { timer, candidates }
    this.DEBOUNCE_DELAY = 2000; // 2 seconds for complete speech collection
    this.MIN_CONFIDENCE = 0.7; // Minimum confidence threshold
    this.MEANINGFUL_SINGLE_WORDS = [
      'yes', 'no', 'hello', 'hi', 'thanks', 'thank', 'please', 'sorry',
      'okay', 'ok', 'stop', 'start', 'help', 'cancel'
    ];
    this.COMMON_ASR_HALLUCINATIONS = [
      'kathryn', 'catherine', 'we\'ll see you', 'thank you thank you',
      'bye bye bye', 'see you next time', 'next week'
    ];
  }

  isValidTranscription(text, confidence = 0.9) {
    if (!text?.trim()) return { valid: false, reason: 'empty' };

    const trimmed = text.trim();
    const words = trimmed.split(/\s+/).filter(w => w.length > 0);

    // Filter punctuation-only
    if (/^[.,!?;:\s]*$/.test(trimmed)) {
      return { valid: false, reason: 'punctuation-only' };
    }

    // Length validation
    if (trimmed.length > 300) {
      return { valid: false, reason: 'too-long' };
    }

    // Word count validation with exceptions
    if (words.length < 2) {
      const isMeaningful = this.MEANINGFUL_SINGLE_WORDS.includes(trimmed.toLowerCase());
      if (!isMeaningful) {
        return { valid: false, reason: 'single-word-not-meaningful' };
      }
    }

    // Repetition detection
    if (words.length > 10) {
      const repetitionCheck = this.checkRepetition(trimmed, words);
      if (!repetitionCheck.valid) {
        return repetitionCheck;
      }
    }

    return { valid: true, score: this.calculateScore(trimmed, words, confidence) };
  }

  checkRepetition(text, words) {
    // BEST PRACTICE: Advanced repetition detection for ASR spam patterns

    // Method 1: Word frequency analysis (catches "KATHRYN KATHRYN KATHRYN...")
    const wordCounts = {};
    words.forEach(word => {
      const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
      if (cleanWord.length > 1) { // Count all meaningful words
        wordCounts[cleanWord] = (wordCounts[cleanWord] || 0) + 1;
      }
    });

    // Strict repetition detection
    for (const [word, count] of Object.entries(wordCounts)) {
      const frequency = count / words.length;

      // Reject if any word appears more than 3 times OR >25% frequency
      if (count > 3 || frequency > 0.25) {
        return { valid: false, reason: `word-spam: "${word}" appears ${count}/${words.length} times (${Math.round(frequency * 100)}%)` };
      }
    }

    // Method 2: Check for ASR hallucination patterns
    const lowerText = text.toLowerCase();
    for (const hallucination of this.COMMON_ASR_HALLUCINATIONS) {
      if (lowerText.includes(hallucination)) {
        return { valid: false, reason: `asr-hallucination: contains "${hallucination}"` };
      }
    }

    // Method 3: Pattern repetition (like "The KATHRYN The KATHRYN...")
    if (words.length > 6) {
      for (let patternLength = 2; patternLength <= 3; patternLength++) {
        for (let i = 0; i <= Math.min(words.length - patternLength, 3); i++) {
          const pattern = words.slice(i, i + patternLength).join(' ').toLowerCase();
          if (pattern.length > 4) {
            const regex = new RegExp(pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            const matches = (text.match(regex) || []).length;
            if (matches > 2) { // Stricter: >2 occurrences is spam
              return { valid: false, reason: `pattern-spam: "${pattern}" repeats ${matches} times` };
            }
          }
        }
      }
    }

    // Method 4: Sentence-level repetition
    const sentences = text.split(/[.!?]+/).filter(s => s.trim());
    if (sentences.length > 2) {
      const firstSentence = sentences[0].trim().toLowerCase();
      if (firstSentence.length > 3) {
        const repetitions = sentences.filter(s => s.trim().toLowerCase() === firstSentence).length;
        if (repetitions > 2) { // Stricter: >2 identical sentences is spam
          return { valid: false, reason: `sentence-spam: "${firstSentence}" repeats ${repetitions} times` };
        }
      }
    }

    return { valid: true };
  }

  calculateScore(text, words, confidence) {
    // BEST PRACTICE: Quality-based scoring that penalizes repetition

    let score = 0;

    // Base score: Moderate word count bonus (not excessive)
    score += Math.min(words.length * 5, 100); // Capped at 100 for word count

    // Confidence bonus
    score += confidence * 50; // Reduced weight

    // Quality bonuses
    if (text.match(/[.!?]$/)) score += 30; // Complete sentence
    if (words.length >= 3 && words.length <= 15) score += 20; // Natural length

    // PENALTY for repetitive patterns
    const wordCounts = {};
    words.forEach(word => {
      const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');
      if (cleanWord.length > 1) {
        wordCounts[cleanWord] = (wordCounts[cleanWord] || 0) + 1;
      }
    });

    // Heavy penalty for word repetition
    for (const count of Object.values(wordCounts)) {
      if (count > 2) {
        score -= (count - 2) * 50; // -50 points per extra repetition
      }
    }

    // Penalty for excessive length (likely spam)
    if (words.length > 20) {
      score -= (words.length - 20) * 10;
    }

    return Math.max(score, 0); // Never negative
  }

  addCandidate(clientId, text, confidence = 0.9, isFinal = false) {
    // TEMPORARY: Allow partial results for UI display, but still apply filtering
    if (!isFinal) {
      console.log(`⏳ Processing partial: "${text.substring(0, 30)}${text.length > 30 ? '...' : ''}" (partial for UI)`);
    }

    // Apply confidence threshold
    if (confidence < this.MIN_CONFIDENCE) {
      console.log(`🔇 Low confidence: ${confidence} < ${this.MIN_CONFIDENCE} - "${text.substring(0, 30)}${text.length > 30 ? '...' : ''}"`);
      return false;
    }

    const validation = this.isValidTranscription(text, confidence);

    if (!validation.valid) {
      console.log(`🔇 Filtered: ${validation.reason} - "${text.substring(0, 30)}${text.length > 30 ? '...' : ''}"`);
      return false;
    }

    if (!this.debounceMap.has(clientId)) {
      this.debounceMap.set(clientId, { timer: null, candidates: [] });
    }

    const entry = this.debounceMap.get(clientId);

    // Calculate quality-based score
    const words = text.trim().split(/\s+/);
    const score = this.calculateScore(text, words, confidence);
    entry.candidates.push({ text, confidence, score, isFinal, timestamp: Date.now() });

    console.log(`📝 Added FINAL candidate: "${text}" (score: ${score}, confidence: ${confidence})`);

    // Clear existing timer
    if (entry.timer) {
      clearTimeout(entry.timer);
    }

    // Set extended timer for complete speech collection
    entry.timer = setTimeout(() => {
      this.sendBestCandidate(clientId);
    }, this.DEBOUNCE_DELAY);

    return true;
  }

  sendBestCandidate(clientId) {
    const entry = this.debounceMap.get(clientId);
    if (!entry || entry.candidates.length === 0) return;

    // Find best candidate (highest score)
    const bestCandidate = entry.candidates.reduce((best, current) =>
      current.score > best.score ? current : best
    );

    console.log(`📝 Sending best transcription: "${bestCandidate.text}" (score: ${bestCandidate.score})`);

    // Send to client (will be implemented in the calling code)
    this.onBestTranscription?.(clientId, bestCandidate);

    // Clear candidates
    entry.candidates = [];
    entry.timer = null;
  }

  cleanup(clientId) {
    const entry = this.debounceMap.get(clientId);
    if (entry?.timer) {
      clearTimeout(entry.timer);
    }
    this.debounceMap.delete(clientId);
  }
}

const transcriptionManager = new TranscriptionManager();

// Create HTTP server
const server = http.createServer();

// Create WebSocket server
const wss = new WebSocket.Server({ 
  server,
  perMessageDeflate: false 
});

console.log('🚀 Starting WebSocket VAD Server...');

// VAD processing function
function processVAD(audioData) {
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
    confidence,
    rms: normalizedRMS
  };
}

// Create WAV file from PCM data
function createWAVFromPCM(pcmData) {
  const sampleRate = 16000;
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * bitsPerSample / 8;
  const blockAlign = numChannels * bitsPerSample / 8;

  const wavHeader = Buffer.alloc(44);

  // RIFF header
  wavHeader.write('RIFF', 0);
  wavHeader.writeUInt32LE(36 + pcmData.length, 4);
  wavHeader.write('WAVE', 8);

  // fmt chunk
  wavHeader.write('fmt ', 12);
  wavHeader.writeUInt32LE(16, 16); // chunk size
  wavHeader.writeUInt16LE(1, 20); // audio format (PCM)
  wavHeader.writeUInt16LE(numChannels, 22);
  wavHeader.writeUInt32LE(sampleRate, 24);
  wavHeader.writeUInt32LE(byteRate, 28);
  wavHeader.writeUInt16LE(blockAlign, 32);
  wavHeader.writeUInt16LE(bitsPerSample, 34);

  // data chunk
  wavHeader.write('data', 36);
  wavHeader.writeUInt32LE(pcmData.length, 40);

  return Buffer.concat([wavHeader, pcmData]);
}

// Handle WebSocket connections
wss.on('connection', (ws) => {
  console.log('🔌 New WebSocket connection established');

  // External ASR connection for this client
  let externalASR = null;
  let audioBuffer = [];
  let isRecording = false;

  // Create unique client ID
  const clientId = Date.now() + '_' + Math.random().toString(36).substring(2, 11);

  // Setup transcription callback
  transcriptionManager.onBestTranscription = (clientId, candidate) => {
    ws.send(JSON.stringify({
      type: 'transcription',
      data: {
        text: candidate.text,
        confidence: candidate.confidence,
        isFinal: true,
        source: 'external_asr'
      }
    }));
  };



  // Initialize external ASR connection if enabled
  if (USE_EXTERNAL_ASR) {
    initializeExternalASR();
  }

  function initializeExternalASR() {
    try {
      console.log('� Connecting to external ASR service...');
      externalASR = new WebSocket(EXTERNAL_ASR_URL);

      externalASR.on('open', () => {
        console.log('✅ Connected to external ASR service');
        // Send ping to verify connection
        externalASR.send(JSON.stringify({ type: 'ping' }));
      });

      externalASR.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());

          // Forward transcription results to client with FINAL-ONLY policy
          if (message.type === 'transcription' || message.type === 'result') {
            const text = message.text || message.transcript || '';
            console.log("🚀 ~ initializeExternalASR ~ text:", text)
            const confidence = message.confidence || 0.9;
            const isFinal = message.is_final || message.isFinal || message.final || false;

            // Only process final transcriptions
            transcriptionManager.addCandidate(clientId, text, confidence, isFinal);
          } else if (message.type === 'pong') {
            console.log('🏓 External ASR pong received');
          }
        } catch (error) {
          console.error('❌ Error parsing external ASR response:', error);
        }
      });

      externalASR.on('error', (error) => {
        console.error('❌ External ASR error:', error.message);
        // Fallback to local processing
        ws.send(JSON.stringify({
          type: 'error',
          message: 'External ASR service unavailable, using local processing'
        }));
      });

      externalASR.on('close', () => {
        console.log('🔌 External ASR connection closed');
        externalASR = null;
      });

    } catch (error) {
      console.error('❌ Failed to initialize external ASR:', error);
    }
  }

  // Send welcome message
  ws.send(JSON.stringify({
    type: 'connected',
    message: 'WebSocket VAD server connected',
    external_asr: USE_EXTERNAL_ASR ? 'enabled' : 'disabled',
    timestamp: Date.now()
  }));

  // Handle incoming messages
  ws.on('message', async (data) => {
    try {
      // Check if it's binary audio data
      if (data instanceof Buffer && data.length > 100) {
        // Handle binary audio chunk
        const vadResult = processVAD(data);

        // Send VAD result back to client (for real-time feedback)
        ws.send(JSON.stringify({
          type: 'vad_result',
          data: {
            isSpeech: vadResult.isSpeech,
            confidence: vadResult.confidence,
            rms: vadResult.rms,
            timestamp: Date.now(),
            audioLength: data.length
          }
        }));

        // If speech detected, send speech detection event
        if (vadResult.isSpeech) {
          ws.send(JSON.stringify({
            type: 'speech_detected',
            message: 'Speech activity detected',
            timestamp: Date.now()
          }));

          // Start recording if not already recording
          if (!isRecording) {
            isRecording = true;
            audioBuffer = [];
            console.log('🎤 Started recording audio for external ASR');
          }
        }

        // Collect audio data for external ASR processing
        if (isRecording) {
          audioBuffer.push(data);

          // Send audio chunk to external ASR if connected
          if (externalASR && externalASR.readyState === WebSocket.OPEN) {
            try {
              // Convert audio buffer to WAV format for external ASR
              const wavData = createWAVFromPCM(data);
              const base64Audio = wavData.toString('base64');

              externalASR.send(JSON.stringify({
                type: 'audio',
                data: base64Audio
              }));

              console.log(`📤 Sent audio chunk to external ASR (${data.length} bytes)`);
            } catch (error) {
              console.error('❌ Error sending audio to external ASR:', error);
            }
          }
        }
        
      } else {
        // Handle JSON messages
        const message = JSON.parse(data.toString());

        // Handle audio-related commands only
        if (message.type === 'stop_recording' && isRecording) {
          isRecording = false;
          console.log('🛑 Stopped recording, processing complete audio...');

          // Send complete audio buffer to external ASR
          if (externalASR && externalASR.readyState === WebSocket.OPEN && audioBuffer.length > 0) {
            try {
              // Combine all audio chunks
              const completeAudio = Buffer.concat(audioBuffer);
              const wavData = createWAVFromPCM(completeAudio);
              const base64Audio = wavData.toString('base64');

              externalASR.send(JSON.stringify({
                type: 'audio',
                data: base64Audio
              }));

              console.log(`📤 Sent complete audio to external ASR (${completeAudio.length} bytes)`);

              // Clear buffer
              audioBuffer = [];

            } catch (error) {
              console.error('❌ Error sending complete audio to external ASR:', error);

              // Fallback to local transcription
              ws.send(JSON.stringify({
                type: 'transcription',
                data: {
                  text: `Local transcription - ${audioBuffer.length} audio chunks processed`,
                  confidence: 0.8,
                  isFinal: true,
                  source: 'local_fallback'
                }
              }));
            }
          }
        } else if (message.type === 'ping') {
          // Handle ping for audio connection health check
          await handleWebSocketMessage(ws, message);
        } else {
          // Ignore non-audio messages (text messages should not come through WebSocket)
          console.log(`ℹ️ Ignoring non-audio message: ${message.type}`);
        }
      }
      
    } catch (error) {
      console.error('❌ WebSocket message error:', error);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Message processing failed',
        error: error.message
      }));
    }
  });

  ws.on('close', () => {
    console.log('🔌 WebSocket connection closed');

    // Clean up external ASR connection
    if (externalASR) {
      externalASR.close();
      externalASR = null;
    }

    // Clear buffers
    audioBuffer = [];
    isRecording = false;

    // Clean up transcription manager
    transcriptionManager.cleanup(clientId);
  });

  ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
  });
});

// Handle WebSocket JSON messages (Audio-only processing)
async function handleWebSocketMessage(ws, message) {
  console.log('📨 Received audio message:', message.type);

  switch (message.type) {
    case 'ping':
      ws.send(JSON.stringify({
        type: 'pong',
        timestamp: Date.now()
      }));
      break;

    default:
      // Only log unknown audio-related messages, don't send error responses
      console.log(`ℹ️ Ignoring non-audio message type: ${message.type}`);
  }
}

// Start server
const PORT = 8080;
server.listen(PORT, () => {
  console.log(`✅ WebSocket VAD Server running on port ${PORT}`);
  console.log(`🔗 WebSocket endpoint: ws://localhost:${PORT}`);
  console.log('🎤 Ready to process voice activity detection!');
});

// Handle server shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down WebSocket VAD Server...');
  wss.close(() => {
    server.close(() => {
      console.log('✅ Server shutdown complete');
      process.exit(0);
    });
  });
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});
