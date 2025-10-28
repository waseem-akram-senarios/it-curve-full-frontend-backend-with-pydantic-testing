# VAD (Voice Activity Detection) Configuration

## Current Status
✅ **VAD is ENABLED and WORKING**

The agent is using **Silero VAD** for speech detection.

## Current Configuration

**File**: `IT_Curves_Bot/main.py` (Line 299)

```python
session = AgentSession(
    stt=deepgram.STT(
        model=deepgram_stt_model, 
        language="en",
        interim_results=True,
        smart_format=True
    ),
    allow_interruptions=True,
    false_interruption_timeout=2.0,
    resume_false_interruption=True,
    llm=openai.LLM(model="gpt-4.1-mini", temperature=0.1),
    tts=deepgram.TTS(model=deepgram_tts_model),
    vad=silero.VAD.load(min_silence_duration=0.75),  # ← VAD configuration
    # turn_detection=EnglishModel(),  # Disabled
)
```

## VAD Settings Explained

### `min_silence_duration=0.75`
- **Default**: 0.75 seconds
- **What it does**: Controls how long silence must be detected before the agent thinks the user has stopped speaking
- **Lower values** (e.g., 0.5): More aggressive - agent responds faster
- **Higher values** (e.g., 1.0): Less aggressive - waits longer to make sure user is done

## How VAD Works

1. **Continuous Listening**: The VAD monitors audio continuously
2. **Speech Detection**: Detects when you start speaking
3. **Silence Detection**: Waits for `min_silence_duration` of silence before processing
4. **Response Trigger**: Only sends your speech to STT after you stop speaking

## VAD vs Turn Detection

| Feature | VAD (Current) | Turn Detection (Disabled) |
|---------|---------------|--------------------------|
| **Purpose** | Detects voice activity | Detects natural conversation turns |
| **Detection** | Energy/amplitude based | Semantic/content based |
| **Response Time** | Immediate | Slightly slower |
| **Accuracy** | Good for simple speech | Better for natural conversations |
| **Docker Support** | ✅ Works | ❌ Requires model download |

## Potential Issues and Solutions

### Issue: Agent not responding to your speech
**Possible causes**:
1. VAD too aggressive (waiting too long for silence)
2. Background noise triggering false positives
3. Microphone sensitivity

**Solution**: Adjust `min_silence_duration`

### Issue: Agent cutting you off mid-speech
**Possible causes**:
1. VAD not aggressive enough (responding too quickly)
2. Small pauses being interpreted as end of speech

**Solution**: Increase `min_silence_duration`

## Adjusting VAD Settings

To change the VAD sensitivity, modify line 299 in `main.py`:

```python
# Current setting
vad=silero.VAD.load(min_silence_duration=0.75),

# More aggressive (responds faster)
vad=silero.VAD.load(min_silence_duration=0.5),

# Less aggressive (waits longer)
vad=silero.VAD.load(min_silence_duration=1.0),

# Very patient (waits for longer pauses)
vad=silero.VAD.load(min_silence_duration=1.5),
```

## Recommended Settings

- **Default/Conservative**: `0.75` seconds ✅ (Current)
- **Fast Response**: `0.5` seconds
- **Patient Listening**: `1.0` seconds
- **Very Patient**: `1.5` seconds

## Testing VAD

1. Connect to the agent at http://localhost:3000
2. Start speaking
3. Pause briefly (0.75 seconds)
4. Agent should process and respond

## Current Status

✅ VAD plugin loaded: `livekit.plugins.silero`  
✅ VAD model: Silero VAD v4  
✅ Configuration: `min_silence_duration=0.75`  

---

**To modify VAD settings**, edit `IT_Curves_Bot/main.py` line 299 and rebuild the Docker image.

