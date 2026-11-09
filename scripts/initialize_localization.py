#!/usr/bin/env python3
"""Seed AMCL only for a freshly spawned campus robot; never change Gazebo pose."""

import argparse
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from tf2_ros import Buffer, TransformListener, TransformException
from rclpy.time import Time

p = argparse.ArgumentParser()
p.add_argument("--fresh-spawn", action="store_true", required=True)
p.add_argument("--x", type=float, default=-11.0)
p.add_argument("--y", type=float, default=0.0)
p.add_argument("--yaw", type=float, default=0.0)
p.add_argument("--timeout", type=float, default=60.0)
a = p.parse_args()
if not all(math.isfinite(v) for v in [a.x, a.y, a.yaw, a.timeout]) or a.timeout <= 0:
    raise SystemExit("Invalid parameters")
rclpy.init()
node = Node("initialize_campus_localization")
node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
pub = node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
buffer = Buffer()
listener = TransformListener(buffer, node)
end = time.monotonic() + a.timeout
try:
    while (
        node.get_clock().now().nanoseconds == 0 or pub.get_subscription_count() == 0
    ) and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    pose = PoseWithCovarianceStamped()
    pose.header.frame_id = "map"
    pose.pose.pose.position.x = a.x
    pose.pose.pose.position.y = a.y
    pose.pose.pose.orientation.z = math.sin(a.yaw / 2)
    pose.pose.pose.orientation.w = math.cos(a.yaw / 2)
    pose.pose.covariance[0] = 0.25
    pose.pose.covariance[7] = 0.25
    pose.pose.covariance[35] = 0.0685
    pose.header.stamp = node.get_clock().now().to_msg()
    pub.publish(pose)
    ready = False
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        try:
            t = buffer.lookup_transform("map", "base_link", Time())
        except TransformException:
            continue
        if math.hypot(t.transform.translation.x - a.x, t.transform.translation.y - a.y) < 0.5:
            ready = True
            break
    if not ready:
        raise TimeoutError("AMCL/map TF chưa sẵn sàng")
    for name in ["map_server", "amcl", "planner_server", "controller_server", "bt_navigator"]:
        client = node.create_client(GetState, f"/{name}/get_state")
        active = False
        while time.monotonic() < end:
            if not client.wait_for_service(timeout_sec=0.5):
                continue
            future = client.call_async(GetState.Request())
            rclpy.spin_until_future_complete(node, future, timeout_sec=1)
            if future.done() and future.result().current_state.id == 3:
                active = True
                break
        if not active:
            raise TimeoutError(f"{name} chưa active")
    print(
        "READY: AMCL map→base_link và lifecycle Nav2 active; không gửi navigation goal, không teleport."
    )
finally:
    node.destroy_node()
    rclpy.try_shutdown()
