# Photorealistic Open Street Maps (POSM)
[cite_start]An end-to-end software pipeline for generating 3D maps with photorealistic textures[cite: 18]. 

## 🚀 What is POSM?
[cite_start]POSM is an open-ended research project designed to automatically produce an output 3D map with photorealistic textures from various data sources[cite: 8, 18]. [cite_start]The primary goal is to fuse 3D building models with photographic street view data to texture static macro components, such as buildings and terrain[cite: 18, 19]. 

## 📋 Key Features (Phase I)
* [cite_start]**End-to-End Pipeline**: Automatically produces an output 3D map with photorealistic textures using photographic data and 3D world models[cite: 18].
* [cite_start]**Generalizability**: Functions within a selected geographic area (such as the University of Michigan North Campus) that has decent photographic coverage and relatively accurate 3D models[cite: 23, 24].
* [cite_start]**Automation**: Requires relatively little hand-tuning to properly function within the chosen area[cite: 25].
* [cite_start]**Texture Mapping**: Textures static macro components (buildings and terrain) or applies a textured flat ground plane if terrain is unavailable[cite: 19].

## 📊 Model Quality Indicators
[cite_start]Because it is difficult to quantitatively evaluate the final 3D model against the real-world data it portrays, the pipeline produces a set of numerical scores alongside the generated model to indicate quality[cite: 11, 29].

* [cite_start]**Overall Model Quality**: A score from 0 (no data) to 100 (perfect models, perfect mapping) that combines texture quality and 3D model correlation[cite: 31, 32, 33].
* [cite_start]**Overall Texture Quality**: A per-area evaluation of generated texture on the 3D model, split into four confidence levels[cite: 34, 35]:
    * [cite_start]**High confidence**: Good, detailed imagery available from multiple viewpoints[cite: 36, 37].
    * [cite_start]**Low confidence**: Out-of-focus, grainy, or inconsistent imagery, or situations where the camera intrinsics/pose cannot be determined[cite: 38, 39, 40].
    * [cite_start]**Occluded**: Unseen areas blocked by objects, but somewhat able to approximate[cite: 41, 43, 44].
    * [cite_start]**Missing**: No photographs available of the area, making it unable to approximate[cite: 42, 45, 46].



* [cite_start]**Overall 3D Model to Texture Correlation**: A numerical score indicating the alignment between input 3D models and generated textures (defined at a granularity such as per-polygon or per-building)[cite: 54, 55].
* [cite_start]**Component-level KPIs**: Includes metrics like "Per-photo goodness" to evaluate the usability of individual photos or areas of photos for mapping[cite: 56, 57].

## 🛠️ Development & Testing
*(Repository currently in setup phase)*

* [cite_start]**Testing**: We strongly consider the use of CI/CD to automate a comprehensive set of test cases during development[cite: 60, 61].
* [cite_start]**Documentation**: We maintain living documents for high-level and detailed system architectures, with inputs and outputs clearly defined[cite: 65, 66, 68].
* [cite_start]**Git Best Practices**: The repository will be properly maintained with this README and necessary environment files[cite: 69].
