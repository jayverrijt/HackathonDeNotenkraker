"""Preview rendering for the desktop demo."""

from __future__ import annotations

import cv2
import numpy as np


def create_overlay(frame, mask, profile):
    if mask is None:
        return frame

    mask = cv2.resize(
        mask,
        (frame.shape[1], frame.shape[0]),
        interpolation=cv2.INTER_NEAREST,
    )
    colored = cv2.applyColorMap(
        (mask.astype(np.uint8) * 17),
        cv2.COLORMAP_TURBO,
    )
    return cv2.addWeighted(frame, 0.65, colored, 0.35, 0)


def draw_detections(frame, detections, profile):
    height, width = frame.shape[:2]

    cv2.rectangle(
        frame,
        (
            int(width * profile.centre_left),
            int(height * profile.lower_region_top),
        ),
        (int(width * profile.centre_right), height),
        (0, 255, 255),
        2,
    )

    for detection in detections:
        if not detection.get("obstacle", True) and "_close_score" not in detection:
            continue

        x1, y1, x2, y2 = map(int, detection["box"])
        color = (0, 0, 255) if detection.get("lower") else (0, 255, 0)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"{detection['name']} {detection['confidence']:.2f}"
        if detection.get("track_id") is not None:
            label += f" ID:{detection['track_id']}"

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

    return frame


def render(frame, detections, mask, profile, scale: float = 1.0):
    """Copy a frame, draw the overlay and detections, then optionally downscale."""
    output = frame.copy()

    if profile.show_segmentation:
        output = create_overlay(output, mask, profile)

    draw_detections(output, detections, profile)

    if scale and scale != 1.0:
        output = cv2.resize(
            output,
            (int(output.shape[1] * scale), int(output.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )

    return output
