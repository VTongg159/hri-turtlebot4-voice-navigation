#!/usr/bin/env python3
"""Operator-paced microphone trials; never inject expected text as a transcript."""

import argparse
import json
from pathlib import Path
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String
from std_srvs.srv import Trigger

TRIALS = [
    ("Đi đến phòng UAV.", ["A"]),
    ("Đi đến phòng chó robot.", ["E"]),
    ("Đi từ phòng UAV qua hành lang đến phòng robot hình người.", ["A", "C", "D"]),
]
ASR_TERMINAL = {
    "TRANSCRIPT",
    "NO_AUDIO",
    "NO_SPEECH",
    "CLIPPED_AUDIO",
    "ASR_ERROR",
    "AUDIO_DEVICE_ERROR",
}


class LiveTrial(Node):
    def __init__(self, folder):
        super().__init__("live_voice_trial")
        self.folder = folder
        self.display_started_at = time.time()
        self.asr = []
        self.parsed = []
        self.navigation = []
        self.attempts = []
        self.lock = threading.RLock()
        self.closed = False
        qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(String, "/voice/asr_status", lambda m: self.receive("asr", m), qos)
        self.create_subscription(
            String, "/voice/navigation_status", lambda m: self.receive("navigation", m), qos
        )
        self.create_subscription(
            String, "/voice/parsed_command", lambda m: self.receive("parsed", m), 10
        )
        self.service_clients = {
            key: self.create_client(Trigger, path)
            for key, path in {
                "start": "/voice/record/start",
                "stop": "/voice/record/stop",
                "discard": "/voice/record/discard",
                "cancel": "/voice/cancel",
            }.items()
        }

    def receive(self, kind, msg):
        try:
            data = json.loads(msg.data)
        except ValueError:
            return
        with self.lock:
            getattr(self, kind).append(data)
            with (self.folder / "events.jsonl").open("a", encoding="utf8") as f:
                f.write(
                    json.dumps(
                        dict(received_wall_time=time.time(), topic=kind, data=data),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        if data.get("wall_time", time.time()) < self.display_started_at:
            return  # Store latched history, but only print events from this live session.
        if kind == "asr" and data.get("event") in ASR_TERMINAL:
            print("\nASR:", data.get("event"), data.get("message"), flush=True)
        if kind == "parsed":
            print("\nPARSER JSON:", json.dumps(data, ensure_ascii=False), flush=True)
        if kind == "navigation" and data.get("event") == "ACTION_TERMINAL":
            print("\nNAV2 ACTION:", json.dumps(data, ensure_ascii=False), flush=True)
        if kind == "navigation" and data.get("event") in {
            "WAYPOINT_SUCCEEDED",
            "ALL_WAYPOINTS_REACHED",
            "REJECTED",
            "BUSY",
        }:
            print(
                "\nNAV:",
                data.get("event"),
                data.get("current_target") or "",
                data.get("message", ""),
                flush=True,
            )

    def call(self, key):
        client = self.service_clients[key]
        if not client.wait_for_service(timeout_sec=4):
            raise RuntimeError("Chưa có service: " + key)
        future = client.call_async(Trigger.Request())
        self.wait(lambda: future.done(), 6)
        response = future.result()
        print(response.message, flush=True)
        return response.success

    def wait(self, predicate, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate():
                return
            if not rclpy.ok():
                raise RuntimeError("ROS đã dừng")
            time.sleep(0.05)
        raise TimeoutError("Hết thời gian chờ kết quả; xem log trong " + str(self.folder))

    def run(self):
        print(f"\nPAIRS LAB — THỬ {len(TRIALS)} CÂU TIẾNG VIỆT TỪ MICROPHONE THẬT\n", flush=True)
        print("Đang chờ Whisper, parser và controller sẵn sàng...", flush=True)
        self.wait(lambda: self.asr and self.asr[-1].get("ready") and self.navigation, 300)
        if self.navigation[-1].get("busy"):
            self.wait(lambda: not self.navigation[-1].get("busy"), 200)
        print("SẴN SÀNG. Nhấn Enter bắt đầu; nói câu trên màn hình; Enter dừng.", flush=True)
        print("Mỗi đoạn tự dừng sau 12 giây. Ctrl+C để kết thúc và yêu cầu hủy.\n", flush=True)
        for number, (sentence, expected) in enumerate(TRIALS, 1):
            while True:
                print("\n" + "=" * 74, flush=True)
                print(
                    f"CÂU {number}/{len(TRIALS)}:  {sentence}\nLộ trình mong đợi: "
                    + " → ".join(expected),
                    flush=True,
                )
                choice = input("Enter để BẮT ĐẦU GHI (q: kết thúc): ").strip().lower()
                if choice == "q":
                    return
                started = time.time()
                asr_index = len(self.asr)
                parsed_index = len(self.parsed)
                nav_index = len(self.navigation)
                result = dict(
                    trial=number,
                    expected_sentence=sentence,
                    expected_waypoints=expected,
                    started_wall_time=started,
                    input_source="real microphone",
                    passed=False,
                )
                try:
                    if not self.call("start"):
                        continue
                    input("ĐANG GHI — Hãy nói ngay. Nói xong nhấn Enter: ")
                    self.call("stop")
                    print("Đang nhận dạng, vui lòng đợi...", flush=True)
                    self.wait(
                        lambda: any(
                            v.get("event") in ASR_TERMINAL and v.get("wall_time", 0) >= started
                            for v in self.asr[asr_index:]
                        ),
                        90,
                    )
                    status = next(
                        v
                        for v in self.asr[asr_index:]
                        if v.get("event") in ASR_TERMINAL and v.get("wall_time", 0) >= started
                    )
                    result["asr"] = status
                    if status["event"] != "TRANSCRIPT":
                        raise RuntimeError(status.get("message", "Không có transcript"))
                    transcript = status["message"]
                    result["actual_transcript"] = transcript
                    self.wait(
                        lambda: any(
                            p.get("transcript") == transcript for p in self.parsed[parsed_index:]
                        ),
                        10,
                    )
                    parsed = next(
                        p for p in self.parsed[parsed_index:] if p.get("transcript") == transcript
                    )
                    result["parsed"] = parsed
                    print("ĐÃ NHẬN:", transcript, "\nPARSER:", parsed.get("waypoints"), flush=True)
                    if parsed.get("waypoints") != expected:
                        self.call("cancel")
                        raise RuntimeError(
                            "Kết quả parser khác lộ trình câu thử; đã yêu cầu hủy nếu có goal"
                        )
                    identity = parsed["command_id"]

                    def terminal():
                        return next(
                            (
                                v
                                for v in reversed(self.navigation[nav_index:])
                                if v.get("command_id") == identity
                                and not v.get("busy")
                                and v.get("state") in {"SUCCEEDED", "FAILED", "CANCELED"}
                            ),
                            None,
                        )

                    print(
                        "Robot đang thực hiện lệnh. Chờ hoàn thành trước câu tiếp theo.", flush=True
                    )
                    self.wait(lambda: terminal() is not None, 600)
                    result["navigation_terminal"] = terminal()
                    result["passed"] = terminal()["state"] == "SUCCEEDED"
                    print(
                        "\nKẾT QUẢ:",
                        "PASS — GIỌNG NÓI → ROBOT THÀNH CÔNG"
                        if result["passed"]
                        else "CHƯA ĐẠT — " + terminal().get("event", ""),
                        flush=True,
                    )
                except (RuntimeError, TimeoutError) as exc:
                    result["error"] = str(exc)
                    print("\nCHƯA ĐẠT:", exc, flush=True)
                self.attempts.append(result)
                (self.folder / "results.json").write_text(
                    json.dumps(self.attempts, ensure_ascii=False, indent=2)
                )
                if result["passed"]:
                    break
                choice = input("Enter thử lại câu này; n: bỏ qua; q: kết thúc: ").strip().lower()
                if choice == "q":
                    return
                if choice == "n":
                    break
        print(
            f"\nĐÃ KẾT THÚC {len(TRIALS)} CÂU. Kết quả thật được lưu tại:", self.folder, flush=True
        )
        input("Nhấn Enter để đóng cửa sổ thử: ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence/voice_demo/pairslab_live")
    parser.add_argument("--plan")
    args = parser.parse_args()
    if args.plan:
        global TRIALS
        plan = json.loads(Path(args.plan).read_text())
        if not isinstance(plan, list) or not plan:
            raise ValueError("Plan must be a nonempty list")
        TRIALS = [(r["sentence"], r["waypoints"]) for r in plan]
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = LiveTrial(folder)

    def spin():
        try:
            rclpy.spin(node)
        except Exception:
            if not node.closed:
                raise

    worker = threading.Thread(target=spin, daemon=True)
    worker.start()
    try:
        node.run()
    except (KeyboardInterrupt, EOFError):
        print("\nKết thúc thử.", flush=True)
        for key in ["discard", "cancel"]:
            try:
                node.call(key)
            except Exception:
                pass
    except Exception as exc:
        print("Không thể tiếp tục:", exc, flush=True)
        try:
            input("Enter để đóng: ")
        except (EOFError, KeyboardInterrupt):
            pass
    finally:
        node.closed = True
        rclpy.try_shutdown()
        worker.join(timeout=2)
        node.destroy_node()


if __name__ == "__main__":
    main()
