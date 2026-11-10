# Unknown-region voice rejection

Real microphone → Whisper ASR → parser UNKNOWN_REGION → navigation state IDLE (REJECTED, busy=false). Selected recording 3 has the exact transcript “Đi đến khu vực Z”. No keyboard transcript was injected.

`acceptance.json` contains real messages, microphone WAV hash and screenshot hash. `terminal.log` is the original live terminal session; `events.jsonl` retains received ROS messages, including earlier latched controller states. `tf_samples.json` contains 88 measured TF positions during recording and the observation interval: displacement and maximum excursion both 0 m; no navigation goal accepted.

The PNG is an unmodified screenshot of the actual running terminal. Raw WAV remains local. Previous attempts are documented in `attempts.json`.
