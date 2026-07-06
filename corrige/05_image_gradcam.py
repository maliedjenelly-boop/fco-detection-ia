"""
VOLET ÉLEVEUR — Grad-CAM : où le modèle image regarde-t-il vraiment ?

Objectif : DIAGNOSTIQUER le biais de dataset. Si le réseau classe « malade »
en regardant le FOND / le texte du PDF plutôt que les LÉSIONS, Grad-CAM le
montre visuellement. C'est la figure clé pour justifier, dans le mémoire, que
les performances image doivent être interprétées avec prudence.

Grad-CAM (Selvaraju et al., 2017) : pondère les cartes d'activation de la
dernière couche convolutive par le gradient du score de la classe prédite,
puis superpose la heatmap sur l'image.

Produit : artifacts_image/gradcam/<nom>_cam.png (image | heatmap | superposition)

Usage :
    pip install torch torchvision timm matplotlib pillow
    python 05_image_gradcam.py                 # échantillonne le jeu de test
    python 05_image_gradcam.py --image chemin/vers/photo.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL_PATH = Path("artifacts_image/fco_image_model.pth")
OUT = Path("artifacts_image/gradcam")


# --------------------------------------------------------------------------- #
class GradCAM:
    """Grad-CAM générique : hooks sur une couche cible (dernière conv)."""

    def __init__(self, model, target_layer):
        import torch  # noqa: F401
        self.model = model
        self.activations = None
        self.gradients = None
        target_layer.register_forward_hook(self._save_activation)

    def _save_activation(self, module, inp, out):
        self.activations = out.detach()
        out.register_hook(self._save_gradient)  # gradient de CETTE activation

    def _save_gradient(self, grad):
        self.gradients = grad.detach()

    def __call__(self, x, class_idx=None):
        import torch
        self.model.zero_grad()
        logits = self.model(x)
        probs = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()
        if class_idx is None:
            class_idx = int(logits.argmax(1).item())
        logits[0, class_idx].backward()

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)      # [1,C,1,1]
        cam = torch.relu((weights * self.activations).sum(1))[0]      # [h,w]
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam.cpu().numpy(), class_idx, probs


def pick_target_layer(model):
    """Dernière couche conv d'EfficientNet (timm) : conv_head, sinon repli."""
    if hasattr(model, "conv_head"):
        return model.conv_head
    last = None
    import torch.nn as nn
    for m in model.modules():
        if isinstance(m, nn.Conv2d):
            last = m
    return last


# --------------------------------------------------------------------------- #
def load():
    try:
        import timm
        import torch
    except ImportError:
        sys.exit("PyTorch/timm requis : pip install torch torchvision timm")
    if not MODEL_PATH.exists():
        sys.exit(f"Modèle absent : {MODEL_PATH}. Lancez d'abord 02_train_image_efficientnet.py")
    ckpt = torch.load(MODEL_PATH, map_location="cpu")
    model = timm.create_model(ckpt["arch"], pretrained=False, num_classes=len(ckpt["classes"]))
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, ckpt


def preprocess(pil_img, ckpt):
    from torchvision import transforms
    pil_img = pil_img.convert("RGB")
    if ckpt.get("clahe"):                       # cohérence avec l'entraînement
        from image_preproc import apply_clahe
        pil_img = apply_clahe(pil_img)
    tf = transforms.Compose([
        transforms.Resize((ckpt["img_size"], ckpt["img_size"])),
        transforms.ToTensor(),
        transforms.Normalize(ckpt["mean"], ckpt["std"]),
    ])
    return tf(pil_img).unsqueeze(0)


def render(pil_img, cam, ckpt, label, conf, out_path):
    size = ckpt["img_size"]
    base = np.asarray(pil_img.convert("RGB").resize((size, size))) / 255.0
    heat = cm.jet(np.asarray(Image.fromarray((cam * 255).astype(np.uint8)).resize((size, size))) / 255.0)[..., :3]
    overlay = 0.55 * base + 0.45 * heat

    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, im, title in zip(
        axes, [base, heat, overlay],
        ["Image", "Grad-CAM", f"Superposition\n→ {label} ({conf:.0%})"]
    ):
        ax.imshow(np.clip(im, 0, 1)); ax.set_title(title); ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None, help="image unique ; sinon échantillonne le test")
    ap.add_argument("--data", default="../fco_dataset_final")
    ap.add_argument("--n", type=int, default=6, help="nb d'images échantillonnées par défaut")
    args = ap.parse_args()

    model, ckpt = load()
    cam_engine = GradCAM(model, pick_target_layer(model))
    classes = ckpt["classes"]
    OUT.mkdir(parents=True, exist_ok=True)

    # Sélection des images
    if args.image:
        images = [Path(args.image)]
    else:
        test_dir = Path(args.data) / "test"
        images = []
        for sub in test_dir.glob("*/*"):
            if sub.suffix.lower() in (".jpg", ".jpeg", ".png"):
                images.append(sub)
        images = images[:: max(1, len(images) // args.n)][: args.n]
    if not images:
        sys.exit("Aucune image trouvée.")

    print(f"Grad-CAM sur {len(images)} image(s) — couche cible : "
          f"{pick_target_layer(model).__class__.__name__}")
    for p in images:
        img = Image.open(p)
        x = preprocess(img, ckpt)
        cam, idx, probs = cam_engine(x)
        label = classes[idx]
        out_path = OUT / f"{p.stem}_cam.png"
        render(img, cam, ckpt, label, probs[idx], out_path)
        print(f"  {p.name:<40} → {label:<10} ({probs[idx]:.0%})  | {out_path}")

    print(f"\n✅ Heatmaps dans : {OUT}/")
    print("👁️  Interprétation : si la chaleur est sur le FOND/le texte et non sur "
          "les lésions (bouche, museau, yeux), le modèle exploite un biais de source.")


if __name__ == "__main__":
    main()
