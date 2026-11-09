#!/usr/bin/env python3
"""Read-only terminal reconstruction of a recorded trial; never starts ROS or audio."""

import argparse
import json
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hold", action="store_true", help="Keep the terminal open for a screenshot"
    )
    args = parser.parse_args()
    evidence = ROOT / "submission/evidence"
    trial = json.loads((evidence / "filmed_voice_acceptance.json").read_text())
    attempts = json.loads((evidence / "filmed_voice_attempts.json").read_text())
    row = trial["result"]
    command = row["parsed"]
    terminal = row["navigation_terminal"]
    assert trial["passed"] and row["passed"]
    assert command["command_id"] == terminal["command_id"] == trial["command_id"]
    assert row["actual_transcript"] == row["asr"]["message"] == command["transcript"]
    assert command["waypoints"] == terminal["waypoints"] == ["A"]
    assert terminal["state"] == "SUCCEEDED"
    assert len(attempts) == 2 and not attempts[0]["passed"] and attempts[1]["passed"]
    excerpt = (evidence / "filmed_voice_terminal_excerpt.txt").read_text().strip()
    parsed = json.dumps(command, indent=2, ensure_ascii=False)
    output = (
        "HÌNH 7 — TÁI DỰNG TỪ LOG THẬT (không phải ảnh chụp lúc thử)\n"
        "Phiên gốc: 09/11/2026. Lần xem này KHÔNG thu âm, KHÔNG gửi navigation goal.\n"
        "\n"
        "[1] PUSH-TO-TALK / ASR — trích terminal gốc của lượt đạt; lược dòng trống\n"
        + excerpt
        + "\n\n"
        "[2] PARSER — dữ liệu JSON của cùng lượt, bổ sung từ receipt đã lưu\n" + parsed + "\n\n"
        "[3] NAV2 — đối chiếu terminal result trong receipt\n"
        + f"command_id : {terminal['command_id']}\n"
        + f"state      : {terminal['state']}\n"
        + f"event      : {terminal['event']}\n"
        + "\n"
        "Lưu ý: có 2 lượt ghi — lượt đầu NO_SPEECH; lượt sau đạt như hiển thị.\n"
        "Nguồn: submission/evidence/filmed_voice_acceptance.json và filmed_voice_attempts.json\n"
    )
    target = ROOT / "submission/figures/figure7_push_to_talk_reconstructed.txt"
    target.write_text(output)
    print(output, end="", flush=True)
    if args.hold:
        print("\nBản xem log tĩnh; nhấn Ctrl+C để đóng.", flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
