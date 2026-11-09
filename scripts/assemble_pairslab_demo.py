#!/usr/bin/env python3
"""Assemble filmed evidence; mux only the microphone audio from this filmed trial."""

from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def probe(path):
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            text=True,
        )
    )


def run(args, log):
    with log.open("w") as f:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-y", *args],
            stdout=f,
            stderr=subprocess.STDOUT,
            check=True,
        )


def stamp(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--session", default="deliverables/pairslab_demo_20261109")
    a = p.parse_args()
    session = (ROOT / a.session).resolve()
    parts = session / "edited"
    parts.mkdir(exist_ok=True)
    coverage = json.loads((session / "coverage.json").read_text())
    assert coverage["passed"] and set("ABDEF") <= set(coverage["visited"])
    filmed = json.loads((session / "voice/filmed_acceptance.json").read_text())
    assert filmed["passed"]
    record = filmed["result"]
    audio = ROOT / record["asr"]["audio_file"]
    assert audio.is_file()
    assert (
        record["actual_transcript"] == record["parsed"]["transcript"]
        and record["navigation_terminal"]["state"] == "SUCCEEDED"
    )
    meta = json.loads((session / "02_voice_master_silent.json").read_text())
    base = meta["capture_requested_wall_time"]
    assert (
        base
        <= record["started_wall_time"]
        <= record["asr"]["wall_time"]
        <= record["navigation_terminal"]["wall_time"]
        <= meta["capture_stopped_wall_time"]
    )
    with wave.open(str(audio)) as f:
        audio_duration = f.getnframes() / f.getframerate()
        assert f.getnchannels() == 1 and f.getsampwidth() == 2
    assert abs(audio_duration - record["asr"]["duration"]) < 0.01
    # File belongs to this filmed trial; do not borrow audio from the earlier acceptance session.
    events = [json.loads(s) for s in (session / "voice/events.jsonl").read_text().splitlines()]
    recording = next(
        e["data"]
        for e in events
        if e["topic"] == "asr"
        and e["data"].get("event") == "RECORDING"
        and record["started_wall_time"]
        <= e["data"].get("wall_time", 0)
        <= record["asr"]["wall_time"]
    )
    raw_duration = float(probe(session / "02_voice_master_silent.mp4")["format"]["duration"])
    begin = max(0, record["started_wall_time"] - base - 2)
    end = min(raw_duration, record["navigation_terminal"]["wall_time"] - base + 9)
    length = end - begin
    audio_delay = max(0, recording["wall_time"] - base - begin)
    assert length > audio_delay + audio_duration
    title_voice = parts / "voice_label.txt"
    title_voice.write_text("T15 — microphone thật | hình và âm thanh cùng lượt quay")
    title_tour = parts / "tour_label.txt"
    title_tour.write_text("TĂNG TỐC 2x | Nguồn lệnh: văn bản tham quan")
    silent = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    broll = parts / "01_environment.mp4"
    run(
        [
            "-i",
            str(session / "01_environment_master.mp4"),
            *silent,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(broll),
        ],
        parts / "broll_mux.log",
    )
    voice = parts / "02_voice_real.mp4"
    voice_filter = f"drawtext=fontfile={FONT}:textfile={title_voice}:fontcolor=white:fontsize=27:box=1:boxcolor=0x102133@0.9:boxborderw=12:x=28:y=25"
    run(
        [
            "-ss",
            str(begin),
            "-i",
            str(session / "02_voice_master_silent.mp4"),
            "-i",
            str(audio),
            "-filter_complex_threads",
            "2",
            "-filter_complex",
            f"[0:v]{voice_filter},format=yuv420p[v];[1:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={round(audio_delay * 1000)}:all=1,apad[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            str(length),
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
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(voice),
        ],
        parts / "voice_mux.log",
    )
    ros = [json.loads(s) for s in (session / "ros_events.jsonl").read_text().splitlines()]
    native_meta = json.loads((session / "03_navigation_master.json").read_text())
    chunks = [
        dict(
            name="03_navigation_master",
            begin=0.0,
            end=float(probe(session / "03_navigation_master.mp4")["format"]["duration"]),
            base=native_meta["capture_requested_wall_time"],
        )
    ]
    if coverage.get("resumed_after_localization_loss"):
        failed = json.loads((session / "navigation_results.json").read_text())[-1]
        assert failed["terminal"]["event"] == "LOCALIZATION_LOST"
        accepted = next(
            e["data"]
            for e in ros
            if e["topic"] == "navigation"
            and e["data"].get("command_id") == failed["parsed"]["command_id"]
            and e["data"].get("event") == "ACCEPTED"
        )
        chunks[0]["end"] = accepted["wall_time"] - chunks[0]["base"] - 0.4
        resumed = json.loads((session / "04_navigation_resume.json").read_text())
        chunks.append(
            dict(
                name="04_navigation_resume",
                begin=0.0,
                end=float(probe(session / "04_navigation_resume.mp4")["format"]["duration"]),
                base=resumed["capture_requested_wall_time"],
            )
        )
    native_clips = []
    for index, chunk in enumerate(chunks):
        target = parts / f"03_tour_part{index + 1}_2x.mp4"
        label = parts / f"tour_label_{index}.txt"
        label.write_text(
            "TĂNG TỐC 2x | Lệnh văn bản"
            + (" | Nối sau cập nhật AMCL; có cắt dựng" if index else "")
        )
        vf = f"setpts=0.5*(PTS-STARTPTS),drawtext=fontfile={FONT}:textfile={label}:fontcolor=white:fontsize=25:box=1:boxcolor=0x102133@0.9:boxborderw=12:x=28:y=25,format=yuv420p"
        duration = (chunk["end"] - chunk["begin"]) / 2
        run(
            [
                "-ss",
                str(chunk["begin"]),
                "-i",
                str(session / (chunk["name"] + ".mp4")),
                *silent,
                "-vf",
                vf,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                str(duration),
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
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(target),
            ],
            parts / f"tour_part{index + 1}.log",
        )
        native_clips.append(target)
    clips = [broll, voice, *native_clips]
    durations = [float(probe(c)["format"]["duration"]) for c in clips]
    manifest = parts / "concat.txt"
    manifest.write_text("".join("file '" + str(c) + "'\n" for c in clips))
    final = session / "PAIRS_Lab_Demo_1080p.mp4"
    chapters = [
        dict(start=0.0, title="Giới thiệu PAIRS Lab và 5 khu nghiên cứu"),
        dict(start=durations[0], title="T15: giọng nói thật → phòng UAV"),
        dict(start=sum(durations[:2]), title="Tour Nav2 bằng văn bản, tăng tốc 2x"),
    ]
    for index, chunk in enumerate(chunks):
        offset = sum(durations[: 2 + index])
        if index:
            chapters.append(
                dict(start=offset, title="Nối sau mất định vị và cập nhật AMCL; bản có cắt dựng")
            )
        for row in coverage["results"]:
            identity = row["parsed"]["command_id"]
            accepted = next(
                (
                    e["data"]
                    for e in ros
                    if e["topic"] == "navigation"
                    and e["data"].get("command_id") == identity
                    and e["data"].get("event") == "ACCEPTED"
                ),
                None,
            )
            if (
                accepted
                and chunk["base"] + chunk["begin"]
                <= accepted["wall_time"]
                < chunk["base"] + chunk["end"]
            ):
                point = offset + (accepted["wall_time"] - chunk["base"] - chunk["begin"]) / 2
                chapters.append(
                    dict(
                        start=point,
                        title="Nav2 → "
                        + row["region"]
                        + " / "
                        + {
                            "B": "Tay máy",
                            "D": "HRI G1",
                            "C": "Sảnh",
                            "F": "TurtleBot",
                            "E": "Go2",
                        }.get(row["region"], row["region"]),
                    )
                )
    chapters.sort(key=lambda c: c["start"])
    metadata = parts / "chapters.ffmeta"
    total = sum(durations)
    lines = [";FFMETADATA1", "title=PAIRS Lab - Map Segmentation and Voice Navigation"]
    for i, ch in enumerate(chapters):
        finish = chapters[i + 1]["start"] if i + 1 < len(chapters) else total
        if finish - ch["start"] < 0.05:
            continue
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={round(ch['start'] * 1000)}",
            f"END={round(finish * 1000)}",
            "title=" + ch["title"],
        ]
    metadata.write_text("\n".join(lines) + "\n")
    run(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-i",
            str(metadata),
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
            str(final),
        ],
        parts / "concat.log",
    )
    output = probe(final)
    v = next(s for s in output["streams"] if s["codec_type"] == "video")
    au = next(s for s in output["streams"] if s["codec_type"] == "audio")
    assert (v["width"], v["height"]) == (1920, 1080) and au["codec_name"] == "aac"
    assert abs(float(output["format"]["duration"]) - total) < 1
    verify = session / "decode_check.log"
    with verify.open("w") as f:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-threads", "2", "-i", str(final), "-f", "null", "-"],
            stdout=f,
            stderr=subprocess.STDOUT,
            check=True,
        )
    assert not verify.read_text().strip(), "Video decode produced errors"
    receipt = dict(
        final_video=str(final.relative_to(ROOT)),
        final_sha256=hashlib.sha256(final.read_bytes()).hexdigest(),
        resolution=[1920, 1080],
        capture_fps=15,
        duration_s=float(output["format"]["duration"]),
        parts=[dict(file=str(c.relative_to(ROOT)), duration_s=d) for c, d in zip(clips, durations)],
        voice=dict(
            source_audio=str(audio.relative_to(ROOT)),
            audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
            actual_transcript=record["actual_transcript"],
            command_id=record["parsed"]["command_id"],
            raw_video=str((session / "02_voice_master_silent.mp4").relative_to(ROOT)),
            trim_start_s=begin,
            trim_end_s=end,
            audio_delay_in_clip_s=audio_delay,
            alignment="Same-session RECORDING event wall time relative to screen capture request; subsecond capture/device startup uncertainty",
            nav_state=record["navigation_terminal"]["state"],
            trials=[
                dict(
                    passed=r.get("passed", False),
                    asr_event=r.get("asr", {}).get("event"),
                    actual_transcript=r.get("actual_transcript"),
                )
                for r in json.loads((session / "voice/results.json").read_text())
            ],
            editing_note="Successful voice attempt only; preceding NO_SPEECH retained in raw video, WAV and logs",
        ),
        navigation_source="labelled keyboard transcripts",
        navigation_chunks=chunks,
        editing_note="Edited sections; failed E attempt omitted from submission clip, preserved in raw. Resume is labelled after stationary AMCL measurement updates; no teleport.",
        navigation_playback_speed=2,
        coverage=coverage,
        chapters=chapters,
        decode_check="PASS",
    )
    (session / "render_manifest.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False))
    (session / "CHAPTERS.md").write_text(
        "# PAIRS Lab — video chapters\n\n"
        + "\n".join(f"- **{stamp(c['start'])}** {c['title']}" for c in chapters)
        + "\n\nGiọng nói lấy từ microphone cùng lượt quay; tour văn bản được ghi nhãn và tăng tốc2x. Clip gốc1x giữ nguyên.\n"
    )
    print(
        json.dumps(
            dict(
                video=receipt["final_video"],
                duration_s=receipt["duration_s"],
                decode_check="PASS",
                coverage=coverage["visited"],
            ),
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
