# config/migrations.py
"""
Migrations-System für Exhibit-Konfigurationen.
Ermöglicht Upgrades zwischen verschiedenen Config-Versionen.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def migrate_config(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migriert eine Config-Dict auf die aktuelle Version.

    Args:
        raw_dict: Rohe Config als Dict

    Returns:
        Migrierte Config (kann das Original sein, falls keine Migration nötig)
    """
    version = raw_dict.get("version", "1.0")

    logger.info(f"Config-Version: {version}")

    # Migrations-Chain
    if version == "1.0":
        # Aktuelle Version, keine Migration nötig
        return raw_dict

    # Zukünftige Migrationen würden hier hinzugefügt:
    # if version == "1.0":
    #     raw_dict = _migrate_1_0_to_1_1(raw_dict)
    #     version = "1.1"
    #
    # if version == "1.1":
    #     raw_dict = _migrate_1_1_to_2_0(raw_dict)
    #     version = "2.0"

    logger.warning(f"Unbekannte Config-Version: {version}. Versuche trotzdem zu laden.")
    return raw_dict


# Beispiel für zukünftige Migration:
# def _migrate_1_0_to_1_1(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Migriert von Version 1.0 zu 1.1.
#     Beispiel: Fügt neues Feld "metadata" zu Layern hinzu.
#     """
#     logger.info("Migriere Config von 1.0 zu 1.1")
#
#     for layer in raw_dict.get("ui", {}).get("layers", []):
#         if "metadata" not in layer:
#             layer["metadata"] = {}
#
#     raw_dict["version"] = "1.1"
#     return raw_dict
