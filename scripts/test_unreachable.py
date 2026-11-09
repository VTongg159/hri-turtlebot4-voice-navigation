#!/usr/bin/env python3
"""Block a real Gazebo doorway temporarily; verify the voice mission stops on failure."""

import json
import subprocess
import time
from pathlib import Path
import rclpy
from nav2_msgs.srv import ClearEntireCostmap
from test_live_pipeline import Probe


def service(name, request_type, request):
    response = subprocess.run(
        [
            "gz",
            "service",
            "-s",
            name,
            "--reqtype",
            request_type,
            "--reptype",
            "gz.msgs.Boolean",
            "--timeout",
            "5000",
            "--req",
            request,
        ],
        capture_output=True,
        text=True,
        timeout=8,
    )
    print(response.stdout, response.stderr, flush=True)
    if "data: true" not in response.stdout:
        raise RuntimeError(f"Gazebo service failed: {name}")


rclpy.init()
p = Probe()
p.scenario = "T12_actual_blocked_room"
created = False
try:
    # Do not overlap the main integration run or preempt its Nav2 goals.
    def earlier_done():
        path = Path("evidence/live_pipeline_results.json")
        return (
            path.exists()
            and len(json.loads(path.read_text())) == 7
            and all(r["passed"] for r in json.loads(path.read_text()))
        )

    p.wait(earlier_done, 240)
    settle = time.monotonic() + 2
    while time.monotonic() < settle:
        rclpy.spin_once(p, timeout_sec=0.1)
    if p.events and p.events[-1]["busy"]:
        raise RuntimeError("Another mission is active")
    sdf = """<sdf version='1.9'><model name='week7_unreachable_blocker'><static>true</static><pose>-3.5 2.5 0.45 0 0 0</pose><link name='link'><collision name='collision'><geometry><box><size>2.6 2.6 0.9</size></box></geometry></collision><visual name='visual'><geometry><box><size>2.6 2.6 0.9</size></box></geometry><material><ambient>0.85 0.12 0.08 1</ambient><diffuse>0.85 0.12 0.08 1</diffuse></material></visual></link></model></sdf>"""
    Path("evidence/unreachable_blocker.sdf").write_text(sdf)
    service("/world/semantic_campus/create", "gz.msgs.EntityFactory", "sdf: " + json.dumps(sdf))
    created = True
    i = p.send("Đi từ A đến C")
    p.wait(lambda: p.terminal(i) is not None, 210)
    terminal = p.terminal(i)
    actions = [e for e in p.events[i:] if e["event"] == "ACTION_TERMINAL"]
    later_goal = any(
        e["event"] == "GOAL_ACCEPTED" and e["current_target"] == "C" for e in p.events[i:]
    )
    failed_action = any(e.get("action_status") == 6 for e in actions)
    result = dict(
        test="T12_real_Gazebo_unreachable",
        passed=terminal["state"] == "FAILED" and failed_action and not later_goal,
        source="Gazebo collision blocker at A, no mocked actions",
        terminal=terminal,
        action_results=actions,
        later_waypoint_sent=later_goal,
    )
    Path("evidence/unreachable_result.json").write_text(
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
    if created:
        service(
            "/world/semantic_campus/remove",
            "gz.msgs.Entity",
            'name: "week7_unreachable_blocker" type: MODEL',
        )
        for name in [
            "/global_costmap/clear_entirely_global_costmap",
            "/local_costmap/clear_entirely_local_costmap",
        ]:
            client = p.create_client(ClearEntireCostmap, name)
            if client.wait_for_service(timeout_sec=3):
                future = client.call_async(ClearEntireCostmap.Request())
                rclpy.spin_until_future_complete(p, future, timeout_sec=5)
    p.destroy_node()
    rclpy.try_shutdown()
