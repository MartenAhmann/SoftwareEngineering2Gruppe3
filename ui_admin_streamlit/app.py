# ui_admin_streamlit/app.py
import streamlit as st
import sys
from pathlib import Path
import subprocess
# Projekt-Root auf sys.path legen
sys.path.append(str(Path(__file__).resolve().parent.parent))
# Views (modular)
from ui_admin_streamlit.content_view import render as render_content
from ui_admin_streamlit.feature_view import render as render_feature
# Optional: später
# from ui_admin_streamlit.layout_view import render as render_layout

def main():
    st.set_page_config(page_title="CNN Exhibit – Admin", layout="centered")

    st.title("CNN Exhibit – Adminpanel (Prototyp)")

    # ------------------------------
    # Kinomodus starten
    # ------------------------------
    project_root = Path(__file__).resolve().parent.parent
    kino_rel_path = Path("ui_kino_kivy") / "app.py"

    if st.button("Kinomodus starten"):
        try:
            # Entspricht:  (im Projektroot)
            #   python ui_kino_kivy/app.py
            subprocess.Popen(
                [sys.executable, str(kino_rel_path)],
                cwd=str(project_root),
            )
            st.info("Kinomodus wurde gestartet (separates Fenster).")
        except Exception as e:
            st.error(f"Kinomodus konnte nicht gestartet werden: {e}")

    # ------------------------------
    # Oben mittige Hauptnavigation
    # ------------------------------
    nav_options = ["content", "layout", "feature view"]
    if "main_nav" not in st.session_state:
        st.session_state.main_nav = "content"

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        # entferne 'selection', nutze key für Zustand
        selected = st.segmented_control(
            "Navigation",
            nav_options,
            key="main_nav_ctrl",
            help="Bereich wählen"
        )
        # Wenn None (erster Lauf), auf Default setzen
        if selected is None:
            selected = st.session_state.get("main_nav", "content")
        st.session_state.main_nav = selected

    st.divider()

    # ------------------------------
    # Dispatcher
    # ------------------------------
    if st.session_state.main_nav == "feature view":
        render_feature()
    elif st.session_state.main_nav == "content":
        render_content()
    else:
        st.subheader("Layout")
        st.info("Layout-Editor folgt. Hier werden später Positionen/Grids für Kivy konfiguriert.")

if __name__ == "__main__":
    main()