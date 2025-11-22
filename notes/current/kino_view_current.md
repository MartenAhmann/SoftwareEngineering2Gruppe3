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
    - Wichtige Attribute (neuer Stand):
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
      - `_build_middle_area`: Baut die zweigeteilte Mittelspalte:
        - Links: `vis_image` (Livebild) + `vis_status_label`.
        - Rechts: Subtitle, Beschreibung, Favoritenliste.
      - `_render_favorites(model_layer_id)`: Rendert pro Modell-Layer die Favoriten als Buttons.
      - `on_favorite_select(model_layer_id, favorite_name, favorite)`: Startet den Live-Modus für den gewählten Favoriten.
      - `on_favorite_remove_ui(...)`: Entfernt Favoriten aus der Sicht (Session-only) und rendert neu.
      - `switch_to_page(page_id)`: Wechselt zwischen „global“ und Modell-Layer-Seiten und stoppt dabei ggf. den Live-Modus.
      - `stop_live()`: Stoppt den laufenden Live-Modus und setzt den State zurück.
      - `update_live_frame(dt, viz_preset)`: Holt Kamera-Snapshot, führt Inferenz durch, visualisiert und aktualisiert `vis_image`.
      - `_update_kivy_texture_from_numpy(img)`: Hilfsfunktion, die ein RGB-Array in eine Kivy-Texture schreibt.

## 3. Datenfluss „Favorit auswählen → Livebild“

1. Benutzer:in wählt im Kino-View einen Favoriten-Button für einen bestimmten Modell-Layer.
2. `on_favorite_select(model_layer_id, favorite_name, favorite)` wird aufgerufen:
   - Stoppt ggf. einen vorher laufenden Live-Modus (`stop_live`).
   - Ruft `camera_service.detect_cameras(max_tested=5)` auf und wählt die erste gefundene Kamera-ID.
   - Speichert `self.live_cam_id` und `self.live_active_layer_id`.
   - Baut aus `favorite["preset"]` ein `VizPreset`-Objekt (Konvertierung aus dem Favoriten-Preset).
   - Setzt `self.live_active_favorite` und aktualisiert `vis_status_label`.
   - Plant `update_live_frame` per `Clock.schedule_interval` im festen Intervall (`LIVE_UPDATE_INTERVAL`).
3. `update_live_frame(dt, viz_preset)` wird im Intervall aufgerufen:
   - Holt Snapshot: `img, err = camera_service.take_snapshot(self.live_cam_id)`.
     - Bei Fehler (`img is None`):
       - Loggt den Fehler.
       - Setzt `vis_status_label` auf eine verständliche Meldung („Kamera-Fehler: …“).
       - Stoppt den Live-Modus via `stop_live`.
   - Führt Inferenz aus: `acts = self.model_engine.run_inference(img)`.
     - Erwartet, dass `self.live_active_layer_id` als Key in `acts` vorhanden ist.
     - Falls nicht vorhanden: Fehler-Log + Status-Label + Stop des Live-Modus.
   - Visualisiert Aktivierung: `vis_img = self.viz_engine.visualize(activation, viz_preset, original=img if viz_preset.overlay else None)`.
     - Bei Exception: Fehler-Log, Status-Label, Stop des Live-Modus.
   - Übergibt `vis_img` an `_update_kivy_texture_from_numpy`, das die Kivy-Texture aktualisiert.
4. `_update_kivy_texture_from_numpy(img)`:
   - Erwartet ein `np.ndarray` der Form (H, W, 3), `dtype=uint8`.
   - Erzeugt (oder erneuert) eine `Texture` mit passender Größe.
   - Schreibt die Bytes mit `blit_buffer(..., colorfmt="rgb", bufferfmt="ubyte")`.
   - Ruft `canvas.ask_update()`, sodass das Bild sichtbar wird.

5. `stop_live()`:
   - Bricht das geplante Clock-Event ab, falls vorhanden.
   - Setzt `live_active_favorite` und `live_active_layer_id` zurück.
   - Aktualisiert `vis_status_label` auf „Live-Modus gestoppt“.

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
