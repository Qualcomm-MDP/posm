from pathlib import Path
from typing import Any, Dict

from posm.src.ingestion.spatial_joiner import spatial_join_data

from .api_client import fetch_mapillary_metadata, fetch_osm_buildings


def run_ingestion(
    lat: float, lon: float, buffer: float = 0.001, output_dir: str = "data/mapillary"
) -> Dict[str, Any]:
    """
    Runs the end-to-end ingestion pipeline for a given coordinate.

    Args:
        lat: Latitude of the center point.
        lon: Longitude of the center point.
        buffer: Bounding box buffer in degrees.
        output_dir: Directory to save downloaded thumbnails.

    Returns:
        A dictionary containing joined buildings and mapped images ready for 3D processing.
    """
    print(f"--- Starting Ingestion Pipeline for ({lat}, {lon}) ---")

    # 1. Fetch OSM Data
    print("Fetching OSM building data...")
    osm_raw_json = fetch_osm_buildings(lat, lon, buffer)
    if not osm_raw_json.get("elements"):
        print("[WARNING] No OSM buildings found in this area.")

    # 2. Fetch Mapillary Metadata
    print("Fetching Mapillary image metadata...")
    mapillary_raw_list = fetch_mapillary_metadata(lat, lon, buffer)
    if not mapillary_raw_list:
        print("[WARNING] No Mapillary images found in this area.")

    if not osm_raw_json.get("elements") and not mapillary_raw_list:
        print("--- Ingestion Aborted: No data to process ---")
        return {"buildings_joined": [], "mapillary_kept": [], "discarded_urls": []}

    # 3. Perform Spatial Join & Scoring
    print("Processing spatial join, scoring, and downloading images...")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    results = spatial_join_data(
        osm_raw_json=osm_raw_json, mapillary_raw_list=mapillary_raw_list, output_dir=out_path
    )

    print("--- Ingestion Complete ---")
    print(f"Buildings processed: {len(results.get('buildings_joined', []))}")
    print(f"Images assigned: {len(results.get('mapillary_kept', []))}")

    return results


__all__ = ["run_ingestion"]
