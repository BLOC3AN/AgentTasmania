import { NextRequest, NextResponse } from 'next/server';

// Chat API endpoint that connects to the Agent Model Service
const AGENT_MODEL_URL = process.env.AGENT_MODEL_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    // Call the Agent Model Service
    const agentResponse = await fetch(`${AGENT_MODEL_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message.trim(),
        conversation_id: request.headers.get('x-conversation-id') || undefined,
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
      response: data.response,
      conversation_id: data.conversation_id,
      sources_used: data.sources_used || [],
      timestamp: new Date().toISOString(),
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
    // Health check that also tests agent service connectivity
    const agentResponse = await fetch(`${AGENT_MODEL_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 seconds
    });

    const agentHealthy = agentResponse.ok;

    return NextResponse.json({
      status: 'Chat API is running',
      agent_service: agentHealthy ? 'connected' : 'disconnected',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json({
      status: 'Chat API is running',
      agent_service: 'disconnected',
      timestamp: new Date().toISOString(),
    });
  }
}
