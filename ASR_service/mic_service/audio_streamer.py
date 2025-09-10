#!/usr/bin/env python3
"""
Complete Audio Streaming Script for ASR WebSocket
- Stream audio file as chunks
- Real-time transcription
- Support both file streaming and live microphone
"""

import asyncio
import websockets
import json
import base64
import wave
import numpy as np
import time
import threading
import pyaudio
from pathlib import Path

# Configuration
WEBSOCKET_URL = "wss://s6rou7ayi3jrzc-3000.proxy.runpod.net/ws/asr"
CHUNK_SIZE_MS = 1000000# 1000ms chunks
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1  # Mono
CHUNK_SIZE_SAMPLES = int(SAMPLE_RATE * CHUNK_SIZE_MS / 1000)  # 800 samples
CHUNK_SIZE_BYTES = CHUNK_SIZE_SAMPLES * 2  # 1600 bytes (16-bit)

class AudioStreamer:
    def __init__(self):
        self.websocket = None
        self.is_streaming = False
        self.audio_buffer = []
        
    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(WEBSOCKET_URL)
            print("✅ WebSocket connected")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect WebSocket"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 WebSocket disconnected")
    
    async def send_ping(self):
        """Test connection with ping"""
        if not self.websocket:
            return False
            
        try:
            ping_message = {"type": "ping"}
            await self.websocket.send(json.dumps(ping_message))
            
            response = await self.websocket.recv()
            result = json.loads(response)
            
            if result.get("type") == "pong":
                print("🏓 Ping successful")
                return True
            else:
                print("❌ Unexpected ping response:", result)
                return False
                
        except Exception as e:
            print(f"❌ Ping failed: {e}")
            return False
    
    async def send_audio_chunk(self, audio_data):
        """Send audio chunk as base64"""
        if not self.websocket:
            return None
            
        try:
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create message
            message = {
                "type": "audio",
                "data": audio_base64
            }
            
            # Send message
            await self.websocket.send(json.dumps(message))
            
            # Wait for response
            response = await self.websocket.recv()
            result = json.loads(response)
            
            return result
            
        except Exception as e:
            print(f"❌ Send chunk failed: {e}")
            return None
    
    async def stream_file(self, file_path, chunk_delay=0):
        """Stream audio file as chunks"""
        print(f"📁 Streaming file: {file_path}")
        
        try:
            # Read WAV file
            with wave.open(str(file_path), 'rb') as wav_file:
                # Get audio parameters
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                
                print(f"📊 Audio info: {frames} frames, {sample_rate}Hz, {channels} channels")
                
                # Read all audio data
                audio_data = wav_file.readframes(frames)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Convert to mono if stereo
                if channels == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    print("🔄 Converted stereo to mono")
                
                # Stream in chunks
                total_chunks = len(audio_array) // CHUNK_SIZE_SAMPLES
                print(f"📦 Streaming {total_chunks} chunks...")
                
                self.is_streaming = True
                transcriptions = []
                
                for i in range(0, len(audio_array), CHUNK_SIZE_SAMPLES):
                    if not self.is_streaming:
                        break
                        
                    # Get chunk
                    chunk = audio_array[i:i + CHUNK_SIZE_SAMPLES]
                    
                    # Pad if necessary
                    if len(chunk) < CHUNK_SIZE_SAMPLES:
                        chunk = np.pad(chunk, (0, CHUNK_SIZE_SAMPLES - len(chunk)))
                    
                    # Convert to bytes
                    chunk_bytes = chunk.astype(np.int16).tobytes()
                    
                    # Send chunk
                    result = await self.send_audio_chunk(chunk_bytes)
                    
                    if result:
                        chunk_num = i // CHUNK_SIZE_SAMPLES + 1
                        print(f"📤 Chunk {chunk_num}/{total_chunks} sent")
                        
                        if result.get("type") == "transcription":
                            transcription = result.get("text", "")
                            if transcription.strip():
                                transcriptions.append(transcription)
                                print(f"📝 Transcription: {transcription}")
                    
                    # Delay between chunks (simulate real-time)
                    await asyncio.sleep(chunk_delay)
                
                print(f"✅ Streaming completed!")
                print(f"📋 Total transcriptions: {len(transcriptions)}")
                
                if transcriptions:
                    full_text = " ".join(transcriptions)
                    print(f"📄 Full transcription: {full_text}")
                    return full_text
                else:
                    print("⚠️ No transcriptions received")
                    return None
                
        except Exception as e:
            print(f"❌ File streaming failed: {e}")
            return None
        finally:
            self.is_streaming = False
    
    async def stream_microphone(self, duration=10):
        """Stream from microphone"""
        print(f"🎤 Starting microphone streaming for {duration} seconds...")
        
        try:
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            
            # Open stream
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE_SAMPLES
            )
            
            print("🎙️ Microphone opened, start speaking...")
            
            self.is_streaming = True
            transcriptions = []
            start_time = time.time()
            
            while self.is_streaming and (time.time() - start_time) < duration:
                # Read audio chunk
                chunk_data = stream.read(CHUNK_SIZE_SAMPLES, exception_on_overflow=False)
                
                # Send chunk
                result = await self.send_audio_chunk(chunk_data)
                
                if result and result.get("type") == "transcription":
                    transcription = result.get("text", "")
                    if transcription.strip():
                        transcriptions.append(transcription)
                        print(f"📝 Live transcription: {transcription}")
                
                # Small delay
                await asyncio.sleep(0)
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            print(f"✅ Microphone streaming completed!")
            
            if transcriptions:
                full_text = " ".join(transcriptions)
                print(f"📄 Full transcription: {full_text}")
                return full_text
            else:
                print("⚠️ No transcriptions received")
                return None
                
        except Exception as e:
            print(f"❌ Microphone streaming failed: {e}")
            return None
        finally:
            self.is_streaming = False
    
    def stop_streaming(self):
        """Stop current streaming"""
        self.is_streaming = False
        print("🛑 Streaming stopped")

async def main():
    """Main function"""
    streamer = AudioStreamer()
    
    # Connect to WebSocket
    if not await streamer.connect():
        return
    
    try:
        # Test connection
        if not await streamer.send_ping():
            return
        
        print("\n" + "="*50)
        print("🎯 Audio Streaming Options:")
        print("1. Stream audio file")
        print("2. Stream from microphone")
        print("3. Send complete file (previous method)")
        print("="*50)
        
        choice = input("Choose option (1-3): ").strip()
        
        if choice == "1":
            # Stream file
            file_path = input("Enter audio file path: ").strip()
            if Path(file_path).exists():
                await streamer.stream_file(file_path)
            else:
                print("❌ File not found")
        
        elif choice == "2":
            # Stream microphone
            duration = int(input("Duration in seconds (default 10): ") or "10")
            await streamer.stream_microphone(duration)
        
        elif choice == "3":
            # Send complete file (previous method)
            file_path = input("Enter audio file path: ").strip()
            if Path(file_path).exists():
                await send_complete_file(streamer, file_path)
            else:
                print("❌ File not found")
        
        else:
            print("❌ Invalid choice")
    
    finally:
        await streamer.disconnect()

async def send_complete_file(streamer, file_path):
    """Send complete file as single message (previous method)"""
    print(f"📁 Sending complete file: {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        
        result = await streamer.send_audio_chunk(audio_data)
        
        if result and result.get("type") == "transcription":
            print(f"📝 Transcription: {result.get('text')}")
        else:
            print("❌ No transcription received")
            
    except Exception as e:
        print(f"❌ Failed to send file: {e}")

if __name__ == "__main__":
    print("🚀 Audio WebSocket Streaming Client")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")