# ui_admin_streamlit/content_view.py
from __future__ import annotations

import streamlit as st

from config.service import load_config, save_config
from config.models import LayerUIConfig


def render():
    """
    Content-Editor:
    - Globaler Ausstellungstitel
    - (vorerst) erster Layer: Texte bearbeiten
    """
    cfg = load_config()

    st.subheader("Globaler Ausstellungstitel")
    cfg.ui.title = st.text_input("Titel", value=cfg.ui.title)

    st.subheader("Layer – Textkonfiguration (minimal)")

    if not cfg.ui.layers:
        cfg.ui.layers.append(
            LayerUIConfig(
                id="layer1_conv1",
                order=1,
                button_label="Frühe Kanten",
                title_bar_label="Layer 1 – Kanten",
                description="",
                viz_preset_id="preset_layer1",
            )
        )

    # aktuell minimal: nur den ersten konfigurierbar machen
    layer = cfg.ui.layers[0]

    layer.button_label = st.text_input("Button-Label", value=layer.button_label)
    layer.title_bar_label = st.text_input("Titelzeilen-Label", value=layer.title_bar_label)
    layer.description = st.text_area("Beschreibung (rechte Spalte)", value=layer.description, height=200)

    if st.button("Konfiguration speichern"):
        save_config(cfg)
        st.success("Gespeichert.")