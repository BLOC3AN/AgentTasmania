# Text-to-Speech Service

Text-to-Speech service sử dụng OpenAI TTS API để chuyển đổi text thành audio cho AgentTasmania system.

## Tính năng

- **Multiple Voices**: 10 giọng nói khác nhau từ OpenAI
- **Multiple Formats**: Hỗ trợ MP3, Opus, AAC, FLAC, WAV, PCM
- **Speed Control**: Điều chỉnh tốc độ từ 0.25x đến 4.0x
- **AI Integration**: Tự động tích hợp với AI Core responses
- **Real-time Playback**: Phát audio trực tiếp trong UI popup

## API Endpoints

### POST /synthesize
Chuyển đổi text thành speech với các tùy chọn tùy chỉnh.

**Request Body:**
```json
{
  "text": "Text to convert to speech",
  "voice": "coral",
  "response_format": "mp3",
  "speed": 1.0
}
```

**Available Voices:**
- `alloy` - Balanced, neutral voice
- `ash` - Clear, expressive voice  
- `ballad` - Smooth, warm voice
- `coral` - Friendly, conversational voice (default)
- `echo` - Calm, soothing voice
- `fable` - Storytelling voice
- `nova` - Energetic, youthful voice
- `onyx` - Deep, authoritative voice
- `sage` - Wise, mature voice
- `shimmer` - Bright, cheerful voice

**Available Formats:**
- `mp3` - Standard MP3 format (default)
- `opus` - Opus codec
- `aac` - AAC format
- `flac` - Lossless FLAC
- `wav` - Uncompressed WAV
- `pcm` - Raw PCM audio

**Response:** Audio stream with appropriate content-type

### POST /synthesize-from-ai-response
Chuyển đổi AI response thành speech. Tự động extract text từ AI Core response format.

**Request Body:**
```json
{
  "llmOutput": "AI response text to convert",
  "agent_response": "Alternative response field"
}
```

**Response:** MP3 audio stream với voice "coral"

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "text-to-speech",
  "version": "1.0.0",
  "openai_connection": "ok"
}
```

### GET /voices
Lấy danh sách voices và formats có sẵn.

**Response:**
```json
{
  "voices": ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"],
  "default": "coral",
  "formats": ["mp3", "opus", "aac", "flac", "wav", "pcm"]
}
```

## Cách sử dụng

### Với Docker
```bash
# Build image
docker build -t tts-service .

# Run service
docker run -p 8007:8007 --env-file .env tts-service
```

### Với Python
```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn main:app --host 0.0.0.0 --port 8007
```

### Với Docker Compose
```bash
# Start all services including TTS
docker compose up -d

# Start only TTS service
docker compose up -d tts
```

## Environment Variables

Cần có OpenAI API key trong `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Integration với Frontend

TTS service tự động được gọi khi:
1. User sử dụng voice modal (popup mic)
2. AI Core trả về response
3. Frontend gọi TTS service và phát audio

**Flow:**
```
User Voice Input → ASR → AI Core → TTS Service → Audio Playback
```

## Testing

```bash
# Test health endpoint
curl http://localhost:8007/health

# Test basic synthesis
curl -X POST "http://localhost:8007/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "coral"}' \
  --output test.mp3

# Test AI response format
curl -X POST "http://localhost:8007/synthesize-from-ai-response" \
  -H "Content-Type: application/json" \
  -d '{"llmOutput": "This is an AI response"}' \
  --output ai_response.mp3

# Get available voices
curl http://localhost:8007/voices
```

## Error Handling

Service xử lý các lỗi phổ biến:
- Empty text input → HTTP 400
- Invalid voice → HTTP 400  
- Invalid format → HTTP 400
- OpenAI API errors → HTTP 500
- Network timeouts → HTTP 500

## Performance

- **Latency**: ~1-3 giây cho text ngắn
- **Throughput**: Phụ thuộc vào OpenAI API limits
- **Audio Quality**: High quality với tts-1 model
- **File Size**: ~50-100KB cho câu ngắn (MP3)

## Monitoring

Service logs tất cả requests và responses:
```bash
# View logs
docker compose logs -f tts

# Monitor health
curl http://localhost:8007/health
```

## Troubleshooting

**Common Issues:**

1. **OpenAI API Key Missing**
   ```
   Error: OpenAI API key not found
   Solution: Add OPENAI_API_KEY to .env file
   ```

2. **Service Not Starting**
   ```
   Error: Port 8007 already in use
   Solution: Stop existing service or change port
   ```

3. **Audio Not Playing**
   ```
   Error: Frontend can't reach TTS service
   Solution: Check service is running on port 8007
   ```

4. **Poor Audio Quality**
   ```
   Solution: Use "tts-1-hd" model for higher quality
   ```
