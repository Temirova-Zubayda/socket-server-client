#!/usr/bin/env python3
# Trains the hat classifier (helmet / cap / no_hat) from head crops saved by hat_detect.py.
# Input:  ~/networking/dataset/hats/<class>/*.jpg
# Output: hat_cls.pt in this folder (hat_detect.py loads it automatically).
import os, random, shutil
from ultralytics import YOLO

SRC = os.path.expanduser("~/networking/dataset/hats")
SPLIT = os.path.expanduser("~/networking/dataset/hats_split")
VAL_PART = 0.2
EPOCHS = 30
IMG = 128   # head crops are small

classes = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
if len(classes) < 2:
    raise SystemExit(f"Need at least 2 class folders in {SRC}, found: {classes}")

shutil.rmtree(SPLIT, ignore_errors=True)
random.seed(0)
for c in classes:
    files = sorted(f for f in os.listdir(os.path.join(SRC, c)) if f.endswith(".jpg"))
    random.shuffle(files)
    n_val = max(1, int(len(files) * VAL_PART))
    for part, names in (("val", files[:n_val]), ("train", files[n_val:])):
        os.makedirs(os.path.join(SPLIT, part, c), exist_ok=True)
        for f in names:
            shutil.copy(os.path.join(SRC, c, f), os.path.join(SPLIT, part, c, f))
    print(f"{c}: {len(files) - n_val} train, {n_val} val")

model = YOLO("yolo11n-cls.pt")   # downloads automatically the first time
results = model.train(data=SPLIT, epochs=EPOCHS, imgsz=IMG, project="runs", name="hat_cls", exist_ok=True)
best = os.path.join(results.save_dir, "weights", "best.pt")
shutil.copy(best, "hat_cls.pt")
print("Saved hat_cls.pt")
