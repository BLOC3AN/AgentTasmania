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
  const [audioLevel, setAudioLevel] = useState<number>(0);

  // Debug logging for state changes
  useEffect(() => {
    console.log('🔄 VoiceModal currentTranscription changed:', currentTranscription);
  }, [currentTranscription]);

  useEffect(() => {
    console.log('🔄 VoiceModal transcriptionHistory changed:', transcriptionHistory);
  }, [transcriptionHistory]);

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
      console.log('📝 Adding to transcription history:', text);
      setTranscriptionHistory(prev => {
        const newHistory = [...prev, text];
        console.log('📋 Updated history:', newHistory);
        // Keep only last 5 transcriptions
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

  // Clear transcription history
  const clearHistory = () => {
    setTranscriptionHistory([]);
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Content - Two Column Layout */}
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${
              voiceStatus === 'listening' ? 'bg-green-400 animate-pulse' :
              voiceStatus === 'processing' ? 'bg-yellow-400 animate-spin' :
              voiceStatus === 'speaking' ? 'bg-purple-400 animate-bounce' :
              'bg-gray-300'
            }`} />
            <h2 className="text-lg font-semibold">Voice Assistant</h2>
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

        {/* Main Content - Two Column Layout */}
        <div className="flex">
          {/* Left Column - Voice Interface */}
          <div className="flex-1 p-6 border-r border-gray-200">
            {/* Audio Visualizer */}
            <div className="text-center mb-6">
              <div className="mb-4">
                <AudioVisualizer />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Speak naturally
              </h3>
              <p className="text-sm text-gray-600">
                {voiceStatus === 'idle' && 'Ready to listen...'}
                {voiceStatus === 'listening' && 'Listening to your voice...'}
                {voiceStatus === 'processing' && 'Processing speech...'}
                {voiceStatus === 'speaking' && 'Transcription complete!'}
              </p>
            </div>

            {/* Hidden SmartMicWebSocket Component */}
            <div className="hidden">
              <SmartMicWebSocket
                isActive={isOpen}
                onTranscription={handleTranscription}
                onStatusChange={(status) => {
                  setVoiceStatus(status);
                  // Simulate audio level for visualization
                  if (status === 'listening') {
                    setAudioLevel(Math.random() * 40 + 10);
                  } else {
                    setAudioLevel(5);
                  }
                }}
              />
            </div>

            {/* Current Transcription - Compact */}
            <div className="mt-6">
              {/* Current Transcription */}
              {currentTranscription && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                  <div className="flex items-center space-x-2 mb-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-medium text-blue-700">Detecting...</span>
                  </div>
                  <p className="text-blue-800 text-sm">{currentTranscription}</p>
                </div>
              )}

              {/* Latest Result */}
              {transcriptionHistory.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-green-700">Latest Result</span>
                  </div>
                  <p className="text-green-800 text-sm bg-white rounded p-2 border border-green-100">
                    &ldquo;{transcriptionHistory[transcriptionHistory.length - 1]}&rdquo;
                  </p>
                </div>
              )}

              {/* Empty State */}
              {!currentTranscription && transcriptionHistory.length === 0 && (
                <div className="text-center py-6">
                  <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-xs">Start speaking to see transcription</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Voice History */}
          <div className="w-80 bg-gray-50 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium text-gray-700">Voice History</span>
                {transcriptionHistory.length > 0 && (
                  <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                    {transcriptionHistory.length}
                  </span>
                )}
              </div>
              {transcriptionHistory.length > 0 && (
                <button
                  onClick={clearHistory}
                  className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded transition-colors"
                  title="Clear all history"
                >
                  Clear
                </button>
              )}
            </div>

            {/* History List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {transcriptionHistory.length > 0 ? (
                transcriptionHistory.map((text, index) => (
                  <div key={index} className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
                    <div className="flex items-start justify-between mb-1">
                      <span className="text-xs text-gray-500 font-medium">#{index + 1}</span>
                      <span className="text-xs text-gray-400">
                        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-sm text-gray-800 leading-relaxed">
                      &ldquo;{text}&rdquo;
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-center py-8">
                  <div className="w-12 h-12 mx-auto mb-3 bg-gray-200 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <p className="text-gray-500 text-xs">No voice history yet</p>
                  <p className="text-gray-400 text-xs mt-1">Start speaking to build history</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer - Minimal */}
        <div className="bg-gray-50 px-6 py-3 border-t text-center">
          <p className="text-xs text-gray-500">
            Press <kbd className="px-1 py-0.5 bg-gray-200 rounded text-xs">Esc</kbd> to close
          </p>
        </div>
      </div>
    </div>
  );
}
