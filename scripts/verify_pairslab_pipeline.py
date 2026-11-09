#!/usr/bin/env python3
"""New-scene parser→controller→Nav2 test. Input is explicitly a keyboard transcript."""

from pathlib import Path
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String

rclpy.init()
node = Node("pairslab_pipeline_test")
events = []
parsed = []
qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
sub = node.create_subscription(
    String, "/voice/navigation_status", lambda m: events.append(json.loads(m.data)), qos
)
parse_sub = node.create_subscription(
    String, "/voice/parsed_command", lambda m: parsed.append(json.loads(m.data)), 10
)
pub = node.create_publisher(String, "/voice/transcript", 10)


def wait(predicate, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        if predicate():
            return
    raise TimeoutError(events[-3:])


try:
    wait(lambda: pub.get_subscription_count() > 0 and bool(events), 20)
    begin = len(events)
    pub.publish(String(data="Đi đến phòng TurtleBot"))
    wait(lambda: any(e.get("event") == "ACCEPTED" for e in events[begin:]), 20)
    wait(
        lambda: any(
            e.get("state") in ["SUCCEEDED", "FAILED", "CANCELED"] and not e.get("busy")
            for e in events[begin:]
        ),
        180,
    )
    terminal = next(
        e
        for e in reversed(events[begin:])
        if e.get("state") in ["SUCCEEDED", "FAILED", "CANCELED"] and not e.get("busy")
    )
    result = dict(
        test="PAIRS scene parser/controller/Nav2",
        input="keyboard transcript; microphone not used",
        passed=terminal["state"] == "SUCCEEDED" and terminal["waypoints"] == ["F"],
        parsed=parsed,
        terminal=terminal,
    )
    Path("evidence/pairslab_redesign/pipeline.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )
    Path("evidence/pairslab_redesign/pipeline_events.json").write_text(
        json.dumps(events, indent=2, ensure_ascii=False)
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    assert result["passed"]
finally:
    node.destroy_node()
    rclpy.try_shutdown()
