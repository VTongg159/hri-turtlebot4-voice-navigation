#!/usr/bin/env python3
"""Film a real microphone source-destination trial, retaining raw events and audio."""

import hashlib
import json
from pathlib import Path
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rclpy.time import Time
from std_msgs.msg import String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformException, TransformListener

from tb4_voice_navigation.semantic_map import SemanticMap

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "evidence/voice_demo/source_destination_live"


def main():
    rclpy.init()
    node = Node("source_destination_voice_trial")
    node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
    semantic = SemanticMap(ROOT / "submission/config/pairs_regions.yaml")
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    started = time.time()
    state = {"asr": {}, "parsed": {}, "navigation": {}}
    rows = []
    positions = []
    event_file = (LOCAL / "events.jsonl").open("w", buffering=1)

    def receive(kind, m):
        data = json.loads(m.data)
        state[kind] = data
        event = dict(received_wall_time=time.time(), topic=kind, data=data)
        rows.append(event)
        event_file.write(json.dumps(event, ensure_ascii=False) + "\n")
        if data.get("wall_time", started) < started:
            return
        if kind == "asr" and data.get("event") in [
            "RECORDING",
            "TRANSCRIPT",
            "NO_SPEECH",
            "ASR_ERROR",
        ]:
            print("ASR:", data.get("event"), "|", data.get("message"), flush=True)
        if kind == "parsed":
            print("PARSER:", json.dumps(data, ensure_ascii=False), flush=True)
        if kind == "navigation" and data.get("event") in [
            "ACCEPTED",
            "GOAL_ACCEPTED",
            "ACTION_TERMINAL",
            "WAYPOINT_SUCCEEDED",
            "ALL_WAYPOINTS_REACHED",
            "REJECTED",
            "LOCALIZATION_LOST",
        ]:
            print(
                "NAV2:",
                data.get("event"),
                "| state=" + data.get("state", ""),
                "| target=" + str(data.get("current_target")),
                "| time=" + str(data.get("wall_time")),
                "| action=" + str(data.get("action_kind", "")),
                "| status=" + str(data.get("action_status", "")),
                "| error=" + str(data.get("error_code", "")),
                flush=True,
            )

    qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for kind, topic, quality in [
        ("asr", "/voice/asr_status", qos),
        ("parsed", "/voice/parsed_command", 10),
        ("navigation", "/voice/navigation_status", qos),
    ]:
        node.create_subscription(String, topic, lambda m, k=kind: receive(k, m), quality)

    def sample():
        try:
            t = buffer.lookup_transform("map", "base_link", Time())
        except TransformException:
            return
        positions.append(
            dict(wall_time=time.time(), x=t.transform.translation.x, y=t.transform.translation.y)
        )

    node.create_timer(0.2, sample)
    start_service = node.create_client(Trigger, "/voice/record/start")
    print("$ python scripts/record_source_destination_voice.py", flush=True)
    print("Input: real microphone | Expected command: Đi từ khu vực A đến khu vực B", flush=True)
    print("Waiting for operator. Recording has not started.", flush=True)
    (LOCAL / "terminal_ready").touch()
    ready_end = time.monotonic() + 180
    while time.monotonic() < ready_end:
        rclpy.spin_once(node, timeout_sec=0.1)
        if positions and state["navigation"] and state["asr"].get("ready"):
            break
    assert state["asr"].get("ready"), "Whisper is not ready"
    input("READY. Press Enter to START microphone recording: ")
    assert positions
    origin = positions[-1]
    col, row = semantic.map.cell(origin["x"], origin["y"])
    assert semantic.lookup("F")["mask"][row, col], "Robot is not in F"
    assert not state["navigation"].get("busy")
    print(f"START: F | TF map -> base_link = ({origin['x']:.3f}, {origin['y']:.3f}) m", flush=True)
    raw = LOCAL / "screen_silent.mp4"
    capture_start = time.time()
    capture_log = (LOCAL / "ffmpeg_capture.log").open("w")
    recorder = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-f",
            "x11grab",
            "-video_size",
            "1920x1080",
            "-framerate",
            "15",
            "-i",
            ":1.0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            str(raw),
        ],
        stdin=subprocess.PIPE,
        stdout=capture_log,
        stderr=subprocess.STDOUT,
    )
    start_time = time.time()
    assert start_service.wait_for_service(timeout_sec=5)
    f = start_service.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, f, timeout_sec=5)
    if not (f.done() and f.result().success):
        recorder.communicate(input=b"q\n", timeout=20)
        raise RuntimeError("Microphone start service did not accept recording")
    (LOCAL / "microphone_started").touch()
    print("MICROPHONE RECORDING — say the command once, then remain silent.", flush=True)
    input("RECORDING. Speak once, then press Enter to STOP: ")
    stop_service = node.create_client(Trigger, "/voice/record/stop")
    assert stop_service.wait_for_service(timeout_sec=3)
    stop_future = stop_service.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, stop_future, timeout_sec=3)
    print("Processing ASR; please wait.", flush=True)
    deadline = time.monotonic() + 300
    identity = None
    success = False
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            asr, parsed, nav = state["asr"], state["parsed"], state["navigation"]
            if asr.get("wall_time", 0) >= start_time and asr.get("event") in [
                "NO_SPEECH",
                "ASR_ERROR",
                "CLIPPED_AUDIO",
                "NO_AUDIO",
            ]:
                raise RuntimeError(asr)
            if parsed.get("transcript") == asr.get("message") and asr.get("event") == "TRANSCRIPT":
                assert parsed.get("type") == "source_destination" and parsed.get("waypoints") == [
                    "A",
                    "B",
                ], parsed
                identity = parsed["command_id"]
            if (
                identity
                and nav.get("command_id") == identity
                and not nav.get("busy")
                and nav.get("state") in ["SUCCEEDED", "FAILED", "CANCELED"]
            ):
                assert nav["state"] == "SUCCEEDED", nav
                success = True
                break
        assert success, "Mission did not complete"
        events = [
            r["data"]
            for r in rows
            if r["topic"] == "navigation" and r["data"].get("command_id") == identity
        ]
        segments = []
        for key in ["A", "B"]:
            accepted = next(
                e
                for e in events
                if e.get("event") == "GOAL_ACCEPTED" and e.get("current_target") == key
            )
            terminal = next(
                e
                for e in events
                if e.get("event") == "ACTION_TERMINAL"
                and e.get("action_kind") == "nav"
                and e.get("current_target") == key
            )
            assert terminal["action_status"] == 4 and terminal["error_code"] == 0
            segments.append(
                dict(
                    goal=key,
                    goal_accepted_wall_time=accepted["wall_time"],
                    terminal_wall_time=terminal["wall_time"],
                    elapsed_s=terminal["wall_time"] - accepted["wall_time"],
                )
            )
        print("RESULT: F -> A -> B | SUCCEEDED", flush=True)
        print("command_id:", identity, flush=True)
        print(
            f"Time to A: {segments[0]['elapsed_s']:.3f} s | A -> B: {segments[1]['elapsed_s']:.3f} s",
            flush=True,
        )
        (LOCAL / "result.json").write_text(
            json.dumps(
                dict(
                    passed=True,
                    input_source="real microphone",
                    start_region="F",
                    start_tf=origin,
                    asr=state["asr"],
                    parsed=state["parsed"],
                    terminal=state["navigation"],
                    segments=segments,
                    capture_started_wall_time=capture_start,
                    audio_sha256=hashlib.sha256(
                        (ROOT / state["asr"]["audio_file"]).read_bytes()
                    ).hexdigest(),
                ),
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        (LOCAL / "tf_samples.json").write_text(json.dumps(positions, indent=2) + "\n")
        # Leave a readable final state in the continuous screen recording.
        end = time.monotonic() + 4
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        if not success and state["navigation"].get("busy"):
            cancel = node.create_client(Trigger, "/voice/cancel")
            if cancel.wait_for_service(timeout_sec=2):
                canceled = cancel.call_async(Trigger.Request())
                rclpy.spin_until_future_complete(node, canceled, timeout_sec=3)
                wait_end = time.monotonic() + 15
                while state["navigation"].get("busy") and time.monotonic() < wait_end:
                    rclpy.spin_once(node, timeout_sec=0.1)
        if recorder.poll() is None:
            recorder.stdin.write(b"q\n")
            recorder.stdin.flush()
            recorder.wait(timeout=20)
        capture_log.close()
        event_file.close()
        del listener
        node.destroy_node()
        rclpy.try_shutdown()
    input("Recording saved. Press Enter to close.")


if __name__ == "__main__":
    main()
