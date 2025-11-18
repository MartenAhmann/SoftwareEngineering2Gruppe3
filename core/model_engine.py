# core/model_engine.py

from __future__ import annotations

import numpy as np
from typing import Dict, List, Callable, Optional

import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision import models

from config.models import ModelConfig


class ModelEngine:
    """
    Zentrale Engine für:
    - Laden von ResNet18 (oder später anderen Modellen)
    - Registrieren von Hooks für ausgewählte Layer
    - Einmalige Inferenz mit Rückgabe der gewünschten Aktivierungen
    """

    def __init__(
        self,
        model_cfg: ModelConfig,
        active_layer_ids: Optional[List[str]] = None,
        device: str = "cpu",
    ):
        self.device = device

        # -------------------------
        # 1. Modell laden
        # -------------------------
        if model_cfg.name == "resnet18":
            self.model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        else:
            raise ValueError(f"Unbekanntes Modell: {model_cfg.name}")

        self.model.eval().to(self.device)

        # -------------------------
        # 2. Layer-Registry aufbauen
        #    (Name → Modul)
        # -------------------------
        self.layer_map: Dict[str, nn.Module] = {}
        for name, module in self.model.named_modules():
            self.layer_map[name] = module

        # Standardlayer falls nichts spezifiziert
        if active_layer_ids is None:
            active_layer_ids = ["conv1", "layer1", "layer2", "layer3", "layer4"]

        self.active_layer_ids = active_layer_ids

        # -------------------------
        # 3. Speicher für Aktivierungen
        # -------------------------
        self._activations: Dict[str, np.ndarray] = {}

        # -------------------------
        # 4. Hooks setzen
        # -------------------------
        self._hooks = []
        self._register_hooks()

        # -------------------------
        # 5. Preprocessing
        # -------------------------
        self.preprocess = T.Compose(
            [
                T.ToTensor(),
                T.Resize((224, 224)),
                T.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )

    # ------------------------------------------------------------------
    # Layer-Hooks
    # ------------------------------------------------------------------

    def _make_hook(self, layer_id: str) -> Callable:
        def hook(module, input, output):
            # output = Activation Tensor
            # Wir speichern eine NumPy-Kopie → Kivy/Streamlit können es direkt nutzen
            self._activations[layer_id] = output.detach().cpu().numpy()

        return hook

    def _register_hooks(self) -> None:
        """Setzt Hooks NUR auf die explizit gewünschten Layer."""
        for layer_id in self.active_layer_ids:
            if layer_id not in self.layer_map:
                raise ValueError(f"Layer {layer_id} existiert nicht im Modell.")
            module = self.layer_map[layer_id]
            self._hooks.append(module.register_forward_hook(self._make_hook(layer_id)))

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def get_available_layers(self) -> List[str]:
        """Gibt alle Layer zurück, die im Modell existieren."""
        return list(self.layer_map.keys())

    def get_active_layers(self) -> List[str]:
        """Gibt die Layer zurück, für die wir Hooks gesetzt haben."""
        return self.active_layer_ids

    def run_inference(self, np_image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Führt einen Forward-Pass durch.
        Erwartet: np_image (H, W, 3), uint8 oder float.
        Gibt zurück: dict(layer_id → activation_numpy_array)
        """
        self._activations.clear()

        # Sicherstellen, dass Bild im passenden Format vorliegt
        if np_image.dtype != np.uint8:
            np_image = np.clip(np_image, 0, 255).astype(np.uint8)

        # In PIL-Format wandeln für torchvision
        from PIL import Image

        pil_img = Image.fromarray(np_image)

        x = self.preprocess(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            _ = self.model(x)

        # Hier ist self._activations jetzt gefüllt
        return self._activations.copy()

    def get_activation(self, layer_id: str) -> np.ndarray:
        """Letzte Aktivierung eines bestimmten Layers holen."""
        return self._activations.get(layer_id)


# ----------------------------------------------------------------------
# Mini-Testfunktion (kann entfernt werden)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # Kleiner Selbsttest ohne UI
    cfg = ModelConfig(name="resnet18", weights="imagenet")
    engine = ModelEngine(cfg, active_layer_ids=["conv1", "layer1"])

    # Dummy-Bild (weiß)
    dummy = np.ones((300, 300, 3), dtype=np.uint8) * 255

    acts = engine.run_inference(dummy)
    print("Aktivierungen:", {k: v.shape for k, v in acts.items()})
