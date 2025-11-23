# Änderungsanalyse v0 – Kino-Modus (Kivy), Favoriten und Global-Config

## 1. Zweck und Kontext dieser Analyse

Diese Analyse dokumentiert den **Ist-Zustand** der aktuellen Codebasis im Projektordner `prototype_v0` (Stand laut Notizen: 2025‑11‑22) im Hinblick auf geplante Änderungen am:

- **Kino-Modus (Kivy, `ui_kino_kivy/`)**,
- **Admin-Views (Streamlit, insbesondere Content-View und Feature-View)**,
- **gemeinsamen Konfigurationsmodell (`config/*`, `exhibit_config.json`)**.

Sie dient ausschließlich als **Vorbereitung für eine spätere Implementierungsplanung** und beantwortet drei fokussierte Fragen:

1. Wie wird **„Global“** heute in Config, Content-View, Feature-View und Kino-View verstanden und genutzt? Woher kommen globale Texte (Titel, Button-Labels etc.), und wo sind Dinge noch hart im Code verdrahtet?
2. Wo und wofür wird die harte ID `"layer1_conv1"` verwendet (Default-Config, Fallbacks, Kommentare), und welche impliziten Annahmen hängen daran?
3. Wie ist der **Lebenszyklus der Favoriten** von der Speicherung in der Config, über die Verwaltung in Streamlit, bis zur Anzeige und Live-Nutzung im Kino-View? Welche Stellen wären betroffen, wenn die Auswahl „Favoriten pro Kivy-Seite“ stärker in der Content-View verankert würde?

Die Datei trifft **keine Architektur- oder Designentscheidungen**, sondern listet nur relevante Stellen (Dateien, Klassen, Funktionen, Felder) auf, die bei der späteren Änderung voraussichtlich angepasst werden müssen oder zumindest zu prüfen sind. Die geplanten Änderungen werden hier **nur als Zielbild / Prompt-Beschreibung** gesammelt, nicht als Umsetzungsvorschrift.

---

## 2. Themenblock 1 – „Global“ und globale UI-Definitionen

### 2.1 Globale Inhalte in der Config

**Relevante Dateien**

- `config/models.py`
  - `class ExhibitUIConfig`  
    Felder:
    - `title: str` – globaler Ausstellungstitel (wird in mehreren UIs angezeigt).
    - `language: str = "de"` – Sprachcode.
    - `layers: List[LayerUIConfig]` – klassische UI-Layer-Konfiguration.
    - `model_layers: Dict[str, ModelLayerContent]` – Content pro Modell-Layer-ID.

- `config/service.py`
  - `_default_config_dict()`  
    Legt Default-Felder an:
    - `"ui": {"title": "Wie ein neuronales Netz sieht", "language": "de", "layers": [...]}`.
    - **Kein eigener `ui.model_layers`-Eintrag** im Default (wird dynamisch ergänzt).

**Beobachtungen (Ist-Zustand)**

- Der Begriff **„Global“** taucht im Config-Datenmodell nicht als eigener Knoten auf.
  - Globale Informationen sind aktuell vor allem der Ausstellungstitel `ui.title`.
  - Weitere globale UI-Aspekte (z.B. globale Button-Beschriftungen) sind nicht explizit als „global“ modelliert.
- `ui.model_layers` ist explizit **modell-layer-basiert** (`model_layer_id -> ModelLayerContent`), nicht „global“.

**Relevanz für das Vorhaben**

- Für das Ziel, „Global“ als Bereich für **seitenübergreifende Variablen** (Titel, alle Button-Labels etc.) zu verstehen, ist heute erst **`ui.title`** klar global.  
  Weitere globale Definitionen (z.B. zentrale Button-Label-Definitionen) existieren so in der Config noch nicht.

**Potentielle Konfliktstellen bei Änderungen**

- Wenn globale Definitionen (z.B. Button-Labels) künftig in einem neuen globalen Config-Bereich liegen sollen, müssen Stellen, die heute direkt auf `LayerUIConfig` zugreifen, sauber umgestellt werden, ohne die bestehende Trennung von **Config** (Daten) und **UI-Logik** (Streamlit/Kivy) zu verletzen (Separation of Concerns).
- Jede Erweiterung der Config-Struktur muss kompatibel zur bestehenden Migration/Validierung in `config/service.py` bleiben; die Config-Schicht sollte rein datenorientiert bleiben und keine UI-spezifische Logik aufnehmen.

---

### 2.2 „Global“ im Content-Editor (Streamlit)

**Relevante Dateien**

- `notes/current/content_view_current.md`
- `ui_admin_streamlit/content_view.py`

**Zentrale Punkte aus der Dokumentation**

- Konstanten / IDs (aus `content_view_current.md`):
  - `PAGE_ID_GLOBAL = "global"` – interne Kennung der Global-Seite.

- Funktion `render()` in `content_view.py` (High-Level-Ablauf):
  1. `cfg = load_config()` – Laden der `ExhibitConfig`.
  2. Falls `cfg.ui.layers` leer ist, wird ein Default-UI-Layer mit ID `"layer1_conv1"` angelegt (siehe Themenblock 2).
  3. Bestimmen der Modell-Layer-IDs über `_get_model_layer_ids(cfg.model)` (via `ModelEngine.get_active_layers()`).
  4. Aufbau der Navigations-Optionen (`nav_options`):
     - Eintrag `("Global", PAGE_ID_GLOBAL)`.
     - Pro Modell-Layer: `("Modell-Layer: {ml_id}", f"model::{ml_id}")`.
     - Pro UI-Layer: `(layer.button_label or layer.id, layer.id)`.
  5. `st.radio` zur Auswahl der Seite.
  6. Rendering abhängig von der gewählten Seite:
     - **Global-Seite (PAGE_ID_GLOBAL)**: Bearbeitung von `cfg.ui.title`.
     - Modell-Layer-Seite: Bearbeitung von `cfg.ui.model_layers[model_layer_id]`.
     - UI-Layer-Seite: Bearbeitung von `LayerUIConfig`-Feldern (Button-Label, Titelzeile, Subtitle, Beschreibung).

**Beobachtungen (Ist-Zustand)**

- Die **Global-Seite** im Content-Editor dient aktuell **ausschließlich** der Bearbeitung des Ausstellungstitels:
  - `st.text_input("Ausstellungstitel", value=cfg.ui.title)`.
- Button-Labels und andere UI-Layer-Informationen sind **nicht** Teil der Global-Seite, sondern werden auf den einzelnen UI-Layer-Seiten (pro `LayerUIConfig`) gepflegt.
- „Global“ ist hier also eine **eigene Seite im Editor**, die nur `cfg.ui.title` verwaltet, keine weiteren globalen UI-Variablen.

**Relevanz für das Vorhaben**

- Wunschbild: „Global“ als **zentraler Ort für seitenübergreifende Variablen** (Titel + Button-Beschriftungen).  
  Ist-Zustand: Global-Seite kennt nur `ui.title`.  
  → Änderungen würden `content_view.py` betreffen (Navigation, Felder, Schreiblogik für Button-Labels und evtl. andere globale Definitionen).

**Potentielle Konfliktstellen bei Änderungen**

- Wenn „Global“ im Admin-UI künftig auch die Pflege aller Button-Beschriftungen übernehmen soll, muss darauf geachtet werden, dass
  - bestehende UI-Layer-Seiten im Editor nicht inkonsistent werden (doppelte Bearbeitungsorte für dasselbe Label),
  - die Business-Logik (Config-Struktur) nicht direkt mit Streamlit-spezifischen Konzepten vermischt wird.
- Die Navigation der Content-View koppelt bereits heute **Content-Struktur** (Modell-Layer, UI-Layer, Global) an die `ModelEngine`.  
  Änderungen an der Bedeutung von „Global“ dürfen diese Kopplung nicht aufbrechen oder zusätzliche Abhängigkeiten zur Kivy-Implementierung hinzufügen; die Trennung `config` ↔ `core` ↔ `ui_admin_streamlit` muss erhalten bleiben.

---

### 2.3 „Global“ im Kino-View (Kivy)

**Relevante Dateien**

- `notes/current/kino_view_current.md`
- `ui_kino_kivy/app.py`

**Zentrale Punkte aus der Dokumentation**

- Klasse `ExhibitRoot(BoxLayout)` in `ui_kino_kivy/app.py`:
  - Lädt `cfg = load_config()`.
  - Verwendet `cfg.ui.title` zur Anzeige in der Titelzeile (`_build_titlebar`).
  - Erstellt Buttonleiste (`_build_buttonbar`):
    - Ein „Global“-Button.
    - Ein Button pro aktivem Modell-Layer (`ModelEngine.get_active_layers()`).
  - Seitenlogik:
    - `switch_to_page(page_id: str)` unterscheidet:
      - `page_id == "global"` – Anzeige einer **Global-/Startseite**.
      - `page_id == model_layer_id` – Anzeige einer modell-layer-spezifischen Seite.
  - Pro Modell-Layer-Seite werden Texte und Favoriten geladen über:
    - `get_model_layer_content(cfg, model_layer_id)` – Texte.
    - `get_favorites_for_model_layer(cfg, model_layer_id)` – Favoriten.

**Beobachtungen (Ist-Zustand)**

- Der „Global“-Button in Kivy führt zu einer **Besucher:innen-Seite** („Globalseite“), nicht zu einem Editor.
- Die Inhalte der Globalseite stammen primär aus `cfg.ui.title` sowie statischen UI-Elementen im Code (Platzhaltertexte, Label-Texte etc.).
- Button-Beschriftungen (inkl. „Global“) sind derzeit weitgehend **hart im Kivy-Code** definiert (z.B. Text des Buttons), nicht über einen separaten globalen Config-Knoten.

**Relevanz für das Vorhaben**

- Die geplante Neuinterpretation von „Global“ (als reine Konfigurations-/Definitionsebene in der Feature-View) steht in einem gewissen Spannungsverhältnis zur heutigen Rolle der Globalseite im Kino-View (Publikumsoberfläche).  
  Eine Änderung der semantics von „Global“ **darf die Besucher:innen-UX der Globalseite nicht unbeabsichtigt verändern**.

**Potentielle Konfliktstellen bei Änderungen**

- Wenn globale Button-Labels künftig in einer globalen Config-Sektion gepflegt werden, sollten Kivy-Labels diese Werte **nur lesen**, nicht eigene Logik dazu mischen (Separation of Concerns: Kivy = Darstellung, Config = Daten).  
  Heute sind einige Texte im Kivy-Code fest eingebaut; eine Umstellung birgt das Risiko, dass bei fehlender Config Fehler oder leere Labels auftreten.
- Die `page_id "global"` im Kivy-View darf nicht mit einer evtl. neuen „Global-Konfigseite“ in Streamlit verwechselt werden.  
  Es sollte klar bleiben: Kivy-„Global“ = Besucher-Seite, Streamlit-„Global“ = Admin-Konfigbereich.

---

### 2.4 „Global“ und Feature-View (Streamlit)

**Relevante Dateien**

- `notes/current/feature_view_current.md`
- `ui_admin_streamlit/feature_view/view.py`

**Beobachtungen (Ist-Zustand)**

- Die Feature-View arbeitet **nicht** mit einem eigenen „Global“-Konzept:
  - Sie bezieht sich auf einen ausgewählten UI-Layer (`ui_layer.id`) und modell-layer-basierte Parameter (`model_layer_id`),
  - kennt aber keine globale Seite oder globale Config-Section.
- Favoriten werden pro UI-Layer verwaltet, nicht global (Details in Themenblock 3).

**Relevanz / mögliche Konflikte**

- Wenn künftig eine **globale Konfigurationsseite für Favoriten und Button-Definitionen** angedacht ist, müsste die Feature-View diese neue Rolle klar von ihrer heutigen Aufgabe (technische Visualisierung und Preset-Verwaltung pro UI-Layer) trennen.  
  Die Feature-View sollte weiterhin primär für **Modell-/Visualisierungs-Engineering** zuständig bleiben, nicht für generische UI-Textpflege.

---

### 2.5 Zusammenfassung Themenblock „Global“

**Ist-Zustand**

- Global in der Config: praktisch nur `ui.title`.
- Global in der Content-View: eigene Admin-Seite, die `ui.title` pflegt.
- Global in der Kino-View: Besucher-Seite mit globalem Titel und weiteren (teilweise hart kodierten) Inhalten.
- Feature-View kennt kein „Global“.

**Geplantes Zielbild (nur als Prompt-Beschreibung, nicht als Design)**

- „Global“ soll im Admin-Kontext dazu dienen, **seitenübergreifende Variablen zu pflegen**:
  - globaler Titel,
  - Beschriftungen aller Buttons (ggf. mit Mapping auf interne Layer-IDs),
  - weitere globale Definitionen, die von allen Kivy-Seiten benötigt werden.
- Es soll geprüft werden, ob diese Informationen **bereits in der Config vorhanden** sind oder noch hart im Code stehen und daher künftig in die Config verlagert werden müssen.

**Hinweise zu Separation of Concerns / mögliche Konflikte**

- Änderungen an „Global“ dürfen die klare Schichtung nicht aufbrechen:
  - `config/*` bleibt reine Daten- und Speicherschicht.
  - `core/*` bleibt modell- und visualisierungszentriert.
  - `ui_admin_streamlit/*` und `ui_kino_kivy/*` bleiben reine Darstellung/Interaktion.
- Potentielle Probleme:
  - Doppelpflege von Labels (Global-Seite vs. UI-Layer-Seiten) → Inkonsistenzen.
  - Vermischung von Kivy-spezifischen Layout-Details mit globaler Textkonfiguration.

---

## 3. Themenblock 2 – Harte ID `"layer1_conv1"`

### 3.1 Vorkommen in Default-Config und Service-Schicht

**Relevante Dateien**

- `config/service.py`
- `notes/current/config_view_current.md`

**Zentrale Stellen**

- `config/service.py`, Funktion `_default_config_dict()`:
  - Legt eine Standard-Config mit genau einem UI-Layer an:
    - `id: "layer1_conv1"`.
    - `order: 1`.
    - `button_label: "Frühe Kanten"`.
    - `title_bar_label: "Layer 1 – Kanten"`.
    - `description: ...`.
    - `viz_preset_id: "preset_layer1"`.
  - Gleichzeitig wird in `viz_presets` ein Preset mit
    - `id: "preset_layer1"`,
    - `layer_id: "layer1_conv1"`,
    - weiteren Visualisierungsparametern angelegt.

**Beobachtungen (Ist-Zustand)**

- `"layer1_conv1"` fungiert als **Bootstrapping-ID** für
  - den ersten UI-Layer in einer frischen Config,
  - ein dazugehöriges Default-Visualisierungspreset.
- Die Config-Validierung (`validate_config`) verlangt nur, dass
  - mindestens ein UI-Layer existiert und
  - alle `viz_preset_id`-Referenzen gültig sind;  
  es gibt **keine hart kodierte Prüfung** auf genau `"layer1_conv1"`.

---

### 3.2 Fallback im Content-Editor

**Relevante Dateien**

- `ui_admin_streamlit/content_view.py`
- `notes/current/content_view_current.md`

**Zentrale Stelle**

- In `render()` (Content-View):
  - Wenn `cfg.ui.layers` leer ist, wird **zusätzlich** ein Default-Layer mit ID `"layer1_conv1"` erzeugt, um sicherzustellen, dass es mindestens einen UI-Layer gibt.

**Beobachtungen (Ist-Zustand)**

- Damit existieren zwei Stellen, die dieselbe ID implizit voraussetzen:
  - `_default_config_dict()` (beim Anlegen/Fehlerfall der Config-Datei),
  - Content-View-Fallback (bei leerer `cfg.ui.layers` im laufenden System).
- Die ID `"layer1_conv1"` ist somit zwar **nicht für den Betrieb zwingend**, aber sie wird stark als „Standard-ID“ zementiert.

---

### 3.3 Beispiele im Datenmodell

**Relevante Dateien**

- `config/models.py`

**Zentrale Stellen**

- Kommentare/Beispielwerte in Dataclasses wie `ModelLayerMapping` und `LayerUIConfig` erwähnen `"layer1_conv1"` als Beispiel-ID.

**Beobachtungen (Ist-Zustand)**

- Diese Stellen sind rein dokumentarisch und haben **keinen funktionalen Zwang** zur Verwendung dieser ID.

---

### 3.4 Zusammenfassung und geplante Änderung

**Ist-Zustand**

- Funktionale Verwendung von `"layer1_conv1"`:
  - Default-UI-Layer in `_default_config_dict()`.
  - Default-Preset in `_default_config_dict()`.
  - Fallback-Layer-Erzeugung in der Content-View.
- Dokumentarische Verwendung:
  - Kommentare in `config/models.py`.

**Geplante Änderung (als Prompt-Beschreibung)**

- Die harte ID `"layer1_conv1"` soll **perspektivisch aus der Config entfernt** werden.  
  Erwartetes Zielbild:
  - UI-Layer-IDs und Preset-IDs werden dynamisch oder über andere Defaults definiert,
  - keine magische Sonder-ID mehr in den Defaults.

**Potentielle Konfliktstellen / Risiken**

- Beim Entfernen oder Umbenennen von `"layer1_conv1"` sind folgende Aspekte besonders kritisch:
  - Migration bestehender `exhibit_config.json`-Dateien (Altbestände), die `"layer1_conv1"` enthalten.
  - Korrekte Anpassung des Fallback-Verhaltens in `content_view.render()`, damit weiterhin garantiert ist, dass mindestens ein Layer existiert, ohne auf diese eine ID festgelegt zu sein.
  - Sicherstellen, dass keine weiteren (evtl. übersehene) Stellen im Code implizit annehmen, dass `cfg.ui.layers[0].id == "layer1_conv1"` ist.
- Aus Sicht der **Separation of Concerns**:
  - Änderungen an Default-IDs gehören in die Config- und Migrationsschicht, nicht in UI-spezifische Logik.
  - UI-Schichten (Streamlit/Kivy) sollten sich möglichst wenig auf konkrete ID-Literals verlassen und eher mit bereitgestellten Strukturen/Listen arbeiten.

---

## 4. Themenblock 3 – Favoritenfluss zwischen Streamlit und Kivy

### 4.1 Speicherort und Struktur der Favoriten in der Config

**Relevante Dateien**

- `config/service.py`
- `notes/current/config_view_current.md`

**Zentrale Stellen**

- Favoriten werden in der JSON-Config **nicht** als eigene Dataclass modelliert, sondern in `metadata`-Feldern der UI-Layer abgelegt:
  - Pfad: `ui.layers[*].metadata.favorites`.
- `config/service.py` stellt die Funktion
  - `get_favorites_for_model_layer(cfg, model_layer_id, max_count=3)` bereit:
    - iteriert über alle `cfg.ui.layers[*].metadata.favorites`,
    - filtert Favoriten, deren `preset["model_layer_id"] == model_layer_id` ist,
    - begrenzt auf `max_count` (Standard: 3).

**Beobachtungen (Ist-Zustand)**

- Favoriten sind **UI-Layer-basiert gespeichert**, aber mit einer **modell-layer-basierten Sicht**:
  - „Schlüssel“ im JSON: `ui_layer.id` (Speicherort in `metadata`),
  - eigentliche Zuordnung zum Modell-Layer: `preset["model_layer_id"]`.
- `get_favorites_for_model_layer` kapselt die „Übersetzung“ von dieser Struktur hin zu „max. 3 Favoriten pro `model_layer_id`“.

---

### 4.2 Verwaltung der Favoriten in der Feature-View

**Relevante Dateien**

- `ui_admin_streamlit/feature_view/view.py`
- `ui_admin_streamlit/feature_view/favorites.py`
- `notes/current/feature_view_current.md`

**Zentrale Stellen**

- `feature_view/view.py`:
  - Lädt `cfg = load_config()` (typisiert) und `raw_cfg = load_raw_config_dict()` (rohes Dict).
  - Wählt aktuell **einen** UI-Layer als Kontext (`ui_layers[0]`, `ui_layer.id` als `layer_key`).
  - Verwendet Funktionen aus `favorites.py`:
    - `get_layer_favorites(raw_cfg, ui_layer.id)`.
    - `upsert_favorite(raw_cfg, ui_layer.id, fav)`.
    - `delete_favorite(raw_cfg, ui_layer.id, fav_name)`.
  - Beim Speichern/Updaten eines Favoriten wird ein Dict erzeugt:
    - `{"name": fav_name, "layer_id": ui_layer.id, "preset": _current_preset_dict()}`.
    - `_current_preset_dict()` enthält u.a. `model_layer_id`, `channels`, `k`, `blend_mode`, `cmap`, `overlay`, `alpha`.

- `feature_view/favorites.py` (aus den Notizen):
  - Arbeitet ausschließlich auf `load_raw_config_dict()` / `save_raw_config_dict()`.
  - Strukturiert und validiert die `metadata.favorites`-Liste pro UI-Layer.

**Beobachtungen (Ist-Zustand)**

- Die Feature-View verwaltet Favoriten **pro UI-Layer-ID** und nutzt dabei `model_layer_id` nur als Bestandteil des Presets.
- Es gibt aktuell **keinen Mechanismus** in der Feature-View, Favoriten explizit pro `model_layer_id` oder „pro Kivy-Seite“ auszuwählen; die Sicht bleibt UI-Layer-orientiert.

---

### 4.3 Nutzung der Favoriten im Kino-View

**Relevante Dateien**

- `ui_kino_kivy/app.py`
- `notes/current/kino_view_current.md`

**Zentrale Stellen**

- Klasse `ExhibitRoot` in `ui_kino_kivy/app.py`:
  - Verwendet `ModelEngine.get_active_layers()` zur Bestimmung der `model_layer_ids`.
  - Pro `model_layer_id`:
    - ruft `_render_favorites(model_layer_id)` auf,
    - diese Funktion nutzt `get_favorites_for_model_layer(cfg, model_layer_id)`.

- `on_favorite_select(model_layer_id, favorite_name, favorite_dict)`:
  - erhält `favorite_dict` im Format der Config (inkl. `preset`).
  - baut ein `VizPreset` aus `favorite_dict["preset"]`.
  - startet Kamera-Stream und Live-Update (`Clock.schedule_interval(update_live_frame, ...)`).

**Beobachtungen (Ist-Zustand)**

- Der Kino-View denkt ausschließlich in **Modell-Layern (`model_layer_id`)**:
  - Seiten = `global` oder `model_layer_id`.
  - Favoriten = Ergebnis von `get_favorites_for_model_layer(cfg, model_layer_id)`.
- Die Begrenzung „maximal 3 Favoriten pro Modell-Layer“ ist in `get_favorites_for_model_layer(..., max_count=3)` implementiert und wird im Kino-View genutzt.
- Die ursprüngliche Information, zu welchem UI-Layer ein Favorit gehört (`layer_id` in der Favoritenstruktur), wird im Kino-View **nicht mehr verwendet**.

---

### 4.4 Zusammenspiel Content-View, Feature-View und Kino-View

**Relevante Dateien / Notizen**

- `notes/current/content_view_current.md`
- `notes/current/feature_view_current.md`
- `notes/current/kino_view_current.md`
- `config/service.py`

**Daten- und Kontrollfluss (heute)**

- Content-View:
  - Pflegt Texte pro `model_layer_id` in `cfg.ui.model_layers[model_layer_id]`.
- Feature-View:
  - Erzeugt und aktualisiert Favoriten, deren Presets eine `model_layer_id` enthalten.
  - Speichert diese Favoriten in `ui.layers[*].metadata.favorites`.
- Kivy-Kino-View:
  - Nutzt `get_model_layer_content(cfg, model_layer_id)` für Texte.
  - Nutzt `get_favorites_for_model_layer(cfg, model_layer_id)` für Favoriten (max. 3) pro Seite.

**Geplantes Zielbild (als Prompt-Beschreibung)**

- Die **Auswahl der Favoriten für jede Kivy-Seite** soll künftig in der Streamlit-Content-View („Content“, pro Layer-Seite) erfolgen, nicht in Kivy selbst.
- Konkreter Wunsch:
  - In `content_view` soll es pro `model_layer_id`-Seite ein Dropdown „Favoriten“ geben.
  - In diesem Dropdown sollen alle Favoriten angezeigt werden, die diesen Modell-Layer verwenden.
  - Pro Favorit gibt es eine Checkbox am rechten Rand.
  - Es können **bis zu 3 Favoriten** angeklickt werden.
  - Diese Auswahl wird in der Config so gespeichert, dass Kivy die jeweils ausgewählten Favoriten pro Seite visualisiert.
- Kivy soll nur noch
  - die Config auslesen und
  - die dazugehörigen Seiten samt ausgewählten Favoriten visualisieren.

---

### 4.5 Potentielle Konfliktstellen und Strukturfragen

**1. Doppelrolle der Feature-View vs. Content-View**

- Heute: Feature-View ist der Ort, an dem Favoriten **erzeugt und bearbeitet** werden; es gibt dort aber keine explizite UI, um „welche Favoriten sind für welche Kino-Seite aktiv?“ einzustellen.
- Geplant: Content-View soll zusätzlich die **Selektion** von Favoriten pro `model_layer_id` übernehmen.

Mögliche Konflikte:

- Wenn sowohl Feature-View (technische Bearbeitung) als auch Content-View (Auswahl für Kivy) auf dieselbe Favoritenstruktur zugreifen, muss klar getrennt sein:
  - Wo werden Favoriten **erzeugt/gelöscht/umbenannt** (Feature-View)?
  - Wo wird nur eine **Selektion / Submenge** pro `model_layer_id` getroffen (Content-View)?
- Gefahr bei unsauberer Trennung:  
  die Content-View beginnt, selbst Favoriten zu erstellen oder zu verändern → Vermischung von Rollen, Verletzung der Separation of Concerns (Content-View = Textkurations-UI, Feature-View = technische Preset-Verwaltung).

**2. Speicherstruktur in der Config**

- Heute: Favoriten liegen in `ui.layers[*].metadata.favorites` und sind nur über `preset.model_layer_id` einem Modell-Layer zuordenbar.
- Geplant: Möglicherweise Anpassungen der Config-Struktur (z.B. Trennung „allgemeine Config“ vs. „Kivy-spezifische Config“ oder zusätzliche Felder zur Selektion von Favoriten pro `model_layer_id`).

Mögliche Konflikte:

- Jede strukturelle Änderung muss
  - mit `config/migrations.py` abgestimmt werden (Migration bestehender Config-Dateien),
  - so gestaltet sein, dass `config/service.get_favorites_for_model_layer` und `ui_kino_kivy/app.py` klar und einfach bleiben (kein Einbau von UI-Logik in die Config-Schicht).
- Eine zu starke Spezialisierung der Config auf Kivy-spezifische Details kann die Wiederverwendbarkeit für andere Frontends (z.B. zukünftige Webfrontends) einschränken.

**3. Kivy-spezifisches Verhalten vs. generische Config**

- Die Idee eines „↦“-Buttons in Kivy, um bei **mehr als einem** aktiven Favoriten pro Layer zwischen ihnen durchzuschalten, ist ein **UI-Verhalten**.
- Die Config sollte nur festhalten, **welche** Favoriten pro `model_layer_id` aktiv sind (z.B. Liste von Favoritennamen oder IDs), nicht **wie** zwischen ihnen navigiert wird.

Mögliche Konflikte:

- Wenn im Config-Format UI-Verhaltensdetails (z.B. Reihenfolge oder Art der Navigation) kodiert würden, wäre die Trennung zwischen
  - Datenmodell (Config) und
  - Präsentationslogik (Kivy)
  gefährdet.

**4. Begrenzung auf maximal 3 Favoriten pro Layer**

- Heute ist die „max 3“-Regel implizit in `get_favorites_for_model_layer(..., max_count=3)` verankert.
- Geplant ist, dass in der Content-View genau diese Begrenzung ebenfalls berücksichtigt wird (Checkboxen, max. 3 auswählbar).

Mögliche Konflikte:

- Wenn später die Begrenzung geändert werden soll (z.B. 4 Favoriten), müssten
  - Kivy,
  - Config-Service,
  - Content-View-UI
  synchron angepasst werden.  
  Die Logik, **wie viele** Favoriten erlaubt sind, sollte möglichst zentral definiert werden (z.B. Konstante im Config-/Core-Bereich), um Streuung zu vermeiden.

---

## 5. Hinweise zur Trennung allgemeiner vs. Kivy-spezifischer Config

**Ist-Situation**

- Viele Config-Bereiche werden **gemeinsam** von Admin- und Kino-View genutzt:
  - `ExhibitConfig.model` (Modellparameter, Layerliste),
  - `ExhibitConfig.ui.title` (globaler Titel),
  - `ExhibitConfig.ui.model_layers` (modell-layer-basierter Textcontent),
  - `ExhibitConfig.ui.layers` (klassische UI-Layer-Struktur, inkl. `metadata.favorites`),
  - `viz_presets` (Visualisierungspresets).
- Es gibt keinen dezidierten Abschnitt „nur für Kivy“; Kivy liest primär aus denselben UI-Strukturen wie Streamlit.

**Mögliche spätere Trennung (nur Markierung, kein Design)**

- Denkbare Bereiche für eine zukünftige Trennung:
  - Allgemeine UI-Definitionen (Texte, Favoriten, Presets) vs.
  - Kivy-spezifische Layout-/Interaktionsdetails (z.B. Raster, Positionen, Update-Intervalle).
- Für das hier betrachtete Vorhaben ist wichtig, dass **jetzt keine neue starke Kopplung** entsteht, z.B. durch:
  - Kivy-spezifische Flags in `metadata` der Favoriten,
  - direkte Kivy-Layout-Hinweise in `ExhibitUIConfig`.

**Hinweis zu Separation of Concerns**

- Alle hier geplanten Änderungen sollten die bestehende Architektur respektieren:
  - `config` modelliert Daten und bietet generische Dienste (Laden/Speichern/Validieren/Migrieren),
  - `core` führt Modellinferenz und Visualisierung aus,
  - `ui_admin_streamlit` und `ui_kino_kivy` implementieren rein die Präsentationslogik.
- Konkrete Anpassungen sollten so gestaltet werden, dass
  - neue Felder/Strukturen in der Config **nicht** von UI-Frameworks abhängen,
  - UI-Code sich möglichst nur lesend auf die Config bezieht und Schreiboperationen konsistent über die Service-Schicht erfolgen.

---

## 6. Zusammenfassung der geplanten Änderungen (als Prompt-Grundlage)

Dieser Abschnitt fasst explizit die vom User beabsichtigten Änderungen zusammen, formuliert als **Input für spätere Implementierungs-Prompts**. Diese Punkte sind bewusst lösungsneutral gehalten.

1. **Neudefinition von „Global“ in der Feature-/Content-View**
   - „Global“ soll **keine eigene Kivy-Seite** im Sinne zusätzlicher Inhaltsebenen sein, sondern in der Admin-Logik (Feature/Content) als Bereich verstanden werden, in dem
     - der globale Titel und
     - seitenübergreifende UI-Variablen (v.a. Button-Beschriftungen für alle Kivy-Seiten)
     gepflegt werden.
   - Es soll überprüft und ggf. umgestellt werden, dass
     - relevante globale UI-Informationen **aus der Config** kommen und
     - nicht mehr hart im Code (Kivy oder Streamlit) verdrahtet sind.

2. **Entkopplung von der harten ID `"layer1_conv1"`**
   - Die Default-ID `"layer1_conv1"` soll **nicht mehr fest in der Config verankert** sein.
   - Defaults und Fallbacks sollen so gestaltet werden, dass
     - keine bestimmte Layer-ID vorausgesetzt wird und
     - die Config flexibel auf geänderte oder erweitere Layerstrukturen reagieren kann.

3. **Favoriten-Auswahl pro Kivy-Seite aus der Content-View heraus**
   - Die konkrete **Auswahl**, welche Favoriten pro `model_layer_id` im Kino-View angezeigt werden (max. 3 pro Layer), soll künftig in der Streamlit-
     Content-View pro Layer-Seite getroffen werden, nicht in Kivy.
   - Geplantes Verhalten (Admin-UI):
     - Auf jeder modell-layer-spezifischen Content-Seite (`content_view`) soll es ein Dropdown „Favoriten“ geben.
     - Dieses Dropdown zeigt alle Favoriten an, deren `preset.model_layer_id` dem aktuellen Layer entspricht.
     - Rechts daneben gibt es pro Favorit eine Checkbox; es können bis zu 3 Favoriten selektiert werden.
     - Diese Auswahl wird in der Config so gespeichert, dass Kivy anschließend
       - nur noch diese Favoriten pro Seite lädt und
       - bei mehr als einem aktiven Favoriten einen UI-Mechanismus („↦“-Button oder ähnliches) bietet, um zwischen ihnen zu wechseln.
   - Kivy bleibt dabei **rein konsumierende Schicht**:  
     Es liest die Config (Welcher `model_layer_id`? Welche Favoriten sind ausgewählt?) und visualisiert; die Entscheidung, **welche** Favoriten aktiv sind, wird in Streamlit getroffen.

4. **Wahrung der Separation of Concerns und Basisarchitektur**
   - Bei allen Änderungen gilt:
     - `config` definiert das Datenmodell und die Persistenz – keine UI-Framework-Kopplung.
     - `core` bleibt UI-unabhängig.
     - `ui_admin_streamlit` ist Admin-Frontend, das Config bearbeitet und Tests/Favoriten verwaltet.
     - `ui_kino_kivy` ist Publikums-Frontend, das Config nur liest und visuell darstellt.
   - Konflikte sind insbesondere dort zu erwarten, wo heute
     - IDs hart codiert sind (`"layer1_conv1"`),
     - Favoriten gleichzeitig von Feature-View und (künftig) Content-View beeinflusst werden,
     - die Rolle von „Global“ in Kivy (Besucher-Seite) und Streamlit (Admin-Config-Seite) ineinanderlaufen könnten.

Diese Punkte bilden die Grundlage für eine nachgelagerte **Implementierungsplanung** (separate Datei), in der konkrete Schritte, Migrationspfade und Codeänderungen entworfen werden können.
