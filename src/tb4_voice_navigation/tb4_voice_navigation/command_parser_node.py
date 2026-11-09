"""Transcript → validated grammar JSON; errors never become navigation requests."""

import json
import uuid
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ament_index_python.packages import get_package_share_directory
from .semantic_map import SemanticMap
from .command_parser import CommandParser


class CommandParserNode(Node):
    def __init__(self):
        super().__init__("command_parser_node")
        default = str(
            Path(get_package_share_directory("tb4_voice_navigation")) / "config/pairs_regions.yaml"
        )
        self.declare_parameter("regions_file", default)
        self.parser = CommandParser(SemanticMap(self.get_parameter("regions_file").value).regions)
        self.pub = self.create_publisher(String, "/voice/parsed_command", 10)
        self.sub = self.create_subscription(String, "/voice/transcript", self.on_text, 10)

    def on_text(self, msg):
        result = self.parser.parse_safe(msg.data)
        result.update(command_id=uuid.uuid4().hex, transcript=msg.data)
        encoded = json.dumps(result, ensure_ascii=False)
        self.pub.publish(String(data=encoded))
        self.get_logger().info(encoded)


def main(args=None):
    rclpy.init(args=args)
    node = CommandParserNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
