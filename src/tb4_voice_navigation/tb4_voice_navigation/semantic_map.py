"""Validated ROS trinary maps and semantic regions; no ROS runtime required."""

from pathlib import Path
import math
import cv2
import numpy as np
import yaml
from .coordinate_utils import pixel_to_map, map_to_pixel


class MapError(ValueError):
    pass


class OccupancyMap:
    def __init__(self, filename):
        self.path = Path(filename).resolve()
        self.metadata = yaml.safe_load(self.path.read_text())
        m = self.metadata
        if m.get("mode", "trinary") != "trinary":
            raise MapError("Only trinary map mode is supported")
        self.resolution = float(m["resolution"])
        self.origin = tuple(float(v) for v in m["origin"])
        if (
            len(self.origin) != 3
            or not all(math.isfinite(v) for v in self.origin)
            or not math.isfinite(self.resolution)
            or self.resolution <= 0
        ):
            raise MapError("Invalid resolution/origin")
        free, occupied = float(m["free_thresh"]), float(m["occupied_thresh"])
        if not 0 <= free < occupied <= 1 or m["negate"] not in (0, 1):
            raise MapError("Invalid thresholds/negate")
        self.image = cv2.imread(str(self.path.parent / m["image"]), cv2.IMREAD_UNCHANGED)
        if self.image is None or self.image.ndim != 2 or self.image.dtype != np.uint8:
            raise MapError("Expected 8-bit grayscale occupancy image")
        self.height, self.width = self.image.shape
        probability = self.image.astype(float) / 255
        if not m["negate"]:
            probability = 1 - probability
        self.free = probability < free
        self.occupied = probability > occupied
        self.unknown = ~(self.free | self.occupied)
        # Pad with blocked pixels: outside the map is never navigable.
        padded = np.pad(self.free.astype(np.uint8), 1)
        self.clearance = (
            cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
            * self.resolution
        )
        # Distance is to blocked cell centre; subtract half cell diagonal conservatively.
        self.clearance = np.maximum(0, self.clearance - self.resolution / math.sqrt(2))

    def to_map(self, col, row):
        return pixel_to_map(col, row, self.height, self.resolution, self.origin)

    def to_pixel(self, x, y):
        return map_to_pixel(x, y, self.height, self.resolution, self.origin)

    def cell(self, x, y):
        c, r = self.to_pixel(x, y)
        if not (math.isfinite(c) and math.isfinite(r)):
            raise MapError("Non-finite goal")
        c, r = math.floor(c + 0.5), math.floor(r + 0.5)
        if not (0 <= c < self.width and 0 <= r < self.height):
            raise MapError("Point outside map")
        return c, r

    def polygon_mask(self, polygon):
        p = np.asarray(polygon, dtype=float)
        if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
            raise MapError("Polygon must contain at least three finite vertices")
        if not np.equal(p, np.floor(p)).all():
            raise MapError("Polygon vertices must use integer pixel indices")
        if (
            (p[:, 0] < 0).any()
            or (p[:, 0] >= self.width).any()
            or (p[:, 1] < 0).any()
            or (p[:, 1] >= self.height).any()
        ):
            raise MapError("Polygon outside map")
        p = p.astype(np.int32)
        if abs(cv2.contourArea(p)) < 1:
            raise MapError("Degenerate polygon")

        # Reject intersecting non-adjacent edges, including collinear touching.
        def orient(a, b, c):
            return np.cross(b - a, c - a).item()

        def intersects(a, b, c, d):
            o = [orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)]
            if o[0] * o[1] < 0 and o[2] * o[3] < 0:
                return True
            for z, q, u, v in [(o[0], c, a, b), (o[1], d, a, b), (o[2], a, c, d), (o[3], b, c, d)]:
                if z == 0 and np.all(q >= np.minimum(u, v)) and np.all(q <= np.maximum(u, v)):
                    return True
            return False

        for i in range(len(p)):
            for j in range(i + 1, len(p)):
                if j == i + 1 or (i == 0 and j == len(p) - 1):
                    continue
                if intersects(p[i], p[(i + 1) % len(p)], p[j], p[(j + 1) % len(p)]):
                    raise MapError("Self-intersecting polygon")
        mask = np.zeros_like(self.image, dtype=np.uint8)
        cv2.fillPoly(mask, [p], 1)
        return mask.astype(bool)


class SemanticMap:
    def __init__(self, filename, map_file=None):
        self.path = Path(filename).resolve()
        data = yaml.safe_load(self.path.read_text())
        self.frame = data.get("map_frame", "map")
        self.map = OccupancyMap(map_file or self.path.parent / data["map_yaml"])
        self.min_clearance = float(data.get("min_clearance", 0.35))
        if not math.isfinite(self.min_clearance) or self.min_clearance < 0.22:
            raise MapError("Clearance must cover TB4 robot radius (0.22m)")
        _, self.components = cv2.connectedComponents(
            (self.map.free & (self.map.clearance >= self.min_clearance)).astype(np.uint8),
            connectivity=4,
        )
        anchor = data["reachable_from_map"]
        c, r = self.map.cell(*anchor)
        self.component = int(self.components[r, c])
        if not self.component:
            raise MapError("Reachability anchor is not in clearance-safe free space")
        self.regions = {}
        for source in data.get("regions", []):
            region = dict(source)
            key = str(region["id"])
            if not key or key in self.regions or not region.get("name"):
                raise MapError("Missing/duplicate region ID or name")
            region["id"] = key
            region["mask"] = self.map.polygon_mask(region["polygon_pixels"])
            region["valid"] = False
            try:
                if source.get("valid") is False:
                    raise MapError(source.get("invalid_reason", "Disabled by user"))
                self.validate_goal(region, region["goal"])
                region["valid"] = True
                region["invalid_reason"] = ""
            except (MapError, KeyError, TypeError, ValueError) as exc:
                region["invalid_reason"] = str(exc)
            self.regions[key] = region
        if not self.regions:
            raise MapError("No semantic regions")

    def validate_goal(self, region, goal):
        values = [float(goal[k]) for k in ("x", "y", "yaw")]
        if not all(math.isfinite(v) for v in values):
            raise MapError("Non-finite goal")
        c, r = self.map.cell(*values[:2])
        if not region["mask"][r, c]:
            raise MapError("Goal outside region polygon")
        if not self.map.free[r, c]:
            raise MapError("Goal in occupied/unknown cell")
        if self.map.clearance[r, c] < self.min_clearance:
            raise MapError("Insufficient obstacle clearance")
        if self.components[r, c] != self.component:
            raise MapError("Goal disconnected from navigable anchor")
        return float(self.map.clearance[r, c])

    def lookup(self, key):
        if key not in self.regions:
            raise MapError(f"Unknown region: {key}")
        region = self.regions[key]
        if not region["valid"]:
            raise MapError(f"Invalid region {key}: {region['invalid_reason']}")
        return region

    def select_goal(self, polygon, yaw=0):
        mask = self.map.polygon_mask(polygon)
        candidates = (
            mask
            & (self.components == self.component)
            & self.map.free
            & (self.map.clearance >= self.min_clearance)
        )
        if not candidates.any():
            raise MapError("No reachable goal with required clearance")
        score = np.where(candidates, self.map.clearance, -1)
        r, c = np.unravel_index(np.argmax(score), score.shape)
        x, y = self.map.to_map(int(c), int(r))
        return {"x": float(x), "y": float(y), "yaw": float(yaw)}
