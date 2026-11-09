#!/usr/bin/env python3
"""Record actual Gazebo pixels + live ROS telemetry; never fabricate navigation results."""

import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import textwrap
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.time import Time
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener, TransformException
from PIL import Image, ImageDraw, ImageFont
from tb4_voice_navigation.semantic_map import SemanticMap

ROOT = Path(__file__).resolve().parents[1]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAMES = {
    "A": "UAV / X500",
    "B": "Tay máy / UR5e + UR3e",
    "C": "Sảnh / PAIRS + ĐHQGHN",
    "D": "HRI / Unitree G1",
    "E": "Chó robot / Unitree Go2",
    "F": "TurtleBot / SLAM + Nav2",
}
VIEW = {"A": "uav", "B": "manipulation", "C": "branding", "D": "hri", "E": "go2", "F": "turtlebot"}


def find_window(title="Gazebo Sim", wm_class="gz-sim-gui"):
    output = subprocess.check_output(["xwininfo", "-root", "-tree"], text=True)
    for line in output.splitlines():
        if title in line and '"' + wm_class + '"' in line:
            return re.search(r"0x[0-9a-f]+", line).group()
    raise RuntimeError("Không tìm thấy cửa sổ " + title)


def arrange_window(wid, x=20, y=65, width=1100, height=800):
    lib = ctypes.CDLL("libX11.so.6")
    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XMoveResizeWindow.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    lib.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = lib.XOpenDisplay(None)
    if not display:
        raise RuntimeError("X11 display is not available")
    try:
        lib.XMoveResizeWindow(display, int(wid, 16), x, y, width, height)
        lib.XRaiseWindow(display, int(wid, 16))
        lib.XSync(display, 0)
    finally:
        lib.XCloseDisplay(display)


class Director(Node):
    def __init__(self, session, mode):
        super().__init__("pairslab_film_director")
        self.set_parameters([rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.session = session
        self.session.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.begin = time.time()
        self.nav_events = []
        self.parsed_events = []
        self.asr_events = []
        self.visited = []
        self.nav_state = {}
        self.asr_state = {}
        self.transcript = ""
        self.pose_value = None
        self.trail = []
        self.headline = "PAIRS ROBOTICS RESEARCH LAB"
        self.detail = "Quay trực tiếp trong Gazebo Harmonic"
        self.proc = None
        self.closed = False
        self.media = {}
        self.last_hud_error = ""
        self.hud_lock = threading.Lock()
        self.hud_rgb = None
        self.hud_stream_stop = threading.Event()
        self.semantic = SemanticMap(ROOT / "src/tb4_voice_navigation/config/pairs_regions.yaml")
        qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(
            String, "/voice/navigation_status", lambda m: self.receive("navigation", m), qos
        )
        self.create_subscription(String, "/voice/asr_status", lambda m: self.receive("asr", m), qos)
        self.create_subscription(
            String, "/voice/parsed_command", lambda m: self.receive("parsed", m), 10
        )
        self.text_pub = self.create_publisher(String, "/voice/transcript", 10)
        self.buffer = Buffer()
        self.tf_listener = TransformListener(self.buffer, self)
        self.hud_timer = self.create_timer(0.5, self.update_hud)
        self.wid = find_window()
        arrange_window(self.wid)
        self.map_base = self.make_map()
        self.update_hud()

    def receive(self, topic, msg):
        try:
            data = json.loads(msg.data)
        except ValueError:
            return
        now = time.time()
        with (self.session / "ros_events.jsonl").open("a", encoding="utf8") as f:
            f.write(
                json.dumps(dict(received_wall_time=now, topic=topic, data=data), ensure_ascii=False)
                + "\n"
            )
        if topic == "navigation":
            self.nav_events.append(data)
            self.nav_state = data
            if data.get("wall_time", 0) >= self.begin and data.get("event") == "WAYPOINT_SUCCEEDED":
                key = data.get("current_target")
                if key and key not in self.visited:
                    self.visited.append(key)
        elif topic == "parsed":
            self.parsed_events.append(data)
        else:
            self.asr_events.append(data)
            self.asr_state = data
            if data.get("wall_time", 0) >= self.begin and data.get("event") == "TRANSCRIPT":
                self.transcript = data["message"]

    def make_map(self):
        import numpy as np
        from PIL import ImageColor

        m = self.semantic.map
        rgb = np.full((m.height, m.width, 3), 247, np.uint8)
        rgb[m.unknown] = (218, 226, 234)
        rgb[m.occupied] = (34, 49, 66)
        for region in self.semantic.regions.values():
            color = ImageColor.getrgb(region.get("display_color", "#8297a8"))
            mask = region["mask"] & m.free
            rgb[mask] = tuple(round(0.17 * c + 0.83 * 247) for c in color)
        return Image.fromarray(rgb).resize((590, 427), Image.Resampling.NEAREST)

    def update_hud(self):
        try:
            with self.hud_lock:
                self.render_hud()
        except Exception as exc:
            if str(exc) != self.last_hud_error:
                self.get_logger().warning("HUD: " + str(exc))
                self.last_hud_error = str(exc)

    def render_hud(self):
        try:
            t = self.buffer.lookup_transform("map", "base_link", Time())
            p = t.transform.translation
            q = t.transform.rotation
            age = abs((self.get_clock().now() - Time.from_msg(t.header.stamp)).nanoseconds / 1e9)
            if age <= 3:
                yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
                self.pose_value = (p.x, p.y, yaw)
                if (
                    not self.trail
                    or math.hypot(self.trail[-1][0] - p.x, self.trail[-1][1] - p.y) > 0.08
                ):
                    self.trail.append((p.x, p.y))
        except TransformException:
            pass
        canvas = Image.new("RGB", (640, 1080), "#102133")
        draw = ImageDraw.Draw(canvas)

        def put(x, y, text, size=24, color="#e6edf5", bold=False):
            draw.text(
                (x, y), str(text), font=ImageFont.truetype(BOLD if bold else FONT, size), fill=color
            )

        def lines(x, y, text, width=40, size=22, color="#d2e0ed"):
            for line in textwrap.wrap(str(text), width)[:4]:
                put(x, y, line, size, color)
                y += size + 8
            return y

        put(25, 20, "PAIRS LAB  /  BÀI THỰC HÀNH 7", 25, "#5bd3d9", True)
        lines(25, 65, self.headline, 34, 27, "#ffffff")
        source = {
            "voice": "MICROPHONE THẬT → ASR → NAV2",
            "tour": "LỆNH VĂN BẢN THAM QUAN → NAV2",
            "broll": "GIỚI THIỆU MÔI TRƯỜNG GAZEBO",
        }[self.mode]
        lines(25, 143, source, 45, 20, "#f5bd69")
        canvas.paste(self.map_base, (25, 220))
        draw = ImageDraw.Draw(canvas)
        m = self.semantic.map

        def pixel(x, y):
            c, r = m.to_pixel(x, y)
            return (25 + c / m.width * 590, 220 + r / m.height * 427)

        if len(self.trail) > 1:
            draw.line([pixel(x, y) for x, y in self.trail[-1000:]], fill="#0c97ad", width=3)
        for key, region in self.semantic.regions.items():
            g = region["goal"]
            x, y = pixel(g["x"], g["y"])
            color = (
                "#27a36e"
                if key in self.visited
                else "#f69d30"
                if key == self.nav_state.get("current_target") and self.nav_state.get("busy")
                else "#516c85"
            )
            draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=color, outline="white", width=2)
            draw.text((x - 5, y - 8), key, font=ImageFont.truetype(BOLD, 13), fill="white")
        if self.pose_value:
            x, y, yaw = self.pose_value
            x, y = pixel(x, y)
            polygon = [
                (x + 12 * math.cos(a), y - 12 * math.sin(a)) for a in [yaw, yaw + 2.5, yaw - 2.5]
            ]
            draw.polygon(polygon, fill="#e62f43", outline="white")
        put(25, 662, "TF MAP: robot đỏ | vệt đi thực: xanh", 19, "#a9bfce")
        state = self.nav_state.get("state", "CHỜ") if self.mode != "broll" else "GIỚI THIỆU SCENE"
        put(
            25,
            700,
            "TRẠNG THÁI: " + state,
            23,
            "#7bdfae" if state == "SUCCEEDED" else "#ffffff",
            True,
        )
        target = self.nav_state.get("current_target")
        lines(
            25, 741, ("Đích: " + NAMES.get(target, str(target))) if target else self.detail, 42, 22
        )
        if self.mode == "voice":
            put(25, 815, "TRANSCRIPT ASR THẬT", 20, "#5bd3d9", True)
            lines(25, 848, self.transcript or "Chờ người dùng nhấn Enter và nói...", 41, 22)
        else:
            put(25, 815, "ĐÃ CÓ RESULT SUCCEEDED:", 20, "#5bd3d9", True)
            put(25, 850, " → ".join(self.visited) or "Chưa có waypoint trong phần quay này", 22)
        if self.pose_value:
            put(
                25,
                957,
                f"Pose thật: ({self.pose_value[0]:.2f}, {self.pose_value[1]:.2f}) m",
                20,
                "#a9bfce",
            )
        put(25, 1000, time.strftime("%d/%m/%Y  %H:%M:%S"), 19, "#91a8bc")
        put(25, 1033, "Model trưng bày tĩnh; TB4 điều hướng thật", 16, "#91a8bc")
        self.hud_rgb = canvas.tobytes()
        tmp = self.session / "hud.tmp.png"
        canvas.save(tmp)
        os.replace(tmp, self.session / "hud.png")

    def wait(self, predicate, seconds=30):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate():
                return
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError("Recorder stopped unexpectedly")
            time.sleep(0.1)
        raise TimeoutError("Chưa có kết quả trong thời hạn")

    def camera(self, view):
        subprocess.run(
            [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/pairslab_camera.py"), view],
            check=True,
            stdout=subprocess.DEVNULL,
            timeout=8,
        )

    def start_video(self, name):
        self.update_hud()
        target = self.session / (name + ".mp4")
        log = open(self.session / (name + "_ffmpeg.log"), "w")
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-f",
            "x11grab",
            "-framerate",
            "15",
            "-window_id",
            self.wid,
            "-i",
            os.environ.get("DISPLAY", ":1"),
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "640x1080",
            "-framerate",
            "2",
            "-i",
            str(self.session / "hud.fifo"),
            "-filter_complex_threads",
            "2",
            "-filter_complex",
            "[0:v]scale=1280:930:force_original_aspect_ratio=decrease,pad=1280:1080:(ow-iw)/2:(oh-ih)/2:color=0x102133[scene];[scene][1:v]hstack=inputs=2,format=yuv420p[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-r",
            "15",
            "-threads",
            "2",
            "-movflags",
            "+faststart",
            str(target),
        ]
        fifo = self.session / "hud.fifo"
        if fifo.exists():
            fifo.unlink()
        os.mkfifo(fifo)
        self.hud_stream_stop.clear()
        start = time.time()
        self.proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log, text=True
        )

        def stream_hud():
            try:
                with open(fifo, "wb") as pipe:
                    deadline = time.monotonic()
                    while not self.hud_stream_stop.is_set():
                        pipe.write(self.hud_rgb)
                        pipe.flush()
                        deadline += 0.5
                        time.sleep(max(0, deadline - time.monotonic()))
            except (BrokenPipeError, OSError):
                pass

        self.hud_writer = threading.Thread(target=stream_hud, daemon=True)
        self.hud_writer.start()
        self.media = dict(
            path=str(target.relative_to(ROOT)),
            capture_requested_wall_time=start,
            mode=self.mode,
            input_source="microphone"
            if self.mode == "voice"
            else "keyboard transcript"
            if self.mode == "tour"
            else "no navigation command",
        )
        self.log_file = log
        time.sleep(2)
        if self.proc.poll() is not None:
            raise RuntimeError("FFmpeg failed: " + str(log.name))
        self.media["capture_confirmed_wall_time"] = time.time()
        print("RECORDING", target, flush=True)

    def stop_video(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.stdin.write("q\n")
            self.proc.stdin.flush()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        self.hud_stream_stop.set()
        self.hud_writer.join(timeout=2)
        self.log_file.close()
        self.media["capture_stopped_wall_time"] = time.time()
        self.media["ffmpeg_exit_code"] = self.proc.returncode
        if self.proc.returncode:
            raise RuntimeError("FFmpeg recorder failed")
        path = ROOT / self.media["path"]
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration:stream=width,height,codec_name",
                    "-of",
                    "json",
                    str(path),
                ],
                text=True,
            )
        )
        self.media["probe"] = probe
        path.with_suffix(".json").write_text(json.dumps(self.media, indent=2, ensure_ascii=False))
        self.proc = None
        print("SAVED", path, flush=True)

    def snapshot(self, name):
        folder = self.session / "stills"
        folder.mkdir(exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "x11grab",
                "-window_id",
                self.wid,
                "-i",
                os.environ.get("DISPLAY", ":1"),
                "-frames:v",
                "1",
                str(folder / (name + ".png")),
            ],
            check=True,
            timeout=8,
        )

    def run_broll(self):
        self.camera("branding")
        time.sleep(1)
        self.start_video("01_environment_master")
        for view, title in [
            ("branding", "NHẬN DIỆN PAIRS LAB + ĐHQGHN"),
            ("overview", "TỔNG QUAN 5 PHÒNG NGHIÊN CỨU"),
            ("uav", "UAV / X500 + LỒNG THỬ BAY"),
            ("manipulation", "TAY MÁY / UR5e + UR3e"),
            ("hri", "HRI / UNITREE G1"),
            ("go2", "LEGGED ROBOTICS / UNITREE GO2"),
            ("turtlebot", "MOBILE ROBOTICS / TURTLEBOT 4"),
        ]:
            self.headline = title
            self.camera(view)
            time.sleep(2)
            self.snapshot("environment_" + view)
            time.sleep(6)
        self.camera("overview")
        time.sleep(3)
        self.stop_video()

    def run_voice(self):
        self.wait(lambda: self.nav_state and self.asr_state.get("ready"), 30)
        if self.nav_state.get("busy"):
            raise RuntimeError("Robot đang bận")
        self.headline = "T15 / NÓI: ĐI ĐẾN PHÒNG UAV"
        self.detail = "Chờ thao tác push-to-talk của người dùng"
        self.camera("overview")
        time.sleep(1)
        self.start_video("02_voice_master_silent")
        voice_folder = self.session / "voice"
        voice_folder.mkdir(exist_ok=True)
        (voice_folder / "recording_ready.json").write_text(json.dumps(self.media, indent=2))
        results = voice_folder / "results.json"
        self.wait(
            lambda: results.exists()
            and any(
                r.get("passed") and r.get("expected_waypoints") == ["A"]
                for r in json.loads(results.read_text())
            ),
            900,
        )
        rows = json.loads(results.read_text())
        success = next(r for r in reversed(rows) if r.get("passed"))
        assert success["started_wall_time"] >= self.media["capture_requested_wall_time"]
        identity = success["parsed"]["command_id"]
        assert any(
            r.get("command_id") == identity and r.get("state") == "SUCCEEDED"
            for r in self.nav_events
        )
        t = self.buffer.lookup_transform("map", "base_link", Time())
        pos = t.transform.translation
        col, row = self.semantic.map.cell(pos.x, pos.y)
        assert self.semantic.lookup("A")["mask"][row, col]
        arrival = dict(x=pos.x, y=pos.y, z=pos.z, inside_region=True)
        self.headline = "PHÒNG UAV / NAV2 SUCCEEDED"
        self.camera("uav")
        time.sleep(2)
        self.snapshot("voice_UAV_arrival")
        time.sleep(7)
        self.stop_video()
        (voice_folder / "filmed_acceptance.json").write_text(
            json.dumps(
                dict(
                    passed=True,
                    input="real microphone during this video recording",
                    command_id=identity,
                    result=success,
                    arrival_pose=arrival,
                    video=self.media,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )

    def run_tour(self, resume=False):
        self.wait(lambda: self.nav_state and self.text_pub.get_subscription_count() > 0, 20)
        time.sleep(2)  # Drain transient-local status history before checking the latest state.
        if self.nav_state.get("busy"):
            raise RuntimeError("Robot đang bận")
        previous = self.session / "voice/filmed_acceptance.json"
        voice_verified = previous.exists() and json.loads(previous.read_text()).get("passed")
        route = (
            ["E", "C"]
            if resume
            else ["B", "D", "C", "F", "C", "E", "C"]
            if voice_verified
            else ["A", "B", "D", "C", "F", "C", "E", "C"]
        )
        voice_seed_pose = None
        if voice_verified and not resume:
            self.wait(lambda: self.pose_value is not None, 15)
            x, y, yaw = self.pose_value
            col, row = self.semantic.map.cell(x, y)
            assert self.semantic.lookup("A")["mask"][row, col], (
                "Robot must still be in A after the filmed voice trial"
            )
            voice_seed_pose = dict(
                region="A",
                x=x,
                y=y,
                yaw=yaw,
                inside_region=True,
                measured_wall_time=time.time(),
                source="measured at tour start after filmed voice mission",
            )
            self.visited = ["A"]
        results = []
        if resume:
            prior = json.loads((self.session / "navigation_results.json").read_text())
            assert prior[-1]["terminal"]["event"] == "LOCALIZATION_LOST"
            results = [r for r in prior if r["terminal"]["state"] == "SUCCEEDED"]
            assert voice_verified
            self.visited = list(dict.fromkeys(["A"] + [r["region"] for r in results]))
        self.headline = "TIẾP TỤC SAU CẬP NHẬT AMCL" if resume else "THAM QUAN NAV2 / ĐI ĐỦ 5 PHÒNG"
        self.camera("overview")
        self.start_video("04_navigation_resume" if resume else "03_navigation_master")
        phrases = {
            "A": "Đi đến phòng UAV",
            "B": "Đi đến phòng tay máy",
            "D": "Đi đến phòng robot hình người",
            "C": "Đi đến sảnh",
            "F": "Đi đến phòng TurtleBot",
            "E": "Đi đến phòng chó robot",
        }
        for key in route:
            self.headline = "NAV2 → " + NAMES[key]
            self.detail = "Đang đi tới " + key
            self.camera("overview")
            begin = len(self.nav_events)
            parse_begin = len(self.parsed_events)
            self.text_pub.publish(String(data=phrases[key]))
            self.wait(
                lambda: any(
                    p.get("transcript") == phrases[key] for p in self.parsed_events[parse_begin:]
                ),
                15,
            )
            parsed = next(
                p for p in self.parsed_events[parse_begin:] if p.get("transcript") == phrases[key]
            )
            identity = parsed["command_id"]
            assert parsed["waypoints"] == [key]

            def terminal():
                return next(
                    (
                        r
                        for r in reversed(self.nav_events[begin:])
                        if r.get("command_id") == identity
                        and not r.get("busy")
                        and r.get("state") in ["SUCCEEDED", "FAILED", "CANCELED"]
                    ),
                    None,
                )

            self.wait(lambda: terminal() is not None, 220)
            t = self.buffer.lookup_transform("map", "base_link", Time())
            pos = t.transform.translation
            col, row = self.semantic.map.cell(pos.x, pos.y)
            inside = bool(self.semantic.lookup(key)["mask"][row, col])
            raw = [
                r
                for r in self.nav_events[begin:]
                if r.get("command_id") == identity
                and r.get("event") == "ACTION_TERMINAL"
                and r.get("action_kind") == "nav"
            ]
            item = dict(
                region=key,
                input="keyboard transcript",
                parsed=parsed,
                terminal=terminal(),
                arrival_pose=dict(x=pos.x, y=pos.y, z=pos.z, inside_region=inside),
                action_results=raw,
            )
            results.append(item)
            (
                self.session
                / ("navigation_resume_results.json" if resume else "navigation_results.json")
            ).write_text(json.dumps(results, indent=2, ensure_ascii=False))
            if terminal()["state"] == "SUCCEEDED":
                assert inside, "Robot pose is outside the required semantic region"
                assert any(r.get("action_status") == 4 and r.get("error_code") == 0 for r in raw)
            if terminal()["state"] != "SUCCEEDED":
                raise RuntimeError("Dừng tour vì waypoint thất bại: " + str(terminal()))
            self.headline = NAMES[key] + " / SUCCEEDED"
            self.camera(VIEW[key])
            time.sleep(2)
            self.snapshot("arrival_" + key)
            time.sleep(6)
        assert set("ABDEF") <= set(self.visited)
        self.headline = "ĐÃ ĐẾN ĐỦ 5 PHÒNG / KẾT THÚC Ở SẢNH"
        self.camera("overview")
        time.sleep(7)
        self.snapshot("tour_complete")
        self.stop_video()
        (self.session / "coverage.json").write_text(
            json.dumps(
                dict(
                    passed=True,
                    resumed_after_localization_loss=resume,
                    visited=self.visited,
                    voice_seed_pose=voice_seed_pose,
                    research_rooms=["A", "B", "D", "E", "F"],
                    route=route,
                    source="A from filmed voice trial; subsequent goals from explicitly-labelled keyboard tour"
                    if voice_verified
                    else "keyboard tour",
                    results=results,
                    video=self.media,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["broll", "voice", "tour"])
    p.add_argument("--session", default="deliverables/pairslab_demo_20261109")
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = Director((ROOT / a.session).resolve(), a.mode)

    def spin():
        try:
            rclpy.spin(node)
        except Exception:
            if not node.closed:
                raise

    worker = threading.Thread(target=spin, daemon=True)
    worker.start()
    try:
        if a.mode == "broll":
            node.run_broll()
        elif a.mode == "voice":
            node.run_voice()
        else:
            node.run_tour(resume=a.resume)
    finally:
        if node.proc is not None:
            node.stop_video()
        node.closed = True
        rclpy.try_shutdown()
        worker.join(timeout=2)
        node.destroy_node()


if __name__ == "__main__":
    main()
