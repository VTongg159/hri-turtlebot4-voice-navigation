#!/usr/bin/env python3
"""Negative tests against real ROS actions/ALSA, with no fake action servers."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger

rclpy.init()
node = Node("live_failure_probe")
events = []
transcripts = []
results = []
qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
sub = node.create_subscription(
    String, "/tests/nav/status", lambda m: events.append(json.loads(m.data)), qos
)
voice_sub = node.create_subscription(
    String, "/tests/asr/status", lambda m: events.append(json.loads(m.data)), qos
)
transcript_sub = node.create_subscription(
    String, "/tests/asr/transcript", lambda m: transcripts.append(m.data), 10
)
pub = node.create_publisher(String, "/tests/nav/command", 10)


def wait(predicate, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        if predicate():
            return
    raise TimeoutError(events[-3:])


def record(test, passed, detail):
    results.append(dict(test=test, passed=bool(passed), detail=detail))
    Path("evidence/live_failures_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )
    print(results[-1], flush=True)
    if not passed:
        raise AssertionError(test)


def start(executable, parameters, remaps):
    args = [
        "ros2",
        "run",
        "tb4_voice_navigation",
        executable,
        "--ros-args",
        "-r",
        "__node:=failure_" + uuid.uuid4().hex[:8],
    ]
    for key, val in parameters.items():
        args += ["-p", f"{key}:={str(val).lower() if isinstance(val, bool) else val}"]
    for key, val in remaps.items():
        args += ["-r", f"{key}:={val}"]
    log = open(f"evidence/{executable}_negative_{len(results)}.log", "w")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    return proc, log


def stop(proc, log):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=5)
    log.close()


nav_remaps = {
    "/voice/parsed_command": "/tests/nav/command",
    "/voice/navigation_status": "/tests/nav/status",
    "/voice/cancel": "/tests/nav/cancel",
    "/voice/planned_path": "/tests/nav/path",
}
args = argparse.ArgumentParser()
args.add_argument("--timeout-test", action="store_true")
options = args.parse_args()
try:
    scenarios = [
        (
            "T11_nav2_unavailable",
            dict(navigate_action="/not_running_navigate_to_pose", server_timeout=3.0),
            "NAV2_NOT_READY",
        ),
        (
            "localization_unavailable",
            dict(base_frame="missing_base_frame", server_timeout=3.0),
            "LOCALIZATION_NOT_READY",
        ),
    ]
    if options.timeout_test:
        scenarios.append(("goal_timeout_real_cancel", dict(goal_timeout=0.3), "GOAL_TIMEOUT"))
    for name, parameters, expected in scenarios:
        events.clear()
        proc, log = start(
            "voice_navigation_node", dict(use_sim_time=True, **parameters), nav_remaps
        )
        try:
            wait(
                lambda: pub.get_subscription_count() > 0
                and any(e.get("event") == "READY" for e in events)
            )
            warmup = time.monotonic() + 3
            while time.monotonic() < warmup:
                rclpy.spin_once(node, timeout_sec=0.1)
            identity = uuid.uuid4().hex
            pub.publish(
                String(data=json.dumps(dict(command_id=identity, type="single", waypoints=["E"])))
            )
            wait(
                lambda: any(
                    e.get("command_id") == identity
                    and e.get("state") == "FAILED"
                    and not e.get("busy")
                    for e in events
                ),
                25,
            )
            terminal = next(
                e
                for e in reversed(events)
                if e.get("command_id") == identity and e.get("state") == "FAILED"
            )
            ok = expected in terminal["event"]
            if name == "goal_timeout_real_cancel":
                ok = ok and any(
                    e.get("action_kind") == "nav" and e.get("action_status") == 5 for e in events
                )
            record(name, ok, dict(terminal=terminal, events=events))
        finally:
            stop(proc, log)
    events.clear()
    transcripts.clear()
    mic_remaps = {
        "/voice/asr_status": "/tests/asr/status",
        "/voice/transcript": "/tests/asr/transcript",
        "/voice/record/start": "/tests/asr/start",
        "/voice/record/stop": "/tests/asr/stop",
        "/voice/record/discard": "/tests/asr/discard",
    }
    proc, log = start(
        "voice_recognition_node",
        dict(audio_device="__week7_nonexistent_device__", max_record_seconds=2),
        mic_remaps,
    )
    try:
        client = node.create_client(Trigger, "/tests/asr/start")
        wait(lambda: any(e.get("event") == "MODEL_READY" for e in events), 30)
        wait(lambda: client.service_is_ready())
        future = client.call_async(Trigger.Request())
        wait(lambda: future.done())
        wait(lambda: any(e.get("event") == "ASR_ERROR" for e in events))
        error = next(e for e in events if e.get("event") == "ASR_ERROR")
        record(
            "T10_missing_microphone_real_ALSA",
            proc.poll() is None and not transcripts and "AUDIO_DEVICE_ERROR" in error["message"],
            error,
        )
    finally:
        stop(proc, log)
finally:
    node.destroy_node()
    rclpy.try_shutdown()
