import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
MAPILLARY_URL = "https://graph.mapillary.com/images"


def fetch_osm_buildings(
    lat: float, lon: float, buffer: float = 0.001, retries: int = 3
) -> Dict[str, Any]:
    """Queries Overpass API for buildings with retry logic."""
    s, w, n, e = (lat - buffer, lon - buffer, lat + buffer, lon + buffer)
    query = f"""
    [out:json][timeout:25];
    (
      way["building"]({s},{w},{n},{e});
      relation["building"]({s},{w},{n},{e});
    );
    out body;
    >;
    out skel qt;
    """
    for attempt in range(retries):
        try:
            print(f"Fetching OSM buildings (Attempt {attempt + 1})...")
            response = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
            if response.status_code == 200:
                return response.json()
            time.sleep((attempt + 1) * 2)
        except Exception as e:
            print(f"OSM attempt failed: {e}")
    return {}


def fetch_mapillary_metadata(
    lat: float, lon: float, buffer: float = 0.001, token: str = None
) -> List[Dict[str, Any]]:
    """Fetches Mapillary metadata including camera parameters and poses."""
    token = token or os.getenv("MAPILLARY_ACCESS_TOKEN")
    if not token:
        raise ValueError("MAPILLARY_ACCESS_TOKEN missing from environment variables.")

    headers = {"Authorization": f"OAuth {token}"}
    s, w, n, e = (lat - buffer, lon - buffer, lat + buffer, lon + buffer)
    bbox = f"{w},{s},{e},{n}"
    fields = (
        "id,thumb_original_url,computed_geometry,computed_compass_angle,"
        "camera_parameters,captured_at,sequence"
    )
    url = f"{MAPILLARY_URL}?bbox={bbox}&fields={fields}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            print(f"[ERROR] Mapillary API {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[CRITICAL] Mapillary fetch failed: {e}")
    return []


def download_thumbnail(url: str, image_id: str, output_dir: Path) -> Optional[str]:
    """Downloads the thumbnail and returns the local path string."""
    if not url:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"{image_id}.jpg"

    if filename.exists():
        return str(filename)

    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            filename.write_bytes(r.content)
            time.sleep(0.1)
            return str(filename)
        else:
            print(f"Error {r.status_code} downloading {image_id}")
    except Exception as e:
        print(f"Failed to download {image_id}: {e}")
    return None
