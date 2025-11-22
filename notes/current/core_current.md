# Core-Schicht – aktueller Stand

## 1. Rolle der Core-Schicht im Gesamtsystem

- Die Core-Schicht kapselt die **modellnahe Logik** des Exponats:
  - Laden und Ausführen des CNN (aktuell ResNet18 mit ImageNet-Gewichten).
  - Registrieren von Hooks auf ausgewählten Layern und Sammeln der Aktivierungen.
  - Umwandeln von Aktivierungen + Visualisierungsparametern (`VizPreset`) in darstellbare RGB-Bilder.
- Sie bildet die **Brücke** zwischen:
  - der Konfiguration (`config`-Package, v.a. `ModelConfig`, `ModelLayerMapping`, `VizPreset`),
  - und den UIs (`ui_admin_streamlit` / `ui_kino_kivy`), die diese Fähigkeiten nutzen.
- Im Gegensatz zur Config-Schicht:
  - kennt `core` konkrete Modell-Implementierungen (hier: PyTorch ResNet18) und Bilddaten,
  - führt tatsächliche numerische Berechnungen (Forward-Pass, Normalisierung, Colormaps) aus,
  - ist weitgehend UI-agnostisch – sie trifft keine Annahmen über Streamlit oder Kivy.

### 1.1 Verortung im Projekt

- Pfad: `core/` im Projektwurzelverzeichnis.
- Zentrale Dateien:
  - `core/model_engine.py` – Model-Engine für CNN-Inferenz und Layer-Aktivierungen.
  - `core/viz_engine.py` – Visualisierungs-Engine für Aktivierungen.
  - `core/__init__.py` – aktuell leer, dient nur als Package-Marker.
- Wichtige Konsumenten:
  - **Feature-View** (`ui_admin_streamlit/feature_view`):
    - Erzeugt eine `ModelEngine`- und `VizEngine`-Instanz im Streamlit-Session-State (`state.init_state()`).
    - Nutzt `ModelEngine.run_inference()` und `VizEngine.visualize()` zur Snapshot-Analyse.
  - **Kino-View** (`ui_kino_kivy`):
    - Nutzt `ModelEngine` und `VizEngine` für die Live-Visualisierung von Kamera-Snapshots.
  - **Kamera-Service** (`core.camera_service`):
    - Zentraler Zugriffspunkt für Kamerafunktionen, wird sowohl von der Feature-View
      als auch vom Kino-View verwendet.

---

## 2. Dateien und Verantwortlichkeiten im `core`-Package

### 2.1 `core/model_engine.py`

- **Verantwortlichkeit:**
  - Kapselt das Laden und Ausführen des CNN-Modells.
  - Registriert Forward-Hooks auf ausgewählten Layern und stellt Aktivierungen als NumPy-Arrays bereit.
  - Bietet eine Mapping-Schicht zwischen UI-Layer-Begriffen und konkreten Modell-Layern.

#### 2.1.1 Zentrale Klasse: `ModelEngine`

Konstruktor-Signatur (vereinfacht):

- `ModelEngine(model_cfg: ModelConfig, active_layer_ids: Optional[List[str]] = None, device: str = "cpu")`

Wichtige Aspekte der Initialisierung:

1. **Modell laden**
   - Unterstütztes Modell (Ist-Stand):
     - `model_cfg.name == "resnet18"` → lädt `models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)`.
   - Für andere Namen: `ValueError("Unbekanntes Modell: ...")`.
   - Modell wird in den `eval()`-Modus versetzt und auf das angegebene Device übertragen (`cpu` standardmäßig).

2. **Layer-Registry aufbauen**
   - Erzeugt `self.layer_map: Dict[str, nn.Module]` aus `self.model.named_modules()`.
   - Key = technische Layer-Bezeichnung aus PyTorch (z.B. `"conv1"`, `"layer1.0.conv1"`, …).
   - Dient als Nachschlagewerk zum Setzen von Hooks und zur Validierung von `active_layer_ids`.

3. **UI-Layer → Model-Layer-Mapping**
   - Erwartet `model_cfg.layer_mappings: List[ModelLayerMapping]` aus `config.models`.
   - Baut ein internes Mapping `self._ui_to_model_map: Dict[str, str]`, das z.B. `"layer1_conv1"` auf `"layer1.0.conv1"` abbilden kann.
   - Aktueller Ist-Stand laut Default-Config: `layer_mappings` ist leer → Mapping ist derzeit faktisch ein No-Op.

4. **Aktive Layer bestimmen**
   - Wenn `active_layer_ids` **nicht** übergeben werden:
     - Default-Liste: `["conv1", "layer1", "layer2", "layer3", "layer4"]`.
   - Diese Liste bestimmt, auf welche Layer Forward-Hooks registriert werden.

5. **Aktivierungsspeicher und Hooks**
   - `self._activations: Dict[str, np.ndarray]` hält die letzten Aktivierungen für die aktiven Layer.
   - `_make_hook(layer_id)` erzeugt einen Forward-Hook, der `output.detach().cpu().numpy()` in `_activations[layer_id]` schreibt.
   - `_register_hooks()` iteriert über `self.active_layer_ids`:
     - Prüft, ob `layer_id` in `self.layer_map` existiert, sonst `ValueError`.
     - Registriert Forward-Hook auf dem entsprechenden PyTorch-Modul und speichert das Hook-Handle in `self._hooks`.

6. **Preprocessing-Pipeline**
   - `self.preprocess = T.Compose([...])` mit Schritten:
     - `ToTensor()` (PIL → Tensor, skaliert auf [0,1]).
     - `Resize((224, 224))` (fixe Zielgröße für ResNet18).
     - `Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])` (ImageNet-Standard).
   - Erwartetes Input-Format: `np.ndarray` (H, W, 3), RGB, `uint8` oder float (wird auf `uint8` gecastet).

#### 2.1.2 Öffentliche API von `ModelEngine`

1. `get_available_layers() -> List[str]`
   - Gibt alle Layernamen zurück, die im PyTorch-Modell existieren (Keys von `self.layer_map`).
   - Wird aktuell im UI nicht direkt genutzt, eignet sich aber zur Diagnose oder für spätere dynamische UIs.

2. `get_active_layers() -> List[str]`
   - Gibt die Liste der `active_layer_ids` zurück (d.h. jene Layer, auf die Hooks gesetzt wurden).
   - In der Feature-View: dient als Auswahlbasis für den Dropdown der Modell-Layer.

3. `get_model_layer_id(ui_layer_id: str) -> Optional[str]`
   - Löst eine UI-Layer-ID in eine Modell-Layer-ID auf:
     - Wenn ein Eintrag in `self._ui_to_model_map` existiert → gibt diesen zurück.
     - Sonst Fallback: gibt `ui_layer_id` unverändert zurück.
   - Ermöglicht, UIs gegen UI-spezifische Bezeichner zu bauen, ohne PyTorch-Layernamen kennen zu müssen.
   - Aktueller Ist-Stand: Mapping-Tabelle ist leer, daher entspricht Rückgabewert praktisch dem Eingabewert.

4. `run_inference(np_image: np.ndarray) -> Dict[str, np.ndarray]`
   - Führt einen Forward-Pass durch und liefert ein Dict `layer_id → activation_numpy_array`.
   - Ablauf:
     1. Löscht alte Aktivierungen: `self._activations.clear()`.
     2. Stellt sicher, dass das Bild `uint8` ist (sonst Clip + Cast).
     3. Wandelt `np_image` via `PIL.Image.fromarray` in ein PIL-Image um.
     4. Wendet `self.preprocess` an, fügt Batch-Dimension hinzu (`unsqueeze(0)`), verschiebt auf Device.
     5. Führt Forward-Pass mit `torch.no_grad()` aus (`_ = self.model(x)`).
     6. Danach sind alle registrierten Hooks getriggert worden und haben Einträge in `self._activations` geschrieben.
     7. Gibt eine Kopie von `self._activations` zurück (`dict` von `layer_id` → `np.ndarray`).
   - Rückgabeformate pro Layer (abhängig vom Modell):
     - typischerweise `shape: (1, C, H, W)`.

5. `get_activation(layer_id: str) -> np.ndarray | None`
   - Liefert die letzte gespeicherte Aktivierung für einen gegebenen Layer.
   - Nutzt intern `self._activations.get(layer_id)` (kann `None` zurückgeben, wenn noch keine Inferenz gelaufen ist oder Layer nicht aktiv war).

6. Selbsttest-Bereich (nur für manuelle Tests):
   - Im `if __name__ == "__main__":`-Block wird eine einfache Inferenz auf einem weißen Dummy-Bild ausgeführt und die Shapes der Aktivierungen geloggt.
   - Dient als Low-Level-Sanity-Check ohne Abhängigkeit zu den UIs.

#### 2.1.3 Nutzung und Verhalten in UIs

- **Feature-View (`ui_admin_streamlit.feature_view.state`)**:
  - `init_state()` erzeugt einmalig pro Streamlit-Session eine `ModelEngine`-Instanz:
    - `ModelConfig(name="resnet18", weights="imagenet")` (ohne explizite `layer_mappings`).
    - `active_layer_ids` werden per Default gesetzt (`"conv1"`–`"layer4"`).
  - `view.render()` ruft aktuell direkt `model_engine.run_inference(snapshot)` auf,
    ohne den vorgesehenen Aktivierungs-Cache zu verwenden.
  - Die Aktivierung für den aktuell gewählten Modell-Layer wird extrahiert und an `VizEngine` übergeben.

- **Kino-View**:
  - Nutzt `ModelEngine` und `VizEngine` für die Live-Visualisierung von Kamera-Snapshots.
  - `ModelEngine` wird mit der aktiven Kamera-ID und vordefinierten Layern (`"conv1"`–`"layer4"`) instanziiert.
  - Bei jedem neuen Kamerabild wird automatisch `run_inference()` aufgerufen.
  - Die Visualisierung nutzt die vordefinierten `VizPreset`-Parameter aus der Config.

---

### 2.2 `core/viz_engine.py`

- **Verantwortlichkeit:**
  - Konvertiert Aktivierungen eines CNN-Layers in ein darstellbares RGB-Bild.
  - Interpretiert ein `VizPreset` aus `config.models` und setzt dessen Parameter um:
    - Auswahl und Kombination von Featuremaps (Channels),
    - Normalisierung auf 0–255,
    - Auswahl/Anwendung einer Colormap,
    - optionales Overlay auf das Originalbild.

#### 2.2.1 Zentrale Klasse: `VizEngine`

Öffentliche Methode:

- `visualize(activation: np.ndarray, preset: VizPreset, original: np.ndarray | None = None) -> np.ndarray`

Erwartete Inputs:

- `activation`: NumPy-Array der Form `(1, C, H, W)`; entspricht typischerweise der Ausgabe eines CNN-Layers.
- `preset`: Instanz von `VizPreset` (aus `config.models`) mit mindestens:
  - `channels`: Liste von Channel-Indizes oder der String `"topk"`.
  - `k`: Anzahl zu berücksichtigender Featuremaps bei `"topk"`.
  - `blend_mode`: `"mean"`, `"max"`, `"sum"`, `"weighted"`, …
  - `overlay`: Bool, ob Overlay genutzt wird.
  - `alpha`: Transparenz für Overlay.
  - `cmap`: Name der Colormap oder Farbrichtung (z.B. `"viridis"`, `"red"`).
- `original`: Optionales Originalbild (H, W, 3) als `np.uint8` (z.B. Kamerasnapshot), für Overlays.

Rückgabe:

- RGB-Bild (`np.ndarray`, `dtype=np.uint8`, Shape HxWx3), darstellbar in UIs.

Ablauf innerhalb von `visualize` (High-Level):

1. **Featuremaps auswählen** – `_select_featuremaps(activation, preset)`
   - Erwartet `activation.shape == (1, C, H, W)`.
   - Wenn `preset.channels == "topk"`:
     - Bestimmt Varianz pro Channel über alle Raumpositionen: `activation.reshape(C, -1).var(axis=1)`.
     - Wählt die `k` Channels mit größter Varianz (Standard `k=3`, falls `preset.k` `None`).
   - Wenn `preset.channels` eine Liste ist:
     - Baut `idx_list = [i for i in preset.channels if 0 <= i < C]`.
   - Rückgabe: Array der Form `(N_selected, H, W)`.

2. **Featuremaps reduzieren** – `_reduce_featuremaps(fmap, preset)`
   - Input: `fmap` Shape `(N, H, W)` oder `(H, W)`.
   - Ziel: 2D-Karte `(H, W)`.
   - Verhalten je nach `preset.blend_mode`:
     - `"mean"`: Mittelwert über Channels.
     - `"max"`: Maximum pro Pixelposition.
     - `"sum"`: Summe.
     - `"weighted"`: aktuell einfache Gleichverteilung (Gewichte = 1/N, mittels `np.tensordot`).
     - Fallback bei unbekanntem Modus: `mean`.
   - Wenn `fmap.ndim == 2`: wird unverändert zurückgegeben.

3. **Normalisieren** – `_normalize(fmap)`
   - Ziel: robustes Mapping auf `uint8` 0–255.
   - Edge-Case-Behandlung:
     - `NaN`-Werte → via `np.nan_to_num(..., nan=0.0)` auf 0 gesetzt.
     - `Inf`-Werte:
       - Bestimmt `valid_mask = ~np.isinf(fmap)`.
       - Wenn es valide Werte gibt:
         - Clip auf `[valid_min, valid_max]`.
       - Wenn alle Werte `inf` sind → setzt ganze Map auf 0.
   - Min-Max-Normalisierung:
     - Zieht `fmap.min()` ab.
     - Teilt durch `maxv = fmap.max()` (falls `maxv > 0`, sonst unverändert).
     - Skaliert mit 255 und castet auf `np.uint8`.

4. **Colormap anwenden** – `_apply_colormap(gray, preset)`
   - Input: 2D Grauwert-Array 0–255 (`uint8`).
   - Unterstützte Modi:
     - Einfache RGB-Highlights:
       - `"red"` / `"r"`: schreibt `gray` in roten Kanal (`rgb[:, :, 2]`).
       - `"green"` / `"g"`: schreibt `gray` in Grün.
       - `"blue"` / `"b"`: schreibt `gray` in Blau.
     - OpenCV-Colormaps (via `cv2.applyColorMap`):
       - `"viridis"`, `"magma"`, `"inferno"`, `"plasma"`, `"jet"`.
     - Fallback: `COLORMAP_VIRIDIS`.

5. **Overlay** – `_overlay(heatmap_rgb, original, alpha)`
   - Wird in `visualize` nur ausgeführt, wenn `preset.overlay == True` **und** `original` nicht `None` ist.
   - Ablauf:
     - Bestimmt Höhe/Breite aus `heatmap_rgb`.
     - Skaliert `original` via `cv2.resize(original, (W, H))`.
     - Verwendet `cv2.addWeighted(original_resized, 1 - alpha, heatmap_rgb, alpha, 0)`
       zur gewichteten Überlagerung.
   - Erwartet beide Inputs als HxWx3 `uint8`.

6. **Selbsttest-Bereich**
   - Im `if __name__ == "__main__":`-Block wird ein Dummy-Test ausgeführt:
     - Zufallsaktivierungen `(1, 5, 20, 20)`.
     - Einfaches `VizPreset` mit zwei Channels.
     - Aufruf von `visualize` und Ausgabe der Resultat-Shape.
   - Dient der isolierten Überprüfung der Engine ohne UIs.

#### 2.2.2 Nutzung und Verhalten in UIs

- **Feature-View**:
  - Erzeugt temporäre `VizPreset`-Instanzen direkt im Code (nicht zwingend identisch mit `viz_presets` aus der JSON):
    - Oberes Bild: Einzel-Channel (aktuell gewählter Slider-Channel).
    - Unteres Bild: kombinierte Channels (Liste oder Top-K).
  - Ruft `viz_engine.visualize(activation=act, preset=preset, original=snapshot_or_none)`
    und zeigt das zurückgegebene Bild mit `st.image` (teilweise nach Resize per `cv2.resize`).
  - Nutzt folgende Preset-Felder aktiv:
    - `channels`, `k`, `blend_mode`, `overlay`, `alpha`, `cmap`.

- **Kino-View**:
  - Nutzt `ModelEngine` und `VizEngine` für die Live-Visualisierung von Kamera-Snapshots.
  - `ModelEngine` wird mit der aktiven Kamera-ID und vordefinierten Layern (`"conv1"`–`"layer4"`) instanziiert.
  - Bei jedem neuen Kamerabild wird automatisch `run_inference()` aufgerufen.
  - Die Visualisierung nutzt die vordefinierten `VizPreset`-Parameter aus der Config.

---

### 2.3 `core/camera_service.py`

- **Verantwortlichkeit:**
  - Kapselt alle generischen Kamera-Funktionen auf Basis von OpenCV.
  - Dient als einzige Stelle im Projekt, an der direkt `cv2.VideoCapture` verwendet wird.
  - Wird von `ui_admin_streamlit.feature_view.camera` (Wrapper) und vom Kivy-Kino-View
    (`ui_kino_kivy/app.py`) verwendet.

- Öffentliche API:
  - `detect_cameras(max_tested: int = 5) -> list[int]`
    - Testet die Kamera-IDs `0..max_tested-1` mit `cv2.VideoCapture`.
    - Gibt eine Liste der IDs zurück, die erfolgreich geöffnet werden konnten.
    - Loggt Fehler auf Debug-Level, bricht aber die Schleife nicht ab.
  - `take_snapshot(cam_id: int, timeout: float = 5.0) -> tuple[np.ndarray | None, str]`
    - Versucht, eine Kamera mit der angegebenen ID zu öffnen und genau ein Bild zu lesen.
    - Rückgabe:
      - Bei Erfolg: `(image_rgb, "")` mit `image_rgb` als `np.ndarray` (H x W x 3, RGB).
      - Bei Fehler: `(None, "Fehlerbeschreibung")`.
    - Wichtige Fehlerfälle:
      - Kamera kann nicht initialisiert werden.
      - Kamera ist nicht geöffnet oder verweigert Zugriff.
      - Timeout beim Öffnen.
      - Lesen des Frames schlägt fehl oder liefert kein Bild.
      - Farbkonvertierung von BGR nach RGB schlägt fehl.

- Konsumenten (Stand dieser Task-Umsetzung):
  - `ui_admin_streamlit/feature_view/camera.py` re-exportiert `detect_cameras` und
    `take_snapshot` und enthält keine eigene Kameralogik mehr.
  - `ui_kino_kivy/app.py` ruft `detect_cameras` zum Finden einer geeigneten Kamera-ID auf
    und verwendet `take_snapshot` im Live-Modus, um fortlaufend Bilder für die
    Modellinferenz und Visualisierung zu liefern.

---

## 3. Interne Abhängigkeiten innerhalb der Core-Schicht

- `model_engine.py` und `viz_engine.py` sind fachlich weitgehend unabhängig:
  - `ModelEngine` kennt nichts von Visualisierung.
  - `VizEngine` kennt nichts von PyTorch oder dem konkreten Modell – nur NumPy-Arrays.
- Gemeinsame Abhängigkeit: `config.models`:
  - `ModelEngine` nutzt `ModelConfig` und `ModelLayerMapping`.
  - `VizEngine` nutzt `VizPreset`.
- Datenfluss innerhalb von `core` (gedachte Standard-Pipeline):
  1. Bild (`np.ndarray` HxWx3) wird an `ModelEngine.run_inference()` übergeben.
  2. Ergebnis ist ein Dict `layer_id → activation` (`np.ndarray`, typ. `(1, C, H, W)`).
  3. UIs wählen daraus einen Layer und ggf. Channels aus.
  4. `VizEngine.visualize(activation, preset, original)` baut daraus ein darstellbares RGB-Bild.

Es gibt **keinen direkten Aufruf** von `VizEngine` aus `ModelEngine` oder umgekehrt – die Kopplung
findet ausschließlich in den UIs bzw. höheren Schichten statt.

---

## 4. Externe Abhängigkeiten zu anderen Projektteilen

### 4.1 Abhängigkeit zur Config-Schicht (`config`)

- `core/model_engine.py`:
  - `from config.models import ModelConfig, ModelLayerMapping`
  - Erwartet, dass `ModelConfig` folgende Felder bereitstellt:
    - `name: str` – Modellname (aktuell `"resnet18"`).
    - `weights: str` – Kennzeichnung der Gewichte (z.B. `"imagenet"`).
    - `layer_mappings: List[ModelLayerMapping]` – optionaler Pool von UI↔Modell-Layer-Zuordnungen.
  - `ModelLayerMapping` wird genutzt, um `ui_layer_id` → `model_layer_id` zu mappen.

- `core/viz_engine.py`:
  - `from config.models import VizPreset`
  - Nutzt Felder:
    - `channels`, `k`, `blend_mode`, `overlay`, `alpha`, `cmap`.
  - Erwartet, dass `channels` entweder Liste von `int` oder String `"topk"` ist.

- **Konsequenz:**
  - Änderungen am Datamodell in `config.models` wirken direkt auf die Core-Schicht.
  - Der Kern ist jedoch relativ robust, solange Feldnamen und Typen kompatibel bleiben.

### 4.2 Abhängigkeiten zu UIs (`ui_admin_streamlit`, `ui_kino_kivy`)

- `core` selbst importiert keine UI-Module.
- UIs importieren `core`:

  - **Feature-View (`ui_admin_streamlit/feature_view/state.py`)**:
    - `from core.model_engine import ModelEngine`
    - `from core.viz_engine import VizEngine`
    - Erzeugt Instanzen für die Dauer einer Streamlit-Session.

  - **Kino-View**:
    - Stand heute existiert keine direkte Importbeziehung.
    - Erwartbar ist ein zukünftiger Import in `ui_kino_kivy/app.py` oder einem separaten Modul
      für Live-Visualisierung.

- **Richtung der Abhängigkeiten:**
  - `ui_*` → `core` → `config`
  - Damit ist `core` eindeutig als (relativ) UI-unabhängige Mittelschicht positioniert.

### 4.3 Bibliotheken (technische Abhängigkeiten)

- `core/model_engine.py`:
  - `torch`, `torch.nn as nn`, `torchvision.transforms as T`, `torchvision.models`.
  - `numpy`.
  - `PIL.Image` (für das Preprocessing von NumPy-Bildern).

- `core/viz_engine.py`:
  - `numpy`.
  - `cv2` (OpenCV) für Colormaps, Resize und Alpha-Blending.

- `core/camera_service.py`:
  - `cv2` (OpenCV) für die Kamerasteuerung und Bildaufnahme.

Diese Bibliotheken müssen in der Laufzeitumgebung vorhanden sein, damit `core` funktioniert.

---

## 5. Datenflüsse mit den aktuellen UIs

### 5.1 Datenfluss: Snapshot-Analyse in der Feature-View (Ist-Stand)

1. **Setup (einmal pro Session)** – in `ui_admin_streamlit.feature_view.state.init_state()`:
   - `ModelEngine` wird mit Default-`ModelConfig` und Standard-Layern (`"conv1"`–`"layer4"`) instanziiert.
   - `VizEngine` wird instanziiert.

2. **Snapshot-Aufnahme** – in `feature_view.view.render()`:
   - Eine Kamera liefert ein RGB-Bild (`np.ndarray`, HxWx3, `uint8`).
   - Dieses Bild wird in `st.session_state.feature_snapshot` abgelegt.

3. **Inferenz (ohne Cache)**:
   - Bei jedem Render-Durchlauf mit vorhandenem Snapshot ruft das UI:
     - `acts = model_engine.run_inference(snapshot)`.
   - Rückgabe: Dict `layer_id → activation`.

4. **Layer- und Channel-Auswahl**:
   - UI wählt einen Modell-Layer (Dropdown über `model_engine.get_active_layers()`).
   - UI bestimmt Channels:
     - Entweder Einzel-Channel (Slider) oder Liste / Top-K.

5. **Visualisierung**:
   - `VizPreset` nur im UI erzeugt (nicht zwingend mit JSON-Presets identisch).
   - `viz_engine.visualize(activation=act, preset=preset, original=snapshot_or_none)`.
   - Ergebnisbilder werden nach Bedarf per OpenCV `resize` skaliert und über Streamlit angezeigt.

6. **Favoriten**:
   - Favoriten speichern nur Preset-Parameter (inkl. `model_layer_id`),
     aber `core` selbst kennt das Favoritenkonzept nicht.

### 5.2 Geplanter/angedeuteter Datenfluss mit der Kino-View

- Aus den bestehenden Komponenten und der Kino-View-Dokumentation ergibt sich folgendes erwartetes Zielbild:

  1. Ein Kameramodul (analog zur Feature-View) liefert kontinuierlich Frames.
  2. `ModelEngine` führt in regelmäßigen Abständen (oder bei Trigger) Inferenz aus.
  3. Aus der Config (`ExhibitConfig.viz_presets`) wird pro UI-Layer ein oder mehrere `VizPreset`s ausgewählt.
  4. `VizEngine` erzeugt daraus RGB-Bilder, die in Kivy als Texturen dargestellt werden.
  5. Die aktuell aktive Layer-Auswahl in der Kino-View bestimmt, welche Presets/Layer verwendet werden.

- Dieser Datenfluss ist aktuell **nicht implementiert**, aber `core` ist so entworfen,
  dass hierfür keine konzeptionellen Änderungen nötig wären.

---

## 6. Auffälligkeiten, Inkonsistenzen und offene Punkte (Ist-Sicht)

1. **Layer-Mappings werden noch nicht genutzt**
   - `ModelEngine` unterstützt explizit ein Mapping von UI-Layer-IDs auf Modell-Layer-IDs (`ModelLayerMapping`).
   - Die Default-Config definiert aktuell keine `layer_mappings` → in der Praxis wird dieser Mechanismus noch nicht verwendet.
   - In der Feature-View wird direkt mit Modell-Layernamen gearbeitet (Dropdown auf `get_active_layers()`).

2. **Aktivierungs-Cache existiert nur in der Feature-View, nicht in `ModelEngine` selbst**
   - `core` kennt keinen eigenen Cache; `run_inference` führt immer einen Forward-Pass aus.
   - Ein Cache ist in `feature_view.state.get_cached_activations` angelegt, wird dort aber aktuell nicht verwendet.
   - Aus Core-Sicht ist das okay (zustandsarm), aber im Gesamtsystem werden dadurch unnötige Inferenzläufe erzeugt.

3. **Gerätewahl (CPU/GPU) ist statisch**
   - `ModelEngine` erhält `device: str = "cpu"` als Parameter, aber Konsumenten nutzen bisher nur den Default.
   - Es gibt keinen Mechanismus im UI oder in der Config, um `cuda`/GPU zu wählen.

4. **Fehler-Handling und Rückgabewerte**
   - `run_inference` wirft Fehler bei ungültiger Konfiguration des Modells (z.B. unbekannter `model_cfg.name`).
   - Für das Bild-Preprocessing werden nicht alle Edge Cases explizit adressiert (z.B. falsche Shape, Graustufenbilder).
     - Annahme: UIs liefern immer RGB-Bilder (was in der Feature-View-Camera aktuell gegeben ist).

5. **Kopplung an ResNet18**
   - `ModelEngine` ist praktisch auf ResNet18 spezialisiert:
     - Hardcodiertes Laden aus `torchvision.models`.
     - Preprocessing fix auf 224x224 + ImageNet-Normalisierung.
   - Die Config erlaubt prinzipiell andere Modelle (über `ModelConfig.name`),
     aber `ModelEngine` reagiert darauf nur mit einem `ValueError`.

6. **Noch keine Integration in die Kino-View**
   - Trotz der klaren Rolle der Core-Schicht zwischen Config und UI nutzt die Kino-View aktuell noch keine `ModelEngine`/`VizEngine`.
   - Visualisierung in der Kino-View ist Stand heute ein Platzhalter.

7. **Package-API nicht explizit gemacht**
   - `core/__init__.py` ist leer → von außen ist nicht sofort sichtbar, welche Symbole als „offizielle“ API gelten.
   - De facto werden `ModelEngine` und `VizEngine` direkt aus ihren Modulen importiert.

---

## 7. Zusammenfassung der Ist-Situation

- `core` besteht aus zwei klar fokussierten Komponenten:
  - `ModelEngine` für modellnahe Inferenz und Layer-Aktivierungen.
  - `VizEngine` für die Generierung von Visualisierungen aus Aktivierungen.
- Die Schicht ist klar zwischen Config und UI positioniert und **UI-agnostisch** umgesetzt:
  - UIs steuern über Presets, Layer-IDs und Bilder, was berechnet und angezeigt wird.
- In der Feature-View ist `core` bereits produktiv eingebunden:
  - Analyst:innen können Snapshots aufnehmen, Layer und Channels wählen und Visualisierungen erzeugen.
- In der Kino-View gibt es noch keine direkte Nutzung der Core-Schicht,
  obwohl das Design sie als natürliche Grundlage für Live-Visualisierung vorsieht.
- Einige geplante/angelegte Mechanismen (Layer-Mappings, Aktivierungs-Cache)
  sind im Ist-Zustand nur teilweise oder noch gar nicht im Einsatz.

---

## 8. Änderungen durch die aktuelle Überarbeitung

### 8.1 Erweiterungen und Anpassungen

- **Zentrale Modell-Layer-Liste für alle Views**
  - `ModelEngine.get_active_layers()` dient nun als **zentrale Quelle** der Modell-Layer-IDs (`model_layer_id`), die in den UIs auswählbar sind.
  - Aktuelle Defaults (bei fehlenden `active_layer_ids`):
    - `["conv1", "layer1", "layer2", "layer3", "layer4"]`.
  - Nutzung im System:
    - **Feature-View**:
      - Dropdown zur Auswahl des Modell-Layers bezieht seine Werte direkt aus `model_engine.get_active_layers()`.
    - **Content-Editor** (`ui_admin_streamlit/content_view.py`):
      - Erzeugt eine Unterseite pro `model_layer_id`, indem eine temporäre `ModelEngine`-Instanz gebaut und `get_active_layers()` aufgerufen wird.
    - **Kino-View** (`ui_kino_kivy/app.py`):
      - Bestimmt die Liste der modell-layer-basierten Seiten über `self._get_model_layer_ids(self.cfg.model)`, das intern ebenfalls `ModelEngine.get_active_layers()` nutzt.
  - Konsequenz:
    - Alle drei Sichten (Feature-View, Content-View, Kino-View) nutzen **dieselbe zentrale Modell-Layer-Liste**.
    - Änderungen an den aktiven Layern müssen nur an einer Stelle (im Core bzw. der `ModelConfig`/`ModelEngine`) nachvollzogen werden.

### 8.2 Dokumentation und Kommentare

- Anpassungen und Erweiterungen in der Dokumentation:
  - Kapitel 1. Rolle der Core-Schicht im Gesamtsystem: Präzisierungen und Ergänzungen.
  - Kapitel 2. Dateien und Verantwortlichkeiten im `core`-Package:
    - Erweiterung um Abschnitt 2.1.4: Gemeinsame Modell-Layer-Liste für alle Views.
    - Anpassungen in den Abschnitten 2.1.1, 2.1.2, 2.1.3 zur Berücksichtigung der zentralen Modell-Layer-Liste.
  - Kapitel 5. Datenflüsse mit den aktuellen UIs: Anpassungen zur Berücksichtigung der Änderungen.
  - Kapitel 6. Auffälligkeiten, Inkonsistenzen und offene Punkte: Anpassungen und Ergänzungen.
  - Kapitel 7. Zusammenfassung der Ist-Situation: Anpassungen zur Berücksichtigung der Änderungen.

---

## 9. Offene Punkte und nächste Schritte

1. **Integration der Core-Schicht in die Kino-View**
   - Geplante Nutzung der Core-Schicht für die Live-Visualisierung in der Kino-View.
   - Erforderliche Anpassungen in `ui_kino_kivy`, um `ModelEngine` und `VizEngine` zu nutzen.

2. **Überprüfung und Testing der Änderungen**
   - Umfassende Tests der erweiterten und angepassten Funktionen.
   - Überprüfung der Integration in die bestehenden UIs (Feature-View, Content-View, Kino-View).

3. **Optimierung und Refactoring**
   - Mögliche Optimierungen in der Core-Schicht basierend auf den gemachten Erfahrungen.
   - Refactoring von Code-Teilen, wo nötig, um Klarheit und Wartbarkeit zu verbessern.

4. **Dokumentation**
   - Aktualisierung der Dokumentation basierend auf den Änderungen und den Ergebnissen der Tests.
   - Sicherstellung, dass alle relevanten Informationen und Anleitungen für die Nutzung der Core-Schicht vorhanden sind.

5. **Schulung und Übergabe**
   - Gegebenenfalls Schulung für Nutzer:innen der Core-Schicht (z.B. andere Entwickler:innen, Analyst:innen).
   - Übergabe der finalisierten Komponenten und Dokumentationen.

---
