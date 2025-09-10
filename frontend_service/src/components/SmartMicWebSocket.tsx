'use client';

import { useState, useEffect, useRef } from 'react';

interface SmartMicWebSocketProps {
  onTranscription: (text: string) => void;
  isActive: boolean;
  onStatusChange: (status: 'idle' | 'listening' | 'processing' | 'speaking') => void;
}

export default function SmartMicWebSocket({ onTranscription, isActive, onStatusChange }: SmartMicWebSocketProps) {
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [audioLevel, setAudioLevel] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeechDetected, setIsSpeechDetected] = useState(false);
  const [vadConfidence, setVadConfidence] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [permissionStatus, setPermissionStatus] = useState<'unknown' | 'granted' | 'denied'>('unknown');
  const [lastTranscription, setLastTranscription] = useState<string>('');

  // WebSocket and audio refs
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const isRecordingRef = useRef(false);
  const silenceStartRef = useRef<number | null>(null);
  const lastSpeechTimeRef = useRef<number | null>(null);
  const recordingStartTimeRef = useRef<number | null>(null);

  // Prevent duplicate transcriptions
  const lastFinalTranscriptionRef = useRef<string>('');
  const transcriptionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Constants from smart_mic.py
  const SILENCE_DURATION = 1000; // 1 second
  const MIN_RECORDING_TIME = 500; // 0.5 seconds
  const WEBSOCKET_URL = 'ws://localhost:8080'; // Local WebSocket server with external ASR integration

  useEffect(() => {
    if (isActive) {
      initializeWebSocketVAD();
    } else {
      cleanup();
    }

    return () => {
      cleanup();
    };
  }, [isActive]);

  const initializeWebSocketVAD = async () => {
    try {
      console.log('🔌 Initializing WebSocket VAD...');
      
      // Connect to WebSocket server
      await connectWebSocket();
      
      // Initialize audio capture
      await initializeAudioCapture();
      
      onStatusChange('listening');
      console.log('✅ WebSocket VAD initialized successfully!');
      
    } catch (error) {
      console.error('❌ WebSocket VAD initialization failed:', error);
      onStatusChange('idle');
      setConnectionStatus('disconnected');
    }
  };

  const connectWebSocket = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      try {
        setConnectionStatus('connecting');
        
        const ws = new WebSocket(WEBSOCKET_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('✅ WebSocket connected');
          setConnectionStatus('connected');
          
          // Send ping to test connection
          ws.send(JSON.stringify({
            type: 'ping',
            timestamp: Date.now()
          }));
          
          resolve();
        };

        ws.onmessage = (event) => {
          handleWebSocketMessage(JSON.parse(event.data));
        };

        ws.onclose = () => {
          console.log('🔌 WebSocket disconnected');
          setConnectionStatus('disconnected');
        };

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          setConnectionStatus('disconnected');
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  };

  const handleWebSocketMessage = (message: any) => {
    console.log('📨 WebSocket message:', message.type);

    switch (message.type) {
      case 'connected':
        console.log('🎉 Server connected:', message.message);
        break;

      case 'vad_result':
        const { isSpeech, confidence } = message.data;
        setIsSpeechDetected(isSpeech);
        setVadConfidence(confidence);
        
        if (isSpeech) {
          lastSpeechTimeRef.current = Date.now();
          silenceStartRef.current = null;
          
          // Auto-start recording if not already recording
          if (!isRecordingRef.current) {
            startRecording();
          }
        } else {
          // Check for auto-stop condition
          if (isRecordingRef.current && lastSpeechTimeRef.current) {
            const silenceDuration = Date.now() - lastSpeechTimeRef.current;
            const recordingDuration = recordingStartTimeRef.current ? 
              Date.now() - recordingStartTimeRef.current : 0;

            if (silenceDuration >= SILENCE_DURATION && recordingDuration >= MIN_RECORDING_TIME) {
              console.log(`🔇 Auto-stopping: ${silenceDuration}ms silence, ${recordingDuration}ms total`);
              stopRecording();
            }
          }
        }
        break;

      case 'speech_detected':
        console.log('🎤 Server detected speech');
        break;

      case 'transcription':
        const { text, isFinal, source } = message.data;
        console.log('📝 Transcription received:', text, `(${source || 'unknown'})`, isFinal ? '[FINAL]' : '[PARTIAL]');

        // Update local transcription display (show partial results)
        setLastTranscription(text);

        // Only send to parent component when transcription is final and different from last
        if (isFinal && text.trim().length > 0) {
          // Check if this is a duplicate of the last final transcription
          if (lastFinalTranscriptionRef.current === text.trim()) {
            console.log('🚫 Duplicate final transcription ignored:', text);
            return;
          }

          // Clear any existing timeout
          if (transcriptionTimeoutRef.current) {
            clearTimeout(transcriptionTimeoutRef.current);
          }

          console.log('✅ Final transcription confirmed:', text);
          lastFinalTranscriptionRef.current = text.trim();
          onTranscription(text);
          onStatusChange('speaking');

          // Clear transcription after showing result
          transcriptionTimeoutRef.current = setTimeout(() => {
            setLastTranscription('');
            onStatusChange('idle');
            lastFinalTranscriptionRef.current = ''; // Reset for next transcription
            console.log('🎧 Ready for next voice input...');
          }, 3000);
        } else if (!isFinal) {
          // For partial results, just update the display without triggering parent callback
          console.log('⏳ Partial transcription (not sending to parent):', text);
        }
        break;

      case 'pong':
        console.log('🏓 Pong received');
        break;

      case 'error':
        console.error('❌ Server error:', message.message);
        break;

      default:
        console.log('❓ Unknown message type:', message.type);
    }
  };

  const initializeAudioCapture = async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000, // 16kHz for VAD
          channelCount: 1
        }
      });

      mediaStreamRef.current = stream;

      // Setup Web Audio API
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      
      // Create analyser for visual feedback
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;
      source.connect(analyser);

      // Create script processor for real-time audio processing
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      
      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        
        // Update audio level for UI
        updateAudioLevel();
        
        // Send audio chunk to WebSocket server
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          sendAudioChunk(inputData);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      console.log('✅ Audio capture initialized');

    } catch (error) {
      console.error('❌ Audio capture failed:', error);
      throw error;
    }
  };

  const updateAudioLevel = () => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    analyser.getByteFrequencyData(dataArray);
    
    // Calculate RMS
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      const value = dataArray[i] / 255.0;
      sum += value * value;
    }
    const rms = Math.sqrt(sum / bufferLength);
    setAudioLevel(rms * 100);
  };

  const sendAudioChunk = (audioData: Float32Array) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    // Convert Float32 to Int16 for VAD processing
    const int16Array = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      int16Array[i] = Math.max(-32768, Math.min(32767, audioData[i] * 32768));
    }

    // Send as binary data
    wsRef.current.send(int16Array.buffer);
  };

  const startRecording = () => {
    if (isRecordingRef.current) return;

    console.log('🎤 Starting recording...');
    isRecordingRef.current = true;
    recordingStartTimeRef.current = Date.now();
    setIsRecording(true);
    onStatusChange('listening');

    // Notify server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'start_recording',
        timestamp: Date.now()
      }));
    }
  };

  const stopRecording = () => {
    if (!isRecordingRef.current) return;

    console.log('🔇 Stopping recording...');
    isRecordingRef.current = false;
    setIsRecording(false);
    onStatusChange('processing');

    // Notify server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'stop_recording',
        timestamp: Date.now()
      }));
    }

    // Reset timing refs
    recordingStartTimeRef.current = null;
    lastSpeechTimeRef.current = null;
    silenceStartRef.current = null;
  };

  const cleanup = () => {
    console.log('🧹 Cleaning up WebSocket VAD...');

    // Clear any pending timeouts
    if (transcriptionTimeoutRef.current) {
      clearTimeout(transcriptionTimeoutRef.current);
      transcriptionTimeoutRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop audio processing
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    // Reset states
    setConnectionStatus('disconnected');
    setAudioLevel(0);
    setIsRecording(false);
    setIsSpeechDetected(false);
    setVadConfidence(0);
    setError(null);
    setPermissionStatus('unknown');
    setLastTranscription('');
    isRecordingRef.current = false;
    lastFinalTranscriptionRef.current = '';
    onStatusChange('idle');
  };

  return (
    <div className="text-center">
      {/* Error Display */}
      {error && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-red-800 text-sm font-medium mb-2">⚠️ Error</div>
          <div className="text-red-700 text-xs">{error}</div>
          {permissionStatus === 'denied' && (
            <div className="mt-2 text-xs text-red-600">
              💡 Please click the microphone icon in your browser&apos;s address bar and allow access
            </div>
          )}
        </div>
      )}

      {/* Connection Status */}
      <div className="mb-2">
        <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
          connectionStatus === 'connected' ? 'bg-green-100 text-green-800' :
          connectionStatus === 'connecting' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          {connectionStatus === 'connected' && '🟢 WebSocket Connected'}
          {connectionStatus === 'connecting' && '🟡 Connecting...'}
          {connectionStatus === 'disconnected' && '🔴 Disconnected'}
        </div>
      </div>

      {/* Enhanced Status Display */}
      <div className="mb-4 text-center">
        {isRecording ? (
          <div className="space-y-2">
            <div className="text-green-600 font-medium text-lg">
              🎤 Recording...
            </div>
            <div className="text-sm text-green-500">
              Speak now • Will auto-stop after 1s silence
            </div>
            <div className="flex justify-center">
              <div className="animate-pulse bg-red-500 rounded-full w-3 h-3"></div>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-blue-600 font-medium text-lg">
              🎧 Ready to Listen
            </div>
            <div className="text-sm text-blue-500">
              Start speaking to begin recording automatically
            </div>
            <div className="text-xs text-gray-400">
              WebSocket VAD • External ASR Integration
            </div>
          </div>
        )}
      </div>

      {/* Enhanced Audio Visualization */}
      <div className="mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex justify-center items-end space-x-1 h-16 mb-3">
            {[...Array(16)].map((_, i) => {
              const baseHeight = 4;
              const maxHeight = 56;
              const heightMultiplier = isSpeechDetected ? audioLevel / 15 : audioLevel / 40;
              const dynamicHeight = Math.max(baseHeight, Math.min(maxHeight, baseHeight + heightMultiplier * (maxHeight - baseHeight)));
              const animationDelay = i * 50;

              return (
                <div
                  key={i}
                  className={`w-2 rounded-full transition-all duration-150 ${
                    isRecording
                      ? 'bg-gradient-to-t from-red-400 to-red-600'
                      : isSpeechDetected
                        ? 'bg-gradient-to-t from-green-400 to-green-600'
                        : 'bg-gradient-to-t from-blue-200 to-blue-400'
                  }`}
                  style={{
                    height: `${dynamicHeight + Math.sin((Date.now() / 150 + animationDelay)) * 4}px`,
                    opacity: connectionStatus === 'connected' ? 1 : 0.3,
                  }}
                />
              );
            })}
          </div>

          {/* Audio Level Indicator */}
          <div className="flex items-center justify-center space-x-2 text-sm">
            <span className="text-gray-500">Audio Level:</span>
            <div className="flex-1 max-w-32 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-100 ${
                  isSpeechDetected ? 'bg-green-500' : 'bg-blue-400'
                }`}
                style={{ width: `${Math.min(100, audioLevel * 2)}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 w-8">{audioLevel.toFixed(0)}</span>
          </div>
        </div>
      </div>

      {/* Manual Controls */}
      <div className="mb-4 flex justify-center space-x-3">
        <button
          onClick={() => {
            if (isRecording) {
              stopRecording();
            } else {
              // Manual start recording (if needed)
              console.log('Manual recording trigger - auto-start is preferred');
            }
          }}
          disabled={connectionStatus !== 'connected'}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
            isRecording
              ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg'
              : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300 disabled:cursor-not-allowed'
          }`}
        >
          {isRecording ? '⏹️ Stop Recording' : '🎤 Voice Ready'}
        </button>

        <button
          onClick={() => {
            // Reset/clear any errors
            setError('');
            console.log('Voice system reset');
          }}
          className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          title="Reset voice system"
        >
          🔄
        </button>
      </div>

      {/* Transcription Display */}
      {lastTranscription && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="text-green-800 text-sm font-medium mb-1">✅ Transcription</div>
          <div className="text-green-700 text-sm">{lastTranscription}</div>
        </div>
      )}

      {/* Compact Status Info */}
      <div className="text-xs text-gray-400 grid grid-cols-2 gap-2">
        <div>Speech: {isSpeechDetected ? '✅' : '❌'}</div>
        <div>VAD: {vadConfidence.toFixed(2)}</div>
        <div>Status: {isRecording ? '🎤' : '⏸️'}</div>
        <div>WS: {connectionStatus === 'connected' ? '🟢' : '🔴'}</div>
      </div>
    </div>
  );
}
