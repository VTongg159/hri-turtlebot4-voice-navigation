"""Command validation shared by the live Nav2 controller and unit tests."""


class RequestError(ValueError):
    pass


def validate_request(command, semantic):
    if not isinstance(command, dict):
        raise RequestError("Command must be a JSON object")
    kind = command.get("type")
    points = command.get("waypoints")
    if kind == "cancel":
        return []
    if kind not in {"single", "source_destination", "multi_waypoint"}:
        raise RequestError("Invalid command type")
    if (
        not isinstance(points, list)
        or not 1 <= len(points) <= 12
        or any(not isinstance(p, str) for p in points)
    ):
        raise RequestError("Expected 1..12 region IDs")
    if kind == "single" and len(points) != 1:
        raise RequestError("Single requires one goal")
    if kind == "source_destination" and len(points) != 2:
        raise RequestError("Source/destination requires two goals")
    if kind == "multi_waypoint" and len(points) < 2:
        raise RequestError("Multi requires at least two goals")
    return [semantic.lookup(p) for p in points]


def same_goal_id(first, second):
    """ROS UUID storage may be numpy-backed; compare bytes, never array truth values."""
    return bytes(first.uuid) == bytes(second.uuid)
