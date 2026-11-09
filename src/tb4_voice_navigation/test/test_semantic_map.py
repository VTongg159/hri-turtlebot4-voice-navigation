from pathlib import Path
import math
import numpy as np
import pytest
from tb4_voice_navigation.coordinate_utils import pixel_to_map, map_to_pixel, yaw_to_quaternion
from tb4_voice_navigation.semantic_map import SemanticMap, MapError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("yaw", [0, math.pi / 2, -math.pi / 3, math.pi])
@pytest.mark.parametrize("pixel", [(0, 0), (299, 219), (149.25, 100.75)])
def test_roundtrip(yaw, pixel):
    origin = (-7.5, -5.5, yaw)
    xy = pixel_to_map(*pixel, 220, 0.05, origin)
    assert map_to_pixel(*xy, 220, 0.05, origin) == pytest.approx(pixel, abs=1e-10)


def test_known_pixel_centres():
    assert pixel_to_map(0, 219, 220, 0.05, (-7.5, -5.5, 0)) == pytest.approx((-7.475, -5.475))
    assert pixel_to_map(0, 219, 220, 0.05, (1, 2, math.pi / 2)) == pytest.approx((0.975, 2.025))


def test_quaternion():
    assert yaw_to_quaternion(math.pi) == pytest.approx((0, 0, 1, 0), abs=1e-12)


@pytest.fixture
def semantic():
    return SemanticMap(ROOT / "config/regions.yaml")


def test_read_real_map(semantic):
    m = semantic.map
    assert (m.width, m.height) == (300, 220)
    assert np.all(m.free.astype(int) + m.occupied.astype(int) + m.unknown.astype(int) == 1)
    assert m.unknown.any() and m.occupied.any() and m.free.any()


def test_all_five_goals_valid(semantic):
    assert len(semantic.regions) == 5
    for key in "ABCDE":
        r = semantic.lookup(key)
        assert semantic.validate_goal(r, r["goal"]) >= 0.35


def test_goal_in_wall_rejected(semantic):
    r = {"mask": np.ones_like(semantic.map.free)}
    with pytest.raises(MapError, match="occupied/unknown"):
        semantic.validate_goal(r, dict(x=0, y=3, yaw=0))


def test_unknown_rejected(semantic):
    r = {"mask": np.ones_like(semantic.map.free)}
    with pytest.raises(MapError, match="occupied/unknown"):
        semantic.validate_goal(r, dict(x=7.4, y=5.4, yaw=0))


def test_goal_outside_polygon(semantic):
    with pytest.raises(MapError, match="outside region"):
        semantic.validate_goal(semantic.lookup("A"), dict(x=3.5, y=2.1, yaw=0))


def test_insufficient_clearance(semantic):
    r = {"mask": np.ones_like(semantic.map.free)}
    with pytest.raises(MapError, match="clearance"):
        semantic.validate_goal(r, dict(x=-6.8, y=0, yaw=0))


def test_nonfinite_goal(semantic):
    with pytest.raises(MapError, match="Non-finite"):
        semantic.validate_goal(semantic.lookup("A"), dict(x=float("nan"), y=0, yaw=0))


def test_unknown_region(semantic):
    with pytest.raises(MapError, match="Unknown region"):
        semantic.lookup("Z")


@pytest.mark.parametrize(
    "polygon",
    [
        [[0, 0], [300, 0], [10, 10]],
        [[1, 1], [1, 1], [1, 1]],
        [[10, 10], [90, 90], [10, 90], [90, 10]],
        [[1.5, 1], [2, 2], [3, 1]],
    ],
)
def test_bad_polygons(semantic, polygon):
    with pytest.raises(MapError):
        semantic.map.polygon_mask(polygon)


def test_select_safe_goal(semantic):
    for r in semantic.regions.values():
        g = semantic.select_goal(r["polygon_pixels"])
        assert semantic.validate_goal(r, g) >= 0.35


def test_reject_polygon_without_navigable_goal(semantic):
    with pytest.raises(MapError, match="No reachable goal"):
        semantic.select_goal([[0, 0], [5, 0], [5, 5], [0, 5]])


def test_doorways_connect_rooms(semantic):
    for x in [-3.5, 3.5]:
        for y in [-1.2, 1.2]:
            c, r = semantic.map.cell(x, y)
            assert semantic.components[r, c] == semantic.component
            assert semantic.map.clearance[r, c] >= 0.35
