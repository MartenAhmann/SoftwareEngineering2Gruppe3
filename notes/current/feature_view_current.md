# Feature-View – aktueller Stand

## 1. Rolle im Gesamtsystem

- Die Feature-View ist ein Streamlit-View im Admin-Panel (`ui_admin_streamlit`), die das Verhalten eines CNN (ResNet18) anhand eines Kamerasnapshots visualisiert.
- Einstieg erfolgt über `ui_admin_streamlit/app.py`:
  - `from ui_admin_streamlit.feature_view import render as render_feature`
  - Im Navigation-Dispatcher wird bei Auswahl "feature view" `render_feature()` aufgerufen.
- Die Feature-View verbindet drei Ebenen:
  - **Konfiguration** (`config`-Modul, v.a. `ExhibitConfig` und `VizPreset`),
  - **Inferenz & Aktivierungen** (`core.model_engine.ModelEngine`),
  - **Visualisierung** (`core.viz_engine.VizEngine`).

## 2. Dateien und Verantwortlichkeiten (Feature-View-Package)

Verzeichnis: `ui_admin_streamlit/feature_view`

### 2.1 `__init__.py`

- Kapselt das Package nach außen.
- Öffentliche API:
  - `render()` wird aus `.view` re-exportiert und in `__all__` eingetragen.
- Konsumenten (z.B. `app.py`) binden nur `feature_view.render`, ohne interne Dateien zu kennen → geringe Kopplung nach außen.

### 2.2 `view.py`

- **Haupt-UI der Feature-View** – alle Streamlit-Controls und der Ablauf der Snapshot-Visualisierung.
- Wichtige Importe:
  - Streamlit/Libs: `streamlit as st`, `cv2`, `numpy as np`.
  - Konfiguration: `config.models.VizPreset`, `config.service.load_config`, `load_raw_config_dict`, `save_raw_config_dict`.
  - Modell/Viz: `core.model_engine.ModelEngine`, `core.viz_engine.VizEngine` (nur Typverwendungen, Instanzen kommen aus `st.session_state`).
  - Feature-View-Submodule:
    - `.camera.detect_cameras`, `.camera.take_snapshot` → Kamerazugriff & Snapshot.
    - `.favorites.get_layer_favorites`, `.upsert_favorite`, `.delete_favorite` → persistente Favoriten.
    - `.state.init_state`, `.layer_state` → Session-State initialisieren und per-Layer-UI-State holen.

- Zentrale Funktion: `render() -> None`
  - Ruft `init_state()`, wodurch `ModelEngine`, `VizEngine` und Session-State-Struktur bereitgestellt werden.
  - Lädt konfigurative Daten:
    - `cfg = load_config()` → typisierte `ExhibitConfig` (Dataclasses).
    - `raw_cfg = load_raw_config_dict()` → rohes JSON-Dict, u.a. für Favoriten.
  - Wählt aktuell **den ersten UI-Layer** (`ui_layers[0]`) als Kontext:
    - `ui_layers = sorted(cfg.ui.layers, key=lambda x: x.order)`
    - `ui_layer = ui_layers[0]`, `layer_key = ui_layer.id`.
  - Holt / initialisiert pro-UI-Layer-UI-State: `st_data = layer_state(layer_key)` (Dict aus `LayerState`).

- UI-Struktur in `render()` (geplanter Ablauf nach Favoriten-Refactoring):

  1. **Top-Reihe: Favoriten auswählen, laden und löschen**

     - Links (`top_left`):
       - `get_layer_favorites(raw_cfg, ui_layer.id)` liefert nur valide Favoriten.
       - `st.selectbox("Favorit wählen", ["–"] + fav_names, key=f"{layer_key}_fav_select_snapshot")`:
         - Die Selectbox dient **nur** zur Auswahl eines Favoriten-Namens, löst aber **keine automatische Anwendung** aus.
       - Separater Button `"Favorit laden"` (`{layer_key}_apply_fav_snapshot`):
         - Setzt ein Session-Flag in `st.session_state.feature_favorite_load_flags[layer_key] = True`.
         - Dieses Flag triggert genau **einen** Lade-Vorgang im nachgelagerten Renderpfad.

     - Rechts (`top_right`):
       - Button "–" (`{layer_key}_delete_fav_snapshot`) löscht den aktuell ausgewählten Favoriten:
         - Lädt frische Roh-Config (`load_raw_config_dict()`),
         - `delete_favorite(raw_del, ui_layer.id, selected_fav_name)`,
         - `save_raw_config_dict(raw_del)`,
         - `st.rerun()`.

     - Einmalige Anwendung eines Favoriten:
       - Im Renderpfad wird geprüft, ob `feature_favorite_load_flags[layer_key]` `True` ist.
       - Nur dann wird das gewählte Preset (`f["preset"]`) in `st_data` übertragen und die zugehörigen `st.session_state`-Widget-Keys gesetzt:
         - Modus & Kanäle/K (`mode`, `channels`, `k`),
         - Darstellungsparameter (`blend_mode`, `cmap`, `overlay`, `alpha`),
         - Modell-Layer (`model_layer_id`),
         - Favoritenname (`fav_name`).
       - Zusätzlich wird `st_data["editing_favorite_name"] = f["name"]` gesetzt, um den Bearbeitungs-Kontext zu halten.
       - Nach der Anwendung wird das Flag `feature_favorite_load_flags[layer_key]` **immer** wieder auf `False` gesetzt.
       - Dadurch gibt es **keinen Autoload** mehr beim reinen Rendern; Presets werden nur noch Event-basiert angewendet.

  2. **Snapshot + Controls (zweispaltig)**

     - Linke Spalte (`left_col`):
       - Kameraerkennung und Snapshot-Aufnahme (**unverändert** zum vorherigen Stand):
         - `detect_cameras()`, `st.selectbox("Kamera", ...)`, `take_snapshot(cam_id)`,
         - Speicherung des Snapshots in `st.session_state.feature_snapshot`.

     - Rechte Spalte (`right_col`):
       - **Modell-Layer-Auswahl**, **Channel-Modus**, **Channels konfigurieren**, **Darstellungsparameter** wie zuvor beschrieben.
       - Channels-Logik:
         - Buttons "In Liste aufnehmen" und "×" manipulieren **nur** `st_data["channels"]` und rufen ggf. `st.rerun()`.
         - Durch das entfernte Autoload wird `st_data["channels"]` **nicht mehr implizit durch Favoriten überschrieben**, außer beim expliziten „Favorit laden“-Event.

  3. **Inferenz + Visualisierung**

     - Unverändert zur vorherigen Dokumentation:
       - Inferenz auf `st.session_state.feature_snapshot` via `model_engine.run_inference(snapshot)`.
       - Erstellung eines `VizPreset` für den Slider-Channel (oberes Bild) und eines zweiten Presets
         für die kombinierte Ansicht (unteres Bild), basierend auf `st_data`.

  4. **Favoriten speichern / aktualisieren (Bearbeitungsmodus)**

     - Unterer Bereich nach Divider:
       - Subheader „Favorit speichern/aktualisieren“.
       - Optionaler Hinweis:
         - Wenn `st_data["editing_favorite_name"]` gesetzt ist, zeigt die UI ein `st.info(...)` mit
           „Bearbeite Favorit: '<Name>'. Änderungen werden beim Speichern in diesen Favoriten übernommen.“
       - Textfeld `"Name des Favoriten"` (`{layer_key}_fav_name_snapshot`), schreibt in `st_data["fav_name"]`.
       - Button "Als Favorit speichern/aktualisieren" (`{layer_key}_save_fav_snapshot`):
         - Validiert Name (nicht leer).
         - Baut Preset-Dict via `_current_preset_dict()`:
           - `channels`: "topk" oder Liste aus `st_data["channels"]`.
           - `k`: nur bei Modus "Top-K" gesetzt.
           - `blend_mode`, `cmap`, `overlay`, `alpha`, `model_layer_id`.
         - Lädt Roh-Konfig: `raw = load_raw_config_dict()`.
         - Erzeugt Favorit:
           - `{"name": fav_name, "layer_id": ui_layer.id, "preset": _current_preset_dict()}`.
         - Persistiert mit `upsert_favorite(raw, ui_layer.id, fav)` und `save_raw_config_dict(raw)`.
         - Aktualisiert den Bearbeitungs-Kontext: `st_data["editing_favorite_name"] = fav_name.strip()`.
         - Zeigt `st.success("Favorit '<Name>' wurde gespeichert/aktualisiert.")`.
       - Rechts steht ein erklärender Hinweistext, dass zum Laden eines Favoriten nun die Kombination aus
         Selectbox **und** Button „Favorit laden“ genutzt werden muss.

### 2.3 `state.py`

- Verantwortlich für **State-Management der Feature-View** im Streamlit-Session-State.

- Zentrale Dataclass: `LayerState`
  - Felder mit Defaults (über `constants`):
    - `mode: str = MODE_SELECTED_CHANNELS` – Standard: "Ausgewählte Channels".
    - `channels: List[int] = []` – Liste explizit ausgewählter Channels.
    - `k: int = DEFAULT_TOP_K` – Anzahl Channels für "Top-K"-Modus.
    - `blend_mode: str = DEFAULT_BLEND_MODE` – Standard-Blend-Modus.
    - `colormap: str = DEFAULT_COLORMAP` – Standard-Colormap.
    - `overlay: bool = False` – Standard: Overlay aus.
    - `alpha: float = DEFAULT_ALPHA` – Transparenz für Overlay.
    - `model_layer_id: str = "conv1"` – initial gewählter Modell-Layer.
    - `last_channel: int = 0` – zuletzt im Slider ausgewählter Channel.
    - `fav_name: str = ""` – aktueller Favoritenname im Eingabefeld.
    - `editing_favorite_name: Optional[str] = None` – Name des Favoriten, der zuletzt explizit geladen oder gespeichert wurde.
      - Dient ausschließlich als **Bearbeitungs-Kontext** und löst **kein Autoload** aus.
  - Methoden:
    - `to_dict()` – konvertiert in ein reines Dict mit Keys (`mode`, `channels`, `k`, `blend_mode`, `cmap`, `overlay`, `alpha`, `model_layer_id`, `last_channel`, `fav_name`, `editing_favorite_name`).
    - `from_dict(d)` – baut `LayerState` wieder aus einem Dict (mit Defaults für fehlende Felder).

- Funktion `compute_snapshot_hash(image: np.ndarray) -> str`
  - MD5-Hash über `image.tobytes()`.
  - Dient als Cache-Key für Aktivierungen.

- Funktion `init_state() -> None`
  - Initialisiert alle Feature-View-relevanten Session-State-Einträge, falls nicht vorhanden:
    - `feature_model_engine`: `ModelEngine`-Instanz mit `ModelConfig(name="resnet18", weights="imagenet")` und aktiven Layern `"conv1"`–`"layer4"`.
    - `feature_viz_engine`: `VizEngine`-Instanz.
    - `feature_state`: Dict für UI-State je `ui-layer-id` → Dict aus `LayerState`.
    - `feature_snapshot`: aktueller Snapshot (`np.ndarray` oder `None`).
    - `feature_activation_cache`: Dict mit
      - `"snapshot_hash"`: MD5-Hash des letzten Snapshots oder `None`,
      - `"activations"`: gecachte Aktivierungen (`Dict[str, np.ndarray]` oder `None`).
    - **Neu:** `feature_favorite_load_flags`: Dict `layer_key -> bool`, das steuert,
      ob in diesem Render-Durchlauf ein Favorit für einen gegebenen Layer **einmalig** angewendet werden soll.

- Funktion `get_cached_activations(snapshot, model_engine) -> Dict[str, np.ndarray]`
  - Implementiert einen einfachen **Inferenz-Cache** basierend auf Bildinhalt:
    - Berechnet `snapshot_hash` via `compute_snapshot_hash`.
    - Vergleicht mit `st.session_state.feature_activation_cache["snapshot_hash"]`.
    - Bei Cache-Hit und vorhandenen `"activations"` wird das Dict direkt zurückgegeben.
    - Bei Cache-Miss wird `model_engine.run_inference(snapshot)` ausgeführt, Ergebnis und Hash im Cache gespeichert und zurückgegeben.

- Funktion `layer_state(layer_key: str) -> Dict[str, Any]`
  - Stellt sicher, dass es für einen `layer_key` (`ui_layer.id`) einen Eintrag in `feature_state` gibt.
  - Initialisiert bei Bedarf mit Defaults aus `LayerState().to_dict()`.
  - Gibt das zugehörige Dict zurück, welches in `view.render()` weiter mutiert wird.

- Funktion `get_layer_state_typed(layer_key: str) -> LayerState`
  - Hilfsfunktion, um typisiertes `LayerState`-Objekt aus dem Dict zu erhalten.

- Funktion `set_layer_state(layer_key: str, state: LayerState) -> None`
  - Schreibt ein `LayerState`-Objekt wieder zurück in `feature_state` (als Dict).

### 2.4 `favorites.py`

- Unverändert gegenüber der vorherigen Dokumentation:
  - Verwaltet **Favoriten (Presets)** auf Basis der JSON-Konfigurationsdatei `config/exhibit_config.json`.
  - Stellt `validate_preset`, `get_layer_favorites`, `upsert_favorite`, `delete_favorite` bereit.
  - Die Preset-Struktur (Felder `channels`, `k`, `blend_mode`, `cmap`, `overlay`, `alpha`, `model_layer_id` oder `layer_id`) bleibt unverändert.

### 2.5 `constants.py`, `camera.py`

- Keine funktionalen Änderungen im Rahmen des Favoriten-Refactorings.
- Siehe bestehenden Abschnitt in dieser Datei für Details.

## 3. Neuer UX-Flow für Favoriten (nach Aufgaben 4–10)

1. Nutzer:in wählt im Dropdown "Favorit wählen" einen Favoriten-Namen.
2. Nutzer:in klickt explizit auf den Button "Favorit laden":
   - Das zugehörige Preset wird **einmalig** in `st_data` und die relevanten Streamlit-Widget-States übertragen.
   - `editing_favorite_name` wird auf den geladenen Namen gesetzt.
3. Nutzer:in verändert beliebig die UI-Einstellungen (Blend-Mode, Colormap, Overlay, Alpha, Channels, Top-K, Modell-Layer).
4. Zum Speichern klickt Nutzer:in auf "Als Favorit speichern/aktualisieren":
   - Der aktuelle `st_data`-Zustand wird via `_current_preset_dict()` in ein Preset-Dict übertragen.
   - `upsert_favorite` schreibt dieses Preset (per Name) in die Config.
   - `editing_favorite_name` wird auf den gespeicherten Namen gesetzt (Bearbeitungsmodus bleibt aktiv).
5. Optional kann Nutzer:in später denselben oder einen anderen Favoriten erneut laden – wieder explizit über den Button.

**Wichtig:**
- Es gibt keinen impliziten Autoload eines Favoriten mehr basierend auf dem Selectbox-Wert allein.
- Änderungen an Channels (Hinzufügen/Entfernen) oder anderen UI-Controls bleiben stabil im aktuellen `st_data`,
  solange kein neues "Favorit laden"-Event ausgelöst wird.

## 6. Beziehung zu modell-layer-basiertem Content und Kino-View

- Die Feature-View bleibt die technische Analyse- und Debug-Ansicht für Modell-Layer und deren Aktivierungen.
- Die im Favoriten-Preset gespeicherte `model_layer_id` wird nun zusätzlich genutzt von:
  - `config.service.get_favorites_for_model_layer(...)` (lesende Sicht für Kino-View).
  - `ui_kino_kivy.app.ExhibitRoot` (Anzeige von bis zu drei Favoriten pro Modell-Layer-Seite).
- Der eigentliche Text-Content (Titel, Subtitle, Beschreibung) für die Modell-Layer-Seiten liegt **nicht** in der Feature-View, sondern in der gemeinsamen Config-Struktur `ui.model_layers[model_layer_id]` und wird über den Content-Editor gepflegt.
- Wichtig für Konsistenz:
  - Feature-View: wählt und speichert `model_layer_id` in Favoriten.
  - Content-Editor: pflegt Texte zu denselben `model_layer_id`s.
  - Kino-View: liest sowohl `model_layer_id` aus Favoriten als auch Content aus `ui.model_layers`.
  - Alle drei Sichten basieren auf derselben Modell-Layer-Liste aus `core.model_engine.ModelEngine.get_active_layers()`.
