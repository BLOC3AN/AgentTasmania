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
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for model
model = None
device = None

# Audio buffering configuration
MIN_AUDIO_DURATION = 2.5  # Minimum 2.5 seconds before transcription
MAX_AUDIO_DURATION = 15.0  # Maximum 15 seconds to prevent memory issues
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection
SILENCE_DURATION_FOR_TRANSCRIPTION = 1.5  # Wait 1.5 seconds of silence before transcribing

class AudioBuffer:
    """Buffer audio chunks for better transcription quality"""

    def __init__(self):
        self.buffer = []
        self.total_samples = 0
        self.last_activity = time.time()
        self.last_silence_start = None

    def add_chunk(self, audio_chunk: np.ndarray) -> bool:
        """Add audio chunk to buffer. Returns True if ready for transcription."""
        self.buffer.append(audio_chunk)
        self.total_samples += len(audio_chunk)

        # Check if chunk has significant audio activity
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        current_time = time.time()

        if rms > SILENCE_THRESHOLD:
            # Speech detected
            self.last_activity = current_time
            self.last_silence_start = None
        else:
            # Silence detected
            if self.last_silence_start is None:
                self.last_silence_start = current_time

        # Calculate current duration
        duration = self.total_samples / SAMPLE_RATE

        # Ready for transcription if:
        # 1. We have minimum duration AND sufficient silence duration after speech
        # 2. OR we've reached maximum duration (prevent memory issues)

        if duration >= MAX_AUDIO_DURATION:
            return True

        if duration >= MIN_AUDIO_DURATION:
            # Check if we have enough silence after the last speech
            if self.last_silence_start is not None:
                silence_duration = current_time - self.last_silence_start
                if silence_duration >= SILENCE_DURATION_FOR_TRANSCRIPTION:
                    return True

        return False

    def get_audio(self) -> np.ndarray:
        """Get concatenated audio from buffer"""
        if not self.buffer:
            return np.array([])
        return np.concatenate(self.buffer)

    def clear(self):
        """Clear the buffer"""
        self.buffer = []
        self.total_samples = 0
        self.last_activity = time.time()
        self.last_silence_start = None

    def is_empty(self) -> bool:
        return len(self.buffer) == 0

    def duration(self) -> float:
        return self.total_samples / SAMPLE_RATE

# Global audio buffers for each connection
audio_buffers: Dict[str, AudioBuffer] = {}

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

        # Try to detect if it's raw PCM data or formatted audio file
        try:
            # First try to read as formatted audio file (WAV, etc.)
            audio, rate = sf.read(io.BytesIO(audio_data))
            logger.info(f"Loaded as formatted audio file: rate={rate}Hz, shape={audio.shape}")
        except:
            # If that fails, treat as raw PCM data (16-bit, 16kHz, mono)
            logger.info(f"Treating as raw PCM data: {len(audio_data)} bytes")

            # Convert raw PCM bytes to numpy array (16-bit signed integers)
            audio_samples = np.frombuffer(audio_data, dtype=np.int16)

            # Convert to float32 and normalize to [-1, 1] range
            audio = audio_samples.astype(np.float32) / 32768.0
            rate = 16000  # Assume 16kHz sample rate for raw PCM

            logger.info(f"Converted PCM: {len(audio_samples)} samples, rate={rate}Hz")

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

def is_likely_formatted_audio(audio_bytes: bytes) -> bool:
    """Quick check if bytes are likely a formatted audio file (WAV, MP3, etc.)"""
    if len(audio_bytes) < 12:
        return False

    # Check for common audio file headers
    header = audio_bytes[:12]

    # WAV file signature
    if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
        return True

    # FLAC file signature
    if header[:4] == b'fLaC':
        return True

    # OGG file signature
    if header[:4] == b'OggS':
        return True

    # M4A/AAC file signature
    if header[4:8] == b'ftyp':
        return True

    # If it's exactly 8192 bytes (common chunk size), likely raw PCM
    if len(audio_bytes) == 8192:
        return False

    # Additional heuristics for raw PCM vs formatted audio
    # Raw PCM typically has more uniform byte distribution
    # Formatted audio files have structured headers with specific patterns

    # Check for too many null bytes (unlikely in audio headers)
    null_count = audio_bytes[:100].count(0)
    if null_count > 50:  # More than 50% nulls in first 100 bytes
        return False

    # Check for very high byte values (common in raw PCM)
    high_byte_count = sum(1 for b in audio_bytes[:100] if b > 200)
    if high_byte_count > 20:  # Many high values suggest raw PCM
        return False

    # If we can't definitively identify it as formatted audio, assume PCM
    return False

async def process_audio_with_buffer(websocket: WebSocket, connection_id: str, audio_bytes: bytes):
    """Process audio using buffering for better transcription quality"""
    try:
        # Convert audio bytes to numpy array with consistent format
        if is_likely_formatted_audio(audio_bytes):
            try:
                # Read as formatted audio file (WAV, etc.)
                audio, rate = sf.read(io.BytesIO(audio_bytes))
                logger.info(f"Loaded as formatted audio file: rate={rate}Hz, shape={audio.shape}")

                # Normalize to mono and standard sample rate
                if len(audio.shape) > 1:
                    # Convert stereo to mono
                    audio = np.mean(audio, axis=1)
                    logger.info("Converted stereo to mono")

                # Ensure float32 format
                audio = audio.astype(np.float32)

            except Exception as e:
                logger.warning(f"Failed to read as formatted audio: {e}, falling back to PCM")
                # Fallback to PCM
                audio_samples = np.frombuffer(audio_bytes, dtype=np.int16)
                audio = audio_samples.astype(np.float32) / 32768.0
                rate = 16000
        else:
            # Treat as raw PCM data (16-bit, 16kHz, mono)
            audio_samples = np.frombuffer(audio_bytes, dtype=np.int16)
            audio = audio_samples.astype(np.float32) / 32768.0
            rate = 16000
            # Only log occasionally to reduce noise
            if len(audio_samples) % 16384 == 0:  # Log every 4th chunk
                logger.info(f"Converted PCM: {len(audio_samples)} samples, rate={rate}Hz")

        # Get buffer for this connection
        buffer = audio_buffers.get(connection_id)
        if not buffer:
            logger.error(f"No buffer found for connection {connection_id}")
            return

        # Add chunk to buffer
        ready_for_transcription = buffer.add_chunk(audio)

        logger.info(f"Buffer status: {buffer.duration():.2f}s, ready: {ready_for_transcription}")

        # If buffer is ready, transcribe and send result
        if ready_for_transcription:
            buffered_audio = buffer.get_audio()

            # Only transcribe if we have significant audio content
            rms = np.sqrt(np.mean(buffered_audio ** 2))
            if rms > SILENCE_THRESHOLD:
                logger.info(f"Transcribing buffered audio: {len(buffered_audio)} samples ({buffer.duration():.2f}s)")

                # Transcribe the buffered audio
                transcription = await transcribe_audio_array(buffered_audio)

                # Send transcription back to client
                if transcription.strip():  # Only send non-empty transcriptions
                    response = {
                        "type": "transcription",
                        "data": {
                            "text": transcription,
                            "isFinal": True,
                            "confidence": 0.9,
                            "source": "external_asr"
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info(f"Sent transcription: '{transcription}'")
            else:
                logger.info(f"Skipping transcription - audio too quiet (RMS: {rms:.4f})")

            # Clear buffer after transcription
            buffer.clear()

    except Exception as e:
        logger.error(f"Buffer processing error: {e}")
        # Send error response
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Buffer processing failed: {str(e)}"
        }))

async def transcribe_audio_array(audio: np.ndarray) -> str:
    """Transcribe audio numpy array using Whisper"""
    global model

    if model is None:
        raise Exception("Model not loaded")

    try:
        logger.info("Starting Whisper transcription...")
        transcribe_start = time.time()

        # Whisper transcription with optimized settings
        result = model.transcribe(
            audio,
            fp16=device == "cuda",
            beam_size=1,
            best_of=1,
            temperature=0,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            condition_on_previous_text=False
        )

        transcribe_time = time.time() - transcribe_start
        logger.info(f"Whisper transcription time: {transcribe_time:.3f}s")

        text = result["text"].strip()
        logger.info(f"Transcription result: '{text}'")

        # Clean up memory
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

        return text

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise e

@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    """WebSocket endpoint for real-time ASR"""
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Create unique connection ID and audio buffer
    connection_id = f"conn_{id(websocket)}"
    audio_buffers[connection_id] = AudioBuffer()

    try:
        while True:
            # Receive message from client (can be text or binary)
            message = await websocket.receive()

            try:
                # Handle different message types
                if "text" in message:
                    # Handle text message (JSON)
                    text_data = message["text"]
                    data = json.loads(text_data)

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

                        # Process with buffering
                        await process_audio_with_buffer(websocket, connection_id, audio_bytes)

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

                elif "bytes" in message:
                    # Handle binary message (direct audio data)
                    audio_bytes = message["bytes"]
                    logger.info(f"Received binary audio data: {len(audio_bytes)} bytes")

                    # Process with buffering
                    await process_audio_with_buffer(websocket, connection_id, audio_bytes)

                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Unknown message format"
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
        # Clean up buffer
        if connection_id in audio_buffers:
            del audio_buffers[connection_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Clean up buffer
        if connection_id in audio_buffers:
            del audio_buffers[connection_id]
