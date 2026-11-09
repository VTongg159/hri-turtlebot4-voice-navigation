#!/usr/bin/env python3
"""PAIRS robotics lab: shared collision/map geometry, authentic static robot exhibits.

All branding images are referenced unchanged. Robot display visuals are imported
from vendor URDFs with forward kinematics; they do not claim active locomotion.
"""

from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import yaml
from scene_assets import append_robot, append_x500

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / "models/pairs_brand/materials/textures"
RES = 0.05
ORIGIN = (-14.5, -10.5, 0.0)
WIDTH, HEIGHT = 580, 420
SPAWN = (-11.0, 0.0, 0.0)
PALETTE = {
    "navy": (0.055, 0.105, 0.18, 1),
    "slate": (0.18, 0.25, 0.32, 1),
    "steel": (0.46, 0.55, 0.62, 1),
    "white": (0.96, 0.97, 0.98, 1),
    "wall": (0.85, 0.89, 0.92, 1),
    "wood": (0.62, 0.43, 0.28, 1),
    "cyan": (0.02, 0.65, 0.79, 1),
    "blue": (0.08, 0.36, 0.78, 1),
    "violet": (0.48, 0.31, 0.78, 1),
    "amber": (0.93, 0.51, 0.10, 1),
    "green": (0.10, 0.56, 0.36, 1),
    "leaf": (0.16, 0.42, 0.29, 1),
    "black": (0.045, 0.055, 0.065, 1),
    "screen": (0.045, 0.15, 0.22, 1),
    "foam": (0.17, 0.23, 0.29, 1),
}
LABS = [
    dict(
        id="A",
        name="Phòng UAV",
        title="01  /  UAV RESEARCH",
        sub="AERIAL ROBOTICS  ·  MOTION CAPTURE",
        color="cyan",
        bounds=(-13.8, -4.9, 2.2, 9.8),
        goal=(-9.0, 3.65, math.pi / 2),
        aliases=[
            "phòng a",
            "khu vực a",
            "uav",
            "khu uav",
            "phòng nghiên cứu uav",
            "phòng drone",
            "máy bay không người lái",
        ],
        label=(-9.3, 9.1),
    ),
    dict(
        id="B",
        name="Phòng tay máy",
        title="02  /  MANIPULATION",
        sub="UR5e  ·  UR3e  ·  ROBOT LEARNING",
        color="blue",
        bounds=(-4.5, 4.5, 2.2, 9.8),
        goal=(0.0, 3.65, math.pi / 2),
        aliases=[
            "phòng b",
            "khu vực b",
            "tay máy",
            "phòng robot tay máy",
            "phòng thao tác",
            "phòng cánh tay robot",
        ],
        label=(0.0, 9.1),
    ),
    dict(
        id="D",
        name="Phòng HRI humanoid",
        title="03  /  HRI + HUMANOIDS",
        sub="UNITREE G1  ·  HUMAN ROBOT INTERACTION",
        color="violet",
        bounds=(4.9, 13.8, 2.2, 9.8),
        goal=(9.0, 3.65, math.pi / 2),
        aliases=[
            "phòng d",
            "khu vực d",
            "hri",
            "khu hri",
            "phòng hri",
            "humanoid",
            "phòng humanoid",
            "phòng g1",
            "robot hình người",
            "phòng robot hình người",
        ],
        label=(9.3, 9.1),
    ),
    dict(
        id="E",
        name="Phòng chó robot",
        title="04  /  LEGGED ROBOTICS",
        sub="UNITREE GO2  ·  TERRAIN + LOCOMOTION",
        color="amber",
        bounds=(-13.8, -0.2, -9.8, -2.2),
        goal=(-7.0, -3.65, -math.pi / 2),
        aliases=[
            "phòng e",
            "khu vực e",
            "chó robot",
            "khu chó robot",
            "phòng go2",
            "go2",
            "phòng robot bốn chân",
            "phòng unitree go2",
        ],
        label=(-7.0, -9.1),
    ),
    dict(
        id="F",
        name="Phòng TurtleBot",
        title="05  /  MOBILE ROBOTICS",
        sub="TURTLEBOT 4  ·  SLAM + AUTONOMY",
        color="green",
        bounds=(0.2, 13.8, -9.8, -2.2),
        goal=(7.0, -3.65, -math.pi / 2),
        aliases=[
            "phòng f",
            "khu vực f",
            "turtlebot",
            "khu turtlebot",
            "phòng robot di động",
            "phòng turtlebot 4",
        ],
        label=(7.0, -9.1),
    ),
]


def rgba(value):
    return PALETTE[value] if isinstance(value, str) else value


class Scene:
    def __init__(self):
        self.objects = []
        self.obstacles = []

    def add(
        self,
        name,
        kind,
        xyz,
        size,
        color,
        collision=False,
        yaw=0.0,
        rpy=None,
        alpha=1.0,
        emission=None,
        shadow=True,
        texture=None,
    ):
        obj = dict(
            name=name,
            kind=kind,
            xyz=tuple(xyz),
            size=tuple(size),
            color=rgba(color),
            collision=collision,
            rpy=rpy or (0.0, 0.0, yaw),
            alpha=alpha,
            emission=emission,
            shadow=shadow,
            texture=texture,
        )
        self.objects.append(obj)
        if collision:
            z = xyz[2]
            height = size[2] if kind == "box" else size[1]
            if z - height / 2 < 0.38 and z + height / 2 > 0.03:
                self.obstacles.append(obj)
        return obj

    def box(self, name, xyz, size, color, collision=False, **kwargs):
        return self.add(name, "box", xyz, size, color, collision, **kwargs)

    def cylinder(self, name, xyz, radius, length, color, collision=False, **kwargs):
        return self.add(name, "cylinder", xyz, (radius, length), color, collision, **kwargs)

    def plane(self, name, xyz, size, texture, rpy=(0, 0, 0)):
        return self.add(name, "plane", xyz, size, "white", rpy=rpy, shadow=False, texture=texture)

    def wall(self, name, x, y, sx, sy, glass=False):
        if glass:
            self.box(name + "_base", (x, y, 0.21), (sx, sy, 0.42), "wall", True)
            self.box(
                name + "_glass",
                (x, y, 0.95),
                (sx, 0.045 if sx > sy else sy, 1.05) if sx > sy else (0.045, sy, 1.05),
                (0.32, 0.57, 0.68, 1),
                True,
                alpha=0.24,
                shadow=False,
            )
            self.box(name + "_header", (x, y, 1.49), (sx + 0.02, sy + 0.02, 0.09), "slate")
            # Mullions break up large glass panels while keeping the interior visible.
            length = max(sx, sy)
            for i, t in enumerate(np.arange(-length / 2 + 0.1, length / 2, 0.95)):
                xx, yy = (x + t, y) if sx > sy else (x, y + t)
                self.box(name + f"_mullion_{i}", (xx, yy, 0.95), (0.035, 0.035, 1.05), "steel")
        else:
            self.box(name, (x, y, 0.7), (sx, sy, 1.4), "wall", True)
            self.box(name + "_cap", (x, y, 1.425), (sx + 0.025, sy + 0.025, 0.05), "slate")
        self.box(name + "_skirt", (x, y, 0.055), (sx + 0.012, sy + 0.012, 0.11), "navy", True)

    def desk(self, name, x, y, sx=1.5, sy=0.72, height=0.78):
        self.box(name + "_surface", (x, y, height), (sx, sy, 0.065), "white", True)
        for a in [-1, 1]:
            self.box(
                name + f"_trestle_{a}",
                (x + a * (sx / 2 - 0.12), y, height / 2),
                (0.065, sy - 0.12, height),
                "slate",
                True,
            )
        self.box(name + "_front_edge", (x, y - sy / 2, height - 0.01), (sx, 0.026, 0.085), "wood")

    def chair(self, name, x, y, yaw=0, color="slate"):
        self.cylinder(name + "_base", (x, y, 0.12), 0.23, 0.22, "black", True)
        self.box(name + "_seat", (x, y, 0.43), (0.46, 0.45, 0.095), color, yaw=yaw)
        self.box(
            name + "_back",
            (x - math.sin(yaw) * 0.19, y + math.cos(yaw) * 0.19, 0.66),
            (0.46, 0.075, 0.49),
            color,
            yaw=yaw,
        )

    def plant(self, name, x, y):
        self.cylinder(name + "_pot", (x, y, 0.26), 0.26, 0.52, "white", True)
        self.cylinder(name + "_stem", (x, y, 0.7), 0.04, 0.7, "wood")
        for i, (dx, dy, z, r) in enumerate(
            [
                (0, 0, 1.15, 0.35),
                (-0.18, 0.08, 1.0, 0.25),
                (0.17, 0.12, 1.3, 0.23),
                (0.05, -0.2, 1.1, 0.25),
            ]
        ):
            self.cylinder(name + f"_leaf_{i}", (x + dx, y + dy, z), r, 0.22, "leaf", shadow=False)

    def export(self, world):
        model = ET.SubElement(world, "model", name="pairs_architecture")
        ET.SubElement(model, "static").text = "true"
        link = ET.SubElement(model, "link", name="building")
        for obj in self.objects:
            x, y, z = obj["xyz"]
            roll, pitch, yaw = obj["rpy"]
            for tag in ["collision", "visual"] if obj["collision"] else ["visual"]:
                item = ET.SubElement(link, tag, name=obj["name"] + "_" + tag)
                ET.SubElement(item, "pose").text = f"{x} {y} {z} {roll} {pitch} {yaw}"
                geometry = ET.SubElement(item, "geometry")
                primitive = ET.SubElement(geometry, obj["kind"])
                if obj["kind"] == "box":
                    ET.SubElement(primitive, "size").text = " ".join(map(str, obj["size"]))
                elif obj["kind"] == "plane":
                    ET.SubElement(primitive, "normal").text = "0 0 1"
                    ET.SubElement(primitive, "size").text = " ".join(map(str, obj["size"]))
                else:
                    ET.SubElement(primitive, "radius").text = str(obj["size"][0])
                    ET.SubElement(primitive, "length").text = str(obj["size"][1])
                if tag == "visual":
                    ET.SubElement(item, "cast_shadows").text = "true" if obj["shadow"] else "false"
                    ET.SubElement(item, "transparency").text = str(1 - obj["alpha"])
                    material = ET.SubElement(item, "material")
                    for key in ["ambient", "diffuse"]:
                        ET.SubElement(material, key).text = " ".join(map(str, obj["color"]))
                    ET.SubElement(material, "specular").text = ".15 .18 .20 1"
                    if obj["emission"]:
                        ET.SubElement(material, "emissive").text = " ".join(
                            map(str, rgba(obj["emission"]))
                        )
                    metal = ET.SubElement(ET.SubElement(material, "pbr"), "metal")
                    ET.SubElement(metal, "metalness").text = ".08"
                    ET.SubElement(metal, "roughness").text = ".65"
                    if obj["texture"]:
                        ET.SubElement(metal, "albedo_map").text = (
                            "model://pairs_brand/materials/textures/" + obj["texture"]
                        )

    def raster(self):
        cols, rows = np.meshgrid(np.arange(WIDTH), np.arange(HEIGHT))
        xx = ORIGIN[0] + (cols + 0.5) * RES
        yy = ORIGIN[1] + (HEIGHT - rows - 0.5) * RES
        image = np.full((HEIGHT, WIDTH), 205, np.uint8)
        image[(abs(xx) < 14) & (abs(yy) < 10)] = 254
        for obj in self.obstacles:
            x, y, _ = obj["xyz"]
            yaw = obj["rpy"][2]
            dx, dy = xx - x, yy - y
            c, s = math.cos(yaw), math.sin(yaw)
            u, v = c * dx + s * dy, -s * dx + c * dy
            if obj["kind"] == "box":
                # SAT of rotated rectangle vs axis-aligned pixel square.
                a, b = obj["size"][0] / 2, obj["size"][1] / 2
                h = RES / 2
                hit = (abs(u) <= a + h * (abs(c) + abs(s))) & (abs(v) <= b + h * (abs(c) + abs(s)))
                hit &= (abs(dx) <= a * abs(c) + b * abs(s) + h) & (
                    abs(dy) <= a * abs(s) + b * abs(c) + h
                )
            else:
                radius = obj["size"][0]
                hit = (
                    np.maximum(abs(dx) - RES / 2, 0) ** 2 + np.maximum(abs(dy) - RES / 2, 0) ** 2
                    <= radius**2
                )
            image[hit] = 0
        return image


def sign_texture(filename, title, subtitle="", color=(22, 77, 111), width=1600, height=260):
    """Code-generated typography for scene signage; original logos are never redrawn."""
    image = Image.new("RGB", (width, height), (246, 249, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 22, height), fill=color)
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    size = 72
    while draw.textbbox((0, 0), title, font=ImageFont.truetype(bold, size))[2] > width - 100:
        size -= 2
    draw.text((55, 42), title, font=ImageFont.truetype(bold, size), fill=(19, 37, 57))
    if subtitle:
        draw.text((58, 154), subtitle, font=ImageFont.truetype(regular, 32), fill=(77, 98, 118))
    image.save(TEXTURES / filename)


def workstation(scene, name, x, y):
    scene.desk(name, x, y)
    scene.box(name + "_monitor", (x, y + 0.17, 1.15), (0.82, 0.07, 0.46), "black")
    scene.box(
        name + "_screen",
        (x, y + 0.125, 1.15),
        (0.75, 0.012, 0.39),
        "screen",
        emission=(0.025, 0.08, 0.12, 1),
        shadow=False,
    )
    for i in range(4):
        scene.box(
            name + f"_code_{i}",
            (x - 0.12 + i * 0.03, y + 0.114, 1.26 - i * 0.065),
            (0.46 - i * 0.045, 0.006, 0.013),
            "cyan",
            shadow=False,
        )
    scene.box(name + "_keyboard", (x, y - 0.13, 0.824), (0.47, 0.17, 0.022), "slate")
    scene.box(name + "_tower", (x + 0.55, y, 0.30), (0.24, 0.49, 0.60), "slate", True)
    scene.chair(name + "_chair", x, y - 0.8)


def light_strip(scene, name, x, y, sx, sy, z=2.35):
    scene.box(name + "_frame", (x, y, z), (sx, sy, 0.045), "slate", shadow=False)
    scene.box(
        name + "_led",
        (x, y, z - 0.027),
        (max(0.02, sx - 0.035), max(0.02, sy - 0.035), 0.012),
        "white",
        emission="white",
        shadow=False,
    )


def landing_pad(scene, name, x, y, r=1.0):
    scene.cylinder(name + "_outer", (x, y, 0.035), r, 0.012, "cyan", shadow=False)
    scene.cylinder(name + "_inner", (x, y, 0.043), r - 0.065, 0.012, "navy", shadow=False)
    for dx in [-0.25, 0.25]:
        scene.box(
            name + f"_h_{dx}", (x + dx, y, 0.055), (0.085, 0.66, 0.008), "white", shadow=False
        )
    scene.box(name + "_h_bar", (x, y, 0.057), (0.54, 0.085, 0.008), "white", shadow=False)


def build():
    TEXTURES.mkdir(parents=True, exist_ok=True)
    s = Scene()
    # Architectural floor: clean white/grey stone, very subtle seams, colored lab borders.
    s.box("foundation", (0, 0, -0.075), (28.3, 20.3, 0.15), "slate")
    s.box("main_floor", (0, 0, 0.012), (27.86, 19.86, 0.02), (0.91, 0.93, 0.95, 1))
    for x in np.arange(-13, 14, 1.0):
        s.box(
            f"tile_x_{x}", (x, 0, 0.024), (0.008, 19.75, 0.003), (0.80, 0.84, 0.88, 1), shadow=False
        )
    for y in np.arange(-9, 10, 1.0):
        s.box(
            f"tile_y_{y}", (0, y, 0.025), (27.75, 0.008, 0.003), (0.80, 0.84, 0.88, 1), shadow=False
        )
    for lab in LABS:
        a, b, c, d = lab["bounds"]
        x, y = (a + b) / 2, (c + d) / 2
        sx, sy = b - a, d - c
        color = rgba(lab["color"])
        floor = tuple(0.91 + 0.07 * v for v in color[:3]) + (1,)
        s.box(lab["id"] + "_floor", (x, y, 0.028), (sx, sy, 0.008), floor, shadow=False)
        for xx in [a + 0.07, b - 0.07]:
            s.box(
                lab["id"] + f"_edge_x_{xx}",
                (xx, y, 0.035),
                (0.045, sy - 0.12, 0.006),
                lab["color"],
                shadow=False,
            )
        for yy in [c + 0.07, d - 0.07]:
            s.box(
                lab["id"] + f"_edge_y_{yy}",
                (x, yy, 0.035),
                (sx - 0.12, 0.045, 0.006),
                lab["color"],
                shadow=False,
            )
        rgb = tuple(int(v * 255) for v in color[:3])
        texture = "sign_" + lab["id"] + ".png"
        sign_texture(texture, lab["title"], lab["sub"], rgb)
        s.plane(
            lab["id"] + "_floor_sign",
            (x, y + (sy / 2 - 0.75 if y > 0 else -sy / 2 + 0.75), 0.047),
            (min(6.4, sx - 1), 1.04),
            texture,
        )
        # Slim ceiling-light rails stop short of the centre for the cutaway camera.
        light_strip(s, lab["id"] + "_left_light", a + 0.45, y, 0.07, sy - 1.1)
        light_strip(s, lab["id"] + "_right_light", b - 0.45, y, 0.07, sy - 1.1)
    s.box("gallery_floor", (0, 0, 0.031), (27.75, 3.75, 0.01), (0.94, 0.95, 0.96, 1), shadow=False)
    for yy in [-1.05, 1.05]:
        s.box(
            "gallery_lane_" + str(yy), (0, yy, 0.041), (26.8, 0.022, 0.006), "steel", shadow=False
        )
    # Perimeter stays low enough to expose the real robot meshes in the overview.
    for name, x, y, sx, sy in [
        ("north", 0, 10, 28, 0.16),
        ("south", 0, -10, 28, 0.16),
        ("west", -14, 0, 0.16, 20),
        ("east", 14, 0, 0.16, 20),
    ]:
        s.wall(name, x, y, sx, sy)
    for x in [-4.7, 4.7]:
        s.wall(f"north_divider_{x}", x, 6, 0.14, 8, glass=True)
    s.wall("south_divider", 0, -6, 0.14, 8, glass=True)
    # Front partition segments have broad doorways; central gallery is always free.
    north = [(-14, -10.1), (-7.9, -1.1), (1.1, 7.9), (10.1, 14)]
    south = [(-14, -8.1), (-5.9, 5.9), (8.1, 14)]
    for y, parts in [(2.0, north), (-2.0, south)]:
        for i, (a, b) in enumerate(parts):
            s.wall(f"gallery_partition_{y}_{i}", (a + b) / 2, y, b - a, 0.12, glass=True)
    for x, y, color in [
        (-9, 2, "cyan"),
        (0, 2, "blue"),
        (9, 2, "violet"),
        (-7, -2, "amber"),
        (7, -2, "green"),
    ]:
        for xx in [x - 1.13, x + 1.13]:
            s.box(f"door_{x}_{y}_{xx}", (xx, y, 0.80), (0.075, 0.19, 1.6), "slate", True)
        s.box(f"door_lintel_{x}_{y}", (x, y, 1.64), (2.34, 0.19, 0.16), color)
        s.box(
            f"door_led_{x}_{y}",
            (x, y - 0.105 if y > 0 else y + 0.105, 1.62),
            (2.15, 0.018, 0.033),
            color,
            emission=color,
            shadow=False,
        )
    # Reception: branded wall, unchanged supplied logos, and a clear 2m centre lane.
    s.box("brand_wall", (4.4, 1.93, 1.18), (5.25, 0.16, 2.36), "navy", True)
    s.box("brand_panel", (4.4, 1.835, 1.18), (4.95, 0.025, 1.95), "white")
    s.plane(
        "pairs_wall_logo", (4.65, 1.812, 1.30), (3.50, 1.15), "logo_pairs.png", (math.pi / 2, 0, 0)
    )
    s.plane("vnu_wall_logo", (2.43, 1.810, 1.30), (0.92, 0.92), "logo_vnu.png", (math.pi / 2, 0, 0))
    s.plane("pairs_gallery_logo", (-0.1, 0, 0.047), (4.1, 4.1 * 689 / 2094), "logo_pairs.png")
    s.plane("vnu_gallery_logo", (-3.6, 0, 0.047), (1.15, 1.15), "logo_vnu.png")
    sign_texture(
        "gallery_title.png",
        "PAIRS ROBOTICS LAB",
        "RESEARCH  /  COLLABORATE  /  DISCOVER",
        width=1500,
        height=260,
    )
    s.plane("gallery_title", (7.4, 0, 0.047), (5.3, 0.92), "gallery_title.png")
    s.box("reception_counter", (-11.7, -1.5, 0.46), (2.8, 0.65, 0.92), "white", True)
    s.box("reception_wood_face", (-11.7, -1.84, 0.46), (2.65, 0.035, 0.72), "wood")
    s.box("reception_countertop", (-11.7, -1.5, 0.96), (2.92, 0.74, 0.08), "navy")
    s.box("kiosk_stand", (-12.9, 1.25, 0.58), (0.24, 0.25, 1.16), "slate", True)
    s.box("kiosk_screen", (-12.9, 1.25, 1.32), (0.78, 0.10, 0.58), "screen")
    for i, x in enumerate([11.9]):
        s.box(f"gallery_bench_{i}", (x, 1.48, 0.23), (2.1, 0.47, 0.46), "wood", True)
    # UAV lab: actual X500 meshes, H pads, mocap poles and a wire-grid flight cage.
    s.box("flight_floor", (-10, 7.1, 0.034), (6.1, 4.8, 0.014), "foam", shadow=False)
    landing_pad(s, "pad_one", -10.9, 6.7, 1.05)
    landing_pad(s, "pad_two", -8.5, 8.1, 0.72)
    for i, (x, y) in enumerate([(-13.1, 4.7), (-6.9, 4.7), (-13.1, 9.5), (-6.9, 9.5)]):
        s.cylinder(f"cage_post_{i}", (x, y, 1.4), 0.045, 2.8, "slate", True)
        s.box(f"mocap_camera_{i}", (x, y, 2.48), (0.16, 0.22, 0.12), "black")
        s.cylinder(
            f"mocap_lens_{i}", (x, y - 0.12, 2.48), 0.045, 0.055, "cyan", rpy=(math.pi / 2, 0, 0)
        )
    for y in [4.7, 9.5]:
        for z in [0.18, 2.7]:
            s.box(
                f"cage_cross_{y}_{z}",
                (-10, y, z),
                (6.25, 0.05, 0.10 if z < 1 else 0.05),
                "slate",
                z < 1,
            )
        for x in np.arange(-13.0, -6.9, 0.45):
            s.box(f"cage_net_x_{x}_{y}", (x, y, 1.4), (0.009, 0.009, 2.6), "steel", shadow=False)
        for z in np.arange(0.55, 2.7, 0.45):
            s.box(f"cage_net_z_{z}_{y}", (-10, y, z), (6.2, 0.008, 0.008), "steel", shadow=False)
    for x in [-13.1, -6.9]:
        for z in [0.18, 2.7]:
            s.box(
                f"cage_side_{x}_{z}",
                (x, 7.1, z),
                (0.05, 4.8, 0.1 if z < 1 else 0.05),
                "slate",
                z < 1,
            )
        for y in np.arange(4.8, 9.5, 0.45):
            s.box(f"cage_net_y_{x}_{y}", (x, y, 1.4), (0.008, 0.008, 2.6), "steel", shadow=False)
    workstation(s, "uav_workstation", -5.75, 8.2)
    s.desk("uav_inspection", -5.8, 5.65, 1.4, 0.8, 0.85)
    # Manipulation lab: clean industrial plinths, two authentic UR arms and parts bins.
    for name, x, y in [("ur5e_station", -2.45, 6.7), ("ur3e_station", 2.30, 6.7)]:
        s.box(name + "_base", (x, y, 0.43), (1.5, 1.3, 0.86), "white", True)
        s.box(name + "_top", (x, y, 0.895), (1.65, 1.45, 0.07), "slate")
        s.box(
            name + "_edge",
            (x, y - 0.742, 0.88),
            (1.6, 0.025, 0.07),
            "blue",
            emission="blue",
            shadow=False,
        )
        for i in range(3):
            s.box(
                name + f"_bin_{i}",
                (x - 0.48 + i * 0.35, y - 0.45, 0.98),
                (0.26, 0.22, 0.12),
                ["cyan", "amber", "violet"][i],
            )
    workstation(s, "arm_station_pc", 0.0, 8.6)
    for x in [-3.9, 3.9]:
        s.box(f"arm_storage_{x}", (x, 8.4, 0.52), (0.75, 1.6, 1.04), "white", True)
        for z in [0.25, 0.58, 0.9]:
            s.box(f"arm_drawer_{x}_{z}", (x, 7.575, z), (0.55, 0.035, 0.018), "steel")
    # HRI lab: stage, authentic Unitree G1, experiment floor and interview area.
    s.box(
        "g1_experiment_mat",
        (9.0, 6.7, 0.042),
        (5.7, 3.8, 0.022),
        (0.81, 0.83, 0.90, 1),
        shadow=False,
    )
    s.cylinder("g1_stage", (8.6, 6.6, 0.075), 1.05, 0.15, "white", True)
    s.cylinder("g1_stage_ring", (8.6, 6.6, 0.154), 1.02, 0.012, "violet", shadow=False)
    s.cylinder("g1_stage_top", (8.6, 6.6, 0.164), 0.96, 0.012, "white", shadow=False)
    for i in range(9):
        angle = i * 2 * math.pi / 9
        s.box(
            f"hri_floor_target_{i}",
            (9 + 2.35 * math.cos(angle), 6.7 + 1.5 * math.sin(angle), 0.058),
            (0.13, 0.13, 0.005),
            "violet",
            shadow=False,
        )
    workstation(s, "hri_pc", 12.35, 8.2)
    s.desk("hri_interview", 11.9, 5.7, 1.3, 0.65)
    s.chair("hri_interview_chair", 11.9, 4.95, color="violet")
    # Quadruped lab: Go2 on a real display platform, stepped terrain and inspection bay.
    s.box(
        "go2_test_mat", (-7.0, -6.8, 0.036), (6.6, 4.2, 0.016), (0.22, 0.27, 0.31, 1), shadow=False
    )
    s.box("go2_stage", (-8.4, -6.2, 0.075), (2.15, 1.65, 0.15), "white", True)
    s.box("go2_stage_trim", (-8.4, -6.2, 0.156), (2.1, 1.6, 0.012), "amber", shadow=False)
    for i, height in enumerate([0.08, 0.15, 0.23, 0.31, 0.23, 0.15, 0.08]):
        s.box(
            f"go2_step_{i}",
            (-5.3 + i * 0.43, -7.05, height / 2),
            (0.40, 2.05, height),
            (0.43 + 0.025 * i, 0.49 + 0.02 * i, 0.53 + 0.02 * i, 1),
            True,
        )
        s.box(
            f"go2_step_edge_{i}",
            (-5.3 + i * 0.43, -6.01, height + 0.004),
            (0.40, 0.035, 0.008),
            "amber",
            shadow=False,
        )
    workstation(s, "go2_pc", -12.0, -8.4)
    s.box("go2_inspection_table", (-11.4, -5.7, 0.38), (1.6, 0.9, 0.76), "white", True)
    # TurtleBot lab: two authentic TB4 displays, charging wall, markers and test lanes.
    s.box(
        "mobile_test_floor",
        (7.6, -6.8, 0.036),
        (8.8, 4.3, 0.014),
        (0.88, 0.92, 0.90, 1),
        shadow=False,
    )
    for i, x in enumerate([5.0, 8.0]):
        s.cylinder(f"tb4_podium_{i}", (x, -6.7, 0.065), 0.58, 0.13, "white", True)
        s.cylinder(f"tb4_ring_{i}", (x, -6.7, 0.134), 0.57, 0.008, "green", shadow=False)
        s.box(f"tb4_dock_{i}", (x, -7.5, 0.19), (0.64, 0.22, 0.38), "slate", True)
    for x in [10.2, 12.2]:
        s.box("mobile_lane_" + str(x), (x, -6.2, 0.049), (0.045, 4.6, 0.008), "green", shadow=False)
    for y in [-4.7, -5.7, -6.7, -7.7]:
        s.box(
            "mobile_lane_cross_" + str(y),
            (11.2, y, 0.05),
            (2.0, 0.025, 0.008),
            "steel",
            shadow=False,
        )
    for i, (x, y) in enumerate([(10.2, -4.7), (12.2, -7.7)]):
        s.cylinder("test_bollard_" + str(i), (x, y, 0.27), 0.14, 0.54, "green", True)
    workstation(s, "mobile_pc", 1.5, -8.4)
    s.box("mobile_parts_cabinet", (1.0, -5.3, 0.55), (0.8, 1.7, 1.1), "white", True)
    # Plants and warm accents soften the technical exhibits without blocking doorways.
    for i, (x, y) in enumerate(
        [
            (-13.4, 3.2),
            (-4.0, 3.0),
            (4.0, 3.0),
            (13.35, 3.0),
            (-13.3, -3.1),
            (-0.8, -9.15),
            (0.8, -3.0),
            (13.3, -8.7),
            (13.2, 0.75),
        ]
    ):
        s.plant("plant_" + str(i), x, y)
    return s


def pixel(x, y):
    return [
        int(round((x - ORIGIN[0]) / RES - 0.5)),
        int(round(HEIGHT - (y - ORIGIN[1]) / RES - 0.5)),
    ]


def main():
    scene = build()
    sdf = ET.Element("sdf", version="1.9")
    world = ET.SubElement(sdf, "world", name="pairs_lab")
    physics = ET.SubElement(world, "physics", name="physics", type="ignored")
    ET.SubElement(physics, "max_step_size").text = ".001"
    ET.SubElement(physics, "real_time_factor").text = "1.0"
    for file, name in [
        ("physics", "Physics"),
        ("user-commands", "UserCommands"),
        ("scene-broadcaster", "SceneBroadcaster"),
        ("sensors", "Sensors"),
        ("imu", "Imu"),
    ]:
        plugin = ET.SubElement(
            world, "plugin", filename="gz-sim-" + file + "-system", name="gz::sim::systems::" + name
        )
        if name == "Sensors":
            ET.SubElement(plugin, "render_engine").text = "ogre2"
    view = ET.SubElement(world, "scene")
    ET.SubElement(view, "ambient").text = ".58 .60 .64 1"
    ET.SubElement(view, "background").text = ".91 .94 .97 1"
    ET.SubElement(view, "shadows").text = "true"
    sun = ET.SubElement(world, "light", name="architectural_daylight", type="directional")
    ET.SubElement(sun, "pose").text = "0 0 18 0 0 0"
    ET.SubElement(sun, "direction").text = "-.45 -.6 -1"
    ET.SubElement(sun, "diffuse").text = ".92 .94 1 1"
    ET.SubElement(sun, "specular").text = ".18 .20 .24 1"
    ET.SubElement(sun, "cast_shadows").text = "true"
    ground = ET.SubElement(world, "model", name="ground_plane")
    ET.SubElement(ground, "static").text = "true"
    link = ET.SubElement(ground, "link", name="link")
    for tag in ["collision", "visual"]:
        item = ET.SubElement(link, tag, name=tag)
        plane = ET.SubElement(ET.SubElement(item, "geometry"), "plane")
        ET.SubElement(plane, "normal").text = "0 0 1"
        ET.SubElement(plane, "size").text = "100 100"
        if tag == "visual":
            mat = ET.SubElement(item, "material")
            for key in ["ambient", "diffuse"]:
                ET.SubElement(mat, key).text = ".82 .86 .90 1"
    scene.export(world)
    g1 = {
        "left_hip_pitch_joint": -0.10,
        "right_hip_pitch_joint": -0.10,
        "left_knee_joint": 0.20,
        "right_knee_joint": 0.20,
        "left_ankle_pitch_joint": -0.10,
        "right_ankle_pitch_joint": -0.10,
        "left_elbow_joint": 0.60,
        "right_elbow_joint": 0.60,
        "left_shoulder_roll_joint": 0.12,
        "right_shoulder_roll_joint": -0.12,
    }
    go2 = {
        f"{leg}_{joint}_joint": value
        for leg in ["FL", "FR", "RL", "RR"]
        for joint, value in [("thigh", 0.78), ("calf", -1.56)]
    }
    arms = {
        "shoulder_pan_joint": 0.4,
        "shoulder_lift_joint": -1.20,
        "elbow_joint": 1.65,
        "wrist_1_joint": -1.95,
        "wrist_2_joint": -1.57,
        "wrist_3_joint": 0.2,
    }
    counts = {}
    counts["g1"] = append_robot(
        world, "unitree_g1", "unitree_g1_hri", 8.6, 6.6, 0.171, yaw=-math.pi / 2, joints=g1
    )
    counts["go2"] = append_robot(
        world, "unitree_go2", "unitree_go2_terrain", -8.4, -6.2, 0.165, yaw=-0.35, joints=go2
    )
    append_robot(
        world, "unitree_go2", "unitree_go2_inspection", -11.4, -5.7, 0.77, yaw=0.1, joints=go2
    )
    counts["ur5e"] = append_robot(
        world, "ur5e", "ur5e_research", -2.45, 6.7, 0.935, yaw=0.2, joints=arms
    )
    append_robot(world, "ur3e", "ur3e_research", 2.3, 6.7, 0.935, yaw=-0.6, joints=arms)
    for i, x in enumerate([5.0, 8.0]):
        append_robot(
            world,
            "turtlebot4_display",
            "turtlebot4_exhibit_" + str(i),
            x,
            -6.7,
            0.145,
            yaw=math.pi / 2,
        )
    counts["x500"] = append_x500(world, "x500_flight_exhibit", -10.9, 6.7, 0.88, yaw=0.35)
    append_x500(world, "x500_inspection_exhibit", -5.8, 5.65, 0.90, yaw=-0.4)
    ET.indent(sdf)
    (ROOT / "worlds/pairs_lab.sdf").write_text(ET.tostring(sdf, encoding="unicode"))
    image = scene.raster()
    cv2.imwrite(str(ROOT / "maps/pairs_lab.pgm"), image)
    (ROOT / "maps/pairs_lab.yaml").write_text(
        yaml.safe_dump(
            dict(
                image="pairs_lab.pgm",
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
    regions = []
    for lab in LABS:
        a, b, c, d = lab["bounds"]
        x, y, yaw = lab["goal"]
        color = "#" + "".join(f"{round(v * 255):02x}" for v in rgba(lab["color"])[:3])
        regions.append(
            dict(
                id=lab["id"],
                name=lab["name"],
                display_color=color,
                aliases=lab["aliases"],
                polygon_pixels=[pixel(a, d), pixel(b, d), pixel(b, c), pixel(a, c)],
                label_pixel=pixel(*lab["label"]),
                goal=dict(x=x, y=y, yaw=yaw),
            )
        )
    regions.insert(
        2,
        dict(
            id="C",
            name="Sảnh PAIRS Lab",
            aliases=[
                "phòng c",
                "khu vực c",
                "hành lang",
                "hành lang c",
                "sảnh",
                "sảnh trung tâm",
                "sảnh pairs lab",
            ],
            polygon_pixels=[
                pixel(-13.7, 1.75),
                pixel(13.7, 1.75),
                pixel(13.7, -1.75),
                pixel(-13.7, -1.75),
            ],
            label_pixel=pixel(0, 0.8),
            goal=dict(x=0.0, y=0.0, yaw=0.0),
        ),
    )
    data = dict(
        map_frame="map",
        map_yaml="../maps/pairs_lab.yaml",
        min_clearance=0.38,
        reachable_from_map=list(SPAWN[:2]),
        scene_name="PAIRS Robotics Research Lab",
        world_size_m=[28, 20],
        spawn_map=list(SPAWN),
        provenance="Same collision geometry as pairs_lab.sdf; static original vendor robot exhibits on physical platforms; not SLAM.",
        regions=regions,
    )
    (ROOT / "config/pairs_regions.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    )
    info = dict(
        source="generate_pairslab_world.py",
        world="pairs_lab.sdf",
        not_slam=True,
        resolution=RES,
        size_m=[28, 20],
        spawn=list(SPAWN),
        architecture_visuals=len(scene.objects),
        collision_footprints=len(scene.obstacles),
        vendor_visual_counts=counts,
        robot_exhibits="static vendor visual meshes, no motion controllers",
        logos="unchanged original PAIRS Lab and VNU PNGs",
    )
    (ROOT / "maps/pairs_provenance.yaml").write_text(
        yaml.safe_dump(info, sort_keys=False, allow_unicode=True)
    )
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
