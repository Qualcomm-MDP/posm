import math
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
import requests
import trimesh

# Hyperparameters preserved from original script
SCALE = 5
interval = 50
altitude = 1.83
FOCAL_LENGTH = 3165


def shoot_rays_for_image(
    CAMERA_LOC: Tuple[float, float],
    HEADING: float,
    INPUT_IMG: str,
    image_id: str,
    bbox: List[float],
    street_mesh: trimesh.Trimesh,
    visibility_score: float,
) -> Tuple[List[Dict[str, Any]], List[List[float]], List[List[float]]]:
    """
    Casts rays from the camera's perspective into the scene and records the hits.
    Returns: (list_of_face_hits, list_of_image_colors, list_of_mesh_colors)
    """
    # 1. Fetch and decode the Mapillary image
    res = requests.get(INPUT_IMG)
    if res.status_code != 200:
        return [], [], []

    img_array = np.frombuffer(res.content, np.uint8)
    splatter_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    splatter_img = cv2.cvtColor(splatter_img, cv2.COLOR_BGR2RGB)

    height, width, _ = splatter_img.shape

    MIN_LAT, MIN_LON, MAX_LAT, MAX_LON = bbox[0], bbox[1], bbox[2], bbox[3]

    # 2. Convert coordinates to local metric space
    converted_min_lon = int(MIN_LON * 10**SCALE)
    converted_min_lat = int(MIN_LAT * 10**SCALE)
    converted_cam_lat = int(CAMERA_LOC[0] * 10**SCALE)
    converted_cam_lon = int(CAMERA_LOC[1] * 10**SCALE)

    local_cam_lat = converted_cam_lat - converted_min_lat
    local_cam_lon = converted_cam_lon - converted_min_lon

    ray_origin = np.array([[local_cam_lat, local_cam_lon, -1 * altitude]])

    # 3. Calculate camera FOV and headings
    HOR_FOV = math.atan((width / 2) / FOCAL_LENGTH)
    VERT_FOV = math.atan((height / 2) / FOCAL_LENGTH)

    MIN_HEADING = math.radians(HEADING) - HOR_FOV

    delta_heading = (HOR_FOV * 2) / int(width / interval)
    delta_tilt = (VERT_FOV * 2) / int(height / interval)
    height_center = int(height / 2)

    rays = []
    colors = []
    heading = MIN_HEADING

    # 4. Sweep the rays across the image
    for i in range(0, width, interval):
        x = math.cos(heading)
        y = math.sin(heading)
        tilt = 0

        column_colors = []
        column_rays = []

        height_offset = 0
        focal_length_adj = abs(FOCAL_LENGTH / math.cos(abs(math.radians(HEADING) - heading)))

        while height_offset <= int(height_center):
            tilt_sin = math.sin(tilt)
            column_rays.append(np.array([[x, y, tilt_sin]]))
            column_rays.append(np.array([[x, y, -1 * tilt_sin]]))

            if height_center + height_offset < height and i < width:
                column_colors.append(splatter_img[height_center + height_offset][i].tolist())
                column_colors.append(splatter_img[height_center - height_offset][i].tolist())
            else:
                column_colors.append([255, 255, 255])
                column_colors.append([255, 255, 255])

            tilt += delta_tilt
            denom = math.sin((math.pi / 2) - tilt)
            height_offset = abs(
                int((focal_length_adj * math.sin(tilt)) / (denom if denom != 0 else 0.0001))
            )

        colors.append(column_colors)
        rays.append(column_rays)
        heading += delta_heading

    # 5. Calculate Intersections and Record Data
    face_hits = []
    image_colors = []
    mesh_colors = []

    for i, column_ray in enumerate(rays):
        for j, ray in enumerate(column_ray):
            locations, index_ray, index_tri = street_mesh.ray.intersects_location(
                ray_origins=ray_origin, ray_directions=ray, multiple_hits=False
            )

            if len(locations) != 0:
                tri_index = int(index_tri[0])
                hit_loc = locations[0]

                # Calculate distance from camera to hit
                distance = float(np.linalg.norm(hit_loc - ray_origin[0]))

                # Basic occlusion check (if ray hits something much closer than expected)
                is_occluded = distance < 2.0

                # Record the hit for the evaluation module
                face_hits.append(
                    {
                        "face_id": tri_index,
                        "image_id": image_id,
                        "distance": distance,
                        "is_occluded": is_occluded,
                        "visibility_score": visibility_score,
                    }
                )

                # Record the colors for correlation scoring
                image_colors.append(colors[i][j])

                # Extract the mesh color at this triangle
                if (
                    hasattr(street_mesh.visual, "vertex_colors")
                    and street_mesh.visual.vertex_colors is not None
                ):
                    triangle_vertex_indices = street_mesh.faces[tri_index]
                    tri_vertex_colors = street_mesh.visual.vertex_colors[triangle_vertex_indices]
                    avg_color = tri_vertex_colors.mean(axis=0).tolist()
                    mesh_colors.append(avg_color)
                else:
                    mesh_colors.append([128, 128, 128, 255])  # Fallback gray

    return face_hits, image_colors, mesh_colors


def run_raycaster(
    ingestion_data: Dict[str, Any], combined_mesh_path: str = "combined.glb"
) -> Dict[str, Any]:
    """
    Iterates through all kept images, fires rays, and packages the data for the evaluation module.
    """
    print(f"Loading mesh from {combined_mesh_path}...")
    street_mesh = trimesh.load_mesh(combined_mesh_path)

    bbox = ingestion_data.get("bbox_south_west_north_east", [0, 0, 0, 0])
    mapillary_kept = ingestion_data.get("mapillary_kept", [])

    all_image_colors = []
    all_mesh_colors = []
    faces_data = {}  # Maps face_id to a list of hits

    print(f"Raycasting {len(mapillary_kept)} images...")

    for entry in mapillary_kept:
        pose = entry.get("pose", {})
        CAMERA_LOC = (pose.get("lat"), pose.get("lon"))
        HEADING = pose.get("heading")
        INPUT_IMG = entry.get("url")
        image_id = entry.get("image_id", "unknown")

        # Grab the visibility score calculated during ingestion
        visibility_score = entry.get("best_candidate", {}).get("visibility_score", 0.0)

        if CAMERA_LOC[0] and CAMERA_LOC[1] and HEADING and INPUT_IMG:
            hits, img_colors, msh_colors = shoot_rays_for_image(
                CAMERA_LOC, HEADING, INPUT_IMG, image_id, bbox, street_mesh, visibility_score
            )

            # Aggregate colors
            all_image_colors.extend(img_colors)
            all_mesh_colors.extend(msh_colors)

            # Group hits by the mesh face they hit
            for hit in hits:
                face_id = hit["face_id"]
                if face_id not in faces_data:
                    faces_data[face_id] = []
                faces_data[face_id].append(hit)

    print("Raycasting complete! Packaging data for evaluation...")

    return {
        "image_colors": all_image_colors,
        "mesh_colors": all_mesh_colors,
        "faces_data": faces_data,
        "total_faces": len(street_mesh.faces),
    }
