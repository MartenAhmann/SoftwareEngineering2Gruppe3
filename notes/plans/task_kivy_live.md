# Task: Kivy-Live-Funktionalität auf Basis von Favoriten

**WICHTIG:** Bei der Umsetzung dieser Task MUSS `notes/DECISIONS.md` beachtet werden.
Insbesondere gilt: Nach _jeder_ relevanten Änderung im Code (z.B. in `core/`, `config/`, `ui_kino_kivy/`, `ui_admin_streamlit/`) sind die entsprechenden `*_current.md`-Dateien in `notes/current/` zu aktualisieren, sodass sie stets den aktuellen Ist-Stand dokumentieren.

---

## Ziel

Im Kino-Kivy-View (`ui_kino_kivy/app.py`) soll aus einem ausgewählten Favoriten ein fortlaufend aktualisiertes Livebild erzeugt und angezeigt werden.

- Die Bildquelle ist eine physische Kamera (z.B. Webcam), angesteuert über OpenCV.
- Aus jedem Kamerabild wird über `ModelEngine` eine Aktivierung für den im Favoriten hinterlegten `model_layer_id` berechnet.
- Diese Aktivierung wird mit `VizEngine` und dem im Favoriten gespeicherten `preset` zu einem Visualisierungsbild verarbeitet.
- Das Visualisierungsbild wird in einem `Image`-Widget in Kivy dargestellt und im festen Intervall (Pseudo-Live) aktualisiert.
- Der User startet den Live-Modus durch Klick auf einen Favoriten im Kino-View und stoppt ihn durch Seitenwechsel oder (optional) einen „Stop Live“-Button.

**Architektur-Vorgabe:**

- Kivy arbeitet ausschließlich mit `config/` und `core/` und ist **nicht direkt** von `ui_admin_streamlit` abhängig.
- Alle Kamera-Funktionen (Snapshot, Erkennung verfügbarer Kameras) werden in einen **zentralen Kamera-Service im Core** ausgelagert (`core/camera_service.py`).
- Sowohl die Streamlit-Feature-View als auch der Kivy-Kino-View nutzen **nur** diesen Core-Kamera-Service.
- `ui_admin_streamlit/feature_view/camera.py` wird auf einen dünnen Wrapper/Re-Export reduziert.

Die Aufgabe orientiert sich strukturell an `notes/reference/edit_favorites_tasks.md` und ist in klar abgegrenzte Schritte gegliedert, die nacheinander umgesetzt werden können.

---

## Voraussetzungen & Referenzen

- Analyse: `notes/analyse_kivy_live.md`
- Beispiel-Task-Struktur: `notes/reference/edit_favorites_tasks.md`
- Entscheidungen: `notes/DECISIONS.md` (MUSS beachtet werden!)
- Aktueller Stand der Kino-Ansicht: `notes/current/kino_view_current.md`
- Aktueller Stand von Core/Config: `notes/current/core_current.md`, `notes/current/config_view_current.md`
- Aktueller Kamera-Code: `ui_admin_streamlit/feature_view/camera.py`

---

## Schritt 1: Analyse & Notizen vorbereiten

**Ziele:** Kontext klären, zentrale Dateien und Notizen bereit haben, Dokumentationspflicht aus `DECISIONS.md` verankern und mögliche Spaghetti-Code-Stellen identifizieren.

- [ ] `notes/analyse_kivy_live.md` lesen und die dort beschriebenen Verantwortlichkeiten und Datenflüsse verstehen:
  - Kamera → ModelEngine → VizEngine → Anzeige im Kino-View.
  - Umgang mit Favoriten und Presets aus der Admin-UI.
- [ ] `ui_admin_streamlit/feature_view/camera.py` lesen und verstehen:
  - [ ] Welche Logik ist rein „Kamera-Backend“ (OpenCV, `detect_cameras`, `take_snapshot`)?
  - [ ] Welche Stellen sind streamlit-spezifisch (falls vorhanden)?
- [ ] `notes/DECISIONS.md` lesen und die wichtigste Vorgabe verinnerlichen:
  - Nach jeder relevanten Änderung müssen die `*_current.md`-Dateien in `notes/current` aktualisiert werden.
- [ ] In `notes/current/kino_view_current.md` einen kurzen Platzhalter-Abschnitt ergänzen (z.B. „Geplante Kivy-Live-Funktionalität“), der:
  - [ ] Ziel-UX beschreibt (Favorit auswählen → Livebild erscheint).
  - [ ] Grob den geplanten Datenfluss benennt (ohne Implementation-Details).
- [ ] In dieser Task (unter einem eigenen kleinen Unterpunkt) festhalten, wo potenziell **Spaghetti-Code** entstehen könnte und wie das verhindert wird:
  - [ ] **Kernentscheidung:** Kamera-Logik wandert in einen zentralen Service im Core (z.B. `core/camera_service.py` oder `core/services/camera_service.py`).
  - [ ] Sowohl Streamlit-Feature-View als auch Kivy-Kino-View nutzen **nur** diesen Service und importieren **nicht gegenseitig** ihre UI-Ebene.

**Hinweis:** Die eigentliche detaillierte Architektur landet in dieser Task-Datei und später in den aktualisierten `*_current.md`-Dateien, sobald der Code umgesetzt ist.

---

## Schritt 2: Architektur-Zielbild „Favorit → Livebild” konkretisieren

**Ziele:** Klar definieren, wie aus einem Favoriten im Kino-View ein Livebild generiert wird – **ohne** direkte Abhängigkeit von Streamlit.

- [ ] Auf Basis von `notes/analyse_kivy_live.md` ein textuelles Architektur-Zielbild festhalten (z.B. direkt in dieser Task-Datei unter diesem Schritt):
  - Datenfluss (High-Level):
    - [ ] Kamera-Snapshot über **Core-Kamera-Service** (z.B. `core.camera_service.take_snapshot`).
    - [ ] `core.model_engine.ModelEngine.run_inference(image)` berechnet Aktivierungen.
    - [ ] `core.viz_engine.VizEngine.visualize(activation, viz_preset, original_image)` erzeugt Visualisierung.
    - [ ] Ergebnis wird als Texture im Kivy-Image-Widget angezeigt.
  - UI-Schichten:
    - [ ] Streamlit-Feature-View: spricht **nur** mit `core` und `config`, nicht mit `ui_kino_kivy`.
    - [ ] Kivy-Kino-View: spricht **nur** mit `core` und `config`, nicht mit `ui_admin_streamlit`.
- [ ] „Live“-Begriff technisch festlegen:
  - [ ] Variante A: Pseudo-Live über wiederholte Snapshots im festen Intervall (z.B. 5–10 FPS).
  - [ ] Variante B: Einzel-Snapshot, der per Button manuell aktualisiert werden kann.
  - [ ] Entscheidung treffen (empfohlen: Variante A als Standard, Variante B als Debug-/Fallback-Option) und in der Task dokumentieren.

---

## Schritt 3: API-Skizze für die Live-Pipeline und Kamera-Services definieren

**Ziele:** Vor der Implementation eine klare API-Skizze für die Kivy-Live-Pipeline haben, inklusive **zentralem Kamera-Service** im Core, der **alle** Kamera-Funktionen (Snapshot und Live-Verwendung) kapselt. Alle Konsumenten (insbesondere `feature_view`) greifen nur noch auf diesen Service zu.

- [ ] API-Skizze in dieser Task-Datei formulieren:
  - [ ] Hilfsfunktion zur Konvertierung `favorite_preset -> VizPreset` (z.B. in `config/service.py` oder `core/`):
    - Signatur-Idee: `def favorite_preset_to_viz_preset(preset_dict: dict) -> VizPreset`.
  - [ ] **Zentraler Kamera-Service im Core** definieren (neue Datei, `core/camera_service.py`):
    - Öffentliche API (konkrete Signaturen, so umsetzen):
      - [ ] `def detect_cameras(max_tested: int = 5) -> list[int]`  
            Findet verfügbare Kameras durch Testen der Kamera-IDs `0..max_tested-1`.
      - [ ] `def take_snapshot(cam_id: int, timeout: float = 5.0) -> tuple[np.ndarray | None, str]`  
            Nimmt **ein** Bild von der Kamera als RGB-Array auf.
    - Interne Implementierungsdetails: siehe **Referenz-API Kamera-Service** weiter unten in diesem Dokument (Anhang A).
  - [ ] **WICHTIG: Migration bestehender Konsumenten auf den Core-Service planen** (siehe Schritt 4 im Detail):
    - [ ] `ui_admin_streamlit/feature_view/camera.py` wird zu einem dünnen Wrapper/Re-Export.
    - [ ] Alle Stellen in der Feature-View, die bisher lokal `detect_cameras` / `take_snapshot` importieren, behalten ihre Imports, nutzen aber implizit den Core-Service.
  - [ ] Lebensdauer der `ModelEngine` im Kivy-Kontext:
    - [ ] Eine Instanz pro `ExhibitRoot`, die über die gesamte App-Laufzeit verwendet wird.
  - [ ] Verwendung von `VizEngine` im Kino-Kontext:
    - [ ] Konstruktion einer Instanz, z.B. `self.viz_engine = VizEngine()` oder ggf. mit Parametern aus der Config.
    - [ ] Hauptmethode: `visualize(activation, viz_preset, original_image)` → `np.ndarray` (RGB).
  - [ ] UI-API in `ExhibitRoot` skizzieren:
    - [ ] `start_live_for_favorite(model_layer_id: str, favorite: dict) -> None`.
    - [ ] `stop_live() -> None`.
    - [ ] `update_live_frame(dt: float) -> None` (wird von Kivy-`Clock` getriggert).

---

## Schritt 4: Anforderungen an Kamera-Integration festlegen (Core-Service + Konsumenten-Migration)

**Ziele:** Klarstellen, wie die Kamera **zentral** und UI-unabhängig genutzt wird und wie Kivy/Streamlit darauf zugreifen. Alle bisherigen Kamera-Funktionen (Snapshot etc.) sollen **im Core** liegen. `feature_view` und Kivy werden explizit auf diesen Service umgestellt.

### 4.1 Bestehende Kamera-Implementierung analysieren

- [ ] `ui_admin_streamlit/feature_view/camera.py` vollständig lesen.
- [ ] Verstehen, dass diese Datei aktuell bereits generische Logik enthält:
  - [ ] `detect_cameras(max_tested: int = 5) -> List[int]` mit OpenCV.
  - [ ] `take_snapshot(cam_id: int, timeout: float = 5.0) -> Tuple[np.ndarray | None, str]` mit Timeout, Fehlerbehandlung, BGR→RGB-Konvertierung.
- [ ] Prüfen, ob es weitere Kamera-Helfer oder Duplikate im Repo gibt (z.B. per Suche nach `detect_cameras` / `take_snapshot`).

### 4.2 Neuen Core-Kamera-Service anlegen (`core/camera_service.py`)

**Zielzustand dieser Datei ist hier vollständig spezifiziert. Der Entwickler soll sie exakt so (bzw. äquivalent) umsetzen.**

- [ ] Neue Datei `core/camera_service.py` anlegen mit folgendem Inhalt (logischer Struktur, nicht exakt Copy&Paste notwendig, aber Verhalten muss identisch sein):
  - **Imports:**
    - [ ] `from __future__ import annotations`
    - [ ] `import logging`
    - [ ] `import time`
    - [ ] `from typing import List, Tuple`
    - [ ] `import cv2`
    - [ ] `import numpy as np`
  - **Logger:**
    - [ ] `logger = logging.getLogger(__name__)`
  - **Funktion `detect_cameras`:**
    - Signatur:
      - [ ] `def detect_cameras(max_tested: int = 5) -> List[int]:`
    - Verhalten (entspricht aktuellem `ui_admin_streamlit/feature_view/camera.py`):
      - [ ] Initialisiere `cams: List[int] = []`.
      - [ ] Schleife `for cam_id in range(max_tested):`
        - [ ] Versuche `cap = cv2.VideoCapture(cam_id)` in `try:`
          - [ ] Wenn `cap is not None and cap.isOpened()`: ID zu `cams` hinzufügen und `cap.release()`.
        - [ ] Bei Exception: `logger.debug(f"Fehler beim Testen von Kamera {cam_id}: {e}")` und Schleife fortsetzen.
      - [ ] Rückgabe: `cams`.
  - **Funktion `take_snapshot`:**
    - Signatur:
      - [ ] `def take_snapshot(cam_id: int, timeout: float = 5.0) -> Tuple[np.ndarray | None, str]:`
    - Verhalten (1:1 wie im aktuellen `camera.py` in `ui_admin_streamlit/feature_view`):
      - [ ] `start_time = time.time()`.
      - [ ] `try: cap = cv2.VideoCapture(cam_id) except Exception as e:`
        - [ ] Setze `error_msg = f"Kamera konnte nicht initialisiert werden: {e}"`.
        - [ ] `logger.error(error_msg)`.
        - [ ] `return None, error_msg`.
      - [ ] Wenn `not cap.isOpened():`
        - [ ] `error_msg = f"Kamera {cam_id} nicht gefunden oder Zugriff verweigert"`.
        - [ ] `logger.error(error_msg)`.
        - [ ] `return None, error_msg`.
      - [ ] Timeout-Check:
        - [ ] Wenn `time.time() - start_time > timeout`:
          - [ ] `cap.release()`.
          - [ ] `error_msg = f"Timeout beim Öffnen der Kamera {cam_id}"`.
          - [ ] `logger.error(error_msg)`.
          - [ ] `return None, error_msg`.
      - [ ] Lese Frame:
        - [ ] `try: ok, frame = cap.read() except Exception as e:`
          - [ ] `cap.release()`.
          - [ ] `error_msg = f"Fehler beim Lesen vom Kamera-Feed: {e}"`.
          - [ ] `logger.error(error_msg)`.
          - [ ] `return None, error_msg`.
        - [ ] `finally: cap.release()`.
      - [ ] Wenn `not ok or frame is None`:
        - [ ] `error_msg = f"Kamera {cam_id} liefert kein Bild"`.
        - [ ] `logger.error(error_msg)`.
        - [ ] `return None, error_msg`.
      - [ ] Farbkonvertierung:
        - [ ] `try: rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) return rgb_frame, ""`
        - [ ] `except Exception as e:`
          - [ ] `error_msg = f"Fehler bei Farbkonvertierung: {e}"`.
          - [ ] `logger.error(error_msg)`.
          - [ ] `return None, error_msg`.

**WICHTIG:** Diese Implementierung soll **funktional identisch** zum bisherigen `ui_admin_streamlit/feature_view/camera.py` sein. Nur der Modulpfad und der Ort im Projekt ändern sich.

### 4.3 Bestehende Streamlit-Feature-View auf Core-Service umstellen

**Ziel:** `ui_admin_streamlit/feature_view/camera.py` wird zu einem dünnen Wrapper, der die Core-Funktionen re-exportiert. Alle bestehenden Importe in der Feature-View bleiben unverändert.

- [ ] Datei `ui_admin_streamlit/feature_view/camera.py` öffnen (aktueller Inhalt siehe Anhang B weiter unten).
- [ ] Inhalt vollständig durch einen Wrapper ersetzen, der exakt Folgendes bereitstellt:
  - **Imports:**
    - [ ] `from __future__ import annotations`
    - [ ] `from typing import List, Tuple`
    - [ ] `import numpy as np`
    - [ ] `from core.camera_service import detect_cameras, take_snapshot`
  - **Optionaler Modul-Docstring:**
    - [ ] Kurze Erklärung, dass dies nur ein Wrapper ist, damit bestehende Importe funktionieren.
  - **Keine** eigene OpenCV-, Logging- oder Zeit-Logik mehr in dieser Datei.
- [ ] Alle bestehenden Importe im Feature-View-Code funktionieren danach weiterhin:
  - Beispiel: `from .camera import take_snapshot` oder `from . import camera`.
  - Diese Importe landen jetzt indirekt bei `core.camera_service`.
- [ ] Sicherstellen, dass im gesamten `ui_admin_streamlit/feature_view`-Paket **keine** direkte Verwendung von OpenCV erfolgt, außer über diesen Wrapper (und damit den Core-Service).

### 4.4 Kivy-Kino-View auf Core-Service aufsetzen

**Ziel:** Kivy verwendet ausschließlich den Core-Kamera-Service und hängt nicht von Streamlit-Modulen ab.

- [ ] In `ui_kino_kivy/app.py` folgende Importe ergänzen (oder anpassen, falls bereits vorhanden):
  - [ ] `from core import camera_service`
    - oder präziser, wenn bevorzugt:
  - [ ] `from core.camera_service import detect_cameras, take_snapshot`
- [ ] **Verbot** (explizit in Code-Reviews prüfen):
  - In `ui_kino_kivy` darf **kein** Import aus `ui_admin_streamlit` erfolgen, insbesondere nicht `ui_admin_streamlit.feature_view.camera`.
- [ ] Standard-Kamera-ID für das Kivy-Live-Feature festlegen:
  - [ ] `self.live_cam_id = 0` als Default im `ExhibitRoot`-Konstruktor.
  - [ ] Optional: vor dem ersten Live-Start `detect_cameras` aufrufen und validieren, ob `0` verfügbar ist; wenn nicht, erste gefundene Kamera-ID verwenden.
- [ ] Kivy verwendet für **alle** Snapshots ausschließlich `camera_service.take_snapshot`.

### 4.5 Fehlerverhalten zentral im Kamera-Service und konsistent in den UIs

- [ ] Fehlerbehandlung wird hauptsächlich im Core-Service umgesetzt:
  - [ ] Bei Fehlern liefert `take_snapshot` `(None, "Fehlerbeschreibung")` zurück und loggt den Fehler.
- [ ] Konsumenten (Streamlit-Feature-View und Kivy-Kino-View) implementieren einheitliches Verhalten:
  - [ ] Wenn `image is None`:
    - [ ] In Streamlit: Ausgabe einer klaren Fehlermeldung im UI (z.B. `st.error`), kein weiterer Snapshot-Versuch in einer engen Schleife.
    - [ ] In Kivy: Anzeige einer Fehlermeldung im `vis_status_label` und ggf. Stoppen des Live-Modus.
- [ ] **Wichtig:** Es soll **keine** zusätzliche, eigenständige „Live-Kamera-Logik“ im UI geben, die OpenCV direkt verwendet. Alles läuft über den Core-Service.

- [ ] Pseudo-Code für die Snapshot-Logik im Kivy-Live-Modus in der Task notieren, z.B. (unter Verwendung des Core-Services):
  - `Clock.schedule_interval(self.update_live_frame, LIVE_UPDATE_INTERVAL)`
  - `def update_live_frame(self, dt: float) -> None:`
    - `img, err = camera_service.take_snapshot(self.live_cam_id)`
    - `if img is None:`
    - &nbsp;&nbsp;&nbsp;&nbsp;`self.vis_status_label.text = f"Kamera-Fehler: {err}"`
    - &nbsp;&nbsp;&nbsp;&nbsp;`self.stop_live()`
    - &nbsp;&nbsp;&nbsp;&nbsp;`return`
    - `acts = self.model_engine.run_inference(img)`
    - `activation = acts[model_layer_id]` (ggf. Fehlerbehandlung, falls Key fehlt)
    - `vis_img = self.viz_engine.visualize(activation, viz_preset, original=img if viz_preset.overlay else None)`
    - `self._update_kivy_texture_from_numpy(vis_img)`

---

## Schritt 5: Datenfluss „Favorit auswählen → Live-Session starten“ im Kivy-Root designen

**Ziele:** Definieren, wie ein Favorit im Kino-View den Live-Modus startet.

- [ ] `ui_kino_kivy/app.py` öffnen und den aktuellen Aufbau von `ExhibitRoot` verstehen.
- [ ] Neue Attribute für `ExhibitRoot` planen:
  - [ ] `self.model_engine: ModelEngine | None` – zentrale Model-Instanz.
  - [ ] `self.viz_engine: VizEngine | None` – zentrale Viz-Instanz.
  - [ ] `self.live_cam_id: int | None` – aktuell verwendete Kamera-ID.
  - [ ] `self.live_active_favorite: dict | None` – aktuell laufender Favorit mit zugehörigem `model_layer_id`.
  - [ ] `self.live_clock_event` – Referenz auf das von `Clock.schedule_interval` zurückgegebene Event.
- [ ] Verhalten bei Favoriten-Auswahl konzipieren (`on_favorite_select(...)` o.ä.):
  - [ ] Wenn bereits ein Live-Modus läuft und ein neuer Favorit gewählt wird:
    - [ ] Zuerst bestehenden Live-Modus stoppen.
    - [ ] Danach neuen Live-Modus mit dem neuen Favoriten starten.
  - [ ] Wenn kein Live-Modus läuft:
    - [ ] Direkt Live-Modus für den gewählten Favoriten starten.
- [ ] Verhalten bei Entfernen von Favoriten-Sessions (z.B. `session_removed_favorites`) definieren:
  - [ ] Wenn ein aktiver Favorit entfernt wird, soll der laufende Live-Modus sofort gestoppt werden.

---

## Schritt 6: UX-/UI-Konzept im Kino-View für den Live-Modus beschreiben

**Ziele:** Klarheit über Benutzerinteraktion und sichtbare Elemente im Kino-View.

- [ ] UX-Variante wählen und dokumentieren:
  - [ ] Variante 1: Klick auf Favoriten-Button startet direkt Livebild für diesen Favoriten.
  - [ ] Variante 2: Klick auf Favoriten-Button öffnet ein Overlay/Popup mit Auswahl „Live starten“ / „Einzelbild berechnen“.
  - [ ] Entscheidung: z.B. zunächst Variante 1 für den Expo-Einsatz, Variante 2 als mögliche spätere Erweiterung.
- [ ] UI-Elemente für den zentralen Bereich des Kino-Views planen:
  - [ ] `self.vis_image`: `kivy.uix.image.Image` zur Darstellung des aktuellsten Livebildes.
  - [ ] `self.vis_status_label`: Label für Status- und Fehlermeldungen („Starte Kamera…“, „Keine Kamera gefunden“, „Live gestoppt“ etc.).
  - [ ] Optional: Fallback-Text, wenn kein Bild verfügbar ist („Wähle einen Favoriten, um zu starten“).
- [ ] Verhalten beim Seitenwechsel (`switch_to_page`):
  - [ ] Definieren, dass beim Wechsel von einem Modell-Layer auf eine andere Seite (z.B. „global“) der Live-Modus gestoppt wird.
  - [ ] Festlegen, ob beim Zurückwechseln zum Layer der Live-Modus automatisch neu gestartet wird oder nicht (empfohlen: nicht automatisch, sondern erst bei erneuter Favoriten-Auswahl).

---

## Schritt 7: Technischen Pfad „Favoriten-Preset → VizPreset“ ausdefinieren

**Ziele:** Präzisieren, wie aus den in Favoriten gespeicherten Presets echte `VizPreset`-Objekte werden.

- [ ] Kurze Spezifikation für eine Konvertierungsfunktion in dieser Task notieren:
  - Signatur-Idee:
    - [ ] `def favorite_preset_to_viz_preset(favorite_preset: dict) -> VizPreset`.
  - Eingabe-Felder (Beispiel):
    - [ ] `channels`
    - [ ] `k`
    - [ ] `blend_mode`
    - [ ] `overlay`
    - [ ] `alpha`
    - [ ] `cmap`
    - [ ] `model_layer_id` (oder `layer_id`)
  - Ausgabe:
    - [ ] Gültiges `VizPreset`-Objekt (`config.models.VizPreset`).
- [ ] Regeln für Defaults und Fehlerfälle festlegen:
  - [ ] Falls `layer_id` im Favorite-Preset fehlt, aus `model_layer_id` ableiten.
  - [ ] Falls `k` fehlt und `channels == "topk"`, sinnvolles Default-`k` wählen (z.B. 3 oder Wert aus globaler Config).
  - [ ] Wenn Pflichtfelder fehlen → Log-Eintrag + Abbruch des Live-Starts mit Statusmeldung im UI.
- [ ] Dokumentieren, wo diese Funktion später aufgerufen wird:
  - [ ] Direkt in `ExhibitRoot.on_favorite_select()`.
  - oder
  - [ ] In einer neuen Service-Funktion in `config/service.py` (z.B. `favorite_to_viz_preset`).

---

## Schritt 8: Integration von `ModelEngine` im Kivy-Kontext spezifizieren

**Ziele:** Modell-Inferenz sauber in Kivy einbinden.

- [ ] In dieser Task definieren, wie `ModelEngine` in `ExhibitRoot` verwendet wird:
  - [ ] Beim Initialisieren von `ExhibitRoot` wird genau eine `ModelEngine`-Instanz erzeugt:
    - [ ] `self.model_engine = ModelEngine(self.cfg.model, device="cpu")` (oder ähnlich, abhängig vom existierenden Code).
  - [ ] Device-Strategie: zunächst nur CPU, keine GPU-Konfiguration im Kivy-Kontext.
- [ ] Ablauf pro Live-Tick (nur konzeptionell):
  - [ ] Kamera-Snapshot liefert `np_image` (H x W x 3, RGB).
  - [ ] `acts = self.model_engine.run_inference(np_image)`.
  - [ ] `model_layer_id = favorite["preset"]["model_layer_id"]`.
  - [ ] `activation = acts[model_layer_id]`.
- [ ] Fehlerpfad definieren:
  - [ ] Wenn `model_layer_id` nicht in `acts` enthalten ist:
    - [ ] Logging/Debug-Ausgabe.
    - [ ] Status-Label aktualisieren („Layer nicht gefunden“ o.ä.).
    - [ ] Live-Modus für diesen Favoriten stoppen.

---

## Schritt 9: Integration von `VizEngine` und Bildaufbereitung für Kivy spezifizieren

**Ziele:** Ergebnisbild der Visualisierung in eine Kivy-Texture überführen.

- [ ] In dieser Task den groben Ablauf vom `np.ndarray` zur Kivy-Texture beschreiben:
  - [ ] `vis_img = self.viz_engine.visualize(activation, viz_preset, original=np_image if viz_preset.overlay else None)`
    - Erwartet wird ein `np.ndarray` (H x W x 3, `uint8`, Wertebereich 0–255).
  - [ ] Umwandlung in Kivy-Format:
    - [ ] Größe aus `vis_img.shape` entnehmen.
    - [ ] Bytes extrahieren: `vis_img.tobytes()`.
    - [ ] `Texture.create(size=(w, h))` und `texture.blit_buffer(..., colorfmt="rgb", bufferfmt="ubyte")` verwenden.
    - [ ] `self.vis_image.texture = texture` setzen.
- [ ] Fehlerfälle definieren:
  - [ ] Wenn `viz_engine.visualize` eine Exception wirft:
    - [ ] Loggen.
    - [ ] Status-Label aktualisieren („Fehler bei Visualisierung“).
    - [ ] Live-Modus stoppen, um Endlosschleifen zu vermeiden.

---

## Schritt 10: Steuerlogik für Start/Stop des Live-Modus planen

**Ziele:** Klarer State- und Lifecycle-Management für den Live-Modus.

- [ ] In dieser Task konzeptionell folgende Methoden in `ExhibitRoot` definieren:
  - [ ] `def start_live_for_favorite(self, model_layer_id: str, favorite: dict) -> None`:
    - [ ] Prüft Kamera-Verfügbarkeit (`self.live_cam_id`).
    - [ ] Konvertiert `favorite["preset"]` → `VizPreset`.
    - [ ] Setzt `self.live_active_favorite` (inkl. `model_layer_id`).
    - [ ] Plant `update_live_frame` mit `Clock.schedule_interval` (z.B. alle 0.2 s).
    - [ ] Aktualisiert Status-Label („Live-Modus aktiv: <Favoritenname>“).
  - [ ] `def stop_live(self) -> None`:
    - [ ] Entfernt das geplante Clock-Event, falls vorhanden.
    - [ ] Setzt `self.live_active_favorite = None` und `self.live_cam_id = None` (oder lässt Kamera-ID separat bestehen).
    - [ ] Aktualisiert Status-Label („Live-Modus gestoppt“).
  - [ ] `def update_live_frame(self, dt: float) -> None`:
    - [ ] Holt Snapshot, führt Inferenz und Visualisierung aus.
    - [ ] Aktualisiert `self.vis_image.texture`.
- [ ] Festlegen, wann `stop_live` automatisch aufgerufen wird:
  - [ ] Beim Wechsel der Seite (`switch_to_page`).
  - [ ] Beim Schließen der App (`App.on_stop`).
  - [ ] Beim Entfernen des aktiven Favoriten.
  - [ ] Optional: Beim Klick auf einen „Stop Live“-Button im UI.

---

## Schritt 11: Änderungen an der Kino-UI-Struktur planen

...existing code...

---

## Schritt 12: Session-Verhalten und Performance-Überlegungen dokumentieren

...existing code...

---

## Schritt 13: Testszenarien für Kivy-Live-Feature definieren

...existing code...

---

## Schritt 14: Pflege der `*_current.md`-Notizen nach Implementation

...existing code...

---

## Schritt 15: Optionale Erweiterungen und Zukunftsschritte

...existing code...

---

## Offene Fragen für spätere Entscheidungen

...existing code...

---

## Anhang A: Referenz-API `core/camera_service.py`

Dieser Anhang beschreibt die **präzise** Ziel-API und das Verhalten von `core/camera_service.py`. Ein Entwickler kann diese Beschreibung direkt 1:1 in Code übersetzen.

```python
# core/camera_service.py (Referenzstruktur)
from __future__ import annotations

import logging
import time
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_cameras(max_tested: int = 5) -> List[int]:
    """Testet die ersten max_tested Kamera-IDs und gibt die gefundenen zurück.

    Args:
        max_tested: Anzahl der zu prüfenden Kamera-IDs ab 0.

    Returns:
        Liste der Kamera-IDs, die erfolgreich geöffnet werden konnten.
    """
    cams: List[int] = []
    for cam_id in range(max_tested):
        try:
            cap = cv2.VideoCapture(cam_id)
            if cap is not None and cap.isOpened():
                cams.append(cam_id)
                cap.release()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Fehler beim Testen von Kamera {cam_id}: {e}")
            continue
    return cams


def take_snapshot(cam_id: int, timeout: float = 5.0) -> Tuple[np.ndarray | None, str]:
    """Nimmt ein einzelnes Bild von der angegebenen Kamera auf.

    Args:
        cam_id: ID der Kamera
        timeout: Maximale Wartezeit in Sekunden

    Returns:
        Tuple (RGB-Array oder None, Fehlermeldung oder "")
        - Bei Erfolg: (image, "")
        - Bei Fehler: (None, "Fehlerbeschreibung")
    """
    start_time = time.time()

    try:
        cap = cv2.VideoCapture(cam_id)
    except Exception as e:  # noqa: BLE001
        error_msg = f"Kamera konnte nicht initialisiert werden: {e}"
        logger.error(error_msg)
        return None, error_msg

    if not cap.isOpened():
        error_msg = f"Kamera {cam_id} nicht gefunden oder Zugriff verweigert"
        logger.error(error_msg)
        return None, error_msg

    # Timeout-Check
    if time.time() - start_time > timeout:
        cap.release()
        error_msg = f"Timeout beim Öffnen der Kamera {cam_id}"
        logger.error(error_msg)
        return None, error_msg

    try:
        ok, frame = cap.read()
    except Exception as e:  # noqa: BLE001
        cap.release()
        error_msg = f"Fehler beim Lesen vom Kamera-Feed: {e}"
        logger.error(error_msg)
        return None, error_msg
    finally:
        cap.release()

    if not ok or frame is None:
        error_msg = f"Kamera {cam_id} liefert kein Bild"
        logger.error(error_msg)
        return None, error_msg

    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return rgb_frame, ""
    except Exception as e:  # noqa: BLE001
        error_msg = f"Fehler bei Farbkonvertierung: {e}"
        logger.error(error_msg)
        return None, error_msg
```

> Hinweis: Der tatsächliche Code im Repository darf minimale Stilabweichungen haben (z.B. andere Linting-Kommentare), aber das **Verhalten** muss diesem Referenzcode entsprechen.

---

## Anhang B: Zielinhalt `ui_admin_streamlit/feature_view/camera.py`

Nach der Umstellung auf den Core-Kamera-Service soll die Datei `ui_admin_streamlit/feature_view/camera.py` nur noch ein Wrapper/Re-Export sein. Ein Entwickler kann den Inhalt exakt wie folgt umsetzen:

```python
from __future__ import annotations

"""Wrapper-Modul für Kamera-Funktionen in der Streamlit-Feature-View.

Die eigentliche Implementierung liegt in ``core.camera_service``.
Dieses Modul re-exportiert nur die dort definierten Funktionen, damit
bestehende Importe aus ``ui_admin_streamlit.feature_view.camera``
weiter funktionieren.
"""

from typing import List, Tuple

import numpy as np

from core.camera_service import detect_cameras, take_snapshot

__all__ = [
    "detect_cameras",
    "take_snapshot",
]
```

**WICHTIG:** In dieser Datei **dürfen keine** direkten OpenCV-Operationen, `logging`-Konfigurationen oder Zeitmessungen mehr stattfinden. Jegliche Kamera-Logik liegt im Core-Service.

---

## Anhang C: Kivy-Live-Fluss aus Favoriten (Referenz-Ablauf)

Dieser Anhang beschreibt den konkreten Ablauf, wie ein Favorit im Kivy-Kino-View zu einem Livebild führt. Er dient als Referenz für die Implementierung von `ExhibitRoot` in `ui_kino_kivy/app.py`.

1. **State im `ExhibitRoot` (neu):**
   - `self.model_engine: ModelEngine` – einmalig initialisiert, z.B. mit `self.cfg.model`.
   - `self.viz_engine: VizEngine` – einmalig initialisiert.
   - `self.live_cam_id: int | None` – Standard `0`, oder erste gefundene Kamera-ID.
   - `self.live_active_favorite: dict | None` – momentan laufender Favorit.
   - `self.live_active_layer_id: str | None` – zugehörige `model_layer_id`.
   - `self.live_clock_event` – Handle auf `Clock.schedule_interval`.
   - `self.vis_image` – `kivy.uix.image.Image` für das Visualisierungsbild.
   - `self.vis_status_label` – Label für Status-/Fehlermeldungen.

2. **Start eines Live-Modus über Favoritenklick:**

```python
def on_favorite_selected(self, layer_id: str, favorite: dict) -> None:
    # 1. Falls bereits ein Live-Modus läuft, zuerst stoppen
    if self.live_clock_event is not None:
        self.stop_live()

    # 2. Kamera-ID setzen (zunächst 0 oder erste gefundene)
    self.live_cam_id = 0  # oder Ergebnis aus camera_service.detect_cameras

    # 3. VizPreset aus dem Favoriten bauen
    viz_preset = favorite_preset_to_viz_preset(favorite["preset"])  # Helper aus config/service.py oder core

    # 4. State aktualisieren
    self.live_active_favorite = favorite
    self.live_active_layer_id = layer_id

    # 5. Status anzeigen
    self.vis_status_label.text = f"Live-Modus aktiv für Favorit: {favorite.get('name', layer_id)}"

    # 6. Live-Timer starten
    self.live_clock_event = Clock.schedule_interval(
        lambda dt: self.update_live_frame(dt, viz_preset),
        LIVE_UPDATE_INTERVAL,
    )
```

3. **Update eines Live-Frames:**

```python
def update_live_frame(self, dt: float, viz_preset: VizPreset) -> None:
    if self.live_cam_id is None or self.model_engine is None:
        return

    # 1. Snapshot holen
    img, err = camera_service.take_snapshot(self.live_cam_id)
    if img is None:
        self.vis_status_label.text = f"Kamera-Fehler: {err}"
        self.stop_live()
        return

    # 2. Inferenz
    acts = self.model_engine.run_inference(img)
    layer_id = self.live_active_layer_id
    if layer_id not in acts:
        self.vis_status_label.text = f"Layer nicht gefunden: {layer_id}"
        self.stop_live()
        return

    activation = acts[layer_id]

    # 3. Visualisierung
    try:
        vis_img = self.viz_engine.visualize(
            activation,
            viz_preset,
            original=img if viz_preset.overlay else None,
        )
    except Exception as e:  # noqa: BLE001
        # Nicht abstürzen, Live-Modus beenden
        self.vis_status_label.text = f"Fehler bei Visualisierung: {e}"
        self.stop_live()
        return

    # 4. Kivy-Texture aktualisieren (Hilfsfunktion im ExhibitRoot)
    self._update_kivy_texture_from_numpy(vis_img)
```

4. **Stoppen des Live-Modus:**

```python
def stop_live(self) -> None:
    if self.live_clock_event is not None:
        self.live_clock_event.cancel()
        self.live_clock_event = None

    self.live_active_favorite = None
    self.live_active_layer_id = None

    self.vis_status_label.text = "Live-Modus gestoppt"
```

5. **Hilfsfunktion für Texture-Update (Pseudo-Code):**

```python
def _update_kivy_texture_from_numpy(self, img: np.ndarray) -> None:
    # img: H x W x 3, dtype=uint8, RGB
    h, w, _ = img.shape
    if not self.vis_image.texture or self.vis_image.texture.size != (w, h):
        self.vis_image.texture = Texture.create(size=(w, h))

    self.vis_image.texture.blit_buffer(
        img.tobytes(),
        colorfmt="rgb",
        bufferfmt="ubyte",
    )
    self.vis_image.canvas.ask_update()
```

> Hinweis: Der konkrete Kivy-Code kann leicht variieren, aber dieser Ablauf beschreibt genau, **wie** das Livebild aus Favoriten kommen soll und welche Komponenten beteiligt sind.
