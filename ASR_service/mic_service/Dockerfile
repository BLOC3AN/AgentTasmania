FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY smart_mic.py .
COPY mic_app.py .

# Pre-download Silero VAD model during build
RUN echo "Pre-downloading Silero VAD model..." && \
    python -c "from silero_vad import load_silero_vad; load_silero_vad()" && \
    echo "Silero VAD model download completed successfully"

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command to run smart_mic.py
# Can be overridden to run mic_app.py: docker run -p 8501:8501 mic-service streamlit run mic_app.py --server.port=8501 --server.address=0.0.0.0
CMD ["streamlit", "run", "smart_mic.py", "--server.port=8501", "--server.address=0.0.0.0"]
