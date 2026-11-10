"""Semantic polygons and goals in map metres, plus active target/status."""

import json
import math
import unicodedata
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Point
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from ament_index_python.packages import get_package_share_directory
from .semantic_map import SemanticMap

COLORS = [
    (0.23, 0.51, 0.96),
    (0.08, 0.72, 0.65),
    (0.58, 0.64, 0.72),
    (0.96, 0.62, 0.04),
    (0.65, 0.55, 0.98),
]


class RegionVisualizationNode(Node):
    def __init__(self):
        super().__init__("region_visualization_node")
        self.declare_parameter(
            "regions_file",
            str(
                Path(get_package_share_directory("tb4_voice_navigation"))
                / "config/pairs_regions.yaml"
            ),
        )
        self.semantic = SemanticMap(self.get_parameter("regions_file").value)
        self.status = {}
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(MarkerArray, "/semantic_regions/markers", qos)
        self.sub = self.create_subscription(String, "/voice/navigation_status", self.update, qos)
        self.timer = self.create_timer(1.0, self.publish)
        self.publish()

    def update(self, msg):
        try:
            self.status = json.loads(msg.data)
            self.publish()
        except (ValueError, TypeError):
            self.get_logger().warning("Invalid navigation status")

    def marker(self, ns, index, kind, rgb):
        marker = Marker()
        marker.header.frame_id = self.semantic.frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = ns
        marker.id = index
        marker.type = kind
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.color.r, marker.color.g, marker.color.b = rgb
        marker.color.a = 1.0
        return marker

    def publish(self):
        result = MarkerArray()
        clear = Marker()
        clear.action = Marker.DELETEALL
        result.markers.append(clear)
        active = self.status.get("current_target") if self.status.get("busy") else None
        for i, (key, region) in enumerate(self.semantic.regions.items()):
            rgb = COLORS[i % len(COLORS)] if region["valid"] else (0.8, 0.1, 0.1)
            if region["valid"] and "display_color" in region:
                code = region["display_color"].lstrip("#")
                rgb = tuple(int(code[j : j + 2], 16) / 255 for j in (0, 2, 4))
            polygon = self.marker("polygons", i, Marker.LINE_STRIP, rgb)
            polygon.scale.x = 0.035
            vertices = region["polygon_pixels"] + [region["polygon_pixels"][0]]
            for col, row in vertices:
                x, y = self.semantic.map.to_map(col, row)
                polygon.points.append(Point(x=float(x), y=float(y), z=0.03))
            result.markers.append(polygon)
            if not region["valid"]:
                continue
            g = region["goal"]
            arrow = self.marker(
                "goals", i, Marker.ARROW, (1.0, 0.15, 0.10) if active == key else rgb
            )
            arrow.pose.position = Point(x=float(g["x"]), y=float(g["y"]), z=0.08)
            arrow.pose.orientation.z = math.sin(g["yaw"] / 2)
            arrow.pose.orientation.w = math.cos(g["yaw"] / 2)
            arrow.scale.x = 0.65
            arrow.scale.y = 0.15
            arrow.scale.z = 0.15
            result.markers.append(arrow)
            label = self.marker("labels", i, Marker.TEXT_VIEW_FACING, rgb)
            label.pose.position = Point(x=float(g["x"]), y=float(g["y"]), z=0.65)
            label.scale.z = 0.26
            display = "".join(
                c
                for c in unicodedata.normalize(
                    "NFD", region["name"].replace("đ", "d").replace("Đ", "D")
                )
                if unicodedata.category(c) != "Mn"
            )
            label.text = f"{key} - {display}" + (
                " ← " + self.status.get("state", "") if active == key else ""
            )
            result.markers.append(label)
        route = self.status.get("waypoints", [])
        if len(route) > 1:
            line = self.marker("waypoint_order", 0, Marker.LINE_STRIP, (0.4, 0.4, 0.6))
            line.scale.x = 0.025
            line.color.a = 0.55
            for key in route:
                if key not in self.semantic.regions:
                    continue
                g = self.semantic.regions[key]["goal"]
                line.points.append(Point(x=float(g["x"]), y=float(g["y"]), z=0.045))
            result.markers.append(line)
        if self.status:
            # Show the state actually received from the live controller, including
            # terminal states for which current_target is intentionally empty.
            state = self.status.get("state", "")
            color = (0.25, 0.95, 0.65) if state == "SUCCEEDED" else (1.0, 0.8, 0.25)
            status = self.marker("navigation_status", 0, Marker.TEXT_VIEW_FACING, color)
            status.pose.position = Point(x=0.0, y=11.4, z=0.2)
            status.scale.z = 0.48
            status.text = "Nav2: " + state + " | route: " + " -> ".join(route)
            identity = self.status.get("command_id", "")
            if identity:
                status.text += "\ncommand_id: " + identity
            result.markers.append(status)
        self.pub.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = RegionVisualizationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
