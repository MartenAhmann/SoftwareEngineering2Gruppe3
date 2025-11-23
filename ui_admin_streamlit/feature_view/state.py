from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

import numpy as np
import streamlit as st

from config.models import ModelConfig
from core.model_engine import ModelEngine
from core.viz_engine import VizEngine
from .constants import (
    MODE_SELECTED_CHANNELS,
    DEFAULT_BLEND_MODE,
    DEFAULT_COLORMAP,
    DEFAULT_ALPHA,
    DEFAULT_TOP_K
)


@dataclass
class LayerState:
    """
    Typisierter State für einen UI-Layer in der Feature-View.
    """
    mode: str = MODE_SELECTED_CHANNELS
    channels: List[int] = field(default_factory=list)
    k: int = DEFAULT_TOP_K
    blend_mode: str = DEFAULT_BLEND_MODE
    colormap: str = DEFAULT_COLORMAP
    overlay: bool = False
    alpha: float = DEFAULT_ALPHA
    model_layer_id: str = "conv1"
    last_channel: int = 0
    fav_name: str = ""
    # Name des Favoriten, der zuletzt explizit in diesen Layer-State geladen wurde.
    # Wichtig: Dieser Name wird NICHT automatisch bei jedem Render neu angewendet,
    # sondern dient nur als Bearbeitungs-Kontext ("Favorit bearbeiten").
    editing_favorite_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert LayerState zu Dict für Session-State."""
        return {
            "mode": self.mode,
            "channels": self.channels,
            "k": self.k,
            "blend_mode": self.blend_mode,
            "cmap": self.colormap,
            "overlay": self.overlay,
            "alpha": self.alpha,
            "model_layer_id": self.model_layer_id,
            "last_channel": self.last_channel,
            "fav_name": self.fav_name,
            "editing_favorite_name": self.editing_favorite_name,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "LayerState":
        """Erstellt LayerState aus Dict."""
        return LayerState(
            mode=d.get("mode", MODE_SELECTED_CHANNELS),
            channels=d.get("channels", []),
            k=d.get("k", DEFAULT_TOP_K),
            blend_mode=d.get("blend_mode", DEFAULT_BLEND_MODE),
            colormap=d.get("cmap", DEFAULT_COLORMAP),
            overlay=d.get("overlay", False),
            alpha=d.get("alpha", DEFAULT_ALPHA),
            model_layer_id=d.get("model_layer_id", "conv1"),
            last_channel=d.get("last_channel", 0),
            fav_name=d.get("fav_name", ""),
            editing_favorite_name=d.get("editing_favorite_name"),
        )


def compute_snapshot_hash(image: np.ndarray) -> str:
    """
    Berechnet MD5-Hash eines Bildarrays für Cache-Vergleich.
    """
    return hashlib.md5(image.tobytes()).hexdigest()


def init_state() -> None:
    """
    Initialisiert die für die Feature-View benötigten Session-State-Einträge.
    """
    if "feature_model_engine" not in st.session_state:
        st.session_state.feature_model_engine = ModelEngine(
            ModelConfig(name="resnet18", weights="imagenet"),
            active_layer_ids=["conv1", "layer1", "layer2", "layer3", "layer4"],
        )
    if "feature_viz_engine" not in st.session_state:
        st.session_state.feature_viz_engine = VizEngine()
    if "feature_state" not in st.session_state:
        st.session_state.feature_state = {}  # je ui-layer-id: UI-Parameter
    if "feature_snapshot" not in st.session_state:
        st.session_state.feature_snapshot = None  # np.ndarray | None

    # Aktivierungs-Cache
    if "feature_activation_cache" not in st.session_state:
        st.session_state.feature_activation_cache = {
            "snapshot_hash": None,
            "activations": None,
        }

    # Flag für einmaliges Laden eines Favoriten je Layer-Key
    if "feature_favorite_load_flags" not in st.session_state:
        # Struktur: { layer_key: bool }
        st.session_state.feature_favorite_load_flags = {}


def get_cached_activations(snapshot: np.ndarray, model_engine: ModelEngine) -> Dict[str, np.ndarray]:
    """
    Führt Inferenz durch oder gibt gecachtes Ergebnis zurück.
    Cache-Key ist der Hash des Snapshot-Bildes.
    """
    snapshot_hash = compute_snapshot_hash(snapshot)
    cache = st.session_state.feature_activation_cache

    if cache["snapshot_hash"] == snapshot_hash and cache["activations"] is not None:
        # Cache Hit
        return cache["activations"]
    else:
        # Cache Miss - neue Inferenz
        activations = model_engine.run_inference(snapshot)
        cache["snapshot_hash"] = snapshot_hash
        cache["activations"] = activations
        return activations


def layer_state(layer_key: str) -> Dict[str, Any]:
    """
    Liefert (und initialisiert) den UI-State für einen einzelnen UI-Layer.
    Intern wird mit Dict gearbeitet für Kompatibilität mit Streamlit Session-State.
    """
    if layer_key not in st.session_state.feature_state:
        # Initialisiere mit Default-LayerState
        default_state = LayerState()
        st.session_state.feature_state[layer_key] = default_state.to_dict()

    return st.session_state.feature_state[layer_key]


def get_layer_state_typed(layer_key: str) -> LayerState:
    """
    Liefert den UI-State als typisiertes LayerState-Objekt.
    """
    state_dict = layer_state(layer_key)
    return LayerState.from_dict(state_dict)


def set_layer_state(layer_key: str, state: LayerState) -> None:
    """
    Setzt den UI-State für einen Layer aus einem LayerState-Objekt.
    """
    st.session_state.feature_state[layer_key] = state.to_dict()