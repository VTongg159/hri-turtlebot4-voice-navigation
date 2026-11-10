#!/usr/bin/env python3
"""Restyle recorded video annotations using the original same-session ROS events."""

from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "deliverables/pairslab_demo_20261109"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
NAMES = {
    "A": "UAV Lab",
    "B": "Manipulation Lab",
    "C": "Lobby",
    "D": "HRI Lab / Unitree G1",
    "E": "Quadruped Lab / Unitree Go2",
    "F": "TurtleBot Lab",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_chapters(path):
    chapters = json.loads((SESSION / "render_manifest.json").read_text())["chapters"]
    titles = [
        "PAIRS Lab — Research environment",
        "T15 — Voice navigation to UAV Lab",
        "Nav2 tour — Keyboard input, 2x playback",
        "Nav2 — B / Manipulation Lab",
        "Nav2 — D / HRI Lab, Unitree G1",
        "Nav2 — C / Lobby",
        "Nav2 — F / TurtleBot Lab",
        "Tour resumed after AMCL update — Edited transition",
        "Nav2 — E / Quadruped Lab, Unitree Go2",
        "Nav2 — C / Lobby",
    ]
    assert len(chapters) == len(titles)
    metadata = [";FFMETADATA1", "title=PAIRS Lab - Map Segmentation and Voice Navigation"]
    duration = json.loads((SESSION / "render_manifest.json").read_text())["duration_s"]
    for i, (ch, title) in enumerate(zip(chapters, titles)):
        end = chapters[i + 1]["start"] if i + 1 < len(chapters) else duration
        metadata.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={round(ch['start'] * 1000)}",
                f"END={round(end * 1000)}",
                "title=" + title,
            ]
        )
    meta = SESSION / "clean_style_chapters.ffmeta"
    meta.write_text("\n".join(metadata) + "\n")
    target = path.with_name(path.stem + "_chapters.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-i",
            str(meta),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(target),
        ],
        check=True,
    )
    target.replace(path)
    return [dict(start=c["start"], title=t) for c, t in zip(chapters, titles)]


def main():
    public = ROOT / "submission/PAIRS_Lab_Demo_1080p.mp4"
    archive = SESSION / "PAIRS_Lab_Demo_original_style.mp4"
    if not archive.exists():
        archive.write_bytes(public.read_bytes())
    manifest = json.loads((SESSION / "render_manifest.json").read_text())
    assert sha(archive) == manifest["final_sha256"]
    events = [json.loads(line) for line in (SESSION / "ros_events.jsonl").read_text().splitlines()]
    events += [
        json.loads(line) for line in (SESSION / "voice/events.jsonl").read_text().splitlines()
    ]
    # Ignore delivery timestamps of retained messages; use actual event timestamps.
    nav = sorted(
        [e["data"] for e in events if e["topic"] == "navigation"],
        key=lambda d: d["wall_time"],
    )
    nav_times = [d["wall_time"] for d in nav]
    voice = json.loads((SESSION / "voice/filmed_acceptance.json").read_text())["result"]
    vbase = json.loads((SESSION / "02_voice_master_silent.json").read_text())[
        "capture_requested_wall_time"
    ]
    durations = [p["duration_s"] for p in manifest["parts"]]
    starts = [0]
    for duration in durations:
        starts.append(starts[-1] + duration)
    fonts = {size: ImageFont.truetype(FONT, size) for size in (18, 20, 22, 24, 26)}

    def layout(t):
        part = min(bisect_right(starts, t) - 1, 3)
        if part == 0:
            wall = 0
            title = "PAIRS Lab — Research environment"
            note = "Gazebo Harmonic | Scene overview"
        elif part == 1:
            wall = vbase + manifest["voice"]["trim_start_s"] + t - starts[1]
            title = "Voice navigation — UAV Lab"
            note = "Microphone → ASR → Parser → Nav2 | 1×"
        else:
            chunk = manifest["navigation_chunks"][part - 2]
            wall = chunk["base"] + chunk["begin"] + 2 * (t - starts[part])
            title = "Nav2 room tour"
            note = "Keyboard input | 2× playback"
            if part == 3:
                note += " | Resumed after AMCL update"
        panel = Image.new("RGB", (1920, 1080), "white")
        d = ImageDraw.Draw(panel)

        def text(x, y, value, size=22, gray=40):
            d.text((x, y), value, font=fonts[size], fill=(gray,) * 3)

        d.rectangle((0, 0, 1919, 54), fill="#eeeeee")
        text(24, 12, title, 24)
        text(24, 1028, note, 22)
        d.line((1280, 55, 1280, 1005), fill="#bcbcbc")
        text(1304, 76, "Navigation", 26)
        text(1304, 180, "Map", 20, 80)
        text(1304, 666, "Triangle: robot   Line: recorded trajectory", 18, 80)
        state = None
        if part:
            index = bisect_right(nav_times, wall) - 1
            if index >= 0:
                state = nav[index]
            if part == 1 and state and state.get("command_id") != voice["parsed"]["command_id"]:
                state = None
        if state:
            route = state.get("waypoints", [])
            target = state.get("current_target") or (route[-1] if route else None)
            if target:
                text(1304, 126, f"Goal: {target} — {NAMES.get(target, target)}", 24)
            text(1304, 710, "Nav2 status", 20, 80)
            text(1480, 708, state["state"], 24)
            text(1304, 754, "Route: " + " → ".join(route), 22)
            text(1304, 928, "command_id", 18, 80)
            text(1304, 957, state.get("command_id", ""), 18)
        elif part == 0:
            text(1304, 126, "Five research labs + lobby", 24)
            text(1304, 714, "A  UAV     B  Manipulation     C  Lobby", 20)
            text(1304, 758, "D  HRI     E  Quadruped     F  TurtleBot", 20)
        else:
            text(1304, 710, "Nav2 status: awaiting command", 22)
        if part == 1:
            text(1304, 808, "ASR transcript", 20, 80)
            # Reveal only after the real ASR event; preserve its verbatim spelling.
            if wall >= voice["asr"]["wall_time"]:
                text(1304, 842, voice["actual_transcript"], 24)
            else:
                text(1304, 842, "Waiting for ASR result…", 22)
        elif part > 1:
            successes = []
            for row in manifest["coverage"]["results"]:
                if row["terminal"]["state"] == "SUCCEEDED" and row["terminal"]["wall_time"] <= wall:
                    if row["region"] not in successes:
                        successes.append(row["region"])
            # A was reached by the preceding real microphone command.
            text(1304, 808, "Completed goals", 20, 80)
            text(1304, 842, " → ".join(["A", *successes]), 24)
        return np.asarray(panel).copy()

    capture = cv2.VideoCapture(str(archive))
    fps = capture.get(cv2.CAP_PROP_FPS)
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    target = SESSION / "PAIRS_Lab_Demo_clean_style.mp4"
    log = (SESSION / "restyle_video_ffmpeg.log").open("w")
    encoder = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "1920x1080",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            "-i",
            str(archive),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map_chapters",
            "1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(target),
        ],
        stdin=subprocess.PIPE,
        stderr=log,
    )
    cache_key = None
    frame_number = 0
    while True:
        ok, bgr = capture.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        t = frame_number / fps
        key = int(t * 4)
        if key != cache_key:
            background = layout(t)
            cache_key = key
        out = background.copy()
        out[75:1005, :1280] = rgb[75:1005, :1280]
        gray = cv2.cvtColor(rgb[220:647, 1305:1895], cv2.COLOR_RGB2GRAY)
        out[220:647, 1305:1895] = gray[:, :, None]
        assert np.array_equal(out[75:1005, :1280], rgb[75:1005, :1280])
        encoder.stdin.write(out.tobytes())
        frame_number += 1
        if frame_number % 900 == 0:
            print(f"Rendered {frame_number}/{count} frames", flush=True)
    capture.release()
    encoder.stdin.close()
    assert encoder.wait() == 0
    log.close()
    assert frame_number == count
    update_chapters(target)

    # Hash compressed audio packets, independent of MP4 container metadata.
    def audio_hash(path):
        return subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-c",
                "copy",
                "-f",
                "hash",
                "-hash",
                "sha256",
                "-",
            ],
            text=True,
        ).strip()

    assert audio_hash(archive) == audio_hash(target)
    receipt = dict(
        original_sha256=sha(archive),
        output_sha256=sha(target),
        original_video="https://github.com/VTongg159/hri-turtlebot4-voice-navigation/blob/451198d/submission/PAIRS_Lab_Demo_1080p.mp4",
        fps=fps,
        frames=frame_number,
        application_pixels="Original decoded Gazebo region copied unchanged before H.264 re-encoding",
        map="Original per-frame map crop converted to grayscale; marker and recorded trajectory preserved",
        labels="English technical terminology; verbatim Vietnamese ASR transcript",
        status_source="Same-session ROS event wall_time mapped through original edit segments; label refresh 4 Hz",
        audio="Original AAC packets copied unchanged; SHA256 verified",
        audio_packet_hash=audio_hash(target),
        timeline="Original cuts and 1x voice / 2x keyboard tour timing retained",
    )
    (ROOT / "submission/evidence/video_style.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    )
    public.write_bytes(target.read_bytes())
    print("PASS: original frame count, Gazebo crop and audio checks", flush=True)


if __name__ == "__main__":
    main()
