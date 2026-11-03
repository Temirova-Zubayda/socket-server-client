#!/usr/bin/env python3
# Runs ON Pinky. Follows the nurse's ArUco marker at 10 cm. If the marker is lost, YOLO looks for the
# nurse for 60 s, then sends TRACKING_FAIL to laptop B. A fallen person sends FALL_ALARM and Pinky
# drives around them. Laptop B must run alarm_server.py.
# Stop rtsp_server_pinky.py first: only one program can use the camera.
#   python3 pinky_follow.py              drive the motors (Pinky Pro bringup must be running)
#   python3 pinky_follow.py --no-drive   test: print drive commands, motors stay still
#   python3 pinky_follow.py --webcam     test on a laptop with its webcam (implies --no-drive)
import os, sys

# Raspberry Pi libcamera (0.3.2 in /usr/local), same fix as rtsp_server_pinky.py. Prepend, so ROS paths stay.
LIB = "/usr/local/lib/aarch64-linux-gnu"
if os.path.isdir(LIB) and not os.environ.get("LD_LIBRARY_PATH", "").startswith(LIB):
    os.environ["LD_LIBRARY_PATH"] = LIB + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["GST_PLUGIN_PATH"] = LIB + "/gstreamer-1.0"
    os.execv(sys.executable, [sys.executable] + sys.argv)   # restart with the new paths

import json, math, queue, socket, threading, time
import cv2
import numpy as np

# ---------------- settings ----------------
SERVER = ("192.168.129.11", 9000)   # laptop B running alarm_server.py
WIDTH, HEIGHT, FPS = 640, 480, 30

MARKER_DICT = cv2.aruco.DICT_4X4_50
MARKER_ID = 13          # the marker on the nurse picture (read from the photo you sent)
MARKER_SIZE_M = 0.03    # side of the black marker square in metres: MEASURE it and change this
FOCAL_PX = 635          # ov5647 at 640x480 (about 53 deg wide); fix with the 10 cm check in the guide

TARGET_DIST_M = 0.10    # follow the nurse 10 cm behind
STOP_DIST_M = 0.06      # closer than this: stop
MAX_LIN = 0.15          # m/s
MAX_ANG = 1.0           # rad/s
K_LIN, K_ANG = 1.0, 1.5

YOLO_TIMEOUT_S = 60     # marker lost: YOLO searches this long, then TRACKING_FAIL
SEARCH_TURN = 0.4       # rad/s, slow turn while YOLO sees nobody

FALL_CHECK_S = 0.5      # how often YOLO pose checks for a fallen person while the marker is seen
FALL_HOLD = 3           # FALLEN must be seen this many checks in a row (no alarm from one bad frame)
ANGLE_LIMIT = 60        # torso tilt from vertical (deg) that counts as lying
ALARM_COOLDOWN_S = 30   # do not send FALL_ALARM again for the same fall

# Detour around a fallen person: (seconds, linear m/s, angular rad/s), "away" = side without the person.
DETOUR = [(0.5, 0.0, 0.0),        # stop
          (1.0, 0.0, 0.8),        # turn away about 45 deg
          (3.0, 0.10, 0.0),       # drive 30 cm
          (1.0, 0.0, -0.8),       # turn back to the old direction
          (0.5, 0.0, 0.0)]        # stop, then look for the marker again


# ---------------- camera ----------------
def open_camera(webcam):
    if webcam:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise SystemExit("Webcam not found.")
        return lambda: (lambda ok_f: ok_f[1] if ok_f[0] else None)(cap.read()), cap.release

    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
    Gst.init(None)
    pipe = Gst.parse_launch(
        f"libcamerasrc ! video/x-raw,format=NV12,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
        "! videoconvert ! videoflip method=rotate-180 ! video/x-raw,format=BGR "   # camera is upside down
        "! appsink name=sink drop=true max-buffers=1 sync=false")
    sink = pipe.get_by_name("sink")
    pipe.set_state(Gst.State.PLAYING)

    def read():
        sample = sink.emit("try-pull-sample", Gst.SECOND)
        if sample is None:
            return None
        s = sample.get_caps().get_structure(0)
        w, h = s.get_value("width"), s.get_value("height")
        buf = sample.get_buffer()
        ok, info = buf.map(Gst.MapFlags.READ)
        frame = np.ndarray((h, w, 3), np.uint8, info.data).copy()
        buf.unmap(info)
        return frame

    return read, lambda: pipe.set_state(Gst.State.NULL)


# ---------------- motors (ROS 2 /cmd_vel) ----------------
class Driver:
    def __init__(self, enabled):
        self.pub = None
        self.last_print = 0
        if enabled:
            import rclpy
            from geometry_msgs.msg import Twist
            rclpy.init()
            self.node = rclpy.create_node("pinky_follow")
            self.pub = self.node.create_publisher(Twist, "/cmd_vel", 10)
            self.Twist = Twist

    def send(self, lin, ang):
        lin = max(-MAX_LIN, min(MAX_LIN, lin))
        ang = max(-MAX_ANG, min(MAX_ANG, ang))
        if self.pub:
            msg = self.Twist()
            msg.linear.x, msg.angular.z = float(lin), float(ang)
            self.pub.publish(msg)
        elif time.time() - self.last_print > 0.5:
            print(f"  drive lin={lin:+.2f} m/s  ang={ang:+.2f} rad/s")
            self.last_print = time.time()

    def stop(self):
        self.send(0.0, 0.0)


# ---------------- messages to laptop B ----------------
class Reporter:
    def __init__(self):
        self.q = queue.Queue()
        threading.Thread(target=self.loop, daemon=True).start()

    def send(self, event, **data):
        msg = {"event": event, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "robot": "pinky", **data}
        print(">> server:", msg)
        self.q.put(msg)

    def loop(self):
        sock = None
        while True:
            line = (json.dumps(self.q.get()) + "\n").encode()
            for _ in range(5):            # the robot keeps working even if the server is down
                try:
                    if sock is None:
                        sock = socket.create_connection(SERVER, timeout=2)
                    sock.sendall(line)
                    break
                except OSError as e:
                    print("Server not reachable:", e)
                    sock = None
                    time.sleep(1)


# ---------------- vision ----------------
def make_marker_finder():
    d = cv2.aruco.getPredefinedDictionary(MARKER_DICT)
    if hasattr(cv2.aruco, "ArucoDetector"):               # OpenCV 4.7+
        detect = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters()).detectMarkers
    else:                                                  # older OpenCV
        params = cv2.aruco.DetectorParameters_create()
        detect = lambda img: cv2.aruco.detectMarkers(img, d, parameters=params)

    def find(frame):
        """Returns (distance in m, x offset -1..1) of the nurse marker, or None."""
        corners, ids, _ = detect(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if ids is None:
            return None
        for c, i in zip(corners, ids.ravel()):
            if i == MARKER_ID:
                pts = c.reshape(4, 2)
                side = np.mean([np.linalg.norm(pts[k] - pts[(k + 1) % 4]) for k in range(4)])
                half = frame.shape[1] / 2
                return FOCAL_PX * MARKER_SIZE_M / side, (pts[:, 0].mean() - half) / half
        return None
    return find


def is_fallen(box, kp):
    # Same rule as fall_detect.py. keypoints: 5,6 = shoulders, 11,12 = hips
    x1, y1, x2, y2 = box
    pts = [kp[i] for i in (5, 6, 11, 12)]
    if all(p[2] > 0.5 for p in pts):
        sx, sy = (pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2
        hx, hy = (pts[2][0] + pts[3][0]) / 2, (pts[2][1] + pts[3][1]) / 2
        return math.degrees(math.atan2(abs(hx - sx), abs(hy - sy) + 1e-6)) > ANGLE_LIMIT
    return (x2 - x1) > (y2 - y1)                  # keypoints hidden: box wider than tall


def make_people_finder():
    from ultralytics import YOLO
    model = YOLO("yolo11n-pose.pt")              # downloads the first time (needs internet once)

    def people(frame):
        """Returns [(box, fallen)] for every person YOLO sees."""
        r = model(frame, imgsz=320, conf=0.5, verbose=False)[0]
        if r.keypoints is None or not len(r.boxes):
            return []
        return [(b, is_fallen(b, k)) for b, k in zip(r.boxes.xyxy.tolist(), r.keypoints.data.tolist())]
    return people


# ---------------- main loop ----------------
def main():
    webcam = "--webcam" in sys.argv
    read, close = open_camera(webcam)
    driver = Driver(enabled=not webcam and "--no-drive" not in sys.argv)
    reporter = Reporter()
    find_marker = make_marker_finder()
    find_people = make_people_finder()

    state = "MARKER"            # MARKER -> SEARCH (YOLO) -> FAILED, and DETOUR after a fall
    lost_since = None
    last_pose = 0.0
    fall_count = 0
    last_alarm = -ALARM_COOLDOWN_S
    detour, detour_step_end = [], 0.0
    print(f"Following marker {MARKER_ID} at {TARGET_DIST_M * 100:.0f} cm. Ctrl+C to stop.")

    try:
        while True:
            frame = read()
            now = time.time()
            if frame is None:
                print("No camera frame")
                driver.stop()
                continue

            # 1. Driving around a fallen person: finish the planned moves first.
            if state == "DETOUR":
                if now >= detour_step_end:
                    if not detour:
                        state, lost_since = "MARKER", None
                        print("Detour done, looking for the marker")
                        continue
                    secs, lin, ang = detour.pop(0)
                    detour_step_end = now + secs
                    current = (lin, ang)
                driver.send(*current)
                continue

            # 2. Fallen person check (every frame while searching, every FALL_CHECK_S otherwise).
            persons = []
            if state == "SEARCH" or now - last_pose >= FALL_CHECK_S:
                last_pose = now
                persons = find_people(frame)
                fallen = [b for b, f in persons if f]
                fall_count = fall_count + 1 if fallen else 0
                if fall_count >= FALL_HOLD:
                    fall_count = 0
                    box = fallen[0]
                    side = "left" if (box[0] + box[2]) / 2 < frame.shape[1] / 2 else "right"
                    if now - last_alarm > ALARM_COOLDOWN_S:
                        reporter.send("FALL_ALARM", message="Fallen person detected",
                                      side=side, bbox=[int(v) for v in box])
                        last_alarm = now
                    away = -1 if side == "left" else 1      # person on the left: turn right (negative)
                    detour = [(s, l, a * away) for s, l, a in DETOUR]
                    detour_step_end, state = 0.0, "DETOUR"
                    print(f"Fallen person on the {side}, driving around")
                    continue

            # 3. Follow the marker.
            m = find_marker(frame)
            if m is not None:
                if state != "MARKER":
                    print("Marker found again")
                state, lost_since = "MARKER", None
                dist, x = m
                lin = 0.0 if dist < STOP_DIST_M else max(0.0, K_LIN * (dist - TARGET_DIST_M))
                driver.send(lin, -K_ANG * x)               # marker on the right: turn right
                continue

            # 4. Marker lost: YOLO search for up to YOLO_TIMEOUT_S, then TRACKING_FAIL.
            if state == "FAILED":
                driver.stop()                              # wait until the marker shows up again
                continue
            if lost_since is None:
                lost_since, state = now, "SEARCH"
                print(f"Marker lost, YOLO searching for {YOLO_TIMEOUT_S} s")
                persons = find_people(frame)
            if now - lost_since > YOLO_TIMEOUT_S:
                reporter.send("TRACKING_FAIL",
                              message=f"Marker {MARKER_ID} not seen for {YOLO_TIMEOUT_S} s")
                state = "FAILED"
                driver.stop()
                continue
            upright = [b for b, f in persons if not f]
            if upright:
                x1, y1, x2, y2 = max(upright, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))  # nearest
                half = frame.shape[1] / 2
                x = ((x1 + x2) / 2 - half) / half
                lin = 0.08 if (y2 - y1) < 0.9 * frame.shape[0] else 0.0          # close enough: stop
                driver.send(lin, -K_ANG * x)
            else:
                driver.send(0.0, SEARCH_TURN)              # nobody seen: turn slowly and look
    except KeyboardInterrupt:
        pass
    finally:
        driver.stop()
        close()
        time.sleep(0.5)                                     # let a last message reach the server


if __name__ == "__main__":
    main()
