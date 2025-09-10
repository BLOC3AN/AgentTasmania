'use client';

import { useState, useEffect, useRef } from 'react';
import { useSession } from '@/hooks/useSession';
import SmartMicWebSocket from './SmartMicWebSocket';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export default function ChatBoxWebSocket() {
  const { sessionId } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
        // setMessages((prev: Message[]) => [...prev, agentMessage]);
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, I encountered an error. Please try again.',
          sender: 'agent',
          timestamp: new Date(),
        };
        // setMessages((prev: Message[]) => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'agent',
        timestamp: new Date(),
      };
      // setMessages((prev: Message[]) => [...prev, errorMessage]);
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
    setIsVoiceMode(!isVoiceMode);
    if (!isVoiceMode) {
      console.log('🎧 Activating WebSocket VAD Voice Mode...');
    } else {
      console.log('🔇 Deactivating Voice Mode...');
      setVoiceStatus('idle');
    }
  };

  const handleVoiceTranscription = (text: string) => {
    console.log('📝 Voice transcription received:', text);
    
    // Add transcribed message to chat
    const userMessage: Message = {
      id: Date.now().toString(),
      text: text,
      sender: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    
    // Send to AI for processing (same as text input)
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
        } else {
          throw new Error('API Error');
        }
      } catch (error) {
        // Fallback demo response
        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          text: `I received your voice message via WebSocket: "${text}". This demonstrates real-time VAD processing with server-side speech detection!`,
          sender: 'agent',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiResponse]);
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
        <div ref={messagesEndRef} />
      </div>

      {/* WebSocket VAD Voice Interface */}
      {isVoiceMode && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="text-center mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">WebSocket VAD Voice Assistant</h4>
            
            {/* SmartMicWebSocket Component */}
            <SmartMicWebSocket
              isActive={isVoiceMode}
              onTranscription={handleVoiceTranscription}
              onStatusChange={(status) => {
                setVoiceStatus(status);
              }}
            />
          </div>
        </div>
      )}

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
            className={`px-3 py-2 rounded-md transition-colors ${
              isVoiceMode 
                ? 'bg-green-600 text-white hover:bg-green-700' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            title="WebSocket VAD Voice Assistant"
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
