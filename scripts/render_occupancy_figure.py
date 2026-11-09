#!/usr/bin/env python3
"""Plot the unchanged occupancy grid with a legend and configured spawn pose."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import yaml

from tb4_voice_navigation.semantic_map import SemanticMap

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "submission/config/pairs_regions.yaml"
    semantic = SemanticMap(source)
    metadata = yaml.safe_load(source.read_text())
    occupancy = semantic.map
    assert occupancy.origin[2] == 0, "This figure uses an axis-aligned map extent"
    x, y, yaw = metadata["spawn_map"]
    col, row = occupancy.cell(x, y)
    assert occupancy.free[row, col]
    assert yaw == 0, "The start marker points along +x in this scene"

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(11.6, 9.2))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.87, bottom=0.19)
    x0, y0, _ = occupancy.origin
    ax.imshow(
        occupancy.image,
        cmap="gray",
        vmin=0,
        vmax=255,
        interpolation="nearest",
        origin="upper",
        extent=(
            x0,
            x0 + occupancy.width * occupancy.resolution,
            y0,
            y0 + occupancy.height * occupancy.resolution,
        ),
    )
    ax.scatter([x], [y], marker=">", s=160, color="#d52b37", edgecolor="white", zorder=5)
    ax.annotate(
        "START (−11, 0) m\nyaw = 0 rad → +x",
        xy=(x, y),
        xytext=(12, 26),
        textcoords="offset points",
        fontsize=10,
        color="#a31b26",
        arrowprops={"arrowstyle": "-", "color": "#a31b26"},
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.95},
    )
    ax.set_xlabel("x trong hệ map (m)")
    ax.set_ylabel("y trong hệ map (m)")
    ax.set_aspect("equal")
    handles = [
        Patch(facecolor=str(254 / 255), edgecolor="#555555", label="Free — ô trống"),
        Patch(facecolor="black", edgecolor="black", label="Occupied — vật cản"),
        Patch(facecolor=str(205 / 255), edgecolor="#555555", label="Unknown — chưa xác định"),
        Line2D(
            [],
            [],
            marker=">",
            linestyle="none",
            color="#d52b37",
            markersize=10,
            label="START — vị trí xuất phát",
        ),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.53, 0.075), ncol=2)
    fig.suptitle("BẢN ĐỒ OCCUPANCY GỐC — PAIRS LAB", fontsize=18, fontweight="bold", y=0.96)
    fig.text(
        0.53,
        0.91,
        "580 × 420 ô  |  0,05 m/ô  |  origin = (−14,5; −10,5; 0)  |  Chưa tô màu vùng A–F",
        ha="center",
        fontsize=10,
    )
    fig.text(
        0.53,
        0.035,
        "Nguồn: pairs_lab.pgm + YAML; bản đồ prior từ collision geometry, không phải SLAM.\n"
        "Chỉ bổ sung chú giải và START; giữ nguyên các ô occupancy của bản gốc.",
        ha="center",
        fontsize=9,
        color="#4b5563",
    )
    output = ROOT / "submission/maps/pairs_lab_occupancy_annotated.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
