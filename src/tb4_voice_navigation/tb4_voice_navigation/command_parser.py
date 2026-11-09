"""Conservative, offline Vietnamese command grammar with exact semantic aliases."""

import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9\s]", " ", text).split())


class CommandError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class CommandParser:
    def __init__(self, regions):
        self.aliases = {}
        for key, region in regions.items():
            for alias in [key, region["name"], *region.get("aliases", [])]:
                name = normalize(str(alias))
                if not name:
                    raise ValueError("Empty region alias")
                self.aliases.setdefault(name, set()).add(str(key))

    def destination(self, text):
        name = normalize(text)
        candidates = self.aliases.get(name, set())
        if not candidates:
            raise CommandError("UNKNOWN_REGION", f"Không tìm thấy khu vực: {text}")
        if len(candidates) != 1:
            raise CommandError("AMBIGUOUS_REGION", f"Tên khu vực không duy nhất: {text}")
        return next(iter(candidates))

    def parse(self, text):
        s = normalize(text)
        if not s:
            raise CommandError("EMPTY_COMMAND", "Câu lệnh trống")
        if s in {
            "dung lai",
            "dung",
            "huy dieu huong",
            "huy",
            "robot dung lai",
            "robot dung",
            "stop",
        }:
            return dict(type="cancel", waypoints=[])
        # Accept only an explicit motion imperative, then parse every destination.
        s = re.sub(r"^(?:hay |vui long )", "", s)
        s = re.sub(r"^robot ", "", s)
        match = re.match(r"^(?:(?:di chuyen|di) (?:den|toi|tu)|den|toi) (.+)$", s)
        if not match:
            raise CommandError("INVALID_SYNTAX", "Cần lệnh đi đến, đi từ ... đến ... hoặc dừng lại")
        source = bool(re.match(r"^(?:di chuyen|di) tu ", s))
        body = match.group(1)
        # Long connectors first; all text between connectors must be an exact alias.
        parts = re.split(
            r"\s+(?:roi den|roi toi|sau do den|sau do toi|sau do|roi|qua|den|toi)\s+", body
        )
        if len(parts) > 12:
            raise CommandError("TOO_MANY_WAYPOINTS", "Tối đa 12 điểm trong một lệnh")
        if source and len(parts) < 2:
            raise CommandError("MISSING_DESTINATION", "Lệnh từ A cần thêm đích đến")
        waypoints = [self.destination(p) for p in parts]
        kind = (
            "single"
            if len(waypoints) == 1
            else "source_destination"
            if source and len(waypoints) == 2
            else "multi_waypoint"
        )
        return dict(type=kind, waypoints=waypoints, starts_from_source=source)

    def parse_safe(self, text):
        try:
            return self.parse(text)
        except CommandError as exc:
            return dict(type="error", waypoints=[], error=dict(code=exc.code, message=str(exc)))
