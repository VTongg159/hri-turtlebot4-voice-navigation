#!/usr/bin/env python3
"""Real ROS/Nav2 integration scenarios. Keyboard transcripts are labelled as such."""

import json
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String


class Probe(Node):
    def __init__(self):
        super().__init__("live_pipeline_test")
        self.events = []
        self.parsed = []
        self.results = []
        self.scenario = "startup"
        qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.sub = self.create_subscription(String, "/voice/navigation_status", self.status, qos)
        self.parser_sub = self.create_subscription(
            String, "/voice/parsed_command", lambda m: self.parsed.append(json.loads(m.data)), 10
        )
        self.pub = self.create_publisher(String, "/voice/transcript", 10)

    def status(self, msg):
        data = json.loads(msg.data)
        self.events.append(data)
        with open("evidence/live_pipeline_events.jsonl", "a") as f:
            f.write(json.dumps(dict(scenario=self.scenario, **data), ensure_ascii=False) + "\n")

    def wait(self, predicate, timeout=20):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.1)
            if predicate():
                return
        raise TimeoutError(f"Scenario {self.scenario}: {self.events[-2:]}")

    def send(self, text):
        start = len(self.events)
        self.pub.publish(String(data=text))
        print("KEYBOARD TEST:", text, flush=True)
        return start

    def event_after(self, index, event):
        return any(e["event"] == event for e in self.events[index:])

    def terminal(self, index):
        return next(
            (
                e
                for e in reversed(self.events[index:])
                if e["event"] in ("ALL_WAYPOINTS_REACHED",)
                or (e["state"] in ("FAILED", "CANCELED") and not e["busy"])
            ),
            None,
        )

    def record(self, name, passed, detail):
        self.results.append(dict(test=name, passed=bool(passed), detail=detail))
        Path("evidence/live_pipeline_results.json").write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2)
        )
        print(self.results[-1], flush=True)
        if not passed:
            raise AssertionError(name)


def main():
    rclpy.init()
    p = Probe()
    try:
        p.wait(lambda: p.pub.get_subscription_count() > 0 and bool(p.events))
        p.scenario = "T09_unknown"
        i = p.send("Đi đến khu vực Z")
        p.wait(lambda: p.event_after(i, "REJECTED"))
        p.record("T09_unknown_no_goal", not p.event_after(i, "GOAL_ACCEPTED"), p.events[-1])
        p.scenario = "T13_T14_cancel_busy"
        i = p.send("Đi từ A qua C đến B")
        p.wait(lambda: p.event_after(i, "GOAL_ACCEPTED"), 25)
        j = p.send("Đi đến E")
        p.wait(lambda: p.event_after(j, "BUSY"))
        p.record("T14_busy_reject", True, p.events[-1])
        k = p.send("Dừng lại")
        p.wait(lambda: p.terminal(k) is not None, 20)
        terminal = p.terminal(k)
        canceled = any(
            e.get("action_kind") == "nav" and e.get("action_status") == 5 for e in p.events[k:]
        )
        p.record("T13_real_action_cancel", terminal["state"] == "CANCELED" and canceled, terminal)
        p.scenario = "T08_multi_order"
        i = p.send("Đi từ A qua C đến B")
        p.wait(lambda: p.terminal(i) is not None, 240)
        terminal = p.terminal(i)
        visited = [e["current_target"] for e in p.events[i:] if e["event"] == "WAYPOINT_SUCCEEDED"]
        p.record(
            "T08_A_C_B",
            terminal["state"] == "SUCCEEDED" and visited == ["A", "C", "B"],
            dict(visited=visited, terminal=terminal),
        )
        p.scenario = "T07_source_order"
        i = p.send("Đi từ A đến B")
        p.wait(lambda: p.terminal(i) is not None, 240)
        terminal = p.terminal(i)
        visited = [e["current_target"] for e in p.events[i:] if e["event"] == "WAYPOINT_SUCCEEDED"]
        p.record(
            "T07_current_to_A_to_B",
            terminal["state"] == "SUCCEEDED" and visited == ["A", "B"],
            dict(visited=visited, terminal=terminal),
        )
        p.scenario = "source_skip_near"
        i = p.send("Đi từ B đến C")
        p.wait(lambda: p.terminal(i) is not None, 180)
        p.record(
            "source_skip_near",
            p.terminal(i)["state"] == "SUCCEEDED" and p.event_after(i, "SOURCE_ALREADY_REACHED"),
            p.terminal(i),
        )
        p.scenario = "T06_semantic_alias"
        i = p.send("Đi đến phòng thí nghiệm")
        p.wait(lambda: p.terminal(i) is not None, 180)
        p.record(
            "T06_alias_keyboard_navigation",
            p.terminal(i)["state"] == "SUCCEEDED" and p.terminal(i)["waypoints"] == ["B"],
            p.terminal(i),
        )
    finally:
        if p.events and p.events[-1].get("busy"):
            i = p.send("Dừng lại")
            try:
                p.wait(lambda: p.terminal(i) is not None, 15)
            except TimeoutError:
                pass
        p.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
