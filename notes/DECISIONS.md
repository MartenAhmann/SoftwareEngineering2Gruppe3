# Entscheidungslog

# Entwickler-Entscheidungen und Konventionen

## Pflege der `_current.md`-Dateien (Config/Core/UI)

- Wenn in einem der folgenden Pakete funktionale Änderungen vorgenommen werden, **müssen** die entsprechenden `_current.md`-Dateien in `notes/current` aktualisiert werden, sodass sie den neuen Ist-Zustand beschreiben:
  - Änderungen an `config/` → `notes/config_view_current.md`
  - Änderungen an `core/` → `notes/core_current.md`
  - Änderungen an `ui_admin_streamlit/feature_view` → `notes/feature_view_current.md`
  - Änderungen an `ui_kino_kivy/` → `notes/kino_view_current.md`
  - Änderungen an `ui_admin_streamlit/content_view` -> `notes/content_view_current.md`
- Vorgehen bei Implementierungsänderungen:
  - Nach Abschluss der Implementierung kurz prüfen, welche Module/Flows betroffen sind.
  - Die zugehörigen `_current.md`-Dateien öffnen und den neuen Ist-Zustand (Datenflüsse, Flags, Events, UX-Flows) in knapper Form dokumentieren.
  - Größere Umbauten (z.B. neues State-/Event-Konzept) immer mit einem eigenen Abschnitt erläutern.
