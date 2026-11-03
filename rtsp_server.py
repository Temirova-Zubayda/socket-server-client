#!/usr/bin/env python3
"""RTSP server for laptop A ("Pinky"). Same job as the tutorial's test-launch.
Run:  python3 rtsp_server.py
Watch from laptop B:  rtsp://<laptop-A-ip>:8554/test
"""
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GstRtspServer, GLib

DEVICE = "/dev/video0"
WIDTH, HEIGHT, FPS = 1280, 720, 30   # LG Camera supports MJPG 1280x720 @ 30 fps

PIPELINE = (
    f"( v4l2src device={DEVICE} "
    f"! image/jpeg,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
    "! jpegdec ! videoconvert "
    "! queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 min-threshold-time=0 "
    "! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 key-int-max=30 "
    "! video/x-h264,profile=baseline "
    "! h264parse ! rtph264pay name=pay0 pt=96 config-interval=1 )"
)

Gst.init(None)
server = GstRtspServer.RTSPServer()
server.set_service("8554")
factory = GstRtspServer.RTSPMediaFactory()
factory.set_launch(PIPELINE)
factory.set_shared(True)   # several viewers share one camera
server.get_mount_points().add_factory("/test", factory)
server.attach(None)
print("Streaming at rtsp://<this-laptop-ip>:8554/test  (Ctrl+C to stop)")
GLib.MainLoop().run()
