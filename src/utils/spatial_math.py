import math
from typing import List, Tuple, Optional


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def wrap_angle_deg(a: float) -> float:
    return (a + 360) % 360


def angle_diff_deg(a: float, b: float) -> float:
    d = (a - b + 180) % 360 - 180
    return abs(d)


def meters_per_degree(lat: float) -> Tuple[float, float]:
    lat_rad = math.radians(lat)
    m_per_deg_lat = 111132.92
    m_per_deg_lon = 111412.84 * math.cos(lat_rad)
    return m_per_deg_lat, m_per_deg_lon


def latlon_to_local_xy(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    mlat, mlon = meters_per_degree(lat0)
    x = (lon - lon0) * mlon
    y = (lat - lat0) * mlat
    return x, y


def polygon_area_m2(polygon_latlon: List[Tuple[float, float]]) -> float:
    if len(polygon_latlon) < 3:
        return 0.0
    poly = polygon_latlon
    if len(poly) >= 4 and poly[0] == poly[-1]:
        poly = poly[:-1]
    if len(poly) < 3:
        return 0.0
    lat0 = sum(p[0] for p in poly) / len(poly)
    lon0 = sum(p[1] for p in poly) / len(poly)
    pts = [latlon_to_local_xy(lat, lon, lat0, lon0) for lat, lon in poly]
    area2 = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area2 += x1 * y2 - x2 * y1
    return abs(area2) * 0.5


def clean_polygon_latlon(poly: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if not poly:
        return poly
    cleaned = [poly[0]]
    for p in poly[1:]:
        if p != cleaned[-1]:
            cleaned.append(p)
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1]:
        cleaned = cleaned[:-1]
    if len(cleaned) >= 3 and cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    return cleaned


def point_in_polygon(lat: float, lon: float, polygon_latlon: List[Tuple[float, float]]) -> bool:
    x, y = lon, lat
    inside = False
    n = len(polygon_latlon)
    if n < 3:
        return False
    for i in range(n - 1):
        y1, x1 = polygon_latlon[i]
        y2, x2 = polygon_latlon[i + 1]
        if (y1 > y) != (y2 > y):
            xinters = (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-12) + x1
            if x < xinters:
                inside = not inside
    return inside


def point_in_polygon_with_holes(
    lat: float,
    lon: float,
    outer_ring_closed: List[Tuple[float, float]],
    inner_rings_closed: Optional[List[List[Tuple[float, float]]]] = None,
) -> bool:
    if not outer_ring_closed or len(outer_ring_closed) < 4:
        return False
    if not point_in_polygon(lat, lon, outer_ring_closed):
        return False
    if inner_rings_closed:
        for hole in inner_rings_closed:
            if hole and len(hole) >= 4 and point_in_polygon(lat, lon, hole):
                return False
    return True


def point_to_segment_distance_m(
    p_lat: float, p_lon: float, a_lat: float, a_lon: float, b_lat: float, b_lon: float
) -> Tuple[float, float]:
    px, py = latlon_to_local_xy(p_lat, p_lon, p_lat, p_lon)
    ax, ay = latlon_to_local_xy(a_lat, a_lon, p_lat, p_lon)
    bx, by = latlon_to_local_xy(b_lat, b_lon, p_lat, p_lon)

    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby

    if ab2 <= 1e-12:
        return math.hypot(px - ax, py - ay), 0.0

    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx, cy = ax + t * abx, ay + t * aby
    return math.hypot(px - cx, py - cy), t
