# Pinky'dan B noutbukka video uzatish (RTSP)

Sana: 2026-10-15. Bu fayl haqiqiy Pinky bilan qilgan barcha ishlarimizni jamlaydi. Laptoplardagi mashq qismi `rtsp-tutorial-notes.md` faylida.

## 1. Qurilmalar

| | Pinky (video yuboradi) | B noutbuk (videoni ko'radi) |
|---|---|---|
| Kirish | `pinky@raspi` | `zubayda@zubayda-950XCJ...` |
| Qurilma | Raspberry Pi 5 Model B Rev 1.1 | Samsung noutbuk |
| Tizim | Ubuntu 24.04.4 LTS, ROS 2 Jazzy (Pinky Pro v1.10 image) | Ubuntu 24.04 |
| GStreamer | 1.24.2 | 1.24.2 |
| IP manzil | **192.168.129.12** (Wi-Fi `wlan0`), 192.168.4.1 (Pinky'ning o'z Wi-Fi nuqtasi `ap0`) | 192.168.129.11 (USB Wi-Fi adapter) |
| Kamera | **ov5647**, lentali kabel (CSI) | — |
| Papka | `~/networking` | `~/networking` |

Video manzili: `rtsp://192.168.129.12:8554/test`

## 2. Pinky'ga kirish (B noutbukdan)

```
ssh pinky@192.168.129.12
```
Qator boshida `pinky@raspi:~$` paydo bo'lsa, Pinky ichidasiz.

## 3. Nimalarni tekshirdik

1. **Ekransiz GStreamer testi** (Pinky'da ekran yo'q, shuning uchun `autovideosink` xato beradi: `munmap_chunk(): invalid pointer`). Buning o'rniga `fakesink` ishlatamiz:
   ```
   gst-launch-1.0 videotestsrc num-buffers=60 ! fakesink
   ```
   Natija: `Got EOS` ✅
2. **Plata va kamera:**
   ```
   cat /proc/device-tree/model; echo
   v4l2-ctl --list-devices
   sudo dmesg | grep -i -E "imx|ov5|ov64|rp1-cfe" | tail -15
   grep -i -E "camera|dtoverlay" /boot/firmware/config.txt
   ```
   Natija: Raspberry Pi 5, kamera **ov5647** `/dev/video0` da, `config.txt` da `dtoverlay=ov5647`.
3. **Kamera rejimlari:**
   ```
   rpicam-hello --list-cameras
   ```
   ov5647: 640x480 (58.9 fps gacha), 1296x972 (43 fps), 1920x1080 (30 fps), 2592x1944 (15 fps).

## 4. Asosiy muammo va yechimi: libcamera versiyasi

**Muammo:** `libcamerasrc` "Could not find any supported camera" va "No IPA found" deb xato berdi.

**Sabab:** GStreamer Ubuntu'ning standart **libcamera 0.2.0** versiyasini ishlatgan. U Raspberry Pi 5 kamerasini tanimaydi. Pinky'da esa Raspberry Pi'ning to'g'ri versiyasi (**0.3.2**) allaqachon `/usr/local` ichida o'rnatilgan ekan.

**Yechim:** GStreamer'ni `/usr/local` dagi versiyaga yo'naltirish (hech narsa o'rnatish shart emas):
```
export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu
export GST_PLUGIN_PATH=/usr/local/lib/aarch64-linux-gnu/gstreamer-1.0
gst-inspect-1.0 libcamerasrc | grep -E "Filename|Version"
```
`Filename` qatorida `/usr/local/...` va `Version 0.3.2...` chiqishi kerak.

> Server fayli (`rtsp_server_pinky.py`) bu ikki sozlamani o'zi qo'yadi, shuning uchun serverni ishga tushirishda `export` yozish shart emas.

## 5. Ikkinchi muammo: rasm formati

**Muammo:** "Can't configure camera with invalid configuration".
**Yechim:** formatni aniq yozish kerak: **`format=NV12`**.
```
gst-launch-1.0 libcamerasrc ! video/x-raw,format=NV12,width=640,height=480,framerate=30/1 ! videoconvert ! identity eos-after=30 ! fakesink
```
Natija: `Got EOS` ✅

Eslatma: `libcamerasrc` da `num-buffers` sozlamasi yo'q. Test uchun `identity eos-after=30` ishlatamiz.

## 6. Uchinchi muammo: rasm teskari

Kamera Pinky'ga teskari o'rnatilgan. Serverda rasmni 180° buramiz: `videoflip method=rotate-180`.

## 7. Yakuniy server fayli (Pinky'da)

Fayl: `~/networking/rtsp_server_pinky.py`
```python
import os, sys
LIB = "/usr/local/lib/aarch64-linux-gnu"
if LIB not in os.environ.get("LD_LIBRARY_PATH", ""):
    os.environ["LD_LIBRARY_PATH"] = LIB
    os.environ["GST_PLUGIN_PATH"] = LIB + "/gstreamer-1.0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GstRtspServer, GLib
WIDTH, HEIGHT, FPS = 640, 480, 30
PIPELINE = (
    f"( libcamerasrc ! video/x-raw,format=NV12,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
    "! videoconvert ! videoflip method=rotate-180 ! queue max-size-buffers=1 leaky=downstream "
    "! x264enc tune=zerolatency speed-preset=ultrafast bitrate=1500 key-int-max=30 "
    "! video/x-h264,profile=baseline ! h264parse ! rtph264pay name=pay0 pt=96 config-interval=1 )")
Gst.init(None)
server = GstRtspServer.RTSPServer(); server.set_service("8554")
factory = GstRtspServer.RTSPMediaFactory(); factory.set_launch(PIPELINE); factory.set_shared(True)
server.get_mount_points().add_factory("/test", factory); server.attach(None)
print("Pinky streaming at rtsp://192.168.129.12:8554/test  (Ctrl+C to stop)")
try:
    GLib.MainLoop().run()
except KeyboardInterrupt:
    pass
```

Pipeline qismlari:
- `libcamerasrc ... format=NV12, 640x480, 30fps`: kameradan rasm oladi.
- `videoflip method=rotate-180`: teskari rasmni to'g'rilaydi.
- `queue max-size-buffers=1 leaky=downstream`: eski kadrlarni ushlab turmaydi (kechikish kamroq).
- `x264enc tune=zerolatency speed-preset=ultrafast`: videoni tez siqadi. Pi 5 da H.264 uchun maxsus chip yo'q, siqishni protsessor qiladi, shuning uchun o'lcham 640x480.
- `rtph264pay`: videoni tarmoq paketlariga bo'ladi.

## 8. Ishga tushirish tartibi

**1-terminal (B noutbuk → Pinky):**
```
ssh pinky@192.168.129.12
cd ~/networking && python3 rtsp_server_pinky.py
```
`Pinky streaming at ...` chiqadi. Bu terminalni **yopmang**.

**2-terminal (B noutbuk, yangi terminal: Ctrl+Alt+T):**
```
cd ~/networking
python3 rtsp_client.py
```
**Camera On** ni bosing.

`rtsp_client.py` dagi manzil Pinky'ga qaratilgan bo'lishi kerak:
```
sed -i 's|^URL = .*|URL = "rtsp://192.168.129.12:8554/test"   # Pinky|' rtsp_client.py
grep "^URL" rtsp_client.py
```

Oddiy GStreamer bilan ko'rish (B noutbukda, OpenCV'siz):
```
gst-launch-1.0 rtspsrc location=rtsp://192.168.129.12:8554/test latency=0 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink sync=false
```

## 9. Ko'p uchraydigan xatolar

| Xato | Sabab | Yechim |
|---|---|---|
| `No such file or directory` (rtsp_server_pinky.py) | Buyruq B noutbukda ishga tushirilgan | Pinky terminalida ishga tushiring (`pinky@raspi:~$`) |
| `Connection refused` | Pinky'dagi server to'xtagan (terminal yopilgan yoki Ctrl+C) | Serverni qayta ishga tushiring, terminalni yopmang |
| `No route to host` (192.168.129.121) | `rtsp_client.py` hali eski laptop A manzilida | URL qatorini Pinky manziliga almashtiring (8-bo'lim) |
| `munmap_chunk(): invalid pointer` | Pinky'da ekran yo'q | Testlarda `fakesink` ishlating |
| `no property "num-buffers"` | `libcamerasrc` bu sozlamani qo'llamaydi | `identity eos-after=30` ishlating |
| Rasm teskari | Kamera teskari o'rnatilgan | `videoflip method=rotate-180` |

## 10. Kechikishni o'lchash

Usul: B noutbukda `python3 clock.py` (millisekundli soat). Pinky kamerasini B ekranidagi soatga qaratamiz va skrinshot olamiz (**Fn + PrtSc**). Kechikish = haqiqiy soat − videodagi soat.

| Qurilma | O'lchovlar | O'rtacha |
|---|---|---|
| Laptop A (1280x720) | 384, 370, 384, 376, 372 ms | ~375 ms |
| **Pinky (640x480)** | 354, 353, 341 ms | **~350 ms** |

Masalan: 15:40:16.591 − 15:40:16.237 = 354 ms.

**Maqsad:** hamshirani kuzatish uchun **200 ms dan kam**. Hozir ~350 ms, demak hali kamaytirish kerak.

## 11. MTU va tarmoq

- MTU (Maximum Transmission Unit): tarmoq bir martada yuboradigan eng katta paket hajmi.
- Pinky: `wlan0` = 1500, `ap0` = 1500, `eth0` = 1500 (kabel ulanmagan).
- B noutbuk: USB Wi-Fi adapter = 1500.
- Wi-Fi uchun 1500 standart va maksimal qiymat. Bitta kadr ~8 KB, ~6 paketga bo'linadi, bu 1–2 ms oladi. **MTU kechikishga deyarli ta'sir qilmaydi, o'zgartirmaymiz.**
- Tekshirish buyrug'i: `ip link show | grep mtu`

**Qaror:** Pinky Wi-Fi'da qoladi (kasalxonada harakatlanadigan robot kabel bilan yura olmaydi).

Taxminlar (hali tekshirilmagan): Pinky bitta Wi-Fi moduli bilan bir vaqtda ham ulanib, ham `ap0` nuqtasini tarqatyapti; B noutbukda USB Wi-Fi adapter. Ikkalasi ham kechikishga biroz qo'shishi mumkin.

## 12. Keyingi qadamlar

- Kechikishni 200 ms dan pastga tushirish: videoni siqish sozlamalari, o'lcham, bufferlar.
- Pinky kadrlarini saqlab, YOLO'da o'qitish (alohida ish).
- Xavfsizlik bilan bog'liq to'xtashlar (to'siq, odam) video B ga borib qaytishini kutmasdan Pinky'ning o'zida ishlashi kerak.
