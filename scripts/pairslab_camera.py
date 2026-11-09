#!/usr/bin/env python3
"""Move only the Gazebo GUI camera; does not move robot or change simulation state."""

import argparse
import math
import subprocess
from scipy.spatial.transform import Rotation

VIEWS = {
    "overview": ((14, -19, 22), (0, 0, 0.2)),
    "uav": ((-4.7, 1.9, 7.0), (-9.5, 6.8, 1.0)),
    "manipulation": ((4.1, 2.7, 5.4), (0, 6.7, 0.9)),
    "hri": ((11.6, 3.1, 3.0), (8.6, 6.6, 0.95)),
    "go2": ((-4.5, -3.4, 3.5), (-8.0, -6.2, 0.55)),
    "turtlebot": ((11, -3.1, 3.7), (6.7, -6.8, 0.5)),
    "branding": ((4.7, -3.1, 2.1), (4.0, 1.8, 1.25)),
}
p = argparse.ArgumentParser()
p.add_argument("view", choices=VIEWS)
a = p.parse_args()
eye, target = VIEWS[a.view]
dx, dy, dz = [t - e for e, t in zip(eye, target)]
yaw = math.atan2(dy, dx)
pitch = math.atan2(-dz, math.hypot(dx, dy))
q = Rotation.from_euler("xyz", [0, pitch, yaw]).as_quat()
request = "pose: {position: {x: %g, y: %g, z: %g}, orientation: {x: %g, y: %g, z: %g, w: %g}}" % (
    *eye,
    *q,
)
result = subprocess.run(
    [
        "gz",
        "service",
        "-s",
        "/gui/move_to/pose",
        "--reqtype",
        "gz.msgs.GUICamera",
        "--reptype",
        "gz.msgs.Boolean",
        "--timeout",
        "3000",
        "--req",
        request,
    ],
    capture_output=True,
    text=True,
)
print(result.stdout, result.stderr)
if "data: true" not in result.stdout:
    raise SystemExit("Gazebo GUI camera is not ready")
