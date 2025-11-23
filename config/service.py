# config/service.py
from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    ExhibitConfig,
    ExhibitUIConfig,
    ModelConfig,
    ModelLayerMapping,
    LayerUIConfig,
    VizPreset,
    ModelLayerContent,
    GlobalUITexts,
)
from .migrations import migrate_config

logger = logging.getLogger(__name__)

MAX_FAVORITES_PER_MODEL_LAYER = 3

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "exhibit_config.json"
LOCK_PATH = BASE_DIR / "config" / "exhibit_config.json.lock"
BACKUP_PATH = BASE_DIR / "config" / "exhibit_config.json.backup"


class FileLock:
    """
    Einfacher File-Lock-Mechanismus über Lock-Datei.
    Plattformunabhängig und ohne externe Abhängigkeiten.
    """

    def __init__(self, lock_path: Path, timeout: float = 2.0):
        self.lock_path = lock_path
        self.timeout = timeout

    def acquire(self) -> bool:
        """
        Versucht Lock zu erwerben. Wartet bis timeout.
        Returns True bei Erfolg, False bei Timeout.
        """
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                # Versuche Lock-Datei zu erstellen (exklusiv)
                # x-Modus: öffnet nur wenn Datei nicht existiert
                with self.lock_path.open("x") as f:
                    f.write(str(time.time()))
                return True
            except FileExistsError:
                # Lock existiert bereits, warte kurz
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Locks: {e}")
                return False

        logger.warning(f"Lock-Timeout nach {self.timeout}s")
        return False

    def release(self) -> None:
        """Gibt Lock frei."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception as e:
            logger.error(f"Fehler beim Freigeben des Locks: {e}")

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"Konnte Lock nicht erwerben nach {self.timeout}s")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def _default_config_dict() -> Dict[str, Any]:
    """Rohes Default-Config als Dict (JSON-kompatibel)."""
    return {
        "version": "1.1",
        "exhibit_id": "cnn_museum_01",
        "model": {
            "name": "resnet18",
            "weights": "imagenet",
            "layer_mappings": [],
        },
        "ui": {
            "title": "Wie ein neuronales Netz sieht",
            "language": "de",
            "global_texts": {
                "global_page_title": "Wie ein neuronales Netz sieht",
                "home_button_label": "Home",
            },
            "kivy_favorites": {},
            "layers": [
                {
                    "id": "layer_1_default",
                    "order": 1,
                    "button_label": "Frühe Kanten",
                    "title_bar_label": "Layer 1 – Kanten",
                    "description": "In dieser Schicht erkennt das Netz einfache Kanten und Helligkeitsübergänge.",
                    "viz_preset_id": "preset_layer1",
                    "subtitle": "Kamera-Blick auf frühe Kanten",
                    "metadata": {
                        "favorites": []
                    },
                }
            ],
        },
        "viz_presets": [
            {
                "id": "preset_layer1",
                "layer_id": "layer_1_default",
                "channels": [0],
                "blend_mode": "mean",
                "overlay": False,
                "alpha": 0.6,
                "cmap": "viridis",
            }
        ],
    }


def validate_config(cfg: ExhibitConfig) -> List[str]:
    """
    Validiert eine ExhibitConfig und gibt eine Liste von Fehlermeldungen zurück.
    Leere Liste bedeutet: Config ist valide.
    """
    errors = []

    # Prüfen: mindestens 1 Layer vorhanden
    if not cfg.ui.layers:
        errors.append("Config muss mindestens einen Layer in ui.layers enthalten")

    # Prüfen: alle viz_preset_id Referenzen existieren
    preset_ids = {p.id for p in cfg.viz_presets}
    for layer in cfg.ui.layers:
        if layer.viz_preset_id not in preset_ids:
            errors.append(
                f"Layer '{layer.id}' referenziert nicht existierenden viz_preset_id '{layer.viz_preset_id}'"
            )

    # Prüfen: model.name ist unterstützt (aktuell nur resnet18)
    supported_models = ["resnet18"]
    if cfg.model.name not in supported_models:
        errors.append(
            f"Modell '{cfg.model.name}' wird nicht unterstützt. Unterstützte Modelle: {supported_models}"
        )

    return errors


def load_config() -> ExhibitConfig:
    """Läd exhibit_config.json, legt Default an, falls nicht vorhanden."""
    if not CONFIG_PATH.exists():
        logger.info("Config-Datei nicht gefunden, erstelle Default-Config")
        save_config_dict(_default_config_dict())

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen der Config-Datei: {e}")
        logger.warning("Verwende Default-Config als Fallback")
        return _from_dict(_default_config_dict())
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Laden der Config: {e}")
        logger.warning("Verwende Default-Config als Fallback")
        return _from_dict(_default_config_dict())

    # Migration durchführen
    raw = migrate_config(raw)

    cfg = _from_dict(raw)

    # Validierung
    validation_errors = validate_config(cfg)
    if validation_errors:
        logger.warning("Config-Validierung fehlgeschlagen:")
        for err in validation_errors:
            logger.warning(f"  - {err}")
        logger.warning("Config wird trotzdem geladen, aber es können Fehler auftreten")

    return cfg


def save_config(cfg: ExhibitConfig) -> None:
    """Speichert ein ExhibitConfig-Objekt nach exhibit_config.json."""
    data = _to_dict(cfg)
    save_config_dict(data)


def save_config_dict(data: Dict[str, Any]) -> None:
    """
    Hilfsfunktion: schreibt ein rohes Dict nach exhibit_config.json.
    Verwendet File-Locking und erstellt Backup vor dem Schreiben.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    lock = FileLock(LOCK_PATH, timeout=2.0)

    try:
        with lock:
            # Backup erstellen falls Config existiert
            if CONFIG_PATH.exists():
                try:
                    shutil.copy2(CONFIG_PATH, BACKUP_PATH)
                    logger.debug("Backup erstellt")
                except Exception as e:
                    logger.warning(f"Konnte Backup nicht erstellen: {e}")

            # Config schreiben
            with CONFIG_PATH.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    except TimeoutError:
        logger.error("Timeout beim Erwerben des File-Locks für Schreibvorgang")
        raise
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Config: {e}")
        # Versuche Backup wiederherzustellen
        if BACKUP_PATH.exists():
            try:
                shutil.copy2(BACKUP_PATH, CONFIG_PATH)
                logger.info("Config aus Backup wiederhergestellt")
            except Exception as restore_error:
                logger.error(f"Konnte Backup nicht wiederherstellen: {restore_error}")
        raise

def load_raw_config_dict() -> Dict[str, Any]:
    """
    Lädt das rohe JSON als Dict ohne Konvertierung in Dataclasses.
    Legt Default an, falls Datei fehlt.
    """
    if not CONFIG_PATH.exists():
        logger.info("Config-Datei nicht gefunden, erstelle Default-Config")
        save_config_dict(_default_config_dict())

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen der Config-Datei: {e}")
        logger.warning("Verwende Default-Config als Fallback")
        return _default_config_dict()
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Laden der Config: {e}")
        logger.warning("Verwende Default-Config als Fallback")
        return _default_config_dict()

    # Migration durchführen
    raw = migrate_config(raw)
    return raw

def save_raw_config_dict(data: Dict[str, Any]) -> None:
    """
    Speichert das rohe Dict exakt zurück (ohne Dataclass-Konvertierung).
    """
    save_config_dict(data)


def _from_dict(d: Dict[str, Any]) -> ExhibitConfig:
    """Konvertiert rohes Dict (JSON) → ExhibitConfig (Dataclasses)."""
    model_raw = d["model"]

    # Layer-Mappings deserialisieren
    mappings_raw = model_raw.get("layer_mappings", [])
    mappings = [ModelLayerMapping(**m) for m in mappings_raw]

    model_cfg = ModelConfig(
        name=model_raw["name"],
        weights=model_raw["weights"],
        layer_mappings=mappings
    )

    ui_raw: Dict[str, Any] = d["ui"]
    layers_raw: List[Dict[str, Any]] = ui_raw.get("layers", [])

    layers: List[LayerUIConfig] = []
    for ld in layers_raw:
        layer_kwargs = {
            "id": ld["id"],
            "order": ld["order"],
            "button_label": ld["button_label"],
            "title_bar_label": ld["title_bar_label"],
            "description": ld["description"],
            "viz_preset_id": ld["viz_preset_id"],
            "subtitle": ld.get("subtitle"),
            "metadata": ld.get("metadata"),
        }
        layers.append(LayerUIConfig(**layer_kwargs))

    # Neues Mapping: model_layers (optional in JSON, daher defensiv lesen)
    model_layers_raw: Dict[str, Any] = ui_raw.get("model_layers", {})
    model_layers: Dict[str, ModelLayerContent] = {}
    for ml_id, ml_cfg in model_layers_raw.items():
        # Defaults setzen, falls Felder fehlen
        model_layers[ml_id] = ModelLayerContent(
            title=ml_cfg.get("title", ml_id),
            subtitle=ml_cfg.get("subtitle"),
            description=ml_cfg.get("description", ""),
        )

    # Globale UI-Texte (optional)
    global_texts_raw = ui_raw.get("global_texts")
    global_texts: GlobalUITexts | None = None
    if isinstance(global_texts_raw, dict):
        global_texts = GlobalUITexts(
            global_page_title=global_texts_raw.get("global_page_title"),
            home_button_label=global_texts_raw.get("home_button_label"),
        )

    kivy_favorites = ui_raw.get("kivy_favorites", {}) or {}

    ui_cfg = ExhibitUIConfig(
        title=ui_raw["title"],
        language=ui_raw.get("language", "de"),
        layers=layers,
        model_layers=model_layers,
        global_texts=global_texts,
        kivy_favorites=kivy_favorites,
    )

    presets_raw: List[Dict[str, Any]] = d.get("viz_presets", [])
    presets = [VizPreset(**p) for p in presets_raw]

    return ExhibitConfig(
        exhibit_id=d["exhibit_id"],
        model=model_cfg,
        ui=ui_cfg,
        viz_presets=presets,
        version=d.get("version", "1.0")
    )


def _to_dict(cfg: ExhibitConfig) -> Dict[str, Any]:
    """Konvertiert ExhibitConfig (Dataclasses) → rohes Dict (JSON)."""
    return {
        "version": cfg.version,
        "exhibit_id": cfg.exhibit_id,
        "model": {
            "name": cfg.model.name,
            "weights": cfg.model.weights,
            "layer_mappings": [
                {
                    "ui_layer_id": m.ui_layer_id,
                    "model_layer_id": m.model_layer_id,
                    "display_name": m.display_name
                }
                for m in cfg.model.layer_mappings
            ],
        },
        "ui": {
            "title": cfg.ui.title,
            "language": cfg.ui.language,
            "layers": [
                {
                    "id": l.id,
                    "order": l.order,
                    "button_label": l.button_label,
                    "title_bar_label": l.title_bar_label,
                    "description": l.description,
                    "viz_preset_id": l.viz_preset_id,
                    "subtitle": l.subtitle,
                    "metadata": l.metadata,
                }
                for l in cfg.ui.layers
            ],
            "model_layers": {
                ml_id: {
                    "title": ml.title,
                    "subtitle": ml.subtitle,
                    "description": ml.description,
                }
                for ml_id, ml in cfg.ui.model_layers.items()
            },
            "global_texts": (
                {
                    "global_page_title": cfg.ui.global_texts.global_page_title,
                    "home_button_label": cfg.ui.global_texts.home_button_label,
                }
                if cfg.ui.global_texts is not None
                else None
            ),
            "kivy_favorites": cfg.ui.kivy_favorites,
        },
        "viz_presets": [
            {
                "id": p.id,
                "layer_id": p.layer_id,
                "channels": p.channels,
                "k": p.k,
                "blend_mode": p.blend_mode,
                "overlay": p.overlay,
                "alpha": p.alpha,
                "cmap": p.cmap,
            }
            for p in cfg.viz_presets
        ],
    }


# Hilfsfunktionen für modell-layer-basierten Content und Favoriten

def get_model_layer_content(cfg: ExhibitConfig, model_layer_id: str) -> ModelLayerContent:
    """Liefert Content für ein bestimmtes model_layer_id mit Fallbacks.

    - Falls kein Eintrag in ui.model_layers vorhanden ist, wird ein Default
      mit Titel = model_layer_id und leerer Description zurückgegeben.
    """
    if model_layer_id in cfg.ui.model_layers:
        return cfg.ui.model_layers[model_layer_id]
    return ModelLayerContent(title=model_layer_id, description="Noch nicht konfiguriert")


def get_favorites_for_model_layer(cfg: ExhibitConfig, model_layer_id: str, max_count: int = MAX_FAVORITES_PER_MODEL_LAYER) -> List[Dict[str, Any]]:
    """Liest Favoriten aus ui.layers[].metadata.favorites, gefiltert nach preset.model_layer_id.

    Gibt eine Liste von Favorite-Objekten (rohe Dicts) mit höchstens max_count Einträgen zurück.
    """
    favorites: List[Dict[str, Any]] = []
    for layer in cfg.ui.layers:
        metadata = layer.metadata or {}
        favs = metadata.get("favorites", [])
        for fav in favs:
            preset = fav.get("preset", {})
            if preset.get("model_layer_id") == model_layer_id:
                favorites.append(fav)
    return favorites[:max_count]


def list_all_favorites_for_model_layer(cfg: ExhibitConfig, model_layer_id: str) -> List[Dict[str, Any]]:
    """Liefert alle Favoriten für ein model_layer_id ohne Begrenzung der Anzahl."""
    return get_favorites_for_model_layer(cfg, model_layer_id, max_count=10_000)


def get_selected_kivy_favorites(cfg: ExhibitConfig, model_layer_id: str) -> List[Dict[str, Any]]:
    """Liefert die für den Kivy-View ausgewählten Favoriten für ein model_layer_id.

    Nutzt ui.kivy_favorites[model_layer_id] als Referenzliste (Namen) und
    filtert dagegen alle vorhandenen Favoriten dieses Modell-Layers.
    """
    selected_ids = cfg.ui.kivy_favorites.get(model_layer_id, [])
    if not selected_ids:
        return []

    all_favs = list_all_favorites_for_model_layer(cfg, model_layer_id)
    by_name = {f.get("name"): f for f in all_favs if "name" in f}

    ordered: List[Dict[str, Any]] = []
    for fav_name in selected_ids:
        fav = by_name.get(fav_name)
        if fav is not None:
            ordered.append(fav)

    return ordered[:MAX_FAVORITES_PER_MODEL_LAYER]


def set_selected_kivy_favorites(cfg: ExhibitConfig, model_layer_id: str, favorite_names: List[str]) -> None:
    """Setzt die ausgewählten Favoriten für einen Modell-Layer.

    - Entfernt Dubletten.
    - Beschneidet auf MAX_FAVORITES_PER_MODEL_LAYER.
    - Ignoriert Namen ohne existierenden Favoriten.
    """
    # Dubletten entfernen, Reihenfolge beibehalten
    seen = set()
    deduped: List[str] = []
    for name in favorite_names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)

    # Existierende Favoriten bestimmen
    all_favs = list_all_favorites_for_model_layer(cfg, model_layer_id)
    existing_names = {f.get("name") for f in all_favs if "name" in f}

    filtered = [n for n in deduped if n in existing_names]
    cfg.ui.kivy_favorites[model_layer_id] = filtered[:MAX_FAVORITES_PER_MODEL_LAYER]

