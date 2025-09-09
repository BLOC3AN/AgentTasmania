#!/usr/bin/env python3
"""
Demo script to test VAD functionality without Streamlit
"""

import numpy as np
import torch
from silero_vad import load_silero_vad
import time

def demo_vad_detection():
    """Demo VAD detection with different audio types"""
    print("🎙️ Loading Silero VAD model...")
    
    try:
        # Load the model
        model = load_silero_vad()
        print("✅ Model loaded successfully!")
        
        sample_rate = 16000
        samples = 512  # Required by Silero VAD for 16kHz
        vad_threshold = 0.5
        
        print(f"\n📊 Testing with threshold: {vad_threshold}")
        print("=" * 50)
        
        # Test cases
        test_cases = [
            ("Silence", torch.zeros(samples, dtype=torch.float32)),
            ("Low tone (440Hz)", 0.1 * torch.sin(2 * np.pi * 440 * torch.linspace(0, samples/sample_rate, samples))),
            ("High tone (1000Hz)", 0.1 * torch.sin(2 * np.pi * 1000 * torch.linspace(0, samples/sample_rate, samples))),
            ("White noise (low)", 0.05 * torch.randn(samples, dtype=torch.float32)),
            ("White noise (medium)", 0.1 * torch.randn(samples, dtype=torch.float32)),
            ("White noise (high)", 0.2 * torch.randn(samples, dtype=torch.float32)),
            ("Mixed signal", 0.1 * torch.sin(2 * np.pi * 440 * torch.linspace(0, samples/sample_rate, samples)) + 0.05 * torch.randn(samples, dtype=torch.float32)),
        ]
        
        for name, audio in test_cases:
            confidence = model(audio, sample_rate).item()
            has_voice = confidence > vad_threshold
            status = "🔴 VOICE" if has_voice else "🟢 QUIET"
            print(f"{name:20} | Confidence: {confidence:.4f} | {status}")
        
        print("\n" + "=" * 50)
        print("✅ VAD demo completed successfully!")
        
        # Simulate real-time detection
        print("\n🔄 Simulating real-time detection (5 seconds)...")
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 5:
            # Simulate random audio input
            if np.random.random() > 0.7:  # 30% chance of "voice"
                audio = 0.1 * torch.sin(2 * np.pi * 440 * torch.linspace(0, samples/sample_rate, samples)) + 0.02 * torch.randn(samples, dtype=torch.float32)
                expected = "VOICE"
            else:
                audio = 0.02 * torch.randn(samples, dtype=torch.float32)  # Just noise
                expected = "QUIET"
            
            confidence = model(audio, sample_rate).item()
            has_voice = confidence > vad_threshold
            detected = "VOICE" if has_voice else "QUIET"
            
            frame_count += 1
            if frame_count % 10 == 0:  # Print every 10th frame
                print(f"Frame {frame_count:3d} | Expected: {expected:5} | Detected: {detected:5} | Confidence: {confidence:.4f}")
            
            time.sleep(0.032)  # Simulate 512 samples at 16kHz = 32ms
        
        print(f"\n✅ Processed {frame_count} frames in real-time simulation")
        return True
        
    except Exception as e:
        print(f"❌ Error in VAD demo: {e}")
        return False

if __name__ == "__main__":
    demo_vad_detection()
