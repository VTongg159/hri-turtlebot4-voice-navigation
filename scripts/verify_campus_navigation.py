#!/usr/bin/env python3
"""Actual Nav2 integration check; no mocks. Run only in the campus simulation."""

import argparse
import json
import math
from pathlib import Path
import time
import yaml
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tb4_voice_navigation.semantic_map import SemanticMap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--regions", default="src/tb4_voice_navigation/config/pairs_regions.yaml")
    p.add_argument("--waypoints", nargs="+", default=["A", "B", "D", "C", "E", "F"])
    p.add_argument("--initialize", action="store_true", help="ONLY on freshly spawned simulation")
    p.add_argument("--output", default="evidence/pairslab_redesign/navigation.json")
    args = p.parse_args()
    s = SemanticMap(args.regions)
    rclpy.init()
    nav = BasicNavigator()
    nav.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])

    def pose(x, y, yaw):
        g = PoseStamped()
        g.header.frame_id = s.frame
        g.header.stamp = nav.get_clock().now().to_msg()
        g.pose.position.x = float(x)
        g.pose.position.y = float(y)
        g.pose.orientation.z = math.sin(yaw / 2)
        g.pose.orientation.w = math.cos(yaw / 2)
        return g

    if args.initialize:
        spawn = yaml.safe_load(Path(args.regions).read_text()).get("spawn_map", [-5.5, 0, 0])
        nav.setInitialPose(pose(*spawn))
    nav.waitUntilNav2Active()
    results = []
    try:
        for key in args.waypoints:
            region = s.lookup(key)
            g = region["goal"]
            target = pose(g["x"], g["y"], g["yaw"])
            start = time.monotonic()
            accepted = nav.goToPose(target)
            last_feedback = None
            print(f"GOAL {key} accepted={accepted}", flush=True)
            if not accepted:
                raise RuntimeError("Goal rejected")
            while not nav.isTaskComplete():
                feedback = nav.getFeedback()
                if feedback:
                    last_feedback = feedback
                if time.monotonic() - start > 180:
                    nav.cancelTask()
                    raise TimeoutError("Goal timeout")
            result = nav.getResult()
            item = dict(
                region=key,
                result=result.name,
                elapsed_wall_s=round(time.monotonic() - start, 2),
                goal=g,
            )
            if last_feedback:
                pos = last_feedback.current_pose.pose.position
                item["last_feedback_xy"] = [pos.x, pos.y]
                item["distance_to_goal_m"] = math.hypot(pos.x - g["x"], pos.y - g["y"])
                item["recoveries"] = last_feedback.number_of_recoveries
            results.append(item)
            Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))
            print(json.dumps(item), flush=True)
            if result != TaskResult.SUCCEEDED:
                raise RuntimeError("Stop after unsuccessful waypoint")
    finally:
        nav.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
