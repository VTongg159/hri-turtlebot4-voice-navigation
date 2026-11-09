#!/usr/bin/env python3
"""Verify real microphone trial evidence and produce an honest acceptance receipt."""

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import wave

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/voice_demo/pairslab_live"
DEST = ROOT / "evidence/pairslab_redesign/voice_acceptance.json"


def main():
    attempts = json.loads((SOURCE / "results.json").read_text())
    events = [json.loads(line) for line in (SOURCE / "events.jsonl").read_text().splitlines()]
    audit = [json.loads(line) for line in (SOURCE / "asr.jsonl").read_text().splitlines()]
    successes = []
    expected = {1: ["A"], 2: ["E"], 3: ["A", "C", "D"]}
    for trial, route in expected.items():
        rows = [r for r in attempts if r["trial"] == trial]
        candidates = [r for r in rows if r.get("passed")]
        if not candidates:
            raise ValueError(f"No successful attempt for trial {trial}")
        row = candidates[-1]
        identity = row["parsed"]["command_id"]
        assert row["input_source"] == "real microphone"
        assert row["parsed"]["waypoints"] == route == row["navigation_terminal"]["waypoints"]
        assert row["navigation_terminal"]["state"] == "SUCCEEDED"
        assert row["asr"]["message"] == row["actual_transcript"] == row["parsed"]["transcript"]
        nav = [
            r["data"]
            for r in events
            if r["topic"] == "navigation" and r["data"].get("command_id") == identity
        ]
        # DDS replay is not counted as a second waypoint or action.
        nav = list({(r["sequence"], r["event"]): r for r in nav}.values())
        nav.sort(key=lambda r: r["sequence"])
        visited = [r["current_target"] for r in nav if r["event"] == "WAYPOINT_SUCCEEDED"]
        terminals = [
            r for r in nav if r["event"] == "ACTION_TERMINAL" and r.get("action_kind") == "nav"
        ]
        assert visited == route, (trial, visited)
        assert len(terminals) == len(route)
        assert all(r["action_status"] == 4 and r["error_code"] == 0 for r in terminals)
        audio = ROOT / row["asr"]["audio_file"]
        with wave.open(str(audio)) as f:
            duration = f.getnframes() / f.getframerate()
            assert f.getframerate() == 16000 and f.getnchannels() == 1 and f.getsampwidth() == 2
        assert abs(duration - row["asr"]["duration"]) < 0.01
        transcribing = next(
            r
            for r in audit
            if r.get("recording_id") == row["asr"]["recording_id"] and r["event"] == "TRANSCRIBING"
        )
        successes.append(
            dict(
                trial=trial,
                expected_sentence=row["expected_sentence"],
                actual_transcript=row["actual_transcript"],
                waypoints=route,
                attempts_required=rows.index(row) + 1,
                command_id=identity,
                nav_result="SUCCEEDED",
                visited_waypoints=visited,
                action_results=[
                    dict(status=r["action_status"], error_code=r["error_code"]) for r in terminals
                ],
                recorded_audio_file=row["asr"]["audio_file"],
                audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
                audio_duration_s=duration,
                asr_phase_wall_s=round(row["asr"]["wall_time"] - transcribing["wall_time"], 3),
                transcript_to_mission_end_wall_s=round(
                    row["navigation_terminal"]["wall_time"] - row["asr"]["wall_time"], 3
                ),
                completed_at=datetime.fromtimestamp(
                    row["navigation_terminal"]["wall_time"], ZoneInfo("Asia/Ho_Chi_Minh")
                ).isoformat(),
            )
        )
    for index, row in enumerate(attempts):
        if row.get("passed"):
            continue
        end = (
            attempts[index + 1]["started_wall_time"] if index + 1 < len(attempts) else float("inf")
        )
        goals = [
            event["data"]
            for event in events
            if event["topic"] == "navigation"
            and event["data"].get("event") == "GOAL_ACCEPTED"
            and row["started_wall_time"] <= event["data"].get("wall_time", 0) < end
        ]
        assert not goals, (index, goals)
    failures = [
        dict(
            trial=r["trial"],
            event=r.get("asr", {}).get("event"),
            actual_transcript=r.get("actual_transcript"),
            error=r.get("error"),
        )
        for r in attempts
        if not r.get("passed")
    ]
    summary = dict(
        test="T15 real microphone → Vietnamese ASR → parser → Nav2 → simulated TB4",
        status="PASS",
        date="2026-11-09",
        input_source="real microphone",
        successful_distinct_commands=3,
        attempt_count=len(attempts),
        successful_attempt_count=sum(bool(r.get("passed")) for r in attempts),
        first_attempt_success_count=sum(
            next(r for r in attempts if r["trial"] == i).get("passed", False) for i in expected
        ),
        successes=successes,
        failed_attempts=failures,
        failed_attempts_sent_no_goals_verified=True,
        limitations=[
            "One user/session, retries included; not a general ASR accuracy benchmark",
            "No screen video was recorded for this session",
        ],
        private_evidence_directory=str(SOURCE.relative_to(ROOT)),
    )
    DEST.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
