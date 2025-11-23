from __future__ import annotations

import logging
import time
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CameraStream:
    """Persistenter Kamera-Stream auf Basis von OpenCV.

    - Öffnet die Kamera einmal im Konstruktor.
    - Liefert über ``read()`` fortlaufend Frames.
    - Wird über ``release()`` explizit geschlossen.

    Diese Klasse ist für „echte“ Live-Streams gedacht (z.B. Kivy-Kino-View),
    während :func:`take_snapshot` weiterhin den einfachen Einmal-Snapshot
    für Streamlit/Feature-View bereitstellt.
    """

    def __init__(self, cam_id: int, width: int | None = None, height: int | None = None):
        self.cam_id = cam_id
        self._cap = cv2.VideoCapture(cam_id)
        if not self._cap or not self._cap.isOpened():
            raise RuntimeError(f"Kamera {cam_id} konnte nicht geöffnet werden")

        # Optionale Auflösung setzen
        if width is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self) -> tuple[np.ndarray | None, str]:
        """Liest ein einzelnes Frame aus dem offenen Stream.

        Returns:
            (RGB-Array oder None, Fehlermeldung oder "").
        """
        if self._cap is None or not self._cap.isOpened():
            return None, f"Kamera {self.cam_id} ist nicht geöffnet"

        try:
            ok, frame = self._cap.read()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Fehler beim Lesen vom Kamera-Stream {self.cam_id}: {e}")
            return None, f"Fehler beim Lesen vom Kamera-Stream: {e}"

        if not ok or frame is None:
            logger.error(f"Kamera {self.cam_id} liefert kein Bild (Stream)")
            return None, f"Kamera {self.cam_id} liefert kein Bild"

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return rgb_frame, ""
        except Exception as e:  # noqa: BLE001
            logger.error(f"Fehler bei Farbkonvertierung im Stream: {e}")
            return None, f"Fehler bei Farbkonvertierung: {e}"

    def release(self) -> None:
        """Schließt den Kamera-Stream, wenn er geöffnet ist."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


def detect_cameras(max_tested: int = 5) -> List[int]:
    """Testet die ersten ``max_tested`` Kamera-IDs und gibt die gefundenen zurück.

    Args:
        max_tested: Anzahl der zu prüfenden Kamera-IDs ab 0.

    Returns:
        Liste der Kamera-IDs, die erfolgreich geöffnet werden konnten.
    """
    cams: List[int] = []
    for cam_id in range(max_tested):
        try:
            cap = cv2.VideoCapture(cam_id)
            if cap is not None and cap.isOpened():
                cams.append(cam_id)
                cap.release()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Fehler beim Testen von Kamera {cam_id}: {e}")
            continue
    return cams


def take_snapshot(cam_id: int, timeout: float = 30.0) -> Tuple[np.ndarray | None, str]:
    """Nimmt ein einzelnes Bild von der angegebenen Kamera auf.

    Args:
        cam_id: ID der Kamera
        timeout: Maximale Wartezeit in Sekunden

    Returns:
        Tuple (RGB-Array oder None, Fehlermeldung oder "")
        - Bei Erfolg: (image, "")
        - Bei Fehler: (None, "Fehlerbeschreibung")
    """
    start_time = time.time()

    try:
        cap = cv2.VideoCapture(cam_id)
    except Exception as e:  # noqa: BLE001
        error_msg = f"Kamera konnte nicht initialisiert werden: {e}"
        logger.error(error_msg)
        return None, error_msg

    if not cap.isOpened():
        error_msg = f"Kamera {cam_id} nicht gefunden oder Zugriff verweigert"
        logger.error(error_msg)
        return None, error_msg

    # Timeout-Check
    if time.time() - start_time > timeout:
        cap.release()
        error_msg = f"Timeout beim Öffnen der Kamera {cam_id}"
        logger.error(error_msg)
        return None, error_msg

    try:
        ok, frame = cap.read()
    except Exception as e:  # noqa: BLE001
        cap.release()
        error_msg = f"Fehler beim Lesen vom Kamera-Feed: {e}"
        logger.error(error_msg)
        return None, error_msg
    finally:
        cap.release()

    if not ok or frame is None:
        error_msg = f"Kamera {cam_id} liefert kein Bild"
        logger.error(error_msg)
        return None, error_msg

    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return rgb_frame, ""
    except Exception as e:  # noqa: BLE001
        error_msg = f"Fehler bei Farbkonvertierung: {e}"
        logger.error(error_msg)
        return None, error_msg
