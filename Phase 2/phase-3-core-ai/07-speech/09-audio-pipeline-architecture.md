# Audio Pipeline Architecture

This guide covers building an audio pipeline for voice assistants on Jetson AGX Orin.

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Microphone │───▶│  VAD/STT    │───▶│  LLM        │
└─────────────┘    └─────────────┘    └─────────────┘
                                               │
                   ┌─────────────┐              │
                   │  Speaker    │◀─────────────┘
                   └─────────────┘
                        ▲
                   ┌─────────────┐
                   │  TTS        │
                   └─────────────┘
```

## Complete Pipeline Code

```python
import asyncio
import threading
import queue
import numpy as np
from faster_whisper import WhisperModel
from transformers import pipeline
import sounddevice as sd

class AudioPipeline:
    def __init__(self):
        # Speech-to-Text
        self.stt_model = WhisperModel(
            "small.en",
            device="cuda",
            compute_type="float16"
        )
        
        # Text-to-Speech
        self.tts_command = "echo '{text}' | piper --model en_US-lessac-medium.onnx --output_file /tmp/output.wav"
        
        # Audio queues
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        
        self.running = False
        
    def start(self):
        self.running = True
        
        # Start recording thread
        self.record_thread = threading.Thread(target=self._record_audio)
        self.record_thread.start()
        
        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_audio)
        self.process_thread.start()
        
    def stop(self):
        self.running = False
        self.record_thread.join()
        self.process_thread.join()
        
    def _record_audio(self):
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self.audio_queue.put(indata.copy())
        
        with sd.InputStream(
            callback=callback,
            channels=1,
            samplerate=16000,
            blocksize=4000
        ):
            while self.running:
                sd.sleep(100)
                
    def _process_audio(self):
        audio_buffer = []
        
        while self.running:
            try:
                audio_chunk = self.audio_queue.get(timeout=1)
                audio_buffer.append(audio_chunk)
                
                # Process when enough audio
                if len(audio_buffer) > 10:  # ~2.5 seconds
                    audio = np.concatenate(audio_buffer)
                    audio_buffer = []
                    
                    # Transcribe
                    segments, info = self.stt_model.transcribe(
                        audio,
                        language="en",
                        beam_size=5
                    )
                    
                    text = " ".join([s.text for s in segments])
                    if text.strip():
                        print(f"Transcribed: {text}")
                        self.text_queue.put(text)
                        
            except queue.Empty:
                continue
```

## VAD-Triggered Pipeline

```python
import webrtcvad

class VADPipeline(AudioPipeline):
    def __init__(self):
        super().__init__()
        self.vad = webrtcvad.Vad(2)
        self.vad.set_mode(2)
        
    def _process_audio(self):
        audio_buffer = []
        is_speech = False
        
        while self.running:
            try:
                audio_chunk = self.audio_queue.get(timeout=1)
                
                # Check for speech
                is_speech_now = self.vad.is_speech(
                    audio_chunk.tobytes(),
                    16000
                )
                
                if is_speech_now:
                    audio_buffer.append(audio_chunk)
                    is_speech = True
                    
                elif is_speech and len(audio_buffer) > 0:
                    # End of speech
                    audio = np.concatenate(audio_buffer)
                    audio_buffer = []
                    is_speech = False
                    
                    # Process transcription
                    segments, _ = self.stt_model.transcribe(audio)
                    text = " ".join([s.text for s in segments])
                    if text.strip():
                        self.text_queue.put(text)
                        
            except queue.Empty:
                continue
```

## Async Pipeline

```python
import asyncio

class AsyncAudioPipeline:
    def __init__(self):
        self.stt = None
        self.llm_queue = asyncio.Queue()
        
    async def initialize(self):
        # Load models
        self.stt = WhisperModel("small.en", device="cuda")
        
    async def process_audio(self, audio_data):
        # Transcribe
        segments, _ = self.stt.transcribe(audio_data)
        text = " ".join([s.text for s in segments])
        
        if text.strip():
            await self.llm_queue.put(text)
            
    async def run(self):
        await self.initialize()
        
        while True:
            text = await self.llm_queue.get()
            print(f"Processing: {text}")
```

## Real-time Processing

```python
class RealTimePipeline:
    def __init__(self, chunk_duration=0.5):
        self.chunk_duration = chunk_duration
        self.sample_rate = 16000
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        
    async def stream_audio(self, audio_stream):
        buffer = np.zeros(self.chunk_size, dtype=np.int16)
        
        async for chunk in audio_stream:
            # Add to buffer
            buffer = np.roll(buffer, -len(chunk))
            buffer[-len(chunk):] = chunk.flatten()
            
            # Process when buffer full
            if self.is_speech(buffer):
                yield buffer
```

## Error Handling

```python
class RobustPipeline(AudioPipeline):
    def __init__(self):
        super().__init__()
        self.retry_count = 3
        self.fallback_stt = "whisper"  # or "vosk"
        
    def _transcribe_with_fallback(self, audio):
        for attempt in range(self.retry_count):
            try:
                segments, _ = self.stt_model.transcribe(audio)
                return " ".join([s.text for s in segments])
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt == self.retry_count - 1:
                    return self._fallback_transcribe(audio)
                    
    def _fallback_transcribe(self, audio):
        # Fallback to simpler model
        print("Using fallback STT")
        return ""
```

## Performance Optimization

```python
class OptimizedPipeline:
    def __init__(self):
        # Use float16 for faster inference
        self.stt = WhisperModel("small.en", device="cuda", compute_type="float16")
        
    def process_batch(self, audio_chunks):
        # Batch processing
        audio = np.concatenate(audio_chunks)
        
        # Use beam_size=1 for faster decoding
        segments, _ = self.stt.transcribe(audio, beam_size=1)
        
        return segments
```

## Testing

```python
import unittest

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = AudioPipeline()
        
    def test_audio_recording(self):
        # Test recording
        pass
        
    def test_transcription(self):
        # Test transcription
        pass
        
    def test_tts_generation(self):
        # Test TTS
        pass
        
if __name__ == "__main__":
    unittest.main()
```
