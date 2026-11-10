#!/usr/bin/env python3
"""Export the genuine source-destination voice trial and append it to the demo."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "evidence/voice_demo/source_destination_live"
SUB = ROOT / "submission"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def probe(p):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                "-of",
                "json",
                str(p),
            ]
        )
    )


def ffmpeg(args):
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-filter_complex_threads",
            "2",
            "-filter_threads",
            "2",
            "-y",
            *map(str, args),
        ],
        check=True,
    )


def main():
    result = json.loads((LOCAL / "result.json").read_text())
    assert result["passed"] and result["parsed"]["waypoints"] == ["A", "B"]
    assert result["asr"]["message"] == "Đi từ khu vực A đến khu vực B"
    events = [json.loads(s) for s in (LOCAL / "events.jsonl").read_text().splitlines()]
    audio = ROOT / result["asr"]["audio_file"]
    assert sha(audio) == result["audio_sha256"]
    recording = max(
        e["data"]["wall_time"]
        for e in events
        if e["topic"] == "asr" and e["data"].get("event") == "RECORDING"
    )
    delay = recording - result["capture_started_wall_time"]
    assert 0 <= delay < 3
    clip = SUB / "source_destination_voice_demo.mp4"
    ffmpeg(
        [
            "-i",
            LOCAL / "screen_silent.mp4",
            "-i",
            audio,
            "-filter_complex",
            f"[0:v]crop=932:1008:0:32,pad=1920:1080:494:36:color=0x303030[v];[1:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={round(delay * 1000)}:all=1,apad[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-threads",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-t",
            str(float(probe(LOCAL / "screen_silent.mp4")["format"]["duration"])),
            "-shortest",
            "-movflags",
            "+faststart",
            clip,
        ]
    )
    main_video = SUB / "PAIRS_Lab_Demo_1080p.mp4"
    backup = LOCAL / "demo_before_source_destination.mp4"
    if not backup.exists():
        shutil.copyfile(main_video, backup)
    before = probe(backup)
    offset = float(before["format"]["duration"])
    clip_duration = float(probe(clip)["format"]["duration"])
    chapters = [
        dict(start=float(c["start_time"]), title=c["tags"]["title"]) for c in before["chapters"]
    ]
    chapters.append(dict(start=offset, title="T07 — Voice source-destination: F to A to B (1x)"))
    switch = result["segments"][1]["goal_accepted_wall_time"] - result["capture_started_wall_time"]
    chapters.append(dict(start=offset + switch, title="T07 — A reached; continuing to B"))
    metadata = [";FFMETADATA1", "title=PAIRS Lab - Map Segmentation and Voice Navigation"]
    for i, chapter in enumerate(chapters):
        end = chapters[i + 1]["start"] if i + 1 < len(chapters) else offset + clip_duration
        metadata += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={round(chapter['start'] * 1000)}",
            f"END={round(end * 1000)}",
            "title=" + chapter["title"],
        ]
    meta = LOCAL / "appended_chapters.ffmeta"
    meta.write_text("\n".join(metadata) + "\n")
    concat = LOCAL / "concat.txt"
    concat.write_text(f"file '{backup}'\nfile '{clip}'\n")
    temporary = LOCAL / "combined_demo.mp4"
    ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat,
            "-i",
            meta,
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
            temporary,
        ]
    )
    ffmpeg(["-threads", "2", "-i", temporary, "-f", "null", "-"])
    shutil.copyfile(temporary, main_video)
    folder = SUB / "evidence/source_destination_voice"
    folder.mkdir(exist_ok=True)
    for name in [
        "result.json",
        "events.jsonl",
        "tf_samples.json",
        "terminal.log",
        "preprocessing_tests.log",
        "build.log",
        "position_at_F.json",
        "position_at_F.log",
    ]:
        shutil.copyfile(LOCAL / name, folder / name)
    attempts = []
    for number, name in enumerate(
        [
            "attempt1_no_speech",
            "attempt2_confidence_rejected",
            "attempt3_vad_rejected",
            "attempt4_confidence_rejected",
            "attempt5_unknown_region",
            ".",
        ],
        1,
    ):
        log = LOCAL / name / "events.jsonl"
        rows = [json.loads(s) for s in log.read_text().splitlines()]
        begins = [
            e["data"]["wall_time"]
            for e in rows
            if e["topic"] == "asr" and e["data"].get("event") == "RECORDING"
        ]
        start = max(begins)
        terminals = [
            e["data"]
            for e in rows
            if e["topic"] == "asr"
            and e["data"].get("wall_time", 0) >= start
            and e["data"].get("event") in ["TRANSCRIPT", "NO_SPEECH"]
        ]
        asr = terminals[-1]
        attempts.append(
            dict(
                attempt=number,
                asr=asr,
                completed_navigation=number == 6,
                config_stage="highpass + Whisper joint silence policy"
                if number >= 5
                else "earlier ASR configuration",
            )
        )
    (folder / "attempts.json").write_text(
        json.dumps(
            dict(
                total_recordings=6,
                selected_attempt=6,
                final_configuration_recordings=2,
                note="Includes one operator-not-ready silent recording. A model startup retry had no microphone recording and is not counted. Configuration changed during debugging; this is not a fixed-configuration ASR accuracy benchmark.",
                attempts=attempts,
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    final_still = SUB / "figures/source_destination_voice_succeeded.png"
    ffmpeg(["-ss", max(0, clip_duration - 2), "-i", clip, "-frames:v", "1", final_still])
    transition = SUB / "figures/source_destination_A_to_B.png"
    ffmpeg(
        [
            "-i",
            LOCAL / "A_to_B_transition.png",
            "-vf",
            "crop=932:1008:0:32",
            "-frames:v",
            "1",
            transition,
        ]
    )
    proof = dict(
        video="source_destination_voice_demo.mp4",
        sha256=sha(clip),
        duration_s=clip_duration,
        capture="Continuous native X11 terminal screen recording cropped from desktop, centered on neutral background at 1x; no painted telemetry. RViz was obscured during capture and is not presented as part of this clip.",
        source_video_sha256=sha(LOCAL / "screen_silent.mp4"),
        source_audio_sha256=sha(audio),
        audio_delay_s=delay,
        audio_alignment="Same-session RECORDING wall_time minus capture request wall_time; subsecond capture/device startup uncertainty",
        previous_demo_sha256=sha(backup),
        final_demo_sha256=sha(main_video),
        added_section_start_s=offset,
        final_demo_duration_s=float(probe(main_video)["format"]["duration"]),
        chapters=chapters,
        decode_check="PASS",
        command_id=result["parsed"]["command_id"],
        screenshot="figures/" + final_still.name,
        screenshot_sha256=sha(final_still),
        screenshot_from_clip_s=max(0, clip_duration - 2),
    )
    (folder / "video.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n")
    (SUB / "CHAPTERS.md").write_text(
        "# PAIRS Lab — Video chapters\n\n"
        + "\n".join(
            f"- **{int(c['start']) // 60:02d}:{int(c['start']) % 60:02d}** {c['title']}"
            for c in chapters
        )
        + "\n\nOriginal tour uses labelled keyboard input at 2x; appended source-destination trial uses real microphone audio and continuous native screen recording at 1x.\n"
    )
    print(json.dumps(proof, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
