from typing import Any, Dict, List, Tuple, Optional
from src.utils.spatial_math import clean_polygon_latlon, polygon_area_m2, point_in_polygon


def parse_height_m(tags: Dict[str, Any]) -> Optional[float]:
    h = tags.get("height")
    if isinstance(h, str):
        s = h.strip().lower().replace("meters", "m").replace(" ", "")
        try:
            if s.endswith("m"):
                s = s[:-1]
            return float(s)
        except Exception:
            pass
    lv = tags.get("building:levels")
    if isinstance(lv, str):
        try:
            return max(1.0, float(lv.strip())) * 3.0
        except Exception:
            pass
    return None


def _way_nodes_latlon(
    way: Dict[str, Any], nodes_by_id: Dict[int, Tuple[float, float]]
) -> List[Tuple[float, float]]:
    return [
        p
        for p in (nodes_by_id.get(nid) for nid in (way.get("nodes") or []))
        if p and p[0] is not None and p[1] is not None
    ]


def _stitch_rings_from_way_node_lists(
    way_node_lists: List[List[Tuple[float, float]]],
) -> List[List[Tuple[float, float]]]:
    segments = [seg for seg in way_node_lists if seg and len(seg) >= 2]
    rings = []
    while segments:
        ring = segments.pop(0)[:]
        changed = True
        while changed and segments:
            changed = False
            end, start = ring[-1], ring[0]
            if len(ring) >= 3 and ring[0] == ring[-1]:
                break
            for i, seg in enumerate(segments):
                s0, s1 = seg[0], seg[-1]
                if end == s0:
                    ring.extend(seg[1:])
                    segments.pop(i)
                    changed = True
                    break
                if end == s1:
                    ring.extend(list(reversed(seg[:-1])))
                    segments.pop(i)
                    changed = True
                    break
                if start == s1:
                    ring = seg[:-1] + ring
                    segments.pop(i)
                    changed = True
                    break
                if start == s0:
                    ring = list(reversed(seg[1:])) + ring
                    segments.pop(i)
                    changed = True
                    break
        ring = clean_polygon_latlon(ring)
        if len(ring) >= 4 and ring[0] == ring[-1]:
            rings.append(ring)
    return rings


def _extract_relation_multipolygon_rings(
    rel: Dict[str, Any],
    ways_by_id: Dict[int, Dict[str, Any]],
    nodes_by_id: Dict[int, Tuple[float, float]],
) -> Tuple[List[List[Tuple[float, float]]], List[List[Tuple[float, float]]]]:
    outer_way_lists, inner_way_lists = [], []
    for m in rel.get("members", []):
        if m.get("type") == "way" and (way := ways_by_id.get(m.get("ref"))):
            pts = _way_nodes_latlon(way, nodes_by_id)
            if len(pts) >= 2:
                (
                    inner_way_lists
                    if (m.get("role") or "").strip().lower() == "inner"
                    else outer_way_lists
                ).append(pts)
    return (
        _stitch_rings_from_way_node_lists(outer_way_lists) if outer_way_lists else [],
        _stitch_rings_from_way_node_lists(inner_way_lists) if inner_way_lists else [],
    )


def extract_osm_buildings(overpass_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    elements = overpass_json.get("elements", [])
    nodes_by_id = {
        e["id"]: (e["lat"], e["lon"])
        for e in elements
        if e.get("type") == "node" and e.get("id") is not None
    }
    ways_by_id = {
        e["id"]: e for e in elements if e.get("type") == "way" and e.get("id") is not None
    }
    buildings = []

    for e in elements:
        if e.get("type") != "way" or "building" not in (tags := e.get("tags", {}) or {}):
            continue
        footprint = clean_polygon_latlon(_way_nodes_latlon(e, nodes_by_id))
        if len(footprint) < 4 or polygon_area_m2(footprint) < 5.0:
            continue
        verts = footprint[:-1]
        buildings.append(
            {
                "osm_id": f"way/{e.get('id')}",
                "osm_type": "way",
                "tags": tags,
                "height_m": parse_height_m(tags),
                "footprint_latlon": footprint,
                "holes_latlon": [],
                "centroid_latlon": (
                    sum(p[0] for p in verts) / len(verts),
                    sum(p[1] for p in verts) / len(verts),
                ),
            }
        )

    for e in elements:
        if e.get("type") != "relation" or "building" not in (tags := e.get("tags", {}) or {}):
            continue
        outer_rings, inner_rings = _extract_relation_multipolygon_rings(e, ways_by_id, nodes_by_id)
        if not outer_rings:
            continue
        outer_rings_sorted = sorted(outer_rings, key=polygon_area_m2, reverse=True)
        primary_outer = outer_rings_sorted[0]
        if len(primary_outer) < 4 or polygon_area_m2(primary_outer) < 5.0:
            continue

        valid_holes = [
            hole
            for hole in inner_rings
            if len(hole) >= 4
            and point_in_polygon(
                sum(p[0] for p in hole[:-1]) / len(hole[:-1]),
                sum(p[1] for p in hole[:-1]) / len(hole[:-1]),
                primary_outer,
            )
        ]
        verts = primary_outer[:-1]
        buildings.append(
            {
                "osm_id": f"relation/{e.get('id')}",
                "osm_type": "relation",
                "tags": tags,
                "height_m": parse_height_m(tags),
                "footprint_latlon": primary_outer,
                "holes_latlon": valid_holes,
                "centroid_latlon": (
                    sum(p[0] for p in verts) / len(verts),
                    sum(p[1] for p in verts) / len(verts),
                ),
                "outer_rings_latlon": outer_rings_sorted,
            }
        )

    return buildings
