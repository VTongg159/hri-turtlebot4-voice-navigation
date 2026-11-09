from pathlib import Path
import pytest
from tb4_voice_navigation.command_parser import CommandParser, normalize
from tb4_voice_navigation.semantic_map import SemanticMap
from tb4_voice_navigation.navigation_policy import validate_request, RequestError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def semantic():
    return SemanticMap(ROOT / "config/regions.yaml")


@pytest.fixture
def parser(semantic):
    return CommandParser(semantic.regions)


@pytest.mark.parametrize(
    "text,kind,points",
    [
        ("Đi đến khu vực A.", "single", ["A"]),
        ("Di chuyển đến phòng học.", "single", ["A"]),
        ("Robot đến phòng thí nghiệm.", "single", ["B"]),
        ("Đi từ A đến B", "source_destination", ["A", "B"]),
        ("Di chuyển từ khu vực A đến khu vực B.", "source_destination", ["A", "B"]),
        ("Đi từ phòng học đến phòng thí nghiệm.", "source_destination", ["A", "B"]),
        ("Đi từ phòng A qua hành lang C rồi đến phòng B.", "multi_waypoint", ["A", "C", "B"]),
        ("Đi đến khu vực A, sau đó đến B.", "multi_waypoint", ["A", "B"]),
        ("  ĐI   TỪ A QUA C ĐẾN B!!! ", "multi_waypoint", ["A", "C", "B"]),
        ("di den phong lab", "single", ["B"]),
        ("Vui lòng đi đến phòng họp", "single", ["D"]),
        ("Đi đến khu nghỉ", "single", ["E"]),
        ("Đi từ A đến A", "source_destination", ["A", "A"]),
    ],
)
def test_valid_commands(parser, text, kind, points):
    result = parser.parse(text)
    assert result["type"] == kind and result["waypoints"] == points


@pytest.mark.parametrize(
    "text,code",
    [
        ("Đi đến khu vực Z", "UNKNOWN_REGION"),
        ("Đi từ A qua Z đến B", "UNKNOWN_REGION"),
        ("Đi đến A rồi đến Z", "UNKNOWN_REGION"),
        ("Đi đến phòng ăn", "UNKNOWN_REGION"),
        ("Đi từ A", "MISSING_DESTINATION"),
        ("", "EMPTY_COMMAND"),
        ("không đi đến A", "INVALID_SYNTAX"),
        ("Hôm nay phòng học đẹp", "INVALID_SYNTAX"),
        ("Đi đến A hoặc B", "UNKNOWN_REGION"),
        ("Đi đến A B", "UNKNOWN_REGION"),
        ("Đi đến A rồi", "UNKNOWN_REGION"),
        ("Đi đến A nhưng không đến B", "UNKNOWN_REGION"),
    ],
)
def test_reject_whole_ambiguous_or_unknown_command(parser, text, code):
    result = parser.parse_safe(text)
    assert result["type"] == "error" and result["waypoints"] == []
    assert result["error"]["code"] == code


@pytest.mark.parametrize("text", ["Dừng lại", "Hủy điều hướng", "Robot dừng lại", "STOP"])
def test_cancel(parser, text):
    assert parser.parse(text) == dict(type="cancel", waypoints=[])


def test_source_semantics(parser):
    assert parser.parse("Đi từ A qua C đến B")["starts_from_source"] is True
    assert parser.parse("Đi đến A rồi đến B")["starts_from_source"] is False


def test_alias_collision_rejected():
    parser = CommandParser(
        {
            "A": dict(name="Room A", aliases=["phòng chung"]),
            "B": dict(name="Room B", aliases=["phòng chung"]),
        }
    )
    assert parser.parse_safe("Đi đến phòng chung")["error"]["code"] == "AMBIGUOUS_REGION"


def test_unicode_normalization():
    assert normalize("ĐI ĐẾN PHÒNG THÍ NGHIỆM") == "di den phong thi nghiem"


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"type": "other", "waypoints": ["A"]},
        {"type": "single", "waypoints": ["A", "B"]},
        {"type": "single", "waypoints": "A"},
        {"type": "source_destination", "waypoints": ["A"]},
        {"type": "multi_waypoint", "waypoints": ["A"]},
    ],
)
def test_request_shape(semantic, value):
    with pytest.raises(RequestError):
        validate_request(value, semantic)


def test_lookup_all_before_navigation(semantic):
    with pytest.raises(ValueError):
        validate_request(dict(type="multi_waypoint", waypoints=["A", "Z"]), semantic)


def test_valid_request(semantic):
    result = validate_request(dict(type="multi_waypoint", waypoints=["A", "C", "B"]), semantic)
    assert [r["id"] for r in result] == ["A", "C", "B"]


def test_actual_ros_uuid_equality_regression():
    from unique_identifier_msgs.msg import UUID
    from tb4_voice_navigation.navigation_policy import same_goal_id

    first = UUID(uuid=list(range(16)))
    second = UUID(uuid=list(range(16)))
    other = UUID(uuid=[0] * 16)
    assert same_goal_id(first, second) is True
    assert same_goal_id(first, other) is False
