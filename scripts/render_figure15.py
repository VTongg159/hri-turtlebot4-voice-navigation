#!/usr/bin/env python3
"""Arrange existing Gazebo arrival screenshots without altering their pixels."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "submission/figures"
    panels = [
        ("arrival_B.png", "(a) B — Manipulation Lab", 24, 24),
        ("arrival_D.png", "(b) D — HRI Lab / Unitree G1", 1148, 24),
        ("arrival_F.png", "(c) F — TurtleBot Lab", 24, 904),
        ("arrival_E.png", "(d) E — Quadruped Lab / Unitree Go2", 1148, 904),
        ("tour_complete.png", "(e) C — Lobby / Tour complete", 586, 1784),
    ]
    canvas = Image.new("RGB", (2272, 2664), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    sources = []
    for name, label, x, y in panels:
        source = folder / name
        image = Image.open(source).convert("RGB")
        assert image.size == (1100, 800)
        canvas.paste(image, (x, y))
        draw.text((x, y + 814), label, font=font, fill="black")
        assert np.array_equal(np.asarray(image), np.asarray(canvas.crop((x, y, x + 1100, y + 800))))
        sources.append(
            dict(
                file="figures/" + name,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                panel=label,
                output_bounds=[x, y, x + 1100, y + 800],
                pixel_identical=True,
            )
        )
    target = folder / "figure15_room_arrivals.png"
    canvas.save(target)
    receipt = dict(
        kind="report montage of five existing Gazebo screenshots; labels outside screenshots",
        output="figures/" + target.name,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        sources=sources,
        navigation_evidence=[
            "evidence/navigation_results.json",
            "evidence/navigation_resume_results.json",
            "evidence/coverage.json",
        ],
        note="Tour uses keyboard transcripts; E and final C belong to the resumed tour after localization recovery. SUCCEEDED is recorded in ROS results, not overlaid onto screenshots.",
    )
    (ROOT / "submission/evidence/figure15_sources.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    )
    print("PASS: all five screenshot panels retain their original pixels")
    print(target)


if __name__ == "__main__":
    main()
