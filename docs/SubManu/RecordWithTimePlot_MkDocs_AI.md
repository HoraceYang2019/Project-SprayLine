---
title: RecordWithTimePlot API Reference
description: Function and operation reference for real-time audio acquisition, queue handling, RMS calculation, and waveform visualization.
tags:
  - audio
  - sounddevice
  - matplotlib
  - threading
  - queue
  - real-time
---

## RecordWithTimePlot API Reference

### Purpose

This document describes the callable functions and key operations used in `RecordWithTimePlot.py`.

It is intended for:

- MkDocs documentation.
- AI-agent retrieval and tool selection.
- Developers who need to understand function inputs, outputs, side effects, and usage constraints.

---

## Function: `audio_reader()`

### Summary

Continuously reads audio frames from the input stream, optionally plays them through the output stream, and sends the latest audio data to `frame_q`.

### Signature

```python
audio_reader() -> None
```

### Inputs

This function has no explicit arguments.

It uses the following global objects:

| Name | Type | Required | Description |
|---|---|---:|---|
| `in_stream` | `sounddevice.RawInputStream` | Yes | Audio input stream. |
| `out_stream` | `sounddevice.RawOutputStream \| None` | No | Optional playback stream. |
| `CHUNK` | `int` | Yes | Number of audio frames read per iteration. |
| `frame_q` | `queue.Queue` | Yes | Transfers captured audio data to the main thread. |
| `stop_event` | `threading.Event` | Yes | Signals termination of audio acquisition. |

### Outputs

Return value:

```python
None
```

Produced data:

```text
bytes
```

The captured audio block is inserted into:

```python
frame_q
```

### Side Effects

- Reads continuously from `in_stream`.
- May write audio to `out_stream`.
- Updates `frame_q`.
- Drops the oldest queued frame if the queue is full.
- Prints input-overflow or playback errors.
- Sets `stop_event` if the reader exits unexpectedly.

### Usage

```python
producer = threading.Thread(
    target=audio_reader,
    daemon=True
)

producer.start()
```

### Agent Guidance

Use `audio_reader()` when continuous real-time audio acquisition is required.

Do not call it directly as a blocking foreground function unless continuous execution is intended.

Preferred usage is as a background thread.

---

## Operation: `in_stream.read(CHUNK)`

### Summary

Reads one block of raw audio data from the input device.

### Signature

```python
data, overflowed = in_stream.read(CHUNK)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `CHUNK` | `int` | Number of audio frames to read. Default: `1024`. |

### Outputs

| Name | Type | Description |
|---|---|---|
| `data` | buffer-like object | Raw captured audio samples. |
| `overflowed` | `bool` | Indicates whether an input overflow occurred. |

### Usage

```python
data, overflowed = in_stream.read(CHUNK)

if overflowed:
    print("[audio_reader] input overflow")
```

### Agent Guidance

Use this operation only after `in_stream` has been created and started.

---

## Operation: `out_stream.write(data)`

### Summary

Writes captured audio data to the output device for loopback playback.

### Signature

```python
out_stream.write(data)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `data` | `bytes` or buffer-like object | Raw audio samples to send to the output device. |

### Outputs

No application-level output is used.

### Preconditions

```python
out_stream is not None
```

This normally requires:

```python
PLAYBACK = True
```

### Usage

```python
if out_stream is not None:
    out_stream.write(data)
```

### Agent Guidance

Use only when audio monitoring or loopback playback is required.

---

## Operation: `frame_q.put_nowait(data)`

### Summary

Places a captured audio block into the inter-thread queue without blocking.

### Signature

```python
frame_q.put_nowait(data)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `data` | `bytes` | Captured audio block. |

### Outputs

```python
None
```

### Exceptions

```python
queue.Full
```

### Usage

```python
try:
    frame_q.put_nowait(data)
except queue.Full:
    try:
        frame_q.get_nowait()
    except queue.Empty:
        pass

    try:
        frame_q.put_nowait(data)
    except queue.Full:
        pass
```

### Agent Guidance

Use this operation for low-latency producer-consumer communication.

When the queue is full, prefer removing old data rather than blocking the audio acquisition thread.

---

## Operation: `frame_q.get(timeout=0.05)`

### Summary

Retrieves an audio frame from the queue.

### Signature

```python
data = frame_q.get(timeout=0.05)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `timeout` | `float` | Maximum wait time in seconds. Default usage: `0.05`. |

### Outputs

| Name | Type | Description |
|---|---|---|
| `data` | `bytes` | Captured audio block. |

### Exceptions

```python
queue.Empty
```

### Usage

```python
try:
    data = frame_q.get(timeout=0.05)
except queue.Empty:
    plt.pause(0.01)
```

### Agent Guidance

Use this operation in the consumer or visualization thread.

---

## Operation: `frame_q.get_nowait()`

### Summary

Retrieves queued data immediately without waiting.

### Signature

```python
data = frame_q.get_nowait()
```

### Inputs

None.

### Outputs

| Name | Type | Description |
|---|---|---|
| `data` | `bytes` | Next queued audio block. |

### Exceptions

```python
queue.Empty
```

### Usage

```python
while True:
    try:
        data = frame_q.get_nowait()
    except queue.Empty:
        break
```

### Agent Guidance

Use this pattern to drain old frames and retain the newest available audio block.

This is suitable for real-time visualization where low latency is more important than processing every frame.

---

## Operation: `np.frombuffer()`

### Summary

Converts raw audio bytes into signed 16-bit NumPy samples.

### Signature

```python
y = np.frombuffer(data, dtype=np.int16)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `data` | `bytes` | Raw audio data. |
| `dtype` | NumPy dtype | Must match the stream format. Current value: `np.int16`. |

### Outputs

| Name | Type | Description |
|---|---|---|
| `y` | `numpy.ndarray` | One-dimensional array of decoded audio samples. |

### Usage

```python
y = np.frombuffer(data, dtype=np.int16)
```

### Agent Guidance

The NumPy dtype must be consistent with:

```python
DTYPE = "int16"
```

---

## Operation: Stereo Reshape and Channel Selection

### Summary

Converts interleaved multi-channel samples into a two-dimensional array and selects one channel.

### Inputs

| Name | Type | Description |
|---|---|---|
| `y` | `numpy.ndarray` | Interleaved audio samples. |
| `CHANNELS` | `int` | Number of input channels. |
| `PLOT_CHANNEL` | `int` | Channel index selected for analysis and plotting. |

### Outputs

| Name | Type | Description |
|---|---|---|
| `y` | `numpy.ndarray` | One-dimensional samples from the selected channel. |

### Usage

```python
if CHANNELS > 1:
    y = y.reshape(-1, CHANNELS)
    y = y[:, PLOT_CHANNEL]
```

### Preconditions

For stereo input:

```python
CHANNELS = 2
```

Valid channel indices are:

```text
0
1
```

### Agent Guidance

Use this operation before RMS calculation or plotting when the stream contains more than one channel.

---

## Operation: RMS Calculation

### Summary

Calculates the root-mean-square amplitude of the selected audio channel.

### Formula

```text
RMS = sqrt(mean(y^2))
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `y` | `numpy.ndarray` | Audio samples from one selected channel. |

### Outputs

| Name | Type | Description |
|---|---|---|
| `rms` | `float` | RMS amplitude of the current audio frame. |

### Usage

```python
rms = float(
    np.sqrt(
        np.mean(
            y.astype(np.float32) ** 2
        )
    )
)
```

### Agent Guidance

Convert `int16` samples to floating point before squaring.

Recommended:

```python
y.astype(np.float32)
```

This prevents integer overflow during RMS calculation.

---

## Operation: `line.set_ydata(y)`

### Summary

Updates the waveform displayed by Matplotlib.

### Signature

```python
line.set_ydata(y)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `y` | `numpy.ndarray` | Selected audio-channel samples. |

### Outputs

```python
None
```

### Usage

```python
line.set_ydata(y)
```

### Agent Guidance

Use after retrieving and decoding the newest audio frame.

---

## Operation: `rms_text.set_text()`

### Summary

Updates the RMS text shown in the plotting window.

### Signature

```python
rms_text.set_text(text)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `text` | `str` | Formatted RMS display string. |

### Outputs

```python
None
```

### Usage

```python
rms_text.set_text(
    f"RMS: {rms:7.1f}"
)
```

---

## Operation: `stop_event.set()`

### Summary

Signals the audio producer and main processing loop to terminate.

### Signature

```python
stop_event.set()
```

### Inputs

None.

### Outputs

```python
None
```

### Usage

```python
stop_event.set()
```

### Agent Guidance

Use during controlled shutdown or unrecoverable audio-processing errors.

---

## Operation: `producer.join(timeout=1.0)`

### Summary

Waits for the producer thread to terminate.

### Signature

```python
producer.join(timeout=1.0)
```

### Inputs

| Name | Type | Description |
|---|---|---|
| `timeout` | `float` | Maximum waiting time in seconds. |

### Outputs

```python
None
```

### Usage

```python
stop_event.set()
producer.join(timeout=1.0)
```

### Agent Guidance

Call after setting `stop_event` and before releasing audio resources.

---

## Agent-Oriented Processing Sequence

For an AI agent that needs to reason about this program, the expected processing order is:

```text
1. Create input stream
2. Start input stream
3. Start audio_reader() producer thread
4. Read audio blocks
5. Place audio bytes in frame_q
6. Retrieve newest frame from frame_q
7. Convert bytes to int16 samples
8. Separate/select channel
9. Calculate RMS
10. Update waveform
11. Update RMS text
12. Repeat until stop_event is set
13. Join producer thread
14. Stop and close streams
```

---

## Key Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `DTYPE` | `"int16"` | Audio sample data type. |
| `CHANNELS` | `2` | Stereo input. |
| `RATE` | `44100` | Sampling frequency in Hz. |
| `CHUNK` | `1024` | Frames per acquisition block. |
| `PLAYBACK` | `False` | Enable or disable audio loopback. |
| `PLOT_CHANNEL` | `0` | Channel used for RMS and waveform plotting. |
| `AX_YLIM` | `32000` | Waveform display amplitude limit. |

---

## Retrieval Keywords

```text
audio_reader
audio capture
sounddevice
RawInputStream
RawOutputStream
audio queue
threading
real-time audio
RMS
stereo channel
waveform plotting
Matplotlib
int16 audio
frame queue
producer consumer
```
