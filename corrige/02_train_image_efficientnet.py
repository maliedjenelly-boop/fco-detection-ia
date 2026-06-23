"""
VOLET IMAGE — Transfer learning EfficientNet-B0 propre (PyTorch + timm).

Corrige les défauts majeurs de l'ancien projet :
  - L'ancien `efficientnet_fco_model.pth` était un backbone pré-entraîné avec
    une TÊTE NON ENTRAÎNÉE (poids aléatoires) -> prédictions au hasard.
  - `train_advanced_fco_model.py` entraînait un gros CNN FROM SCRATCH (~30M
    paramètres) sur ~100 images -> surapprentissage garanti, et il plantait
    car il cherchait un dossier 'val/' inexistant à l'origine.
  - Ici : vrai transfer learning en 2 phases (tête puis fine-tuning),
    augmentation raisonnable, class weights, early stopping, évaluation honnête.

TÂCHE : binaire "healthy" vs "fco_signs" (= mild+moderate+severe).
  Raison : 4 (moderate) images d'entraînement ne permettent PAS un modèle de
  sévérité fiable. La question utile ("animal sain ou suspect FCO ?") est binaire.

⚠️  BIAIS DE DATASET CRITIQUE (à lire — aucun modèle ne corrige cela) :
  Les images "healthy" sont des photos de stock (moutons entiers, fond propre)
  et les images pathologiques sont des FIGURES recadrées de PDF cliniques
  (gros plans bouche/langue). Le réseau peut apprendre "photo de stock vs
  scan de PDF" au lieu de "sain vs malade". Métriques de test gonflées.
  => Voir le rapport, section "Bonnes pratiques / petit dataset médical".

Usage :
    pip install torch torchvision timm scikit-learn matplotlib seaborn
    python 02_train_image_efficientnet.py --data ../fco_dataset_final --epochs 25
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import timm
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 224
HEALTHY_NAMES = ("sain", "healthy")  # noms acceptés pour la classe saine ; le reste -> malade
OUT_DIR = Path("artifacts_image")


# --------------------------------------------------------------------------- #
# Dataset binaire : sain/healthy (0) vs malade/fco_signs (1)                  #
# --------------------------------------------------------------------------- #
def is_image(path: str) -> bool:
    """Filtre les fichiers non-image (ex : Thumbs.db sous Windows)."""
    return path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))


class BinaryFolder(datasets.ImageFolder):
    """ImageFolder -> binaire {0: sain, 1: malade}.

    Compatible avec :
      - le nouveau jeu 2 classes  (dossiers `sain` / `malade`),
      - l'ancien jeu 4 classes     (dossier `healthy` + mild/moderate/severe).
    """

    def __init__(self, root, transform):
        super().__init__(root, transform=transform, is_valid_file=is_image)
        healthy_name = next((n for n in HEALTHY_NAMES if n in self.class_to_idx), None)
        if healthy_name is None:
            raise ValueError(f"Aucune classe saine {HEALTHY_NAMES} trouvée dans {root}")
        healthy_idx = self.class_to_idx[healthy_name]
        # Remap : classe saine -> 0, toutes les autres -> 1
        self.samples = [(p, 0 if t == healthy_idx else 1) for p, t in self.samples]
        self.targets = [t for _, t in self.samples]
        # Libellés de sortie cohérents avec la convention du dossier
        self.classes = ["sain", "malade"] if healthy_name == "sain" else ["healthy", "fco_signs"]


def build_transforms():
    """Augmentation modérée (dataset minuscule : on évite les transfos extrêmes)."""
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    return train_tf, eval_tf


def make_loaders(data_dir: Path, batch_size: int):
    train_tf, eval_tf = build_transforms()
    train_ds = BinaryFolder(data_dir / "train", train_tf)
    val_ds = BinaryFolder(data_dir / "val", eval_tf)
    test_ds = BinaryFolder(data_dir / "test", eval_tf)

    counts = Counter(train_ds.targets)
    print(f"Train: {dict(counts)} | Val: {len(val_ds)} | Test: {len(test_ds)}")

    # Rééquilibrage par sur-échantillonnage de la classe minoritaire.
    class_w = {c: len(train_ds) / (2 * n) for c, n in counts.items()}
    sample_w = [class_w[t] for t in train_ds.targets]
    sampler = WeightedRandomSampler(sample_w, num_samples=len(train_ds), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, num_workers=0)
    # Poids pour la loss (en complément du sampler, pour stabilité).
    weight_tensor = torch.tensor([class_w[0], class_w[1]], dtype=torch.float)
    return train_loader, val_loader, test_loader, weight_tensor, train_ds.classes


# --------------------------------------------------------------------------- #
# Modèle : EfficientNet-B0 pré-entraîné, tête remplacée                       #
# --------------------------------------------------------------------------- #
def build_model(num_classes: int = 2) -> nn.Module:
    model = timm.create_model("efficientnet_b0", pretrained=True, num_classes=num_classes)
    return model


def set_backbone_trainable(model: nn.Module, trainable: bool):
    """Gèle/dégèle tout sauf la tête de classification."""
    for name, p in model.named_parameters():
        p.requires_grad = trainable or name.startswith("classifier")


# --------------------------------------------------------------------------- #
# Boucles d'entraînement / évaluation                                         #
# --------------------------------------------------------------------------- #
def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train() if train else model.eval()
    total_loss, correct, n = 0.0, 0, 0
    torch.set_grad_enabled(train)
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        if train:
            optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        if train:
            loss.backward()
            optimizer.step()
        total_loss += loss.item() * x.size(0)
        correct += (out.argmax(1) == y).sum().item()
        n += x.size(0)
    torch.set_grad_enabled(True)
    return total_loss / n, correct / n


def fit(model, train_loader, val_loader, criterion, device, epochs, lr, patience, tag):
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    best_acc, best_state, wait = 0.0, None, 0
    for ep in range(1, epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer, device, True)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()
        print(f"[{tag}] epoch {ep:02d} | train acc {tr_acc:.2f} loss {tr_loss:.3f} "
              f"| val acc {va_acc:.2f} loss {va_loss:.3f}")
        if va_acc > best_acc:
            best_acc, best_state, wait = va_acc, {k: v.cpu().clone() for k, v in model.state_dict().items()}, 0
        else:
            wait += 1
            if wait >= patience:
                print(f"[{tag}] early stopping (best val acc {best_acc:.2f})")
                break
    if best_state:
        model.load_state_dict(best_state)
    return best_acc


@torch.no_grad()
def evaluate(model, loader, classes, device):
    model.eval()
    preds, gts = [], []
    for x, y in loader:
        out = model(x.to(device))
        preds.extend(out.argmax(1).cpu().numpy())
        gts.extend(y.numpy())
    print("\nRapport de classification (TEST) :")
    print(classification_report(gts, preds, target_names=classes, zero_division=0))
    cm = confusion_matrix(gts, preds)
    OUT_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(4.5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=classes, yticklabels=classes)
    plt.ylabel("Vraie classe"); plt.xlabel("Prédiction"); plt.title("Confusion (test)")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "confusion_image.png", dpi=150)
    plt.close()


# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="../fco_dataset_binaire")  # jeu 2 classes sain/malade
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device : {device}")

    train_loader, val_loader, test_loader, weights, classes = make_loaders(
        Path(args.data), args.batch_size
    )
    model = build_model(num_classes=2).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights.to(device))

    # --- Phase 1 : on n'entraîne QUE la tête (backbone gelé) -------------- #
    print("\n=== Phase 1 : entraînement de la tête (backbone gelé) ===")
    set_backbone_trainable(model, False)
    fit(model, train_loader, val_loader, criterion, device,
        epochs=max(8, args.epochs // 3), lr=1e-3, patience=5, tag="head")

    # --- Phase 2 : fine-tuning de tout le réseau à faible LR -------------- #
    print("\n=== Phase 2 : fine-tuning complet (LR faible) ===")
    set_backbone_trainable(model, True)
    fit(model, train_loader, val_loader, criterion, device,
        epochs=args.epochs, lr=1e-4, patience=7, tag="finetune")

    # --- Évaluation finale sur le test ------------------------------------ #
    evaluate(model, test_loader, classes, device)

    OUT_DIR.mkdir(exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "arch": "efficientnet_b0",
            "classes": classes,
            "img_size": IMG_SIZE,
            "mean": IMAGENET_MEAN,
            "std": IMAGENET_STD,
            "task": "binary_healthy_vs_fco",
        },
        OUT_DIR / "fco_image_model.pth",
    )
    print(f"\n✅ Modèle sauvegardé : {OUT_DIR / 'fco_image_model.pth'}")
    print("⚠️  Rappel : vérifier le biais de source (stock vs PDF) avant toute conclusion.")


if __name__ == "__main__":
    main()
