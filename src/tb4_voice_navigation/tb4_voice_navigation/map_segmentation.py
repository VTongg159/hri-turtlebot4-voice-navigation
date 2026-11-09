"""Render actual occupancy, edit polygons/goals, export watershed suggestions."""

import argparse
from pathlib import Path
import cv2
import numpy as np
import yaml
from .semantic_map import SemanticMap, MapError

COLORS = ["#3b82f6", "#14b8a6", "#94a3b8", "#f59e0b", "#a78bfa", "#ec4899"]


def render(s, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from matplotlib.colors import to_rgb

    plt.rcParams["font.family"] = "DejaVu Sans"
    m = s.map
    data = yaml.safe_load(s.path.read_text())
    fig = plt.figure(figsize=(15, 11), facecolor="#f3f6fa")
    ax = fig.add_axes([0.06, 0.19, 0.88, 0.66])
    base = np.ones((m.height, m.width, 3))
    base[m.unknown] = (0.89, 0.91, 0.94)
    base[m.occupied] = (0.13, 0.18, 0.24)
    ax.imshow(base, interpolation="nearest")
    labels = {
        k: r.get("label_pixel", np.mean(r["polygon_pixels"], axis=0)) for k, r in s.regions.items()
    }
    for i, (key, r) in enumerate(s.regions.items()):
        color = r.get("display_color", COLORS[i % len(COLORS)])
        overlay = np.zeros((m.height, m.width, 4))
        area = r["mask"] & m.free
        overlay[area, :3] = to_rgb(color)
        overlay[area, 3] = 0.17
        ax.imshow(overlay, interpolation="nearest")
        ax.add_patch(
            Polygon(
                r["polygon_pixels"],
                closed=True,
                fill=False,
                edgecolor=color,
                linewidth=1.4,
                alpha=0.7,
            )
        )
        if r["valid"]:
            g = r["goal"]
            c, row = m.to_pixel(g["x"], g["y"])
            ax.scatter(c, row, s=230, color=color, edgecolor="white", linewidth=2, zorder=5)
            ax.text(
                c,
                row,
                key,
                color="white",
                ha="center",
                va="center",
                weight="bold",
                fontsize=10,
                zorder=6,
            )
            angle = g["yaw"] - m.origin[2]
            ax.annotate(
                "",
                xy=(c + 12 * np.cos(angle), row - 12 * np.sin(angle)),
                xytext=(c, row),
                arrowprops=dict(arrowstyle="->", color=color, lw=2),
            )
        c, row = labels.get(key, np.mean(r["polygon_pixels"], axis=0))
        ax.text(
            c,
            row,
            f"{key}  /  {r['name']}",
            ha="center",
            va="center",
            fontsize=11,
            weight="bold",
            color="#172b43",
            bbox=dict(boxstyle="round,pad=.5", facecolor="white", alpha=0.94, edgecolor="none"),
        )
    spawn = data.get("spawn_map", [-5.5, 0, 0])
    c, row = m.to_pixel(*spawn[:2])
    ax.scatter(c, row, marker="^", s=180, color="#172b43", edgecolor="white", zorder=7)
    ax.text(c, row - 9, "START", fontsize=8, ha="center", weight="bold")
    xmin, ymin = m.to_map(0, m.height - 1)
    xmax, ymax = m.to_map(m.width - 1, 0)
    step = max(1.0, float(np.ceil((xmax - xmin) / 8)))
    xs = np.arange(np.ceil(xmin / step) * step, xmax, step)
    ys = np.arange(np.ceil(ymin / step) * step, ymax, step)
    ax.set_xticks([m.to_pixel(x, 0)[0] for x in xs], labels=list(map(str, xs)))
    ax.set_yticks([m.to_pixel(0, y)[1] for y in ys], labels=list(map(str, ys)))
    ax.set_xlabel("x / mét", color="#52657b")
    ax.set_ylabel("y / mét", color="#52657b")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, labelcolor="#52657b")
    for y, text, size, color in [
        (0.94, data.get("scene_name", "SEMANTIC CAMPUS"), 30, "#172b43"),
        (0.90, "Bài thực hành 7  ·  TurtleBot 4 / ROS 2 Jazzy / Gazebo Harmonic", 13, "#52657b"),
        (
            0.135,
            f"{len(s.regions) - 1} PHÒNG NGHIÊN CỨU   /   1 SẢNH   /   {len(s.regions)} ĐÍCH ĐIỀU HƯỚNG",
            14,
            "#172b43",
        ),
        (
            0.10,
            f"{data.get('world_size_m', [14, 10])[0]} × {data.get('world_size_m', [14, 10])[1]} m  •  Lưới {m.resolution:g} m/ô  •  Goal có clearance và kết nối",
            12,
            "#52657b",
        ),
        (
            0.065,
            "Chấm tròn: goal đã kiểm tra  |  Mũi tên: yaw đích  |  Màu nền: polygon ∩ ô free",
            11,
            "#52657b",
        ),
        (
            0.035,
            "Nguồn occupancy: collision của world; không phải SLAM. Nhãn phòng do người dùng định nghĩa.",
            10,
            "#52657b",
        ),
    ]:
        fig.text(
            0.065, y, text, fontsize=size, color=color, weight="bold" if size >= 14 else "normal"
        )
    fig.savefig(output, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def automatic(m, output):
    distance = cv2.distanceTransform(m.free.astype(np.uint8), cv2.DIST_L2, 5)
    peaks = (distance > max(2, 0.40 * distance.max())).astype(np.uint8)
    peaks = cv2.morphologyEx(peaks, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    _, markers = cv2.connectedComponents(peaks)
    markers = markers.astype(np.int32) + 1
    markers[m.free & (peaks == 0)] = 0
    cv2.watershed(cv2.cvtColor(m.image, cv2.COLOR_GRAY2BGR), markers)
    markers[~m.free] = 0
    np.save(output, markers)
    print("Watershed suggestions only; manual review required.")


def edit(filename):
    s = SemanticMap(filename)
    points = []
    data = yaml.safe_load(Path(filename).read_text())
    scale = 3

    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x // scale, y // scale])
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.namedWindow("Regions")
    cv2.setMouseCallback("Regions", click)
    print(
        "Left vertex; right undo; n save/name polygon; g edit goal; q quit. Text prompts in terminal."
    )
    while True:
        image = cv2.cvtColor(s.map.image, cv2.COLOR_GRAY2BGR)
        for r in s.regions.values():
            cv2.polylines(image, [np.array(r["polygon_pixels"], np.int32)], True, (150, 90, 20), 1)
        if points:
            cv2.polylines(image, [np.array(points, np.int32)], False, (0, 0, 255), 1)
        cv2.imshow(
            "Regions", cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        )
        key = cv2.waitKey(30) & 255
        if key == ord("q"):
            break
        try:
            if key == ord("n"):
                s.map.polygon_mask(points)
                rid = input("ID: ").strip()
                name = input("Tên: ").strip()
                if not rid or not name:
                    raise MapError("ID/name required")
                aliases = [
                    v.strip() for v in input("Aliases (comma separated): ").split(",") if v.strip()
                ]
                region = dict(
                    id=rid,
                    name=name,
                    aliases=aliases,
                    polygon_pixels=points.copy(),
                    goal=s.select_goal(points),
                )
                data["regions"] = [r for r in data["regions"] if str(r["id"]) != rid] + [region]
                points.clear()
            elif key == ord("g"):
                rid = input("Region ID: ").strip()
                region = s.lookup(rid)
                x, y, yaw = map(float, input("map x y yaw: ").split())
                goal = dict(x=x, y=y, yaw=yaw)
                s.validate_goal(region, goal)
                next(r for r in data["regions"] if str(r["id"]) == rid)["goal"] = goal
            else:
                continue
            Path(filename).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
            s = SemanticMap(filename)
        except (ValueError, KeyError) as exc:
            print("Rejected:", exc)
    cv2.destroyAllWindows()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("regions")
    p.add_argument("--output", default="segmented_map.png")
    p.add_argument("--edit", action="store_true")
    p.add_argument("--auto", action="store_true")
    args = p.parse_args()
    if args.edit:
        edit(args.regions)
    elif args.auto:
        automatic(SemanticMap(args.regions).map, args.output)
    else:
        s = SemanticMap(args.regions)
        render(s, args.output)
        print(
            yaml.safe_dump(
                {
                    k: dict(
                        valid=r["valid"],
                        goal=r["goal"],
                        clearance_m=s.validate_goal(r, r["goal"]) if r["valid"] else None,
                        reason=r["invalid_reason"],
                    )
                    for k, r in s.regions.items()
                },
                allow_unicode=True,
                sort_keys=False,
            )
        )


if __name__ == "__main__":
    main()
