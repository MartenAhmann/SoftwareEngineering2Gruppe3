# config/migrations.py
"""
Migrations-System für Exhibit-Konfigurationen.
Ermöglicht Upgrades zwischen verschiedenen Config-Versionen.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _migrate_1_0_to_1_1(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Migriert von Version 1.0 auf 1.1.

    Fügt ui.global_texts und ui.kivy_favorites hinzu, falls sie fehlen.
    Löscht keine bestehenden Daten.
    """
    logger.info("Migriere Config von 1.0 zu 1.1")

    ui = raw_dict.setdefault("ui", {})

    # Globale UI-Texte nur setzen, wenn noch nicht vorhanden
    if "global_texts" not in ui or ui.get("global_texts") is None:
        ui["global_texts"] = {
            "global_page_title": ui.get("title", "Global"),
            "home_button_label": "Home",
        }

    # Kivy-Favoriten-Auswahl initial leer
    if "kivy_favorites" not in ui or ui.get("kivy_favorites") is None:
        ui["kivy_favorites"] = {}

    raw_dict["version"] = "1.1"
    return raw_dict


def migrate_config(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Migriert eine Config-Dict auf die aktuelle Version.

    Args:
        raw_dict: Rohe Config als Dict

    Returns:
        Migrierte Config (kann das Original sein, falls keine Migration nötig)
    """
    version = raw_dict.get("version", "1.0")

    logger.info(f"Config-Version: {version}")

    # Migrations-Chain
    if version == "1.0":
        raw_dict = _migrate_1_0_to_1_1(raw_dict)
        version = "1.1"

    if version == "1.1":
        # Aktuelle Version, keine weitere Migration nötig
        return raw_dict

    logger.warning(f"Unbekannte Config-Version: {version}. Versuche trotzdem zu laden.")
    return raw_dict


# Beispiel für zukünftige Migration:
# def _migrate_1_1_to_2_0(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Migriert von Version 1.1 zu 2.0.
#     Beispiel: Ändert Struktur oder fügt neue Pflichtfelder hinzu.
#     """
#     logger.info("Migriere Config von 1.1 zu 2.0")
#
#     # Beispielhafte Änderungen:
#     if "altes_feld" in raw_dict:
#         raw_dict["neues_feld"] = raw_dict.pop("altes_feld")
#
#     raw_dict["version"] = "2.0"
#     return raw_dict
