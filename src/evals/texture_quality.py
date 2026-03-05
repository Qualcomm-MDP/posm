from typing import Any, Dict, List

def evaluate_face_confidence(face_hits: List[Dict[str, Any]]) -> str:
    """
    Evaluates a single mesh polygon (face) and categorizes its texture confidence.
    Categories match the Phase I criteria: High confidence, Low confidence, Occluded, Missing.
    """
    # 4. Missing: No photograph of area
    if not face_hits:
        return "Missing"

    # 3. Occluded: Unseen area blocked by objects (simulated by hit distance vs expected)
    if any(hit.get("is_occluded", False) for hit in face_hits):
        return "Occluded"

    unique_viewpoints = set(hit.get("image_id") for hit in face_hits)
    
    # Calculate average visibility/goodness score for the hits on this face
    avg_score = sum(hit.get("visibility_score", 0) for hit in face_hits) / len(face_hits)

    # 1. High confidence: Good, detailed imagery available from multiple viewpoints
    if len(unique_viewpoints) >= 2 and avg_score >= 1.5:
        return "High confidence"

    # 2. Low confidence: Out-of-focus, grainy, or inconsistent imagery
    return "Low confidence"

def aggregate_texture_quality(faces_data: Dict[int, List[Dict[str, Any]]], total_faces: int) -> Dict[str, Any]:
    """
    Aggregates the per-area evaluations into an overall texture quality distribution.
    """
    distribution = {
        "High confidence": 0,
        "Low confidence": 0,
        "Occluded": 0,
        "Missing": 0
    }
    
    for face_id in range(total_faces):
        hits = faces_data.get(face_id, [])
        confidence = evaluate_face_confidence(hits)
        distribution[confidence] += 1
        
    # Calculate percentages
    percentages = {k: round((v / total_faces) * 100, 2) for k, v in distribution.items()}
    
    return {
        "raw_counts": distribution,
        "percentages": percentages
    }