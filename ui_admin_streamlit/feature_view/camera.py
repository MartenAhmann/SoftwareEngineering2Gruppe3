from __future__ import annotations

"""Wrapper-Modul für Kamera-Funktionen in der Streamlit-Feature-View.

Die eigentliche Implementierung liegt in ``core.camera_service``.
Dieses Modul re-exportiert nur die dort definierten Funktionen, damit
bestehende Importe aus ``ui_admin_streamlit.feature_view.camera``
weiter funktionieren.
"""

from typing import List, Tuple

import numpy as np

from core.camera_service import detect_cameras, take_snapshot

__all__ = [
    "detect_cameras",
    "take_snapshot",
]
