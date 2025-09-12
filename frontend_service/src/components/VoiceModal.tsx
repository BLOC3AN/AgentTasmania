'use client';

import { useState, useEffect } from 'react';
import SmartMicWebSocket from './SmartMicWebSocket';
import MarkdownRenderer from './MarkdownRenderer';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscription: (text: string) => void;
  processingState?: 'idle' | 'listening' | 'processing_stt' | 'processing_ai' | 'playing_tts';
  onProcessingStateChange?: (state: 'idle' | 'listening' | 'processing_stt' | 'processing_ai' | 'playing_tts', timeoutMs?: number) => void;
  onAIResponse?: (userInput: string, aiResponse: string) => void;
  onStopTTS?: () => void;
}

interface ConversationPair {
  userInput: string;
  aiResponse?: string;
  timestamp: Date;
}

type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export default function VoiceModal({ isOpen, onClose, onTranscription, processingState = 'idle', onProcessingStateChange, onAIResponse, onStopTTS }: VoiceModalProps) {
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle');
  const [currentTranscription, setCurrentTranscription] = useState<string>('');
  const [conversationHistory, setConversationHistory] = useState<ConversationPair[]>([]);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  // Determine if mic should be available based on processing state
  const isMicAvailable = processingState === 'idle' || processingState === 'listening';

  // Update voice status based on processing state
  useEffect(() => {
    switch (processingState) {
      case 'idle':
        setVoiceStatus('idle');
        break;
      case 'listening':
        setVoiceStatus('listening');
        break;
      case 'processing_stt':
      case 'processing_ai':
        setVoiceStatus('processing');
        break;
      case 'playing_tts':
        setVoiceStatus('speaking');
        break;
    }
  }, [processingState]);

  // Debug logging for state changes
  useEffect(() => {
    console.log('🔄 VoiceModal currentTranscription changed:', currentTranscription);
  }, [currentTranscription]);

  useEffect(() => {
    console.log('🔄 VoiceModal conversationHistory changed:', conversationHistory);
  }, [conversationHistory]);

  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden'; // Prevent background scroll
    } else {
      // Reset states when modal closes
      setCurrentTranscription('');
      setVoiceStatus('idle');
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Handle transcription updates
  const handleTranscription = (text: string) => {
    console.log('🎯 VoiceModal handleTranscription called with:', text);
    setCurrentTranscription(text);
    if (text.trim()) {
      console.log('📝 Adding user input to conversation history:', text);
      setConversationHistory(prev => {
        const newPair: ConversationPair = {
          userInput: text,
          timestamp: new Date()
        };
        const newHistory = [...prev, newPair];
        console.log('📋 Updated conversation history:', newHistory);
        // Keep only last 5 conversations
        return newHistory.slice(-5);
      });
      // Clear current transcription after adding to history
      setTimeout(() => {
        console.log('🧹 Clearing current transcription');
        setCurrentTranscription('');
      }, 3000);
    }
    onTranscription(text);
  };

  // Handle AI response updates
  const handleAIResponse = (userInput: string, aiResponse: string) => {
    console.log('🤖 VoiceModal handleAIResponse called:', { userInput, aiResponse });
    setConversationHistory((prev: ConversationPair[]) => {
      const newHistory = prev.map((pair: ConversationPair) =>
        pair.userInput === userInput && !pair.aiResponse
          ? { ...pair, aiResponse }
          : pair
      );
      console.log('📋 Updated conversation history with AI response:', newHistory);
      return newHistory;
    });
  };

  // Expose handleAIResponse to parent
  useEffect(() => {
    if (onAIResponse) {
      // This is a bit of a hack, but we need to expose the function to parent
      (window as any).voiceModalHandleAIResponse = handleAIResponse;
    }
  }, [onAIResponse]);

  // Clear conversation history
  const clearHistory = () => {
    setConversationHistory([]);
    setCurrentTranscription('');
  };

  // Gentle audio level animation - Eye-friendly
  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const animateAudioLevel = () => {
      if (voiceStatus === 'listening') {
        // Gentle, slower audio level changes (30fps instead of 60fps)
        setAudioLevel(prev => {
          const target = Math.random() * 20 + 8; // Reduced amplitude
          return prev + (target - prev) * 0.05; // Slower interpolation
        });
      } else {
        // Gradually decrease to idle level
        setAudioLevel(prev => prev * 0.9 + 3);
      }
    };

    if (isOpen) {
      // Use setInterval instead of requestAnimationFrame for slower, eye-friendly updates
      intervalId = setInterval(animateAudioLevel, 33); // ~30fps instead of 60fps
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isOpen, voiceStatus]);

  if (!isOpen) return null;

  // Removed unused helper functions

  // Eye-Friendly Audio Visualization Component
  const AudioVisualizer = () => {
    const bars = Array.from({ length: 8 }, (_, i) => {
      // Gentler height variations
      const baseHeight = Math.max(6, audioLevel * (0.3 + Math.random() * 0.4));
      const delay = i * 100; // Slower stagger
      return (
        <div
          key={i}
          className="bg-gradient-to-t from-blue-400 to-purple-400 rounded-full transition-all duration-500 ease-in-out"
          style={{
            height: `${baseHeight}px`,
            width: '5px',
            transitionDelay: `${delay}ms`,
            transform: voiceStatus === 'listening' ? 'scaleY(1.1)' : 'scaleY(1)',
            opacity: voiceStatus === 'listening' ? 0.9 : 0.6
          }}
        />
      );
    });

    return (
      <div className="flex items-end justify-center space-x-2 h-12 mb-4">
        {bars}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content - Responsive Layout */}
      <div className="relative w-full max-w-2xl mx-auto bg-white rounded-xl sm:rounded-2xl shadow-2xl overflow-hidden max-h-[95vh] sm:max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-3 sm:p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className={`w-3 h-3 rounded-full ${
              voiceStatus === 'listening' ? 'bg-green-400 animate-pulse' :
              voiceStatus === 'processing' ? 'bg-yellow-400 animate-spin' :
              voiceStatus === 'speaking' ? 'bg-purple-400 animate-bounce' :
              'bg-gray-300'
            }`} />
            <h2 className="text-base sm:text-lg font-semibold">Voice Assistant</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
            title="Close (Esc)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Main Content - Scrollable */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {/* Voice Interface */}
          <div className="w-full">
            {/* Audio Visualizer */}
            <div className="text-center mb-6">
              <div className="mb-4">
                <AudioVisualizer />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Speak naturally
              </h3>
              <p className="text-sm text-gray-600">
                {processingState === 'idle' && 'Ready to listen...'}
                {processingState === 'listening' && 'Listening to your voice...'}
                {processingState === 'processing_stt' && 'Processing speech...'}
                {processingState === 'processing_ai' && 'AI is thinking...'}
                {processingState === 'playing_tts' && (
                  <span className="flex items-center justify-center space-x-2">
                    <span>Playing response...</span>
                    {onStopTTS && (
                      <button
                        onClick={onStopTTS}
                        className="ml-2 px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition-colors"
                        title="Stop audio"
                      >
                        Stop
                      </button>
                    )}
                  </span>
                )}
                {!isMicAvailable && 'Mic unavailable - processing...'}
              </p>
            </div>

            {/* Hidden SmartMicWebSocket Component */}
            <div className="hidden">
              <SmartMicWebSocket
                isActive={isOpen && isMicAvailable}
                onTranscription={handleTranscription}
                onStatusChange={(status) => {
                  // Only update status if mic is available
                  if (isMicAvailable) {
                    setVoiceStatus(status);
                    // Notify parent about listening state
                    if (status === 'listening' && onProcessingStateChange) {
                      onProcessingStateChange('listening');
                    } else if (status === 'idle' && processingState === 'listening' && onProcessingStateChange) {
                      onProcessingStateChange('idle');
                    }
                  }
                  // Simulate audio level for visualization
                  if (status === 'listening') {
                    setAudioLevel(Math.random() * 40 + 10);
                  } else {
                    setAudioLevel(5);
                  }
                }}
              />
            </div>

            {/* Current Transcription */}
            {currentTranscription && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-2 mb-1">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className="text-xs font-medium text-blue-700">Detecting...</span>
                </div>
                <p className="text-blue-800 text-sm">{currentTranscription}</p>
              </div>
            )}

            {/* Conversation History */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-medium text-gray-700">Conversation History</span>
                  {conversationHistory.length > 0 && (
                    <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                      {conversationHistory.length}
                    </span>
                  )}
                </div>
                {conversationHistory.length > 0 && (
                  <button
                    onClick={clearHistory}
                    className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded transition-colors"
                    title="Clear all history"
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* History List - Improved scrolling */}
              <div className="space-y-3 max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                {conversationHistory.length > 0 ? (
                  conversationHistory.map((conversation: ConversationPair, index: number) => (
                    <div key={index} className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs text-gray-500 font-medium">#{index + 1}</span>
                        <span className="text-xs text-gray-400">
                          {conversation.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      {/* User Input */}
                      <div className="mb-2">
                        <div className="flex items-center space-x-1 mb-1">
                          <svg className="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                          </svg>
                          <span className="text-xs text-blue-600 font-medium">You</span>
                        </div>
                        <p className="text-sm text-gray-800 leading-relaxed bg-blue-50 rounded p-2">
                          &ldquo;{conversation.userInput}&rdquo;
                        </p>
                      </div>

                      {/* AI Response */}
                      {conversation.aiResponse && (
                        <div>
                          <div className="flex items-center space-x-1 mb-1">
                            <svg className="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                            <span className="text-xs text-green-600 font-medium">AI</span>
                          </div>
                          <div className="bg-green-50 rounded p-2">
                            <MarkdownRenderer
                              content={conversation.aiResponse}
                              className="text-gray-800"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <div className="w-12 h-12 mx-auto mb-3 bg-gray-200 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                    <p className="text-gray-500 text-xs">No conversation history yet</p>
                    <p className="text-gray-400 text-xs mt-1">Start speaking to build history</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer - Minimal */}
        <div className="flex-shrink-0 bg-gray-50 px-4 sm:px-6 py-2 sm:py-3 border-t text-center">
          <p className="text-xs text-gray-500">
            Press <kbd className="px-1 py-0.5 bg-gray-200 rounded text-xs">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}
