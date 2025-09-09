#!/usr/bin/env python3
"""
Debug Microphone - Analyze audio input issues
"""

import streamlit as st
import pyaudio
import numpy as np
import time

# Configuration
CHUNK = 4096  # Larger buffer to prevent overflow
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100  # Standard sample rate

def get_audio_debug(data):
    """Get detailed audio analysis"""
    try:
        audio_data = np.frombuffer(data, dtype=np.int16)
        if len(audio_data) == 0:
            return {
                'rms': 0.0,
                'min': 0,
                'max': 0,
                'mean': 0.0,
                'std': 0.0,
                'clipped': False,
                'zero_count': 0
            }
        
        rms = np.sqrt(np.mean(audio_data**2))
        min_val = np.min(audio_data)
        max_val = np.max(audio_data)
        mean_val = np.mean(audio_data)
        std_val = np.std(audio_data)
        
        # Check for clipping (values at max/min of int16)
        clipped = (max_val >= 32767) or (min_val <= -32768)
        zero_count = np.sum(audio_data == 0)
        
        return {
            'rms': float(rms) if not np.isnan(rms) else 0.0,
            'min': int(min_val),
            'max': int(max_val),
            'mean': float(mean_val),
            'std': float(std_val),
            'clipped': clipped,
            'zero_count': int(zero_count)
        }
    except Exception as e:
        return {
            'error': str(e),
            'rms': 0.0,
            'min': 0,
            'max': 0,
            'mean': 0.0,
            'std': 0.0,
            'clipped': False,
            'zero_count': 0
        }

def list_audio_devices():
    """List available audio input devices"""
    audio = pyaudio.PyAudio()
    devices = []
    
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'rate': info['defaultSampleRate']
            })
    
    audio.terminate()
    return devices

def debug_audio_stream(device_index=None, duration=10):
    """Debug audio stream with detailed analysis"""
    audio = pyaudio.PyAudio()
    
    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK
        )
        
        # UI elements
        status_placeholder = st.empty()
        metrics_placeholder = st.empty()
        chart_placeholder = st.empty()
        
        start_time = time.time()
        rms_history = []
        
        while time.time() - start_time < duration:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                debug_info = get_audio_debug(data)
            except Exception as e:
                st.error(f"Read error: {e}")
                continue
            
            current_time = time.time() - start_time
            rms_history.append(debug_info['rms'])
            
            # Keep only last 50 samples for chart
            if len(rms_history) > 50:
                rms_history.pop(0)
            
            # Update status
            status_placeholder.text(f"Recording... {current_time:.1f}s / {duration}s")
            
            # Update metrics
            with metrics_placeholder.container():
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("RMS Level", f"{debug_info['rms']:.1f}")
                    st.metric("Min Value", debug_info['min'])
                    st.metric("Max Value", debug_info['max'])
                
                with col2:
                    st.metric("Mean", f"{debug_info['mean']:.1f}")
                    st.metric("Std Dev", f"{debug_info['std']:.1f}")
                    st.metric("Zero Count", debug_info['zero_count'])
                
                with col3:
                    clipped_status = "🔴 YES" if debug_info['clipped'] else "🟢 NO"
                    st.metric("Clipped", clipped_status)
                    
                    if 'error' in debug_info:
                        st.error(f"Error: {debug_info['error']}")
            
            # Simple chart
            if len(rms_history) > 1:
                chart_placeholder.line_chart(rms_history)
            
            time.sleep(0.1)
            
    except Exception as e:
        st.error(f"Stream error: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
        audio.terminate()
        
        status_placeholder.empty()
        metrics_placeholder.empty()

def main():
    st.set_page_config(
        page_title="Debug Mic",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Microphone Debug Tool")
    st.markdown("Analyze audio input issues and microphone behavior")
    
    # List devices
    st.subheader("📱 Available Audio Devices")
    devices = list_audio_devices()
    
    if devices:
        device_df = []
        for device in devices:
            device_df.append({
                'Index': device['index'],
                'Name': device['name'],
                'Channels': device['channels'],
                'Sample Rate': f"{device['rate']:.0f} Hz"
            })
        st.table(device_df)
        
        # Device selection
        device_names = [f"{d['index']}: {d['name']}" for d in devices]
        selected = st.selectbox("Select Input Device", ["Default"] + device_names)
        
        device_index = None
        if selected != "Default":
            device_index = int(selected.split(":")[0])
    else:
        st.error("No audio input devices found!")
        return
    
    st.markdown("---")
    
    # Debug controls
    col1, col2 = st.columns(2)
    
    with col1:
        duration = st.slider("Debug Duration (seconds)", 5, 30, 10)
        
    with col2:
        if st.button("🔍 Start Debug Analysis", type="primary"):
            st.info("🎤 Starting audio analysis... Try speaking and staying quiet!")
            debug_audio_stream(device_index, duration)
            st.success("✅ Analysis complete!")
    
    # Instructions
    st.markdown("---")
    st.subheader("📋 How to Debug")
    st.markdown("""
    **What to look for:**
    
    1. **RMS Level** - Should increase when speaking, decrease when quiet
    2. **Clipping** - Should be NO (🟢). If YES (🔴), reduce microphone gain
    3. **Min/Max Values** - Should vary with sound. If always 0, mic might be muted
    4. **Zero Count** - High values might indicate mic issues
    
    **Common Issues:**
    - **Level = 0 when speaking**: Microphone muted or wrong device selected
    - **Clipping**: Microphone gain too high, reduce in system settings
    - **No variation**: Wrong microphone or permission issues
    - **Inverted behavior**: Check microphone settings or try different device
    """)
    
    # System info
    with st.expander("🔧 System Info"):
        st.markdown(f"""
        **Audio Settings:**
        - Format: {FORMAT} (16-bit PCM)
        - Channels: {CHANNELS} (Mono)
        - Sample Rate: {RATE} Hz
        - Chunk Size: {CHUNK} samples
        
        **Expected Behavior:**
        - Quiet environment: RMS 50-500
        - Normal speech: RMS 1000-5000
        - Loud speech: RMS 5000-15000
        """)

if __name__ == "__main__":
    main()
