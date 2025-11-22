# config/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Union, Optional, Dict

BlendMode = Literal["sum", "mean", "max", "weighted"]


@dataclass
class ModelLayerMapping:
    """
    Mapping zwischen UI-Layer-ID und dem tatsächlichen Modell-Layer-Namen.
    Ermöglicht saubere Trennung zwischen UI-Struktur und Modellarchitektur.
    """
    ui_layer_id: str        # z.B. "layer1_conv1"
    model_layer_id: str     # z.B. "conv1" oder "layer1.0.conv1"
    display_name: str       # z.B. "Erste Faltungsschicht"


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
    subtitle: Optional[str] = None  # Kurzunterzeile für Kamera-/Layer-Ansicht (optional)
    metadata: dict | None = None    # Generische Metadaten (z.B. favorites), Schema bleibt bewusst generisch


@dataclass
class ModelConfig:
    name: str = "resnet18"
    weights: str = "imagenet"
    layer_mappings: List[ModelLayerMapping] = field(default_factory=list)


@dataclass
class ModelLayerContent:
    """Content-Felder pro model_layer_id.

    Wird in ExhibitUIConfig als Mapping ui.model_layers[model_layer_id] geführt.
    """

    title: str
    subtitle: Optional[str] = None
    description: str = ""


@dataclass
class ExhibitUIConfig:
    title: str                               # globaler Ausstellungstitel
    language: str = "de"
    layers: List[LayerUIConfig] = field(default_factory=list)
    # Neues Mapping: Content pro Modell-Layer-ID
    model_layers: Dict[str, ModelLayerContent] = field(default_factory=dict)


@dataclass
class ExhibitConfig:
    exhibit_id: str
    model: ModelConfig
    ui: ExhibitUIConfig
    viz_presets: List[VizPreset] = field(default_factory=list)
    version: str = "1.0"
