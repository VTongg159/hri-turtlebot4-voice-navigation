"""Validate the new real scene assets, collision-derived map and voice aliases."""

from pathlib import Path
import json
import xml.etree.ElementTree as ET
import pytest
from tb4_voice_navigation.semantic_map import SemanticMap
from tb4_voice_navigation.command_parser import CommandParser

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scene():
    return SemanticMap(ROOT / "config/pairs_regions.yaml")


def test_pairslab_six_goals_are_reachable(scene):
    assert set(scene.regions) == set("ABCDEF")
    assert (scene.map.width, scene.map.height) == (580, 420)
    for region in scene.regions.values():
        assert scene.validate_goal(region, region["goal"]) >= 0.38


@pytest.mark.parametrize(
    "text,points",
    [
        ("Đi đến phòng UAV", ["A"]),
        ("Đi đến phòng tay máy", ["B"]),
        ("Đi đến khu HRI", ["D"]),
        ("Đi đến phòng robot hình người", ["D"]),
        ("Đi đến phòng humanoid", ["D"]),
        ("Đi đến phòng chó robot", ["E"]),
        ("Đi đến phòng Unitree Go2", ["E"]),
        ("Đi đến phòng TurtleBot", ["F"]),
        ("Đi đến sảnh", ["C"]),
        ("Đi từ phòng UAV qua hành lang đến phòng chó robot", ["A", "C", "E"]),
    ],
)
def test_pairslab_voice_aliases(scene, text, points):
    assert CommandParser(scene.regions).parse(text)["waypoints"] == points


def test_no_ambiguous_generic_laboratory(scene):
    assert CommandParser(scene.regions).parse_safe("Đi đến phòng thí nghiệm")["type"] == "error"


def test_model_meshes_and_textures_are_portable_and_present():
    tree = ET.parse(ROOT / "worlds/pairs_lab.sdf")
    refs = [e.text.strip() for e in tree.findall(".//uri") + tree.findall(".//albedo_map")]
    assert len(refs) > 100
    for ref in refs:
        assert ref.startswith("model://")
        path = ROOT / "models" / ref.removeprefix("model://")
        assert path.is_file(), ref
        assert "/home/" not in ref


def test_real_unitree_models_and_no_exhibit_control_plugins():
    root = ET.parse(ROOT / "worlds/pairs_lab.sdf").getroot()
    models = {m.get("name"): m for m in root.findall("world/model")}
    for name in ["unitree_g1_hri", "unitree_go2_terrain", "unitree_go2_inspection"]:
        model = models[name]
        assert model.findtext("static") == "true"
        assert model.findall(".//visual/geometry/mesh")
        assert not model.findall(".//plugin")
    assert (ROOT / "models/unitree_g1/LICENSE").is_file()
    assert (ROOT / "models/unitree_go2/LICENSE").is_file()


def test_doorway_centres_share_navigable_component(scene):
    for x, y in [(-9, 2), (0, 2), (9, 2), (-7, -2), (7, -2)]:
        col, row = scene.map.cell(x, y)
        assert scene.components[row, col] == scene.component
        assert scene.map.clearance[row, col] >= 0.38


def test_map_world_provenance():
    import yaml

    data = yaml.safe_load((ROOT / "maps/pairs_provenance.yaml").read_text())
    assert data["not_slam"] is True
    assert data["world"] == "pairs_lab.sdf"
    manifest = json.loads((ROOT / "models/asset_manifest.json").read_text())
    assert manifest["unitree_commit"] == "725b59b6de39a26c425632120c89f23c49a36f1e"
