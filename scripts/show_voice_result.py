#!/usr/bin/env python3
"""Display saved ASR/parser/Nav2 results as a compact terminal report."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import threading
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hold", action="store_true")
    args = parser.parse_args()
    evidence = ROOT / "submission/evidence"
    trial = json.loads((evidence / "filmed_voice_acceptance.json").read_text())
    trace = json.loads((evidence / "figure7_command_trace.json").read_text())
    record = trial["result"]
    parsed = record["parsed"]
    identity = parsed["command_id"]
    assert identity == trial["command_id"] == record["navigation_terminal"]["command_id"]
    assert all(e["command_id"] == identity for e in trace)
    assert parsed["transcript"] == record["actual_transcript"] == record["asr"]["message"]
    events = {e["event"]: e for e in trace}
    actions = {e["action_kind"]: e for e in trace if e["event"] == "ACTION_TERMINAL"}
    assert all(e["action_status"] == 4 and e["error_code"] == 0 for e in actions.values())
    config = yaml.safe_load((ROOT / "submission/config/pairs_regions.yaml").read_text())
    region = next(r for r in config["regions"] if r["id"] == parsed["waypoints"][0])
    goal = region["goal"]

    def clock(event):
        return datetime.fromtimestamp(event["wall_time"], ZoneInfo("Asia/Ho_Chi_Minh")).strftime(
            "%H:%M:%S.%f"
        )[:-3]

    duration = record["navigation_terminal"]["wall_time"] - record["asr"]["wall_time"]
    lines = [
        "PAIRS Lab | Kiểm thử điều hướng bằng giọng nói | 09/11/2026",
        f"command_id: {identity}",
        "",
        "[1] PUSH-TO-TALK / SPEECH RECOGNITION",
        "    Enter bắt đầu ghi -> nói -> Enter dừng ghi -> nhận dạng",
        f"    Audio       : microphone | {record['asr']['duration']:.3f} s | 16 kHz, mono, PCM16",
        f"    ASR         : {record['asr']['event']} [{clock(record['asr'])}]",
        f"    Transcript  : {record['actual_transcript']}",
        "",
        "[2] COMMAND PARSER / SEMANTIC MAP",
        f"    Type        : {parsed['type']}",
        f"    Waypoints   : {parsed['waypoints']}",
        f"    Destination : {region['id']} - {region['name']}",
        f"    Goal (map)  : x={goal['x']:.2f} m, y={goal['y']:.2f} m, yaw={goal['yaw']:.4f} rad",
        "",
        "[3] NAV2 / ROBOT NAVIGATION",
        f"    {clock(events['ACCEPTED'])}  ACCEPTED -> kiểm tra định vị và goal",
        f"    {clock(actions['plan'])}  ComputePathToPose: SUCCEEDED, error_code=0",
        f"    {clock(events['GOAL_ACCEPTED'])}  NavigateToPose: GOAL_ACCEPTED",
        f"    {clock(actions['nav'])}  NavigateToPose: SUCCEEDED, error_code=0",
        f"    {clock(events['WAYPOINT_SUCCEEDED'])}  WAYPOINT_SUCCEEDED: A",
        f"    {clock(events['ALL_WAYPOINTS_REACHED'])}  ALL_WAYPOINTS_REACHED",
        "",
        f"    Kết quả     : SUCCEEDED - hoàn thành đích A ({region['name']})",
        f"    Thời gian   : {duration:.3f} s từ transcript đến kết thúc nhiệm vụ",
        "    Lượt ghi    : 2/2; lượt đầu NO_SPEECH, lượt sau hoàn thành",
    ]
    output = "\n".join(lines) + "\n"
    (ROOT / "submission/figures/figure7_voice_command_result.txt").write_text(output)
    print(output, end="", flush=True)
    if args.hold:
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
