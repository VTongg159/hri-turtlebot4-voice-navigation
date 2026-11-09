#!/usr/bin/env python3
"""Fetch pinned Unitree originals; vendor existing robot resources for an offline scene."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import argparse
import json
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
UNITREE_SHA = "725b59b6de39a26c425632120c89f23c49a36f1e"
BASE = f"https://raw.githubusercontent.com/unitreerobotics/unitree_ros/{UNITREE_SHA}/"


def fetch(source, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    for attempt in range(4):
        try:
            with urllib.request.urlopen(BASE + source, timeout=60) as r:
                data = r.read()
            target.write_bytes(data)
            return target
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--px4-models",
        type=Path,
        help="Optional existing PX4 models directory containing x500_base",
    )
    args = parser.parse_args()
    manifest_path = MODELS / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"models": {}}
    manifest["unitree_commit"] = UNITREE_SHA
    if args.px4_models:
        shutil.copytree(args.px4_models / "x500_base", MODELS / "x500_base", dirs_exist_ok=True)
    if not (MODELS / "x500_base/model.sdf").exists():
        raise SystemExit(
            "Provide --px4-models /path/to/PX4/Tools/simulation/gz/models for the X500 source, or use the vendored assets in this repository."
        )
    manifest["models"]["x500_base"] = {
        "source": "https://github.com/PX4/PX4-gazebo-models/tree/main/models/x500_base",
        "use": "static vendor visuals; no motor plugins",
        "license": "BSD-3-Clause, see x500_base/LICENSE",
    }
    license_path = fetch("LICENSE", MODELS / "UNITREE_LICENSE")
    print("Fetching official Unitree G1 and Go2 meshes", flush=True)
    tasks = []
    for name, source, urdf_name in [
        ("unitree_g1", "robots/g1_description", "g1_29dof.urdf"),
        ("unitree_go2", "robots/go2_description", "urdf/go2_description.urdf"),
    ]:
        folder = MODELS / name
        urdf = fetch(source + "/" + urdf_name, folder / "robot.urdf")
        refs = {m.get("filename") for m in ET.parse(urdf).findall(".//mesh")}
        for ref in refs:
            rel = ref.split("/", 3)[3] if ref.startswith("package://") else ref
            tasks.append((source + "/" + rel, folder / rel))
        shutil.copyfile(license_path, folder / "LICENSE")
        manifest["models"][name] = {
            "source": "https://github.com/unitreerobotics/unitree_ros/tree/"
            + UNITREE_SHA
            + "/"
            + source,
            "urdf": urdf_name,
            "use": "static posed exhibit, no locomotion controller",
        }
    with ThreadPoolExecutor(max_workers=6) as pool:
        for p in pool.map(lambda a: fetch(*a), tasks):
            print(p.relative_to(ROOT), flush=True)
    # Some Collada files reference external texture images. Resolve only image nodes.
    for name in ["unitree_go2"]:
        folder = MODELS / name
        for dae in folder.rglob("*.dae"):
            tree = ET.parse(dae)
            for item in tree.findall(".//{*}library_images/{*}image/{*}init_from"):
                rel = (item.text or "").strip()
                if not rel or rel.startswith(("data:", "#")):
                    continue
                destination = (dae.parent / rel).resolve()
                if not destination.is_relative_to(folder.resolve()):
                    raise ValueError("Texture path outside vendor folder")
                path = destination.relative_to(folder.resolve()).as_posix()
                fetch("robots/go2_description/" + path, destination)
    ur = get_package_share_directory("ur_description")
    for kind in ["ur5e", "ur3e"]:
        folder = MODELS / kind
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            Path(ur) / "meshes" / kind / "visual", folder / "meshes", dirs_exist_ok=True
        )
        raw = subprocess.check_output(
            ["xacro", str(Path(ur) / "urdf/ur.urdf.xacro"), "ur_type:=" + kind, "name:=" + kind],
            text=True,
        )
        (folder / "robot.urdf").write_text(raw)
        licenses = Path("/usr/share/doc/ros-jazzy-ur-description/copyright")
        if licenses.exists():
            shutil.copyfile(licenses, folder / "COPYRIGHT")
        manifest["models"][kind] = {
            "source": "https://github.com/UniversalRobots/Universal_Robots_ROS2_Description",
            "installed_version": "3.5.1",
            "use": "static kinematically posed exhibit",
        }
    # The TurtleBot copy is visual only: simulator plugins/sensors are not imported.
    tb = Path(get_package_share_directory("nav2_minimal_tb4_description"))
    folder = MODELS / "turtlebot4_display"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tb / "meshes", folder / "meshes", dirs_exist_ok=True)
    raw = subprocess.check_output(
        ["xacro", str(tb / "urdf/standard/turtlebot4.urdf.xacro")], text=True
    )
    (folder / "robot.urdf").write_text(raw)
    copyright = Path("/usr/share/doc/ros-jazzy-nav2-minimal-tb4-description/copyright")
    if copyright.exists():
        shutil.copyfile(copyright, folder / "COPYRIGHT")
    manifest["models"]["turtlebot4_display"] = {
        "source": "https://github.com/ros-navigation/nav2_minimal_turtlebot_simulation",
        "use": "static exhibit; the navigation robot is a separate real simulated TB4",
    }
    manifest["files"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in MODELS.rglob("*")
        if p.is_file() and p.name != "asset_manifest.json"
    }
    (MODELS / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Offline mesh assets ready", flush=True)


if __name__ == "__main__":
    main()
