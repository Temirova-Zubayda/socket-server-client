#!/usr/bin/env python3
# Construction helmet detection + hat classification. YOLO pose finds each person's head,
# a small classifier (hat_cls.pt, made by train_hat.py) says helmet / cap / no_hat.
#   python3 hat_detect.py                  laptop webcam
#   python3 hat_detect.py 192.168.129.12   Pinky RTSP stream (rtsp_server.py must be running)
# Keys: 1 = save heads as helmet, 2 = cap, 3 = no_hat (dataset for train_hat.py), q = quit.
import os, sys, time
import cv2
from ultralytics import YOLO

CLASSES = ["helmet", "cap", "no_hat"]
COLORS = {"helmet": (0, 200, 0), "cap": (0, 165, 255), "no_hat": (0, 0, 255)}
SAVE_DIR = os.path.expanduser("~/networking/dataset/hats")
CLS_MODEL = "hat_cls.pt"
CLS_CONF = 0.6          # below this the label shows "?"
HOLD_FRAMES = 10        # no_hat must last this many frames before the alarm shows

if len(sys.argv) > 1:
    url = f"rtsp://{sys.argv[1]}:8554/test"
    gst = (f"rtspsrc location={url} latency=0 ! rtph264depay ! h264parse ! avdec_h264 "
           "! videoconvert ! video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false")
    cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        cap = cv2.VideoCapture(url)
else:
    cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("Camera not found. Webcam: try VideoCapture(1). RTSP: is the server running?")

pose = YOLO("yolo11n-pose.pt")   # downloads automatically the first time
cls = YOLO(CLS_MODEL) if os.path.exists(CLS_MODEL) else None
if cls is None:
    print(f"{CLS_MODEL} not found: only head boxes are shown. Collect data with keys 1/2/3, then run train_hat.py")


def head_box(kp, w, h):
    # keypoints 0-4 = nose, eyes, ears; 5,6 = shoulders. Box goes up from the eyes to include the hat.
    face = [p for p in kp[:5] if p[2] > 0.5]
    if len(face) < 2:
        return None
    xs, ys = [p[0] for p in face], [p[1] for p in face]
    size = max(xs) - min(xs)
    sh = [p for p in kp[5:7] if p[2] > 0.5]
    if len(sh) == 2:
        size = max(size, abs(sh[0][0] - sh[1][0]) * 0.5)
    size = max(size, 20)
    cx, eye_y = sum(xs) / len(xs), min(ys)
    x1, x2 = cx - size * 1.0, cx + size * 1.0
    y1, y2 = eye_y - size * 1.4, max(ys) + size * 0.5
    x1, y1, x2, y2 = int(max(x1, 0)), int(max(y1, 0)), int(min(x2, w)), int(min(y2, h))
    return (x1, y1, x2, y2) if x2 - x1 > 10 and y2 - y1 > 10 else None


saved = 0
no_hat_frames = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    h, w = frame.shape[:2]
    out = frame.copy()
    r = pose(frame, conf=0.5, verbose=False)[0]
    crops = []
    any_no_hat = False
    if r.keypoints is not None:
        for kp in r.keypoints.data.tolist():
            box = head_box(kp, w, h)
            if box is None:
                continue
            x1, y1, x2, y2 = box
            crop = frame[y1:y2, x1:x2]
            crops.append(crop)
            label, color = "head", (255, 255, 0)
            if cls is not None:
                c = cls(crop, verbose=False)[0].probs
                name, conf = cls.names[c.top1], float(c.top1conf)
                if conf >= CLS_CONF:
                    label, color = f"{name} {conf:.2f}", COLORS.get(name, color)
                    any_no_hat |= name == "no_hat"
                else:
                    label = f"? {conf:.2f}"
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.putText(out, label, (x1, max(y1 - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    no_hat_frames = no_hat_frames + 1 if any_no_hat else 0
    if no_hat_frames >= HOLD_FRAMES:
        cv2.putText(out, "ALARM: NO HELMET!", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.putText(out, f"saved: {saved}  (1 helmet, 2 cap, 3 no_hat, q quit)", (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("Helmet / hat detection", out)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    if key in (ord("1"), ord("2"), ord("3")) and crops:
        folder = os.path.join(SAVE_DIR, CLASSES[key - ord("1")])
        os.makedirs(folder, exist_ok=True)
        for i, crop in enumerate(crops):
            name = time.strftime("%Y%m%d_%H%M%S_") + f"{int(time.time() * 1000) % 1000:03d}_{i}.jpg"
            cv2.imwrite(os.path.join(folder, name), crop)
            saved += 1

cap.release()
cv2.destroyAllWindows()
