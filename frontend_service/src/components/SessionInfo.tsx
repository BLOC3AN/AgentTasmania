'use client';

import { useSession } from '@/hooks/useSession';

interface SessionInfoProps {
  showDetails?: boolean;
  className?: string;
}

export default function SessionInfo({ showDetails = false, className = '' }: SessionInfoProps) {
  const { sessionId, isLoading, error, isNewSession, refreshSession, clearSession, createNewSession } = useSession();

  if (!showDetails) {
    return (
      <div className={`text-xs text-gray-500 ${className}`}>
        {isLoading ? (
          <span>Loading session...</span>
        ) : error ? (
          <span className="text-red-500">Session error</span>
        ) : sessionId ? (
          <span>Session: {sessionId.slice(-8)}</span>
        ) : (
          <span>No session</span>
        )}
      </div>
    );
  }

  return (
    <div className={`p-4 bg-gray-50 rounded-lg border ${className}`}>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Session Information</h3>
      
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-600">Status:</span>
          <span className={`font-medium ${
            isLoading ? 'text-yellow-600' : 
            error ? 'text-red-600' : 
            sessionId ? 'text-green-600' : 'text-gray-600'
          }`}>
            {isLoading ? 'Loading...' : 
             error ? 'Error' : 
             sessionId ? 'Active' : 'None'}
          </span>
        </div>
        
        {sessionId && (
          <>
            <div className="flex justify-between">
              <span className="text-gray-600">Session ID:</span>
              <span className="font-mono text-gray-800">{sessionId.slice(-12)}</span>
            </div>
            
            <div className="flex justify-between">
              <span className="text-gray-600">Type:</span>
              <span className="text-gray-800">{isNewSession ? 'New' : 'Existing'}</span>
            </div>
          </>
        )}
        
        {error && (
          <div className="flex justify-between">
            <span className="text-gray-600">Error:</span>
            <span className="text-red-600 text-xs">{error}</span>
          </div>
        )}
      </div>
      
      <div className="mt-3 flex space-x-2">
        <button
          onClick={refreshSession}
          disabled={isLoading}
          className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
        >
          Refresh
        </button>
        
        <button
          onClick={createNewSession}
          disabled={isLoading}
          className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50"
        >
          New Session
        </button>
        
        <button
          onClick={clearSession}
          disabled={isLoading || !sessionId}
          className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
        >
          Clear
        </button>
      </div>
    </div>
  );
}
