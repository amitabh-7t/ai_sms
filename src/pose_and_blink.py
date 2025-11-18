"""
pose_and_blink.py

Utilities for:
 - head-pose estimation (yaw, pitch, roll)
 - eye-aspect-ratio (EAR) calculation for blink detection
 - blink-rate computation (blinks per minute)

Uses MediaPipe FaceMesh if available for robust landmark extraction.
Functions accept mediapipe-style landmarks (list of normalized landmarks).
"""

import math
import time
from collections import deque

import numpy as np
import cv2

# Try lazy import for mediapipe (not required on systems without it)
USE_MEDIAPIPE = False
try:
    import mediapipe as mp  # type: ignore
    USE_MEDIAPIPE = True
except Exception:
    USE_MEDIAPIPE = False

# Common landmark indices used for EAR and solvePnP.
# These are typical Mediapipe FaceMesh indices (verify visually if needed).
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]    # [p0,p1,p2,p3,p4,p5]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

# 3D model points for solvePnP. Units are arbitrary but consistent.
MODEL_POINTS_3D = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye left corner
    (225.0, 170.0, -135.0),      # Right eye right corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)


def normalized_landmark_to_xy(landmark, image_w: int, image_h: int):
    """Convert a mediapipe normalized landmark to image x,y coords."""
    return (landmark.x * image_w, landmark.y * image_h)


def eye_aspect_ratio(landmarks, indices, image_w: int, image_h: int) -> float:
    """
    Compute EAR given mediapipe landmarks list and indices for the eye.
    indices: list of 6 indices that correspond to the eye landmarks.
    Returns EAR (float). Lower EAR indicates closed eye.
    """
    try:
        pts = [np.array(normalized_landmark_to_xy(landmarks[i], image_w, image_h)) for i in indices]
        # vertical distances
        A = np.linalg.norm(pts[1] - pts[5])
        B = np.linalg.norm(pts[2] - pts[4])
        # horizontal distance
        C = np.linalg.norm(pts[0] - pts[3])
        if C == 0:
            return 0.0
        ear = (A + B) / (2.0 * C)
        return float(ear)
    except Exception:
        return 0.0


def get_head_pose(landmarks, image_w: int, image_h: int):
    """
    Estimate head pose (yaw, pitch, roll) in degrees using solvePnP.
    landmarks: mediapipe landmarks list (normalized)
    Returns tuple (yaw, pitch, roll)
    """
    try:
        image_points = np.array([
            normalized_landmark_to_xy(landmarks[1], image_w, image_h),    # nose tip
            normalized_landmark_to_xy(landmarks[199], image_w, image_h),  # chin (approx)
            normalized_landmark_to_xy(landmarks[33], image_w, image_h),   # left eye left corner
            normalized_landmark_to_xy(landmarks[263], image_w, image_h),  # right eye right corner
            normalized_landmark_to_xy(landmarks[61], image_w, image_h),   # left mouth corner
            normalized_landmark_to_xy(landmarks[291], image_w, image_h)   # right mouth corner
        ], dtype=np.float64)

        focal_length = image_w
        center = (image_w / 2.0, image_h / 2.0)
        camera_matrix = np.array([[focal_length, 0, center[0]],
                                  [0, focal_length, center[1]],
                                  [0, 0, 1]], dtype="double")
        dist_coeffs = np.zeros((4, 1))  # assume no lens distortion

        success, rotation_vector, translation_vector = cv2.solvePnP(
            MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return 0.0, 0.0, 0.0

        # Convert rotation vector to rotation matrix
        rmat, _ = cv2.Rodrigues(rotation_vector)
        pose_mat = np.hstack((rmat, translation_vector))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
        pitch, yaw, roll = euler_angles.flatten()
        # return yaw, pitch, roll for consistency with earlier code
        return float(yaw), float(pitch), float(roll)
    except Exception:
        return 0.0, 0.0, 0.0


class BlinkTracker:
    """
    Track blinks over time using EAR threshold and debounce logic.
    Use:
      bt = BlinkTracker(ear_thresh=0.20, debounce_frames=3, window_seconds=60)
      bt.update(ear_value)  # call every frame
      bt.is_blinking()  # current boolean state
      bt.blinks_per_minute()  # blinks per minute (float)
    """

    def __init__(self, ear_thresh: float = 0.20, debounce_frames: int = 3, window_seconds: int = 60):
        self.ear_thresh = ear_thresh
        self.debounce_frames = debounce_frames
        self.window_seconds = window_seconds
        self._frame_below = 0
        self._last_blink_ts = deque()
        self._is_closed = False

    def update(self, ear_value: float):
        """
        Update tracker with latest EAR. Should be called once per frame.
        Returns True if a blink was registered on this update.
        """
        now = time.time()
        blink_registered = False

        if ear_value < self.ear_thresh:
            self._frame_below += 1
        else:
            if self._frame_below >= self.debounce_frames:
                # We count this as one blink
                self._last_blink_ts.append(now)
                blink_registered = True
            self._frame_below = 0

        # purge old timestamps outside window
        while self._last_blink_ts and (now - self._last_blink_ts[0]) > self.window_seconds:
            self._last_blink_ts.popleft()

        return blink_registered

    def blinks_per_minute(self) -> float:
        """Return estimated blinks per minute over the configured window."""
        if not self._last_blink_ts:
            return 0.0
        # window_seconds -> minutes
        minutes = max( (time.time() - self._last_blink_ts[0]) / 60.0, 1.0)
        return float(len(self._last_blink_ts) / minutes)

    def recent_blinks_count(self) -> int:
        return len(self._last_blink_ts)

    def is_eye_closed(self) -> bool:
        return self._frame_below >= self.debounce_frames