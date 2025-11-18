# config/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Union

BlendMode = Literal["sum", "mean", "max", "weighted"]


@dataclass
class VizPreset:
    id: str
    layer_id: str
    channels: Union[List[int], str] = "topk"  # z.B. [0, 3, 7] oder "topk"
    k: int | None = None                     # nur relevant, wenn channels == "topk"
    blend_mode: BlendMode = "mean"
    overlay: bool = False
    alpha: float = 0.6
    cmap: str = "viridis"


@dataclass
class LayerUIConfig:
    id: str                   # interne Layer-ID, z.B. "layer1_conv1"
    order: int                # Reihenfolge in der Button-Leiste
    button_label: str         # Text auf dem Button unten
    title_bar_label: str      # Text in der Titelleiste für diesen Layer
    description: str          # Erklärungstext (rechte Spalte)
    viz_preset_id: str        # Referenz auf VizPreset.id


@dataclass
class ModelConfig:
    name: str = "resnet18"
    weights: str = "imagenet"


@dataclass
class ExhibitUIConfig:
    title: str                               # globaler Ausstellungstitel
    language: str = "de"
    layers: List[LayerUIConfig] = field(default_factory=list)


@dataclass
class ExhibitConfig:
    exhibit_id: str
    model: ModelConfig
    ui: ExhibitUIConfig
    viz_presets: List[VizPreset] = field(default_factory=list)
