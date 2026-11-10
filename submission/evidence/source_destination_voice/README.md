# Real voice source-destination trial

Start: F, measured TF (7.080, -3.462) m; robot reached F through native Nav2 beforehand. Real microphone transcript: “Đi từ khu vực A đến khu vực B”. Parser: source_destination, waypoints [A,B], starts_from_source=true. Command ID: `1af3f6bf42ac4fe294a391b0a2dfccf9`.

A: GOAL_ACCEPTED→navigation ACTION_TERMINAL = 57.04916358 s. B: 41.80065107 s. Both navigation results status 4, error_code 0; overall SUCCEEDED. A terminal precedes B goal acceptance. `events.jsonl` contains complete actual events; `tf_samples.json` contains measured TF.

Six recordings total, including the initial operator-not-ready recording. Two recordings used the final ASR configuration: UNKNOWN_REGION then success. Earlier recordings used earlier preprocessing/confidence policy; this session does not measure accuracy of a fixed configuration. See `attempts.json`. A model startup retry with no recording is excluded.

ASR fix: second-order Butterworth high-pass 80 Hz before VAD/Whisper, keeping raw WAV unchanged; Whisper joint no-speech/logprob policy, with numeric thresholds unchanged (-0.8, 0.5). Confident text is not independently rejected by no_speech_prob. Reference: https://github.com/openai/whisper/blob/main/whisper/transcribe.py . No prompt containing the expected transcript was passed to Whisper.

The supplementary clip is a continuous real terminal capture with same-session microphone audio at 1x. RViz was obscured by another window during filming; the desktop was cropped to the actual terminal and padded in neutral gray for Full HD. No telemetry text was painted onto the recording. A separate native RViz screenshot shows the post-mission SUCCEEDED state at B. `video.json` records provenance, timestamps, audio hash, crop and appended video section. Raw full-desktop footage and WAV remain local.

The report fragment is `docs/source_destination_results.tex`; no LaTeX compilation was performed.
