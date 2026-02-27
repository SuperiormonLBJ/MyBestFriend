---
type: project
title: Vehicle Geometry & Axle Detection from Traffic Surveillance
importance: high
year: 2022
tags: [computer-vision, intelligent-transportation, multi-object-tracking, yolo, deep-learning, research, multi-modal]
---

Tags:
#computer-vision #intelligent-transportation #multi-object-tracking #yolo #deep-learning #research #multi-modal

## 1. Overview

**Domain:** Intelligent Transportation / Computer Vision

**Role:** Research Engineer / CV Engineer / NUS Master

**Duration:** Academic Research Project for NUS Master

**Summary:**

Developed computer vision pipelines to extract **vehicle geometry parameters** (width, length, wheelbase, location) and **axle configurations** from stationary traffic surveillance cameras for intelligent transportation and safety monitoring.

## 2. Problem (Pain)

Traditional traffic monitoring systems mainly capture:

- Vehicle count
- Speed
- Flow rate

However, **vehicle structural parameters** are missing:

- Vehicle width & length
- Wheelbase
- Axle number and distance

These parameters are critical for:

- Road safety monitoring
- Infrastructure protection
- Intelligent transportation analytics

Challenges:

- No depth sensors available (monocular camera only)
- Perspective distortion
- Occlusion and motion blur

## 3. Solution (Architecture)

### Pipeline A — Vehicle Geometry Extraction

**Input**

- Stationary surveillance camera video

**Processing**

- Camera calibration via vanishing points
- Vehicle detection using YOLOv4
- Morphology filtering for contour refinement
- MedianFlow tracking for wheel feature points

**Output**

- Vehicle width
- Wheelbase
- Vehicle length estimation

### Pipeline B — Axle Configuration Detection

**Input**

- Highway traffic video frames

**Processing**

- Vehicle tracking using DeepSORT
- Wheel detection using YOLOv5 (custom-trained)
- Ground-plane projection via vanishing point geometry

**Output**

- Axle count
- Axle distance estimation

## 4. Tech Stack

**Computer Vision**

- YOLOv4 (vehicle detection)
- YOLOv5 (wheel detection)
- OpenCV

**Tracking**

- MedianFlow
- DeepSORT

**Data Processing**

- Python
- Morphological operations

**Dataset**

- Custom labeled vehicle dataset (~500 images)

## 5. Multi-Modal / Geometry Modeling (High Value Section)

Key idea:

- Use **camera geometry constraints** instead of 3D sensors

Techniques:

- Vanishing point calibration
- Linear regression between:
    - vehicle length
    - wheelbase

External data:

- Web crawler vehicle dimension dataset

## 6. Challenges

### Perspective distortion

Monocular camera makes real-world dimension estimation difficult.

**Solution**

- Ground-plane projection using vanishing points.

### Wheel detection accuracy

Small object detection (wheel) is difficult.

**Solution**

- Custom dataset labeling (~500 images)
- YOLOv5 fine-tuning

### Tracking stability

Occlusion and motion blur reduce tracking quality.

**Solution**

- Multi-frame tracking using MedianFlow and DeepSORT.

## 7. Engineering Decisions (Strong Interview Signal)

- Use geometry-based estimation instead of 3D bounding boxes
- Combine detection + tracking for temporal consistency
- Introduce external vehicle dimension priors

## 8. Performance & Results

Vehicle length estimation:

- Mean Absolute Error reduced by **77%**
- From **1.14m → 0.26m**

Axle detection:

- 90% accuracy across axle types
- 93% accuracy on axle distance estimation

## 9. System Design Insight (Interview Reusable)

This project demonstrates:

- Multi-stage CV pipelines
- Detection + Tracking architecture
- Geometry-based measurement
- Weakly supervised modeling using external priors

## 10. Interview Snippets

**Q: How did you estimate real-world vehicle size from a single camera?**

A: Using vanishing-point calibration and ground-plane projection.

**Q: Why combine detection and tracking?**

A: Tracking stabilizes predictions across frames and reduces noise.

**Q: How did you improve length estimation accuracy?**

A: Introduced wheelbase priors from external vehicle dimension datasets.

## 11. Future Improvements

- Replace YOLOv4/v5 with YOLOv11 or RT-DETR
- Introduce depth estimation models
- Deploy real-time inference pipeline
- Add MLOps for dataset iteration