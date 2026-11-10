# PAIRS Lab test evidence

Selected results and event logs from the PAIRS Lab simulation are in
[pairs_lab/](pairs_lab/). Files were copied unchanged from the local experiment
records. [manifest.json](pairs_lab/manifest.json) lists their hashes and the map
and region files used for comparison.

| Test | Files |
| --- | --- |
| Six-goal Nav2 baseline | [navigation.json](pairs_lab/navigation.json) |
| Goal validity and clearance | [goals_validation.json](pairs_lab/goals_validation.json) |
| Parser-to-Nav2 integration | [pipeline.json](pairs_lab/pipeline.json), [events](pairs_lab/pipeline_events.json) |
| Laser/map alignment | [scan_alignment.json](pairs_lab/scan_alignment.json) |
| Three microphone commands, 9 November 2026 | [voice_acceptance.json](pairs_lab/voice_acceptance.json) |
| Voice source–destination F→A→B | [result](pairs_lab/source_destination_voice/result.json), [events](pairs_lab/source_destination_voice/events.jsonl), [attempts](pairs_lab/source_destination_voice/attempts.json) |
| Voice rejection of region Z | [acceptance](pairs_lab/unknown_region_voice/acceptance.json), [TF samples](pairs_lab/unknown_region_voice/tf_samples.json) |
| Measured trajectory A→B→D→C→E→F | [results](pairs_lab/trajectory_pairs/results.json), [TF samples](pairs_lab/trajectory_pairs/tf_samples.jsonl), [AMCL samples](pairs_lab/trajectory_pairs/amcl_samples.jsonl) |
| Multi-waypoint A→C→D, keyboard input | [result](pairs_lab/rviz_multiwaypoint/result.json), [plan and capture metadata](pairs_lab/rviz_multiwaypoint/capture.json) |
| Build and source checks | [source_validation.json](pairs_lab/source_validation.json) |

These are separate trials. The trajectory run used native Nav2 goals; the
multi-waypoint RViz capture used keyboard input. Voice source–destination used
six recordings across ASR configuration changes, including two with the final
configuration; see its attempt log before interpreting success rates.

Some records retain local audio paths, screenshot paths, hashes, or historical
commit IDs for provenance. Raw WAV files, screenshots, reports, and videos stay
local. Commit IDs recorded before the commit-message rewrite refer to the
original history.
