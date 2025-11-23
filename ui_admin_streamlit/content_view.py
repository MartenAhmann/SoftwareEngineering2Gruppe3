# ui_admin_streamlit/content_view.py
from __future__ import annotations

import streamlit as st

from config.service import (
    load_config,
    save_config,
    get_model_layer_content,
    list_all_favorites_for_model_layer,
    set_selected_kivy_favorites,
    MAX_FAVORITES_PER_MODEL_LAYER,
)
from config.models import LayerUIConfig, ModelConfig, ModelLayerContent, GlobalUITexts
from core.model_engine import ModelEngine


PAGE_ID_GLOBAL = "global"


def _get_layer_by_id(cfg, layer_id: str) -> LayerUIConfig | None:
    for layer in cfg.ui.layers:
        if layer.id == layer_id:
            return layer
    return None


def _get_model_layer_ids(cfg_model: ModelConfig) -> list[str]:
    """Bestimmt die Liste der Modell-Layer-IDs analog zur Feature-View.

    Nutzt denselben Default wie ModelEngine, falls keine explizite Liste
    hinterlegt ist. Hier wird kein ModelEngine-Objekt persistent gehalten,
    sondern nur der Kontrakt der aktiven Layer verwendet.
    """
    # Wir instanziieren die Engine kurz, um die aktive Layer-Liste zu erhalten.
    engine = ModelEngine(cfg_model)
    return engine.get_active_layers()


def render():
    """Content-Editor mit Unternavigation (Global + Modell-Layer-Pages + UI-Layerseiten)."""
    cfg = load_config()

    st.subheader("Content-Editor")

    # Sicherstellen, dass es mindestens einen UI-Layer gibt
    if not cfg.ui.layers:
        cfg.ui.layers.append(
            LayerUIConfig(
                id="layer_1_default",
                order=1,
                button_label="Frühe Kanten",
                title_bar_label="Layer 1 – Kanten",
                description="",
                viz_preset_id="preset_layer1",
            )
        )

    # Modell-Layer-Liste aus ModelConfig / ModelEngine bestimmen
    model_layer_ids = _get_model_layer_ids(cfg.model)

    # Linke Unternavigation: Global + Modell-Layer + bestehende UI-Layer
    nav_options: list[tuple[str, str]] = [("Global", PAGE_ID_GLOBAL)]

    # Gruppe Modell-Layer
    for ml_id in model_layer_ids:
        label = f"Modell-Layer: {ml_id}"
        nav_options.append((label, f"model::{ml_id}"))

    # Bestehende UI-Layer (optional weiterhin sichtbar)
    for layer in sorted(cfg.ui.layers, key=lambda l: l.order):
        label = layer.button_label or layer.id
        nav_options.append((label, layer.id))

    labels = [label for label, _ in nav_options]
    values = [value for _, value in nav_options]

    active_index = 0
    active_idx = st.radio(
        "Seite wählen",
        options=range(len(labels)),
        format_func=lambda i: labels[i],
        index=active_index,
        horizontal=False,
    )
    active_page_id = values[active_idx]

    # Rendering
    if active_page_id == PAGE_ID_GLOBAL:
        st.subheader("Globale Inhalte")
        cfg.ui.title = st.text_input("Ausstellungstitel", value=cfg.ui.title)

        # Globale UI-Texte initialisieren, falls None
        if cfg.ui.global_texts is None:
            cfg.ui.global_texts = GlobalUITexts(
                global_page_title=cfg.ui.title,
                home_button_label="Home",
            )

        gt = cfg.ui.global_texts
        gt.global_page_title = st.text_input(
            "Titel der Globalseite",
            value=gt.global_page_title or cfg.ui.title,
        )
        gt.home_button_label = st.text_input(
            "Label für Global/Home-Button",
            value=gt.home_button_label or "Home",
        )
    elif active_page_id.startswith("model::"):
        # Modell-Layer-Content-Seite
        model_layer_id = active_page_id.split("::", 1)[1]
        content: ModelLayerContent = get_model_layer_content(cfg, model_layer_id)

        st.subheader(f"Modell-Layer: {model_layer_id}")
        new_title = st.text_input("Seitentitel", value=content.title)
        new_subtitle = st.text_input(
            "Subtitle (Kamera-Ansicht)", value=content.subtitle or ""
        )
        new_description = st.text_area(
            "Beschreibung (Erklärungstext)",
            value=content.description,
            height=200,
        )

        # Änderungen in cfg.ui.model_layers zurückschreiben
        cfg.ui.model_layers[model_layer_id] = ModelLayerContent(
            title=new_title,
            subtitle=new_subtitle or None,
            description=new_description,
        )

        st.markdown("---")
        st.markdown("**Kino-Favoriten-Auswahl für diesen Modell-Layer**")

        all_favs = list_all_favorites_for_model_layer(cfg, model_layer_id)
        if not all_favs:
            st.info(
                "Für diesen Modell-Layer existieren noch keine Favoriten. "
                "Lege Favoriten in der Feature-View an."
            )
        else:
            aktuelle_auswahl = cfg.ui.kivy_favorites.get(model_layer_id, [])
            neue_auswahl: list[str] = []

            for fav in all_favs:
                name = fav.get("name", "(ohne Namen)")
                checked = name in aktuelle_auswahl
                checked = st.checkbox(
                    f"Favorit im Kino anzeigen: {name}",
                    value=checked,
                    key=f"fav_select_{model_layer_id}_{name}",
                )
                if checked:
                    neue_auswahl.append(name)

            # Temporäre Auswahl im Streamlit-State ablegen, damit der Speichern-Button darauf zugreifen kann
            st.session_state["_kivy_fav_selection_model_layer_id"] = model_layer_id
            st.session_state["_kivy_fav_selection_names"] = neue_auswahl
    else:
        # Klassische UI-Layer-Seiten (Bestand)
        layer = _get_layer_by_id(cfg, active_page_id)
        if layer is None:
            st.error(f"Unbekannter Layer: {active_page_id}")
        else:
            st.subheader(f"Layer: {layer.id}")
            layer.button_label = st.text_input("Button-Label", value=layer.button_label)
            layer.title_bar_label = st.text_input("Titelzeilen-Label", value=layer.title_bar_label)
            layer.subtitle = st.text_input("Subtitle (Kamera-Ansicht)", value=layer.subtitle or "")
            layer.description = st.text_area(
                "Beschreibung (rechte Spalte)",
                value=layer.description,
                height=200,
            )

    if st.button("Konfiguration speichern"):
        # Zusätzliche Logik: ggf. Kino-Favoriten-Auswahl speichern
        ml_id = st.session_state.get("_kivy_fav_selection_model_layer_id")
        names = st.session_state.get("_kivy_fav_selection_names")
        if ml_id is not None and names is not None:
            if len(names) > MAX_FAVORITES_PER_MODEL_LAYER:
                st.error(
                    f"Es dürfen maximal {MAX_FAVORITES_PER_MODEL_LAYER} Favoriten pro Modell-Layer im Kino aktiv sein. "
                    "Bitte Auswahl reduzieren."
                )
                return
            set_selected_kivy_favorites(cfg, ml_id, names)

        save_config(cfg)
        st.success("Gespeichert.")
