# ui_kino_pyqt/app.py
import sys
import logging
from pathlib import Path
from typing import Dict, Set, Optional

import numpy as np

# --- Quickfix für Imports (wie in ui_kino_kivy/app.py) ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.service import (
    load_config,
    get_model_layer_content,
    get_selected_kivy_favorites,
)
from config.models import ModelConfig, ModelLayerContent, VizPreset
from core.model_engine import ModelEngine
    # ModelEngine.run_inference(np_image) -> dict[layer_id, activation]
from core.viz_engine import VizEngine
from core import camera_service

from PyQt5 import QtWidgets, QtGui, QtCore  # bei Bedarf auf PyQt6 anpassen

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LIVE_UPDATE_INTERVAL_SEC = 1 / 30  # ~30 FPS
LIVE_UPDATE_INTERVAL_MS = int(LIVE_UPDATE_INTERVAL_SEC * 1000)


class ExhibitWindow(QtWidgets.QWidget):
    """
    PyQt-Variante des Kino-Views:
    - Top: Titelzeile
    - Mitte: links Visualisierung + Status, rechts Subtitle/Description/Favoriten
    - Unten: Buttonleiste (Global + pro model_layer_id)
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        # Session-only State (Favoriten entfernt)
        self.session_removed_favorites: Dict[str, Set[str]] = {}
        self.active_page_id: Optional[str] = None   # "global" oder model_layer_id

        # Live-/Model-/Viz-State
        self.model_engine: Optional[ModelEngine] = None
        self.viz_engine: Optional[VizEngine] = None
        self.live_cam_id: Optional[int] = None
        self.live_active_favorite: Optional[dict] = None
        self.live_active_layer_id: Optional[str] = None
        self.current_viz_preset: Optional[VizPreset] = None

        self.camera_stream: Optional[camera_service.CameraStream] = None

        # UI-Widgets, werden später gebaut
        self.title_label: Optional[QtWidgets.QLabel] = None
        self.image_label: Optional[QtWidgets.QLabel] = None
        self.vis_status_label: Optional[QtWidgets.QLabel] = None
        self.subtitle_label: Optional[QtWidgets.QLabel] = None
        self.desc_label: Optional[QtWidgets.QLabel] = None
        self.fav_container: Optional[QtWidgets.QWidget] = None
        self.fav_layout: Optional[QtWidgets.QVBoxLayout] = None

        self.model_layer_ids: list[str] = []

        # Hauptlayout (damit _show_error_ui immer etwas hat, worin es rendern kann)
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Live-Timer (ersetzt Kivy Clock.schedule_interval)
        self.live_timer = QtCore.QTimer(self)
        self.live_timer.timeout.connect(self.update_live_frame)

        # Config laden
        try:
            self.cfg = load_config()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Config: {e}")
            self._show_error_ui(f"Fehler beim Laden der Konfiguration:\n{e}")
            return

        # Modell-Layer-Liste bestimmen (analog zur Feature-View)
        try:
            self.model_layer_ids = self._get_model_layer_ids(self.cfg.model)
        except Exception as e:
            logger.error(f"Fehler beim Bestimmen der Modell-Layer: {e}")
            self._show_error_ui(f"Fehler beim Bestimmen der Modell-Layer:\n{e}")
            return

        if not self.model_layer_ids:
            logger.error("Keine Modell-Layer konfiguriert")
            self._show_error_ui(
                "Keine Modell-Layer konfiguriert. Bitte Admin-View prüfen."
            )
            return

        # Model- und Viz-Engine initialisieren
        try:
            self.model_engine = ModelEngine(self.cfg.model)
            self.viz_engine = VizEngine()
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren von Model/VizEngine: {e}")
            self._show_error_ui(
                f"Fehler beim Initialisieren der Modell-/Visualisierungs-Engine:\n{e}"
            )
            return

        # UI aufbauen
        try:
            self._build_titlebar()
            self._build_middle_area()
            self._build_buttonbar()
            # Start auf Globalseite
            self.switch_to_page("global")
        except Exception as e:
            logger.error(f"Fehler beim Aufbau der UI: {e}")
            self._show_error_ui(f"Fehler beim Aufbau der Oberfläche:\n{e}")

    # ----------------------------------------------------
    # Hilfsfunktionen
    # ----------------------------------------------------

    def _show_error_ui(self, message: str) -> None:
        """Zeigt eine Fehler-UI an, wenn die normale UI nicht aufgebaut werden kann."""
        # Layout leeren
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        label = QtWidgets.QLabel(f"FEHLER\n\n{message}", self)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: red; font-weight: bold;")
        self.main_layout.addWidget(label)

    def _get_model_layer_ids(self, cfg_model: ModelConfig) -> list[str]:
        """Bestimmt aktive Modell-Layer analog zur Feature-View über ModelEngine."""
        engine = ModelEngine(cfg_model)
        # ModelEngine.get_active_layers() gibt Liste von Layer-IDs zurück
        return engine.get_active_layers()

    # ----------------------------------------------------
    # UI-Bau
    # ----------------------------------------------------

    def _build_titlebar(self) -> None:
        gt = self.cfg.ui.global_texts
        title_text = (
            gt.global_page_title
            if gt is not None and gt.global_page_title
            else self.cfg.ui.title
        )

        self.title_label = QtWidgets.QLabel(title_text, self)
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setWordWrap(True)

        self.main_layout.addWidget(self.title_label)

    def _build_middle_area(self) -> None:
        middle = QtWidgets.QWidget(self)
        middle_layout = QtWidgets.QHBoxLayout(middle)

        # Linke Seite: Visualisierung + Statuslabel
        left = QtWidgets.QWidget(middle)
        left_layout = QtWidgets.QVBoxLayout(left)

        self.image_label = QtWidgets.QLabel(left)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        self.vis_status_label = QtWidgets.QLabel(
            "Wähle einen Favoriten, um Live zu starten.", left
        )
        self.vis_status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.vis_status_label.setWordWrap(True)

        left_layout.addWidget(self.image_label)
        left_layout.addWidget(self.vis_status_label)

        # Rechte Seite: Subtitle + Beschreibung + Favoriten
        right = QtWidgets.QWidget(middle)
        right_layout = QtWidgets.QVBoxLayout(right)

        self.subtitle_label = QtWidgets.QLabel("", right)
        self.subtitle_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.subtitle_label.setWordWrap(True)

        self.desc_label = QtWidgets.QLabel("", right)
        self.desc_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.desc_label.setWordWrap(True)

        self.fav_container = QtWidgets.QWidget(right)
        self.fav_layout = QtWidgets.QVBoxLayout(self.fav_container)
        self.fav_layout.setContentsMargins(0, 0, 0, 0)
        self.fav_layout.setSpacing(4)

        right_layout.addWidget(self.subtitle_label)
        right_layout.addWidget(self.desc_label)
        right_layout.addWidget(self.fav_container)

        middle_layout.addWidget(left, stretch=1)
        middle_layout.addWidget(right, stretch=1)

        self.main_layout.addWidget(middle, stretch=1)

    def _build_buttonbar(self) -> None:
        bottom = QtWidgets.QWidget(self)
        bottom_layout = QtWidgets.QHBoxLayout(bottom)

        # Global-Button
        gt = self.cfg.ui.global_texts
        global_label = (
            gt.home_button_label
            if gt is not None and gt.home_button_label
            else "Global"
        )

        global_btn = QtWidgets.QPushButton(global_label, bottom)
        global_btn.clicked.connect(lambda: self.switch_to_page("global"))
        bottom_layout.addWidget(global_btn)

        # Buttons für alle Modell-Layer
        for ml_id in self.model_layer_ids:
            btn = QtWidgets.QPushButton(ml_id, bottom)

            def make_handler(page_id: str):
                return lambda: self.switch_to_page(page_id)

            btn.clicked.connect(make_handler(ml_id))
            bottom_layout.addWidget(btn)

        self.main_layout.addWidget(bottom)

    # ----------------------------------------------------
    # Page- und Favoriten-Logik
    # ----------------------------------------------------

    def switch_to_page(self, page_id: str) -> None:
        """Wechselt zwischen Globalseite ('global') und Modell-Layer-Seiten."""
        # Beim Seitenwechsel laufenden Live-Modus stoppen
        if self.live_timer.isActive():
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
            self.vis_status_label.setText("Wähle einen Favoriten, um Live zu starten.")
        self.subtitle_label.setText("")
        self.desc_label.setText(
            "Willkommen in der Ausstellung. Wähle unten einen Layer, um Details zu sehen."
        )
        self._render_favorites(None)

    def _render_model_layer_page(self, model_layer_id: str) -> None:
        """Setzt UI-Inhalte für eine Modell-Layer-Seite inkl. Subtitle und Favoriten."""
        content: ModelLayerContent = get_model_layer_content(self.cfg, model_layer_id)
        if self.vis_status_label is not None:
            self.vis_status_label.setText(
                "Wähle einen Favoriten, um Live zu starten."
            )
        self.subtitle_label.setText(content.subtitle or "")
        self.desc_label.setText(content.description)
        self._render_favorites(model_layer_id)

    def _render_favorites(self, model_layer_id: Optional[str]) -> None:
        """Rendert den Favoriten-Bereich für die gegebene Modell-Layer-Seite.
        Bei None: leert den Bereich.
        """
        if self.fav_layout is None:
            return

        # Layout leeren
        while self.fav_layout.count():
            item = self.fav_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if model_layer_id is None:
            return

        favorites = get_selected_kivy_favorites(self.cfg, model_layer_id)

        # Session-only entfernte Favoriten herausfiltern
        removed = self.session_removed_favorites.get(model_layer_id, set())
        visible_favorites = [f for f in favorites if f.get("name") not in removed]

        if not visible_favorites:
            no_label = QtWidgets.QLabel("Keine Favoriten hinterlegt", self.fav_container)
            no_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            self.fav_layout.addWidget(no_label)
            return

        for fav in visible_favorites:
            name = fav.get("name", "(ohne Namen)")

            row_widget = QtWidgets.QWidget(self.fav_container)
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            select_btn = QtWidgets.QPushButton(name, row_widget)
            remove_btn = QtWidgets.QPushButton("X", row_widget)
            remove_btn.setFixedWidth(40)

            # Handler mit gebundenen Parametern
            select_btn.clicked.connect(
                lambda _=False, ml_id=model_layer_id, fav_name=name, fav_dict=fav:
                    self.on_favorite_select(ml_id, fav_name, fav_dict)
            )
            remove_btn.clicked.connect(
                lambda _=False, ml_id=model_layer_id, fav_name=name:
                    self.on_favorite_remove_ui(ml_id, fav_name)
            )

            row_layout.addWidget(select_btn, stretch=1)
            row_layout.addWidget(remove_btn, stretch=0)
            self.fav_layout.addWidget(row_widget)

    def on_favorite_select(
        self, model_layer_id: str, favorite_name: str, favorite: dict
    ) -> None:
        """Event-Handler für die Auswahl eines Favoriten: startet Live-Modus für diesen Favoriten."""
        logger.info(
            "Favorite ausgewählt: model_layer_id=%s, name=%s, preset=%s",
            model_layer_id,
            favorite_name,
            favorite.get("preset"),
        )

        # Falls bereits ein Live-Modus läuft, zuerst stoppen
        if self.live_timer.isActive():
            self.stop_live()

        # Kamera-ID bestimmen (zunächst 0 oder erste gefundene)
        cams = camera_service.detect_cameras(max_tested=5)
        if not cams:
            if self.vis_status_label is not None:
                self.vis_status_label.setText("Keine Kamera gefunden.")
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
                self.vis_status_label.setText(f"Kamera-Stream-Fehler: {e}")
            return

        # Model-Layer-ID bestimmen (im einfachsten Fall entspricht sie direkt model_layer_id)
        self.live_active_layer_id = model_layer_id

        # VizPreset aus dem Favoriten-Preset bauen
        preset_dict = favorite.get("preset") or {}
        try:
            self.current_viz_preset = VizPreset(
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
                self.vis_status_label.setText(
                    f"Fehler im Preset des Favoriten: {e}"
                )
            return

        self.live_active_favorite = favorite

        if self.vis_status_label is not None:
            self.vis_status_label.setText(
                f"Live-Modus aktiv für Favorit: {favorite_name}"
            )

        # Live-Timer starten
        self.live_timer.start(LIVE_UPDATE_INTERVAL_MS)

    def on_favorite_remove_ui(self, model_layer_id: str, favorite_name: str) -> None:
        """Event-Handler für das Entfernen eines Favoriten aus der UI (Session-only)."""
        removed = self.session_removed_favorites.setdefault(model_layer_id, set())
        removed.add(favorite_name)
        logger.info(
            "Favorite (UI-only) entfernt: model_layer_id=%s, name=%s",
            model_layer_id,
            favorite_name,
        )

        # UI aktualisieren
        if self.active_page_id == model_layer_id:
            self._render_model_layer_page(model_layer_id)

    # ----------------------------------------------------
    # Live-Logik
    # ----------------------------------------------------

    def stop_live(self) -> None:
        """Stoppt den laufenden Live-Modus (falls aktiv)."""
        if self.live_timer.isActive():
            self.live_timer.stop()

        # Kamera-Stream schließen
        if self.camera_stream is not None:
            self.camera_stream.release()
            self.camera_stream = None

        self.live_active_favorite = None
        self.live_active_layer_id = None
        self.current_viz_preset = None

        if self.vis_status_label is not None:
            self.vis_status_label.setText("Live-Modus gestoppt")

    def update_live_frame(self) -> None:
        """Holt einen Snapshot, führt Inferenz und Visualisierung aus und aktualisiert das PyQt-Image."""
        if (
            self.camera_stream is None
            or self.model_engine is None
            or self.viz_engine is None
            or self.current_viz_preset is None
        ):
            return

        # 1. Frame aus offenem Stream holen
        img, err = self.camera_stream.read()
        if img is None:
            logger.error(f"Kamera-Fehler im Live-Modus (Stream): {err}")
            if self.vis_status_label is not None:
                self.vis_status_label.setText(f"Kamera-Fehler: {err}")
            self.stop_live()
            return

        # 2. Inferenz
        try:
            acts = self.model_engine.run_inference(img)
        except Exception as e:
            logger.error(f"Fehler bei Modell-Inferenz im Live-Modus: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.setText(
                    f"Fehler bei Modell-Inferenz: {e}"
                )
            self.stop_live()
            return

        layer_id = self.live_active_layer_id
        if layer_id is None or layer_id not in acts:
            logger.error(f"Layer-ID nicht in Aktivierungen: {layer_id}")
            if self.vis_status_label is not None:
                self.vis_status_label.setText(f"Layer nicht gefunden: {layer_id}")
            self.stop_live()
            return

        activation = acts[layer_id]

        # 3. Visualisierung
        try:
            vis_img = self.viz_engine.visualize(
                activation,
                self.current_viz_preset,
                original=img if self.current_viz_preset.overlay else None,
            )
        except Exception as e:
            logger.error(f"Fehler bei Visualisierung im Live-Modus: {e}")
            if self.vis_status_label is not None:
                self.vis_status_label.setText(
                    f"Fehler bei Visualisierung: {e}"
                )
            self.stop_live()
            return

        # 4. PyQt-Image aktualisieren
        self._update_qimage_from_numpy(vis_img)

    def _update_qimage_from_numpy(self, img: np.ndarray) -> None:
        """Aktualisiert die Pixmap von `self.image_label` aus einem RGB-NumPy-Array."""
        if self.image_label is None:
            return

        if not isinstance(img, np.ndarray):
            logger.error("Visualisierungsbild ist kein NumPy-Array")
            return

        if img.ndim != 3 or img.shape[2] != 3:
            logger.error(f"Unerwartete Bildform: shape={img.shape}")
            return

        h, w, _ = img.shape
        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)

        # Qt erwartet Daten in RGB888
        bytes_per_line = 3 * w
        qimg = QtGui.QImage(
            img.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
        )

        pixmap = QtGui.QPixmap.fromImage(qimg)

        # An Widgetgröße angepasst mit Aspect-Ratio
        target_size = self.image_label.size()
        if target_size.width() > 0 and target_size.height() > 0:
            pixmap = pixmap.scaled(
                target_size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

        self.image_label.setPixmap(pixmap)

    # ----------------------------------------------------
    # Alte API (kompatibel halten)
    # ----------------------------------------------------

    def _on_layer_switch(self, layer) -> None:
        """Alte API – mapped UI-Layer (mit id) auf den korrespondierenden Modell-Layer."""
        if hasattr(layer, "id"):
            self.switch_to_page(getattr(layer, "id"))

    # ----------------------------------------------------
    # Qt-Ereignisse
    # ----------------------------------------------------

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        """Stellt sicher, dass Kamera-Stream und Timer gestoppt werden."""
        self.stop_live()
        super().closeEvent(event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = ExhibitWindow()
    window.setWindowTitle("CNN Exhibit (PyQt)")
    window.showMaximized()  # oder showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
