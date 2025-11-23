# Kino-View – aktueller Stand

## 1. Rolle des Kino-Views im Gesamtsystem

- Kivy-Kino-View ist das **Publikums-Frontend** des Exponats:
  - Läuft auf dem Ausstellungsrechner im Vollbild (Kino-Modus).
  - Zeigt Besuchenden die aktuellen Visualisierungen und Erläuterungen.
- Implementiert als eigenständige Kivy-App im Package `ui_kino_kivy`.
- Nutzt die **gleiche Konfiguration** (`config/exhibit_config.json`) wie die Admin-Oberfläche (`ui_admin_streamlit`):
  - Teilt sich insbesondere die UI-Layer-Definitionen (`ui.layers` in `ExhibitConfig` / `LayerUIConfig`).
- Ergänzt das System um eine klare **Trennung von Admin-View (Streamlit)** und **Exponats-View (Kivy)**:
  - Admin-View: Konfiguration, Debug, Entwickler:innen.
  - Kino-View: stabile, kuratierte Präsentation für Besuchende.
- Aktueller Stand: Fokus auf Grundgerüst und Navigation zwischen UI-Layern,
  Visualisierung noch als Platzhalter.

## 2. Dateien und Verantwortlichkeiten im `ui_kino_kivy`-Package

### 2.1 Package-Übersicht

- Verzeichnis: `ui_kino_kivy/`
- Kernrollen:
  - Einstiegspunkt der Kivy-App.
  - Aufbau des Wurzel-Layouts.
  - Einbindung der Konfiguration (Titel, Layer, Beschreibungen, Buttonlabels).
- Wichtige Dateien:
  - `ui_kino_kivy/__init__.py`
  - `ui_kino_kivy/app.py` (derzeit zentrale Implementierung)

### 2.2 `ui_kino_kivy/__init__.py`

- Initialisiert das Package (aktuell vor allem für Importe/Packaging relevant).
- Potenzieller Ort, um später öffentliche API-Symbole zu exportieren, z.B.:
  - `CNNExhibitKivyApp`
  - Fabrik-Funktionen für den App-Start.

### 2.3 `ui_kino_kivy/app.py`

- **Hauptmodul der Kivy-Kino-App**.
- Verantwortlichkeiten (erweitert gegenüber der vorherigen Iteration):
  - Konfiguration laden (`load_config()` aus `config.service`).
  - UI-Layer und Modell-Layer in Einklang bringen (Buttons, Seitenwechsel).
  - Aufbau des Kivy-Layouts (Titelzeile, Mittelbereich, Buttonleiste).
  - Reaktion auf Layer-Wechsel durch Button-Klicks.
  - **Live-Visualisierung** von Modell-Aktivierungen auf Basis von Kamera-Snapshots:
    - Nutzt `core.camera_service` für alle Kamerafunktionen.
    - Nutzt `ModelEngine` für die Inferenz.
    - Nutzt `VizEngine` für die Visualisierung.

- Zentrale Klassen/Attribute:
  - `ExhibitRoot(BoxLayout)`
    - Wurzel-Widget der App.
    - Wichtige Attribute (aktueller Stand):
      - `self.cfg`: vollständige `ExhibitConfig`.
      - `self.model_layer_ids`: Liste der aktiven Modell-Layer-IDs.
      - `self.session_removed_favorites`: Session-Only-State für ausgeblendete Favoriten.
      - `self.model_engine: ModelEngine | None`: zentrale Modellinstanz für den Live-Modus.
      - `self.viz_engine: VizEngine | None`: zentrale Visualisierungsinstanz.
      - `self.live_cam_id: int | None`: aktuell verwendete Kamera-ID für den Live-Modus.
      - `self.live_active_favorite: dict | None`: aktuell laufender Favorit.
      - `self.live_active_layer_id: str | None`: zugehörige Modell-Layer-ID.
      - `self.live_clock_event`: Handle auf das von `Clock.schedule_interval` zurückgegebene Event.
      - `self.vis_image: Image`: Kivy-Image-Widget für das Livebild.
      - `self.vis_status_label: Label`: Status-/Fehlerlabel unterhalb des Livebildes.

    - Wichtige Methoden (Ist-Stand):
      - `__init__`: Lädt Config, initialisiert `ModelEngine` und `VizEngine`, baut UI und startet auf der Globalseite.
      - `_build_titlebar`: Baut die Titelzeile mit Text aus `cfg.ui.global_texts.global_page_title` (Fallback: `cfg.ui.title`).
      - `_build_middle_area`: Baut die zweigeteilte Mittelspalte (Livebild + rechte Text-/Favoritenspalte).
      - `_build_buttonbar`: Baut eine Buttonleiste mit einem Global-Button (Label aus `cfg.ui.global_texts.home_button_label`
        oder Fallback "Global") sowie Buttons für alle Modell-Layer.
      - `switch_to_page(page_id)`: Wechselt zwischen „global“ und Modell-Layer-Seiten, stoppt dabei ggf. den Live-Modus.
      - `_render_global_page()`: Setzt Texte für die Globalseite (Status, Begrüßungstext) und leert den Favoritenbereich.
      - `_render_model_layer_page(model_layer_id)`: Lädt Content für einen Modell-Layer (`get_model_layer_content`) und
        ruft `_render_favorites(model_layer_id)` auf.
      - `_render_favorites(model_layer_id)`: Rendert für einen Modell-Layer die ausgewählten Kino-Favoriten als Buttons,
        basierend auf `get_selected_kivy_favorites` und ggf. Session-Filter (`session_removed_favorites`).
      - `on_favorite_select(model_layer_id, favorite_name, favorite)`: Startet den Live-Modus für den gewählten Favoriten.
      - `on_favorite_remove_ui(...)`: Entfernt Favoriten aus der aktuellen Sicht (Session-only) und rendert neu.
      - `stop_live()`: Stoppt den laufenden Live-Modus und setzt den State zurück.
      - `update_live_frame(dt, viz_preset)`: Holt Kamera-Snapshot, führt Inferenz durch, visualisiert und aktualisiert `vis_image`.
      - `_update_kivy_texture_from_numpy(img)`: Hilfsfunktion, die ein RGB-Array in eine Kivy-Texture schreibt.

## 3. Datenfluss „Favorit auswählen → Livebild“ und Auswahlquelle

1. Die Auswahl, **welche** Favoriten pro `model_layer_id` im Kino-View sichtbar sind, wird im Admin-Content-Editor
   getroffen und in `cfg.ui.kivy_favorites[model_layer_id]` gespeichert.
2. Beim Wechsel auf eine Modell-Layer-Seite ruft der Kino-View `_render_model_layer_page(model_layer_id)` auf:
   - Lädt Text-Content über `get_model_layer_content(cfg, model_layer_id)`.
   - Ermittelt die für diese Seite aktiven Favoriten über `get_selected_kivy_favorites(cfg, model_layer_id)`, das
     `cfg.ui.kivy_favorites` interpretiert und auf die tatsächlich existierenden Favoriten (aus `metadata.favorites`)
     abbildet.
3. `_render_favorites(model_layer_id)` rendert für jeden aktiven Favoriten einen Button, optional mit einem „X“-Button,
   um Favoriten sessionweise auszublenden.
4. Benutzer:in wählt im Kino-View einen Favoriten-Button für einen bestimmten Modell-Layer.
5. `on_favorite_select(model_layer_id, favorite_name, favorite)` wird aufgerufen:
   - Stoppt ggf. einen vorher laufenden Live-Modus (`stop_live`).
   - Ruft `camera_service.detect_cameras(max_tested=5)` auf und wählt die erste gefundene Kamera-ID.
   - Speichert `self.live_cam_id` und `self.live_active_layer_id`.
   - Baut aus `favorite["preset"]` ein `VizPreset`-Objekt (Konvertierung aus dem Favoriten-Preset).
   - Setzt `self.live_active_favorite` und aktualisiert `vis_status_label`.
   - Plant `update_live_frame` per `Clock.schedule_interval` im festen Intervall (`LIVE_UPDATE_INTERVAL`).
6. `update_live_frame(dt, viz_preset)` wird im Intervall aufgerufen:
   - Holt Snapshot über den `CameraStream`.
   - Führt Inferenz über `ModelEngine` aus.
   - Visualisiert Aktivierungen mit `VizEngine` und aktualisiert das Kivy-Image.

**Wichtig:**
- Die Kino-View wählt **nicht selbst** aus, welche Favoriten aktiv sind. Diese Auswahl erfolgt ausschließlich
  in der Content-View und wird über `ui.kivy_favorites` an den Kino-View übergeben.
- Die Feature-View ist dafür zuständig, Favoriten (Name + Preset inkl. `preset.model_layer_id`) anzulegen,
  zu bearbeiten und zu löschen.

## 4. Abhängigkeiten und Architektur-Vorgaben

- Der Kino-View hängt nur von `config` und `core` ab:
  - `config.service` (Config laden, Modell-Layer-Content, Favoriten für Modell-Layer).
  - `config.models` (`ModelConfig`, `ModelLayerContent`, `VizPreset`).
  - `core.model_engine` (`ModelEngine`).
  - `core.viz_engine` (`VizEngine`).
  - `core.camera_service` (Kamera-Erkennung und Snapshot-Erzeugung).
- Es gibt **keine** direkten Importe von `ui_admin_streamlit` nach `ui_kino_kivy`.
- Der Kamera-Zugriff erfolgt ausschließlich über `core.camera_service`, nicht direkt per `cv2` im UI.

## 5. Geplante/weitere Schritte (aus Task "Kivy-Live-Funktionalität")

- Feinjustierung der UX (z.B. optionaler „Stop Live“-Button).
- Eventuelle Trennung von State und View in eigene Module (analog zur Feature-View).
- Weitere Tests für unterschiedliche Kamera-Setups und Fehlerfälle (keine Kamera, langsame Kamera, Model-Layer nicht verfügbar).
