#!/usr/bin/env python3
"""
Test script for Silero VAD integration
"""

import numpy as np
import torch
from silero_vad import load_silero_vad

def test_silero_vad():
    """Test Silero VAD functionality"""
    print("Loading Silero VAD model...")
    
    try:
        # Load the model
        model = load_silero_vad()
        print("✅ Model loaded successfully!")
        
        # Create some test audio data (16kHz, 512 samples as required by Silero VAD)
        sample_rate = 16000
        samples = 512  # Required by Silero VAD for 16kHz

        # Test with silence
        silence = torch.zeros(samples, dtype=torch.float32)
        confidence_silence = model(silence, sample_rate).item()
        print(f"Silence confidence: {confidence_silence:.4f}")

        # Test with simulated voice (sine wave)
        t = torch.linspace(0, samples/sample_rate, samples)
        voice_sim = 0.1 * torch.sin(2 * np.pi * 440 * t)  # 440Hz tone
        confidence_voice = model(voice_sim, sample_rate).item()
        print(f"Simulated voice confidence: {confidence_voice:.4f}")

        # Test with random noise (might be detected as voice)
        noise = 0.05 * torch.randn(samples, dtype=torch.float32)
        confidence_noise = model(noise, sample_rate).item()
        print(f"Noise confidence: {confidence_noise:.4f}")
        
        print("✅ Silero VAD test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Silero VAD: {e}")
        return False

if __name__ == "__main__":
    test_silero_vad()
