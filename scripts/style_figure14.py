#!/usr/bin/env python3
"""Restyle Figure 14's secondary panel while preserving the Gazebo crop exactly."""

import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def main():
    folder = ROOT / "submission/figures"
    original = folder / "figure14_voice_video_original.png"
    video = ROOT / "submission/PAIRS_Lab_Demo_1080p.mp4"
    proof_path = ROOT / "submission/evidence/figure14_video_frame.json"
    expected = json.loads(proof_path.read_text())
    if original.exists():
        assert (
            hashlib.sha256(original.read_bytes()).hexdigest() == expected["original_frame_sha256"]
        )
    else:
        archive = ROOT / "deliverables/pairslab_demo_20261109/PAIRS_Lab_Demo_original_style.mp4"
        if archive.exists():
            video = archive
        assert hashlib.sha256(video.read_bytes()).hexdigest() == expected["source_video_sha256"], (
            "Figure 14 needs the original video version listed in its evidence JSON"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                "139",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(original),
            ],
            check=True,
        )
    source = Image.open(original).convert("RGB")
    assert source.size == (1920, 1080)
    # These are the actual application pixels inside the video composition.
    bounds = (0, 75, 1280, 1005)
    application = source.crop(bounds)
    output = Image.new("RGB", (1920, 930), "white")
    output.paste(application, (0, 0))
    draw = ImageDraw.Draw(output)
    draw.line((1280, 0, 1280, 930), fill="#bcbcbc", width=1)
    draw.rectangle((1281, 0, 1919, 43), fill="#eeeeee")
    draw.line((1281, 43, 1919, 43), fill="#c8c8c8", width=1)

    def text(x, y, value, size=21, bold=False, shade=30):
        draw.text(
            (x, y),
            value,
            fill=(shade, shade, shade),
            font=ImageFont.truetype(BOLD if bold else FONT, size),
        )

    text(1304, 9, "Navigation", 23)
    text(1304, 66, "Goal: A — UAV Lab", 24, bold=True)
    text(1304, 110, "Map", 19, shade=85)
    # Keep the map, goal labels, robot marker and recorded trail at the same
    # locations as the source frame; only remove their chromatic styling.
    map_image = source.crop((1305, 220, 1895, 647)).convert("L").convert("RGB")
    output.paste(map_image, (1305, 145))
    draw = ImageDraw.Draw(output)
    text(1304, 583, "Triangle: robot     Line: recorded trajectory", 17, shade=90)
    draw.line((1304, 618, 1896, 618), fill="#d0d0d0", width=1)
    text(1304, 639, "Nav2 status", 20, shade=80)
    text(1495, 637, "SUCCEEDED", 24, bold=True)
    text(1304, 688, "ASR transcript", 20, shade=80)
    text(1304, 719, "Đi đến phòng UAV", 24)
    text(1304, 772, "Robot pose (map)", 20, shade=80)
    text(1535, 772, "(−8.91, 3.44) m", 21)
    draw.line((1304, 820, 1896, 820), fill="#d0d0d0", width=1)
    text(1304, 842, "Video: 02:19", 19, shade=80)
    text(1304, 875, "09/11/2026 · 16:33:13", 19, shade=80)

    assert np.array_equal(np.asarray(application), np.asarray(output.crop((0, 0, 1280, 930))))
    secondary = np.asarray(output)[:, 1280:]
    assert np.array_equal(secondary[:, :, 0], secondary[:, :, 1])
    assert np.array_equal(secondary[:, :, 1], secondary[:, :, 2])
    target = folder / "figure14_voice_video_UAV_succeeded.png"
    output.save(target)
    proof = ROOT / "submission/evidence/figure14_video_frame.json"
    receipt = json.loads(proof.read_text())
    receipt.update(
        source_kind="restyled presentation of the same 02:19 video frame; original Gazebo pixels preserved, secondary panel monochrome",
        original_frame="figures/" + original.name,
        original_frame_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        frame_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        restyled=True,
        output_dimensions=[1920, 930],
        native_application_crop={
            "source_bounds": list(bounds),
            "output_bounds": [0, 0, 1280, 930],
            "pixel_identical": True,
        },
        secondary_panel="white background, black/gray text, grayscale of the original map crop",
        displayed_pose_source="(-8.91, 3.44) m displayed in the original video frame; not substituted from a later trial",
    )
    proof.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print("PASS: exact Gazebo pixels retained; all secondary pixels grayscale")
    print(target)


if __name__ == "__main__":
    main()
