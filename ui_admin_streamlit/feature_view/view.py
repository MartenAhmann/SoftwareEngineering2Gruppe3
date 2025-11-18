from __future__ import annotations

from typing import Dict, Any, List

import cv2
import numpy as np
import streamlit as st

from config.models import VizPreset
from config.service import load_config, load_raw_config_dict, save_raw_config_dict
from core.model_engine import ModelEngine
from core.viz_engine import VizEngine

from .camera import detect_cameras, take_snapshot
from .favorites import get_layer_favorites, upsert_favorite, delete_favorite
from .state import init_state, layer_state


def render() -> None:
    """
    Haupt-UI der Feature-View.
    """
    init_state()

    cfg = load_config()
    raw_cfg = load_raw_config_dict()

    model_engine: ModelEngine = st.session_state.feature_model_engine
    viz_engine: VizEngine = st.session_state.feature_viz_engine

    st.subheader("Feature-View – Snapshot-Konfiguration")

    # aktuell: erster UI-Layer als Kontext
    ui_layers = sorted(cfg.ui.layers, key=lambda x: x.order)
    if not ui_layers:
        st.warning("Keine UI-Layer in der Config vorhanden.")
        return
    ui_layer = ui_layers[0]
    layer_key = ui_layer.id

    st_data = layer_state(layer_key)

    # ------------------------------
    # Top-Reihe: Favorit laden (links)
    # ------------------------------
    top_left, top_right = st.columns([3, 1])
    with top_left:
        favs = get_layer_favorites(raw_cfg, ui_layer.id)
        fav_names = [f.get("name", f"fav_{i}") for i, f in enumerate(favs)]
        selected_fav_name = st.selectbox(
            "Favorit laden",
            ["–"] + fav_names,
            index=0,
            key=f"{layer_key}_fav_select_snapshot",
            help="Gespeicherte Presets für diesen UI-Layer laden.",
        )

    with top_right:
        # Kleiner "Minus"-Button zum Löschen des aktuell gewählten Favoriten
        if st.button(
                "–",
                key=f"{layer_key}_delete_fav_snapshot",
                help="Ausgewählten Favoriten löschen.",
        ):
            if selected_fav_name == "–":
                st.warning("Bitte zuerst einen Favoriten auswählen, der gelöscht werden soll.")
            else:
                raw_del = load_raw_config_dict()
                delete_favorite(raw_del, ui_layer.id, selected_fav_name)
                save_raw_config_dict(raw_del)
                st.success(f"Favorit '{selected_fav_name}' wurde gelöscht.")
                # Auswahl im Dropdown zurücksetzen
                st.rerun()

    if selected_fav_name != "–":
        for f in favs:
            if f.get("name") == selected_fav_name:
                preset = f.get("preset", {})

                # -----------------------------
                # Mode & Channels & K
                # -----------------------------
                if preset.get("channels") == "topk":
                    st_data["mode"] = "Top-K"
                    # k aus dem Preset oder Fallback 3
                    k_val = preset.get("k") if preset.get("k") is not None else st_data.get("k", 3)
                else:
                    st_data["mode"] = "Ausgewählte Channels"
                    # Channels-Liste aus dem Preset
                    st_data["channels"] = (
                        preset.get("channels", [0]) if isinstance(preset.get("channels"), list) else [0]
                    )
                    # Für Channels-Modus: letztes k beibehalten oder Default 3,
                    # aber NICHT None aus dem Preset übernehmen
                    k_val = st_data.get("k", 3)

                st_data["k"] = k_val

                # Blend-Mode, Cmap, Overlay, Alpha
                st_data["blend_mode"] = preset.get("blend_mode", "mean")
                st_data["cmap"] = preset.get("cmap", "viridis")
                st_data["overlay"] = preset.get("overlay", True)
                st_data["alpha"] = float(preset.get("alpha", 0.5))

                # Name & Model-Layer
                st_data["fav_name"] = f.get("name", "")
                new_layer_id = preset.get("model_layer_id", st_data.get("model_layer_id", "conv1"))
                st_data["model_layer_id"] = new_layer_id

                # -----------------------------
                # Streamlit-Widget-State setzen
                # -----------------------------

                # Modell-Layer-Selectbox
                st.session_state[f"{layer_key}_model_layer"] = new_layer_id

                # Mode-Radio ("Ausgewählte Channels" vs. "Top-K")
                st.session_state[f"{layer_key}_mode_snapshot"] = st_data["mode"]

                # K-Slider für Top-K (nur relevant, wenn Mode == "Top-K")
                if st_data["mode"] == "Top-K":
                    st.session_state[f"{layer_key}_k_snapshot"] = int(st_data["k"])

                # Blend-Mode-Selectbox
                st.session_state[f"{layer_key}_blend_snapshot"] = st_data["blend_mode"]

                # Colormap-Selectbox
                st.session_state[f"{layer_key}_cmap_snapshot"] = st_data["cmap"]

                # Overlay-Checkbox
                st.session_state[f"{layer_key}_overlay_snapshot"] = bool(st_data["overlay"])

                # Alpha-Slider
                st.session_state[f"{layer_key}_alpha_snapshot"] = float(st_data["alpha"])

                st.success(f"Favorit '{selected_fav_name}' geladen.")
                break

    st.markdown("---")

    # ------------------------------
    # Snapshot + Controls
    # ------------------------------
    left_col, right_col = st.columns([1, 2])

    with left_col:
        cams = detect_cameras()
        if not cams:
            st.error("Keine Kameras gefunden. Bitte eine Kamera anschließen.")
            return

        cam_id = st.selectbox(
            "Kamera",
            cams,
            index=0,
            key="feature_cam_select_snapshot",
            help="Kameraquelle für den Snapshot.",
        )

        if st.button(
            "Take picture",
            help=(
                "Nimmt ein einzelnes Bild von der gewählten Kamera auf. "
                "Dieses Bild wird für alle folgenden Visualisierungen verwendet."
            ),
        ):
            snap = take_snapshot(cam_id)
            if snap is None:
                st.error("Kamera-Snapshot fehlgeschlagen.")
            else:
                st.session_state.feature_snapshot = snap

    with right_col:
        st.markdown("**Einstellungen für Modell-Output**")

        model_layers = model_engine.get_active_layers()
        if not model_layers:
            st.error("Keine aktiven Modell-Layer konfiguriert.")
            return
        current_model_layer = st_data.get("model_layer_id", "conv1")
        if current_model_layer not in model_layers:
            current_model_layer = "conv1"
        model_layer_id = st.selectbox(
            "Modell-Layer",
            model_layers,
            index=model_layers.index(current_model_layer),
            key=f"{layer_key}_model_layer",
            help=(
                "Welcher Schicht im ResNet soll angezeigt werden?\n"
                "- conv1: frühe Kanten/Filter direkt nach dem Eingang\n"
                "- layer1–layer4: immer tiefere Schichten mit komplexeren Merkmalen"
            ),
        )
        st_data["model_layer_id"] = model_layer_id

        mode = st.radio(
            "Channel-Modus",
            ["Ausgewählte Channels", "Top-K"],
            horizontal=True,
            key=f"{layer_key}_mode_snapshot",
            index=0 if st_data["mode"] == "Ausgewählte Channels" else 1,
            help=(
                "Legt fest, wie die Featuremaps (Kanäle) ausgewählt werden:\n"
                "- Ausgewählte Channels: du bestimmst einzelne Channel-Indizes manuell.\n"
                "- Top-K: es werden automatisch die K aktivsten Featuremaps gewählt."
            ),
        )
        st_data["mode"] = mode

        st.markdown("**Channels konfigurieren**")

        snapshot = st.session_state.feature_snapshot
        if snapshot is None:
            st.info("Bitte zuerst einen Snapshot aufnehmen, um Channels auswählen zu können.")
            C = None
        else:
            acts_tmp = model_engine.run_inference(snapshot)
            act_tmp = acts_tmp.get(model_layer_id)
            if act_tmp is None:
                st.error(f"Aktivierung für Modell-Layer '{model_layer_id}' nicht gefunden.")
                return
            _, C, _, _ = act_tmp.shape

        if mode == "Ausgewählte Channels":
            if C is None:
                st.caption("Noch kein Snapshot – Channel-Auswahl wird aktiviert, sobald ein Bild vorliegt.")
            else:
                last_ch = int(st_data.get("last_channel", 0))
                last_ch = max(0, min(C - 1, last_ch))
                selected_channel = st.slider(
                    "Channel wählen",
                    min_value=0,
                    max_value=C - 1,
                    value=last_ch,
                    key=f"{layer_key}_channel_slider",
                    help="Einzelner Featuremap-Channel, der zur Liste hinzugefügt werden kann.",
                )
                st_data["last_channel"] = selected_channel

                cols_add = st.columns([2, 3])
                with cols_add[0]:
                    if st.button("In Liste aufnehmen", key=f"{layer_key}_add_channel"):
                        if selected_channel not in st_data["channels"]:
                            st_data["channels"].append(selected_channel)
                            st_data["channels"] = list(dict.fromkeys(st_data["channels"]))

                with cols_add[1]:
                    st.caption("Ausgewählte Channels:")

                if not st_data["channels"]:
                    st.caption(
                        "Noch keine Channels in der Liste. "
                        "Wähle oben einen Channel und klicke auf 'In Liste aufnehmen'."
                    )
                else:
                    # Channel zum Entfernen sammeln, statt während der Iteration zu mutieren
                    remove_channel: int | None = None

                    for ch in st_data["channels"]:
                        row_cols = st.columns([4, 1])
                        with row_cols[0]:
                            st.write(f"Channel {ch}")
                        with row_cols[1]:
                            if st.button(
                                "✕",
                                key=f"{layer_key}_del_channel_{ch}",  # Key basiert auf Channel-Wert
                                help="Channel aus der Liste entfernen.",
                            ):
                                remove_channel = ch

                    if remove_channel is not None:
                        # Alle Vorkommen dieses Channels entfernen
                        st_data["channels"] = [
                            c for c in st_data["channels"] if c != remove_channel
                        ]
                        # Direkt neu rendern, damit die Liste optisch sofort aktualisiert wird
                        st.rerun()
        else:
            st_data["k"] = st.slider(
                "K für Top-K Featuremaps",
                min_value=1,
                max_value=10,
                value=int(st_data.get("k", 3)),
                key=f"{layer_key}_k_snapshot",
                help="Wie viele der aktivsten Featuremaps sollen automatisch zusammengefasst werden?",
            )

        st_data["blend_mode"] = st.selectbox(
            "Blend-Mode",
            ["mean", "max", "sum", "weighted"],
            index=["mean", "max", "sum", "weighted"].index(st_data.get("blend_mode", "mean")),
            key=f"{layer_key}_blend_snapshot",
            help=(
                "Wie mehrere Featuremaps zu einer 2D-Karte kombiniert werden:\n"
                "- mean: Mittelwert über alle gewählten Channels\n"
                "- max: pro Pixel der größte Wert über alle Channels\n"
                "- sum: Summe der Werte (stärkere Kontraste)\n"
                "- weighted: aktuell einfache Gleichgewichtung (wie mean)"
            ),
        )

        st_data["cmap"] = st.selectbox(
            "Farbschema (Colormap)",
            ["viridis", "magma", "inferno", "plasma", "jet", "red", "green", "blue"],
            index=[
                "viridis",
                "magma",
                "inferno",
                "plasma",
                "jet",
                "red",
                "green",
                "blue",
            ].index(st_data.get("cmap", "viridis")),
            key=f"{layer_key}_cmap_snapshot",
            help=(
                "Farbcodierung der Aktivierung:\n"
                "- viridis/magma/inferno/plasma/jet: wissenschaftliche Colormaps von blau → gelb etc.\n"
                "- red/green/blue: einfache Färbung nur in einem Farbkanal."
            ),
        )

        st_data["overlay"] = st.checkbox(
            "Originalbild überlagern",
            value=bool(st_data.get("overlay", True)),
            key=f"{layer_key}_overlay_snapshot",
            help=(
                "Wenn aktiviert, wird die Heatmap halbtransparent auf das Originalbild gelegt.\n"
                "Wenn deaktiviert, siehst du nur die Heatmap der Aktivierung."
            ),
        )

        st_data["alpha"] = float(
            st.slider(
                "Overlay-Alpha",
                min_value=0.0,
                max_value=1.0,
                value=float(st_data.get("alpha", 0.5)),
                key=f"{layer_key}_alpha_snapshot",
                help="Wie stark die Heatmap im Overlay sichtbar ist (0 = nur Original, 1 = nur Heatmap).",
            )
        )

    # ------------------------------
    # Inferenz + Visualisierung auf Snapshot (zwei Outputs)
    # ------------------------------
    if st.session_state.feature_snapshot is None:
        with left_col:
            st.info("Bitte zuerst einen Snapshot aufnehmen.")
        return

    snapshot = st.session_state.feature_snapshot
    acts = model_engine.run_inference(snapshot)

    act = acts.get(st_data["model_layer_id"])
    if act is None:
        with left_col:
            st.error(f"Aktivierung für Modell-Layer '{st_data['model_layer_id']}' nicht gefunden.")
        return

    _, C, _, _ = act.shape
    mode = st_data["mode"]

    # Oberes Bild: nur der aktuell gewählte Channel (Slider)
    selected_channel = int(st_data.get("last_channel", 0))
    selected_channel = max(0, min(C - 1, selected_channel))
    st_data["last_channel"] = selected_channel

    top_preset = VizPreset(
        id="temp_single",
        layer_id=st_data["model_layer_id"],
        channels=[selected_channel],
        k=None,
        blend_mode=st_data["blend_mode"],
        cmap=st_data["cmap"],
        overlay=st_data["overlay"],
        alpha=float(st_data["alpha"]),
    )

    vis_img_top = viz_engine.visualize(
        activation=act,
        preset=top_preset,
        original=snapshot if top_preset.overlay else None,
    )

    # Unteres Bild: zusammengelegte Channels (Liste oder Top-K)
    has_combined_preview = True

    if mode == "Ausgewählte Channels":
        # Nur eindeutige, gültige Channels verwenden
        unique_channels = list(
            dict.fromkeys(
                int(c) for c in st_data["channels"] if isinstance(c, int) and 0 <= c < C
            )
        )
        channels: List[int] | str = unique_channels
        k: int | None = None

        if not channels:
            has_combined_preview = False
    else:
        k_val = int(st_data["k"])
        k_val = max(1, min(min(10, C), k_val))
        st_data["k"] = k_val
        channels = "topk"
        k = k_val

    vis_img_bottom_200 = None
    if has_combined_preview:
        bottom_preset = VizPreset(
            id="temp_combined",
            layer_id=st_data["model_layer_id"],
            channels=channels,
            k=k,
            blend_mode=st_data["blend_mode"],
            cmap=st_data["cmap"],
            overlay=st_data["overlay"],
            alpha=float(st_data["alpha"]),
        )

        vis_img_bottom = viz_engine.visualize(
            activation=act,
            preset=bottom_preset,
            original=snapshot if bottom_preset.overlay else None,
        )
        vis_img_bottom_200 = cv2.resize(vis_img_bottom, (200, 200))

    vis_img_top_200 = cv2.resize(vis_img_top, (200, 200))

    with left_col:
        st.image(
            vis_img_top_200,
            caption="Ausgewählter Channel",
            use_container_width=False,
        )
        if has_combined_preview and vis_img_bottom_200 is not None:
            st.image(
                vis_img_bottom_200,
                caption="Zusammengelegte Channels aus Liste",
                use_container_width=False,
            )
        else:
            if mode == "Ausgewählte Channels":
                st.caption(
                    "Noch keine Channels in der Liste – "
                    "füge mindestens einen Channel hinzu, um die kombinierte Vorschau zu sehen."
                )

    # ------------------------------
    # Favoriten speichern/aktualisieren
    # ------------------------------
    st.markdown("---")
    st.subheader("Favorit speichern/aktualisieren")

    fav_name = st.text_input(
        "Name des Favoriten",
        value=st_data.get("fav_name", ""),
        key=f"{layer_key}_fav_name_snapshot",
        help="Beschreibe diese Einstellung mit einem Namen (z. B. 'Frühe Kanten – starke Kantenbetonung').",
    )
    st_data["fav_name"] = fav_name

    def _current_preset_dict() -> Dict[str, Any]:
        return {
            "channels": ("topk" if st_data["mode"] == "Top-K" else st_data["channels"]),
            "k": (int(st_data["k"]) if st_data["mode"] == "Top-K" else None),
            "blend_mode": st_data["blend_mode"],
            "cmap": st_data["cmap"],
            "overlay": bool(st_data["overlay"]),
            "alpha": float(st_data["alpha"]),
            "model_layer_id": st_data.get("model_layer_id", "conv1"),
        }

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "Als Favorit speichern/aktualisieren",
            key=f"{layer_key}_save_fav_snapshot",
            help="Speichert diese Einstellung als Favorit im Config-File für diesen UI-Layer.",
        ):
            if not fav_name.strip():
                st.error("Bitte einen Namen für den Favoriten angeben.")
            else:
                raw = load_raw_config_dict()
                fav = {
                    "name": fav_name.strip(),
                    "layer_id": ui_layer.id,
                    "preset": _current_preset_dict(),
                }
                upsert_favorite(raw, ui_layer.id, fav)
                save_raw_config_dict(raw)
                st.success(f"Favorit '{fav_name}' gespeichert/aktualisiert.")

    with c2:
        st.caption("Zum Laden eines Favoriten nutze das Dropdown ganz oben links.")