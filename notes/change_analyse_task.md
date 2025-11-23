# Implementierungsplan zu `change_analyse_v0.md`

Rolle: Du bist Junior-Entwickler:in im Team. Du setzt die folgenden Aufgaben exakt in der angegebenen Reihenfolge um. Lies jeden Schritt vollständig, bevor Du beginnst. Halte Dich genau an die beschriebenen Dateien, Strukturen und Begriffe.

**Wichtiger Grundsatz:** Immer wenn Du in einem Bereich arbeitest, der in einer der Dateien unter `notes/current/` dokumentiert ist (z.B. `config_view_current.md`, `content_view_current.md`, `core_current.md`, `feature_view_current.md`, `kino_view_current.md`), **musst** Du nach Abschluss Deiner Codeänderungen die entsprechende `notes/current/*_current.md`-Datei anpassen, sodass Dokumentation und Implementierung exakt übereinstimmen.

---

## 0. Überblick und Reihenfolge

Du arbeitest in dieser groben Reihenfolge:

1. Grundlagen und Konstanten vorbereiten.
2. "Global" in Config und Content-View erweitern (globale UI-Texte).
3. Harte ID `"layer1_conv1"` aus Default- und Fallback-Logik entkoppeln.
4. Config-Struktur für die Auswahl "Favoriten pro Kivy-Seite" einführen.
5. Content-View erweitern: Auswahl der Favoriten pro `model_layer_id`.
6. Kivy-Kino-View an neue Struktur für Favoriten und globale Texte anpassen.
7. Feature-View klar auf Favoriten-Verwaltung begrenzen.
8. Alle `notes/current/*_current.md`-Dateien aktualisieren.
9. Abschließender konzeptioneller Check (Randfälle und Konsistenz).

Arbeite Schritt für Schritt. Überspringe nichts. Wenn etwas unklar ist, halte Dich an die Beschreibung in `notes/change_analyse_v0.md` und den aktuellen Code.

---

## 1. Grundlagen und Konstanten vorbereiten

### 1.1 Relevante Dateien lesen

Bevor Du Code änderst, liest Du die folgenden Dateien komplett durch, damit Du den Ist-Zustand kennst:

- `config/models.py`
- `config/service.py`
- `config/migrations.py`
- `ui_admin_streamlit/content_view.py`
- `ui_admin_streamlit/feature_view/view.py`
- `ui_admin_streamlit/feature_view/favorites.py`
- `ui_kino_kivy/app.py`
- `notes/change_analyse_v0.md`
- `notes/current/config_view_current.md`
- `notes/current/content_view_current.md`
- `notes/current/feature_view_current.md`
- `notes/current/kino_view_current.md`
- `notes/current/core_current.md`

Achte beim Lesen besonders auf:

- Wie `model_layer_id`, `ui_layer.id`, `ui.model_layers` und `viz_presets` aktuell zusammenhängen.
- Wo `"layer1_conv1"` als ID verwendet wird (Code und Doku).
- Wie Favoriten aktuell von Feature-View über die Config in den Kino-View gelangen.
- Wie "Global" jeweils verstanden wird (Admin vs. Kino).

### 1.2 Zentrale Konstanten anlegen

1. Öffne `config/service.py`.
2. Lege im oberen Bereich, in der Nähe bestehender Konstanten, Folgendes an (Namen ggf. an vorhandenen Stil anpassen):
   - `MAX_FAVORITES_PER_MODEL_LAYER = 3`
3. Falls im Code mehrfach der Literal-String `"global"` als Page-ID verwendet wird und noch keine zentrale Konstante existiert:
   - Lege in der passenden UI-Schicht (in `ui_admin_streamlit/content_view.py`) eine Konstante `PAGE_ID_GLOBAL = "global"` an, **falls** dort noch nicht vorhanden.
4. Ersetze im Projekt harte Vorkommen von `3` für die Anzahl von Favoriten, **soweit eindeutig** auf "max. 3 Favoriten pro Modell-Layer im Kino-View" bezogen, durch `MAX_FAVORITES_PER_MODEL_LAYER`.

> Hinweis: Ändere nur Stellen, bei denen klar ist, dass es um die Höchstzahl der Favoriten im Kino-View geht. Andere Verwendungen von `3` lässt Du unverändert.

---

## 2. "Global" erweitern: Globale UI-Texte in Config und Content-View

Ziel: "Global" soll im Admin-Kontext ein klarer Bereich sein, in dem globale UI-Texte (z.B. Titel, allgemeine Button-Beschriftungen) gepflegt werden. Du erweiterst das Datenmodell und die Content-View entsprechend.

### 2.1 Datenmodell in `config/models.py` erweitern

1. Öffne `config/models.py` und finde die Definition der UI-Config-Klasse (z.B. `ExhibitUIConfig`).
2. Lege eine neue Dataklasse für globale UI-Texte an, z.B.:
   - `GlobalUITexts` mit Feldern wie (Beispiele, an Bedürfnisse im Code anpassen):
     - `global_page_title: Optional[str] = None`
     - `home_button_label: Optional[str] = None`
     - ggf. weitere globale Texte, die Kivy später benötigt (Global-Seite, Buttons).
3. Ergänze die UI-Config-Klasse um ein entsprechendes Feld, z.B.:
   - `global_texts: Optional[GlobalUITexts] = None`
4. Achte darauf:
   - Alle neuen Felder müssen Default-Werte haben (z.B. `None` oder sinnvolle Strings), damit bestehende `exhibit_config.json`-Dateien weiterhin gültig bleiben.
   - Die neue Struktur darf keine UI-Framework-spezifischen Objekte enthalten, nur einfache Daten (Strings etc.).

### 2.2 Default-Werte und Validierung in `config/service.py`

1. Öffne `config/service.py` und finde `_default_config_dict()`.
2. Erweitere die default-Config im `"ui"`-Bereich so, dass zusätzlich zu `"title"` und `"language"` auch Default-Werte für `global_texts` gesetzt werden, z.B.:
   - `"global_texts": {"global_page_title": "Global", "home_button_label": "Home"}`
3. Ergänze die Validierungslogik (z.B. in `validate_config`):
   - Wenn `ui.global_texts` vorhanden ist, müssen die enthaltenen Felder Strings (oder `null`) sein.
   - Falls `ui.global_texts` fehlt, wird dies **nicht** als Fehler gewertet; die Anwendung nutzt dann später Fallback-Werte.

### 2.3 Global-Seite in `ui_admin_streamlit/content_view.py` ausbauen

1. Öffne `ui_admin_streamlit/content_view.py`.
2. Suche in `render()` (oder der Hauptfunktion) den Block, der die Global-Seite (`PAGE_ID_GLOBAL`) rendert.
3. Erweitere diesen Block wie folgt:
   - Lade `cfg = load_config()` wie gehabt.
   - Stelle sicher, dass beim Rendern ein Objekt für `cfg.ui.global_texts` vorhanden ist:
     - Wenn `cfg.ui.global_texts` `None` ist, erzeuge ein temporäres Objekt mit Defaults (`GlobalUITexts(...)`).
   - Füge zu dem bestehenden Textfeld für `cfg.ui.title` zusätzliche Eingabefelder hinzu:
     - Textfeld für `global_page_title`.
     - Textfeld für `home_button_label`.
     - Weitere Felder nur, wenn sie im Modell definiert wurden.
   - Beim Speichern:
     - Schreibe die geänderten Werte zurück in `cfg.ui.global_texts`.
     - Stelle sicher, dass das aktualisierte `cfg` über die Service-Schicht persistiert wird (verwende die vorhandene Speichermethode im File).

4. Achte darauf, dass:
   - Bei nicht gesetzten Feldern `None` oder leere Strings zulässig sind.
   - Es keinen Absturz gibt, wenn ältere Configs noch kein `global_texts`-Feld besitzen.

### 2.4 Doku `content_view_current.md` aktualisieren

1. Öffne `notes/current/content_view_current.md`.
2. Ergänze den Abschnitt zur Global-Seite so, dass jetzt beschrieben ist:
   - Die Global-Seite erlaubt die Bearbeitung von:
     - `cfg.ui.title` (Ausstellungstitel),
     - `cfg.ui.global_texts.global_page_title`,
     - `cfg.ui.global_texts.home_button_label`,
     - sowie weiterer globaler Texte, falls vorhanden.
3. Stelle sicher, dass die Beschreibung exakt zum realen Verhalten in `content_view.py` passt.

> Wichtig: Du hast in diesem Schritt die `#file:current`-Datei `notes/current/content_view_current.md` angepasst, weil Du die Global-Seite in `content_view.py` erweitert hast.

---

## 3. Harte ID `"layer1_conv1"` entkoppeln

Ziel: Die Anwendung soll nicht von einer speziellen Standard-ID abhängen. `"layer1_conv1"` soll als magische ID verschwinden, ohne bestehende Configs zu zerstören.

### 3.1 Vorkommen von `"layer1_conv1"` identifizieren

1. Suche im gesamten Projekt nach dem String `"layer1_conv1"`.
2. Notiere Dir pro Fundstelle:
   - Datei und Kontext (z.B. Default-Config, Fallback in Content-View, Kommentar).
   - Ob die Stelle **funktional** (Logik) oder nur **dokumentarisch** ist.

### 3.2 Default-Config in `config/service.py` anpassen

1. Öffne `config/service.py` und gehe zu `_default_config_dict()`.
2. Dort wird aktuell ein UI-Layer mit `id: "layer1_conv1"` erzeugt und ein `viz_preset` mit `layer_id: "layer1_conv1"`.
3. Ändere diese Defaults so:
   - Verwende eine generischere ID, z.B. `"layer_1_default"`.
   - Passe das zugehörige `viz_preset` an, sodass `layer_id` auf diese neue Default-ID zeigt.
4. Achte darauf:
   - Es darf keine weitere Logik geben, die explizit `"layer1_conv1"` erwartet.
   - Die Default-Config funktioniert weiterhin, wenn noch keine `exhibit_config.json` existiert.

### 3.3 Fallback in `ui_admin_streamlit/content_view.py` anpassen

1. In `content_view.py`, in `render()`, existiert eine Stelle, die bei leerer `cfg.ui.layers` einen neuen Layer mit ID `"layer1_conv1"` anlegt.
2. Passe diese Stelle so an:
   - Erzeuge einen Default-Layer mit einer generischen ID (z.B. `"layer_1_default"`).
   - Idealerweise delegierst Du das Erzeugen eines Default-Layers an eine Funktion in `config/service.py` (z.B. `create_default_ui_layer()`), damit Default-Logik zentral bleibt.
3. Stelle sicher, dass
   - keine Stelle im UI-Code mehr davon ausgeht, dass der erste Layer zwingend `"layer1_conv1"` heißt.

### 3.4 Dokumentation und Kommentare anpassen

1. Entferne in `config/models.py` Kommentare oder Beispielwerte, in denen `"layer1_conv1"` als besondere Standard-ID dargestellt wird. Ersetze sie durch generische IDs (z.B. `"layer_1"` oder `"example_layer"`).
2. Öffne `notes/current/config_view_current.md` und `notes/current/content_view_current.md`:
   - Ersetze textuelle Bezüge auf `"layer1_conv1"` durch eine Beschreibung, dass Defaults generische IDs verwenden und keine magische ID vorausgesetzt wird.
3. Öffne `notes/current/core_current.md`:
   - Prüfe, ob dort `"layer1_conv1"` erwähnt ist.
   - Wenn ja, passe die Beschreibung an das neue Verhalten an.

> Wichtig: Du hast in diesem Schritt mehrere `#file:current`-Dateien angepasst (`config_view_current.md`, `content_view_current.md`, ggf. `core_current.md`), weil Du die Bedeutung der Default-Layer-IDs geändert hast.

---

## 4. Config-Struktur für "Favoriten pro Kivy-Seite" einführen

Ziel: In der Config wird explizit abgelegt, welche Favoriten pro `model_layer_id` für den Kivy-Kino-View aktiv sind (max. 3). Diese Struktur ist UI-neutral und wird später von Content-View und Kivy gemeinsam genutzt.

### 4.1 Bestehende Favoritenstruktur verstehen

1. Lies in `config/service.py` die Implementierung von `get_favorites_for_model_layer(cfg, model_layer_id, max_count=3)` genau durch.
2. Lies in `ui_admin_streamlit/feature_view/favorites.py` die Funktionen:
   - `get_layer_favorites(raw_cfg, ui_layer_id)`
   - `upsert_favorite(raw_cfg, ui_layer_id, fav)`
   - `delete_favorite(raw_cfg, ui_layer_id, fav_name)`
3. Stelle sicher, dass Du verstehst:
   - Wie Favoriten in `ui.layers[*].metadata.favorites` abgelegt werden.
   - Welche Felder ein Favorit hat (Name, `layer_id`, `preset`, `preset.model_layer_id`, ...).

### 4.2 Neue Selektionsstruktur in `config/models.py`

1. Öffne `config/models.py`.
2. Ergänze die UI-Config-Klasse (z.B. `ExhibitUIConfig`) um eine neue Struktur für die Kivy-Favoriten-Auswahl, z.B.:
   - `kivy_favorites: Dict[str, List[str]] = field(default_factory=dict)`
     - Schlüssel: `model_layer_id`
     - Wert: Liste von Favoriten-Referenzen (z.B. Favoriten-Namen oder IDs – wähle das, was in der aktuellen Favoritenstruktur eindeutig ist).
3. Dokumentiere in einem Kommentar:
   - Dass `kivy_favorites` nur speichert, **welche** Favoriten pro `model_layer_id` aktiv sind.
   - Dass die eigentlichen Favoriten weiter in `ui.layers[*].metadata.favorites` liegen.

### 4.3 Service-Funktionen in `config/service.py`

1. Öffne `config/service.py`.
2. Stelle sicher, dass `_default_config_dict()` `ui.kivy_favorites` standardmäßig auf ein leeres Dict setzt (oder den entsprechenden Default in der Dataklasse nutzt).
3. Implementiere zwei neue Hilfsfunktionen:

   - `def get_selected_kivy_favorites(cfg, model_layer_id: str) -> List[dict]:`
     - Lies alle Favoriten-Referenzen aus `cfg.ui.kivy_favorites.get(model_layer_id, [])`.
     - Ermittle zugehörige Favoriten in `ui.layers[*].metadata.favorites`.
     - Filtere nicht existierende Referenzen heraus.
     - Begrenze die Ergebnisliste auf `MAX_FAVORITES_PER_MODEL_LAYER` Einträge.

   - `def set_selected_kivy_favorites(cfg, model_layer_id: str, favorite_ids: List[str]) -> None:`
     - Entferne Dubletten aus `favorite_ids`.
     - Begrenze auf `MAX_FAVORITES_PER_MODEL_LAYER` Einträge.
     - Filtere IDs heraus, für die es keinen entsprechenden Favoriten in `ui.layers[*].metadata.favorites` gibt.
     - Schreibe die bereinigte Liste in `cfg.ui.kivy_favorites[model_layer_id]`.

4. Ändere **keine** bestehende Public-Funktion in ihrer Signatur. Du fügst nur neue Funktionen hinzu.

### 4.4 Migration in `config/migrations.py`

1. Öffne `config/migrations.py`.
2. Füge eine Migration hinzu, die bei älteren Configs sicherstellt:
   - Wenn `ui.kivy_favorites` fehlt, dann wird es als leeres Mapping/Datenstruktur angelegt.
   - Optional (nur wenn fachlich gewünscht): Wähle als Erstinitialisierung pro `model_layer_id` die ersten bis zu `MAX_FAVORITES_PER_MODEL_LAYER` vorhandenen Favoriten. Wenn das nicht klar definiert ist, lass die Struktur leer.
3. Kommentiere diese Migration so, dass klar ist:
   - Ab welcher Version `ui.kivy_favorites` eingeführt wurde.
   - Dass sie keine Favoriten löscht oder umbenennt.

### 4.5 Doku `config_view_current.md` aktualisieren

1. Öffne `notes/current/config_view_current.md`.
2. Ergänze einen Abschnitt zur neuen Struktur `ui.kivy_favorites`:
   - Beschreibe den Pfad und das Datenformat (`model_layer_id -> Liste von Favoriten-Referenzen`).
   - Erwähne, dass maximal `MAX_FAVORITES_PER_MODEL_LAYER` Einträge pro Modell-Layer gespeichert werden.

> Wichtig: Du hast in diesem Schritt `notes/current/config_view_current.md` angepasst, weil Du die Config-Struktur erweitert hast.

---

## 5. Content-View: Auswahl der Favoriten pro `model_layer_id`

Ziel: In der Content-View wird pro `model_layer_id`-Seite bestimmt, welche Favoriten im Kino-View angezeigt werden (max. `MAX_FAVORITES_PER_MODEL_LAYER`).

### 5.1 UI im `content_view` für Favoriten-Auswahl

1. Öffne `ui_admin_streamlit/content_view.py`.
2. Finde den Code-Block, der eine Seite für einen bestimmten `model_layer_id` rendert (Modell-Layer-Seite).
3. Unterhalb der bestehenden Text- und Inhaltselemente für diesen Modell-Layer fügst Du eine neue Sektion ein, z.B. "Favoriten-Auswahl für diese Kivy-Seite":
   - Hole eine Liste **aller** Favoriten für diesen `model_layer_id` über eine Service-Funktion:
     - Entweder `get_favorites_for_model_layer(cfg, model_layer_id, max_count=None)` (falls anpassbar),
     - oder eine neue Hilfsfunktion, die alle Favoriten dieses Modell-Layers ohne Begrenzung zurückgibt.
   - Hole die aktuelle Auswahl für diesen `model_layer_id` über `get_selected_kivy_favorites(cfg, model_layer_id)` oder direkt aus `cfg.ui.kivy_favorites`.
   - Baue in Streamlit eine Darstellung, in der pro Favorit (z.B. identifiziert über seinen Namen):
     - der Name angezeigt wird,
     - eine Checkbox vorhanden ist, ob dieser Favorit im Kino aktiv sein soll.

### 5.2 Begrenzung und Speichern

1. Wenn der Benutzer die Seite speichert (z.B. über einen "Speichern"-Button):
   - Lies alle Checkbox-Zustände aus.
   - Zähle, wie viele Favoriten ausgewählt wurden.
   - Wenn mehr als `MAX_FAVORITES_PER_MODEL_LAYER` ausgewählt sind:
     - Entscheide Dich für eine der folgenden Varianten (im Code klar ersichtlich):
       - Entweder zeigst Du eine Fehlermeldung an und speicherst nicht.
       - Oder Du beschränkst die Auswahl automatisch auf die ersten `MAX_FAVORITES_PER_MODEL_LAYER` und zeigst einen Hinweistext an.
   - Übergib die final ausgewählte Liste an `set_selected_kivy_favorites(cfg, model_layer_id, selected_ids)`.
   - Speichere die Config wie bisher üblich.

2. Behandle folgende Edge Cases sauber:
   - Es gibt keine Favoriten für diesen `model_layer_id`:
     - Zeige nur einen Hinweistext (z.B. "Für diesen Modell-Layer existieren noch keine Favoriten. Lege Favoriten in der Feature-View an.")
     - Keine Checkboxen anzeigen.
   - In `ui.kivy_favorites` sind Favoriten referenziert, die nicht mehr existieren:
     - Bereinige diese Referenzen beim Laden der Seite (über `get_selected_kivy_favorites`).
     - Speichere beim nächsten Speichern eine bereinigte Liste zurück.

### 5.3 Doku `content_view_current.md` aktualisieren

1. Öffne `notes/current/content_view_current.md`.
2. Ergänze im Abschnitt zur modell-layer-spezifischen Seite eine Beschreibung der neuen Favoriten-Auswahl:
   - Erwähne, dass pro `model_layer_id` bis zu `MAX_FAVORITES_PER_MODEL_LAYER` Favoriten ausgewählt werden können.
   - Beschreibe, wo in der Config diese Auswahl gespeichert wird (`ui.kivy_favorites[model_layer_id]`).
3. Entferne oder passe Aussagen an, die bisher suggerieren, dass die Kino-Favoriten-Auswahl nur in der Feature-View stattfindet.

> Wichtig: Du hast erneut `notes/current/content_view_current.md` angepasst, weil sich das Verhalten der Content-View geändert hat.

---

## 6. Kivy-Kino-View an neue Favoriten-Auswahl und globale Texte anpassen

Ziel: Kivy liest die in der Config getroffene Favoriten-Auswahl und die globalen UI-Texte und visualisiert diese; Kivy selbst entscheidet nicht mehr, **welche** Favoriten aktiv sind.

### 6.1 Favoriten-Beschaffung in `ui_kino_kivy/app.py` umstellen

1. Öffne `ui_kino_kivy/app.py`.
2. Finde die Stellen, an denen aktuell `get_favorites_for_model_layer(cfg, model_layer_id)` oder `get_favorites_for_model_layer(..., max_count=3)` aufgerufen wird.
3. Ersetze diese Aufrufe durch die neue Funktion `get_selected_kivy_favorites(cfg, model_layer_id)` aus `config/service.py`.
4. Stelle sicher, dass der Kivy-Code **keine** eigene Limitierung auf 3 Favoriten mehr vornimmt. Die Limitierung geschieht jetzt durch die Config/Service-Schicht.

### 6.2 UI-Verhalten bei mehreren Favoriten

1. Analysiere die aktuelle Darstellung von Favoriten im Kino-View (z.B. Buttons am Rand, Auswahlmenü).
2. Implementiere, falls noch nicht vorhanden, eine UI-Logik für den Fall, dass mehr als ein Favorit für einen `model_layer_id` aktiv ist:
   - Beispiel: Ein "↦"-Button, der zwischen den aktiven Favoriten durchschaltet.
   - Oder: Mehrere Buttons, einer pro Favorit.
3. Die genaue Darstellung richtest Du nach bestehenden Patterns im Kivy-Code aus. Wichtig ist nur:
   - Die Anzahl der dargestellten Favoriten entspricht der in der Config getroffenen Auswahl.
   - Es gibt keinen versteckten Sonderfall mehr, der implizit von "max. 3" im Kino-View ausgeht.

### 6.3 Globale UI-Texte in Kivy verwenden

1. Bleibe in `ui_kino_kivy/app.py`.
2. Suche alle Stellen, an denen globale Texte oder Button-Beschriftungen aktuell hart im Code stehen, insbesondere:
   - Text des Global-Buttons.
   - Titelzeile.
   - ggf. weitere wiederkehrende Texte auf der Globalseite.
3. Ersetze diese Hardcodings so, dass Kivy die Werte aus `cfg.ui.global_texts` (bzw. den von Dir eingeführten Feldern) liest:
   - Wenn ein Text in der Config `None` oder leer ist, verwende denselben Fallback-Wert wie in `_default_config_dict()`.
4. Achte darauf, dass Kivy nur liest und nicht in die Config schreibt.

### 6.4 Doku `kino_view_current.md` aktualisieren

1. Öffne `notes/current/kino_view_current.md`.
2. Ergänze/aktualisiere die Beschreibung:
   - Wie die Globalseite ihre Texte aus `cfg.ui.title` und `cfg.ui.global_texts` bezieht.
   - Wie pro `model_layer_id` die Favoriten aus der Config-Selektionsstruktur (`ui.kivy_favorites`) bestimmt werden.
   - Wie der Fall mit mehreren aktiven Favoriten pro Seite im UI gehandhabt wird (Wechsel-Mechanismus).
3. Stelle klar, dass:
   - Die Auswahl, **welche** Favoriten aktiv sind, in der Content-View getroffen wird.
   - Die Favoriten selbst in der Feature-View definiert und gepflegt werden.

> Wichtig: Du hast in diesem Schritt `notes/current/kino_view_current.md` angepasst, weil sich das Verhalten des Kino-Views geändert hat.

---

## 7. Feature-View: Rolle auf Favoriten-Verwaltung begrenzen

Ziel: Die Feature-View bleibt der Ort für das Anlegen/Bearbeiten/Löschen von Favoriten. Sie entscheidet **nicht**, welche Favoriten im Kino-View aktiv sind.

### 7.1 Code in `feature_view` prüfen und bereinigen

1. Öffne `ui_admin_streamlit/feature_view/view.py` und `ui_admin_streamlit/feature_view/favorites.py`.
2. Suche nach Stellen, an denen:
   - von einer Begrenzung auf "maximal 3 Favoriten" pro Layer ausgegangen wird,
   - Kivy-spezifisches Verhalten (z.B. "Seite" im Kino-View) direkt erwähnt wird.
3. Entferne oder passe solche Stellen so an, dass:
   - Feature-View beliebig viele Favoriten pro UI-/Modell-Layer verwalten kann.
   - Keine Annahmen mehr über "max. 3 im Kino" direkt in der Feature-View kodiert sind.

### 7.2 Doku `feature_view_current.md` aktualisieren

1. Öffne `notes/current/feature_view_current.md`.
2. Aktualisiere die Beschreibung der Feature-View:
   - Betone, dass hier Favoriten erstellt, geändert und gelöscht werden.
   - Erkläre, dass die Auswahl, welche Favoriten im Kino angezeigt werden, in der Content-View erfolgt.
   - Beschreibe kurz das Datenformat eines Favoriten (inkl. `preset.model_layer_id`).
3. Füge einen Querverweis auf `notes/current/content_view_current.md` ein.

> Wichtig: Du hast in diesem Schritt `notes/current/feature_view_current.md` angepasst, weil sich die Rolle der Feature-View klarer abgegrenzt hat.

---

## 8. Alle `notes/current/*_current.md`-Dateien final konsistent machen

Nach allen Codeänderungen prüfst Du die Dokumentation in `notes/current/` systematisch.

### 8.1 `config_view_current.md`

- Prüfe die Beschreibung der Config-Struktur insgesamt.
- Stelle sicher, dass:
  - die neuen Felder `ui.global_texts` und `ui.kivy_favorites` korrekt und vollständig beschrieben sind,
  - keine überholten Verweise auf `"layer1_conv1"` als Sonderfall existieren.

### 8.2 `content_view_current.md`

- Prüfe, ob alle Änderungen an der Content-View korrekt dokumentiert sind:
  - Erweiterung der Global-Seite.
  - Auswahl von Favoriten pro `model_layer_id`.
- Entferne veraltete Aussagen zur Favoritensteuerung.

### 8.3 `kino_view_current.md`

- Prüfe die Beschreibung der Kino-View-Logik:
  - Nutzung globaler UI-Texte.
  - Nutzung von `ui.kivy_favorites`.
  - Verhalten bei mehreren Favoriten.

### 8.4 `core_current.md`

- Prüfe, ob dort Annahmen über feste Layer-IDs oder die Rolle von `"layer1_conv1"` gemacht werden.
- Passe die Beschreibungen an, falls nötig, sodass:
  - `ModelEngine` und `viz_presets` keine magische ID benötigen.

### 8.5 `feature_view_current.md`

- Stelle sicher, dass die Rolle der Feature-View eindeutig beschrieben ist.
- Erwähne, dass die eigentliche Favoriten-Auswahl für den Kino-View in der Content-View passiert.

---

## 9. Abschließender konzeptioneller Check

Am Ende machst Du einen bewussten, konzeptionellen Kontrollgang durch die Zusammenhänge. Du änderst dabei nur noch etwas, wenn Dir Inkonsistenzen auffallen.

### 9.1 Favoriten-Lebenszyklus

- Gehe gedanklich durch:
  1. Anlegen/Bearbeiten/Löschen eines Favoriten in der Feature-View.
  2. Speichern in `ui.layers[*].metadata.favorites`.
  3. Auswahl pro `model_layer_id` in der Content-View und Speichern in `ui.kivy_favorites`.
  4. Laden und Anzeigen der ausgewählten Favoriten im Kino-View.
- Prüfe, ob in keinem der Schritte mehr eine harte Annahme über `"layer1_conv1"` oder "max. 3" außerhalb der zentralen Konstante gemacht wird.

### 9.2 Global-Konzept

- Prüfe, ob die Rolle von "Global" konsistent ist:
  - In der Admin-Content-View als Ort zur Pflege globaler UI-Texte.
  - Im Kino-View als Besucher-Globalseite, die diese Texte nutzt.
- Stelle sicher, dass in der Doku diese beiden Sichten klar getrennt beschrieben sind und nicht verwechselt werden.

### 9.3 Separation of Concerns

- Kontrolliere stichprobenartig, dass:
  - `config/*` keine UI-spezifischen Layout-Details enthält.
  - Kivy- und Streamlit-Code nur über `config.service` oder klar definierte Schnittstellen mit der Config interagieren.
  - Keine neue, versteckte Kopplung zwischen UI-Code und hart codierten IDs entstanden ist.

Wenn alle Punkte erfüllt sind und die Doku unter `notes/current/*_current.md` mit dem Code übereinstimmt, ist die Implementierung der in `change_analyse_v0.md` beschriebenen Änderungen fachlich sauber vorbereitet.
