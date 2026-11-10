import numpy as np
import pytest

from tb4_voice_navigation.audio_preprocessing import prepare_asr_audio


def test_dc_and_rumble_removed_without_attenuating_voice_band():
    t = np.arange(16000) / 16000
    voice = 0.1 * np.sin(2 * np.pi * 1000 * t)
    raw = voice + 0.2 + 0.1 * np.sin(2 * np.pi * 10 * t)
    filtered = prepare_asr_audio(raw)
    assert filtered.shape == raw.shape and filtered.dtype == np.float32
    assert np.sqrt(np.mean((filtered[1600:] - voice[1600:]) ** 2)) < 0.01
    assert np.sqrt(np.mean(filtered[1600:] ** 2)) > 0.065


def test_silence_and_disabled_filter_preserve_samples():
    assert np.array_equal(prepare_asr_audio(np.zeros(16000)), np.zeros(16000))
    raw = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    assert np.array_equal(prepare_asr_audio(raw, highpass_hz=0), raw)


def test_invalid_audio_rejected():
    with pytest.raises(ValueError):
        prepare_asr_audio([np.nan])
    with pytest.raises(ValueError):
        prepare_asr_audio([0], highpass_hz=8000)
