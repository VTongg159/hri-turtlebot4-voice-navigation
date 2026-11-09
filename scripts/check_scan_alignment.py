#!/usr/bin/env python3
"""Measure actual Gazebo scan endpoints against occupied cells in the prior map."""

import json
import argparse
from pathlib import Path
import math
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener, TransformException
from tb4_voice_navigation.semantic_map import OccupancyMap, MapError

parser = argparse.ArgumentParser()
parser.add_argument("--map", default="src/tb4_voice_navigation/maps/pairs_lab.yaml")
parser.add_argument("--output", default="evidence/pairslab_redesign/scan_alignment.json")
args = parser.parse_args()
rclpy.init()
node = Node("campus_scan_alignment")
node.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
buffer = Buffer()
listener = TransformListener(buffer, node)
latest = []
sub = node.create_subscription(
    LaserScan, "/scan", lambda msg: latest.append(msg), qos_profile_sensor_data
)
m = OccupancyMap(args.map)
distance = (
    cv2.distanceTransform((~m.occupied).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    * m.resolution
)
errors = []
count = 0
outside = 0
end = time.monotonic() + 25
while count < 10 and time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.1)
    if not latest:
        continue
    scan = latest[-1]
    try:
        t = buffer.lookup_transform("map", scan.header.frame_id, Time.from_msg(scan.header.stamp))
    except TransformException:
        continue
    latest.clear()
    q = t.transform.rotation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    for i, d in enumerate(scan.ranges):
        if not math.isfinite(d) or not scan.range_min < d < scan.range_max:
            continue
        a = yaw + scan.angle_min + i * scan.angle_increment
        x = t.transform.translation.x + d * math.cos(a)
        y = t.transform.translation.y + d * math.sin(a)
        try:
            c, r = m.cell(x, y)
        except MapError:
            outside += 1
            continue
        errors.append(float(distance[r, c]))
    count += 1
result = dict(
    scan_topic="/scan",
    scan_frame=scan.header.frame_id if count else None,
    scan_count=count,
    endpoint_count=len(errors),
    outside_map_endpoints=outside,
    method="TF at scan timestamp; endpoint distance to nearest occupied cell; model-derived map",
    quantiles_m={str(q): float(np.quantile(errors, q)) for q in [0.5, 0.9, 0.95, 0.99]}
    if errors
    else {},
)
# Explicit measurement criterion, not proof of every possible scan or pose.
result["criterion"] = "10 scans, median<=0.15m and p95<=0.40m"
result["passed"] = bool(
    count == 10 and errors and np.quantile(errors, 0.5) <= 0.15 and np.quantile(errors, 0.95) <= 0.4
)
Path(args.output).write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
node.destroy_node()
rclpy.shutdown()
raise SystemExit(0 if result["passed"] else 1)
