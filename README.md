# Photorealistic Open Street Maps (POSM)
An end-to-end software pipeline for generating 3D maps with photorealistic textures. 

## 🚀 Why POSM?
POSM is an open-ended research project designed to automatically produce an output 3D map with photorealistic textures from various data sources. The primary goal is to fuse 3D building models with photographic street view data to texture static macro components, such as buildings and terrain. 

## 📋 Key Features (Phase I)
* **End-to-End Pipeline**: Automatically produces an output 3D map with photorealistic textures using photographic data and 3D world models.
* **Generalizability**: Functions within a selected geographic area (such as the University of Michigan North Campus) that has decent photographic coverage and relatively accurate 3D models.
* **Automation**: Requires relatively little hand-tuning to properly function within the chosen area.
* **Texture Mapping**: Textures static macro components (buildings and terrain) or applies a textured flat ground plane if terrain is unavailable.

## 📊 Model Quality Indicators
Because it is difficult to quantitatively evaluate the final 3D model against the real-world data it portrays, the pipeline produces a set of numerical scores alongside the generated model to indicate quality.

* **Overall Model Quality**: A score from 0 (no data) to 100 (perfect models, perfect mapping) that combines texture quality and 3D model correlation.
* **Overall Texture Quality**: A per-area evaluation of generated texture on the 3D model, split into four confidence levels:
    * **High confidence**: Good, detailed imagery available from multiple viewpoints.
    * **Low confidence**: Out-of-focus, grainy, or inconsistent imagery, or situations where the camera intrinsics/pose cannot be determined.
    * **Occluded**: Unseen areas blocked by objects, but somewhat able to approximate.
    * **Missing**: No photographs available of the area, making it unable to approximate.

* **Overall 3D Model to Texture Correlation**: A numerical score indicating the alignment between input 3D models and generated textures (defined at a granularity such as per-polygon or per-building).
* **Component-level KPIs**: Includes metrics like "Per-photo goodness" to evaluate the usability of individual photos or areas of photos for mapping.

## 🛠️ Development & Testing
*(Repository currently in setup phase)*

* **Testing**: We strongly consider the use of CI/CD to automate a comprehensive set of test cases during development.
* **Documentation**: We maintain living documents for high-level and detailed system architectures, with inputs and outputs clearly defined.
* **Git Best Practices**: The repository will be properly maintained with this README and necessary environment files.
