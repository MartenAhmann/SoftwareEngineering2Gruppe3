# config/service.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    ExhibitConfig,
    ExhibitUIConfig,
    ModelConfig,
    LayerUIConfig,
    VizPreset,
)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "exhibit_config.json"


def _default_config_dict() -> Dict[str, Any]:
    """Rohes Default-Config als Dict (JSON-kompatibel)."""
    return {
        "exhibit_id": "cnn_museum_01",
        "model": {
            "name": "resnet18",
            "weights": "imagenet",
        },
        "ui": {
            "title": "Wie ein neuronales Netz sieht",
            "language": "de",
            "layers": [
                {
                    "id": "layer1_conv1",
                    "order": 1,
                    "button_label": "Frühe Kanten",
                    "title_bar_label": "Layer 1 – Kanten",
                    "description": "In dieser Schicht erkennt das Netz einfache Kanten und Helligkeitsübergänge.",
                    "viz_preset_id": "preset_layer1",
                }
            ],
        },
        "viz_presets": [
            {
                "id": "preset_layer1",
                "layer_id": "layer1_conv1",
                "channels": [0],
                "blend_mode": "mean",
                "overlay": False,
                "alpha": 0.6,
                "cmap": "viridis",
            }
        ],
    }


def load_config() -> ExhibitConfig:
    """Läd exhibit_config.json, legt Default an, falls nicht vorhanden."""
    if not CONFIG_PATH.exists():
        save_config_dict(_default_config_dict())
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return _from_dict(raw)


def save_config(cfg: ExhibitConfig) -> None:
    """Speichert ein ExhibitConfig-Objekt nach exhibit_config.json."""
    data = _to_dict(cfg)
    save_config_dict(data)


def save_config_dict(data: Dict[str, Any]) -> None:
    """Hilfsfunktion: schreibt ein rohes Dict nach exhibit_config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_raw_config_dict() -> Dict[str, Any]:
    """
    Lädt das rohe JSON als Dict ohne Konvertierung in Dataclasses.
    Legt Default an, falls Datei fehlt.
    """
    if not CONFIG_PATH.exists():
        save_config_dict(_default_config_dict())
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_raw_config_dict(data: Dict[str, Any]) -> None:
    """
    Speichert das rohe Dict exakt zurück (ohne Dataclass-Konvertierung).
    """
    save_config_dict(data)


def _from_dict(d: Dict[str, Any]) -> ExhibitConfig:
    """Konvertiert rohes Dict (JSON) → ExhibitConfig (Dataclasses)."""
    model_cfg = ModelConfig(**d["model"])

    ui_raw: Dict[str, Any] = d["ui"]
    layers_raw: List[Dict[str, Any]] = ui_raw.get("layers", [])

    # Nur die Felder an LayerUIConfig übergeben, die es wirklich kennt
    layers: List[LayerUIConfig] = []
    for ld in layers_raw:
        layer_kwargs = {
            "id": ld["id"],
            "order": ld["order"],
            "button_label": ld["button_label"],
            "title_bar_label": ld["title_bar_label"],
            "description": ld["description"],
            "viz_preset_id": ld["viz_preset_id"],
        }
        layers.append(LayerUIConfig(**layer_kwargs))

    ui_cfg = ExhibitUIConfig(
        title=ui_raw["title"],
        language=ui_raw.get("language", "de"),
        layers=layers,
    )

    presets_raw: List[Dict[str, Any]] = d.get("viz_presets", [])
    presets = [VizPreset(**p) for p in presets_raw]

    return ExhibitConfig(
        exhibit_id=d["exhibit_id"],
        model=model_cfg,
        ui=ui_cfg,
        viz_presets=presets,
    )


def _to_dict(cfg: ExhibitConfig) -> Dict[str, Any]:
    """Konvertiert ExhibitConfig (Dataclasses) → rohes Dict (JSON)."""
    return {
        "exhibit_id": cfg.exhibit_id,
        "model": {
            "name": cfg.model.name,
            "weights": cfg.model.weights,
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
                }
                for l in cfg.ui.layers
            ],
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
