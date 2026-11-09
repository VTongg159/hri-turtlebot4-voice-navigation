"""Terminal push-to-talk client for the live microphone node."""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


def main(args=None):
    rclpy.init(args=args)
    node = Node("push_to_talk")
    start = node.create_client(Trigger, "/voice/record/start")
    stop = node.create_client(Trigger, "/voice/record/stop")

    def call(client):
        if not client.wait_for_service(timeout_sec=3):
            print("ASR service chưa có")
            return False
        future = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(node, future, timeout_sec=5)
        if not future.done():
            print("Service timeout")
            return False
        response = future.result()
        print(response.message)
        return response.success

    try:
        while rclpy.ok():
            input("Enter để bắt đầu ghi (Ctrl+D thoát): ")
            if call(start):
                input("Hãy nói; Enter để dừng: ")
                call(stop)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        # Do not leave a recorder running after this client exits.
        if rclpy.ok() and stop.service_is_ready():
            call(stop)
        node.destroy_node()
        rclpy.try_shutdown()
