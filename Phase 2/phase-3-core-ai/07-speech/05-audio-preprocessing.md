# Audio Preprocessing

This guide covers audio preprocessing techniques for speech recognition on Jetson AGX Orin.

## Install Audio Libraries

```bash
pip install scipy pydub numpy
```

## Reading Audio

```python
import wave
import struct
import numpy as np

# Using wave
with wave.open('audio.wav', 'r') as wav:
    frames = wav.getnframes()
    rate = wav.getframerate()
    audio_data = wav.readframes(frames)

# Using scipy
from scipy.io import wavfile
rate, audio = wavfile.read('audio.wav')

# Using pydub
from pydub import AudioSegment
audio = AudioSegment.from_wav('audio.wav')
```

## Audio Properties

```python
# Sample rate
print(f"Sample rate: {audio.frame_rate} Hz")

# Channels
print(f"Channels: {audio.channels}")

# Duration
print(f"Duration: {len(audio) / 1000} seconds")

# Bit depth
print(f"Sample width: {audio.sample_width} bytes")
```

## Resampling

```python
from scipy import signal
import numpy as np

def resample_audio(audio, orig_rate, target_rate):
    """Resample audio to target sample rate"""
    num_samples = int(len(audio) * target_rate / orig_rate)
    resampled = signal.resample(audio, num_samples)
    return resampled, target_rate

# Example
new_rate = 16000
resampled_audio, new_rate = resample_audio(audio, 44100, new_rate)
```

## Mono to Stereo Conversion

```python
# Convert stereo to mono
def to_mono(audio):
    if len(audio.shape) > 1:
        return np.mean(audio, axis=1)
    return audio

# Convert mono to stereo
def to_stereo(audio):
    if len(audio.shape) == 1:
        return np.stack([audio, audio], axis=1)
    return audio
```

## Normalization

```python
import numpy as np

def normalize_audio(audio):
    """Normalize audio to -1 to 1 range"""
    max_val = np.abs(audio).max()
    if max_val > 0:
        return audio / max_val
    return audio

def normalize_db(audio, target_db=-20):
    """Normalize to target dB"""
    current_db = 20 * np.log10(np.sqrt(np.mean(audio**2)))
    gain = target_db - current_db
    gain_linear = 10 ** (gain / 20)
    return audio * gain_linear
```

## Noise Reduction

```python
import numpy as np
from scipy import signal

def spectral_gating(audio, noise_profile=None):
    """Simple noise reduction using spectral gating"""
    # Compute STFT
    f, t, Zxx = signal.stft(audio, fs=16000)
    
    # Estimate noise if not provided
    if noise_profile is None:
        noise_profile = np.abs(Zxx[:, :10]).mean(axis=1, keepdims=True)
    
    # Gate
    magnitude = np.abs(Zxx)
    threshold = noise_profile * 1.5
    mask = magnitude > threshold
    gated = Zxx * mask
    
    # ISTFT
    _, audio_denoised = signal.istft(gated, fs=16000)
    return audio_denoised
```

## Voice Activity Detection

```python
import numpy as np
from scipy import signal

def is_speech(audio, rate=16000, threshold=0.02):
    """Simple energy-based voice activity detection"""
    energy = np.sum(audio ** 2) / len(audio)
    return energy > threshold

def vad(audio, rate=16000, frame_duration=0.03, threshold=0.02):
    """Frame-based VAD"""
    frame_length = int(rate * frame_duration)
    frames = []
    
    for i in range(0, len(audio) - frame_length, frame_length // 2):
        frame = audio[i:i + frame_length]
        if is_speech(frame, rate, threshold):
            frames.append(frame)
    
    return np.concatenate(frames) if frames else np.array([])
```

## Trimming Silence

```python
import numpy as np

def trim_silence(audio, threshold=0.01):
    """Remove silence from beginning and end"""
    mask = np.abs(audio) > threshold
    
    if not mask.any():
        return audio
    
    first = np.argmax(mask)
    last = len(audio) - np.argmax(mask[::-1])
    
    return audio[first:last]

def trim_silence_blocks(audio, min_silence=0.5, threshold=0.01):
    """Remove all silence blocks"""
    is_speech = np.abs(audio) > threshold
    
    # Find transitions
    diff = np.diff(is_speech.astype(int))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    
    if len(starts) == 0:
        return audio
    
    # Keep speech blocks
    speech = []
    for start, end in zip(starts, ends):
        if end - start > min_silence * 16000:
            speech.append(audio[start:end])
    
    return np.concatenate(speech) if speech else np.array([])
```

## Audio Format Conversion

```python
from pydub import AudioSegment

def convert_audio(input_file, output_file, format_out='wav'):
    """Convert audio format"""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format=format_out)

# Convert to 16kHz mono WAV
def convert_for_stt(input_file, output_file):
    """Convert to format suitable for speech recognition"""
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio.export(output_file, format='wav')
```

## Audio Augmentation

```python
import numpy as np

def add_noise(audio, noise_level=0.005):
    """Add random noise"""
    noise = np.random.normal(0, noise_level, len(audio))
    return audio + noise

def time_stretch(audio, rate=1.0):
    """Stretch audio in time"""
    from scipy import signal
    indices = np.round(np.arange(0, len(audio), rate)).astype(int)
    indices = indices[indices < len(audio)]
    return audio[indices]

def pitch_shift(audio, rate=1.0):
    """Shift pitch"""
    from scipy import signal
    indices = np.round(np.arange(0, len(audio), 1.0/rate)).astype(int)
    indices = indices[indices < len(audio)]
    return audio[indices]
```

## Feature Extraction

```python
import numpy as np
from scipy import signal

def compute_mfcc(audio, rate=16000, n_mfcc=13):
    """Compute MFCC features"""
    from scipy.fftpack import dct
    
    # Pre-emphasis
    preemphasized = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
    
    # Frame
    frame_length = int(0.025 * rate)
    frame_step = int(0.01 * rate)
    frames = []
    for i in range(0, len(preemphasized) - frame_length, frame_step):
        frames.append(preemphasized[i:i + frame_length])
    frames = np.array(frames)
    
    # Apply Hamming window
    window = np.hamming(frame_length)
    frames = frames * window
    
    # FFT
    mag = np.abs(np.fft.rfft(frames, n=frame_length))
    
    # Mel filterbank
    n_filters = 26
    low_freq = 0
    high_freq = rate / 2
    mel_points = np.linspace(1125 * np.log(1 + low_freq / 700), 
                             1125 * np.log(1 + high_freq / 700), n_filters + 2)
    hz_points = 700 * (np.exp(mel_points / 1125) - 1)
    bin_points = np.floor((frame_length + 1) * hz_points / rate).astype(int)
    
    filterbank = np.zeros((n_filters, frame_length // 2 + 1))
    for i in range(n_filters):
        filterbank[i, bin_points[i]:bin_points[i+1]] = np.linspace(0, 1, bin_points[i+1] - bin_points[i])
        filterbank[i, bin_points[i+1]:bin_points[i+2]] = np.linspace(1, 0, bin_points[i+2] - bin_points[i+1])
    
    # Apply filterbank
    filterbanked = np.dot(mag, filterbank.T)
    log_filterbanked = np.log(filterbanked + 1e-10)
    
    # DCT
    mfcc = dct(log_filterbanked, type=2, axis=1, norm='ortho')[:, :n_mfcc]
    
    return mfcc
```
