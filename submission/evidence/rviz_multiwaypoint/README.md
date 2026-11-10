# Live RViz multi-waypoint capture

Keyboard transcript: “Đi từ A qua C đến D”. Actual parser route: A→C→D.

The unmodified X11 screenshot was captured while navigating C→D. Cyan path is Nav2 `/plan` for the active leg, rather than a concatenated whole-mission plan. Semantic region polygons and goal arrows are provided by `region_visualization_node`; the straight waypoint-order line is hidden. The status marker is driven by actual controller messages.

The command later completed with `SUCCEEDED`; see `result.json`, `events.jsonl`, and the complete plan coordinates in `capture.json`. This trial used keyboard input; no microphone recording was made.
