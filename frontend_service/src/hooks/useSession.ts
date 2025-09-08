import { useState, useEffect, useCallback } from 'react';

interface SessionInfo {
  session_id: string;
  is_new_session: boolean;
  timestamp: string;
  status: string;
}

interface UseSessionReturn {
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  isNewSession: boolean;
  refreshSession: () => Promise<void>;
  clearSession: () => Promise<void>;
  createNewSession: () => Promise<void>;
}

export function useSession(): UseSessionReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNewSession, setIsNewSession] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/session', {
        method: 'GET',
        credentials: 'include', // Include cookies
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch session: ${response.status}`);
      }

      const data: SessionInfo = await response.json();
      setSessionId(data.session_id);
      setIsNewSession(data.is_new_session);
      
      console.log('Session loaded:', {
        sessionId: data.session_id,
        isNew: data.is_new_session,
        status: data.status
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Session fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshSession = useCallback(async () => {
    await fetchSession();
  }, [fetchSession]);

  const clearSession = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/session', {
        method: 'DELETE',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to clear session: ${response.status}`);
      }

      setSessionId(null);
      setIsNewSession(false);
      
      console.log('Session cleared');

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Session clear error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createNewSession = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/session', {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.status}`);
      }

      const data: SessionInfo = await response.json();
      setSessionId(data.session_id);
      setIsNewSession(true);
      
      console.log('New session created:', {
        sessionId: data.session_id,
        status: data.status
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Session creation error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize session on mount
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  return {
    sessionId,
    isLoading,
    error,
    isNewSession,
    refreshSession,
    clearSession,
    createNewSession,
  };
}
