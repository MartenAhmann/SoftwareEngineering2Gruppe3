# Task-Liste: Editieren von Favoriten in der Feature-View

## Allgemeine Meta-Aufgaben

1. **Konvention festlegen und dokumentieren**
   - Definiere explizit die Regel: Wenn irgendwo im Code Änderungen durchgeführt werden, **müssen die betroffenen `_current.md`-Dateien des jeweiligen Packages in `notes/` auch aktualisiert werden** (Ist-Zustand der Implementierung).
   - Betroffene aktuelle Übersichts-Dateien einbinden, damit sie bei Änderungen mitgepflegt werden:
     - `notes/kino_view_current.md`
     - `notes/feature_view_current.md`
     - `notes/core_current.md`
     - `notes/config_view_current.md`
   - In den Developer-Notizen kurz festhalten, wie diese Dateien gepflegt werden (z.B. nach Implementierungsänderungen kurz den neuen Ist-Zustand der relevanten Module skizzieren).

2. **Bestandsaufnahme & Code-Stellen identifizieren**
   - In `ui_admin_streamlit/feature_view/view.py` und den zugehörigen State-/Favorites-Hilfsfunktionen folgende Stellen suchen und markieren:
     - Block, der beim Auswählen eines Favoriten (`selected_fav_name != "–"` o.ä.) den kompletten `st_data`-State aus dem Preset lädt.
     - Stelle(n), an denen Streamlit-Widget-States (`st.session_state[...]`) anhand des geladenen Presets gesetzt werden.
     - Logik zum Hinzufügen/Entfernen von Channels (`st_data["channels"]`) inkl. der Buttons mit "×" und zugehörigem `st.rerun()`.
     - Hilfsfunktionen wie `_current_preset_dict()` und `upsert_favorite()`, die Favoriten aus `st_data` erzeugen und in die Config schreiben.
   - Sicherstellen, dass klar ist, welche Datenstruktur `st_data` genau hat und wie sie zwischen Render-Zyklen gehalten wird.

3. **Ist-Zustand in `_current.md`-Notizen ergänzen**
   - Auf Basis der Bestandsaufnahme die aktuellen Implementierungsdetails in den Notiz-Dateien ergänzen/aktualisieren:
     - `feature_view_current.md`: aktuelles Verhalten beim Laden und Bearbeiten von Favoriten, insbesondere Kopplung von Selectbox und State-Reset.
     - `core_current.md`: relevante Core-/Service-Funktionen (z.B. Laden/Speichern von Favoriten in der Config), falls noch nicht sauber dokumentiert.
     - `config_view_current.md`: wie Favoriten in der Config strukturiert sind und wie die View sie liest/schreibt.
     - `kino_view_current.md`: nur ergänzen, falls sich durch die Änderungen Seiteneffekte oder gemeinsame Komponenten ergeben.

---

## Fachliche/technische Aufgaben aus der Problemanalyse

4. **Entkopplung von Favoriten-Auswahl und dauerhaftem Preset-Override**
   - Ziel: Die Selectbox "Favorit laden" soll einen Favoriten **einmalig in den aktuellen UI-State laden**, danach sollen lokale UI-Änderungen nicht mehr automatisch überschrieben werden.
   - Konkrete Schritte:
     - Einen klaren Übergangszustand einführen: "Favorit wurde geladen" vs. "kein aktiver Favorit-Autoload".
       - Option A: Nach dem Laden eines Favoriten den Selectbox-Wert automatisch auf einen neutralen Wert zurücksetzen (z.B. "–" / "Kein Favorit ausgewählt").
       - Option B: Separaten Button "Favorit anwenden" einführen; die Selectbox wählt nur den Namen, und erst der Button überträgt das Preset **einmalig** in `st_data`.
     - Den Code-Block, der aktuell bei jedem Rendern prüft `if selected_fav_name != "–"` und dann `st_data` + `st.session_state` aus dem Preset überschreibt, so umbauen, dass er nur beim expliziten "Laden"-Event ausgeführt wird (z.B. via Button-Callback oder State-Flag).
     - Sicherstellen, dass nach dem einmaligen Laden **kein** weiterer automatischer Preset-Reset im normalen Renderpfad erfolgt.

5. **Klare Phase "Favorit bearbeiten" einführen**
   - Ziel: Nachdem ein Favorit geladen wurde, soll der Nutzer frei an UI-Controls (Blend-Mode, Farbschema, Overlay-Alpha, Channels etc.) arbeiten können, ohne dass diese Änderungen durch einen erneuten Preset-Apply überschrieben werden.
   - Konkrete Schritte:
     - Ein Flag in `st.session_state` oder `st_data` einführen, z.B. `editing_favorite_name` oder `active_favorite_snapshot`, das festhält, **welcher Favorit zuletzt geladen wurde**, ohne ihn bei jedem Render neu zu applizieren.
     - Alle Stellen prüfen, an denen aktuell der Name aus der Selectbox verwendet wird, um Logik zu triggern; Umstellung auf das neue Editing-Flag, wo sinnvoll.
     - UI-Hinweis anzeigen, z.B. "Bearbeite Favorit: <Name>" oder "Aktuelle Einstellungen sind nicht gespeichert", damit der Nutzer den Modus versteht.

6. **Preset-Anwendung nur noch ereignisgesteuert (Event-basiert)**
   - Ziel: Verhindern, dass die Preset-Anwendung implizit bei jedem Render-Durchlauf passiert.
   - Konkrete Schritte:
     - Logik so umbauen, dass das Laden eines Presets nur in klar definierten Events passiert:
       - Klick auf "Favorit laden"-/"Anwenden"-Button.
       - Optional: explizites Neu-Laden, wenn der Nutzer nach dem Speichern bewusst erneut laden möchte.
     - Prüfen, ob und wie Streamlit-Mechanismen (Button-Rückgabewert, `st.session_state`-Flags) genutzt werden, um dieses Event zu erkennen.
     - Sicherstellen, dass bei normalen UI-Interaktionen (Slider bewegen, Checkbox umschalten, Channels verändern) **kein** implizites erneutes Laden aus der Config erfolgt.

7. **Channels-Listenänderungen dauerhaft im UI-State halten**
   - Ziel: Entfernen/Hinzufügen von Channels soll konsistent im aktuellen `st_data["channels"]` bleiben, auch nach Reruns.
   - Konkrete Schritte:
     - Den Code für die "×"-Buttons prüfen und sicherstellen, dass er ausschließlich `st_data["channels"]` manipuliert und danach ein `st.rerun()` triggert.
     - Verifizieren, dass **kein** anderer Code-Block im normalen Renderpfad die Channels-Liste aus einem Preset überschreibt (siehe Entkopplung in Aufgabe 4/6).
     - Edge Cases testen:
       - Mehrere Channels nacheinander entfernen.
       - Neue Channels hinzufügen und dann wieder entfernen.
       - Kombination aus Kanaländerungen und anderen UI-Änderungen (Blend-Mode, Alpha, etc.).

8. **Favoriten-Speicherlogik robust gegen veraltete Preset-Snapshots machen**
   - Ziel: Wenn der Nutzer einen Favoriten speichert oder aktualisiert, sollen die in der Config geschriebenen Daten garantiert dem **aktuellen** UI-State entsprechen.
   - Konkrete Schritte:
     - `_current_preset_dict()` prüfen: Stellt die Funktion aus `st_data` tatsächlich alle relevanten Felder (inkl. Channels, Blend-Mode, Overlay, Alpha, etc.) zusammen?
     - Sicherstellen, dass `upsert_favorite()` immer auf dem aktuellsten `st_data` arbeitet und nicht auf einem zwischengespeicherten Preset-Snapshot.
     - Nach dem Speichern eines Favoriten überlegen:
       - Soll der Bearbeitungsmodus (`editing_favorite_name`) aktiv bleiben?
       - Soll der Nutzer einen klaren Hinweis bekommen: "Favorit <Name> wurde aktualisiert"?
       - Optional: Selectbox-Eintrag aktualisieren/neu laden, falls neue Favoriten hinzukommen.

9. **Selektives Neu-Laden nach Speichern eines Favoriten**
   - Ziel: Verhindern, dass ein veralteter Favoriten-Zustand direkt nach dem Speichern wieder angewendet wird.
   - Konkrete Schritte:
     - Nach Speichern/Updaten eines Favoriten entweder:
       - Den Autoload-Mechanismus vollständig deaktivieren (siehe Aufgaben 4/6), oder
       - Falls weiterhin ein Laden passieren soll: sicherstellen, dass der Code die frisch gespeicherte Version aus der Config neu liest.
     - Ggf. nach `upsert_favorite()` einen expliziten Refresh der Favoritenliste aus der Config anstoßen.

10. **UX-Fluss für "Favorit bearbeiten" definieren**
    - Ziel: Für den Nutzer klaren, konsistenten Flow schaffen.
    - Möglicher Flow:
      1. Favorit aus Dropdown wählen.
      2. Button "Favorit laden" klicken → Preset wird **einmalig** in `st_data` geschrieben, UI-Controls spiegeln diesen Zustand wider.
      3. Nutzer ändert nach Belieben Einstellungen und Channels.
      4. Nutzer klickt "Favorit speichern/aktualisieren" → aktueller `st_data` wird in Config persistiert.
      5. Optional: UI meldet Erfolg, Bearbeitungsmodus bleibt aktiv oder wird explizit beendet.
    - Implementiere, was von diesem Flow im Projektkontext am besten passt, und dokumentiere Abweichungen in `feature_view_current.md`.

---

## Tests & Qualitätssicherung

11. **Manuelle Testszenarien definieren**
    - Test 1: Favorit laden, nur Overlay-Checkbox und Alpha ändern, dann erneut UI interagieren → Änderungen bleiben erhalten, solange kein erneutes explizites Laden erfolgt.
    - Test 2: Favorit laden, Channels-Liste anpassen (einige löschen, einige hinzufügen), mehrfach `st.rerun()` provozieren (durch Interaktion) → Channels bleiben im geänderten Zustand.
    - Test 3: Favorit bearbeiten und mit demselben Namen speichern/aktualisieren → Config enthält neuen Stand; erneutes Laden ergibt exakt die bearbeiteten Werte.
    - Test 4: Neuen Favoriten aus aktuellem UI-State speichern → erscheint in der Favoriten-Selectbox und lässt sich korrekt laden.

12. **Automatisierbare Teile prüfen**
    - Prüfen, ob zentrale Funktionen (z.B. `upsert_favorite`, Preset-Merge-Logik, ggf. Core-Service-Funktionen) mit Unit-Tests abgedeckt werden können.
    - Mindestens einfache Tests für:
      - Übernahme des `st_data` in ein Preset-Dict und zurück.
      - Manipulation der Channels-Liste (Hinzufügen/Löschen) ohne unbeabsichtigte Seiteneffekte.

13. **Aktualisierung der `_current.md`-Notizen nach Umsetzung**
    - Nach Abschluss der Implementierungsänderungen:
      - `feature_view_current.md` aktualisieren: neuer Ablauf beim Laden/Bearbeiten/Speichern von Favoriten.
      - `core_current.md` und `config_view_current.md` ergänzen, falls sich Schnittstellen oder Datenstrukturen geändert haben.
      - `kino_view_current.md` nur anpassen, wenn betroffen.
    - Sicherstellen, dass alle relevanten Stellen in den Notizen den **neuen Ist-Zustand** korrekt widerspiegeln.

