# Config-Schicht – aktueller Stand

## 1. Rolle im Gesamtsystem

- Die Config-Schicht bündelt alle Einstellungen rund um das Exponat in einer zentralen, dateibasierten Konfiguration.
- Zentrales Artefakt ist die JSON-Datei `config/exhibit_config.json`, die über das Python-Package `config` gelesen und geschrieben wird.
- Die Konfiguration beschreibt u.a.:
  - Identität des Exponats (`exhibit_id`),
  - verwendetes CNN-Modell (ResNet18) inkl. Layer-Mappings,
  - die UI-Struktur mit Layern, Titeln und Beschreibungstexten,
  - vordefinierte Visualisierungspresets für Featuremaps.
- Die Config-Schicht wird von mehreren Teilen des Systems gemeinsam genutzt:
  - **Kino-View** (`ui_kino_kivy`): liest `ExhibitConfig`, um Buttons, Titel, Texte und Visualisierungspresets anzuzeigen.
  - **Admin-Panel / Feature-View** (`ui_admin_streamlit`): liest `ExhibitConfig` typisiert und arbeitet zusätzlich auf der rohen JSON-Struktur, um z.B. Favoriten in `metadata` zu verwalten.
- Im Gegensatz zur `core`-Schicht (Model- und Visualisierungsengine) führt die Config-Schicht keine Inferenz aus und kennt keine PyTorch-Modelle; sie beschreibt nur Strukturen und Parameter.

### 1.1 Verortung im Projekt

- Pfad: `config/` im Projektwurzelverzeichnis.
- Wichtige Konsumenten:
  - `ui_kino_kivy/app.py` (lädt `ExhibitConfig` per `config.service.load_config`).
  - `ui_admin_streamlit/feature_view/view.py` (nutzt `load_config`, `load_raw_config_dict`, `save_raw_config_dict`).
  - weitere UI- oder Service-Komponenten können über dieselbe API auf die Config zugreifen.
- Die Datei `exhibit_config.json` wird bei Bedarf automatisch angelegt:
  - Wenn beim Laden keine Datei vorhanden ist, schreibt `config.service` eine Default-Konfiguration auf Basis von `_default_config_dict()`.

### 1.2 High-Level-Konzepte der Config-Schicht

- Die Config-Schicht arbeitet mit drei Ebenen:
  - **Persistente Ebene**: die JSON-Datei `config/exhibit_config.json` als dauerhafte, menschenlesbare Konfiguration.
  - **Typisierte Ebene**: Dataclasses in `config/models.py` (`ExhibitConfig`, `ModelConfig`, `LayerUIConfig`, `VizPreset` usw.) bilden die JSON-Struktur in Python ab.
  - **Service- / Migrations-Ebene**: Funktionen in `config/service.py` und `config/migrations.py` verbinden Datei und Dataclasses (Laden, Speichern, Validierung, Versionierung).
- Wichtige Domänenbegriffe in der Config-Schicht:
  - **Exhibit**: das Gesamtobjekt der Ausstellungskonfiguration (`ExhibitConfig`).
  - **UI-Layer**: ein logischer Schritt oder eine Ebene der Darstellung, z.B. „frühe Kanten“; in der Config als `LayerUIConfig` geführt.
  - **Model-Layer-Mapping**: Zuordnung zwischen UI-Layer-IDs und konkreten Layernamen des CNN.
  - **Viz-Preset**: vordefinierte Visualisierungseinstellung für Aktivierungen (Channels, Blend-Mode, Overlay etc.).

---

## 2. Dateien und Verantwortlichkeiten im `config`-Package

Verzeichnis: `config/`

### 2.1 Überblick

- Die Config-Schicht besteht aus folgenden Kernelementen:
  - `config/models.py` – Deklariert das Datamodell (Dataclasses) für die Konfiguration.
  - `config/service.py` – Bietet Funktionen zum Laden/Speichern der Konfiguration als Dataclasses und als rohes Dict, inkl. Locking und Backup.
  - `config/migrations.py` – Kapselt alle Versionsmigrationen für die JSON-Struktur.
  - `config/exhibit_config.json` – die persistente, von Menschen lesbare Konfigurationsdatei.
  - `config/exhibit_config.json.backup` – Backupkopie der letzten funktionierenden Config.
  - `config/exhibit_config.json.lock` – temporäre Lock-Datei während Schreibzugriffen.

---

### 2.2 `config/models.py`

- Verantwortlichkeit:
  - Definiert die Dataclasses, die die Struktur der Exhibit-Konfiguration typisiert abbilden.
  - Diese Klassen werden von `config.service` verwendet, um JSON-Daten in Python-Objekte und zurück zu konvertieren.

#### 2.2.1 `BlendMode`

- Typalias `BlendMode = Literal["sum", "mean", "max", "weighted"]`.
- Beschränkt die möglichen Strings für die Blend-Strategie bei der Visualisierung von Featuremaps.

#### 2.2.2 `ModelLayerMapping`

- Dataclass zur Abbildung der Beziehung zwischen UI-Layern und konkreten Modell-Layern.
- Felder:
  - `ui_layer_id: str` – ID eines UI-Layers, z.B. `"layer1_conv1"`.
  - `model_layer_id: str` – technischer Name des Layers im CNN, z.B. `"conv1"` oder `"layer1.0.conv1"`.
  - `display_name: str` – sprechender Name für diesen Mapping-Eintrag, z.B. „Erste Faltungsschicht“.
- Dient dazu, UI-Begriffe von der konkreten Modellarchitektur zu entkoppeln.

#### 2.2.3 `VizPreset`

- Dataclass zur Beschreibung einer Visualisierungskonfiguration für Aktivierungen.
- Felder:
  - `id: str` – eindeutige ID des Presets, z.B. `"preset_layer1"`.
  - `layer_id: str` – referenziert typischerweise einen UI-Layer oder Model-Layer.
  - `channels: Union[List[int], str]` – entweder eine Liste expliziter Channel-Indizes (z.B. `[0, 3, 7]`) oder der String `"topk"`.
  - `k: int | None` – nur relevant, wenn `channels == "topk"`; gibt an, wie viele Top-Featuremaps genutzt werden sollen.
  - `blend_mode: BlendMode` – Blend-Strategie, z.B. `"mean"`.
  - `overlay: bool` – ob die Heatmap auf das Originalbild gelegt werden soll.
  - `alpha: float` – Transparenzfaktor für das Overlay (0–1).
  - `cmap: str` – Name der Colormap, z.B. `"viridis"`.
- `VizPreset` wird u.a. aus der JSON-Konfiguration geladen und von Visualisierungskomponenten interpretiert.

#### 2.2.4 `LayerUIConfig`

- Dataclass, die einen UI-Layer beschreibt.
- Felder:
  - `id: str` – interne ID des Layers, z.B. `"layer1_conv1"`.
  - `order: int` – Reihenfolge in der UI (z.B. Button-Reihenfolge).
  - `button_label: str` – Text auf dem Button am unteren Rand der Kino-View.
  - `title_bar_label: str` – Text in der Titelleiste der Kino-View, wenn der Layer aktiv ist.
  - `description: str` – erläuternder Text, der den Layer inhaltlich beschreibt.
  - `viz_preset_id: str` – Referenz auf ein `VizPreset.id` für die Standardvisualisierung dieses UI-Layers.

#### 2.2.5 `ModelConfig`

- Dataclass für die Modellkonfiguration.
- Felder:
  - `name: str = "resnet18"` – Name des verwendeten Modells (aktuell ResNet18).
  - `weights: str = "imagenet"` – Name bzw. Quelle der Pretrained-Gewichte.
  - `layer_mappings: List[ModelLayerMapping]` – optionale Liste von Mapping-Einträgen zwischen UI-Layern und Modell-Layern.

#### 2.2.6 `ExhibitUIConfig`

- Kapselt alle UI-bezogenen Konfigurationsaspekte des Exponats.
- Felder:
  - `title: str` – globaler Ausstellungstitel, der in der Kino-View angezeigt wird.
  - `language: str = "de"` – Sprachkennzeichen, aktuell standardmäßig „de“.
  - `layers: List[LayerUIConfig]` – Liste aller UI-Layer, aus denen z.B. die Kino-View ihre Buttons und Texte bezieht.
  - `model_layers: Dict[str, ModelLayerContent]` – Mapping von Modell-Layer-IDs auf deren Content-Konfiguration.

#### 2.2.7 `ExhibitConfig`

- Wurzel-Dataclass der gesamten Konfiguration.
- Felder:
  - `exhibit_id: str` – eindeutige Kennung des Exponats.
  - `model: ModelConfig` – Modellkonfiguration für das CNN.
  - `ui: ExhibitUIConfig` – UI-spezifische Konfiguration.
  - `viz_presets: List[VizPreset]` – Liste aller verfügbaren Visualisierungspresets.
  - `version: str = "1.0"` – Versionskennzeichen der Config-Struktur.

---

### 2.3 `config/service.py`

- Verantwortlichkeit:
  - Stellt die zentrale API zum Laden und Speichern der Konfiguration bereit.
  - Arbeitet sowohl mit typisierten Dataclasses (`ExhibitConfig`) als auch mit rohen JSON-Dicts.
  - Kapselt Schutzmechanismen wie File-Locking und Backup-Wiederherstellung.

#### 2.3.1 Pfade und Konstanten

- `BASE_DIR = Path(__file__).resolve().parent.parent` – Projektbasisverzeichnis.
- `CONFIG_PATH = BASE_DIR / "config" / "exhibit_config.json"` – Pfad zur Hauptkonfigurationsdatei.
- `LOCK_PATH = BASE_DIR / "config" / "exhibit_config.json.lock"` – Pfad zur Lock-Datei.
- `BACKUP_PATH = BASE_DIR / "config" / "exhibit_config.json.backup"` – Pfad zur Backup-Datei.

#### 2.3.2 `FileLock`

- Klasse zur Realisierung eines einfachen File-Locks.
- Konstruktor:
  - `FileLock(lock_path: Path, timeout: float = 2.0)` – speichert Lock-Pfad und Timeout.
- `acquire()`:
  - Versucht in einer Schleife bis zum Timeout, die Lock-Datei exklusiv zu erstellen (`open("x")`).
  - Schreibt bei Erfolg einen Zeitstempel in die Lock-Datei und gibt `True` zurück.
  - Bei bereits existierender Lock-Datei wird kurz gewartet (`time.sleep(0.05)`) und erneut versucht.
  - Bei anderen Fehlern wird geloggt und `False` zurückgegeben.
  - Nach Ablauf des Timeouts wird eine Warnung geloggt und `False` geliefert.
- `release()`:
  - Löscht die Lock-Datei, falls vorhanden; Fehler werden geloggt.
- Kontextmanager-Unterstützung:
  - `__enter__()` ruft `acquire()` auf und wirft bei Misserfolg `TimeoutError`.
  - `__exit__()` ruft `release()` auf.
- `FileLock` wird von `save_config_dict()` verwendet, um gleichzeitige Schreibzugriffe zu koordinieren.

#### 2.3.3 `_default_config_dict()`

- Gibt ein rohes, JSON-kompatibles Default-Config-Dict zurück.
- Struktur des Default-Dicts:
  - `version`: `"1.0"`.
  - `exhibit_id`: `"cnn_museum_01"`.
  - `model`:
    - `name`: `"resnet18"`.
    - `weights`: `"imagenet"`.
    - `layer_mappings`: leere Liste.
  - `ui`:
    - `title`: `"Wie ein neuronales Netz sieht"`.
    - `language`: `"de"`.
    - `layers`: Liste mit genau einem Default-Layer:
      - `id`: `"layer1_conv1"`.
      - `order`: `1`.
      - `button_label`: `"Frühe Kanten"`.
      - `title_bar_label`: `"Layer 1 – Kanten"`.
      - `description`: erklärender Text zu frühen Kanten und Helligkeitsübergängen.
      - `viz_preset_id`: `"preset_layer1"`.
  - `viz_presets`:
    - Liste mit einem Default-Preset:
      - `id`: `"preset_layer1"`.
      - `layer_id`: `"layer1_conv1"`.
      - `channels`: `[0]`.
      - `blend_mode`: `"mean"`.
      - `overlay`: `False`.
      - `alpha`: `0.6`.
      - `cmap`: `"viridis"`.
- Dieses Dict wird sowohl für die Erstinitialisierung der Datei als auch als Fallback verwendet, wenn Lesen oder Parsen fehlschlägt.

#### 2.3.4 `validate_config(cfg: ExhibitConfig) -> List[str]`

- Prüft eine geladene `ExhibitConfig` auf grundlegende Konsistenz.
- Validierungsregeln:
  - Es muss mindestens ein UI-Layer (`cfg.ui.layers`) vorhanden sein.
  - Für jeden Layer muss `viz_preset_id` in der Menge der existierenden Preset-IDs (`cfg.viz_presets`) enthalten sein.
  - `cfg.model.name` muss in der Liste unterstützter Modelle liegen (aktuell nur `"resnet18"`).
- Liefert:
  - Eine Liste von Fehlermeldungs-Strings.
  - Leere Liste bedeutet: keine bekannten Validierungsfehler.
- Die Funktion wird in `load_config()` aufgerufen; gefundene Fehler werden geloggt, die Config wird aber dennoch zurückgegeben.

#### 2.3.5 `load_config() -> ExhibitConfig`

- Lädt die Konfigurationsdatei und liefert eine typisierte `ExhibitConfig`.
- Ablauf:
  1. Prüfen, ob `CONFIG_PATH` existiert.
     - Falls nicht, wird eine Default-Config mittels `save_config_dict(_default_config_dict())` angelegt.
  2. Versuch, das JSON über `json.load` zu laden.
     - Bei `JSONDecodeError` oder anderen Ausnahmen:
       - Es wird ein Fehler geloggt.
       - Als Fallback wird `_from_dict(_default_config_dict())` zurückgegeben.
  3. Auf das geladene Dict wird `migrate_config(raw)` angewendet.
  4. Das migrierte Dict wird mittels `_from_dict(raw)` in eine `ExhibitConfig` umgewandelt.
  5. Es erfolgt eine Validierung mit `validate_config(cfg)`.
     - Eventuelle Validierungsfehler werden als Warnungen geloggt.
     - Die Config wird trotz Fehlern zurückgegeben.

#### 2.3.6 `save_config(cfg: ExhibitConfig) -> None`

- Nimmt eine `ExhibitConfig` entgegen, wandelt sie mit `_to_dict` in ein rohes Dict um und delegiert das Speichern an `save_config_dict(data)`.
- Dient als typisierte Schreib-API für Konsumenten, die mit Dataclasses arbeiten.

#### 2.3.7 `save_config_dict(data: Dict[str, Any]) -> None`

- Schreibt ein rohes Dict nach `exhibit_config.json`.
- Ablauf:
  1. Stellt sicher, dass der `config`-Ordner existiert (`mkdir(parents=True, exist_ok=True)`).
  2. Erstellt einen `FileLock` mit `LOCK_PATH` und Timeout (2 Sekunden).
  3. Betritt den Lock-Kontext (`with lock:`):
     - Wenn `CONFIG_PATH` bereits existiert, wird versucht, eine Kopie nach `BACKUP_PATH` zu schreiben (`shutil.copy2`).
       - Bei Fehlern beim Backup wird eine Warnung geloggt, der Schreibvorgang wird dennoch fortgesetzt.
     - Die aktuelle Config wird mit `json.dump` nach `CONFIG_PATH` geschrieben (UTF-8, `ensure_ascii=False`, `indent=2`).
  4. Fehlerbehandlung:
     - Bei `TimeoutError` beim Erwerb des Locks wird ein Fehler geloggt und die Exception weitergereicht.
     - Bei anderen Ausnahmen beim Schreiben:
       - Fehler wird geloggt.
       - Falls ein Backup existiert, wird versucht, dieses zurückzuspielen (`BACKUP_PATH` → `CONFIG_PATH`).
       - Eventuelle Fehler bei der Wiederherstellung werden ebenfalls geloggt.
       - Die ursprüngliche Exception wird erneut geworfen.

#### 2.3.8 `load_raw_config_dict() -> Dict[str, Any]`

- Lädt die Konfiguration als rohes Dict, ohne in Dataclasses zu konvertieren.
- Ablauf analog zu `load_config()`, aber ohne `_from_dict` und Validierung:
  1. Prüfen und ggf. Anlegen der Datei via `save_config_dict(_default_config_dict())`, wenn `CONFIG_PATH` nicht existiert.
  2. Versuch, die Datei mit `json.load` zu laden.
     - Bei Fehlern (Parsing oder IO) wird ein Fehler geloggt und `_default_config_dict()` als Fallback zurückgegeben.
  3. Das geladene Dict wird durch `migrate_config(raw)` geschickt.
  4. Rückgabe des migrierten rohen Dicts.
- Diese Funktion wird u.a. in der Feature-View verwendet, um auf Zusatzstrukturen wie `metadata.favorites` zuzugreifen, die nicht in Dataclasses modelliert sind.

#### 2.3.9 `save_raw_config_dict(data: Dict[str, Any]) -> None`

- Speichert ein rohes Konfigurations-Dict unverändert zurück.
- Delegiert direkt an `save_config_dict(data)`.
- Wird z.B. aus der Feature-View heraus verwendet, um veränderte Roh-Konfigurationsdaten (inkl. `metadata`) zu persistieren.

#### 2.3.10 `_from_dict(d: Dict[str, Any]) -> ExhibitConfig`

- Konvertiert ein rohes, bereits migriertes Config-Dict in eine `ExhibitConfig`.
- Vorgehen:
  - Modellteil:
    - Liest `model_raw = d["model"]`.
    - Deserialisiert `layer_mappings` aus der Liste von Dicts in `ModelLayerMapping`-Instanzen.
    - Erstellt ein `ModelConfig`-Objekt (`name`, `weights`, `layer_mappings`).
  - UI-Teil:
    - Liest `ui_raw = d["ui"]`.
    - Liest `layers_raw = ui_raw.get("layers", [])`.
    - Für jeden Layer wird ein `LayerUIConfig` aufgebaut, indem nur die erwarteten Felder durchgereicht werden:
      - `id`, `order`, `button_label`, `title_bar_label`, `description`, `viz_preset_id`.
    - Unerwartete Felder wie z.B. `metadata` werden bewusst nicht übernommen.
    - Erstellt ein `ExhibitUIConfig` mit `title`, `language` (Default "de" falls nicht vorhanden) und der Liste von `LayerUIConfig`.
  - Presets:
    - Liest `presets_raw = d.get("viz_presets", [])`.
    - Wandelt jedes Dict mittels `VizPreset(**p)` in ein `VizPreset`-Objekt.
  - Gesamtobjekt:
    - Erzeugt ein `ExhibitConfig` mit
      - `exhibit_id = d["exhibit_id"]`,
      - dem modellierten `model_cfg`,
      - dem `ui_cfg`,
      - der Liste `presets`,
      - `version = d.get("version", "1.0")`.

#### 2.3.11 `_to_dict(cfg: ExhibitConfig) -> Dict[str, Any]`

- Konvertiert eine `ExhibitConfig` zurück in ein rohes Dict.
- Struktur der Rückgabe spiegelt `_from_dict` wider:
  - `version`: aus `cfg.version`.
  - `exhibit_id`: aus `cfg.exhibit_id`.
  - `model`:
    - `name`, `weights` aus `cfg.model`.
    - `layer_mappings`: Liste von Dicts mit `ui_layer_id`, `model_layer_id`, `display_name`.
  - `ui`:
    - `title`, `language` aus `cfg.ui`.
    - `layers`: Liste von Layer-Dicts mit
      - `id`, `order`, `button_label`, `title_bar_label`, `description`, `viz_preset_id`.
    - Zusätzliche Felder wie `metadata` werden hier nicht erzeugt.
  - `viz_presets`:
    - Liste von Dicts mit den Feldern
      - `id`, `layer_id`, `channels`, `k`, `blend_mode`, `overlay`, `alpha`, `cmap`.

---

### 2.4 `config/migrations.py`

- Verantwortlichkeit:
  - Enthält die Logik zur Migration von älteren Config-Versionen auf die aktuelle Struktur.
  - Arbeitet ausschließlich auf rohen Dicts, nicht auf Dataclasses.

#### 2.4.1 `migrate_config(raw_dict: Dict[str, Any]) -> Dict[str, Any]`

- Einziger aktuell genutzter Einstiegspunkt für Migrationen.
- Verhalten:
  - Liest die aktuelle Version aus `raw_dict.get("version", "1.0")`.
  - Loggt die gefundene Version (`"Config-Version: ..."`).
  - Wenn die Version `"1.0"` ist:
    - Wird das Dict unverändert zurückgegeben (aktuelle Zielversion).
  - Für andere Versionen ist derzeit keine aktive Migrationskette implementiert.
    - Der Code enthält kommentierte Beispiele, wie zukünftige Migrationen aussehen könnten.
    - Bei unbekannter Version wird eine Warnung geloggt, das Dict aber trotzdem zurückgegeben.
- `migrate_config` wird aus `load_config()` und `load_raw_config_dict()` heraus immer vor der Weiterverarbeitung des Dicts aufgerufen.

---

### 2.5 `config/exhibit_config.json`, Backup und Lock-Datei

- `exhibit_config.json`:
  - JSON-Datei, die die komplette `ExhibitConfig` in einer für Menschen lesbaren Form enthält.
  - Wird von `config.service` gelesen und beschrieben; andere Code-Stellen greifen nicht direkt über `open`/`json` darauf zu.
- `exhibit_config.json.backup`:
  - Kopie der letzten gültigen Konfiguration.
  - Wird vor dem Schreiben neuer Daten angelegt und kann bei Schreibfehlern zur Wiederherstellung dienen.
- `exhibit_config.json.lock`:
  - Lock-Datei, die während eines Schreibvorgangs existiert.
  - Wird von `FileLock` benutzt, um konkurrierende Schreibzugriffe zu koordinieren.

---

## 3. Datenmodell und JSON-Struktur

### 3.1 Wurzelobjekt `ExhibitConfig`

- Oberste Ebene der Konfiguration bildet `ExhibitConfig` ab.
- Entsprechende Struktur im JSON:
  - `version: str` – z.B. `"1.0"`.
  - `exhibit_id: str` – z.B. `"cnn_museum_01"`.
  - `model: { ... }` – modellbezogene Einstellungen.
  - `ui: { ... }` – UI-bezogene Einstellungen.
  - `viz_presets: [ ... ]` – Liste von Visualisierungspresets.
- `version` steuert, wie `migrate_config` das Dict behandeln würde, wenn künftig Migrationen hinzukommen.

### 3.2 Modellkonfiguration (`model` / `ModelConfig` & `ModelLayerMapping`)

- JSON-Teil `model`:
  - `name`: Modellname, aktuell `"resnet18"`.
  - `weights`: Name/Quelle der Pretrained-Gewichte, z.B. `"imagenet"`.
  - `layer_mappings`: Liste von Mappings zwischen UI- und Modell-Layern.
- Jedes Element in `layer_mappings` entspricht einem `ModelLayerMapping`:
  - `ui_layer_id`: ID eines UI-Layers (z.B. `"layer1_conv1"`).
  - `model_layer_id`: technischer Layername im CNN (z.B. `"conv1"`).
  - `display_name`: lesbarer Anzeigename.
- Die Layer-Mappings erlauben es, UI-Layer eindeutig mit den entsprechenden internen Modell-Schichten zu verknüpfen.

### 3.3 UI-Konfiguration (`ui` / `ExhibitUIConfig` & `LayerUIConfig`)

- JSON-Teil `ui` strukturiert die Darstellung der Kino- und Admin-Views.
- Felder auf `ui`-Ebene:
  - `title`: globaler Titel, der z.B. in der Kino-View oben angezeigt wird.
  - `language`: Sprachcode, z.B. `"de"`.
  - `layers`: Liste der UI-Layer-Objekte.
- Struktur eines UI-Layers (entsprechend `LayerUIConfig`):
  - `id`: interne ID des Layers.
  - `order`: Ordnungszahl für die Sortierung der Layer in der UI.
  - `button_label`: Text für den Layer-Button.
  - `title_bar_label`: Text für die Titelleiste bei aktivem Layer.
  - `description`: erläuternder Fließtext.
  - `viz_preset_id`: ID eines zugeordneten `VizPreset`.
- In der rohen JSON-Struktur können zusätzliche Felder wie `metadata` vorhanden sein, die von den Dataclasses nicht abgebildet werden:
  - `metadata`: optionales Objekt pro Layer.
  - `metadata.favorites`: Liste von Favoriten, wie sie in der Feature-View genutzt werden (Namen und Presets für UI-spezifische Voreinstellungen).
  - Diese Felder werden in `_from_dict` bewusst ignoriert, sind aber im rohen Dict über `load_raw_config_dict()` verfügbar.

### 3.3.1 Modell-Layer-basierter Content (`ui.model_layers`)

- Zusätzlich zu den klassischen UI-Layern (`ui.layers`) gibt es eine explizite Content-Struktur pro Modell-Layer:
  - In `config.models` als Dataclass `ModelLayerContent` modelliert.
  - In `ExhibitUIConfig` als Mapping `model_layers: Dict[str, ModelLayerContent]` geführt.
- JSON-Struktur:
  - `ui.model_layers` ist ein Objekt, dessen Keys `model_layer_id`-Strings sind (z.B. `"conv1"`, `"layer1"`, `"layer2"`, ...).
  - Jeder Eintrag hat die Form:
    - `title: str` – Seitentitel für diesen Modell-Layer (z.B. "Layer 1 – Kanten").
    - `subtitle: str | null` – kurzer Untertitel, der u.a. in der Kameraansicht der Kino-View verwendet wird.
    - `description: str` – längerer Erklärungstext für Laien.
- Nutzung:
  - **Content-Editor** (`ui_admin_streamlit/content_view.py`):
    - Bietet eine Unterseite pro Modell-Layer an, auf der genau diese Felder gepflegt werden.
    - Änderungen werden per `save_config(cfg)` wieder in `ui.model_layers` geschrieben.
  - **Kino-View** (`ui_kino_kivy/app.py`):
    - Liest für jede Modell-Layer-Seite den Content über `config.service.get_model_layer_content(cfg, model_layer_id)`.
    - Verwendet `subtitle` und `description` für die rechte Spalte der Kivy-Oberfläche.
- Fallback-Regeln:
  - Wenn ein `model_layer_id`-Eintrag in `ui.model_layers` fehlt, gibt `get_model_layer_content` einen Default zurück:
    - `title = model_layer_id`.
    - `description = "Noch nicht konfiguriert"`.
  - Dadurch bleibt das System robust, auch wenn Content für einzelne Layer noch nicht gepflegt wurde.

### 3.3.2 Modell-Layer-basierte Favoriten-Sicht (`get_favorites_for_model_layer`)

- Zusätzlich zu `metadata.favorites` auf UI-Layer-Ebene stellt `config.service` eine Hilfsfunktion bereit:
  - `get_favorites_for_model_layer(cfg: ExhibitConfig, model_layer_id: str, max_count: int = 3) -> List[Dict[str, Any]]`.
- Verhalten:
  - Durchsucht alle `cfg.ui.layers` und deren `metadata.favorites`.
  - Filtert Favoriten so, dass `fav["preset"].get("model_layer_id") == model_layer_id` gilt.
  - Beschränkt die Ergebnisliste auf `max_count` Elemente (Standard: 3).
- Nutzung:
  - **Kino-View**: Zeigt pro Modell-Layer-Seite bis zu drei Favoriten an, ohne die Rohstruktur im UI neu interpretieren zu müssen.
  - **Feature-View**: Kann weiterhin direkt mit `metadata.favorites` arbeiten; die neue Hilfsfunktion ändert das bestehende Schema nicht, sondern ergänzt nur eine lesende Sicht.

---

## 4. Service-Layer: Laden, Speichern, Validierung

### 4.1 Laden als Dataclasses: `load_config()`

- Haupt-Einststiegspunkt für alle Teile des Systems, die eine typisierte `ExhibitConfig` benötigen.
- Zusammenfassung des Ablaufs:
  1. Wenn `exhibit_config.json` noch nicht existiert, wird eine Default-Config mit `_default_config_dict()` erzeugt und über `save_config_dict` geschrieben.
  2. Die Datei wird per `json.load` eingelesen.
     - Bei Parsing- oder IO-Fehlern wird ein Fallback über `_from_dict(_default_config_dict())` verwendet.
  3. Das geladene Dict wird an `migrate_config` übergeben, um es ggf. auf die aktuelle Version zu heben.
  4. Anschließend wird das Dict mit `_from_dict` in eine `ExhibitConfig` konvertiert.
  5. `validate_config` prüft die typisierte Config und gibt eventuelle Fehlermeldungen zurück, die geloggt werden.
  6. Die (ggf. fehlerhafte, aber deserialisierte) `ExhibitConfig` wird an den Aufrufer zurückgegeben.

### 4.2 Laden als Roh-JSON: `load_raw_config_dict()`

- Dient vor allem für Anwendungsfälle, bei denen auch Felder genutzt werden sollen, die in den Dataclasses nicht modelliert sind (z.B. `ui.layers[].metadata`).
- Ablauf:
  1. Falls `CONFIG_PATH` nicht existiert, wird eine Default-Config erstellt und gespeichert.
  2. Das JSON wird mittels `json.load` geladen.
     - Bei Fehlern beim Laden wird `_default_config_dict()` als Fallback verwendet.
  3. Auf das geladene Dict wird `migrate_config` angewendet.
  4. Das migrierte Dict wird unverändert an den Aufrufer zurückgegeben.
- Wird u.a. von der Feature-View genutzt, um Favoritenstrukturen (`metadata.favorites`) zu lesen und zu modifizieren.

### 4.3 Speichern und File-Locking (`save_config()`, `save_config_dict()`, `save_raw_config_dict()`)

- `save_config(cfg: ExhibitConfig)`:
  - Wandelt eine `ExhibitConfig` mit `_to_dict` in ein Dict um und ruft `save_config_dict(data)` auf.
- `save_config_dict(data: Dict[str, Any])`:
  - Zuständig für den eigentlichen Schreibvorgang nach `exhibit_config.json`.
  - Nutzt `FileLock`, um konkurrierende Schreibzugriffe über `exhibit_config.json.lock` zu synchronisieren.
  - Erstellt vor dem Überschreiben, falls möglich, ein Backup der bestehenden Config in `exhibit_config.json.backup`.
  - Schreibt das übergebene Dict als formatiertes JSON (UTF-8, `ensure_ascii=False`, `indent=2`).
  - Bei Fehlern während des Schreibens versucht die Funktion, das Backup zurückzuspielen.
- `save_raw_config_dict(data: Dict[str, Any])`:
  - Delegiert direkt an `save_config_dict`.
  - Wird z.B. von der Feature-View genutzt, um nach Änderungen am rohen Config-Dict (inkl. `metadata`) die Datei zu aktualisieren.

### 4.4 Validierung: `validate_config()`

- `validate_config` wird nach dem Deserialisieren einer `ExhibitConfig` in `load_config()` aufgerufen.
- Die Funktion prüft insbesondere:
  - Ob mindestens ein UI-Layer existiert.
  - Ob jede `viz_preset_id` eines Layers auf ein existierendes Preset verweist.
  - Ob der Modellname (`cfg.model.name`) unterstützt wird (derzeit nur `"resnet18"`).
- Fehler werden als Strings gesammelt und in der Log-Ausgabe als Warnungen ausgegeben.
- Die Config wird ungeachtet der Validierungsfehler an den Aufrufer zurückgegeben; die Validierung dient primär der Früherkennung von Inkonsistenzen.

---

## 5. Migrationsmechanismus und Versionierung

### 5.1 `migrate_config()` – aktueller Stand

- `migrate_config(raw_dict)` ist die zentrale Funktion für alle Versionsmigrationen der Config.
- Verhalten im Ist-Zustand:
  - Liest die Version aus `raw_dict["version"]` bzw. setzt sie auf `"1.0"`, falls nicht vorhanden.
  - Loggt die gefundene Version.
  - Wenn die Version `"1.0"` ist, wird das Dict unverändert zurückgegeben.
  - Für andere Versionen existiert aktuell keine aktive Migrationslogik:
    - Der Code enthält kommentierte Beispiel-Aufrufe für zukünftige Migrationen.
    - Bei einer unbekannten Version wird eine Warnung geloggt und das Dict dennoch zurückgegeben.
- Sowohl `load_config()` als auch `load_raw_config_dict()` rufen `migrate_config` immer vor der weiteren Verarbeitung auf.

---

## 6. Zusammenspiel mit anderen Modulen und Datenflüsse

### 6.1 Typischer Flow: Admin-Panel (Feature-View) liest & schreibt Config

- Die Feature-View im Admin-Panel nutzt die Config-Schicht in zwei Formen:
  1. **Typisierte Sicht:**
     - `cfg = load_config()` liefert eine `ExhibitConfig`.
     - Daraus werden z.B. die UI-Layer (`cfg.ui.layers`) gelesen und nach `order` sortiert.
  2. **Rohe Sicht:**
     - `raw_cfg = load_raw_config_dict()` lädt das zugrundeliegende JSON als Dict.
     - Auf Basis dieses Dicts werden z.B. `metadata.favorites` pro UI-Layer gelesen und modifiziert.
- Nach Änderungen (z.B. Anlegen, Aktualisieren oder Löschen von Favoriten) wird das rohe Dict über `save_raw_config_dict(raw_cfg)` wieder in `exhibit_config.json` geschrieben.
- Während des Schreibens sorgt `save_config_dict` für Locking und Backup-Erstellung.

### 6.2 Typischer Flow: Kino-View liest Config

- Die Kivy-basierte Kino-View nutzt die Config read-only.
- Beim Start der Anwendung wird `load_config()` aufgerufen.
- Aus der resultierenden `ExhibitConfig` werden z.B. verwendet:
  - `cfg.ui.title` für den Titel der Ausstellung.
  - `cfg.ui.layers`, sortiert nach `order`, um die Button-Leiste unten und den initialen aktiven Layer zu bestimmen.
  - `LayerUIConfig.description` und `title_bar_label` für die rechte Textspalte bzw. die Titelzeile.
  - `cfg.viz_presets` und die jeweiligen `viz_preset_id` der Layer, um passende Visualisierungsvoreinstellungen auszuwählen.
- Die Kino-View schreibt die Config-Datei nicht; Änderungen an der Konfiguration erfolgen ausschließlich über Admin-Werkzeuge oder direkte Bearbeitung der JSON-Datei.

### 6.3 Interne Abhängigkeiten innerhalb der Config-Schicht

- `config/service.py` hängt ab von:
  - `config/models.py` (`ExhibitConfig`, `ExhibitUIConfig`, `ModelConfig`, `ModelLayerMapping`, `LayerUIConfig`, `VizPreset`).
  - `config/migrations.py` (`migrate_config`).
  - Standardbibliothek (`json`, `logging`, `shutil`, `time`, `pathlib`).
- `config/migrations.py`:
  - Arbeitet nur mit rohen Dicts und benötigt keine Dataclasses.
  - Verwendet Logging für Diagnose von Versions- und Migrationszuständen.
- `config/models.py`:
  - Enthält ausschließlich Dataclasses und Typdefinitionen; keine IO- oder Logik-Funktionen.

---

## 7. Zusammenfassung des Ist-Zustands der Config-Schicht

- Die Config-Schicht stellt eine zentrale, dateibasierte Konfiguration für das Exponat bereit, basierend auf `config/exhibit_config.json`.
- `config/models.py` definiert das typisierte Datenmodell (`ExhibitConfig`, `ModelConfig`, `ExhibitUIConfig`, `LayerUIConfig`, `VizPreset`, `ModelLayerMapping`).
- `config/service.py` kümmert sich um Laden, Speichern, Validierung und Schutzmechanismen (File-Lock, Backup) und bietet sowohl typisierte als auch rohe Zugriffswege.
- `config/migrations.py` kapselt den Migrationsmechanismus, der aktuell auf Version `"1.0"` ohne aktive Strukturänderungen ausgelegt ist.
- Kino-View und Admin-Panel greifen auf diese einheitliche Quelle zu und nutzen die Config, um UI-Struktur, Texte und Visualisierungen konsistent auszulesen und – im Fall des Admin-Panels – zu verändern.
