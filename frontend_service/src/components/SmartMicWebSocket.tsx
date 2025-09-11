'use client';

import { useState, useEffect, useRef } from 'react';
import { AdvancedAudioProcessor, AudioMetrics } from '@/utils/AdvancedAudioProcessor';
import { TranscriptionFilter, FilterResult } from '@/utils/TranscriptionFilter';

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
  const [isCalibrating, setIsCalibrating] = useState<boolean>(false);
  const [noiseFloor, setNoiseFloor] = useState<number>(0);
  const [currentMetrics, setCurrentMetrics] = useState<AudioMetrics | null>(null);

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

  // Advanced processing refs
  const audioProcessorRef = useRef<AdvancedAudioProcessor | null>(null);
  const transcriptionFilterRef = useRef<TranscriptionFilter | null>(null);

  // Prevent duplicate transcriptions
  const lastFinalTranscriptionRef = useRef<string>('');
  const transcriptionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Speech session management
  const speechSessionActiveRef = useRef(false);
  const continuousSilenceStartRef = useRef<number | null>(null);

  // Constants from smart_mic.py
  const SILENCE_DURATION = 1000; // 1 second
  const MIN_RECORDING_TIME = 500; // 0.5 seconds
  const SESSION_END_SILENCE = 1500; // 1.5 seconds to end speech session
  // const WEBSOCKET_URL = 'wss://gxza5pgzegfdme-3000.proxy.runpod.net/ws/asr'; // External ASR Configuration
  const WEBSOCKET_URL = 'wss://s6rou7ayi3jrzc-3000.proxy.runpod.net/ws/asr';

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

      // Initialize advanced processors
      audioProcessorRef.current = new AdvancedAudioProcessor({
        energyThreshold: 0.01,
        rmsThreshold: 0.02,
        minConfidence: 0.6,
        minSpeechDuration: 300,
        maxSilenceDuration: 1500
      });

      transcriptionFilterRef.current = new TranscriptionFilter({
        minConfidence: 0.3,  // Lowered from 0.5 to 0.3 - more permissive for external ASR
        minLength: 3,        // Lowered from 5 to 3 - allow shorter phrases
        minWords: 1,         // Allow single meaningful words
        enableNoiseWordFilter: false,  // Disable for external ASR testing
        enableRepetitionFilter: false, // Disable for external ASR testing
        enableLanguageFilter: false    // Disable for external ASR testing
      });

      // Set up calibration monitoring
      setIsCalibrating(true);
      setTimeout(() => {
        if (audioProcessorRef.current) {
          setNoiseFloor(audioProcessorRef.current.getNoiseFloor());
          setIsCalibrating(false);
        }
      }, 3000);

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
    console.log('🔍 DEBUG: Received WebSocket message type:', message.type, 'data:', message.data);
    switch (message.type) {
      case 'connected':
        console.log('🎉 Server connected:', message.message);
        break;

      case 'vad_result':
        const { isSpeech, confidence: vadConfidenceValue } = message.data;
        setIsSpeechDetected(isSpeech);
        setVadConfidence(vadConfidenceValue);

        if (isSpeech) {
          lastSpeechTimeRef.current = Date.now();
          continuousSilenceStartRef.current = null;

          // Start speech session if not active
          if (!speechSessionActiveRef.current) {
            speechSessionActiveRef.current = true;
            console.log('🎤 Starting new speech session');

            // Auto-start recording for new speech session
            if (!isRecordingRef.current) {
              startRecording();
            }
          }
        } else {
          // Handle silence during speech session
          if (speechSessionActiveRef.current) {
            if (!continuousSilenceStartRef.current) {
              continuousSilenceStartRef.current = Date.now();
            }

            const silenceDuration = Date.now() - continuousSilenceStartRef.current;
            const recordingDuration = recordingStartTimeRef.current ?
              Date.now() - recordingStartTimeRef.current : 0;

            // Auto-stop recording after silence threshold
            if (isRecordingRef.current && silenceDuration >= SILENCE_DURATION && recordingDuration >= MIN_RECORDING_TIME) {
              console.log(`🔇 Auto-stopping: ${silenceDuration}ms silence, ${recordingDuration}ms total`);
              stopRecording();
            }

            // End speech session after extended silence
            if (silenceDuration >= SESSION_END_SILENCE) {
              console.log(`🔚 Ending speech session: ${silenceDuration}ms continuous silence`);
              speechSessionActiveRef.current = false;
              continuousSilenceStartRef.current = null;
            }
          }
        }
        break;

      case 'speech_detected':
        console.log('🎤 Server detected speech');
        break;

      case 'transcription':
        const { text, isFinal, source, confidence: transcriptionConfidence } = message.data;
        console.log('📝 Transcription received:', text, `(${source || 'unknown'})`, isFinal ? '[FINAL]' : '[PARTIAL]', `confidence: ${transcriptionConfidence || 'N/A'}`);

        // Update local transcription display (show partial results)
        setLastTranscription(text);

        // Only process final transcriptions
        if (isFinal && text.trim().length > 0) {
          // Check if this is a duplicate of the last final transcription
          if (lastFinalTranscriptionRef.current === text.trim()) {
            console.log('🚫 Duplicate final transcription ignored:', text);
            return;
          }

          // Apply advanced transcription filtering
          if (transcriptionFilterRef.current) {
            const filterResult = transcriptionFilterRef.current.filterTranscription(
              text,
              transcriptionConfidence || 0.8,
              undefined, // duration not available from WebSocket
              undefined  // word confidences not available
            );

            console.log('🔍 Transcription filter result:', {
              isValid: filterResult.isValid,
              confidence: filterResult.confidence ? filterResult.confidence.toFixed(3) : 'N/A',
              reason: filterResult.reason,
              metadata: filterResult.metadata
            });

            if (!filterResult.isValid) {
              console.log('🚫 Transcription filtered out:', filterResult.reason);
              setLastTranscription(`[Filtered: ${filterResult.reason}]`);

              // Clear filtered transcription after short delay
              setTimeout(() => {
                setLastTranscription('');
              }, 2000);
              return;
            }

            // Use filtered text if available
            const finalText = filterResult.filteredText || text;

            // Clear any existing timeout
            if (transcriptionTimeoutRef.current) {
              clearTimeout(transcriptionTimeoutRef.current);
            }

            console.log('✅ Final transcription confirmed after filtering:', finalText);
            console.log('🚀 Calling onTranscription with:', finalText);
            lastFinalTranscriptionRef.current = finalText.trim();
            onTranscription(finalText);
            onStatusChange('speaking');

            // Clear transcription after showing result
            transcriptionTimeoutRef.current = setTimeout(() => {
              setLastTranscription('');
              onStatusChange('idle');
              lastFinalTranscriptionRef.current = ''; // Reset for next transcription
              console.log('🎧 Ready for next voice input...');
            }, 3000);
          } else {
            // Fallback to original logic if filter not available
            console.log('⚠️ Transcription filter not available, using original logic');
            lastFinalTranscriptionRef.current = text.trim();
            onTranscription(text);
            onStatusChange('speaking');
          }
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

        // Process audio with advanced processor
        if (audioProcessorRef.current) {
          const metrics = audioProcessorRef.current.processAudioFrame(inputData, 16000);
          setCurrentMetrics(metrics);

          // Update UI with processed metrics
          setAudioLevel(metrics.rms * 100);

          // Determine if speech is detected
          const isSpeechDetected = audioProcessorRef.current.isSpeech(metrics);
          setIsSpeechDetected(isSpeechDetected);
          setVadConfidence(metrics.confidence);

          // Auto-start/stop recording based on advanced VAD
          if (isSpeechDetected && !isRecordingRef.current) {
            console.log('🎤 Advanced VAD detected speech - starting recording');
            startRecording();
          } else if (!isSpeechDetected && isRecordingRef.current) {
            // Let the existing silence detection handle stopping
          }
        } else {
          // Fallback to basic audio level update
          updateAudioLevel();
        }

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

    // Reset advanced processors
    if (audioProcessorRef.current) {
      audioProcessorRef.current.reset();
      audioProcessorRef.current = null;
    }

    transcriptionFilterRef.current = null;

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
    setIsCalibrating(false);
    setNoiseFloor(0);
    setCurrentMetrics(null);
    isRecordingRef.current = false;
    lastFinalTranscriptionRef.current = '';

    // Reset speech session refs
    speechSessionActiveRef.current = false;
    continuousSilenceStartRef.current = null;
    recordingStartTimeRef.current = null;
    lastSpeechTimeRef.current = null;
    silenceStartRef.current = null;

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

        {/* Calibration Status */}
        {isCalibrating && (
          <div className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 ml-2">
            🎚️ Calibrating Noise Floor...
          </div>
        )}

        {/* Noise Floor Display */}
        {!isCalibrating && noiseFloor > 0 && (
          <div className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700 ml-2">
            📊 Noise Floor: {(noiseFloor * 1000).toFixed(1)}
          </div>
        )}
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

      {/* Advanced Metrics Display */}
      {currentMetrics && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-700 mb-2">🔬 Advanced Audio Metrics</div>
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
            <div>RMS: {(currentMetrics.rms * 1000).toFixed(1)}</div>
            <div>Energy: {(currentMetrics.energy * 1000).toFixed(1)}</div>
            <div>ZCR: {currentMetrics.zcr.toFixed(3)}</div>
            <div>Confidence: {(currentMetrics.confidence * 100).toFixed(0)}%</div>
            <div>Spectral: {currentMetrics.spectralCentroid.toFixed(0)}Hz</div>
            <div>Rolloff: {currentMetrics.spectralRolloff.toFixed(0)}Hz</div>
          </div>
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
