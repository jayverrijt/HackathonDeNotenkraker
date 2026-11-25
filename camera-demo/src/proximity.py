"""Image-space proximity and scene heuristics.

There is no depth sensor and the semantic model has no ``curb`` or ``tree``
class, so these are deliberately conservative, uncertain warnings:

* close object: large box low in the frame, in the walking band, seen in
  several recent detection frames;
* curb: a road/sidewalk boundary close to the bottom of the frame, or a
  road/sidewalk transition in the central path;
* scene: large vegetation/building regions in the semantic mask, described at
  low priority so they do not compete with safety warnings.

Never convert these scores into metres.
"""

from __future__ import annotations

from collections import deque

import cv2
import numpy as np

from .messages import curb_message, scene_message


def detection_key(det) -> str:
    if det.get("track_id") is not None:
        return f"{det['name']}_{det['track_id']}"
    return f"{det['name']}_{det.get('position', 'unknown')}"


def close_details(det, width: int, height: int, profile):
    """Return ``(score, bottom, area)`` for a close object, or ``None``."""
    x1, y1, x2, y2 = map(float, det["box"])
    width = max(1.0, float(width))
    height = max(1.0, float(height))

    cx = (x1 + x2) / 2.0 / width
    bottom = y2 / height
    area = max(0.0, x2 - x1) * max(0.0, y2 - y1) / (width * height)

    if not (profile.close_centre_left <= cx <= profile.close_centre_right):
        return None
    if bottom < profile.close_bottom_ratio:
        return None
    if area < profile.close_area_ratio:
        return None

    return bottom + min(area, 0.25), bottom, area


def close_score(det, width: int, height: int, profile):
    """Return an image-space closeness score, or ``None`` if not close."""
    details = close_details(det, width, height, profile)
    return None if details is None else details[0]


class CloseObjectTracker:
    """Require a close object in 2 of the last 3 detection frames.

    Very close boxes can warn on their first frame.  The short history avoids
    losing a warning when tracker IDs flicker or a single frame is missed.
    """

    def __init__(self):
        self.windows = {}

    def update(self, detections, width: int, height: int, profile, now=None):
        # Age existing windows by one frame.
        for key in self.windows:
            self.windows[key].append(False)

        close = []
        for det in detections:
            details = close_details(det, width, height, profile)
            if details is None:
                continue

            score, bottom, area = details
            key = detection_key(det)
            window = self.windows.get(key)
            if window is None:
                window = deque(maxlen=3)
                window.append(True)
                self.windows[key] = window
            else:
                window[-1] = True

            immediate = (
                bottom >= profile.close_immediate_bottom
                and area >= profile.close_immediate_area
            )
            required = 1 if immediate else profile.close_persist_frames

            if sum(window) >= required:
                det["_close_score"] = score
                close.append(det)

        for key in list(self.windows):
            if not any(self.windows[key]):
                del self.windows[key]

        close.sort(
            key=lambda d: (d["name"] == "person", d.get("_close_score", 0.0)),
            reverse=True,
        )
        return close


def class_ids(class_names):
    if isinstance(class_names, dict):
        items = ((int(k), str(v).lower()) for k, v in class_names.items())
    else:
        items = ((i, str(v).lower()) for i, v in enumerate(class_names))
    return {name: idx for idx, name in items}


def _resize_mask(mask, max_w=320):
    h, w = mask.shape[:2]
    if w <= max_w:
        return mask
    scale = max_w / float(w)
    return cv2.resize(
        mask,
        (max_w, max(1, int(round(h * scale)))),
        interpolation=cv2.INTER_NEAREST,
    )


class CurbDetector:
    """Best-effort curb / road-edge detector using the semantic mask."""

    def __init__(self, profile):
        self.profile = profile

    def analyze(self, mask, class_names, now=None):
        if mask is None or class_names is None or getattr(mask, "ndim", 0) != 2:
            return None

        names = class_ids(class_names)
        road_id = names.get("road")
        sidewalk_id = names.get("sidewalk")
        if road_id is None or sidewalk_id is None:
            return None

        mask = _resize_mask(mask, max_w=320)
        h, w = mask.shape[:2]

        curb_id = names.get("curb")
        if curb_id is not None:
            frac = float((mask == curb_id).mean())
            if frac >= 0.01:
                return {
                    "message": curb_message("ahead"),
                    "key": "curb_ahead",
                    "confidence": frac,
                    "zone": "ahead",
                }

        road = mask == road_id
        sidewalk = mask == sidewalk_id

        # --- Curb ahead: sidewalk underfoot, road above it in the centre. ---
        x0, x1 = int(0.30 * w), int(0.70 * w)
        bottom_y = int(0.85 * h)
        if bottom_y < h:
            bottom_side = float(sidewalk[bottom_y:h, x0:x1].mean())
            bottom_road = float(road[bottom_y:h, x0:x1].mean())
            if (
                bottom_side >= self.profile.curb_center_side_min
                and bottom_road <= 0.40
            ):
                band_y0, band_y1 = int(0.50 * h), int(0.85 * h)
                band = road[band_y0:band_y1, x0:x1]
                if band.size:
                    row_road = band.mean(axis=1)
                    strong_rows = int((row_road >= 0.50).sum())
                    mean_road = float(row_road.mean()) if row_road.size else 0.0
                    if (
                        strong_rows >= 3
                        and mean_road >= self.profile.curb_center_road_min
                    ):
                        return {
                            "message": curb_message("ahead"),
                            "key": "curb_ahead",
                            "confidence": mean_road,
                            "zone": "ahead",
                        }

        # --- Lateral curb: road and sidewalk both in the near lower band. ---
        lower_y = int(0.70 * h)
        best = None
        for zone, a, b in (
            ("left", 0.0, 0.33),
            ("right", 0.66, 1.0),
            ("centre", 0.33, 0.66),
        ):
            xa, xb = int(a * w), int(b * w)
            band_side = float(sidewalk[lower_y:h, xa:xb].mean())
            band_road = float(road[lower_y:h, xa:xb].mean())
            if (
                band_side >= self.profile.curb_side_min
                and band_road >= self.profile.curb_road_min
            ):
                confidence = min(band_side, band_road * 2.0)
                if best is None or confidence > best[0]:
                    best = (confidence, zone)

        if best is not None:
            confidence, zone = best
            return {
                "message": curb_message(zone),
                "key": f"curb_{zone}",
                "confidence": confidence,
                "zone": zone,
            }

        return None


class SceneDescriber:
    """Low-priority descriptions from the semantic mask."""

    SCENE_CLASSES = ("vegetation", "building", "wall", "fence")

    def __init__(self, profile):
        self.profile = profile

    def analyze(self, mask, class_names, now=None):
        if mask is None or class_names is None or getattr(mask, "ndim", 0) != 2:
            return None

        names = class_ids(class_names)
        scene_ids = {
            name: names[name]
            for name in self.SCENE_CLASSES
            if name in names
        }
        if not scene_ids:
            return None

        mask = _resize_mask(mask, max_w=320)
        h, w = mask.shape[:2]
        y0, y1 = int(0.05 * h), int(0.85 * h)

        best = None
        for name, idx in scene_ids.items():
            for side, a, b in (
                ("left", 0.0, 0.33),
                ("centre", 0.33, 0.66),
                ("right", 0.66, 1.0),
            ):
                xa, xb = int(a * w), int(b * w)
                region = mask[y0:y1, xa:xb]
                if not region.size:
                    continue
                fraction = float((region == idx).mean())
                if fraction < self.profile.scene_min_fraction:
                    continue
                if best is None or fraction > best[0]:
                    best = (fraction, name, side)

        if best is None:
            return None

        fraction, name, side = best
        return {
            "message": scene_message(name, side),
            "key": f"scene_{name}_{side}",
            "confidence": fraction,
            "scene_class": name,
            "side": side,
        }
