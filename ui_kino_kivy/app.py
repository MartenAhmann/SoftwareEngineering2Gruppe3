# ui_kino_kivy/app.py
import sys
import logging
from pathlib import Path

import numpy as np

# --- Quickfix für Imports ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture

from config.service import (
    load_config,
    get_model_layer_content,
    get_selected_kivy_favorites,
)
from config.models import ModelConfig, ModelLayerContent, VizPreset
from core.model_engine import ModelEngine
from core.viz_engine import VizEngine
from core import camera_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LIVE_UPDATE_INTERVAL = 1/30  # echtes Livebild anstreben (~30 FPS)


class ExhibitRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Session-Only-State für Favoriten (pro model_layer_id)
        self.session_removed_favorites: dict[str, set[str]] = {}
        self.active_page_id: str | None = None  # "global" oder model_layer_id

        # Live-/Model-/Viz-State
        self.model_engine: ModelEngine | None = None
        self.viz_engine: VizEngine | None = None
        self.live_cam_id: int | None = None
        self.live_active_favorite: dict | None = None
        self.live_active_layer_id: str | None = None
        self.live_clock_event = None
        self.vis_image: Image | None = None
        self.vis_status_label: Label | None = None
        self.camera_stream: camera_service.CameraStream | None = None

        # Config laden mit Fehlerbehandlung
        try:
            self.cfg = load_config()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Config: {e}")
            self._show_error_ui(f"Fehler beim Laden der Konfiguration:\n{e}")
            return

        # Modell-Layer-Liste bestimmen (selber Vertrag wie Feature-View)
        try:
            self.model_layer_ids = self._get_model_layer_ids(self.cfg.model)
        except Exception as e:
            logger.error(f"Fehler beim Bestimmen der Modell-Layer: {e}")
            self._show_error_ui(f"Fehler beim Bestimmen der Modell-Layer:\n{e}")
            return

        if not self.model_layer_ids:
            logger.error("Keine Modell-Layer konfiguriert")
            self._show_error_ui("Keine Modell-Layer konfiguriert. Bitte Admin-View prüfen.")
            return

        # Model- und Viz-Engine initialisieren
        try:
            self.model_engine = ModelEngine(self.cfg.model)
            self.viz_engine = VizEngine()
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren von Model/VizEngine: {e}")
            self._show_error_ui(f"Fehler beim Initialisieren der Modell-/Visualisierungs-Engine:\n{e}")
            return

        try:
            self._build_titlebar()
            self._build_middle_area()
            self._build_buttonbar()
            # Starte auf Globalseite
            self.switch_to_page("global")
        except Exception as e:
            logger.error(f"Fehler beim Aufbau der UI: {e}")
            self._show_error_ui(f"Fehler beim Aufbau der Oberfläche:\n{e}")

    # ----------------------------------------------------
    # Hilfsfunktionen
    # ----------------------------------------------------

    def _show_error_ui(self, message: str) -> None:
        """Zeigt eine Fehler-UI an, wenn die normale UI nicht aufgebaut werden kann."""
        error_label = Label(
            text=f"[b]FEHLER[/b]\n\n{message}",
            markup=True,
            halign="center",
            valign="middle",
            color=(1, 0, 0, 1)
        )
        error_label.bind(size=lambda *x: setattr(error_label, "text_size", error_label.size))
        self.add_widget(error_label)

    def _get_model_layer_ids(self, cfg_model: ModelConfig) -> list[str]:
        """Bestimmt aktive Modell-Layer analog zur Feature-View über ModelEngine."""
        engine = ModelEngine(cfg_model)
        return engine.get_active_layers()

    # ----------------------------------------------------
    # UI-Bau
    # ----------------------------------------------------

    def _build_titlebar(self):
        gt = self.cfg.ui.global_texts
        title_text = (
            gt.global_page_title
            if gt is not None and gt.global_page_title
            else self.cfg.ui.title
        )

        titlebar = Label(
            text=title_text,
            size_hint_y=0.10,
            halign="center",
            valign="middle"
        )
        titlebar.bind(size=lambda *x: setattr(titlebar, "text_size", titlebar.size))
        self.add_widget(titlebar)

    def _build_middle_area(self):
        middle = BoxLayout(orientation="horizontal", size_hint_y=0.75)

        # Linke Seite: Visualisierung als Kivy-Image + Statuslabel
        left = BoxLayout(orientation="vertical", size_hint_x=0.5)

        self.vis_image = Image()
        self.vis_status_label = Label(
            text="Wähle einen Favoriten, um Live zu starten.",
            halign="center",
            valign="middle",
            size_hint_y=0.2,
        )
        self.vis_status_label.bind(size=lambda *x: setattr(self.vis_status_label, "text_size", self.vis_status_label.size))

        left.add_widget(self.vis_image)
        left.add_widget(self.vis_status_label)

        # Rechte Seite: Subtitle + Beschreibung + Favoriten
        right = BoxLayout(orientation="vertical")

        self.subtitle_label = Label(
            text="",
            halign="left",
            valign="top",
            size_hint_y=0.15,
        )
        self.subtitle_label.bind(size=lambda *x: setattr(self.subtitle_label, "text_size", self.subtitle_label.size))

        self.desc_label = Label(
            text="",
            halign="left",
            valign="top",
            size_hint_y=0.55,
        )
        self.desc_label.bind(size=lambda *x: setattr(self.desc_label, "text_size", self.desc_label.size))

        self.favorites_box = BoxLayout(orientation="vertical", size_hint_y=0.30)

        right.add_widget(self.subtitle_label)
        right.add_widget(self.desc_label)
        right.add_widget(self.favorites_box)

        middle.add_widget(left)
        middle.add_widget(right)
        self.add_widget(middle)

    def _build_buttonbar(self):
        bottom = BoxLayout(orientation="horizontal", size_hint_y=0.15)

        # Global-Button
        gt = self.cfg.ui.global_texts
        global_label = (
            gt.home_button_label
            if gt is not None and gt.home_button_label
            else "Global"
        )

        global_btn = Button(
            text=global_label,
            on_press=lambda instance: self.switch_to_page("global"),
        )
        bottom.add_widget(global_btn)

        # Buttons für alle Modell-Layer
        for ml_id in self.model_layer_ids:
            btn = Button(
                text=ml_id,
                on_press=lambda instance, page_id=ml_id: self.switch_to_page(page_id),
            )
            bottom.add_widget(btn)

        self.add_widget(bottom)

    # ----------------------------------------------------
    # Page- und Favoriten-Logik
    # ----------------------------------------------------

    def switch_to_page(self, page_id: str) -> None:
        """Wechselt zwischen Globalseite ("global") und Modell-Layer-Seiten (page_id == model_layer_id)."""
        # Beim Seitenwechsel laufenden Live-Modus stoppen
        if self.live_clock_event is not None:
            self.stop_live()

        self.active_page_id = page_id

        if page_id == "global":
            self._render_global_page()
        else:
            if page_id not in self.model_layer_ids:
                logger.error(f"Unbekannte page_id '{page_id}' – zeige Fehlerhinweis")
                self._show_error_ui(f"Unbekannte Seite: {page_id}")
                return
            self._render_model_layer_page(page_id)

    def _render_global_page(self) -> None:
        """Setzt UI-Inhalte für die Globalseite."""
        if self.vis_status_label is not None:
            self.vis_status_label.text = "Wähle einen Favoriten, um Live zu starten."
        self.subtitle_label.text = ""
        self.desc_label.text = "Willkommen in der Ausstellung. Wähle unten einen Layer, um Details zu sehen."
        self._render_favorites(None)

    def _render_model_layer_page(self, model_layer_id: str) -> None:
        """Setzt UI-Inhalte für eine Modell-Layer-Seite inkl. Subtitle und Favoriten."""
        content: ModelLayerContent = get_model_layer_content(self.cfg, model_layer_id)
        if self.vis_status_label is not None:
            self.vis_status_label.text = "Wähle einen Favoriten, um Live zu starten."
        self.subtitle_label.text = content.subtitle or ""
        self.desc_label.text = content.description
        self._render_favorites(model_layer_id)

    def _render_favorites(self, model_layer_id: str | None) -> None:
        """Rendert den Favoriten-Bereich für die gegebene Modell-Layer-Seite. Bei None: leert den Bereich."""
        self.favorites_box.clear_widgets()

        if model_layer_id is None:
            return

        favorites = get_selected_kivy_favorites(self.cfg, model_layer_id)

        # Session-only entfernte Favoriten herausfiltern
        removed = self.session_removed_favorites.get(model_layer_id, set())
        visible_favorites = [f for f in favorites if f.get("name") not in removed]

        if not visible_favorites:
            self.favorites_box.add_widget(
                Label(
                    text="Keine Favoriten hinterlegt",
                    halign="left",
                    valign="top",
                )
            )
            return

        for fav in visible_favorites:
            name = fav.get("name", "(ohne Namen)")

            row = BoxLayout(orientation="horizontal")

            def make_select_handler(ml_id: str, fav_name: str, fav_dict: dict):
                return lambda instance: self.on_favorite_select(ml_id, fav_name, fav_dict)

            def make_remove_handler(ml_id: str, fav_name: str):
                return lambda instance: self.on_favorite_remove_ui(ml_id, fav_name)

            select_btn = Button(
                text=name,
                on_press=make_select_handler(model_layer_id, name, fav),
            )
            remove_btn = Button(
                text="X",
                size_hint_x=0.2,
                on_press=make_remove_handler(model_layer_id, name),
            )
            row.add_widget(select_btn)
            row.add_widget(remove_btn)
            self.favorites_box.add_widget(row)

    def on_favorite_select(self, model_layer_id: str, favorite_name: str, favorite: dict) -> None:
        """Event-Handler für die Auswahl eines Favoriten: startet Live-Modus für diesen Favoriten."""
        logger.info(
            f"Favorite ausgewählt: model_layer_id={model_layer_id}, name={favorite_name}, preset={favorite.get('preset')}"
        )

        # Falls bereits ein Live-Modus läuft, zuerst stoppen
        if self.live_clock_event is not None:
            self.stop_live()

        # Kamera-ID bestimmen (zunächst 0 oder erste gefundene)
        cams = camera_service.detect_cameras(max_tested=5)
        if not cams:
            if self.vis_status_label is not None:
                self.vis_status_label.text = "Keine Kamera gefunden."
            logger.error("Keine Kamera verfügbar für Live-Modus")
            return

        self.live_cam_id = cams[0]

        # Vorherigen Stream schließen, neuen öffnen
        if self.camera_stream is not None:
            self.camera_stream.release()
            self.camera_stream = None
        try:
            self.camera_stream = camera_service.CameraStream(self.live_cam_id)
        except Exception as e:
            logger.error(f"Kamera-Stream konnte nicht geöffnet werden: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Kamera-Stream-Fehler: {e}"
            return

        # Model-Layer-ID bestimmen (im einfachsten Fall entspricht sie direkt model_layer_id)
        self.live_active_layer_id = model_layer_id

        # VizPreset aus dem Favoriten-Preset bauen
        preset_dict = favorite.get("preset") or {}
        try:
            viz_preset = VizPreset(
                id=preset_dict.get("id", f"fav_{favorite_name}"),
                layer_id=preset_dict.get("model_layer_id", model_layer_id),
                channels=preset_dict.get("channels", "topk"),
                k=preset_dict.get("k"),
                blend_mode=preset_dict.get("blend_mode", "mean"),
                overlay=preset_dict.get("overlay", False),
                alpha=preset_dict.get("alpha", 0.5),
                cmap=preset_dict.get("cmap", "viridis"),
            )
        except Exception as e:
            logger.error(f"Fehler beim Erzeugen des VizPreset aus Favorite: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Fehler im Preset des Favoriten: {e}"
            return

        self.live_active_favorite = favorite

        if self.vis_status_label is not None:
            self.vis_status_label.text = f"Live-Modus aktiv für Favorit: {favorite_name}"

        # Live-Timer starten
        self.live_clock_event = Clock.schedule_interval(
            lambda dt: self.update_live_frame(dt, viz_preset),
            LIVE_UPDATE_INTERVAL,
        )

    def on_favorite_remove_ui(self, model_layer_id: str, favorite_name: str) -> None:
        """Event-Handler für das Entfernen eines Favoriten aus der UI (Session-only)."""
        removed = self.session_removed_favorites.setdefault(model_layer_id, set())
        removed.add(favorite_name)
        logger.info(f"Favorite (UI-only) entfernt: model_layer_id={model_layer_id}, name={favorite_name}")

        # UI aktualisieren
        if self.active_page_id == model_layer_id:
            self._render_model_layer_page(model_layer_id)

    # ----------------------------------------------------
    # Live-Logik
    # ----------------------------------------------------

    def stop_live(self) -> None:
        """Stoppt den laufenden Live-Modus (falls aktiv)."""
        if self.live_clock_event is not None:
            try:
                self.live_clock_event.cancel()
            except Exception:
                pass
            self.live_clock_event = None

        # Kamera-Stream schließen
        if self.camera_stream is not None:
            self.camera_stream.release()
            self.camera_stream = None

        self.live_active_favorite = None
        self.live_active_layer_id = None

        if self.vis_status_label is not None:
            self.vis_status_label.text = "Live-Modus gestoppt"

    def update_live_frame(self, dt: float, viz_preset: VizPreset) -> None:
        """Holt einen Snapshot, führt Inferenz und Visualisierung aus und aktualisiert das Kivy-Image."""
        if self.camera_stream is None or self.model_engine is None or self.viz_engine is None:
            return

        # 1. Frame aus offenem Stream holen
        img, err = self.camera_stream.read()
        if img is None:
            logger.error(f"Kamera-Fehler im Live-Modus (Stream): {err}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Kamera-Fehler: {err}"
            self.stop_live()
            return

        # 2. Inferenz
        try:
            acts = self.model_engine.run_inference(img)
        except Exception as e:
            logger.error(f"Fehler bei Modell-Inferenz im Live-Modus: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Fehler bei Modell-Inferenz: {e}"
            self.stop_live()
            return

        layer_id = self.live_active_layer_id
        if layer_id is None or layer_id not in acts:
            logger.error(f"Layer nicht gefunden in Aktivierungen: {layer_id}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Layer nicht gefunden: {layer_id}"
            self.stop_live()
            return

        activation = acts[layer_id]

        # 3. Visualisierung
        try:
            vis_img = self.viz_engine.visualize(
                activation,
                viz_preset,
                original=img if viz_preset.overlay else None,
            )
        except Exception as e:
            logger.error(f"Fehler bei Visualisierung im Live-Modus: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.text = f"Fehler bei Visualisierung: {e}"
            self.stop_live()
            return

        # 4. Kivy-Texture aktualisieren
        self._update_kivy_texture_from_numpy(vis_img)

    def _update_kivy_texture_from_numpy(self, img: np.ndarray) -> None:
        """Aktualisiert die Texture von `self.vis_image` aus einem RGB-NumPy-Array."""
        if self.vis_image is None:
            return

        if not isinstance(img, np.ndarray):
            logger.error("Visualisierungsbild ist kein NumPy-Array")
            return

        if img.ndim != 3 or img.shape[2] != 3:
            logger.error(f"Unerwartete Bildform für Kivy-Texture: shape={img.shape}")
            return

        h, w, _ = img.shape
        if not self.vis_image.texture or self.vis_image.texture.size != (w, h):
            # Neue Texture mit korrekter Größe erzeugen
            self.vis_image.texture = Texture.create(size=(w, h))

        # Kivy erwartet Rohbytes im RGB-Format
        self.vis_image.texture.blit_buffer(
            img.tobytes(),
            colorfmt="rgb",
            bufferfmt="ubyte",
        )
        self.vis_image.canvas.ask_update()

    # ----------------------------------------------------
    # Alte API (kompatibel halten)
    # ----------------------------------------------------

    def _on_layer_switch(self, layer):
        """Alte API – mapped UI-Layer (mit id) auf den korrespondierenden Modell-Layer.

        Erwartet, dass Layer-IDs bereits direkt model_layer_id entsprechen oder
        im Preset/Mapping auflösbar sind. Für diese Iteration nutzen wir
        direkt layer.id als page_id.
        """
        if hasattr(layer, "id"):
            self.switch_to_page(getattr(layer, "id"))


class CNNExhibitKivyApp(App):
    def build(self):
        return ExhibitRoot()


if __name__ == "__main__":
    CNNExhibitKivyApp().run()
