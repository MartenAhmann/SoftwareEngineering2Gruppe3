from __future__ import annotations

from typing import List

import cv2
import numpy as np


def detect_cameras(max_tested: int = 5) -> List[int]:
    """
    Testet die ersten max_tested Kamera-IDs und gibt die gefundenen zurück.
    """
    cams: List[int] = []
    for cam_id in range(max_tested):
        cap = cv2.VideoCapture(cam_id)
        if cap is not None and cap.isOpened():
            cams.append(cam_id)
            cap.release()
    return cams


def take_snapshot(cam_id: int) -> np.ndarray | None:
    """
    Nimmt ein einzelnes Bild von der angegebenen Kamera auf.
    Rückgabe: RGB-Array oder None bei Fehler.
    """
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        return None
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)