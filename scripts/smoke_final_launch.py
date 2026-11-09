#!/usr/bin/env python3
"""Validate the final launch with a real parser/Nav2 mission and optional RViz capture."""

import json
from pathlib import Path
import re
import subprocess
import time
import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from test_live_pipeline import Probe

rclpy.init()
p = Probe()
p.scenario = "final_launch_smoke"
asr = []
sub = p.create_subscription(
    String,
    "/voice/asr_status",
    lambda m: asr.append(json.loads(m.data)),
    QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),
)
try:
    p.wait(
        lambda: p.pub.get_subscription_count() > 0
        and p.events
        and any(e.get("ready") for e in asr),
        30,
    )
    i = p.send("Đi đến phòng thí nghiệm")
    p.wait(lambda: p.event_after(i, "GOAL_ACCEPTED"), 30)
    # Capture the actual RViz window while the goal is active, not a rendered mockup.
    settle = time.monotonic() + 3
    while time.monotonic() < settle:
        rclpy.spin_once(p, timeout_sec=0.1)
    windows = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    ids = []
    for line in windows.splitlines():
        if "semantic.rviz" in line and '("rviz2" "rviz2")' in line:
            match = re.search(r"0x[0-9a-f]+", line)
            if match:
                ids.append(match.group())
    if ids:
        response = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "x11grab",
                "-window_id",
                ids[-1],
                "-i",
                ":1",
                "-frames:v",
                "1",
                "docs/rviz_semantic.png",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        Path("evidence/rviz_screenshot.log").write_text(response.stderr)
    p.wait(lambda: p.terminal(i) is not None, 120)
    terminal = p.terminal(i)
    result = dict(
        test="fresh_full_launch_parser_to_Nav2",
        input="keyboard transcript, NOT microphone",
        passed=terminal["state"] == "SUCCEEDED",
        terminal=terminal,
        asr_model_ready=any(e.get("ready") for e in asr),
    )
    Path("evidence/final_launch_smoke.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )
    print(result, flush=True)
    assert result["passed"]
finally:
    if p.events and p.events[-1].get("busy"):
        i = p.send("Dừng lại")
        try:
            p.wait(lambda: p.terminal(i) is not None, 15)
        except TimeoutError:
            pass
    p.destroy_node()
    rclpy.try_shutdown()
