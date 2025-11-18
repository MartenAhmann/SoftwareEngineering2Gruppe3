from __future__ import annotations

from typing import Dict, Any

import streamlit as st

from config.models import ModelConfig
from core.model_engine import ModelEngine
from core.viz_engine import VizEngine


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


def layer_state(layer_key: str) -> Dict[str, Any]:
    """
    Liefert (und initialisiert) den UI-State für einen einzelnen UI-Layer.
    """
    s = st.session_state.feature_state.setdefault(layer_key, {})
    s.setdefault("mode", "Ausgewählte Channels")
    s.setdefault("channels", [])
    s.setdefault("k", 3)
    s.setdefault("blend_mode", "mean")
    s.setdefault("cmap", "viridis")
    s.setdefault("overlay", False)
    s.setdefault("alpha", 0.5)
    s.setdefault("fav_name", "")
    s.setdefault("model_layer_id", "conv1")
    s.setdefault("last_channel", 0)
    return s