from __future__ import annotations

from typing import Dict, Any, List


def get_layer_favorites(raw_cfg: Dict[str, Any], layer_ui_id: str) -> List[Dict[str, Any]]:
    """
    Liefert die Favoritenliste für einen UI-Layer aus dem rohen Config-Dict.
    Legt die Struktur bei Bedarf an.
    """
    layers = raw_cfg.get("ui", {}).get("layers", [])
    for l in layers:
        if l.get("id") == layer_ui_id:
            metadata = l.setdefault("metadata", {})
            favs = metadata.setdefault("favorites", [])
            return favs
    return []


def upsert_favorite(raw_cfg: Dict[str, Any], layer_ui_id: str, fav: Dict[str, Any]) -> None:
    """
    Fügt einen Favoriten ein oder aktualisiert ihn (per name) in der Favoritenliste des Layers.
    """
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