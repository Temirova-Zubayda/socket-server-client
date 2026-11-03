#!/usr/bin/env python3
# Webcam + YOLO pose: marks a person FALLEN when the body is horizontal. Press q to quit.
import math
import cv2
from ultralytics import YOLO

model = YOLO("yolo11n-pose.pt")   # downloads automatically the first time
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("Camera not found. Try VideoCapture(1).")

ANGLE_LIMIT = 60     # torso tilt from vertical (degrees) that counts as lying
HOLD_FRAMES = 10     # FALLEN must last this many frames before the alarm shows
fallen_frames = 0

def is_fallen(box, kp):
    x1, y1, x2, y2 = box
    wide = (x2 - x1) > (y2 - y1)                      # box wider than tall
    # keypoints: 5,6 = shoulders, 11,12 = hips
    pts = [kp[i] for i in (5, 6, 11, 12)]
    if all(p[2] > 0.5 for p in pts):
        sx, sy = (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2
        hx, hy = (pts[2][0] + pts[3][0]) / 2, (pts[2][1] + pts[3][1]) / 2
        angle = math.degrees(math.atan2(abs(hx - sx), abs(hy - sy) + 1e-6))
        return angle > ANGLE_LIMIT, angle
    return wide, None                                  # keypoints hidden: use box shape only

while True:
    ok, frame = cap.read()
    if not ok:
        break
    r = model(frame, conf=0.5, verbose=False)[0]
    out = r.plot(boxes=False)                          # draws skeletons
    any_fallen = False
    if r.keypoints is not None and len(r.boxes):
        for box, kp in zip(r.boxes.xyxy.tolist(), r.keypoints.data.tolist()):
            fallen, angle = is_fallen(box, kp)
            any_fallen |= fallen
            color = (0, 0, 255) if fallen else (0, 255, 0)
            text = "FALLEN" if fallen else "OK"
            if angle is not None:
                text += f" {angle:.0f}deg"
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)
            cv2.putText(out, text, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    fallen_frames = fallen_frames + 1 if any_fallen else 0
    if fallen_frames >= HOLD_FRAMES:
        cv2.putText(out, "ALARM: PERSON FELL!", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.imshow("Fall detection (q = quit)", out)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
