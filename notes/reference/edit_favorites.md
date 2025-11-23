# Problem-Analyse: Editieren von Favoriten in der Feature-View

1. **Preset-Übernahme beim Laden eines Favoriten überschreibt nachträgliche UI-Änderungen**
   - Beim Auswählen eines gespeicherten Favoriten (`selected_fav_name != "–"`) wird in `feature_view/view.py` der komplette UI-State `st_data` (inkl. `blend_mode`, `cmap`, `overlay`, `alpha`, `mode`, `channels`, `k`, `model_layer_id`, `fav_name` usw.) direkt aus dem geladenen Preset überschrieben.
   - Zusätzlich werden im gleichen Block unmittelbar die zugehörigen Streamlit-Widget-States (`st.session_state[...]`) für alle relevanten Controls (Selectboxen, Radio, Checkbox, Slider) auf die Werte aus dem Preset gesetzt.
   - Dieser Block wird bei jedem Render-Durchlauf erneut ausgeführt, solange im "Favorit laden"-Selectbox ein Favoritenname ausgewählt ist.
   - Wenn der Nutzer nach dem Laden eines Favoriten z. B. die Checkbox "Originalbild überlagern" oder die Regler/Selectboxen für Farbschema, Overlay-Alpha oder Blend-Mode interaktiv ändert, werden diese Änderungen zwar kurz im UI wirksam, beim nächsten Render-Durchlauf aber wieder durch die Preset-Werte überschrieben, weil weiterhin derselbe Favorit im Dropdown ausgewählt ist.
   - Das erklärt das beobachtete Verhalten: "es refresht kurz und es kommt der Urzustand wieder zurück" – die interaktiven Änderungen werden nicht dauerhaft in `st_data` gehalten, sondern direkt wieder durch die geladenen Preset-Daten ersetzt.

2. **Kopplung von Favoriten-Auswahl und kontinuierlicher Preset-Anwendung**
   - Die Selectbox "Favorit laden" dient aktuell nicht nur zum einmaligen Laden eines Presets, sondern fungiert implizit als dauerhafter Modus-Schalter: solange ein Favorit ausgewählt bleibt, wird dessen Preset bei jedem Rendern erneut auf den State angewendet.
   - Dadurch gibt es keinen Zustand "Favorit ist geladen, aber nun werden nur noch lokale Änderungen vorgenommen"; stattdessen werden lokale Änderungen immer wieder durch das Ursprungs-Preset übersteuert, solange der Favorit im Dropdown aktiv bleibt.
   - Dieses Muster verhindert effektiv das nachträgliche Editieren eines Favoriten im UI, weil zwischen "aktueller UI-State" und "ausgewählter Favorit" keine Entkopplung erfolgt.

3. **Löschen von Channels aus der Liste ist nur temporär wirksam**
   - Das Entfernen von Channels aus `st_data["channels"]` funktioniert zur Laufzeit über die "✕"-Buttons korrekt (die Liste wird angepasst und `st.rerun()` aufgerufen).
   - Wenn jedoch ein Favorit aktiv im Dropdown ausgewählt bleibt, setzt der oben beschriebene Preset-Ladeblock bei jedem Render-Durchlauf `st_data["channels"]` wieder auf die `channels`-Liste aus dem gespeicherten Preset zurück.
   - Dadurch erscheinen gelöschte Channels nach einem kurzen Refresh erneut in der Liste, weil der State nicht aus dem aktuellen UI, sondern erneut aus dem ursprünglichen Preset rekonstruiert wird.
   - Die beobachtete Symptomatik "zusätzliche Channels eintragen funktioniert, nachträgliches Löschen aber nicht" ergibt sich daraus, dass:
     - Hinzugefügte Channels in `st_data["channels"]` berücksichtigt werden, solange das Preset nicht erneut streng aus der Config angewendet wird.
     - Beim (erneuten) Anwenden des Favoriten-Presets aus der Config die `channels`-Liste exakt aus dem gespeicherten Stand übernommen wird und damit alle UI-Löschungen wieder verwirft.

4. **Favoriten-Speicherlogik aktualisiert Config, aber nicht den Ladevorgang**
   - Beim Klick auf "Als Favorit speichern/aktualisieren" wird über `_current_preset_dict()` ein Preset aus dem aktuellen `st_data` erzeugt und via `upsert_favorite()` in der Raw-Config gespeichert.
   - Diese Änderung landet korrekt im Config-File, aber der direkt anschließende Render-Durchlauf verwendet weiterhin den aktuell im Dropdown ausgewählten Favoriten als Quelle für den State-Reset.
   - Wenn der Nutzer denselben Favoriten-Namen wie zuvor verwendet, kann es dazu kommen, dass der Laden-Block weiterhin mit einem veralteten Preset aus einem früheren Render-Durchlauf arbeitet, solange der Selectbox-State nicht explizit zurückgesetzt oder der Favorit neu ausgewählt wird.
   - Das Zusammenspiel aus dauerhafter Preset-Anwendung beim Rendern und der Selectbox, die auf demselben Favoriten-Namen verharrt, führt dazu, dass sich UI-Änderungen subjektiv "nicht merken lassen", obwohl sie prinzipiell in die Config geschrieben werden können.

5. **Kein expliziter Übergang von "Favorit laden" zu "Favorit bearbeiten"**
   - Im aktuellen Design existiert keine klare Trennung zwischen dem Moment des einmaligen Ladens eines Favoriten (Snapshot der damaligen Preset-Werte) und der Phase, in der der Nutzer diese Werte frei bearbeitet.
   - Stattdessen ist das Laden eines Favoriten an den permanenten Zustand der Selectbox gekoppelt, was im Effekt die UI in einen Modus versetzt, in dem die Preset-Werte dauerhaft dominieren und lokale Änderungen immer wieder überschrieben werden.
   - Dieses fehlende Übergangsmodell ist die zentrale Ursache dafür, dass das nachträgliche Bearbeiten eines bestehenden Favoriten im UI nicht zuverlässig funktioniert.

