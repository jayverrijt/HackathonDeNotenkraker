---
name: offline-accessibility-vision
description: Design, develop, train, optimize and deploy an offline, real-time AI visual assistance system for blind and visually impaired people using smartphone cameras, computer vision, object detection, semantic segmentation, tracking, depth estimation, speech and haptic feedback.
---

# Offline Accessibility Vision Assistant

## 1. Project mission

Build a smartphone-based visual assistance system that helps blind and visually impaired people understand their immediate surroundings.

The system uses a chest-mounted smartphone camera to continuously observe the outdoor environment, recognize relevant objects and surroundings, estimate spatial relationships, and communicate useful information through spoken notifications and haptic feedback.

The system must prioritize:

Nearby obstacles.
People and groups of people.
Roads and sidewalks.
Trash bins and street furniture.
Objects obstructing pedestrian paths.
Moving objects and changing surroundings.
Potentially hazardous situations.

The primary objective is to provide useful environmental awareness without requiring an internet connection.

This is an assistive technology project, not a replacement for a white cane, guide dog or established mobility techniques.

## 2. Core product vision

A person wears a smartphone on their chest.

The camera continuously captures the environment.

AI models analyze the camera feed locally on the phone.

The application determines:

What objects are visible.
Where objects appear in the camera image.
Whether objects persist or move between frames.
Whether objects appear in potentially relevant walking areas.
Which observations deserve an audio or vibration notification.

Example notifications:

"There are several people ahead."
"A trash bin is visible on your right."
"There is a bench in front of you."
"A bicycle is approaching from the left."
"The sidewalk appears to continue ahead."
"There is an object near the lower centre of the camera view."

Notifications must be concise, understandable and appropriately prioritized.

Never present uncertain computer vision predictions as established facts.

## 3. Hardware requirements

### Primary hardware

Smartphones released within approximately the last five years.

Supported platforms:

Android.
iOS.

### Initial hardware assumptions

Chest-mounted smartphone.
Rear-facing camera.
Continuous camera capture.
No external depth sensor initially.
On-device AI inference.
Offline operation.
Built-in speaker or headphones.
Smartphone vibration motor.

### Potential future hardware

External stereo cameras.
Time-of-flight sensors.
LiDAR-capable devices.
Wearable cameras.
Bone-conduction headphones.
Dedicated haptic devices.

Do not make an external sensor mandatory for the initial prototype.

## 4. AI architecture

Use a modular multi-model architecture.

### A. Semantic segmentation

Primary model:

YOLO26s-sem

Responsibilities:

Road recognition.
Sidewalk recognition.
Pedestrian scene understanding.
Vegetation.
Buildings.
Vehicles.
General environmental segmentation.

Important: Semantic segmentation assigns classes to pixels. It does not independently identify individual object instances.

Use appropriate pretrained datasets and evaluate their class coverage.

The Cityscapes model does not contain every object required by this project.

### B. Object detection

Initial baseline:

YOLO26n

Responsibilities:

Individual people.
Bicycles.
Cars.
Motorcycles.
Benches where supported.
Other detectable obstacles.

Develop a custom-trained detector for missing classes.

Priority custom classes:

Trash bins.
Bollards.
Benches.
Electric scooters.
Parked bicycles.
Construction barriers.
Street signs.
Boxes and discarded objects.
Low obstacles.
Objects protruding into pedestrian paths.

Choose models based on measured mobile performance, not parameter count alone.

### C. Object tracking

Use an object tracking system such as:

BoT-SORT.
ByteTrack.
Other suitable lightweight trackers.

Tracking should establish object persistence and estimate image-space movement.

The system must account for chest-camera movement.

Do not interpret raw bounding-box movement as reliable object movement without compensating for camera motion.

### D. Depth estimation

Initially investigate monocular depth estimation.

Responsibilities:

Relative depth estimation.
Approximate object proximity.
Scene geometry.
Identifying potentially close objects.

Important limitations: Monocular depth estimates are not automatically reliable metric distance measurements.

Never announce precise distances without appropriate calibration and validation.

Investigate additional depth sensors in later development stages.

## 5. Real-time processing architecture

Target:

Continuous camera capture.
Approximately 2–10 AI inference FPS.
Smooth camera preview.
Low latency.
Low battery consumption.
Low thermal load.

Recommended initial processing schedule:

Component Target frequency
Camera 30 FPS
Semantic segmentation 2 FPS
Object detection 5 FPS
Tracking Every detection frame
Depth estimation 2–5 FPS
Alert generation Event-driven

These are initial targets, not guaranteed performance specifications.

Use:

Latest-frame-only processing.
Frame dropping instead of accumulating queues.
Independent camera and inference threads.
Asynchronous rendering.
Reusable memory buffers.
Model quantization where validated.
Adaptive inference frequency.

Never allow slow inference to block the camera preview.

## 6. Spatial awareness

Divide the camera image into approximate regions:

Left.
Centre.
Right.
Upper.
Lower.

Use these regions to describe where objects appear.

For example:

"Trash bin visible on the right."

"Person visible in the lower centre."

"Several people in the central camera view."

Do not automatically equate image position with actual walking direction.

The chest-mounted camera's angle, orientation and movement must be calibrated.

Future improvements:

Ground-plane estimation.
Camera orientation estimation.
Depth-aware spatial reasoning.
Walking-path estimation.
Obstacle persistence analysis.

## 7. Obstacle prioritization

Build a dedicated alert engine.

Each observation should contain:

Object class.
Confidence.
Bounding box.
Tracking ID.
Image-space position.
Detection timestamp.
Persistence.
Estimated proximity, when available.
Uncertainty.

The alert engine should consider:

Whether an object is relevant to the walking environment.
Whether it is potentially close.
Whether it is moving.
Whether it is already being announced.
Whether a higher-priority alert is active.

Do not infer collision risk from a bounding box alone.

Avoid repeatedly announcing stationary objects.

Prioritize potentially important observations over general scene descriptions.

Never suppress a potentially important warning solely because it resembles an earlier alert.

## 8. Audio and haptic feedback

Audio is a primary interaction method.

Use concise spoken messages.

Examples:

"Person ahead."
"Several people ahead."
"Trash bin on the right."
"Object in the lower centre."
"Bicycle approaching from the left."

Avoid:

Long descriptions.
Constant narration.
Repeated announcements.
Unnecessary technical terminology.
Unsupported distance claims.

Implement:

Text-to-speech.
Speech priority.
Alert cooldowns.
Duplicate suppression.
Interruptible speech.
Configurable speech speed.
Volume controls.
Quiet mode.

Haptic feedback should supplement speech.

Do not assign directional vibration patterns until the directional interpretation has been tested and validated.

## 9. Mobile deployment

### Android

Preferred technologies:

Kotlin.
CameraX.
LiteRT or ONNX Runtime.
Android hardware acceleration.
Android TextToSpeech.
Android vibration APIs.

Investigate:

NNAPI.
XNNPACK.
Qualcomm QNN where supported.

### iOS

Preferred technologies:

Swift.
AVFoundation.
CoreML.
Apple Neural Engine where supported.
AVSpeechSynthesizer.
Core Haptics.

### Shared model development

Keep model training and evaluation in Python.

Export separate deployment artifacts as appropriate.

Maintain consistent:

Input preprocessing.
Color channel ordering.
Normalization.
Letterboxing.
Output interpretation.
Segmentation class mappings.
Confidence thresholds.

Validate exported models against the original PyTorch implementation.

Do not assume two runtimes produce identical results without testing.

## 10. Python development prototype

The first development environment should be Python.

Recommended dependencies:

ultralytics
opencv-python
numpy
pyttsx3
PyTorch

Initial project structure:

```text
accessibility-assistant/
│
├── models/
│ ├── yolo26s-sem.pt
│ └── yolo26n.pt
│
├── data/
│ ├── images/
│ └── annotations/
│
├── src/
│ ├── camera.py
│ ├── segmentation.py
│ ├── detection.py
│ ├── tracking.py
│ ├── depth.py
│ ├── spatial_analysis.py
│ ├── alert_engine.py
│ ├── speech.py
│ ├── haptics.py
│ └── main.py
│
├── training/
│ ├── dataset.yaml
│ └── train.py
│
├── deployment/
│ ├── android/
│ └── ios/
│
├── tests/
│
├── config.py
├── requirements.txt
└── README.md
```

Keep each subsystem independent.

Avoid placing all inference, camera capture, tracking and speech logic in one large source file as the project matures.

## 11. Dataset development

Build an outdoor obstacle dataset.

Capture diverse environments:

Urban streets.
Sidewalks.
Parks.
Residential neighborhoods.
Shopping areas.
Pedestrian crossings.
Public transport areas.
Different lighting and weather conditions.

Include:

Daylight.
Overcast conditions.
Rain.
Shadows.
Low-light conditions.
Different camera heights.
Different chest-mount angles.
Motion blur.
Crowded environments.

Annotate bounding boxes for individual objects and semantic masks for environmental classes.

Include difficult examples:

Partially hidden trash bins.
Objects near image boundaries.
Low obstacles.
Dark objects.
Objects against visually similar backgrounds.
People partially occluded by other people.

Respect privacy when collecting and storing street footage.

Avoid collecting identifiable footage unnecessarily.

## 12. Evaluation and testing

Measure more than FPS.

Important metrics:

### Model quality

Precision.
Recall.
mAP.
Segmentation mIoU.
Per-class performance.
Small-object recall.

### Real-time performance

Inference latency.
Camera-to-alert latency.
Sustained FPS.
Memory usage.
Battery consumption.
Device temperature.

### Accessibility quality

Missed important obstacles.
Incorrect warnings.
Duplicate warnings.
Speech interruption.
Alert comprehension.
User workload.
User confidence.

Test in controlled environments before outdoor trials.

Include blind and visually impaired participants and mobility specialists in usability evaluation.

## 13. Safety principles

This project has real-world safety implications.

Always:

Clearly communicate uncertainty.
Avoid unsupported distance measurements.
Avoid declaring a path safe based only on camera imagery.
Avoid issuing autonomous navigation instructions without validated perception and localization.
Preserve access to conventional mobility aids.
Minimize alert fatigue.
Prioritize reliability over speed.
Test adverse conditions.
Maintain offline functionality.

Never describe the prototype as a replacement for a white cane or guide dog.

Treat false negatives and false positives as important engineering problems.

## 14. Development roadmap

### Phase 1: Python prototype

- Live camera feed.
- YOLO26s-sem segmentation.
- YOLO26n detection.
- Object tracking.
- Spatial image analysis.
- Spoken notifications.

### Phase 2: Custom obstacle recognition

- Collect outdoor images.
- Annotate trash bins, bollards, scooters and other obstacles.
- Train a lightweight detector.
- Evaluate on unseen environments.

### Phase 3: Improved spatial understanding

- Monocular depth estimation.
- Camera orientation calibration.
- Ground-plane estimation.
- Camera-motion compensation.
- Temporal object analysis.

### Phase 4: Intelligent alert engine

- Alert prioritization.
- Duplicate suppression.
- Configurable warnings.
- Speech and haptic integration.

### Phase 5: Mobile applications

- Android implementation.
- iOS implementation.
- Hardware acceleration.
- Thermal optimization.
- Offline operation.

### Phase 6: Accessibility validation

- Controlled obstacle courses.
- Supervised outdoor testing.
- Feedback from visually impaired users.
- Mobility specialist evaluation.
- Iterative improvement.

## 15. Instructions for AI coding assistants

When working on this project:

Understand the complete architecture before proposing changes.
Prefer modular, testable code.
Keep all inference on-device.
Never introduce a cloud dependency without explicit approval.
Preserve compatibility between Android and iOS where practical.
Verify model input and output formats against the actual Ultralytics version.
Never invent model capabilities or dataset classes.
Measure performance on real hardware.
Distinguish image-space position from physical distance.
Prioritize safety, reliability and accessibility.
Explain model limitations clearly.
Provide complete, runnable implementations when asked to implement a feature.
Include installation commands and configuration.
Add tests for important processing and alert logic.
Do not claim a feature works until it has been tested.

## 16. Overall success criteria

The project succeeds when a blind or visually impaired person can wear a smartphone, walk through an outdoor environment, and receive timely, understandable, useful information about relevant surroundings.

The system should be:

Offline.
Responsive.
Accessible.
Energy-efficient.
Privacy-conscious.
Reliable.
Compatible with Android and iOS.

The ultimate goal is to improve environmental awareness and support greater independence through practical on-device computer vision.
