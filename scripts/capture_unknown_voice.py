#!/usr/bin/env python3
"""Capture a real microphone rejection trial in a live terminal; no injected text."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from std_msgs.msg import String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformException, TransformListener

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "evidence/voice_demo/unknown_region_live"
PUBLIC = ROOT / "submission/evidence/unknown_region_voice"


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node("unknown_region_voice_capture")
    node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
    tf = Buffer()
    listener = TransformListener(tf, node)
    state = {"asr": {}, "parser": {}, "navigation": {}}
    events = []
    poses = []
    trial_start = time.time()

    def receive(kind, msg):
        data = json.loads(msg.data)
        if data.get("wall_time", trial_start) < trial_start and kind != "navigation":
            return
        state[kind] = data
        events.append(dict(received_wall_time=time.time(), topic=kind, data=data))
        if kind == "parser" or (
            kind == "asr"
            and data.get("event") in ["RECORDING", "TRANSCRIPT", "NO_SPEECH", "ASR_ERROR"]
        ):
            print(kind.upper() + ": " + json.dumps(data, ensure_ascii=False), flush=True)
        if kind == "navigation":
            print("NAVIGATION: " + json.dumps(data, ensure_ascii=False), flush=True)

    qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for kind, topic, q in [
        ("asr", "/voice/asr_status", qos),
        ("parser", "/voice/parsed_command", 10),
        ("navigation", "/voice/navigation_status", qos),
    ]:
        node.create_subscription(String, topic, lambda m, k=kind: receive(k, m), q)

    def sample():
        try:
            t = tf.lookup_transform("map", "base_link", Time())
        except TransformException:
            return
        poses.append(
            dict(wall_time=time.time(), x=t.transform.translation.x, y=t.transform.translation.y)
        )

    node.create_timer(0.2, sample)
    start = node.create_client(Trigger, "/voice/record/start")
    print("$ python scripts/capture_unknown_voice.py", flush=True)
    print("Input: microphone / Whisper ASR. Waiting for operator start.", flush=True)
    (LOCAL / "terminal_ready").touch()
    while not (LOCAL / "start_recording").exists():
        rclpy.spin_once(node, timeout_sec=0.1)
    assert state["navigation"].get("state") == "IDLE" and poses
    assert start.wait_for_service(timeout_sec=5)
    record_begin = time.time()
    future = start.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=5)
    assert future.done() and future.result().success
    print("MICROPHONE RECORDING — say: Đi đến khu vực Z", flush=True)
    deadline = time.monotonic() + 100
    rejected_at = None
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            parsed, nav = state["parser"], state["navigation"]
            if (
                parsed.get("error", {}).get("code") == "UNKNOWN_REGION"
                and nav.get("event") == "REJECTED"
            ):
                rejected_at = rejected_at or time.time()
                if time.time() - rejected_at >= 5:
                    break
            if state["asr"].get("event") in ["NO_SPEECH", "ASR_ERROR"]:
                raise RuntimeError(state["asr"])
        else:
            raise TimeoutError(state)
        relevant = [p for p in poses if p["wall_time"] >= record_begin]
        assert len(relevant) > 10
        first, last = relevant[0], relevant[-1]
        displacement = ((last["x"] - first["x"]) ** 2 + (last["y"] - first["y"]) ** 2) ** 0.5
        excursion = max(
            ((p["x"] - first["x"]) ** 2 + (p["y"] - first["y"]) ** 2) ** 0.5 for p in relevant
        )
        assert state["asr"]["event"] == "TRANSCRIPT"
        assert state["parser"]["error"]["code"] == "UNKNOWN_REGION"
        assert state["navigation"]["state"] == "IDLE" and not state["navigation"]["busy"]
        accepted = [
            e
            for e in events
            if e["topic"] == "navigation"
            and e["data"].get("event") == "ACCEPTED"
            and e["data"].get("wall_time", 0) >= record_begin
        ]
        assert not accepted and excursion < 0.05
        print(
            f"TF map -> base_link: {len(relevant)} samples, displacement={displacement:.6f} m, max excursion={excursion:.6f} m",
            flush=True,
        )
        print(
            "RESULT: UNKNOWN_REGION | state=IDLE | busy=false | accepted navigation goals=0",
            flush=True,
        )
        (PUBLIC / "events.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
        )
        (PUBLIC / "tf_samples.json").write_text(json.dumps(relevant, indent=2) + "\n")
        audio = ROOT / state["asr"]["audio_file"]
        receipt = dict(
            passed=True,
            input="real microphone",
            asr=state["asr"],
            parser=state["parser"],
            navigation=state["navigation"],
            tf_displacement_m=displacement,
            tf_max_excursion_m=excursion,
            accepted_navigation_goals=0,
            audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
            note="Fresh controller started IDLE before this trial; no navigation commands or pose resets during recording. Raw microphone WAV stays local.",
        )
        time.sleep(1)
        tree = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
        frame = next(
            l
            for l in tree.splitlines()
            if "mutter-x11-frames" in l
            and os.environ.get("UNKNOWN_TRIAL_TITLE", "Unknown region voice trial") in l
        )
        client = next(
            l
            for l in tree.splitlines()
            if '("terminator" "Terminator")' in l
            and os.environ.get("UNKNOWN_TRIAL_TITLE", "Unknown region voice trial") in l
        )
        wid = re.search(r"0x[0-9a-f]+", frame).group()
        client_id = re.search(r"0x[0-9a-f]+", client).group()
        subprocess.run(["xdotool", "windowactivate", client_id], check=True, timeout=3)
        target = ROOT / "submission/figures/unknown_region_voice_idle.png"
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
                os.environ.get("DISPLAY", ":1"),
                "-frames:v",
                "1",
                str(target),
            ],
            check=True,
            timeout=10,
        )
        receipt.update(
            screenshot="figures/" + target.name,
            screenshot_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            capture="Unmodified screenshot of live terminal during actual ASR/parser trial",
        )
        (PUBLIC / "acceptance.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        )
        print("Screenshot saved:", target, flush=True)
        input("Press Enter to close this terminal.")
    finally:
        del listener
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
