import { NextRequest, NextResponse } from 'next/server';

// Simple chat API endpoint for demonstration
// In a real implementation, this would connect to your actual AI agent service

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Simple response logic based on keywords
    let response = "I understand you're asking about academic writing. ";
    
    if (message.toLowerCase().includes('apa')) {
      response += "APA style is crucial for academic writing. Remember to include in-text citations with author and year, like (Smith, 2023). For direct quotes, also include page numbers.";
    } else if (message.toLowerCase().includes('quote') || message.toLowerCase().includes('citation')) {
      response += "When using direct quotes, remember the 'sandwich' method: introduce the quote, present it with proper citation, then explain its significance to your argument.";
    } else if (message.toLowerCase().includes('paraphrase')) {
      response += "Paraphrasing involves converting another author's ideas into your own words while maintaining the original meaning. It's useful when a direct quote would disrupt your writing flow.";
    } else if (message.toLowerCase().includes('source')) {
      response += "Sources should serve deliberate purposes in your writing - as evidence, context, theoretical frameworks, or supporting arguments. Each source should contribute meaningfully to your analysis.";
    } else if (message.toLowerCase().includes('reference')) {
      response += "Your reference list should include all sources cited in your text. Follow APA format carefully, and remember that in-text citations must match your reference list entries.";
    } else {
      response += "Could you be more specific about what aspect of academic writing you'd like help with? I can assist with APA referencing, source integration, paraphrasing, or citation techniques.";
    }
    
    return NextResponse.json({
      response,
      timestamp: new Date().toISOString(),
    });
    
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Failed to process message' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'Chat API is running',
    timestamp: new Date().toISOString(),
  });
}
