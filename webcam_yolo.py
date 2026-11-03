#!/usr/bin/env python3
# Laptop webcam + pretrained YOLO (COCO). Shows only "person". Press q to quit.
import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")   # downloads automatically the first time
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("Camera not found. Try VideoCapture(1).")

while True:
    ok, frame = cap.read()
    if not ok:
        break
    results = model(frame, classes=[0], conf=0.5, verbose=False)   # class 0 = person
    out = results[0].plot()
    cv2.putText(out, f"persons: {len(results[0].boxes)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("YOLO webcam (q = quit)", out)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
