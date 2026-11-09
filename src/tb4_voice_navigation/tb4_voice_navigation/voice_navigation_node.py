"""Sequential real Nav2 actions with plan checks, TF validation and cancel fencing."""

import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.time import Time
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Path as NavPath
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from std_msgs.msg import String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener, TransformException
from ament_index_python.packages import get_package_share_directory
from .semantic_map import SemanticMap, MapError
from .navigation_policy import validate_request, RequestError, same_goal_id


class VoiceNavigationNode(Node):
    def __init__(self):
        super().__init__("voice_navigation_node")
        defaults = dict(
            regions_file=str(
                Path(get_package_share_directory("tb4_voice_navigation"))
                / "config/pairs_regions.yaml"
            ),
            navigate_action="/navigate_to_pose",
            planner_action="/compute_path_to_pose",
            base_frame="base_link",
            server_timeout=10.0,
            goal_timeout=180.0,
            planning_timeout=15.0,
            cancel_timeout=10.0,
            tf_max_age=2.0,
            source_tolerance=0.30,
            localization_covariance_max=0.5,
            audit_file="",
        )
        for k, v in defaults.items():
            self.declare_parameter(k, v)
        self.p = lambda k: self.get_parameter(k).value
        self.semantic = SemanticMap(self.p("regions_file"))
        self.nav = ActionClient(self, NavigateToPose, self.p("navigate_action"))
        self.planner = ActionClient(self, ComputePathToPose, self.p("planner_action"))
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        qos = QoSProfile(depth=50, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(String, "/voice/navigation_status", qos)
        self.path_pub = self.create_publisher(NavPath, "/voice/planned_path", qos)
        self.sub = self.create_subscription(String, "/voice/parsed_command", self.command, 10)
        self.pose_sub = self.create_subscription(
            PoseWithCovarianceStamped, "/amcl_pose", self.amcl, qos
        )
        self.cancel_service = self.create_service(Trigger, "/voice/cancel", self.cancel_service_cb)
        self.covariance = None
        self.state = "IDLE"
        self.busy = False
        self.goal_handle = None
        self.pending = False
        self.cancel_sent = False
        self.stop_reason = None
        self.command_id = ""
        self.route = []
        self.index = 0
        self.phase_started = time.monotonic()
        self.feedback_at = 0.0
        self.sequence = 0
        self.last_status = {}
        self.cancel_warned = False
        self.timer = self.create_timer(0.1, self.tick)
        self.emit("READY", "Chờ câu lệnh")

    def emit(self, event, message, **extra):
        self.sequence += 1
        data = dict(
            sequence=self.sequence,
            state=self.state,
            event=event,
            message=message,
            command_id=self.command_id,
            waypoints=[r["id"] for r in self.route],
            waypoint_index=self.index,
            current_target=self.route[self.index]["id"]
            if self.busy and self.index < len(self.route)
            else None,
            busy=self.busy,
            wall_time=time.time(),
            **extra,
        )
        self.last_status = data
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
        self.pub.publish(String(data=encoded))
        self.get_logger().info(encoded)
        if self.p("audit_file"):
            try:
                with open(self.p("audit_file"), "a", encoding="utf8") as f:
                    f.write(encoded + "\n")
            except OSError as exc:
                self.get_logger().error(f"Audit: {exc}")

    def amcl(self, msg):
        if msg.header.frame_id == self.semantic.frame:
            self.covariance = msg.pose.covariance

    def current_pose(self):
        if self.covariance is None:
            raise RequestError("Chưa nhận AMCL pose")
        values = [self.covariance[i] for i in (0, 7, 35)]
        if any(
            not math.isfinite(v) or v < 0 or v > self.p("localization_covariance_max")
            for v in values
        ):
            raise RequestError("Localization covariance chưa đủ tốt")
        t = self.tf.lookup_transform(self.semantic.frame, self.p("base_frame"), Time())
        age = (self.get_clock().now() - Time.from_msg(t.header.stamp)).nanoseconds / 1e9
        if abs(age) > self.p("tf_max_age"):
            raise RequestError(f"TF không còn tươi: {age:.2f}s")
        return t.transform.translation

    def command(self, msg):
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                raise RequestError("Expected JSON object")
            if data.get("type") == "cancel":
                self.request_cancel("USER_CANCEL")
                return
            if data.get("type") == "error":
                self.emit("REJECTED", str(data.get("error", {})))
                return
            if self.busy:
                self.emit(
                    "BUSY",
                    "Robot đang bận; từ chối lệnh mới",
                    rejected_command_id=str(data.get("command_id", "")),
                )
                return
            regions = validate_request(data, self.semantic)
            self.command_id = str(data.get("command_id", ""))
            self.route = regions
            self.index = 0
            self.busy = True
            self.state = "VALIDATING"
            self.source_command = (
                data.get("starts_from_source", data["type"] == "source_destination") is True
            )
            self.phase_started = time.monotonic()
            self.stop_reason = None
            self.cancel_warned = False
            self.emit("ACCEPTED", "Đã kiểm tra semantic metadata; chờ Nav2 và localization")
        except (ValueError, TypeError, KeyError, MapError, RequestError) as exc:
            self.emit("REJECTED", str(exc))

    def cancel_service_cb(self, request, response):
        response.success = self.busy
        response.message = (
            "Đã yêu cầu hủy; chờ terminal action result"
            if self.busy
            else "Không có nhiệm vụ đang chạy"
        )
        self.request_cancel("USER_CANCEL")
        return response

    def request_cancel(self, reason):
        if not self.busy:
            self.emit("NOT_BUSY", "Không có nhiệm vụ để hủy")
            return
        if not self.stop_reason:
            self.stop_reason = reason
            self.state = "CANCELING"
            self.phase_started = time.monotonic()
            self.emit(reason, "Đang hủy; giữ khóa busy tới khi action kết thúc")
        if self.goal_handle is not None and not self.cancel_sent:
            self.cancel_sent = True
            self.goal_handle.cancel_goal_async().add_done_callback(self.cancel_reply)
        elif not self.pending and self.goal_handle is None:
            self.finish_stop()

    def cancel_reply(self, future):
        try:
            response = future.result()
            if not response.goals_canceling:
                self.emit(
                    "CANCEL_NOT_ACCEPTED", "Server chưa xác nhận hủy; tiếp tục chờ action result"
                )
        except Exception as exc:
            self.emit("CANCEL_ERROR", str(exc))

    def finish_stop(self):
        reason = self.stop_reason or "FAILED"
        self.finish("CANCELED" if reason == "USER_CANCEL" else "FAILED", reason)

    def finish(self, state, reason):
        self.busy = False
        self.state = state
        self.pending = False
        self.goal_handle = None
        self.cancel_sent = False
        self.emit(reason, "Nhiệm vụ kết thúc")
        self.stop_reason = None

    def tick(self):
        if not self.busy:
            return
        elapsed = time.monotonic() - self.phase_started
        if self.state == "CANCELING":
            if elapsed > self.p("cancel_timeout") and not self.cancel_warned:
                self.cancel_warned = True
                self.emit(
                    "CANCEL_UNCONFIRMED",
                    "Chưa có terminal result; tiếp tục khóa lệnh mới để tránh goal đồng thời",
                )
            return
        if self.state == "VALIDATING":
            try:
                position = self.current_pose()
            except (TransformException, RequestError) as exc:
                if elapsed > self.p("server_timeout"):
                    self.finish("FAILED", f"LOCALIZATION_NOT_READY: {exc}")
                return
            if not (self.nav.server_is_ready() and self.planner.server_is_ready()):
                if elapsed > self.p("server_timeout"):
                    self.finish("FAILED", "NAV2_NOT_READY")
                return
            if self.index == 0 and self.source_command:
                g = self.route[0]["goal"]
                if math.hypot(position.x - g["x"], position.y - g["y"]) <= self.p(
                    "source_tolerance"
                ):
                    self.emit("SOURCE_ALREADY_REACHED", "Bỏ qua điểm nguồn trong sai số cho phép")
                    self.index += 1
            if self.index >= len(self.route):
                self.finish("SUCCEEDED", "ALL_WAYPOINTS_REACHED")
                return
            self.start_plan()
        elif self.state == "PLANNING" and elapsed > self.p("planning_timeout"):
            self.request_cancel("PLANNING_TIMEOUT")
        elif self.state == "NAVIGATING":
            if elapsed > self.p("goal_timeout"):
                self.request_cancel("GOAL_TIMEOUT")
                return
            try:
                self.current_pose()
            except (TransformException, RequestError):
                self.request_cancel("LOCALIZATION_LOST")

    def goal_pose(self):
        region = self.semantic.lookup(self.route[self.index]["id"])
        self.semantic.validate_goal(region, region["goal"])
        g = region["goal"]
        pose = PoseStamped()
        pose.header.frame_id = self.semantic.frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(g["x"])
        pose.pose.position.y = float(g["y"])
        pose.pose.orientation.z = math.sin(g["yaw"] / 2)
        pose.pose.orientation.w = math.cos(g["yaw"] / 2)
        return pose

    def start_plan(self):
        self.state = "PLANNING"
        self.phase_started = time.monotonic()
        try:
            request = ComputePathToPose.Goal()
            request.goal = self.goal_pose()
            request.use_start = False
            self.pending = True
            self.emit("CHECKING_PATH", "Kiểm tra đường đi bằng Nav2 planner")
            self.planner.send_goal_async(request).add_done_callback(
                lambda f: self.accepted(f, "plan")
            )
        except Exception as exc:
            self.pending = False
            self.finish("FAILED", f"PLAN_SEND_ERROR: {exc}")

    def accepted(self, future, kind):
        self.pending = False
        try:
            handle = future.result()
        except Exception as exc:
            # Transport outcome may be uncertain: retain the fence rather than send another goal.
            self.pending = True
            self.request_cancel(f"ACTION_TRANSPORT_UNCERTAIN: {exc}")
            return
        if not handle.accepted:
            if self.stop_reason:
                self.finish_stop()
            else:
                self.finish("FAILED", f"{kind.upper()}_REJECTED")
            return
        self.goal_handle = handle
        self.cancel_sent = False
        handle.get_result_async().add_done_callback(lambda f: self.result(f, kind))
        if self.stop_reason:
            self.request_cancel(self.stop_reason)
        else:
            self.emit("PLAN_ACCEPTED" if kind == "plan" else "GOAL_ACCEPTED", "Nav2 đã nhận goal")

    def result(self, future, kind):
        try:
            wrapped = future.result()
        except Exception as exc:
            self.request_cancel(f"ACTION_RESULT_UNCERTAIN: {exc}")
            return
        self.goal_handle = None
        self.cancel_sent = False
        self.emit(
            "ACTION_TERMINAL",
            "Đã nhận terminal result thật",
            action_kind=kind,
            action_status=int(wrapped.status),
            error_code=int(getattr(wrapped.result, "error_code", 0)),
        )
        if self.stop_reason:
            self.finish_stop()
            return
        result = wrapped.result
        code = getattr(result, "error_code", 0)
        if wrapped.status != GoalStatus.STATUS_SUCCEEDED or code != 0:
            self.finish(
                "FAILED",
                f"{kind.upper()}_FAILED status={wrapped.status} error={code} {getattr(result, 'error_msg', '')}",
            )
            return
        if kind == "plan":
            if not result.path.poses:
                self.finish("FAILED", "EMPTY_PATH")
                return
            self.path_pub.publish(result.path)
            try:
                self.current_pose()
                request = NavigateToPose.Goal()
                request.pose = self.goal_pose()
                self.state = "NAVIGATING"
                self.phase_started = time.monotonic()
                self.pending = True
                self.emit("NAVIGATING", "Đang đi tới khu vực")
                self.nav.send_goal_async(
                    request, feedback_callback=self.feedback
                ).add_done_callback(lambda f: self.accepted(f, "nav"))
            except Exception as exc:
                self.pending = False
                self.finish("FAILED", f"NAV_SEND_ERROR: {exc}")
        else:
            self.emit("WAYPOINT_SUCCEEDED", "Nav2 xác nhận waypoint thành công")
            self.index += 1
            if self.index == len(self.route):
                self.finish("SUCCEEDED", "ALL_WAYPOINTS_REACHED")
            else:
                self.state = "VALIDATING"
                self.phase_started = time.monotonic()

    def feedback(self, msg):
        if not self.busy or self.state != "NAVIGATING" or self.goal_handle is None:
            return
        if not same_goal_id(msg.goal_id, self.goal_handle.goal_id):
            return
        if time.monotonic() - self.feedback_at < 2:
            return
        self.feedback_at = time.monotonic()
        f = msg.feedback
        remaining = float(f.distance_remaining)
        if math.isfinite(remaining):
            self.emit(
                "FEEDBACK",
                "Phản hồi Nav2",
                distance_remaining=remaining,
                recoveries=int(f.number_of_recoveries),
            )


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = VoiceNavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node.busy:
            node.request_cancel("USER_CANCEL")
        end = time.monotonic() + 5
        while node.busy and time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
    except Exception:
        if node.busy:
            node.request_cancel("CONTROLLER_ERROR")
            end = time.monotonic() + 5
            while node.busy and time.monotonic() < end and rclpy.ok():
                try:
                    rclpy.spin_once(node, timeout_sec=0.1)
                except Exception:
                    break
        raise
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
