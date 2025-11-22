from __future__ import annotations

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def validate_preset(preset: Dict[str, Any]) -> bool:
    """
    Validiert, ob ein Preset-Dict alle erforderlichen Felder hat und korrekte Typen enthält.

    Returns:
        True wenn valide, False sonst
    """
    # Pflichtfelder - model_layer_id ist optional (für Favoriten), layer_id ist optional (für VizPresets)
    required_fields = ["channels", "blend_mode", "cmap", "overlay", "alpha"]

    # Prüfe Pflichtfelder
    for field in required_fields:
        if field not in preset:
            logger.warning(f"Preset fehlt Pflichtfeld: {field}")
            return False

    # Typprüfung für layer_id oder model_layer_id (mindestens eines muss vorhanden sein)
    has_layer_id = "layer_id" in preset
    has_model_layer_id = "model_layer_id" in preset

    if not (has_layer_id or has_model_layer_id):
        logger.warning("Preset muss entweder 'layer_id' oder 'model_layer_id' enthalten")
        return False

    if has_layer_id and not isinstance(preset["layer_id"], str):
        logger.warning("Preset layer_id muss string sein")
        return False

    if has_model_layer_id and not isinstance(preset["model_layer_id"], str):
        logger.warning("Preset model_layer_id muss string sein")
        return False

    # channels muss Liste oder "topk" sein
    channels = preset["channels"]
    if not (isinstance(channels, list) or channels == "topk"):
        logger.warning("Preset channels muss Liste oder 'topk' sein")
        return False

    if isinstance(channels, list):
        if not all(isinstance(c, int) for c in channels):
            logger.warning("Preset channels Liste muss nur Integers enthalten")
            return False

    # blend_mode Prüfung
    valid_blend_modes = ["mean", "max", "sum", "weighted"]
    if preset["blend_mode"] not in valid_blend_modes:
        logger.warning(f"Ungültiger blend_mode: {preset['blend_mode']}")
        return False

    # overlay muss bool sein
    if not isinstance(preset["overlay"], bool):
        logger.warning("Preset overlay muss bool sein")
        return False

    # alpha muss float zwischen 0 und 1 sein
    alpha = preset["alpha"]
    if not isinstance(alpha, (int, float)) or not (0 <= alpha <= 1):
        logger.warning(f"Preset alpha muss zwischen 0 und 1 sein, ist: {alpha}")
        return False

    return True


def get_layer_favorites(raw_cfg: Dict[str, Any], layer_ui_id: str) -> List[Dict[str, Any]]:
    """
    Liefert die Favoritenliste für einen UI-Layer aus dem rohen Config-Dict.
    Legt die Struktur bei Bedarf an.
    Filtert ungültige Favoriten aus.
    """
    layers = raw_cfg.get("ui", {}).get("layers", [])
    for l in layers:
        if l.get("id") == layer_ui_id:
            metadata = l.setdefault("metadata", {})
            favs = metadata.setdefault("favorites", [])

            # Filtere ungültige Favoriten
            valid_favs = []
            for fav in favs:
                if "preset" in fav and validate_preset(fav["preset"]):
                    valid_favs.append(fav)
                else:
                    logger.warning(f"Ungültiger Favorit '{fav.get('name', 'unnamed')}' wird übersprungen")

            # Aktualisiere Liste mit nur validen Favoriten
            metadata["favorites"] = valid_favs
            return valid_favs
    return []


def upsert_favorite(raw_cfg: Dict[str, Any], layer_ui_id: str, fav: Dict[str, Any]) -> None:
    """
    Fügt einen Favoriten ein oder aktualisiert ihn (per name) in der Favoritenliste des Layers.
    Validiert das Preset vor dem Speichern.
    """
    # Validierung
    if "preset" not in fav:
        logger.error("Favorit muss 'preset' Feld enthalten")
        raise ValueError("Favorit muss 'preset' Feld enthalten")

    if not validate_preset(fav["preset"]):
        logger.error("Preset-Validierung fehlgeschlagen")
        raise ValueError("Ungültiges Preset")

    favs = get_layer_favorites(raw_cfg, layer_ui_id)
    for i, f in enumerate(favs):
        if f.get("name") == fav.get("name"):
            favs[i] = fav
            return
    favs.append(fav)

def delete_favorite(raw_cfg: Dict[str, Any], layer_ui_id: str, fav_name: str) -> None:
    """
    Entfernt einen Favoriten mit dem angegebenen Namen aus der Favoritenliste des Layers.
    Tut nichts, wenn der Name nicht existiert.
    """
    favs = get_layer_favorites(raw_cfg, layer_ui_id)
    remaining = [f for f in favs if f.get("name") != fav_name]
    # Liste in-place aktualisieren, damit Referenzen intakt bleiben
    favs.clear()
    favs.extend(remaining)