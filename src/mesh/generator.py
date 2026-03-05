from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import trimesh

SCALE = 5


def generate_plane(height: float, width: float):
    corners = [
        [0, 0, 0],
        [0, width, 0],
        [height, width, 0],
        [height, 0, 0],
    ]
    faces = np.array([[0, 1, 2, 3]])
    plane = trimesh.Trimesh(vertices=corners, faces=faces)
    return plane, corners, faces


def initialize_plane(min_lat: float, min_lon: float, max_lat: float, max_lon: float):
    max_lat_scaled = int(max_lat * (10**SCALE))
    min_lat_scaled = int(min_lat * (10**SCALE))
    max_lon_scaled = int(max_lon * (10**SCALE))
    min_lon_scaled = int(min_lon * (10**SCALE))

    delta_lat = abs(max_lat_scaled - min_lat_scaled)
    delta_long = abs(max_lon_scaled - min_lon_scaled)

    plane, corners, faces = generate_plane(delta_lat, delta_long)
    return plane, corners, faces


def get_corners(footprint_latlon: List, min_lat: float, min_lon: float):
    corners = []
    for point in footprint_latlon:
        latitude = int(float(point[0]) * (10**SCALE))
        longitude = int(float(point[1]) * (10**SCALE))

        local_i = abs(latitude - int(min_lat * (10**SCALE)))
        local_j = abs(longitude - int(min_lon * (10**SCALE)))

        corners.append([local_i, local_j])
    return corners


def get_lines(corners: List, loop: bool = True):
    lines = []
    start = 0
    end = 1
    lines.append(trimesh.path.entities.Line([start, end]))

    for i in range(len(corners) - 2):
        start += 1
        end += 1
        lines.append(trimesh.path.entities.Line([start, end]))

    if loop:
        lines.append(trimesh.path.entities.Line([end, 0]))
    return lines


def build_scene(
    ingestion_data: Dict[str, Any], output_dir: str = "output_meshes"
) -> trimesh.Trimesh:
    """Takes ingested OSM data and builds 3D extruded building meshes."""
    bbox = ingestion_data.get("bbox_south_west_north_east", [0, 0, 0, 0])
    min_lat, min_lon, max_lat, max_lon = bbox[0], bbox[1], bbox[2], bbox[3]

    plane, plane_vertices, plane_faces = initialize_plane(min_lat, min_lon, max_lat, max_lon)
    buildings = [plane]

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    buildings_data = ingestion_data.get("buildings_joined", [])
    print(f"Extruding {len(buildings_data)} buildings...")

    for b in buildings_data:
        osm_id = b.get("osm_id", "unknown").replace("/", "_")
        corners = get_corners(b.get("footprint_latlon", []), min_lat, min_lon)
        lines = get_lines(corners)

        path = trimesh.path.path.Path2D(
            entities=lines,
            vertices=corners,
        )

        polys = path.polygons_closed
        if not polys or not polys[0]:
            continue

        height = b.get("height_m") or 3.0
        height = -1 * height
        mesh = path.extrude(height=height)

        if isinstance(mesh, list):
            mesh = trimesh.util.concatenate(
                [m.to_mesh() if hasattr(m, "to_mesh") else m for m in mesh]
            )
        else:
            if hasattr(mesh, "to_mesh"):
                mesh = mesh.to_mesh()

        mesh.export(str(out_path / f"{osm_id}.glb"), file_type="glb")
        buildings.append(mesh)

        combined_mesh = trimesh.util.concatenate(buildings)

        combined_mesh_path = out_path / "combined.glb"
        combined_mesh.export(str(combined_mesh_path))
        print(f"Saved combined building mesh to {combined_mesh_path}!")

        return combined_mesh
