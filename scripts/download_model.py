#!/usr/bin/env python3
"""Explicitly download/cache a real multilingual Whisper model before offline launch."""

import argparse
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument("--model", default="small")
args = p.parse_args()
model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=4)
if not model.model.is_multilingual:
    raise SystemExit("Use a multilingual model, not *.en")
print("MODEL_READY", args.model, "CPU int8; cached for local_files_only=true")
