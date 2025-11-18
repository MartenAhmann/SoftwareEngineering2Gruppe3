# ui_kino_kivy/app.py
import sys
from pathlib import Path

# --- Quickfix für Imports ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

from config.service import load_config


Window.fullscreen = False  # Für den Prototyp noch nicht erzwingen


class ExhibitRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.cfg = load_config()
        self.active_layer = self._get_first_layer()

        self._build_titlebar()
        self._build_middle_area()
        self._build_buttonbar()

    # ----------------------------------------------------
    # Hilfsfunktionen
    # ----------------------------------------------------

    def _get_first_layer(self):
        layers = sorted(self.cfg.ui.layers, key=lambda x: x.order)
        return layers[0] if layers else None

    # ----------------------------------------------------
    # UI-Bau
    # ----------------------------------------------------

    def _build_titlebar(self):
        titlebar = Label(
            text=self.cfg.ui.title,
            size_hint_y=0.10,
            halign="center",
            valign="middle"
        )
        titlebar.bind(size=lambda *x: setattr(titlebar, "text_size", titlebar.size))
        self.add_widget(titlebar)

    def _build_middle_area(self):
        middle = BoxLayout(orientation="horizontal", size_hint_y=0.75)

        # Visualisierungs-Platzhalter (links)
        self.vis_label = Label(
            text="[Visualisierung folgt]",
            halign="center",
            valign="middle"
        )
        self.vis_label.bind(size=lambda *x: setattr(self.vis_label, "text_size", self.vis_label.size))

        # Beschreibungstext (rechts)
        desc_text = self.active_layer.description if self.active_layer else ""
        self.desc_label = Label(
            text=desc_text,
            halign="left",
            valign="top"
        )
        self.desc_label.bind(size=lambda *x: setattr(self.desc_label, "text_size", self.desc_label.size))

        middle.add_widget(self.vis_label)
        middle.add_widget(self.desc_label)
        self.add_widget(middle)

    def _build_buttonbar(self):
        bottom = BoxLayout(orientation="horizontal", size_hint_y=0.15)

        layers = sorted(self.cfg.ui.layers, key=lambda x: x.order)
        for layer in layers:
            btn = Button(
                text=layer.button_label,
                on_press=lambda instance, lyr=layer: self._on_layer_switch(lyr)
            )
            bottom.add_widget(btn)

        self.add_widget(bottom)

    # ----------------------------------------------------
    # Event-Handler
    # ----------------------------------------------------

    def _on_layer_switch(self, layer):
        """Wechsel des aktiven Layers (noch ohne Visualisierung)."""
        self.active_layer = layer

        # UI aktualisieren
        self.vis_label.text = f"[Layer gewechselt → {layer.id}]"
        self.desc_label.text = layer.description


class CNNExhibitKivyApp(App):
    def build(self):
        return ExhibitRoot()

if __name__ == "__main__":
    CNNExhibitKivyApp().run()
