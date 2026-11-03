# Pinky: hamshirani kuzatish, YOLO va yiqilgan odam alarmi

Sana: 2026-10-16. Fayllar: `pinky_follow.py` Pinky'da ishlaydi, `alarm_server.py` esa laptop B'da ishlaydi.

## Nima qiladi

1. **Marker kuzatish.** Pinky hamshira rasmidagi ArUco markerni (`DICT_4X4_50`, **ID 13**) kuzatadi va undan **10 sm** orqada yuradi. Marker 6 sm dan yaqin bo'lsa, Pinky to'xtaydi.
2. **Marker yo'qolsa.** YOLO **60 soniya** davomida hamshirani (tik turgan odamni) qidiradi. Marker qayta ko'rinsa, Pinky yana marker bo'yicha yuradi. 60 soniyadan keyin ham marker chiqmasa, Pinky to'xtaydi va serverga `TRACKING_FAIL` yuboradi.
3. **Yiqilgan odam.** YOLO pose har 0.5 soniyada tekshiradi. Odam 3 marta ketma-ket yiqilgan holatda ko'rinsa, serverga `FALL_ALARM` boradi. Keyin Pinky odam yo'q tomonga 45° buriladi, 30 sm yuradi, yana avvalgi yo'nalishga qaytadi va markerni qidiradi. Bitta yiqilish uchun alarm 30 soniyada bir martadan ko'p yuborilmaydi.

## Ishga tushirish

**Laptop B'da (1-terminal):**
```
cd ~/networking
python3 alarm_server.py
```

**Pinky'da (2-terminal):**
```
ssh pinky@192.168.129.12
cd ~/networking
python3 -c "import cv2, ultralytics; print(cv2.__version__)"   # xato chiqsa: pip install ultralytics --break-system-packages
ros2 topic list | grep cmd_vel                                  # /cmd_vel chiqishi kerak (Pinky Pro bringup ishlayapti)
python3 pinky_follow.py --no-drive                              # avval motorlarsiz sinov
python3 pinky_follow.py                                         # haqiqiy yurish
```
`rtsp_server_pinky.py` o'chirilgan bo'lishi kerak, chunki kamerani faqat bitta dastur ishlata oladi.

Fayllarni laptop B'dan Pinky'ga ko'chirish:
```
scp ~/networking/pinky_follow.py pinky@192.168.129.12:~/networking/
```

## Avval sozlash kerak bo'lgan 2 narsa

- `MARKER_SIZE_M = 0.03`: markerning qora kvadrati tomonini lineyka bilan o'lchab, metrda yozing (masalan, 2.5 sm = `0.025`).
- **10 sm tekshiruvi:** markerni kameradan aniq 10 sm uzoqlikka qo'ying va `--no-drive` bilan ishga tushiring. `lin` 0 ga yaqin chiqishi kerak. Pinky juda oldinga intilsa `FOCAL_PX` ni kamaytiring, juda tez to'xtasa oshiring.

## Hali sinalmagan narsalar

- Mantiq kompyuterda soxta kamera bilan sinaldi: marker kuzatish, 60 soniya qidiruv, `TRACKING_FAIL`, `FALL_ALARM`, aylanib o'tish va serverga xabar. Haqiqiy Pinky'da, motorlar va YOLO bilan hali sinalmagan.
- Markerni topish sizning rasmingizda ishladi (ID 13).
- Aylanib o'tishda Pinky to'siqlarni ko'rmaydi, faqat yiqilgan odam qaysi tomonda ekaniga qaraydi.
