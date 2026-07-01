# Configure HDMI Audio Output

By default, audio may go to the headphone jack. Configure HDMI audio for your monitor speakers.

## Identify Audio Sinks

```bash
pactl list short sinks
```

Look for a sink containing `hdmi` (e.g., `alsa_output.platform-3510000.hda.hdmi-stereo`).

## Set Default Sink Temporarily

```bash
pactl set-default-sink <sink_name>
```

Example:

```bash
pactl set-default-sink alsa_output.platform-3510000.hda.hdmi-stereo
```

## Test Audio

```bash
speaker-test -t sine -f 1000 -c 2
```

## Make Permanent

Create configuration file:

```bash
nano ~/.config/pulse/default.pa
```

Add:

```
set-default-sink <sink_name>
```

Example:

```
set-default-sink alsa_output.platform-3510000.hda.hdmi-stereo
```

## Verify Configuration

```bash
pactl get-default-sink
```

Should return your HDMI device.

## Next Steps

- [Whisper STT](02-whisper-stt.md) - Speech-to-Text
- [Piper TTS](03-piper-tts.md) - Text-to-Speech
