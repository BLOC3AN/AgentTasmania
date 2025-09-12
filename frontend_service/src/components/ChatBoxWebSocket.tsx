'use client';

import { useState, useEffect, useRef } from 'react';
import { useSession } from '@/hooks/useSession';
import VoiceModal from './VoiceModal';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface VoiceHistory {
  id: string;
  text: string;
  timestamp: Date;
}

export default function ChatBoxWebSocket() {
  const { sessionId } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [voiceHistory, setVoiceHistory] = useState<VoiceHistory[]>([]);
  const [showVoiceHistory, setShowVoiceHistory] = useState(false);
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const [processingState, setProcessingState] = useState<'idle' | 'listening' | 'processing_stt' | 'processing_ai' | 'playing_tts'>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const processingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (sessionId && messages.length === 0) {
      const welcomeMessage: Message = {
        id: 'welcome',
        text: 'Hello! I\'m here to help you with your academic writing. I now support WebSocket-based voice input with real-time VAD processing!',
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, [sessionId, messages.length]);

  const sendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev: Message[]) => [...prev, userMessage]);
    setInputText('');
    setIsTyping(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputText,
          sessionId: sessionId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const agentMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: data.response,
          sender: 'agent',
          timestamp: new Date(),
        };
        console.log("🚀 ~ sendMessage ~ agentMessage:", agentMessage)
        setMessages((prev: Message[]) => [...prev, agentMessage]);

        // Play TTS response if in voice mode
        if (isVoiceMode && data.response) {
          await playTTSResponse(data.response);
        }
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, I encountered an error. Please try again.',
          sender: 'agent',
          timestamp: new Date(),
        };
        setMessages((prev: Message[]) => [...prev, errorMessage]);
      }
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages((prev: Message[]) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const toggleVoiceMode = () => {
    if (!isVoiceMode) {
      console.log('🎧 Opening Voice Modal...');
      setIsVoiceMode(true);
      setShowVoiceModal(true);
    } else {
      console.log('🔇 Closing Voice Modal...');
      setIsVoiceMode(false);
      setShowVoiceModal(false);
    }
  };

  const closeVoiceModal = () => {
    setIsVoiceMode(false);
    setShowVoiceModal(false);
    // Reset to idle state when closing modal
    resetToIdleState();
  };

  const toggleVoiceHistory = () => {
    setShowVoiceHistory(!showVoiceHistory);
  };

  const clearVoiceHistory = () => {
    setVoiceHistory([]);
  };

  // Processing State Management
  const setProcessingStateWithTimeout = (state: typeof processingState, timeoutMs: number = 30000) => {
    setProcessingState(state);

    // Clear existing timeout
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
    }

    // Set timeout to reset to idle if stuck
    if (state !== 'idle') {
      processingTimeoutRef.current = setTimeout(() => {
        console.warn(`⚠️ Processing timeout in state: ${state}, resetting to idle`);
        resetToIdleState();
      }, timeoutMs);
    }
  };

  const resetToIdleState = () => {
    setProcessingState('idle');
    setIsTyping(false);
    setIsPlayingTTS(false);

    // Stop any playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    // Clear timeout
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }

    console.log('🔄 Reset to idle state - ready for next voice input');
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current);
      }
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // TTS Service Integration
  const playTTSResponse = async (text: string) => {
    if (!text.trim() || !isVoiceMode) return;

    try {
      setIsPlayingTTS(true);
      console.log('🎵 Calling TTS service for text:', text);

      const response = await fetch('http://localhost:8007/synthesize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          voice: 'coral',
          response_format: 'mp3',
          speed: 1.0
        }),
      });

      if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        // Create and play audio
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }

        const audio = new Audio(audioUrl);
        audioRef.current = audio;

        audio.onended = () => {
          setIsPlayingTTS(false);
          URL.revokeObjectURL(audioUrl);
          console.log('🎵 TTS playback completed');
          resetToIdleState();
        };

        audio.onerror = () => {
          setIsPlayingTTS(false);
          URL.revokeObjectURL(audioUrl);
          console.error('❌ TTS playback error');
          resetToIdleState();
        };

        await audio.play();
        console.log('🎵 TTS playback started');
      } else {
        throw new Error(`TTS service error: ${response.status}`);
      }
    } catch (error) {
      console.error('❌ TTS Error:', error);
      setIsPlayingTTS(false);
      resetToIdleState();
    }
  };

  const handleVoiceTranscription = async (text: string) => {
    console.log('📝 Voice transcription received:', text);

    // Check if we're in a state that can accept new input
    if (processingState !== 'idle' && processingState !== 'listening') {
      console.warn('⚠️ Voice input ignored - currently processing:', processingState);
      return;
    }

    // Set to processing STT state
    setProcessingStateWithTimeout('processing_stt', 5000);

    // Add to voice history
    const voiceEntry: VoiceHistory = {
      id: Date.now().toString(),
      text: text,
      timestamp: new Date()
    };
    setVoiceHistory(prev => [...prev, voiceEntry].slice(-10)); // Keep last 10 entries

    // Add transcribed message to chat
    const userMessage: Message = {
      id: Date.now().toString(),
      text: text,
      sender: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    // Set to processing AI state
    setProcessingStateWithTimeout('processing_ai', 30000);
    setIsTyping(true);
    
    setTimeout(async () => {
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: text,
            sessionId: sessionId,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          const agentMessage: Message = {
            id: (Date.now() + 1).toString(),
            text: data.response,
            sender: 'agent',
            timestamp: new Date(),
          };
          setMessages((prev: Message[]) => [...prev, agentMessage]);

          // Play TTS response if in voice mode
          if (isVoiceMode && data.response) {
            setProcessingStateWithTimeout('playing_tts', 60000);
            await playTTSResponse(data.response);
            // playTTSResponse will call resetToIdleState when done
          } else {
            // No TTS needed, reset to idle
            resetToIdleState();
          }
        } else {
          throw new Error('API Error');
        }
      } catch (error) {
        console.error('❌ AI API Error:', error);
        // Fallback demo response
        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          text: `I received your voice message via WebSocket: "${text}". This demonstrates real-time VAD processing with server-side speech detection!`,
          sender: 'agent',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiResponse]);

        // Play TTS response if in voice mode
        if (isVoiceMode && aiResponse.text) {
          setProcessingStateWithTimeout('playing_tts', 60000);
          await playTTSResponse(aiResponse.text);
          // playTTSResponse will call resetToIdleState when done
        } else {
          // No TTS needed, reset to idle
          resetToIdleState();
        }
      } finally {
        setIsTyping(false);
      }
    }, 1000);
  };

  if (!isOpen) {
    return (
      <button
        onClick={toggleChat}
        className="fixed bottom-6 right-6 w-16 h-16 bg-blue-600 text-white rounded-full shadow-2xl hover:bg-blue-700 transition-all duration-200 flex items-center justify-center pointer-events-auto"
        style={{
          zIndex: 999999,
          position: 'fixed',
          bottom: '24px',
          right: '24px'
        }}
        aria-label="Open chat"
      >
        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 3.582-8 8-8s8 3.582 8 8z" />
        </svg>
      </button>
    );
  }

  return (
    <div
      className={`fixed bg-white rounded-lg shadow-2xl border border-gray-200 transition-all duration-300 pointer-events-auto ${
        isExpanded ? 'w-96 h-[600px]' : 'w-80 h-96'
      } ${isVoiceMode ? 'w-[500px]' : ''}
      sm:w-80 sm:h-96
      ${isExpanded ? 'sm:w-96 sm:h-[600px]' : ''}
      ${isVoiceMode ? 'sm:w-[500px]' : ''}`}
      style={{
        zIndex: 999999,
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        maxHeight: 'calc(100vh - 48px)',
        maxWidth: 'calc(100vw - 48px)',
        minWidth: '280px',
        minHeight: '320px'
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-blue-600 text-white rounded-t-lg">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-3.582 8-8 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 3.582-8 8-8s8 3.582 8 8z" />
          </svg>
          <span className="font-medium">WebSocket VAD Assistant</span>
        </div>
        <div className="flex items-center space-x-2">
          {/* Voice History Button */}
          {voiceHistory.length > 0 && (
            <button
              onClick={toggleVoiceHistory}
              className={`text-white hover:text-gray-200 transition-colors relative ${
                showVoiceHistory ? 'bg-white bg-opacity-20 rounded' : ''
              }`}
              title="Voice History"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <span className="absolute -top-1 -right-1 bg-green-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {voiceHistory.length}
              </span>
            </button>
          )}
          <button
            onClick={toggleExpand}
            className="text-white hover:text-gray-200 transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            )}
          </button>
          <button
            onClick={toggleChat}
            className="text-white hover:text-gray-200 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Voice History Panel */}
      {showVoiceHistory && voiceHistory.length > 0 && (
        <div className="border-b border-gray-200 bg-green-50 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              <span className="text-sm font-medium text-green-700">Voice History ({voiceHistory.length})</span>
            </div>
            <button
              onClick={clearVoiceHistory}
              className="text-xs text-green-600 hover:text-green-800 px-2 py-1 rounded transition-colors"
              title="Clear voice history"
            >
              Clear
            </button>
          </div>
          <div className="space-y-1 max-h-24 overflow-y-auto">
            {voiceHistory.slice(-5).reverse().map((entry) => (
              <div key={entry.id} className="text-xs text-green-800 bg-white rounded px-2 py-1 border border-green-100 flex items-center justify-between">
                <span className="truncate flex-1 mr-2">{entry.text}</span>
                <span className="text-green-500 text-xs flex-shrink-0">
                  {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
            {voiceHistory.length > 5 && (
              <div className="text-xs text-green-400 text-center py-1">
                ... and {voiceHistory.length - 5} more entries
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ height: isExpanded ? '480px' : '240px' }}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs px-4 py-2 rounded-lg ${
                message.sender === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        {isPlayingTTS && (
          <div className="flex justify-start">
            <div className="bg-green-100 text-green-800 px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                </svg>
                <span className="text-sm">Playing audio response...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Voice Modal */}
      <VoiceModal
        isOpen={showVoiceModal}
        onClose={closeVoiceModal}
        onTranscription={handleVoiceTranscription}
        processingState={processingState}
        onProcessingStateChange={setProcessingStateWithTimeout}
      />

      {/* Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about academic writing..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isTyping}
          />
          <button
            onClick={toggleVoiceMode}
            disabled={processingState !== 'idle' && !isVoiceMode}
            className={`px-3 py-2 rounded-md transition-colors ${
              isVoiceMode
                ? 'bg-green-600 text-white hover:bg-green-700'
                : processingState !== 'idle' && !isVoiceMode
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            title={processingState !== 'idle' && !isVoiceMode
              ? `Voice unavailable - ${processingState.replace('_', ' ')}`
              : "WebSocket VAD Voice Assistant"
            }
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </button>
          <button
            onClick={sendMessage}
            disabled={!inputText.trim() || isTyping}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
