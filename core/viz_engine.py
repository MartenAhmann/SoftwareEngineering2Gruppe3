# core/viz_engine.py

from __future__ import annotations

import numpy as np
import cv2
from typing import List, Dict
from config.models import VizPreset


class VizEngine:
    """
    Wandelt Aktivierungen eines Layers + VizPreset in ein darstellbares RGB-Bild um.
    Unterstützt:
    - Auswahl mehrerer Featuremaps
    - Blend-Modi (mean, max, sum, weighted)
    - Colormaps (OpenCV + einfache RGB-Verstärkungsmodi)
    - Overlay über Originalbild
    """

    # -----------------------------
    # 1. Hauptmethode
    # -----------------------------
    def visualize(
        self,
        activation: np.ndarray,       # shape: (1, C, H, W)
        preset: VizPreset,
        original: np.ndarray | None = None,  # optional (H,W,3)
    ) -> np.ndarray:
        """
        Gibt ein fertiges RGB-Bild zurück (uint8), HxWx3.
        """

        # -------------------------
        # A) Featuremaps auswählen
        # -------------------------
        fmap = self._select_featuremaps(activation, preset)

        # -------------------------
        # B) Featuremaps reduzieren
        # -------------------------
        reduced = self._reduce_featuremaps(fmap, preset)

        # -------------------------
        # C) Normalisieren
        # -------------------------
        heatmap_gray = self._normalize(reduced)

        # -------------------------
        # D) Colormap anwenden
        # -------------------------
        heatmap_rgb = self._apply_colormap(heatmap_gray, preset)

        # -------------------------
        # E) Overlay
        # -------------------------
        if preset.overlay and original is not None:
            heatmap_rgb = self._overlay(heatmap_rgb, original, preset.alpha)

        return heatmap_rgb

    # -----------------------------
    # 2. Featuremap-Auswahl
    # -----------------------------

    def _select_featuremaps(self, activation: np.ndarray, preset: VizPreset) -> np.ndarray:
        """
        Gibt ein Array shape (N_selected, H, W) zurück.
        """
        _, C, H, W = activation.shape

        if preset.channels == "topk":
            # Energie-basierte Auswahl (größte Varianz)
            k = preset.k if preset.k is not None else 3
            variances = activation.reshape(C, -1).var(axis=1)
            idx = np.argsort(variances)[-k:]
            return activation[0, idx, :, :]

        # explizite Liste
        idx_list = [i for i in preset.channels if 0 <= i < C]
        return activation[0, idx_list, :, :]

    # -----------------------------
    # 3. Reduktion
    # -----------------------------

    def _reduce_featuremaps(self, fmap: np.ndarray, preset: VizPreset) -> np.ndarray:
        """
        fmap shape = (N, H, W)
        Gibt 2D-Map zurück (H, W).
        """
        if fmap.ndim == 2:
            return fmap

        if preset.blend_mode == "mean":
            return fmap.mean(axis=0)
        elif preset.blend_mode == "max":
            return fmap.max(axis=0)
        elif preset.blend_mode == "sum":
            return fmap.sum(axis=0)
        elif preset.blend_mode == "weighted":
            # simple weights = 1/N (kann später konfigurierbar werden)
            w = np.ones(fmap.shape[0]) / fmap.shape[0]
            return np.tensordot(w, fmap, axes=(0, 0))
        else:
            return fmap.mean(axis=0)

    # -----------------------------
    # 4. Normalisierung
    # -----------------------------

    def _normalize(self, fmap: np.ndarray) -> np.ndarray:
        """
        fmap -> skaliert auf 0-255 uint8
        """
        fmap = fmap - fmap.min()
        maxv = fmap.max()
        fmap = fmap / maxv if maxv > 0 else fmap
        fmap = (fmap * 255).clip(0, 255).astype(np.uint8)
        return fmap

    # -----------------------------
    # 5. Colormaps
    # -----------------------------

    def _apply_colormap(self, gray: np.ndarray, preset: VizPreset) -> np.ndarray:
        """
        Unterstützte Modi:
        - OpenCV-Colormaps: viridis, magma, inferno, etc.
        - simple RGB highlighting: "red", "green", "blue"
        """
        cmap = preset.cmap.lower()

        if cmap in ["red", "r"]:
            rgb = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
            rgb[:, :, 2] = gray
            return rgb

        if cmap in ["green", "g"]:
            rgb = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
            rgb[:, :, 1] = gray
            return rgb

        if cmap in ["blue", "b"]:
            rgb = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
            rgb[:, :, 0] = gray
            return rgb

        # OpenCV colormaps
        cv_maps = {
            "viridis": cv2.COLORMAP_VIRIDIS,
            "magma": cv2.COLORMAP_MAGMA,
            "inferno": cv2.COLORMAP_INFERNO,
            "plasma": cv2.COLORMAP_PLASMA,
            "jet": cv2.COLORMAP_JET,
        }

        if cmap in cv_maps:
            return cv2.applyColorMap(gray, cv_maps[cmap])

        # fallback
        return cv2.applyColorMap(gray, cv2.COLORMAP_VIRIDIS)

    # -----------------------------
    # 6. Overlay
    # -----------------------------

    def _overlay(self, heatmap_rgb: np.ndarray, original: np.ndarray, alpha: float) -> np.ndarray:
        """
        Beide müssen HxWx3 uint8 sein.
        """
        # resize original to heatmap size
        H, W, _ = heatmap_rgb.shape
        original_resized = cv2.resize(original, (W, H))

        blended = cv2.addWeighted(original_resized, 1 - alpha, heatmap_rgb, alpha, 0)
        return blended


# ------------------------------------------------------
# Minimaler Selbsttest (optional)
# ------------------------------------------------------

if __name__ == "__main__":
    # Dummy test: einfache Heatmap aus zufälligen Activations
    fmap = np.random.rand(1, 5, 20, 20).astype(np.float32)
    preset = VizPreset(id="p1", layer_id="conv1", channels=[0, 1], blend_mode="mean")

    engine = VizEngine()
    img = engine.visualize(fmap, preset)

    print("Output shape:", img.shape)  # (H, W, 3)
