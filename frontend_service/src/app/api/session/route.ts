import { NextRequest, NextResponse } from 'next/server';
import { getOrCreateSessionId, createSessionResponse, clearSessionCookie } from '@/lib/session';

/**
 * GET /api/session - Get current session ID or create new one
 */
export async function GET(request: NextRequest) {
  try {
    const { sessionId, isNew } = getOrCreateSessionId(request);
    
    const responseData = {
      session_id: sessionId,
      is_new_session: isNew,
      timestamp: new Date().toISOString(),
      status: 'active'
    };

    return createSessionResponse(responseData, sessionId);
  } catch (error) {
    console.error('Session API error:', error);
    return NextResponse.json(
      { error: 'Failed to get session' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/session - Create new session (force new session)
 */
export async function POST(request: NextRequest) {
  try {
    // Always create a new session
    const { sessionId } = getOrCreateSessionId(request);
    
    const responseData = {
      session_id: sessionId,
      is_new_session: true,
      timestamp: new Date().toISOString(),
      status: 'created'
    };

    return createSessionResponse(responseData, sessionId);
  } catch (error) {
    console.error('Session creation error:', error);
    return NextResponse.json(
      { error: 'Failed to create session' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/session - Clear current session
 */
export async function DELETE() {
  try {
    const response = NextResponse.json({
      message: 'Session cleared',
      timestamp: new Date().toISOString(),
      status: 'cleared'
    });

    return clearSessionCookie(response);
  } catch (error) {
    console.error('Session deletion error:', error);
    return NextResponse.json(
      { error: 'Failed to clear session' },
      { status: 500 }
    );
  }
}
