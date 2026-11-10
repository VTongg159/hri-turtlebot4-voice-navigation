#!/usr/bin/env python3
"""Run real Nav2 goals A B D C E F and record measured map->base_link TF."""

import json
import math
from pathlib import Path
import time

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import rclpy
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener

from tb4_voice_navigation.semantic_map import SemanticMap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/trajectory_pairs_20261110"


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    semantic = SemanticMap(ROOT / "submission/config/pairs_regions.yaml")
    rclpy.init()
    nav = BasicNavigator(node_name="pairs_trajectory_recorder")
    nav.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
    buffer = Buffer()
    listener = TransformListener(buffer, nav)
    active = {"goal": None}
    samples = (OUT / "tf_samples.jsonl").open("w", buffering=1)
    amcl = (OUT / "amcl_samples.jsonl").open("w", buffering=1)

    def record_tf():
        try:
            t = buffer.lookup_transform("map", "base_link", Time())
        except TransformException:
            return
        p, q = t.transform.translation, t.transform.rotation
        stamp = t.header.stamp.sec + t.header.stamp.nanosec * 1e-9
        age = nav.get_clock().now().nanoseconds * 1e-9 - stamp
        if abs(age) > 1:
            return
        samples.write(
            json.dumps(
                dict(
                    wall_time=time.time(),
                    stamp=stamp,
                    goal=active["goal"],
                    x=p.x,
                    y=p.y,
                    yaw=math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)),
                    tf_age_s=age,
                )
            )
            + "\n"
        )

    def record_amcl(m):
        p = m.pose.pose.position
        amcl.write(
            json.dumps(
                dict(
                    stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                    x=p.x,
                    y=p.y,
                    covariance=list(m.pose.covariance),
                )
            )
            + "\n"
        )

    timer = nav.create_timer(0.2, record_tf)
    sub = nav.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", record_amcl, 20)
    results = []
    try:
        nav.waitUntilNav2Active()
        for _ in range(15):
            rclpy.spin_once(nav, timeout_sec=0.1)
        for key in "ABDCEF":
            active["goal"] = key
            record_tf()
            g = semantic.lookup(key)["goal"]
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = nav.get_clock().now().to_msg()
            pose.pose.position.x, pose.pose.position.y = float(g["x"]), float(g["y"])
            pose.pose.orientation.z = math.sin(g["yaw"] / 2)
            pose.pose.orientation.w = math.cos(g["yaw"] / 2)
            start = time.time()
            assert nav.goToPose(pose), f"Rejected goal {key}"
            print("GOAL", key, "accepted", flush=True)
            while not nav.isTaskComplete():
                if time.time() - start > 240:
                    nav.cancelTask()
                    raise TimeoutError(key)
            result = nav.getResult()
            record_tf()
            t = buffer.lookup_transform("map", "base_link", Time())
            x, y = t.transform.translation.x, t.transform.translation.y
            col, row = semantic.map.cell(x, y)
            inside = bool(semantic.lookup(key)["mask"][row, col])
            item = dict(
                region=key,
                result=result.name,
                started_wall_time=start,
                ended_wall_time=time.time(),
                goal=g,
                arrival_xy=[x, y],
                inside_region=inside,
            )
            results.append(item)
            (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(item), flush=True)
            assert result == TaskResult.SUCCEEDED and inside
        print("PASS: six real Nav2 goals, TF trajectory recorded", flush=True)
    finally:
        nav.destroy_timer(timer)
        nav.destroy_subscription(sub)
        del listener
        samples.close()
        amcl.close()
        nav.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
