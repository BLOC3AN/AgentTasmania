import { NextRequest, NextResponse } from 'next/server';
import { getOrCreateSessionId, createSessionResponse, isValidSessionId } from '@/lib/session';

// Chat API endpoint that connects to the AI Core Service
// Use internal Docker network URL for server-side requests
const AI_CORE_URL = 'http://ai-core:8000';

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    // Get or create session ID from cookie
    const { sessionId, isNew } = getOrCreateSessionId(request);

    // Validate session ID format
    if (!isValidSessionId(sessionId)) {
      console.warn('Invalid session ID format:', sessionId);
    }

    // Call the AI Core Service
    const agentResponse = await fetch(`${AI_CORE_URL}/api/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        version: "v1.0",
        query: message.trim(),
        session_id: sessionId,
        user_id: "frontend_user",
        channel_id: "frontend",
        llm_model: "gemini-2.0-flash",
        token: ""
      }),
      // Add timeout to prevent hanging requests
      signal: AbortSignal.timeout(30000), // 30 seconds
    });

    if (!agentResponse.ok) {
      console.error(`Agent service error: ${agentResponse.status} ${agentResponse.statusText}`);

      // Fallback response if agent service is unavailable
      const fallbackData = {
        response: "I'm currently experiencing some technical difficulties. Please try again in a moment, or feel free to ask about academic writing topics like APA referencing, source integration, or citation techniques.",
        timestamp: new Date().toISOString(),
        fallback: true,
        session_id: sessionId,
        session_info: {
          session_id: sessionId,
          is_new_session: isNew
        }
      };

      return createSessionResponse(fallbackData, sessionId);
    }

    const data = await agentResponse.json();

    // Create response with session cookie
    const responseData = {
      response: data.llmOutput || data.response || "No response from AI",
      conversation_id: data.session_id || sessionId,
      session_id: sessionId,
      sources_used: data.sources_used || [],
      timestamp: new Date().toISOString(),
      success: data.success,
      model: data.model,
      processing_time: data.response_time_ms,
      session_info: {
        session_id: sessionId,
        is_new_session: isNew
      }
    };

    return createSessionResponse(responseData, sessionId);

  } catch (error) {
    console.error('Chat API error:', error);

    // Get session ID even in error case
    const { sessionId, isNew } = getOrCreateSessionId(request);

    // Provide a helpful fallback response
    const errorData = {
      response: "I'm having trouble connecting to my knowledge base right now. Please try again in a moment. In the meantime, remember that good academic writing involves proper source integration, clear APA citations, and thoughtful analysis of your sources.",
      timestamp: new Date().toISOString(),
      fallback: true,
      session_id: sessionId,
      session_info: {
        session_id: sessionId,
        is_new_session: isNew
      }
    };

    return createSessionResponse(errorData, sessionId);
  }
}

export async function GET() {
  try {
    // Health check that also tests AI Core service connectivity
    const agentResponse = await fetch(`${AI_CORE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 seconds
    });

    const agentHealthy = agentResponse.ok;

    return NextResponse.json({
      status: 'Chat API is running',
      ai_core_service: agentHealthy ? 'connected' : 'disconnected',
      timestamp: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json({
      status: 'Chat API is running',
      ai_core_service: 'disconnected',
      timestamp: new Date().toISOString(),
    });
  }
}
