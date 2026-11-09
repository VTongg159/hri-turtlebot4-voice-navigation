"""Pose original URDF visual meshes using forward kinematics, with portable model URIs."""

from pathlib import Path
import copy
import math
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

MODELS = Path(__file__).resolve().parents[1] / "models"
_CACHE = {}


def vector(text, default=(0, 0, 0)):
    return np.array([float(v) for v in text.split()] if text else default, dtype=float)


def transform(origin=None):
    result = np.eye(4)
    if origin is not None:
        result[:3, 3] = vector(origin.get("xyz"))
        result[:3, :3] = Rotation.from_euler("xyz", vector(origin.get("rpy"))).as_matrix()
    return result


def pose_text(matrix):
    angles = Rotation.from_matrix(matrix[:3, :3]).as_euler("xyz")
    return " ".join(f"{v:.9g}" for v in [*matrix[:3, 3], *angles])


def mesh_reference(model, filename):
    if model in ("unitree_g1", "unitree_go2"):
        rel = filename.split("/", 3)[3] if filename.startswith("package://") else filename
    elif model.startswith("ur"):
        rel = "meshes/" + Path(filename).name
    elif model == "turtlebot4_display":
        rel = "meshes/" + Path(filename).name
    else:
        raise ValueError(model)
    path = MODELS / model / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    return path, "model://" + model + "/" + rel


def visual_parts(model, joints=None):
    joints = joints or {}
    root = ET.parse(MODELS / model / "robot.urdf").getroot()
    links = {e.get("name"): e for e in root.findall("link")}
    edges = root.findall("joint")
    children = {e.find("child").get("link") for e in edges}
    roots = set(links) - children
    poses = {name: np.eye(4) for name in roots}
    pending = edges.copy()
    while pending:
        changed = False
        for edge in pending[:]:
            parent = edge.find("parent").get("link")
            child = edge.find("child").get("link")
            if parent not in poses:
                continue
            local = transform(edge.find("origin"))
            amount = float(joints.get(edge.get("name"), 0))
            if edge.get("type") in ("revolute", "continuous"):
                axis = vector(
                    edge.find("axis").get("xyz") if edge.find("axis") is not None else None,
                    (1, 0, 0),
                )
                rotation = np.eye(4)
                rotation[:3, :3] = Rotation.from_rotvec(axis * amount).as_matrix()
                local = local @ rotation
            elif edge.get("type") == "prismatic":
                axis = vector(edge.find("axis").get("xyz"), (1, 0, 0))
                local[:3, 3] += axis * amount
            poses[child] = poses[parent] @ local
            pending.remove(edge)
            changed = True
        if not changed:
            raise ValueError("Invalid/disconnected URDF tree")
    materials = {e.get("name"): e for e in root.findall("material")}
    parts = []
    zmin = math.inf
    for name, link in links.items():
        for i, source in enumerate(link.findall("visual")):
            mesh = source.find("geometry/mesh")
            if mesh is None:
                continue
            path, uri = mesh_reference(model, mesh.get("filename"))
            matrix = poses[name] @ transform(source.find("origin"))
            scale = vector(mesh.get("scale"), (1, 1, 1))
            if path not in _CACHE:
                shape = trimesh.load(str(path), force="mesh", process=False)
                _CACHE[path] = np.asarray(shape.vertices)
            vertices = _CACHE[path] * scale
            zmin = min(zmin, float((vertices @ matrix[:3, :3].T + matrix[:3, 3])[:, 2].min()))
            material = source.find("material")
            if material is not None and material.find("color") is None:
                material = materials.get(material.get("name"), material)
            rgba = (
                vector(material.find("color").get("rgba"), (1, 1, 1, 1))
                if material is not None and material.find("color") is not None
                else None
            )
            parts.append(dict(name=f"{name}_{i}", matrix=matrix, uri=uri, scale=scale, rgba=rgba))
    return parts, zmin


def append_robot(world, model, name, x, y, surface, yaw=0.0, joints=None):
    parts, zmin = visual_parts(model, joints)
    display = ET.SubElement(world, "model", name=name)
    ET.SubElement(display, "static").text = "true"
    ET.SubElement(display, "pose").text = f"{x} {y} {surface - zmin:.9g} 0 0 {yaw}"
    link = ET.SubElement(display, "link", name="display")
    for part in parts:
        visual = ET.SubElement(link, "visual", name=part["name"])
        ET.SubElement(visual, "pose").text = pose_text(part["matrix"])
        mesh = ET.SubElement(ET.SubElement(visual, "geometry"), "mesh")
        ET.SubElement(mesh, "uri").text = part["uri"]
        ET.SubElement(mesh, "scale").text = " ".join(map(str, part["scale"]))
        if part["rgba"] is not None:
            mat = ET.SubElement(visual, "material")
            for tag in ("ambient", "diffuse"):
                ET.SubElement(mat, tag).text = " ".join(map(str, part["rgba"]))
    return len(parts)


def append_x500(world, name, x, y, surface, yaw=0):
    source = ET.parse(MODELS / "x500_base/model.sdf").getroot().find("model")
    result = ET.SubElement(world, "model", name=name)
    ET.SubElement(result, "static").text = "true"
    ET.SubElement(result, "pose").text = f"{x} {y} {surface + 0.24} 0 0 {yaw}"
    # Copy only original visual geometry: no duplicate sensors, TF, motors or transport plugins.
    count = 0
    for src_link in source.findall("link"):
        link = ET.SubElement(result, "link", name=src_link.get("name"))
        if src_link.find("pose") is not None:
            link.append(copy.deepcopy(src_link.find("pose")))
        for src in src_link.findall("visual"):
            visual = copy.deepcopy(src)
            material = visual.find("material")
            if material is not None and material.find("script") is not None:
                name = material.findtext("script/name", "").lower()
                material.remove(material.find("script"))
                color = (
                    ".06 .07 .08 1"
                    if "black" in name
                    else ".55 .57 .59 1"
                    if "grey" in name
                    else ".9 .92 .94 1"
                )
                for tag in ["ambient", "diffuse"]:
                    old = material.find(tag)
                    if old is not None:
                        material.remove(old)
                    ET.SubElement(material, tag).text = color
            link.append(visual)
            count += 1
    return count
