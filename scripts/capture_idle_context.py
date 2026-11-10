#!/usr/bin/env python3
"""Pair native terminal and RViz screenshots after the real voice rejection trial."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from PIL import Image

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

ROOT = Path(__file__).resolve().parents[1]


def capture(title, client_class, target):
    tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    frame = next(l for l in tree.splitlines() if title in l and "mutter-x11-frames" in l)
    client = next(l for l in tree.splitlines() if title in l and client_class in l)
    wid = re.search(r"0x[0-9a-f]+", frame).group()
    cid = re.search(r"0x[0-9a-f]+", client).group()
    subprocess.run(["xdotool", "windowactivate", cid], check=True, timeout=3)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "x11grab",
            "-window_id",
            wid,
            "-i",
            ":1",
            "-frames:v",
            "1",
            str(target),
        ],
        check=True,
        timeout=10,
    )
    return dict(
        file=str(target.relative_to(ROOT / "submission")),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        wall_time=time.time(),
        window_id=wid,
    )


def main():
    folder = ROOT / "submission/evidence/unknown_region_voice"
    rclpy.init()
    node = Node("unknown_voice_idle_context")
    node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    statuses = []
    qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(
        String, "/voice/navigation_status", lambda m: statuses.append(json.loads(m.data)), qos
    )
    positions = []
    started = time.time()
    captures = None
    while time.time() - started < 10:
        rclpy.spin_once(node, timeout_sec=0.1)
        try:
            t = buffer.lookup_transform("map", "base_link", Time())
        except TransformException:
            continue
        positions.append(
            dict(wall_time=time.time(), x=t.transform.translation.x, y=t.transform.translation.y)
        )
        if time.time() - started > 3 and captures is None:
            assert statuses[-1]["state"] == "IDLE" and not statuses[-1]["busy"]
            terminal = capture(
                "Unknown region voice trial 3",
                '("terminator" "Terminator")',
                folder / "terminal_context.png",
            )
            rviz = capture("pairs_lab_idle.rviz", '("rviz2" "rviz2")', folder / "rviz_context.png")
            captures = [terminal, rviz]
    assert captures and positions
    original = json.loads((folder / "tf_samples.json").read_text())[-1]
    offset = max(
        ((p["x"] - original["x"]) ** 2 + (p["y"] - original["y"]) ** 2) ** 0.5 for p in positions
    )
    assert offset < 0.05
    target = ROOT / "submission/figures/unknown_region_voice_idle_rviz.png"
    # Explicit montage of untouched native screenshots. Pad only if window
    # decorations differ in height; no labels or data painted onto either one.
    height = max(
        Image.open(folder / name).height for name in ["terminal_context.png", "rviz_context.png"]
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(folder / "terminal_context.png"),
            "-i",
            str(folder / "rviz_context.png"),
            "-filter_complex",
            f"[0:v]pad=iw:{height}:0:0:white[a];[1:v]pad=iw:{height}:0:0:white[b];[a][b]hstack=inputs=2[v]",
            "-map",
            "[v]",
            "-frames:v",
            "1",
            str(target),
        ],
        check=True,
    )
    proof = dict(
        capture="Montage of two unmodified native window screenshots taken after the voice trial",
        chronology="Terminal remains open with original trial output; RViz shows live IDLE at the same unchanged TF position after rejection",
        screenshots=captures,
        screenshot=str(target.relative_to(ROOT / "submission")),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        live_status=statuses[-1],
        positions=positions,
        maximum_offset_from_voice_trial_m=offset,
        rviz_config="src/tb4_voice_navigation/rviz/pairs_lab_idle.rviz",
        original_voice_proof="acceptance.json",
    )
    (folder / "rviz_context.json").write_text(
        json.dumps(proof, indent=2, ensure_ascii=False) + "\n"
    )
    print("PASS: robot IDLE; maximum TF offset from voice trial:", offset)
    print(target)
    del listener
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
