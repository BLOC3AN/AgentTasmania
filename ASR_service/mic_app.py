#!/usr/bin/env python3
"""
Simple Microphone Recording App
- Record for fixed duration
- Send to STT service
"""

import streamlit as st
import pyaudio
import wave
import requests
import tempfile
import os
import time

# Configuration
STT_ENDPOINT = "https://s6rou7ayi3jrzc-3000.proxy.runpod.net/asr"

def record_audio(duration=5):
    """Record audio for specified duration"""
    CHUNK = 4096  # Larger buffer to prevent overflow
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100  # Standard sample rate
    
    audio = pyaudio.PyAudio()
    
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    frames = []
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, int(RATE / CHUNK * duration)):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        except Exception:
            continue
        
        # Update progress
        progress = (i + 1) / (RATE / CHUNK * duration)
        progress_bar.progress(progress)
        status_text.text(f"Recording... {progress*100:.0f}%")
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    progress_bar.empty()
    status_text.empty()
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return temp_file.name

def send_to_stt(audio_file_path):
    """Send audio file to STT service"""
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_file_path), f, 'audio/wav')}
            
            start_time = time.time()
            response = requests.post(STT_ENDPOINT, files=files, timeout=60)
            total_time = time.time() - start_time
            
        if response.status_code == 200:
            result = response.json()
            result['client_time'] = f"{total_time:.3f}s"
            return result
        else:
            return {"error": f"STT Error: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Error: {e}"}

def main():
    st.set_page_config(
        page_title="Mic Recorder",
        page_icon="🎤",
        layout="centered"
    )
    
    st.title("🎤 Microphone Recorder")
    st.markdown("Record audio and transcribe with STT service")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    
    # Controls
    col1, col2 = st.columns(2)
    
    with col1:
        duration = st.slider("Duration (seconds)", 1, 10, 5)
    
    with col2:
        if st.button("🎤 Record & Transcribe", type="primary"):
            try:
                st.info(f"🎤 Recording for {duration} seconds...")
                
                # Record audio
                audio_file = record_audio(duration)
                
                if audio_file:
                    st.success("✅ Recording completed!")
                    
                    # Send to STT
                    with st.spinner('🤖 Processing...'):
                        result = send_to_stt(audio_file)
                    
                    if 'error' not in result:
                        transcription = result.get('transcription', 'No transcription')
                        timing = result.get('timing', {})
                        device = result.get('device', 'unknown')
                        backend = result.get('backend', 'unknown')
                        client_time = result.get('client_time', 'N/A')
                        
                        # Display result
                        st.markdown("---")
                        st.subheader("📝 Result")
                        st.markdown(f"**Text:** {transcription}")
                        
                        # Performance metrics
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Device:** {device}")
                            st.markdown(f"**Backend:** {backend}")
                        with col2:
                            if timing:
                                st.markdown(f"**Processing:** {timing.get('processing', 'N/A')}")
                                st.markdown(f"**Server Total:** {timing.get('total', 'N/A')}")
                            st.markdown(f"**Client Total:** {client_time}")
                        
                        # Add to results
                        st.session_state.results.append({
                            'timestamp': time.strftime('%H:%M:%S'),
                            'duration': f"{duration}s",
                            'text': transcription,
                            'timing': timing,
                            'device': device,
                            'backend': backend,
                            'client_time': client_time
                        })
                    else:
                        st.error(f"❌ {result['error']}")
                    
                    # Cleanup
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
                else:
                    st.warning("⚠️ No audio recorded")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # Clear results
    if st.session_state.results:
        if st.button("🗑️ Clear Results"):
            st.session_state.results = []
    
    # Display results
    if st.session_state.results:
        st.markdown("---")
        st.subheader("📚 Results")
        
        for i, result in enumerate(reversed(st.session_state.results)):
            with st.expander(f"🕐 {result['timestamp']} - {result['text'][:30]}..."):
                st.markdown(f"**Duration:** {result['duration']}")
                st.markdown(f"**Text:** {result['text']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Device:** {result['device']}")
                    st.markdown(f"**Backend:** {result['backend']}")
                with col2:
                    timing = result['timing']
                    if timing:
                        st.markdown(f"**Processing:** {timing.get('processing', 'N/A')}")
                        st.markdown(f"**Server Total:** {timing.get('total', 'N/A')}")
                    st.markdown(f"**Client Total:** {result['client_time']}")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown(f"**Endpoint:** `{STT_ENDPOINT}`")
        
        if st.button("🔧 Test Connection"):
            try:
                response = requests.get(STT_ENDPOINT.replace('/asr', '/health'), timeout=5)
                if response.status_code == 200:
                    health = response.json()
                    st.success("✅ Service Online")
                    st.json(health)
                else:
                    st.error("❌ Service Error")
            except:
                st.error("❌ Cannot connect")
        
        st.markdown("---")
        st.markdown("### 📋 Instructions")
        st.markdown("""
        1. Set recording duration (1-10 seconds)
        2. Click 'Record & Transcribe'
        3. Speak into microphone during recording
        4. View transcription result
        """)

if __name__ == "__main__":
    main()
