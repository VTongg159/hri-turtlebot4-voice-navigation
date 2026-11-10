"""Remove microphone DC/low-frequency rumble before VAD and ASR."""

import numpy as np
from scipy.signal import butter, sosfilt


def prepare_asr_audio(samples, sample_rate=16000, highpass_hz=80.0):
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 1 or not np.isfinite(samples).all():
        raise ValueError("ASR audio must be finite mono samples")
    if not 0 <= highpass_hz < sample_rate / 2:
        raise ValueError("High-pass cutoff must be below Nyquist")
    if highpass_hz == 0 or not len(samples):
        return samples.copy()
    sections = butter(2, highpass_hz, btype="highpass", fs=sample_rate, output="sos")
    return sosfilt(sections, samples).astype(np.float32)
