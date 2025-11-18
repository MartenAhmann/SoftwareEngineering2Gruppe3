## 1. Abhängigkeiten

Mit `pip` zu installierende Pakete (z. B. in einem venv):
streamlit
opencv-python
numpy
pillow
torch
torchvision
kivy

## 2. Grundidee: 3‑Layer‑Architektur

Die Anwendung ist in drei Schichten organisiert:

1. **Core + Config (Storage-Schicht)**
   - Verzeichnis: `core/`, `config/`
   - Enthält:
     - Modell-Engine (`ModelEngine`) für ResNet‑Inference.
     - Visualisierungs-Engine (`VizEngine`) für Featuremaps.
     - Zentrale Konfiguration (`exhibit_config.json`) und Datamodelle (`config/models.py`).
   - Dient als gemeinsame „Storage“-Schicht für beide Views.

2. **Admin-View (Streamlit)**
   - Verzeichnis: `ui_admin_streamlit/`
   - Start: `streamlit run ui_admin_streamlit/app.py`
   - Zweck:
     - Bearbeitung der Ausstellungskonfiguration (`content_view`).
     - Konfiguration und Testen der Feature-Visualisierung (`feature_view`).
     - Schreiben von Änderungen in `config/exhibit_config.json`.

3. **Kino-View (Kivy)**
   - Verzeichnis: `ui_kino_kivy/`
   - Start: `python ui_kino_kivy/app.py`
   - Zweck:
     - Präsentationsoberfläche für den Ausstellungsbetrieb („Kinomodus“).
     - Liest dieselbe Konfiguration aus `config/exhibit_config.json`.
     - Nutzt dieselben Modelle/Viz-Einstellungen wie der Admin-View.

Beide Views greifen lesend/schreibend auf dieselbe Config-Datei zu und teilen sich Modell- und Visualisierungslogik.

## 3. Geplante Erweiterungen

### Content-View

- Für jeden Layer-Bereich sollen Favoriten ausgewählt und verwaltet werden können.
- Möglichkeit schaffen, Texte für verschiedene Layer umfassender zu definieren:
  - Button-Label
  - Titelzeilen-Label
  - Beschreibungstext (ausbauen, ggf. mehrsprachig / strukturierter)

### Layout-View

- Aufbau einer eigenen Layout-Seite:
  - Planung eines Grids / Layouts für die Kivy-Anwendung.
  - Konfiguration von Positionen, Größen und Anordnung der Visualisierungselemente.

### Feature-View

- Verbesserung der Konfigurationsmöglichkeiten:
  - Klarere Trennung zwischen Einzel-Channel-Ansicht und zusammengelegten Channels.
  - Mehr Optionen für Blend-Modi und Colormaps.
  - Robuste Speicherung in `exhibit_config.json`.
  - Saubere Behandlung zusätzlicher Metadaten (z. B. `metadata.favorites`).
- Optimierung der Liste der überlagerten Channels:
  - Sicherstellen, dass Channels intern eindeutig und konsistent verwaltet werden.
  - Besseres UI-Verhalten beim Hinzufügen/Entfernen und bei Favoritenwechsel.
