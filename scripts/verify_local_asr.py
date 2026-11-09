#!/usr/bin/env python3
"""Actual model/VAD test using explicitly synthetic silence, not a speech demo."""

import json
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)
segments, info = m.transcribe(
    np.zeros(32000, dtype=np.float32),
    language="vi",
    vad_filter=True,
    condition_on_previous_text=False,
)
texts = [s.text for s in segments]
result = dict(
    input="synthetic zero samples: 2s at 16kHz; NOT real speech",
    multilingual=m.model.is_multilingual,
    language=info.language,
    vad_speech_seconds=info.duration_after_vad,
    transcripts=texts,
    passed=not texts,
)
Path("evidence/asr_silence.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
assert result["passed"]
