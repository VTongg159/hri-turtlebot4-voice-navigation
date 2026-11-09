#!/usr/bin/env python3
"""Export the verified public deliverables without private raw microphone files."""

import hashlib
import json
from pathlib import Path
import shutil

import cv2

from tb4_voice_navigation.semantic_map import SemanticMap

ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "deliverables/pairslab_demo_20261109"
DEST = ROOT / "submission"
PACKAGE = ROOT / "src/tb4_voice_navigation"


def copy(source, target):
    """Keep the export explicit; never copy the raw recording directory."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main():
    render = json.loads((FILM / "render_manifest.json").read_text())
    assert render["decode_check"] == "PASS" and render["coverage"]["passed"]
    assert not (FILM / "decode_check.log").read_text().strip()
    video = ROOT / render["final_video"]
    assert hashlib.sha256(video.read_bytes()).hexdigest() == render["final_sha256"]
    for row in render["coverage"]["results"]:
        assert row["terminal"]["state"] == "SUCCEEDED"
        assert row["arrival_pose"]["inside_region"]
        assert any(
            result["action_status"] == 4 and result["error_code"] == 0
            for result in row["action_results"]
        )
    for name in ("pairs_lab.pgm", "pairs_lab.yaml", "pairs_provenance.yaml"):
        copy(PACKAGE / "maps" / name, DEST / "maps" / name)
    copy(PACKAGE / "config/pairs_regions.yaml", DEST / "config/pairs_regions.yaml")
    copy(ROOT / "docs/pairslab_segmentation.png", DEST / "maps/pairslab_segmentation.png")
    semantic = SemanticMap(DEST / "config/pairs_regions.yaml")
    assert set(semantic.regions) == set("ABCDEF")
    assert cv2.imwrite(str(DEST / "maps/pairs_lab_original.png"), semantic.map.image)
    goals = {
        key: {
            "valid": region["valid"],
            "goal": region["goal"],
            "clearance_m": semantic.validate_goal(region, region["goal"]),
            "min_clearance_m": semantic.min_clearance,
        }
        for key, region in semantic.regions.items()
    }
    evidence = DEST / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "goals_validation.json").write_text(
        json.dumps(goals, indent=2, ensure_ascii=False) + "\n"
    )
    for name in (
        "navigation.json",
        "pipeline.json",
        "pipeline_events.json",
        "scan_alignment.json",
        "voice_acceptance.json",
        "video_acceptance.json",
    ):
        copy(ROOT / "evidence/pairslab_redesign" / name, evidence / name)
    # Historical scene tests are labelled rather than mixed with current-scene runs.
    for name in (
        "live_pipeline_results.json",
        "live_failures_results.json",
        "unreachable_result.json",
    ):
        copy(ROOT / "evidence" / name, evidence / "historical_campus" / name)
    for name in ("coverage.json", "navigation_results.json", "navigation_resume_results.json"):
        copy(FILM / name, evidence / name)
    copy(FILM / "render_manifest.json", evidence / "render_manifest.json")
    copy(FILM / "voice/results.json", evidence / "filmed_voice_attempts.json")
    copy(FILM / "voice/filmed_acceptance.json", evidence / "filmed_voice_acceptance.json")
    copy(ROOT / "evidence/publication/validation.json", evidence / "source_validation.json")
    copy(video, DEST / "PAIRS_Lab_Demo_1080p.mp4")
    copy(FILM / "CHAPTERS.md", DEST / "CHAPTERS.md")
    for path in sorted((FILM / "stills").glob("*.png")):
        copy(path, DEST / "figures" / path.name)
    from render_occupancy_figure import main as render_occupancy

    render_occupancy()
    files = {
        str(path.relative_to(DEST)): {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(DEST.rglob("*"))
        if path.is_file() and path.name not in {"manifest.json", "README.md"}
    }
    manifest = {
        "scene": "PAIRS Robotics Research Lab",
        "map_source": "collision-derived prior; not SLAM",
        "segmentation": "supervised semantic polygons; watershed suggestions not quantitatively evaluated",
        "voice_in_video": "one real microphone command -> ASR -> parser A -> real simulated Nav2 success",
        "voice_attempts_in_filmed_session": "2 recordings: NO_SPEECH then success; final clip uses success",
        "tour": "labelled keyboard transcripts, 2x playback, resumed after localization loss",
        "video_duration_s": render["duration_s"],
        "raw_files": "kept locally; raw WAV/video not included in public export",
        "latex": "../docs/bao_cao_bai7.tex; placeholders only; not compiled",
        "files": files,
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Exported {len(files)} checked files to {DEST}")


if __name__ == "__main__":
    main()
