# Content-View (Content-Editor) – aktueller Stand

## 1. Rolle im Gesamtsystem

- Die Content-View ist ein Streamlit-View im Admin-Panel (`ui_admin_streamlit`) und dient als **Content-Editor** für textuelle Inhalte des Exponats.
- Einstieg erfolgt über `ui_admin_streamlit/app.py`:
  - `from ui_admin_streamlit.content_view import render as render_content`
  - Im Navigation-Dispatcher wird bei Auswahl der entsprechenden Seite `render_content()` aufgerufen (konkreter Menüname je nach App-Implementierung).
- Die Content-View verbindet drei Schichten:
  - **Konfiguration** (`config`-Package): `ExhibitConfig`, `ExhibitUIConfig`, `ModelLayerContent`, `LayerUIConfig`.
  - **Core-Schicht** (`core.model_engine.ModelEngine`): wird genutzt, um eine konsistente Liste von Modell-Layer-IDs zu ermitteln.
  - **Admin-UI (Streamlit)**: Oberflächen zur Pflege von Titel, Untertiteln und Beschreibungstexten für globale Inhalte, Modell-Layer-Seiten und klassische UI-Layer.

Ziel:
- Alle in der Ausstellung angezeigten Texte zentral in `config/exhibit_config.json` pflegen, insbesondere:
  - globaler Ausstellungstitel,
  - pro Modell-Layer: Seitentitel, Kamera-Subtitle, Beschreibungstext,
  - optional pro UI-Layer: Button-Label, Titelzeile, Kamera-Subtitle, Kurzbeschreibung.

---

## 2. Dateien und Verantwortlichkeiten (Content-View)

Verzeichnis: `ui_admin_streamlit/`

- `ui_admin_streamlit/content_view.py`
  - Enthält die gesamte Logik und das Streamlit-UI für den Content-Editor.
  - Wird direkt von `app.py` importiert.

### 2.1 `render()` – Haupteinstieg der Content-View

Signatur: `render() -> None`

Verantwortlichkeiten:

- Lädt die aktuelle Konfiguration über `load_config()`.
- Stellt eine Unternavigation bereit, mit der zwischen verschiedenen Content-Bereichen gewechselt werden kann:
  - **Global** (Seite `PAGE_ID_GLOBAL`): globaler Ausstellungstitel (`cfg.ui.title`).
  - **Modell-Layer-Seiten**: eine Seite pro Modell-Layer-ID aus der `ModelEngine`.
  - **Klassische UI-Layer-Seiten**: optionale Bearbeitung der klassischen `LayerUIConfig`-Texte.
- Stellt Eingabefelder zur Bearbeitung von Textinhalten bereit und schreibt Änderungen in die im `config`-Modul definierte Config-Struktur zurück.
- Persistiert Änderungen beim Klick auf „Konfiguration speichern“ dauerhaft in `config/exhibit_config.json` über `save_config(cfg)`.

Ablauf (High-Level):

1. `cfg = load_config()` – Laden der typisierten `ExhibitConfig`.
2. Sicherstellen, dass mindestens ein UI-Layer existiert:
   - Falls `cfg.ui.layers` leer ist, wird ein Default-Layer `LayerUIConfig(...)` mit ID `"layer_1_default"` angelegt.
3. Ermitteln der Modell-Layer-IDs über `_get_model_layer_ids(cfg.model)`:
   - Diese Funktion nutzt intern eine temporäre `ModelEngine`-Instanz (siehe Abschnitt 2.2).
4. Aufbau einer Navigationsliste (`nav_options`) mit Einträgen:
   - `( "Global", PAGE_ID_GLOBAL )`.
   - Für jeden Modell-Layer `ml_id`: `( "Modell-Layer: {ml_id}", f"model::{ml_id}" )`.
   - Für jeden vorhandenen UI-Layer `layer`: `(layer.button_label or layer.id, layer.id)`.
5. Darstellung einer `st.radio`-Komponente „Seite wählen“, die einen der Einträge auswählt.
6. Rendering der gewählten Seite:
   - **Global-Seite**: Felder für Ausstellungstitel und globale UI-Texte (`ui.global_texts`).
   - **Modell-Layer-Seite**: Felder für `ModelLayerContent` (`title`, `subtitle`, `description`) und eine Checkbox-Auswahl der Kino-Favoriten.
   - **UI-Layer-Seite**: Felder für `LayerUIConfig` (`button_label`, `title_bar_label`, `subtitle`, `description`).
7. Speichern:
   - Button „Konfiguration speichern“ ruft `save_config(cfg)` auf.
   - Zeigt nach Erfolg `st.success("Gespeichert.")`.

---

## 3. Hilfsfunktionen in `content_view.py`

### 3.1 `_get_layer_by_id(cfg, layer_id: str) -> LayerUIConfig | None`

- Sucht in `cfg.ui.layers` nach einem `LayerUIConfig` mit passender `id`.
- Rückgabewerte:
  - Gefundener `LayerUIConfig` oder
  - `None`, falls kein Layer mit dieser ID existiert.
- Nutzung:
  - Dient der Zuordnung eines UI-Layer-Seiten-Eintrags aus der Navigation zu seinem Config-Objekt.
  - Wird in der UI-Layer-Seite des Editors verwendet, um Felder wie `button_label`, `title_bar_label`, `subtitle` und `description` zu bearbeiten.

### 3.2 `_get_model_layer_ids(cfg_model: ModelConfig) -> list[str]`

- Bestimmt die Liste der Modell-Layer-IDs, die als Content-Seiten angeboten werden sollen.
- Vorgehen:
  1. Erzeugt eine temporäre `ModelEngine`-Instanz mit dem übergebenen `ModelConfig`.
  2. Ruft `engine.get_active_layers()` auf und gibt diese Liste zurück.
- Motivation:
  - Die Content-View bleibt damit automatisch konsistent mit der Feature-View und der späteren Kino-View,
    da alle drei auf dem gleichen Mechanismus (`ModelEngine.get_active_layers()`) zur Bestimmung der Modell-Layer basieren.
- Besonderheiten:
  - Die `ModelEngine` wird hier **nur kurzzeitig** zur Ermittlung der Layerliste instanziiert;
    es gibt keinen dauerhaft gehaltenen Engine- oder Aktivierungszustand im Content-Editor.

---

## 4. Content-Seiten und Datenmodell

### 4.1 Globale Inhalte

- Seite mit ID `PAGE_ID_GLOBAL` (Konstante `PAGE_ID_GLOBAL = "global"`).
- UI:
  - `st.subheader("Globale Inhalte")`.
  - `st.text_input("Ausstellungstitel", value=cfg.ui.title)`.
  - Initialisiert bei Bedarf `cfg.ui.global_texts` mit sinnvollen Defaults (Titel der Ausstellung und `"Home"` als Button-Label).
  - Textfelder für die Felder von `GlobalUITexts`:
    - `Titel der Globalseite` (`cfg.ui.global_texts.global_page_title`):
      - Überschrift, die in der Kino-View in der Titelzeile verwendet wird.
    - `Label für Global/Home-Button` (`cfg.ui.global_texts.home_button_label`):
      - Text auf dem Global-/Home-Button in der Buttonleiste der Kino-View.
- Schreibweise in der Config:
  - `cfg.ui.title` wird direkt aktualisiert.
  - `cfg.ui.global_texts.*` werden direkt über das `GlobalUITexts`-Objekt verändert.
- Zweck:
  - Globaler Ausstellungstitel und globale UI-Texte, die von der Kino-View verwendet werden (Titelzeile, Global-Button).

### 4.2 Modell-Layer-Content (`ui.model_layers` / `ModelLayerContent`) und Kino-Favoriten-Auswahl

- Seiten-IDs im Format `model::{model_layer_id}` (z.B. `model::conv1`, `model::layer1`, `model::layer2`, …).
- Content-Struktur basiert auf der in `config.models` definierten Dataclass `ModelLayerContent`.
- Pro Modell-Layer-Seite:
  - `content: ModelLayerContent = get_model_layer_content(cfg, model_layer_id)`.
    - `get_model_layer_content` stammt aus `config.service` und stellt sicher, dass für jede `model_layer_id`
      ein vollständiges `ModelLayerContent`-Objekt existiert (ggf. mit Defaults).
- UI-Felder für Text-Content:
  - `Seitentitel` (`content.title`).
  - `Subtitle (Kamera-Ansicht)` (`content.subtitle`).
  - `Beschreibung (Erklärungstext)` (`content.description`).
- Zusätzlich: **Kino-Favoriten-Auswahl pro `model_layer_id`**
  - Unterhalb der Textfelder zeigt die Content-View eine Sektion „Kino-Favoriten-Auswahl für diesen Modell-Layer“.
  - Sie nutzt `list_all_favorites_for_model_layer(cfg, model_layer_id)`, um alle vorhandenen Favoriten anzuzeigen,
    deren Preset `model_layer_id` entspricht.
  - Für jeden Favoriten wird eine Checkbox gerendert:
    - Label z.B. `"Favorit im Kino anzeigen: {name}"`.
    - Der anfängliche Checkbox-Zustand ergibt sich aus `cfg.ui.kivy_favorites.get(model_layer_id, [])`.
  - Die aktuelle Auswahl (Liste der angehakten Favoritennamen) wird im Streamlit-Session-State zwischengespeichert,
    damit sie beim Klick auf „Konfiguration speichern“ ausgewertet werden kann.
- Speichern der Auswahl:
  - Beim Klick auf den globalen Button „Konfiguration speichern“ wird geprüft, ob eine Auswahl für den aktuell
    bearbeiteten `model_layer_id` im Session-State liegt.
  - Ist dies der Fall, wird die Anzahl der ausgewählten Favoriten gegen `MAX_FAVORITES_PER_MODEL_LAYER` geprüft:
    - Bei mehr als `MAX_FAVORITES_PER_MODEL_LAYER` wird ein Fehler angezeigt und das Speichern abgebrochen.
    - Ansonsten wird `set_selected_kivy_favorites(cfg, model_layer_id, names)` aufgerufen, das die Auswahl in
      `cfg.ui.kivy_favorites[model_layer_id]` schreibt.
  - Anschließend wird `save_config(cfg)` aufgerufen und ein Erfolgshinweis angezeigt.
- Beziehung zu anderen Komponenten:
  - **Feature-View**: definiert und verwaltet die eigentlichen Favoriten (Name + Preset) in `metadata.favorites`.
  - **Kino-View**: liest die Auswahl aus `ui.kivy_favorites` über `get_selected_kivy_favorites` und zeigt genau diese
    Favoriten pro `model_layer_id` an.

### 4.3 Klassische UI-Layer-Seiten (`LayerUIConfig`)

- Zusätzlich zu modell-layer-basiertem Content kann der Editor weiterhin klassische UI-Layer-Texte pflegen.
- Für jeden `LayerUIConfig` in `cfg.ui.layers` wird ein Navigationspunkt erzeugt:
  - Label: `layer.button_label` oder (Fallback) `layer.id`.
  - Seiten-ID: `layer.id`.
- In der Seitenlogik:
  - `layer = _get_layer_by_id(cfg, active_page_id)`.
  - Falls `layer` nicht gefunden wird:
    - Anzeige eines Fehlers: `st.error(f"Unbekannter Layer: {active_page_id}")`.
- UI-Felder pro Layer:
  - `Button-Label` (`layer.button_label`):
    - Text für den Button in der Kino-View-Buttonleiste.
  - `Titelzeilen-Label` (`layer.title_bar_label`):
    - Text in der Titelzeile der Kino-View, wenn der Layer aktiv ist.
  - `Subtitle (Kamera-Ansicht)` (`layer.subtitle`):
    - Kurzer Untertitel, der in einer Kameraansicht verwendet werden kann (`layer.subtitle or ""`).
  - `Beschreibung (rechte Spalte)` (`layer.description`):
    - Text für die rechte Spalte in der Kino-View (Erläuterungstext für den jeweiligen UI-Layer).
- Zweck:
  - Abwärtskompatibilität und parallele Pflege der ursprünglichen UI-Layer-Contentstruktur.
  - Hilft, ältere oder ergänzende UI-Layer-Beschreibungen weiterhin verfügbar zu halten.

---

## 5. Interaktionen mit `config` und `core`

### 5.1 Nutzung von `config.service` und `config.models`

- Im Content-Editor werden folgende Funktionen und Typen verwendet:
  - `load_config()`:
    - Lädt `ExhibitConfig` aus `config/exhibit_config.json`.
  - `save_config(cfg)`:
    - Serialisiert `ExhibitConfig` und schreibt sie zurück in die JSON-Datei (inkl. Backup/Locking gemäß `config.service`).
  - `get_model_layer_content(cfg, model_layer_id)`:
    - Liest oder initialisiert den `ModelLayerContent`-Eintrag für einen gegebenen Modell-Layer.
  - `LayerUIConfig`, `ModelConfig`, `ModelLayerContent`:
    - Dataclasses aus `config.models`, die die UI- und Contentstruktur typisieren.

- Datenfluss mit der Config-Schicht:
  1. Beim Betreten der Content-View wird `cfg = load_config()` aufgerufen.
  2. Benutzer:in bearbeitet Textfelder:
     - Direkt auf Feldern von `cfg.ui` (`title`, `model_layers[...]`, `layers[...]`).
  3. Beim Speichern wird `save_config(cfg)` aufgerufen, das intern die JSON-Datei aktualisiert.

### 5.2 Nutzung von `core.model_engine.ModelEngine`

- Der Content-Editor nutzt `ModelEngine` ausschließlich, um eine konsistente Liste von Modell-Layer-IDs zu erhalten:
  - `_get_model_layer_ids(cfg.model)` → `ModelEngine(cfg_model)` → `get_active_layers()`.
- Vorteile dieser Kopplung:
  - Alle Schichten (Feature-View, Content-View, Kino-View) arbeiten mit derselben Modell-Layer-Liste.
  - Änderungen an der Modellkonfiguration (`ModelConfig` / `ModelLayerMapping` / aktive Layer) müssen nicht in mehreren UIs separat gepflegt werden.
- Keine Inferenz im Content-Editor:
  - Es werden keine Bilder geladen, keine Aktivierungen berechnet und keine Visualisierungen erzeugt.
  - Damit bleibt die Content-View performant und unabhängig vom aktuellen Kamerastatus.

---

## 6. UX-Überblick und typische Workflows

### 6.1 Texte für Modell-Layer pflegen

1. Admin wählt im Admin-Panel die Content-View / den Content-Editor.
2. In der linken Navigation wählt er unter „Modell-Layer: …“ einen konkreten Modell-Layer (z.B. `conv1` oder `layer2`).
3. In der rechten Seite bearbeitet er:
   - Seitentitel,
   - Subtitle für die Kamera-Ansicht,
   - Beschreibungstext für Besucher:innen.
4. Klick auf „Konfiguration speichern“:
   - Änderungen werden in `cfg.ui.model_layers[model_layer_id]` übernommen und in `exhibit_config.json` persistiert.

### 6.2 Globale und UI-Layer-Texte bearbeiten

- Global:
  - Auswahl „Global“ in der Navigation.
  - Änderung des Ausstellungstitels (z.B. für das gesamte Exponat).
- UI-Layer:
  - Auswahl eines klassischen UI-Layers (Button-Label oder ID).
  - Anpassen von:
    - Button-Text,
    - Titelzeilen-Label,
    - Subtitle,
    - Beschreibungstext.
- Speichern erneut über „Konfiguration speichern“.

---

## 7. Beziehungen zu anderen Views

- **Feature-View**:
  - Speichert `model_layer_id` in Favoriten-Presets (`metadata.favorites` in der JSON-Config).
  - Greift auf `ModelEngine` und `VizEngine` zu, um Aktivierungen zu visualisieren.
  - Arbeitet auf derselben Modell-Layer-Liste wie der Content-Editor.
- **Kino-View**:
  - Nutzt `cfg.ui.layers` und perspektivisch `cfg.ui.model_layers` + Favoriten,
    um pro Modell-Layer-Seite:
    - Texte (Titel, Subtitle, Beschreibung),
    - und ausgewählte Favoriten-Visualisierungen anzuzeigen.
- **Config-Schicht**:
  - Die Content-View ist der primäre Editor für `ui.title`, `ui.layers[*].*` und `ui.model_layers[*].*`.
  - Dadurch bleiben `config_view_current.md`, `feature_view_current.md` und `kino_view_current.md` konsistent,
    da sie sich alle auf dieselbe zentrale Config-Struktur beziehen.

---

*Zuletzt geprüft: Stand 2025-11-23 (basierend auf `ui_admin_streamlit/content_view.py` und aktueller Config-/Core-Implementierung).*
