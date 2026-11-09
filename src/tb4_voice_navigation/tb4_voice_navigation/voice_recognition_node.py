"""Real ALSA push-to-talk + local multilingual Whisper with bounded recording."""

import json
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import threading
import time
import uuid
import wave
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger


class VoiceRecognitionNode(Node):
    def __init__(self):
        super().__init__("voice_recognition_node")
        defaults = dict(
            model="small",
            local_files_only=True,
            cpu_threads=4,
            audio_device="default",
            max_record_seconds=12,
            min_record_seconds=0.4,
            min_rms=0.008,
            max_clipping_fraction=0.08,
            min_avg_logprob=-0.8,
            max_no_speech_probability=0.5,
            recordings_dir="",
            audit_file="",
        )
        for k, v in defaults.items():
            self.declare_parameter(k, v)
        self.p = lambda k: self.get_parameter(k).value
        if not 1 <= self.p("max_record_seconds") <= 30:
            raise ValueError("max_record_seconds must be 1..30")
        self.pub = self.create_publisher(String, "/voice/transcript", 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status_pub = self.create_publisher(String, "/voice/asr_status", qos)
        self.start_srv = self.create_service(Trigger, "/voice/record/start", self.start)
        self.stop_srv = self.create_service(Trigger, "/voice/record/stop", self.stop)
        self.discard_srv = self.create_service(Trigger, "/voice/record/discard", self.discard)
        self.events = queue.Queue()
        self.model = None
        self.process = None
        self.worker = None
        self.recording_id = 0
        self.ready = False
        self.discarded = False
        self.stop_requested = False
        self.closed = False
        self.timer = self.create_timer(0.1, self.drain)
        self.status("MODEL_LOADING", "Đang nạp Whisper đa ngôn ngữ từ máy local")
        threading.Thread(target=self.load_model, daemon=True).start()

    def status(self, event, message, **extra):
        data = dict(
            event=event,
            message=message,
            ready=self.ready,
            busy=bool(self.worker and self.worker.is_alive()),
            wall_time=time.time(),
            **extra,
        )
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
        self.status_pub.publish(String(data=encoded))
        self.get_logger().info(encoded)
        if self.p("audit_file"):
            try:
                with open(self.p("audit_file"), "a", encoding="utf8") as f:
                    f.write(encoded + "\n")
            except OSError as exc:
                self.get_logger().error(f"ASR audit: {exc}")

    def load_model(self):
        try:
            if not shutil.which("arecord"):
                raise RuntimeError("Thiếu arecord (alsa-utils)")
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                self.p("model"),
                device="cpu",
                compute_type="int8",
                cpu_threads=self.p("cpu_threads"),
                num_workers=1,
                local_files_only=self.p("local_files_only"),
            )
            if not self.model.model.is_multilingual:
                raise RuntimeError("Model phải hỗ trợ đa ngôn ngữ/tiếng Việt")
            self.events.put(("MODEL_READY", "Whisper sẵn sàng; dùng service start/stop để nói", {}))
        except Exception as exc:
            self.events.put(("MODEL_ERROR", str(exc), {}))

    def drain(self):
        while True:
            try:
                event, message, extra = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "MODEL_READY":
                self.ready = True
            if (
                event == "TRANSCRIPT"
                and extra.get("recording_id") == self.recording_id
                and not self.discarded
                and not self.closed
            ):
                self.pub.publish(String(data=message))
            self.status(event, message, **extra)

    def start(self, request, response):
        if not self.ready:
            response.success = False
            response.message = "ASR chưa sẵn sàng; xem /voice/asr_status"
            return response
        if self.worker and self.worker.is_alive():
            response.success = False
            response.message = "Đang ghi âm hoặc nhận dạng"
            return response
        self.discarded = False
        self.stop_requested = False
        self.recording_id += 1
        try:
            self.process = subprocess.Popen(
                [
                    "arecord",
                    "-q",
                    "-D",
                    self.p("audio_device"),
                    "-t",
                    "raw",
                    "-f",
                    "S16_LE",
                    "-r",
                    "16000",
                    "-c",
                    "1",
                    "-d",
                    str(self.p("max_record_seconds")),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.worker = threading.Thread(
                target=self.capture, args=(self.recording_id,), daemon=True
            )
            self.worker.start()
            response.success = True
            response.message = f"Đang ghi âm, tối đa {self.p('max_record_seconds')} giây"
            self.status("RECORDING", response.message)
        except OSError as exc:
            response.success = False
            response.message = str(exc)
            self.status("AUDIO_DEVICE_ERROR", str(exc))
        return response

    def stop(self, request, response):
        if self.process is not None and self.process.poll() is None:
            self.stop_requested = True
            try:
                self.process.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass
            response.success = True
            response.message = "Dừng ghi; đang nhận dạng"
        else:
            response.success = False
            response.message = "Không có phiên ghi âm đang chạy"
        return response

    def discard(self, request, response):
        self.discarded = True
        self.stop(request, response)
        response.success = True
        response.message = "Đã bỏ phiên âm thanh; không publish transcript"
        return response

    def capture(self, recording_id):
        try:
            process = self.process
            try:
                raw, stderr = process.communicate(timeout=self.p("max_record_seconds") + 4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError("AUDIO_TIMEOUT: arecord không kết thúc")
            if process.returncode and not self.stop_requested:
                raise RuntimeError("AUDIO_DEVICE_ERROR: " + stderr.decode(errors="replace")[:500])
            if self.discarded or self.closed:
                return
            samples = (
                np.frombuffer(raw[: len(raw) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
            )
            duration = len(samples) / 16000
            if duration < self.p("min_record_seconds"):
                self.events.put(("NO_AUDIO", "Âm thanh quá ngắn", dict(duration=duration)))
                return
            rms = float(np.sqrt(np.mean(samples * samples)))
            clip = float(np.mean(abs(samples) > 0.995))
            metrics = dict(
                recording_id=recording_id, duration=duration, rms=rms, clipping_fraction=clip
            )
            if rms < self.p("min_rms"):
                self.events.put(("NO_SPEECH", "Tín hiệu quá nhỏ; không gửi transcript", metrics))
                return
            if clip > self.p("max_clipping_fraction"):
                self.events.put(
                    ("CLIPPED_AUDIO", "Âm thanh bị clipping; giảm gain microphone", metrics)
                )
                return
            if self.p("recordings_dir"):
                folder = Path(self.p("recordings_dir"))
                folder.mkdir(parents=True, exist_ok=True)
                filename = folder / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.wav"
                with wave.open(str(filename), "wb") as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(16000)
                    f.writeframes(raw)
                metrics["audio_file"] = str(filename)
            self.events.put(("TRANSCRIBING", "Đang nhận dạng tiếng Việt", metrics))
            segments, info = self.model.transcribe(
                samples,
                language="vi",
                beam_size=5,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(min_speech_duration_ms=250, min_silence_duration_ms=400),
                condition_on_previous_text=False,
                max_new_tokens=100,
            )
            accepted = []
            for segment in segments:
                if segment.avg_logprob >= self.p(
                    "min_avg_logprob"
                ) and segment.no_speech_prob <= self.p("max_no_speech_probability"):
                    accepted.append(segment.text.strip())
            transcript = " ".join(" ".join(accepted).split())
            metrics["vad_speech_seconds"] = float(info.duration_after_vad)
            if self.discarded or self.closed:
                return
            if not transcript or len(transcript) > 240 or sum(c.isalpha() for c in transcript) < 2:
                self.events.put(
                    ("NO_SPEECH", "Không có transcript đủ tin cậy; không gửi lệnh", metrics)
                )
                return
            self.events.put(("TRANSCRIPT", transcript, metrics))
        except Exception as exc:
            self.events.put(("ASR_ERROR", str(exc), {}))

    def close(self):
        self.closed = True
        self.discarded = True
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


def main(args=None):
    rclpy.init(args=args)
    node = VoiceRecognitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()
