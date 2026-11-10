#!/usr/bin/env python3
"""Run a keyboard multi-waypoint command and capture the actual live RViz window."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from nav_msgs.msg import Path as RosPath
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission/evidence/rviz_multiwaypoint"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Resume capture of the existing command without publishing another",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node("capture_multiwaypoint_rviz")
    node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    state = {"status": {}, "parsed": {}, "plan": None, "captured": False}
    if args.observe:
        history = [json.loads(line) for line in (OUT / "events.jsonl").read_text().splitlines()]
        state["parsed"] = next(row["data"] for row in reversed(history) if row["topic"] == "parsed")
    events = (OUT / "events.jsonl").open("a" if args.observe else "w", buffering=1)

    def receive(kind, data):
        state[kind] = data
        events.write(
            json.dumps(dict(wall_time=time.time(), topic=kind, data=data), ensure_ascii=False)
            + "\n"
        )

    qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(
        String, "/voice/navigation_status", lambda m: receive("status", json.loads(m.data)), qos
    )
    node.create_subscription(
        String, "/voice/parsed_command", lambda m: receive("parsed", json.loads(m.data)), 10
    )

    def plan(m):
        data = dict(
            frame_id=m.header.frame_id,
            stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
            received_wall_time=time.time(),
            points=[[p.pose.position.x, p.pose.position.y] for p in m.poses],
        )
        state["plan"] = data

    node.create_subscription(RosPath, "/plan", plan, 10)
    pub = node.create_publisher(String, "/voice/transcript", 10)
    deadline = time.monotonic() + 300
    while pub.get_subscription_count() == 0:
        rclpy.spin_once(node, timeout_sec=0.1)
        assert time.monotonic() < deadline
    text = "Đi từ A qua C đến D"
    started = 0 if args.observe else time.time()
    if not args.observe:
        pub.publish(String(data=text))
    print("KEYBOARD INPUT:", text, flush=True)
    receipt = None
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            parsed, status = state["parsed"], state["status"]
            identity = parsed.get("command_id")
            if parsed.get("waypoints") != ["A", "C", "D"] or status.get("command_id") != identity:
                continue
            assert status.get("wall_time", 0) >= started
            try:
                t = buffer.lookup_transform("map", "base_link", Time())
            except TransformException:
                continue
            x, y = t.transform.translation.x, t.transform.translation.y
            if (
                not state["captured"]
                and status.get("state") == "NAVIGATING"
                and status.get("current_target") == "D"
                and 3.5 < x < 5.5
                and 0.3 < y < 2.5
                and state["plan"]
                and len(state["plan"]["points"]) > 2
            ):
                tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
                line = next(
                    line
                    for line in tree.splitlines()
                    if "mutter-x11-frames" in line and "pairs_lab_multiwaypoint.rviz" in line
                )
                window = re.search(r"0x[0-9a-f]+", line).group()
                client_line = next(
                    line
                    for line in tree.splitlines()
                    if '("rviz2" "rviz2")' in line and "pairs_lab_multiwaypoint.rviz" in line
                )
                client = re.search(r"0x[0-9a-f]+", client_line).group()
                subprocess.run(["xdotool", "windowactivate", client], check=True, timeout=3)
                screenshot = ROOT / "submission/figures/rviz_multiwaypoint_plan.png"
                captured_at = time.time()
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-f",
                        "x11grab",
                        "-window_id",
                        window,
                        "-i",
                        os.environ.get("DISPLAY", ":1"),
                        "-frames:v",
                        "1",
                        str(screenshot),
                    ],
                    check=True,
                    timeout=15,
                )
                receipt = dict(
                    capture="Unmodified X11 screenshot of live RViz while navigating C->D",
                    screenshot="figures/rviz_multiwaypoint_plan.png",
                    sha256=hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                    window_id=window,
                    capture_wall_time=captured_at,
                    input_source="keyboard transcript",
                    transcript=text,
                    parsed=parsed,
                    navigation_status_at_trigger=status,
                    tf_at_trigger=dict(x=x, y=y, frame="map->base_link"),
                    plan_topic="/plan",
                    plan_at_trigger=state["plan"],
                    rviz_config="src/tb4_voice_navigation/rviz/pairs_lab_multiwaypoint.rviz",
                    note="Nav2 /plan is the currently active leg toward D; A->C->D is the command route. Straight waypoint-order line disabled to avoid confusing it with the planned path.",
                )
                (OUT / "capture.json").write_text(
                    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
                )
                state["captured"] = True
                print("CAPTURED:", screenshot, flush=True)
            if status.get("state") in ["SUCCEEDED", "FAILED", "CANCELED"] and not status.get(
                "busy"
            ):
                (OUT / "result.json").write_text(
                    json.dumps(status, ensure_ascii=False, indent=2) + "\n"
                )
                assert status["state"] == "SUCCEEDED", status
                assert state["captured"], "Mission ended without requested screenshot"
                print("PASS: A C D SUCCEEDED, live mid-leg screenshot captured", flush=True)
                return
        raise TimeoutError(state["status"])
    finally:
        events.close()
        del listener
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
