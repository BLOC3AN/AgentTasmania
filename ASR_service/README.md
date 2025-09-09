# ASR Service - Automatic Speech Recognition

## Overview

ASR Service sử dụng Whisper ONNX model để chuyển đổi audio thành text với hiệu suất cao và load balancing.

## Features

- **ONNX Whisper Model**: Sử dụng whisper-tiny model được tối ưu hóa
- **Load Balancing**: 3 instances với nginx load balancer
- **Health Checks**: Monitoring và auto-recovery
- **Error Handling**: Comprehensive error handling và validation
- **Docker Support**: Containerized deployment

## API Endpoints

### POST /asr
Transcribe audio file to text

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: audio file (wav, mp3, flac, m4a, ogg)

**Response:**
```json
{
  "text": "transcribed text here",
  "status": "success"
}
```

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "model": "whisper-tiny"
}
```

## Setup

### Prerequisites
- Docker và Docker Compose
- Internet connection (để download Whisper model lần đầu)

### Automatic Setup
Model sẽ được tự động export sang ONNX trong quá trình build Docker image. Không cần setup manual.

### Run Service
```bash
# Build và start ASR service với load balancing
docker-compose up --build asr-lb asr_1 asr_2

# Or start entire system
docker-compose up --build
```

**Note**: Lần build đầu tiên sẽ mất thời gian để download và export Whisper model (~39MB).

### Test Service
```bash
# Health check
curl http://localhost:8006/health

# Transcribe audio
curl -X POST -F "file=@audio.wav" http://localhost:8006/asr
```

## Load Balancing

Service sử dụng nginx load balancer với 2 ASR instances:
- **asr_1**: Internal port 8006
- **asr_2**: Internal port 8006
- **asr-lb**: External port 8006 (nginx)

Load balancing strategy: `least_conn` với health checks.

## Monitoring

- Health checks mỗi 30s
- Auto-restart nếu unhealthy
- Logs qua Dozzle: http://localhost:5555

## Performance

- Model: whisper-tiny (39MB)
- CPU optimized (ONNX Runtime)
- Memory efficient
- Fast inference time
