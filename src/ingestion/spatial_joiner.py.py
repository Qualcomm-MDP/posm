from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from src.utils.spatial_math import (
    point_to_segment_distance_m,
    bearing_deg,
    wrap_angle_deg,
    angle_diff_deg,
    point_in_polygon_with_holes,
    haversine_m,
)
from src.ingestion.osm_parser import extract_osm_buildings
from src.ingestion.api_client import download_thumbnail


@dataclass
class EdgeInfo:
    distance_m: float
    edge_index: int
    closest_point_lat: float
    closest_point_lon: float
    edge_bearing_deg: float
    facade_normal_deg: float


def nearest_edge_info(
    cam_lat: float, cam_lon: float, polygon_latlon_closed: List[Tuple[float, float]]
) -> Optional[EdgeInfo]:
    if len(polygon_latlon_closed) < 4:
        return None
    best_d, best_i, best_t = float("inf"), -1, 0.0

    for i in range(len(polygon_latlon_closed) - 1):
        a_lat, a_lon = polygon_latlon_closed[i]
        b_lat, b_lon = polygon_latlon_closed[i + 1]
        d, t = point_to_segment_distance_m(cam_lat, cam_lon, a_lat, a_lon, b_lat, b_lon)
        if d < best_d:
            best_d, best_i, best_t = d, i, t

    a_lat, a_lon = polygon_latlon_closed[best_i]
    b_lat, b_lon = polygon_latlon_closed[best_i + 1]
    cp_lat = a_lat + best_t * (b_lat - a_lat)
    cp_lon = a_lon + best_t * (b_lon - a_lon)
    e_bearing = bearing_deg(a_lat, a_lon, b_lat, b_lon)

    n1, n2 = wrap_angle_deg(e_bearing + 90), wrap_angle_deg(e_bearing - 90)
    b_cp_to_cam = bearing_deg(cp_lat, cp_lon, cam_lat, cam_lon)
    n = n1 if angle_diff_deg(n1, b_cp_to_cam) <= angle_diff_deg(n2, b_cp_to_cam) else n2

    return EdgeInfo(best_d, best_i, cp_lat, cp_lon, e_bearing, n)


def mapillary_pose(img: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coords = img.get("computed_geometry", {}).get("coordinates")
    heading = img.get("computed_compass_angle")
    if (
        not isinstance(coords, list)
        or len(coords) < 2
        or coords[1] is None
        or coords[0] is None
        or heading is None
    ):
        return None
    return {
        "lat": float(coords[1]),
        "lon": float(coords[0]),
        "heading": float(heading),
        "captured_at": img.get("captured_at"),
    }


def is_approx_daylight(lat: float, lon: float, captured_at_ms: Optional[int]) -> bool:
    if captured_at_ms is None:
        return True
    try:
        dt_utc = datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc)
        return 7.0 <= (dt_utc.hour + (dt_utc.minute / 60.0) + (lon / 15.0)) % 24 <= 19.0
    except Exception:
        return True


def score_candidate(distance_m: float, heading_delta_deg: float) -> float:
    score = sum(
        [
            2.0
            if distance_m <= 15
            else 1.5
            if distance_m <= 30
            else 1.0
            if distance_m <= 50
            else 0.5
            if distance_m <= 80
            else 0.0,
            2.0
            if heading_delta_deg <= 15
            else 1.5
            if heading_delta_deg <= 30
            else 1.0
            if heading_delta_deg <= 45
            else 0.5
            if heading_delta_deg <= 60
            else 0.0,
        ]
    )
    return round(score - min(distance_m / 200.0, 0.6), 4)


def dynamic_heading_threshold_deg(distance_m: float) -> float:
    return (
        60.0
        if distance_m <= 15
        else 45.0
        if distance_m <= 30
        else 30.0
        if distance_m <= 50
        else 25.0
    )


def thin_sequence(
    images: List[Dict[str, Any]], min_move_m: float = 2.0, min_heading_change_deg: float = 5.0
) -> List[Dict[str, Any]]:
    kept, last = [], None
    for img in images:
        if (
            last is None
            or haversine_m(
                img["pose"]["lat"], img["pose"]["lon"], last["pose"]["lat"], last["pose"]["lon"]
            )
            >= min_move_m
            or angle_diff_deg(img["pose"].get("heading", 0.0), last["pose"].get("heading", 0.0))
            >= min_heading_change_deg
        ):
            kept.append(img)
            last = img
    return kept


def spatial_join_data(
    osm_raw_json: Dict[str, Any],
    mapillary_raw_list: List[Dict[str, Any]],
    output_dir: Path,
    max_distance_m: float = 50.0,
) -> Dict[str, Any]:
    """Matches raw mapillary data to parsed OSM buildings in memory."""
    buildings = extract_osm_buildings(osm_raw_json)
    b_by_id = {b["osm_id"]: {**b, "assigned_images": []} for b in buildings}
    kept_images, discarded_urls = [], []

    for img in mapillary_raw_list:
        pose = mapillary_pose(img)
        url = img.get("thumb_original_url")
        if (
            not url
            or pose is None
            or not buildings
            or not is_approx_daylight(pose["lat"], pose["lon"], pose["captured_at"])
        ):
            if url:
                discarded_urls.append(url)
            continue

        candidates = []
        for b in buildings:
            if point_in_polygon_with_holes(
                pose["lat"], pose["lon"], b["footprint_latlon"], b.get("holes_latlon")
            ):
                continue
            if (ei := nearest_edge_info(pose["lat"], pose["lon"], b["footprint_latlon"])) is None:
                continue

            heading_delta = angle_diff_deg(
                pose["heading"],
                bearing_deg(pose["lat"], pose["lon"], ei.closest_point_lat, ei.closest_point_lon),
            )
            candidates.append(
                {
                    "osm_id": b["osm_id"],
                    "distance_to_edge_m": round(ei.distance_m, 3),
                    "closest_edge_index": ei.edge_index,
                    "heading_delta_deg": round(heading_delta, 2),
                    "visibility_score": score_candidate(ei.distance_m, heading_delta),
                }
            )

        candidates.sort(key=lambda c: (-c["visibility_score"], c["distance_to_edge_m"]))
        best = candidates[0] if candidates else None

        if (
            best is None
            or best["distance_to_edge_m"] > max_distance_m
            or best["heading_delta_deg"] > dynamic_heading_threshold_deg(best["distance_to_edge_m"])
        ):
            discarded_urls.append(url)
            continue

        local_thumb_path = download_thumbnail(url, img["id"], output_dir)
        join_info = {
            "image_id": img["id"],
            "url": url,
            "pose": pose,
            "best_candidate": best,
            "assigned_building": best["osm_id"],
            "local_thumb_path": local_thumb_path,
        }
        b_by_id[best["osm_id"]]["assigned_images"].append(join_info)
        kept_images.append(join_info)

    return {
        "buildings_joined": list(b_by_id.values()),
        "mapillary_kept": kept_images,
        "discarded_urls": discarded_urls,
    }
