"""Geographic helpers -- kept tiny and dependency-free (just math)."""
from __future__ import annotations

import math
from typing import Iterable, Tuple

EARTH_RADIUS_KM = 6371.0088

Coord = Tuple[float, float]


def haversine_km(a: Coord, b: Coord) -> float:
    """Great-circle distance between two (lat, lon) points in kilometres."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def centroid(points: Iterable[Coord]) -> Coord:
    """Mean latitude/longitude of a set of points."""
    pts = list(points)
    if not pts:
        return (0.0, 0.0)
    lat = sum(p[0] for p in pts) / len(pts)
    lon = sum(p[1] for p in pts) / len(pts)
    return (lat, lon)


def gaussian_decay(distance_km: float, scale_km: float) -> float:
    """Smooth 1->0 influence weight that fades with distance."""
    if scale_km <= 0:
        return 0.0
    return math.exp(-(distance_km ** 2) / (2 * scale_km ** 2))
