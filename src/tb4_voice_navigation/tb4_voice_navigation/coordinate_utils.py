"""Pixel centres ↔ map coordinates, including rotated origins."""

import math


def pixel_to_map(col, row, height, resolution, origin):
    u, v = (col + 0.5) * resolution, (height - row - 0.5) * resolution
    c, s = math.cos(origin[2]), math.sin(origin[2])
    return origin[0] + c * u - s * v, origin[1] + s * u + c * v


def map_to_pixel(x, y, height, resolution, origin):
    dx, dy = x - origin[0], y - origin[1]
    c, s = math.cos(origin[2]), math.sin(origin[2])
    return (c * dx + s * dy) / resolution - 0.5, height - (-s * dx + c * dy) / resolution - 0.5


def yaw_to_quaternion(yaw):
    return 0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)
