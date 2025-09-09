#!/bin/bash

# Smart Microphone Launcher with ALSA optimization
# This script sets up the environment and runs the Smart Microphone app

echo "🎙️ Starting Smart Microphone with Silero VAD"
echo "=============================================="

# Set ALSA environment variables to reduce warnings
export ALSA_PCM_CARD=0
export ALSA_PCM_DEVICE=0

# Suppress ALSA warnings in the terminal
export ALSA_CARD=0

echo "🔧 Setting up audio environment..."
echo "   ALSA_PCM_CARD=$ALSA_PCM_CARD"
echo "   ALSA_PCM_DEVICE=$ALSA_PCM_DEVICE"

# Check if required packages are installed
echo ""
echo "🔍 Checking dependencies..."

# Check Python packages
python3 -c "import streamlit, pyaudio, torch, silero_vad" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ All Python packages are installed"
else
    echo "   ❌ Missing Python packages. Installing..."
    pip install -r requirements.txt
fi

# Check audio system
echo ""
echo "🎤 Testing audio system..."
python3 test_audio_system.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Audio system is ready"
else
    echo "   ⚠️ Audio system test failed, but continuing..."
fi

echo ""
echo "🚀 Launching Smart Microphone..."
echo "   Press Ctrl+C to stop"
echo ""

# Find available port
PORT=8501
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo "   Access the app at: http://localhost:$PORT"
echo "   Using port: $PORT"

# Run Streamlit with optimized settings
streamlit run smart_mic.py \
    --server.headless true \
    --server.port $PORT \
    --server.address localhost \
    --browser.gatherUsageStats false \
    --logger.level error

echo ""
echo "👋 Smart Microphone stopped"
