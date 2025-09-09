#!/usr/bin/env python3
"""
Test audio system compatibility and troubleshoot ALSA issues
"""

import os
import sys
import warnings

# Suppress ALSA warnings
if sys.platform.startswith('linux'):
    os.environ['ALSA_PCM_CARD'] = '0'
    os.environ['ALSA_PCM_DEVICE'] = '0'

warnings.filterwarnings("ignore", category=UserWarning, module="pyaudio")

def test_audio_system():
    """Test audio system functionality"""
    print("🔧 Testing Audio System Compatibility")
    print("=" * 50)
    
    # Test 1: PyAudio import
    print("1. Testing PyAudio import...")
    try:
        import pyaudio
        print("   ✅ PyAudio imported successfully")
    except ImportError as e:
        print(f"   ❌ PyAudio import failed: {e}")
        print("   💡 Solution: pip install pyaudio")
        print("   💡 Or: sudo apt-get install python3-pyaudio")
        return False
    
    # Test 2: PyAudio initialization
    print("\n2. Testing PyAudio initialization...")
    try:
        audio = pyaudio.PyAudio()
        print("   ✅ PyAudio initialized successfully")
    except Exception as e:
        print(f"   ❌ PyAudio initialization failed: {e}")
        return False
    
    # Test 3: Get device info
    print("\n3. Getting audio device information...")
    try:
        device_count = audio.get_device_count()
        print(f"   📊 Found {device_count} audio devices")
        
        # List all devices
        print("\n   📋 Available devices:")
        for i in range(device_count):
            try:
                info = audio.get_device_info_by_index(i)
                device_type = "🎤" if info['maxInputChannels'] > 0 else "🔊"
                print(f"   {device_type} Device {i}: {info['name']}")
                print(f"      Channels: In={info['maxInputChannels']}, Out={info['maxOutputChannels']}")
                print(f"      Sample Rate: {info['defaultSampleRate']}")
            except Exception as e:
                print(f"   ⚠️ Device {i}: Error getting info - {e}")
    except Exception as e:
        print(f"   ❌ Failed to get device info: {e}")
    
    # Test 4: Default input device
    print("\n4. Testing default input device...")
    try:
        default_input = audio.get_default_input_device_info()
        print(f"   ✅ Default input: {default_input['name']}")
        print(f"   📊 Max input channels: {default_input['maxInputChannels']}")
        print(f"   🔊 Default sample rate: {default_input['defaultSampleRate']}")
    except Exception as e:
        print(f"   ❌ No default input device: {e}")
        print("   💡 Check if microphone is connected and enabled")
    
    # Test 5: Test recording capability
    print("\n5. Testing recording capability...")
    try:
        # Test parameters
        CHUNK = 512
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("   ✅ Audio stream opened successfully")
        print("   🎤 Testing 1 second of recording...")
        
        # Record for 1 second
        frames = []
        for i in range(0, int(RATE / CHUNK * 1)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        print("   ✅ Recording test completed successfully")
        
    except Exception as e:
        print(f"   ❌ Recording test failed: {e}")
        print("   💡 Check microphone permissions and settings")
    
    # Test 6: Silero VAD compatibility
    print("\n6. Testing Silero VAD compatibility...")
    try:
        from silero_vad import load_silero_vad
        print("   ✅ Silero VAD imported successfully")
        
        model = load_silero_vad()
        print("   ✅ Silero VAD model loaded successfully")
        
        # Test with dummy data
        import torch
        import numpy as np
        
        dummy_audio = torch.zeros(512, dtype=torch.float32)
        confidence = model(dummy_audio, 16000).item()
        print(f"   ✅ VAD test completed (confidence: {confidence:.4f})")
        
    except Exception as e:
        print(f"   ❌ Silero VAD test failed: {e}")
        print("   💡 Check: pip install silero-vad torch torchaudio")
    
    # Cleanup
    try:
        audio.terminate()
        print("\n✅ Audio system cleanup completed")
    except Exception as e:
        print(f"\n⚠️ Cleanup warning: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Audio system test completed!")
    print("\n💡 If you see ALSA warnings, they are usually harmless.")
    print("💡 The important thing is that PyAudio and recording work.")
    
    return True

def show_alsa_help():
    """Show help for ALSA issues"""
    print("\n🔧 ALSA Troubleshooting Guide")
    print("=" * 30)
    print("ALSA warnings are common on Linux and usually harmless.")
    print("They don't affect functionality if PyAudio works.")
    print("\nTo reduce ALSA warnings:")
    print("1. sudo apt-get install alsa-utils")
    print("2. Check: aplay -l  (list playback devices)")
    print("3. Check: arecord -l  (list recording devices)")
    print("4. Set environment variables:")
    print("   export ALSA_PCM_CARD=0")
    print("   export ALSA_PCM_DEVICE=0")

if __name__ == "__main__":
    success = test_audio_system()
    
    if not success:
        print("\n❌ Audio system test failed!")
        show_alsa_help()
        sys.exit(1)
    else:
        print("\n✅ Audio system is ready for Smart Microphone!")
        print("🚀 You can now run: streamlit run smart_mic.py")
