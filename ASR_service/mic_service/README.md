# Mic Service

Microphone service với Voice Activity Detection (VAD) sử dụng Silero VAD và Streamlit.

## Tính năng

- **Smart Microphone** (`smart_mic.py`): Tự động phát hiện giọng nói và bắt đầu/dừng ghi âm
- **Simple Microphone** (`mic_app.py`): Ghi âm với thời gian cố định

## Cách sử dụng với Docker

### Build Docker image

```bash
cd ASR_service/mic_service
docker build -t mic-service .
```

### Chạy Smart Microphone (mặc định)

```bash
docker run -p 8501:8501 --device /dev/snd mic-service
```

### Chạy Simple Microphone

```bash
docker run -p 8501:8501 --device /dev/snd mic-service streamlit run mic_app.py --server.port=8501 --server.address=0.0.0.0
```

### Truy cập ứng dụng

Mở trình duyệt và truy cập: `http://localhost:8501`

## Cấu hình

- **Port**: 8501 (Streamlit default)
- **STT Endpoint**: Được cấu hình trong code để kết nối với ASR service
- **Audio Device**: Sử dụng microphone mặc định của hệ thống

## Yêu cầu hệ thống

- Docker
- Microphone device
- Audio drivers (ALSA trên Linux)

## Lưu ý

- Container cần quyền truy cập audio device (`--device /dev/snd`)
- Silero VAD model sẽ được tải xuống tự động khi build image
