import gc
import logging
import base64
import json
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import soundfile as sf
import torch
import librosa
import io
from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import WhisperProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for model and processor
model = None
processor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global model, processor
    try:
        logger.info("Loading ASR model...")
        model = ORTModelForSpeechSeq2Seq.from_pretrained(
            "./onnx-whisper-tiny",
            provider="CPUExecutionProvider"
        )
        processor = WhisperProcessor.from_pretrained("./onnx-whisper-tiny")
        logger.info("ASR model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    # Shutdown
    logger.info("ASR service shutting down")

app = FastAPI(
    title="ASR WebSocket Service",
    description="Real-time Speech Recognition service using Whisper ONNX",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "healthy", "model": "whisper-tiny"}

def process_audio_data(audio_data: bytes) -> str:
    """Process audio data and return transcription"""
    global model, processor

    if model is None or processor is None:
        raise Exception("Model not loaded")

    try:
        # Load audio from bytes
        audio, rate = sf.read(io.BytesIO(audio_data))

        # Resample to 16kHz if needed (Whisper requirement)
        target_sr = 16000
        if rate != target_sr:
            logger.info(f"Resampling audio from {rate}Hz to {target_sr}Hz")
            audio = librosa.resample(audio, orig_sr=rate, target_sr=target_sr)
            rate = target_sr

        # Ensure mono audio
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # Process audio with Whisper
        inputs = processor(audio, sampling_rate=rate, return_tensors="pt")

        # Inference
        with torch.no_grad():
            generated_ids = model.generate(**inputs)

        # Decode
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Clean up memory
        del inputs, generated_ids
        gc.collect()

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
