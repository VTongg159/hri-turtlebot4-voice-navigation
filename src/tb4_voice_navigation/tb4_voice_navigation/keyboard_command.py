"""Keyboard is a parser/controller test input, not a speech demonstration."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main(args=None):
    rclpy.init(args=args)
    node = Node("keyboard_command")
    pub = node.create_publisher(String, "/voice/transcript", 10)
    print("Keyboard test input. Type a command; Ctrl+D exits. Example: Đi từ A qua C đến B")
    try:
        while rclpy.ok():
            text = input("> ").strip()
            if text:
                pub.publish(String(data=text))
                rclpy.spin_once(node, timeout_sec=0.1)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
