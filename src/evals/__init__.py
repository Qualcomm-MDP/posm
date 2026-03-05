from .texture_quality import evaluate_face_confidence, aggregate_texture_quality
from .model_quality import calculate_texture_correlation, calculate_overall_model_quality

def generate_kpi_report(
    image_colors: list, 
    mesh_colors: list, 
    faces_data: dict, 
    total_faces: int
) -> dict:
    """Generates the full suite of Model Quality Indicators required by Phase I."""
    
    correlation = calculate_texture_correlation(image_colors, mesh_colors)
    texture_quality = aggregate_texture_quality(faces_data, total_faces)
    
    overall_score = calculate_overall_model_quality(
        correlation_score=correlation,
        texture_percentages=texture_quality["percentages"]
    )
    
    return {
        "overall_model_quality_score": overall_score,
        "overall_texture_quality": texture_quality,
        "overall_3d_model_to_texture_correlation": correlation
    }

__all__ = [
    "evaluate_face_confidence",
    "aggregate_texture_quality",
    "calculate_texture_correlation",
    "calculate_overall_model_quality",
    "generate_kpi_report"
]