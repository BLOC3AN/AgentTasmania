'use client';

import { useState } from 'react';
import SessionInfo from '@/components/SessionInfo';
import { useSession } from '@/hooks/useSession';

export default function TestSessionPage() {
  const [testMessage, setTestMessage] = useState('');
  const [chatResponse, setChatResponse] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const { sessionId } = useSession();

  const testChatAPI = async () => {
    if (!testMessage.trim()) return;
    
    setIsLoading(true);
    setChatResponse(null);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-conversation-id': sessionId || 'test-session',
        },
        credentials: 'include',
        body: JSON.stringify({ message: testMessage }),
      });
      
      const data = await response.json();
      setChatResponse(data);
    } catch (error) {
      setChatResponse({ error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsLoading(false);
    }
  };

  const testSessionAPI = async (method: string) => {
    try {
      const response = await fetch('/api/session', {
        method: method,
        credentials: 'include',
      });
      
      const data = await response.json();
      console.log(`Session ${method} result:`, data);
    } catch (error) {
      console.error(`Session ${method} error:`, error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Session Management Test</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Session Info Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Session Information</h2>
              <SessionInfo showDetails={true} />
            </div>
            
            {/* Session API Tests */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Session API Tests</h2>
              <div className="space-y-3">
                <button
                  onClick={() => testSessionAPI('GET')}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  GET /api/session
                </button>
                
                <button
                  onClick={() => testSessionAPI('POST')}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  POST /api/session (Create New)
                </button>
                
                <button
                  onClick={() => testSessionAPI('DELETE')}
                  className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  DELETE /api/session (Clear)
                </button>
              </div>
            </div>
          </div>
          
          {/* Chat API Test Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Chat API Test</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Test Message
                  </label>
                  <input
                    type="text"
                    value={testMessage}
                    onChange={(e) => setTestMessage(e.target.value)}
                    placeholder="Enter a test message..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <button
                  onClick={testChatAPI}
                  disabled={!testMessage.trim() || isLoading || !sessionId}
                  className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Sending...' : 'Test Chat API'}
                </button>
                
                {!sessionId && (
                  <p className="text-sm text-red-600">
                    Waiting for session to be initialized...
                  </p>
                )}
              </div>
            </div>
            
            {/* Response Display */}
            {chatResponse && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">Chat Response</h2>
                <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96">
                  {JSON.stringify(chatResponse, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
        
        {/* Instructions */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">How to Test</h2>
          <ol className="list-decimal list-inside space-y-2 text-blue-800">
            <li>Check the session information panel to see your current session</li>
            <li>Use the session API buttons to test session management</li>
            <li>Enter a test message and click "Test Chat API" to test the chat functionality</li>
            <li>Check the browser's developer tools to see cookies and network requests</li>
            <li>Refresh the page to test session persistence</li>
          </ol>
        </div>
        
        {/* Back to Home */}
        <div className="mt-8 text-center">
          <a
            href="/"
            className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            ← Back to Home
          </a>
        </div>
      </div>
    </div>
  );
}
