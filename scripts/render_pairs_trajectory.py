#!/usr/bin/env python3
"""Plot recorded TF on the existing segmentation PNG using its map axes geometry."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "submission/evidence/trajectory_pairs"
    samples = [json.loads(line) for line in (folder / "tf_samples.jsonl").read_text().splitlines()]
    results = json.loads((folder / "results.json").read_text())
    assert [r["region"] for r in results] == list("ABDCEF")
    assert all(r["result"] == "SUCCEEDED" and r["inside_region"] for r in results)
    config = yaml.safe_load((ROOT / "submission/config/pairs_regions.yaml").read_text())
    metadata = yaml.safe_load((ROOT / "submission/maps/pairs_lab.yaml").read_text())
    width, height = Image.open(ROOT / "submission/maps/pairs_lab.pgm").size
    background_path = ROOT / "submission/maps/pairslab_segmentation.png"
    background = np.asarray(Image.open(background_path).convert("RGB")).copy()
    assert background.shape == (1650, 2250, 3)
    # The existing PNG comes from map_segmentation.render(), a 15x11 inch figure
    # at 150 dpi, with add_axes([.06,.19,.88,.66]) and equal-aspect imshow.
    # Derive its actual map viewport using Matplotlib itself, not visual guesses.
    reference = plt.figure(figsize=(15, 11), dpi=150)
    ref = reference.add_axes([0.06, 0.19, 0.88, 0.66])
    ref.set_xlim(-0.5, width - 0.5)
    ref.set_ylim(height - 0.5, -0.5)
    ref.set_aspect("equal")
    reference.canvas.draw()
    bounds = ref.get_window_extent().bounds
    left, bottom, viewport_w, viewport_h = bounds
    top = background.shape[0] - bottom - viewport_h
    plt.close(reference)
    x0, y0, theta = metadata["origin"]
    resolution = metadata["resolution"]

    def project(x, y):
        dx, dy = np.asarray(x) - x0, np.asarray(y) - y0
        local_x = np.cos(theta) * dx + np.sin(theta) * dy
        local_y = -np.sin(theta) * dx + np.cos(theta) * dy
        # Continuous pixel centres: c=u/r-.5, v=H-.5-w/r.
        col, row = local_x / resolution - 0.5, height - 0.5 - local_y / resolution
        return left + (col + 0.5) * viewport_w / width, top + (row + 0.5) * viewport_h / height

    # Keep the exact supplied background/map; reserve its footer for the legend.
    background[1400:] = 255
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(15, 11), dpi=150, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(background, interpolation="nearest")
    ax.set_xlim(-0.5, 2249.5)
    ax.set_ylim(1649.5, -0.5)
    ax.axis("off")
    colors = ["#d73027", "#2166ac", "#8e44ad", "#e08214", "#00876c", "#ce2686"]
    legend, stats = [], []
    previous = "START"
    for key, color in zip("ABDCEF", colors):
        rows = [r for r in samples if r["goal"] == key]
        xy = np.array([[r["x"], r["y"]] for r in rows])
        assert len(xy) >= 2
        jumps = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        # Break rather than invent motion across TF gaps/localization jumps.
        breaks = np.where((jumps > 0.5) | (np.diff([r["stamp"] for r in rows]) > 1.0))[0] + 1
        length = float(jumps[jumps <= 0.5].sum())
        for chunk in np.split(xy, breaks):
            if len(chunk) < 2:
                continue
            px, py = project(chunk[:, 0], chunk[:, 1])
            # No interpolation/smoothing or replacement with planned paths.
            ax.plot(px, py, color=color, lw=2.3, alpha=0.9, zorder=8)
            distances = np.r_[0, np.cumsum(np.linalg.norm(np.diff(chunk, axis=0), axis=1))]
            for distance in np.arange(0.9, distances[-1], 2.3):
                i = min(np.searchsorted(distances, distance), len(chunk) - 1)
                j = max(0, np.searchsorted(distances, max(0, distance - 0.3)))
                if i > j:
                    ax.annotate(
                        "",
                        xy=(px[i], py[i]),
                        xytext=(px[j], py[j]),
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, mutation_scale=15),
                        zorder=9,
                    )
        legend.append(Line2D([0], [0], color=color, lw=2.5, label=f"{previous} → {key}"))
        stats.append(
            dict(goal=key, samples=len(rows), measured_length_m=length, discontinuities=len(breaks))
        )
        previous = key
    for region in config["regions"]:
        g = region["goal"]
        px, py = project(g["x"], g["y"])
        ax.scatter(px, py, s=270, facecolors="white", edgecolors="black", lw=1.2, zorder=10)
        ax.text(
            px,
            py,
            region["id"],
            ha="center",
            va="center",
            fontsize=10,
            color="black",
            weight="bold",
            zorder=11,
        )
    sx, sy = project(samples[0]["x"], samples[0]["y"])
    ax.scatter(sx, sy, marker="*", s=280, color="black", edgecolor="white", zorder=12)
    fig.text(
        0.065,
        0.12,
        "Measured trajectory — START → A → B → D → C → E → F",
        fontsize=16,
        weight="bold",
        color="black",
    )
    fig.legend(
        handles=legend,
        loc="lower left",
        bbox_to_anchor=(0.06, 0.06),
        ncol=6,
        frameon=False,
        fontsize=12,
        handlelength=2.4,
        columnspacing=1.4,
    )
    fig.text(
        0.065,
        0.035,
        "Source: map → base_link TF (5 Hz) · Six Nav2 goals: SUCCEEDED · Arrows: travel direction",
        fontsize=11,
        color="#444444",
    )
    fig.text(
        0.065,
        0.012,
        "Measured localization trajectory in Gazebo; no smoothing. Occupancy prior derived from world collision geometry.",
        fontsize=10,
        color="#444444",
    )
    target = ROOT / "submission/figures/trajectory_pairs.png"
    fig.savefig(target, dpi=150)
    plt.close(fig)
    receipt = dict(
        figure="figures/trajectory_pairs.png",
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source="Measured map->base_link TF in a new Nav2 run; not planned paths or video tracing",
        background="maps/pairslab_segmentation.png",
        route=list("ABDCEF"),
        total_samples=len(samples),
        segments=stats,
        map_geometry=dict(
            width=width, height=height, resolution=resolution, origin=metadata["origin"]
        ),
        background_map_viewport=dict(left=left, top=top, width=viewport_w, height=viewport_h),
        formula="u=cos(theta)*(x-x0)+sin(theta)*(y-y0); w=-sin(theta)*(x-x0)+cos(theta)*(y-y0); c=u/r-0.5; v=H-0.5-w/r",
        editing="Original background footer replaced with legend; exact map pixels retained underneath trajectory. No smoothing; gaps >0.5m or >1s broken.",
    )
    (folder / "figure_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(target)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
