#!/usr/bin/env python3
"""
Smart Microphone with Voice Activity Detection
- Auto-start recording when voice detected
- Auto-stop when silence detected
"""

import streamlit as st
import pyaudio
import wave
import requests
import tempfile
import os
import time
import numpy as np

# Configuration
STT_ENDPOINT = "https://s6rou7ayi3jrzc-3000.proxy.runpod.net/asr"
CHUNK = 4096  # Larger buffer to prevent overflow
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # Standard sample rate
SILENCE_THRESHOLD = 67  # Adjusted based on calibration
SILENCE_DURATION = 2.0   # Seconds of silence before stopping
MIN_RECORDING_TIME = 1.0 # Minimum recording time

def get_audio_level(data):
    """Calculate RMS audio level"""
    try:
        audio_data = np.frombuffer(data, dtype=np.int16)
        if len(audio_data) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio_data**2))
        return float(rms) if not np.isnan(rms) else 0.0
    except:
        return 0.0

def record_with_vad(silence_threshold=SILENCE_THRESHOLD, silence_duration=SILENCE_DURATION, min_recording_time=MIN_RECORDING_TIME):
    """Record with Voice Activity Detection"""
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    frames = []
    recording = False
    silence_start = None
    start_time = time.time()

    # UI elements
    status_placeholder = st.empty()
    level_placeholder = st.empty()
    time_placeholder = st.empty()
    stop_button_placeholder = st.empty()

    try:
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                level = get_audio_level(data)
            except Exception:
                continue

            current_time = time.time() - start_time

            # Show stop button when recording
            if recording:
                if stop_button_placeholder.button("🛑 Stop Recording", key=f"stop_{int(time.time()*1000)}"):
                    status_placeholder.info("🛑 Manual stop")
                    break

            # Update UI with threshold indicator
            progress_value = max(0.0, min(level / 3000, 1.0))
            if not np.isnan(progress_value):
                level_placeholder.progress(progress_value)

            # Show current level vs threshold
            level_status = "🔴 VOICE" if level > silence_threshold else "🟢 QUIET"
            time_placeholder.text(f"Time: {current_time:.1f}s | Level: {int(level)} | Threshold: {int(silence_threshold)} | {level_status}")
            
            if level > silence_threshold:
                if not recording:
                    recording = True
                    status_placeholder.success("🎤 Recording started...")
                    start_time = time.time()
                
                frames.append(data)
                silence_start = None
                
            else:
                if recording:
                    frames.append(data)
                    
                    if silence_start is None:
                        silence_start = time.time()
                    
                    silence_dur = time.time() - silence_start

                    if silence_dur >= silence_duration and current_time >= min_recording_time:
                        status_placeholder.info("🔇 Silence detected - stopping...")
                        break
                else:
                    status_placeholder.info("🎧 Listening for voice...")
            
            # Safety timeout
            if current_time > 30:  # Max 30 seconds
                status_placeholder.warning("⏰ Timeout - stopping...")
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # Clear UI
        status_placeholder.empty()
        level_placeholder.empty()
        time_placeholder.empty()
    
    if not frames:
        return None
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return temp_file.name

def calibrate_noise_floor(duration=3):
    """Calibrate noise floor for better threshold detection"""
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    levels = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        for i in range(0, int(RATE / CHUNK * duration)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                level = get_audio_level(data)
            except Exception:
                continue
            levels.append(level)

            progress = (i + 1) / (RATE / CHUNK * duration)
            progress_bar.progress(progress)
            status_text.text(f"Calibrating... {progress*100:.0f}% | Current: {int(level)}")

    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        progress_bar.empty()
        status_text.empty()

    if levels:
        avg_noise = np.mean(levels)
        recommended_threshold = avg_noise * 3  # 3x noise floor
        return int(recommended_threshold)
    return SILENCE_THRESHOLD

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
        page_title="Smart Mic",
        page_icon="🎙️",
        layout="centered"
    )
    
    st.title("🎙️ Smart Microphone")
    st.markdown("Voice Activity Detection - Auto start/stop recording")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    
    # Settings
    with st.expander("⚙️ Settings"):
        col1, col2 = st.columns(2)
        with col1:
            silence_threshold = st.slider("Silence Threshold", 0, 200, 67)
            silence_duration = st.slider("Silence Duration (s)", 0.5, 5.0, SILENCE_DURATION, 0.1)

            if st.button("🎯 Auto Calibrate"):
                with st.spinner("🎯 Calibrating noise floor... Stay quiet!"):
                    recommended = calibrate_noise_floor()
                    st.success(f"✅ Recommended threshold: {recommended}")
                    st.info("Adjust the slider above to this value")
        with col2:
            min_recording = st.slider("Min Recording (s)", 0.5, 3.0, MIN_RECORDING_TIME, 0.1)
            st.markdown(f"**Sample Rate:** {RATE} Hz")
            st.markdown(f"**Current Threshold:** {silence_threshold}")
    
    # Main controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎙️ Start Smart Recording", type="primary", disabled=st.session_state.recording):
            st.session_state.recording = True
            
            try:
                st.info("🎧 Listening for voice... Speak to start recording")
                
                # Record with VAD
                audio_file = record_with_vad(silence_threshold, silence_duration, min_recording)
                
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
                    st.warning("⚠️ No voice detected")
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                st.session_state.recording = False
    
    with col2:
        if st.session_state.results:
            if st.button("🗑️ Clear Results"):
                st.session_state.results = []
    
    # Display results
    if st.session_state.results:
        st.markdown("---")
        st.subheader("📚 Results")
        
        for result in reversed(st.session_state.results):
            with st.expander(f"🕐 {result['timestamp']} - {result['text'][:30]}..."):
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
        st.header("📋 How it works")
        st.markdown("""
        1. **Click 'Start Smart Recording'**
        2. **Speak into microphone** - recording starts automatically
        3. **Stop speaking** - recording stops after 2s silence
        4. **View transcription** result
        
        **Features:**
        - 🎧 Auto-detect voice
        - 🔇 Auto-stop on silence
        - 📊 Real-time audio level
        - ⏱️ Performance metrics
        """)
        
        st.markdown("---")
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

if __name__ == "__main__":
    main()
