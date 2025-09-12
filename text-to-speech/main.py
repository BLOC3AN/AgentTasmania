from dotenv import load_dotenv
load_dotenv()

import os
import io
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Text-to-Speech Service",
    description="Convert text to speech using OpenAI TTS API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai_client = AsyncOpenAI()

# Available voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer
AVAILABLE_VOICES = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
AVAILABLE_FORMATS = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

class TTSRequest(BaseModel):
    text: str
    voice: str = "coral"
    response_format: str = "mp3"
    speed: float = 1.0

class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_length: int = 0

@app.post("/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    Convert text to speech using OpenAI TTS API
    """
    try:
        # Validate input
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        if request.voice not in AVAILABLE_VOICES:
            raise HTTPException(status_code=400, detail=f"Voice must be one of: {AVAILABLE_VOICES}")

        if request.response_format not in AVAILABLE_FORMATS:
            raise HTTPException(status_code=400, detail=f"Format must be one of: {AVAILABLE_FORMATS}")

        if not (0.25 <= request.speed <= 4.0):
            raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")

        logger.info(f"🎵 Synthesizing speech: voice={request.voice}, format={request.response_format}, text_length={len(request.text)}")

        # Generate speech using OpenAI TTS
        response = await openai_client.audio.speech.create(
            model="tts-1",  # or "tts-1-hd" for higher quality
            voice=request.voice,
            input=request.text,
            response_format=request.response_format,
            speed=request.speed
        )

        # Convert response to bytes
        audio_data = response.content

        logger.info(f"✅ Speech synthesis completed: {len(audio_data)} bytes")

        # Determine content type based on format
        content_type_map = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/pcm"
        }

        content_type = content_type_map.get(request.response_format, "audio/mpeg")

        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}",
                "Content-Length": str(len(audio_data))
            }
        )

    except Exception as e:
        logger.error(f"❌ TTS Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

@app.post("/synthesize-from-ai-response")
async def synthesize_from_ai_response(ai_response: dict):
    """
    Synthesize speech from AI Core response format
    Expected format: {"llmOutput": "text to speak", ...}
    """
    try:
        # Extract text from AI response
        text = ai_response.get("llmOutput", "")
        if not text:
            text = ai_response.get("agent_response", "")

        if not text:
            raise HTTPException(status_code=400, detail="No text found in AI response")

        # Use default settings for AI responses
        request = TTSRequest(
            text=text,
            voice="coral",
            response_format="mp3",
            speed=1.0
        )

        return await synthesize_speech(request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ AI Response TTS Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process AI response: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test OpenAI client
        await openai_client.models.list()
        return {
            "status": "healthy",
            "service": "text-to-speech",
            "version": "1.0.0",
            "openai_connection": "ok"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "text-to-speech",
            "version": "1.0.0",
            "openai_connection": "failed",
            "error": str(e)
        }

@app.get("/voices")
async def get_available_voices():
    """Get list of available voices"""
    return {
        "voices": AVAILABLE_VOICES,
        "default": "coral",
        "formats": AVAILABLE_FORMATS
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8007))
    uvicorn.run(app, host="0.0.0.0", port=port)