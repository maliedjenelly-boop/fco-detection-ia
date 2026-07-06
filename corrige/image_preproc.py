# -*- coding: utf-8 -*-
"""
Prétraitement d'image — égalisation d'histogramme adaptative (CLAHE).

Standardise le contraste et la luminance entre des images de sources
hétérogènes (photos stock vs figures cliniques), AVANT le redimensionnement
et la normalisation. Appliqué de façon identique à l'entraînement et à
l'inférence, pour éviter tout décalage.

CLAHE (Contrast Limited Adaptive Histogram Equalization) applique l'égalisation
d'histogramme localement (par tuiles), avec limitation du contraste pour éviter
d'amplifier le bruit — la version « professionnelle » de l'égalisation vue en cours.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False


def apply_clahe(img: Image.Image, clip_limit: float = 2.0, tile: int = 8) -> Image.Image:
    """Applique CLAHE sur la luminance et renvoie une image RGB (PIL)."""
    arr = np.asarray(img.convert("RGB"))
    if _HAS_CV2:
        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    else:
        # Repli sans OpenCV : égalisation d'histogramme globale sur la luminance.
        ycc = np.asarray(Image.fromarray(arr).convert("YCbCr")).copy()
        y = ycc[:, :, 0]
        hist, _ = np.histogram(y.flatten(), 256, [0, 256])
        cdf = hist.cumsum()
        cdf_m = np.ma.masked_equal(cdf, 0)
        cdf_m = (cdf_m - cdf_m.min()) * 255 / (cdf_m.max() - cdf_m.min())
        lut = np.ma.filled(cdf_m, 0).astype("uint8")
        ycc[:, :, 0] = lut[y]
        rgb = np.asarray(Image.fromarray(ycc, "YCbCr").convert("RGB"))
    return Image.fromarray(rgb)


class CLAHE:
    """Transform PIL -> PIL utilisable dans torchvision.transforms.Compose."""

    def __init__(self, clip_limit: float = 2.0, tile: int = 8):
        self.clip_limit = clip_limit
        self.tile = tile

    def __call__(self, img: Image.Image) -> Image.Image:
        return apply_clahe(img, self.clip_limit, self.tile)

    def __repr__(self):
        return f"CLAHE(clip_limit={self.clip_limit}, tile={self.tile})"
