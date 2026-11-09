#!/usr/bin/env python3
"""Generate a furnished multiroom Gazebo world and its collision-derived map.

The occupancy raster is a model-derived prior, NOT a recorded SLAM result.
All obstacles that intersect the robot height are rasterised from the very
same primitive geometry used for SDF collision. No external assets/network.
"""

from pathlib import Path
import math
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
RES = 0.05
ORIGIN = (-7.5, -5.5, 0.0)
W, H = 300, 220
obstacles = []
scene = []

PALETTE = {
    "wall": (0.83, 0.85, 0.89, 1),
    "trim": (0.15, 0.22, 0.30, 1),
    "wood": (0.64, 0.41, 0.23, 1),
    "white": (0.92, 0.94, 0.95, 1),
    "blue": (0.18, 0.43, 0.66, 1),
    "green": (0.26, 0.52, 0.39, 1),
    "teal": (0.12, 0.55, 0.57, 1),
    "orange": (0.86, 0.42, 0.19, 1),
    "leaf": (0.15, 0.40, 0.22, 1),
    "pot": (0.45, 0.26, 0.18, 1),
}


def box(name, x, y, z, sx, sy, sz, color, yaw=0.0, collision=True):
    scene.append(
        dict(
            name=name,
            x=x,
            y=y,
            z=z,
            size=(sx, sy, sz),
            color=color,
            yaw=yaw,
            kind="box",
            collision=collision,
        )
    )
    if collision and z - sz / 2 < 0.38 and z + sz / 2 > 0.03:
        obstacles.append(scene[-1])


def cylinder(name, x, y, z, radius, length, color, collision=True):
    scene.append(
        dict(
            name=name,
            x=x,
            y=y,
            z=z,
            radius=radius,
            length=length,
            color=color,
            yaw=0.0,
            kind="cylinder",
            collision=collision,
        )
    )
    if collision and z - length / 2 < 0.38 and z + length / 2 > 0.03:
        obstacles.append(scene[-1])


def wall(name, x, y, sx, sy):
    box(name, x, y, 0.7, sx, sy, 1.4, "wall")
    box(name + "_cap", x, y, 1.415, sx + 0.025, sy + 0.025, 0.045, "trim", collision=False)
    box(name + "_skirting", x, y, 0.075, sx + 0.018, sy + 0.018, 0.15, "trim")


def desk(name, x, y, sx=1.15, sy=0.62, color="wood"):
    box(name + "_top", x, y, 0.74, sx, sy, 0.07, color)
    for dx in [-sx / 2 + 0.07, sx / 2 - 0.07]:
        for dy in [-sy / 2 + 0.07, sy / 2 - 0.07]:
            box(name + f"_leg_{dx}_{dy}", x + dx, y + dy, 0.35, 0.07, 0.07, 0.70, "trim")
    # Conservative footprint: tabletop overhang is not projected as a solid wall.
    # Chairs/legs and all other low collision geometry are projected exactly.


def chair(name, x, y, color="blue", yaw=0):
    box(name + "_base", x, y, 0.22, 0.42, 0.42, 0.44, color, yaw)
    box(
        name + "_back",
        x - math.sin(yaw) * 0.19,
        y + math.cos(yaw) * 0.19,
        0.55,
        0.44,
        0.07,
        0.45,
        color,
        yaw,
    )


def plant(name, x, y):
    cylinder(name + "_pot", x, y, 0.20, 0.24, 0.4, "pot")
    cylinder(name + "_foliage", x, y, 0.60, 0.33, 0.47, "leaf", collision=False)
    for dx, dy in [(-0.20, 0), (0.18, 0.12), (0, -0.2)]:
        cylinder(name + f"_leaf_{dx}", x + dx, y + dy, 0.78, 0.16, 0.16, "green", collision=False)


# Floor panels are visual-only; the ground plane provides collision.
box("hall_floor", 0, 0, 0.012, 13.8, 2.25, 0.02, (0.84, 0.86, 0.86, 1), collision=False)
for name, x, y, color in [
    ("classroom", -3.5, 3.05, (0.87, 0.91, 0.96, 1)),
    ("laboratory", 3.5, 3.05, (0.84, 0.93, 0.92, 1)),
    ("meeting", -3.5, -3.05, (0.95, 0.90, 0.81, 1)),
    ("lounge", 3.5, -3.05, (0.90, 0.88, 0.95, 1)),
]:
    box(name + "_floor", x, y, 0.012, 6.8, 3.65, 0.02, color, collision=False)
# Hall inlays and entrance mats help spatial orientation without obstacles.
for x in np.arange(-6, 7, 1):
    box(
        f"hall_inlay_{x}",
        float(x),
        0,
        0.024,
        0.028,
        2.15,
        0.006,
        (0.69, 0.73, 0.75, 1),
        collision=False,
    )
for x in [-3.5, 3.5]:
    for y in [-1.2, 1.2]:
        box(
            f"door_mat_{x}_{y}",
            x,
            y,
            0.026,
            1.35,
            0.55,
            0.008,
            (0.25, 0.34, 0.43, 1),
            collision=False,
        )
# Exterior and centre partitions; 1.5m clear door openings.
wall("north", 0, 5, 14, 0.16)
wall("south", 0, -5, 14, 0.16)
wall("west", -7, 0, 0.16, 10)
wall("east", 7, 0, 0.16, 10)
for y in [-1.2, 1.2]:
    for idx, (a, b) in enumerate([(-7, -4.25), (-2.75, 2.75), (4.25, 7)]):
        wall(f"hall_wall_{y}_{idx}", (a + b) / 2, y, b - a, 0.14)
for y in [-3.1, 3.1]:
    wall(f"partition_{y}", 0, y, 0.14, 3.8)
# Blue/teal panels above the room walls, decorative, no phantom occupancy.
for x in [-3.5, 3.5]:
    for y in [-1.2, 1.2]:
        box(
            f"lintel_{x}_{y}",
            x,
            y,
            1.55,
            1.5,
            0.14,
            0.20,
            "blue" if x < 0 else "teal",
            collision=False,
        )
# Classroom: three rows, two desks per row, teaching board and storage.
for row, y in enumerate([2.1, 3.25, 4.35]):
    for col, x in enumerate([-5.65, -1.4]):
        desk(f"class_desk_{row}_{col}", x, y, 1.25, 0.55)
        chair(f"class_chair_{row}_{col}", x, y - 0.48)
box("teaching_board", -6.88, 3.05, 0.97, 0.035, 2.1, 0.65, "green", collision=False)
box("class_storage", -3.6, 4.65, 0.45, 1.8, 0.5, 0.9, "wood")
# Lab: peripheral workbenches, stools, a central island, low cabinets.
for i, y in enumerate([2.0, 3.3, 4.4]):
    desk(f"lab_bench_{i}", 6.25, y, 1.1, 0.7, "white")
    chair(f"lab_stool_{i}", 5.40, y, "teal", math.pi / 2)
box("lab_island", 3.35, 3.6, 0.43, 1.5, 0.8, 0.86, "white")
box("lab_island_surface", 3.35, 3.6, 0.89, 1.6, 0.9, 0.08, "trim", collision=False)
box("lab_cabinet", 1.0, 4.6, 0.5, 1.2, 0.55, 1.0, "teal")
# Meeting room with long table and chairs; entrances remain clear.
desk("meeting_table", -3.5, -3.5, 2.65, 0.9)
for i, x in enumerate([-4.5, -3.5, -2.5]):
    chair(f"meeting_north_{i}", x, -2.75, "orange", math.pi)
    chair(f"meeting_south_{i}", x, -4.25, "orange")
box("meeting_screen", -0.10, -3.5, 1.0, 0.035, 1.8, 0.7, "trim", collision=False)
# Lounge sofas, coffee table, reception counter.
box("lounge_sofa_east", 6.3, -3.4, 0.30, 0.85, 2.2, 0.6, "blue")
box("lounge_sofa_back", 6.70, -3.4, 0.65, 0.15, 2.2, 0.75, "blue")
box("lounge_sofa_south", 4.1, -4.45, 0.3, 2.3, 0.8, 0.6, "teal")
box("lounge_sofa_south_back", 4.1, -4.80, 0.65, 2.3, 0.12, 0.75, "teal")
cylinder("coffee_table", 4.5, -3.3, 0.23, 0.48, 0.46, "wood")
box("reception", 1.0, -3.7, 0.5, 0.7, 1.6, 1.0, "white")
for i, (x, y) in enumerate(
    [
        (-6.45, 4.45),
        (-0.65, 4.45),
        (6.4, 4.5),
        (0.65, 1.85),
        (-6.45, -4.45),
        (-0.65, -4.45),
        (6.35, -1.9),
        (1.0, -4.65),
    ]
):
    plant(f"plant_{i}", x, y)
# Hall benches fit outside the central 1.5m travel lane.
for i, x in enumerate([-5.9, 5.9]):
    box(f"hall_bench_{i}", x, -0.83, 0.22, 1.05, 0.38, 0.44, "wood")

sdf = ET.Element("sdf", version="1.9")
world = ET.SubElement(sdf, "world", name="semantic_campus")
physics = ET.SubElement(world, "physics", name="physics", type="ignored")
ET.SubElement(physics, "max_step_size").text = "0.001"
ET.SubElement(physics, "real_time_factor").text = "1.0"
for filename, name in [
    ("gz-sim-physics-system", "gz::sim::systems::Physics"),
    ("gz-sim-user-commands-system", "gz::sim::systems::UserCommands"),
    ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
    ("gz-sim-sensors-system", "gz::sim::systems::Sensors"),
    ("gz-sim-imu-system", "gz::sim::systems::Imu"),
]:
    plugin = ET.SubElement(world, "plugin", filename=filename, name=name)
    if name.endswith("Sensors"):
        ET.SubElement(plugin, "render_engine").text = "ogre2"
scene_node = ET.SubElement(world, "scene")
ET.SubElement(scene_node, "ambient").text = ".65 .65 .65 1"
ET.SubElement(scene_node, "background").text = ".88 .92 .96 1"
ET.SubElement(scene_node, "shadows").text = "true"
light = ET.SubElement(world, "light", name="sun", type="directional")
ET.SubElement(light, "pose").text = "0 0 12 0 0 0"
ET.SubElement(light, "direction").text = "-.4 -.3 -1"
ET.SubElement(light, "diffuse").text = ".95 .95 .92 1"
ET.SubElement(light, "specular").text = ".2 .2 .2 1"
ET.SubElement(light, "cast_shadows").text = "true"
# Plane model.
ground = ET.SubElement(world, "model", name="ground_plane")
ET.SubElement(ground, "static").text = "true"
link = ET.SubElement(ground, "link", name="link")
for tag in ["collision", "visual"]:
    shape = ET.SubElement(link, tag, name=tag)
    plane = ET.SubElement(ET.SubElement(shape, "geometry"), "plane")
    ET.SubElement(plane, "normal").text = "0 0 1"
    ET.SubElement(plane, "size").text = "100 100"
    if tag == "visual":
        mat = ET.SubElement(shape, "material")
        ET.SubElement(mat, "ambient").text = ".94 .94 .93 1"
        ET.SubElement(mat, "diffuse").text = ".94 .94 .93 1"
for obj in scene:
    model = ET.SubElement(world, "model", name=obj["name"])
    ET.SubElement(model, "static").text = "true"
    ET.SubElement(model, "pose").text = f"{obj['x']} {obj['y']} {obj['z']} 0 0 {obj['yaw']}"
    link = ET.SubElement(model, "link", name="link")
    for tag in ["collision", "visual"] if obj["collision"] else ["visual"]:
        node = ET.SubElement(link, tag, name=tag)
        geom = ET.SubElement(node, "geometry")
        primitive = ET.SubElement(geom, obj["kind"])
        if obj["kind"] == "box":
            ET.SubElement(primitive, "size").text = " ".join(map(str, obj["size"]))
        else:
            ET.SubElement(primitive, "radius").text = str(obj["radius"])
            ET.SubElement(primitive, "length").text = str(obj["length"])
        if tag == "visual":
            color = PALETTE[obj["color"]] if isinstance(obj["color"], str) else obj["color"]
            material = ET.SubElement(node, "material")
            for key in ["ambient", "diffuse"]:
                ET.SubElement(material, key).text = " ".join(map(str, color))
ET.indent(sdf)
(ROOT / "worlds" / "semantic_campus.sdf").write_text(ET.tostring(sdf, encoding="unicode"))
# Rasterise cell/primitive intersections conservatively; outside walls unknown.
cols, rows = np.meshgrid(np.arange(W), np.arange(H))
xx = ORIGIN[0] + (cols + 0.5) * RES
yy = ORIGIN[1] + (H - rows - 0.5) * RES
image = np.full((H, W), 205, np.uint8)
inside = (abs(xx) < 7) & (abs(yy) < 5)
image[inside] = 254
for obj in obstacles:
    dx, dy = xx - obj["x"], yy - obj["y"]
    c, s = math.cos(obj["yaw"]), math.sin(obj["yaw"])
    u, v = c * dx + s * dy, -s * dx + c * dy
    if obj["kind"] == "box":
        # All current boxes are orthogonal; overlap any part of pixel cell.
        hit = (abs(u) <= obj["size"][0] / 2 + RES / 2) & (abs(v) <= obj["size"][1] / 2 + RES / 2)
    else:
        hit = (
            np.maximum(abs(dx) - RES / 2, 0) ** 2 + np.maximum(abs(dy) - RES / 2, 0) ** 2
            <= obj["radius"] ** 2
        )
    image[hit] = 0
cv2.imwrite(str(ROOT / "maps" / "campus.pgm"), image)
(ROOT / "maps" / "campus.yaml").write_text(
    yaml.safe_dump(
        dict(
            image="campus.pgm",
            mode="trinary",
            resolution=RES,
            origin=list(ORIGIN),
            negate=0,
            occupied_thresh=0.65,
            free_thresh=0.196,
        ),
        sort_keys=False,
    )
)
(ROOT / "maps" / "provenance.yaml").write_text(
    yaml.safe_dump(
        dict(
            source="collision geometry from generate_training_world.py",
            method="conservative cell/primitive intersection at robot collision height 0.03–0.38m",
            not_slam=True,
            world="semantic_campus.sdf",
            resolution=RES,
            collision_obstacles=len(obstacles),
            visual_objects=len(scene),
        ),
        sort_keys=False,
        allow_unicode=True,
    )
)
print(f"Generated {len(scene)} objects, {len(obstacles)} collision footprints, map {W}x{H}")
