import numpy as np
from typing import List, Dict, Any

def calculate_texture_correlation(image_colors: List[List[float]], mesh_colors: List[List[float]]) -> float:
    """
    Calculates the 'Overall 3D model to texture correlation' using cosine similarity.
    Measures how well the input 3D models and generated texture are aligned.
    """
    if not image_colors or not mesh_colors or len(image_colors) != len(mesh_colors):
        return 0.0

    cos_sims = []
    for img_c, mesh_c in zip(image_colors, mesh_colors):
        # Prevent division by zero and normalize vectors
        img_vec = np.array(img_c[:3], dtype=float)
        mesh_vec = np.array(mesh_c[:3], dtype=float)
        
        norm_img = np.linalg.norm(img_vec)
        norm_mesh = np.linalg.norm(mesh_vec)

        if norm_img == 0 or norm_mesh == 0:
            continue

        sim = np.dot(img_vec / norm_img, mesh_vec / norm_mesh)
        # Clip to handle minor floating point inaccuracies
        sim = np.clip(sim, -1.0, 1.0)
        cos_sims.append(sim)

    # Convert average from [-1, 1] scale to [0, 1] scale
    avg_sim = float(np.mean(cos_sims)) if cos_sims else 0.0
    correlation_normalized = (avg_sim + 1) / 2
    
    return round(correlation_normalized, 4)

def calculate_overall_model_quality(correlation_score: float, texture_percentages: Dict[str, float]) -> float:
    """
    Calculates 'Overall model quality' on a scale from 0 to 100.
    Combines texture quality scores with the 3D correlation score.
    """
    # Weighting the confidence percentages
    high_conf = texture_percentages.get("High confidence", 0)
    low_conf = texture_percentages.get("Low confidence", 0)
    
    # Give partial credit for low confidence, full credit for high confidence
    coverage_score = (high_conf * 1.0) + (low_conf * 0.4)
    
    # Final formula: Coverage heavily dictates the baseline, correlation scales it.
    # If coverage is perfect (100) and correlation is perfect (1.0), score is 100.
    final_score = coverage_score * correlation_score
    
    return round(final_score, 2)