'use client';

import { useState, useEffect } from 'react';
import SmartMicWebSocket from './SmartMicWebSocket';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscription: (text: string) => void;
}

type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export default function VoiceModal({ isOpen, onClose, onTranscription }: VoiceModalProps) {
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle');
  const [currentTranscription, setCurrentTranscription] = useState<string>('');
  const [transcriptionHistory, setTranscriptionHistory] = useState<string[]>([]);

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
    setCurrentTranscription(text);
    if (text.trim()) {
      setTranscriptionHistory(prev => {
        const newHistory = [...prev, text];
        // Keep only last 5 transcriptions
        return newHistory.slice(-5);
      });
      // Clear current transcription after adding to history
      setTimeout(() => setCurrentTranscription(''), 3000);
    }
    onTranscription(text);
  };

  // Clear transcription history
  const clearHistory = () => {
    setTranscriptionHistory([]);
    setCurrentTranscription('');
  };

  if (!isOpen) return null;

  const getStatusColor = () => {
    switch (voiceStatus) {
      case 'listening': return 'text-green-600';
      case 'processing': return 'text-blue-600';
      case 'speaking': return 'text-purple-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusText = () => {
    switch (voiceStatus) {
      case 'listening': return 'Listening...';
      case 'processing': return 'Processing...';
      case 'speaking': return 'Speaking...';
      default: return 'Ready';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative w-full max-w-4xl max-h-full bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
           style={{
             maxWidth: 'calc(100vw - 32px)',
             maxHeight: 'calc(100vh - 32px)'
           }}>
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 sm:p-6 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <h2 className="text-xl sm:text-2xl font-bold truncate">Voice Assistant</h2>
              <p className="text-blue-100 mt-1 text-sm sm:text-base truncate">WebSocket VAD Voice Processing</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-colors flex-shrink-0 ml-4"
              title="Close (Esc)"
            >
              <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-gray-50 px-4 sm:px-6 py-3 sm:py-4 border-b flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
              <div className={`w-3 h-3 rounded-full flex-shrink-0 ${
                voiceStatus === 'listening' ? 'bg-green-500 animate-pulse' :
                voiceStatus === 'processing' ? 'bg-blue-500 animate-spin' :
                voiceStatus === 'speaking' ? 'bg-purple-500 animate-bounce' :
                'bg-gray-400'
              }`} />
              <span className={`font-medium text-sm sm:text-base truncate ${getStatusColor()}`}>
                {getStatusText()}
              </span>
            </div>
            <div className="text-xs sm:text-sm text-gray-500 hidden sm:block">
              Press <kbd className="px-2 py-1 bg-gray-200 rounded text-xs">Esc</kbd> to close
            </div>
          </div>
        </div>

        {/* Voice Interface */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="text-center max-w-2xl mx-auto">
            <div className="mb-6 sm:mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mb-4">
                <svg className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <h3 className="text-lg sm:text-xl font-semibold text-gray-800 mb-2">
                Speak naturally
              </h3>
              <p className="text-sm sm:text-base text-gray-600 px-4">
                Your voice will be processed in real-time with advanced VAD technology
              </p>
            </div>

            {/* SmartMicWebSocket Component */}
            <div className="bg-gray-50 rounded-xl p-4 sm:p-6">
              <SmartMicWebSocket
                isActive={isOpen}
                onTranscription={handleTranscription}
                onStatusChange={setVoiceStatus}
              />
            </div>

            {/* Real-time Transcription Display */}
            <div className="mt-4 sm:mt-6">
              {/* Current Transcription */}
              {currentTranscription && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4 mb-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-xs sm:text-sm font-medium text-blue-700">Detecting...</span>
                  </div>
                  <p className="text-sm sm:text-base text-blue-800 font-medium break-words">{currentTranscription}</p>
                </div>
              )}

              {/* Transcription History */}
              {transcriptionHistory.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 sm:p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2 min-w-0 flex-1">
                      <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-xs sm:text-sm font-medium text-green-700 truncate">Recent Transcriptions</span>
                    </div>
                    <button
                      onClick={clearHistory}
                      className="text-xs text-green-600 hover:text-green-800 hover:bg-green-100 px-2 py-1 rounded transition-colors flex-shrink-0"
                      title="Clear history"
                    >
                      Clear
                    </button>
                  </div>
                  <div className="space-y-2 max-h-24 sm:max-h-32 overflow-y-auto">
                    {transcriptionHistory.map((text, index) => (
                      <div key={index} className="text-xs sm:text-sm text-green-800 bg-white rounded p-2 border border-green-100 break-words">
                        &ldquo;{text}&rdquo;
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty State */}
              {!currentTranscription && transcriptionHistory.length === 0 && (
                <div className="text-center py-6 sm:py-8">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 sm:w-8 sm:h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-xs sm:text-sm px-4">Start speaking to see your voice transcription here</p>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="mt-6 sm:mt-8 grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 text-xs sm:text-sm text-gray-600">
              <div className="flex items-center justify-center sm:justify-start space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full flex-shrink-0"></div>
                <span className="text-center sm:text-left">Auto-start when speech detected</span>
              </div>
              <div className="flex items-center justify-center sm:justify-start space-x-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0"></div>
                <span className="text-center sm:text-left">Real-time audio processing</span>
              </div>
              <div className="flex items-center justify-center sm:justify-start space-x-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full flex-shrink-0"></div>
                <span className="text-center sm:text-left">Advanced noise filtering</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-4 sm:px-6 py-3 sm:py-4 border-t flex-shrink-0">
          <div className="flex items-center justify-between text-xs sm:text-sm text-gray-500">
            <div className="truncate">
              WebSocket VAD • Real-time Voice Processing
            </div>
            <div className="flex items-center space-x-2 sm:space-x-4 ml-4">
              <span className="hidden sm:inline">Status:</span>
              <span className={`${getStatusColor()} font-medium`}>{getStatusText()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
