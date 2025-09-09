import gc
import logging
import base64
import json
import numpy as np
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
import soundfile as sf
import torch
import io
import whisper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for model
model = None
device = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global model, device
    try:
        logger.info("Loading ASR model...")

        # Check for GPU availability
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
        else:
            device = "cpu"
            logger.info("No GPU detected, using CPU")

        # Load Whisper model (try base for better speed/quality balance)
        model = whisper.load_model("base.en", device=device)
        logger.info(f"Whisper model loaded successfully on {device}")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    # Shutdown
    logger.info("ASR service shutting down")

app = FastAPI(
    title="ASR WebSocket Service",
    description="Real-time Speech Recognition service using Whisper",
    version="1.0.0",
    lifespan=lifespan
)

# Add compression middleware
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "healthy", "model": "whisper-base.en", "device": device}

@app.post("/asr")
async def transcribe_audio(file: UploadFile = File(...)):
    """HTTP endpoint for audio transcription"""
    start_time = time.time()
    logger.info(f"=== ASR Request Started ===")

    if model is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    # Validate file type
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    try:
        # Read file content
        read_start = time.time()
        audio_bytes = await file.read()
        read_time = time.time() - read_start
        logger.info(f"File read time: {read_time:.3f}s, size: {len(audio_bytes)} bytes")

        # Process audio and get transcription
        process_start = time.time()
        transcription = process_audio_data(audio_bytes)
        process_time = time.time() - process_start

        total_time = time.time() - start_time
        logger.info(f"Processing time: {process_time:.3f}s")
        logger.info(f"Total request time: {total_time:.3f}s")
        logger.info(f"=== ASR Request Completed ===")

        return {
            "status": "success",
            "transcription": transcription,
            "filename": file.filename,
            "device": device,
            "timing": {
                "file_read": f"{read_time:.3f}s",
                "processing": f"{process_time:.3f}s",
                "total": f"{total_time:.3f}s"
            }
        }

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

def process_audio_data(audio_data: bytes) -> str:
    """Process audio data and return transcription"""
    global model

    if model is None:
        raise Exception("Model not loaded")

    try:
        # Load audio from bytes
        load_start = time.time()
        audio, rate = sf.read(io.BytesIO(audio_data))
        load_time = time.time() - load_start
        logger.info(f"Audio load time: {load_time:.3f}s, rate: {rate}Hz, shape: {audio.shape}")

        # Ensure audio is float32 (required by Whisper)
        prep_start = time.time()
        audio = audio.astype(np.float32)

        # Convert to mono if stereo (simple average)
        if len(audio.shape) > 1:
            logger.info("Converting stereo to mono")
            audio = np.mean(audio, axis=1)

        prep_time = time.time() - prep_start
        logger.info(f"Audio preprocessing time: {prep_time:.3f}s, final shape: {audio.shape}")

        # Let Whisper handle resampling internally (faster than librosa)
        # Whisper automatically resamples to 16kHz

        # Transcribe with Whisper (includes automatic preprocessing)
        transcribe_start = time.time()
        logger.info("Starting Whisper transcription...")
        result = model.transcribe(
            audio,
            language="en",  # Force English for faster processing
            task="transcribe",  # Explicit task
            fp16=True if device == "cuda" else False,  # Use FP16 on GPU for speed
            verbose=False,  # Reduce logging overhead
            # Performance optimizations
            beam_size=1,  # Faster beam search (default is 5)
            best_of=1,    # Only generate 1 candidate (default is 5)
            temperature=0,  # Deterministic output, faster
            compression_ratio_threshold=2.4,  # Skip low-quality segments faster
            no_speech_threshold=0.6,  # Skip silence faster
            condition_on_previous_text=False  # Don't use context, faster
        )
        transcribe_time = time.time() - transcribe_start
        logger.info(f"Whisper transcription time: {transcribe_time:.3f}s")

        text = result["text"].strip()
        logger.info(f"Transcription result: '{text}'")

        # Clean up memory
        cleanup_start = time.time()
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        cleanup_time = time.time() - cleanup_start
        logger.info(f"Memory cleanup time: {cleanup_time:.3f}s")

        return text

    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        raise e

@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    """WebSocket endpoint for real-time ASR"""
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()

            try:
                # Parse JSON message
                data = json.loads(message)

                if data.get("type") == "audio":
                    # Decode base64 audio data
                    audio_base64 = data.get("data")
                    if not audio_base64:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "No audio data provided"
                        }))
                        continue

                    # Decode base64 to bytes
                    audio_bytes = base64.b64decode(audio_base64)

                    # Process audio and get transcription
                    transcription = process_audio_data(audio_bytes)

                    # Send transcription back to client
                    response = {
                        "type": "transcription",
                        "text": transcription,
                        "status": "success"
                    }
                    await websocket.send_text(json.dumps(response))

                elif data.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "status": "healthy"
                    }))

                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {data.get('type')}"
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Processing error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Processing failed: {str(e)}"
                }))

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
