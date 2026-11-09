#!/usr/bin/env python3
"""Draw the pixel/map convention used by coordinate_utils, with a checked example."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import yaml

from tb4_voice_navigation.semantic_map import OccupancyMap

ROOT = Path(__file__).resolve().parents[1]


def main():
    m = OccupancyMap(ROOT / "submission/maps/pairs_lab.yaml")
    assert m.origin[2] == 0, "The illustrated PAIRS map has zero origin rotation"
    c, v = 109, 136
    x, y = m.to_map(c, v)
    assert all(abs(a - b) < 1e-10 for a, b in zip(m.to_pixel(x, y), (c, v)))
    assert abs(x + 9.025) < 1e-10 and abs(y - 3.675) < 1e-10
    origin = yaml.safe_load((ROOT / "submission/maps/pairs_lab.yaml").read_text())["origin"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig = plt.figure(figsize=(16, 10), facecolor="white")
    left = fig.add_axes((0.055, 0.33, 0.40, 0.49))
    right = fig.add_axes((0.555, 0.33, 0.40, 0.49))
    blue, green, red = "#1769aa", "#12816c", "#d02f45"

    def arrow(ax, start, end, color):
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={"arrowstyle": "-|>", "color": color, "lw": 2, "mutation_scale": 15},
        )

    left.add_patch(
        Rectangle((0, 0), m.width, m.height, facecolor="#f1f6fb", edgecolor=blue, lw=1.6)
    )
    for col in range(0, m.width, 58):
        left.plot((col, col), (0, m.height), color="#d0ddec", lw=0.7)
    for row in range(0, m.height, 42):
        left.plot((0, m.width), (row, row), color="#d0ddec", lw=0.7)
    # This axes uses screen-like downward y, while its numeric limits are explicit.
    left.invert_yaxis()
    arrow(left, (0, -18), (m.width, -18), blue)
    arrow(left, (-18, 0), (-18, m.height), blue)
    left.text(320, -35, "c (cột) tăng →", color=blue, ha="center", va="bottom")
    left.text(-34, 240, "v (hàng) tăng ↓", color=blue, rotation=90, ha="center", va="center")
    left.scatter([0], [0], s=45, color=blue, zorder=4)
    left.text(0, -78, "Góc trên trái của ảnh", color=blue, weight="bold")
    left.plot((c + 0.5, c + 0.5), (0, v + 0.5), "--", color=red, lw=1.2)
    left.plot((0, c + 0.5), (v + 0.5, v + 0.5), "--", color=red, lw=1.2)
    left.scatter([c + 0.5], [v + 0.5], color=red, s=80, zorder=5)
    left.annotate(
        "P: tâm pixel (c, v) = (109, 136)",
        (c + 0.5, v + 0.5),
        (c + 65, v + 55),
        color=red,
        fontsize=11,
        arrowprops={"arrowstyle": "-", "color": red},
    )
    left.text(m.width / 2, m.height + 35, "W = 580 cột; H = 420 hàng", ha="center")
    left.text(
        m.width / 2,
        m.height + 66,
        "Tâm pixel đầu: cách mép trái và mép trên ½ ô",
        ha="center",
        fontsize=10,
    )
    left.set_xlim(-65, m.width + 15)
    left.set_ylim(m.height + 88, -95)
    left.set_aspect("equal")
    left.axis("off")

    x0, y0, _ = origin
    xmax, ymax = x0 + m.width * m.resolution, y0 + m.height * m.resolution
    right.add_patch(
        Rectangle((x0, y0), xmax - x0, ymax - y0, facecolor="#edf8f3", edgecolor=green, lw=1.6)
    )
    for xx in (-10, -5, 5, 10):
        right.plot((xx, xx), (y0, ymax), color="#cbe2d7", lw=0.7)
    for yy in (-10, -5, 5, 10):
        right.plot((x0, xmax), (yy, yy), color="#cbe2d7", lw=0.7)
    arrow(right, (x0, 0), (xmax + 1.4, 0), green)
    arrow(right, (0, y0), (0, ymax + 1.4), green)
    right.text(xmax + 1.5, -1.0, "x (m) →", color=green, ha="right")
    right.text(0.8, ymax + 1.0, "y (m) ↑", color=green)
    right.scatter([0], [0], color=green, s=45, zorder=5)
    right.text(0.6, -1.6, "Omap = (0, 0)", color=green, fontsize=10)
    right.plot((x, x), (0, y), "--", color=red, lw=1.2)
    right.plot((0, x), (y, y), "--", color=red, lw=1.2)
    right.scatter([x], [y], color=red, s=80, zorder=5)
    right.annotate(
        "P = (−9,025; 3,675) m",
        (x, y),
        (-13.6, 7.7),
        color=red,
        fontsize=11,
        arrowprops={"arrowstyle": "-", "color": red},
    )
    right.scatter([x0], [y0], color="#965b0b", marker="s", s=55, zorder=6)
    right.annotate(
        "Origin trong map.yaml\n(x₀, y₀) = (−14,5; −10,5) m",
        (x0, y0),
        (-13.6, -14.0),
        fontsize=10,
        color="#965b0b",
        arrowprops={"arrowstyle": "-", "color": "#965b0b"},
    )
    right.text(0, ymax + 3.3, "Trục y của map hướng lên", color=green, ha="center", weight="bold")
    right.set_xlim(-17.5, 17.5)
    right.set_ylim(-15, 15)
    right.set_aspect("equal")
    right.axis("off")

    fig.suptitle("QUY ƯỚC TỌA ĐỘ PIXEL VÀ HỆ MAP", fontsize=21, fontweight="bold", y=0.96)
    fig.text(0.255, 0.865, "1. ẢNH OCCUPANCY", color=blue, ha="center", fontsize=15, weight="bold")
    fig.text(
        0.755, 0.865, "2. TỌA ĐỘ ROS / MAP", color=green, ha="center", fontsize=15, weight="bold"
    )
    fig.text(0.50, 0.60, "→", fontsize=34, ha="center", color="#556173")
    fig.text(
        0.50,
        0.54,
        "Đảo trục dọc\n+ tâm ô\n+ resolution",
        ha="center",
        va="center",
        fontsize=10,
        color="#556173",
    )
    fig.text(
        0.5,
        0.255,
        r"$\theta_0 = 0:\qquad x = x_0 + (c + 0.5)\,r"
        r"\qquad\qquad y = y_0 + (H - v - 0.5)\,r$",
        ha="center",
        fontsize=17,
        bbox={"boxstyle": "round,pad=0.7", "facecolor": "#f1f4f8", "edgecolor": "#d9e0ea"},
    )
    fig.text(
        0.5,
        0.16,
        "PAIRS Lab: r = 0,05 m/ô; θ₀ = 0 rad. Hai điểm P biểu diễn cùng một vị trí.",
        ha="center",
        fontsize=12,
    )
    fig.text(
        0.5,
        0.105,
        "Lưới trái chỉ minh họa quy ước, không vẽ đầy đủ 580 × 420 ô.\n"
        "Origin khai báo trong YAML (góc dưới trái lưới) khác gốc Omap. +0,5 xác định tâm ô, tránh lệch nửa pixel.",
        ha="center",
        fontsize=10,
        color="#556173",
    )
    output = ROOT / "submission/figures/pairs_lab_pixel_map_coordinates"
    output.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output.with_suffix("." + extension), dpi=220, facecolor="white")
    plt.close(fig)
    print(output.with_suffix(".png"))


if __name__ == "__main__":
    main()
