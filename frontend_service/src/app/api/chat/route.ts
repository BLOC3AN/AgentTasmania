import { NextRequest, NextResponse } from 'next/server';

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

    // Call the AI Core Service
    const agentResponse = await fetch(`${AI_CORE_URL}/api/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        version: "v1.0",
        query: message.trim(),
        session_id: request.headers.get('x-conversation-id') || `frontend_${Date.now()}`,
        user_id: "frontend_user",
        channel_id: "frontend",
        llm_model: "gemini-2.0-flash",
        language: "VietNam",
        token: ""
      }),
      // Add timeout to prevent hanging requests
      signal: AbortSignal.timeout(30000), // 30 seconds
    });

    if (!agentResponse.ok) {
      console.error(`Agent service error: ${agentResponse.status} ${agentResponse.statusText}`);

      // Fallback response if agent service is unavailable
      return NextResponse.json({
        response: "I'm currently experiencing some technical difficulties. Please try again in a moment, or feel free to ask about academic writing topics like APA referencing, source integration, or citation techniques.",
        timestamp: new Date().toISOString(),
        fallback: true,
      });
    }

    const data = await agentResponse.json();

    return NextResponse.json({
      response: data.llmOutput || data.response || "No response from AI",
      conversation_id: data.session_id,
      sources_used: data.sources_used || [],
      timestamp: new Date().toISOString(),
      success: data.success,
      model: data.model,
      processing_time: data.response_time_ms
    });

  } catch (error) {
    console.error('Chat API error:', error);

    // Provide a helpful fallback response
    return NextResponse.json({
      response: "I'm having trouble connecting to my knowledge base right now. Please try again in a moment. In the meantime, remember that good academic writing involves proper source integration, clear APA citations, and thoughtful analysis of your sources.",
      timestamp: new Date().toISOString(),
      fallback: true,
    });
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
  } catch (error) {
    return NextResponse.json({
      status: 'Chat API is running',
      ai_core_service: 'disconnected',
      timestamp: new Date().toISOString(),
    });
  }
}
