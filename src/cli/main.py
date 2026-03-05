import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from src.evals import generate_kpi_report
from src.ingestion import run_ingestion
from src.mesh import build_scene
from src.texture import run_raycaster


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="POSM: Python OpenStreetMap to 3D Mesh Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required Arguments
    parser.add_argument("lat", type=float, help="Latitude of the center point")
    parser.add_argument("lon", type=float, help="Longitude of the center point")

    # Optional Arguments
    parser.add_argument(
        "--buffer", type=float, default=0.001, help="Bounding box buffer size in degrees"
    )
    parser.add_argument(
        "--output-dir", type=str, default="output", help="Directory to save meshes and data"
    )

    args = parser.parse_args()

    print(f"=== Starting POSM Pipeline for ({args.lat}, {args.lon}) ===")

    # Step 1: Ingestion
    print("\n--- Phase 1: Ingestion ---")
    data = run_ingestion(args.lat, args.lon, args.buffer, f"{args.output_dir}/mapillary")

    if not data.get("buildings_joined"):
        print("Pipeline aborted: No buildings found in this area.")
        return

    # Step 2: Mesh Generation
    print("\n--- Phase 2: Mesh Generation ---")
    combined_mesh_path = f"{args.output_dir}/meshes/combined.glb"
    build_scene(data, output_dir=f"{args.output_dir}/meshes")

    # Step 3: Texture Mapping (Raycasting)
    print("\n--- Phase 3: Texture Raycasting ---")
    raycast_results = run_raycaster(data, combined_mesh_path)

    # Step 4: KPI Evaluation
    print("\n--- Phase 4: KPI Evaluation ---")
    kpis = generate_kpi_report(**raycast_results)

    # Save KPIs to disk
    kpi_path = Path(args.output_dir) / "kpis.json"
    with open(kpi_path, "w") as f:
        json.dump(kpis, f, indent=4)

    print("\n=== POSM Pipeline Complete! ===")
    print(f"Overall Model Quality Score: {kpis['overall_model_quality_score']}/100")
    print(f"Results saved to: {args.output_dir}/")


if __name__ == "__main__":
    main()
