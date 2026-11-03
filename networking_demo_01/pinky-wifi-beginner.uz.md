# Pinky'ni ikkita WiFi tarmoqqa ulash: yangi boshlovchilar uchun qo'llanma

Koreyscha: [pinky-wifi-beginner.ko.md](pinky-wifi-beginner.ko.md)

Bu qo'llanma Pinky bilan hali hech ishlamagan odam uchun. Har bir qadamni tartib bilan bajaring.

## Nima qilamiz?

Pinky (Raspberry Pi bilan ishlaydigan robot) da ikkita WiFi "antenna" bor:

| Antenna | Nomi Linux'da | Qaysi tarmoqqa | Nima uchun |
|---|---|---|---|
| Ichki WiFi | `wlan0` | `team2_5G` (jamoa router'i) | team2 loyihasi |
| USB WiFi adapter | `wlx588694f526d6` | `FASTCAMPUS_10F` | FASTCAMPUS tarmog'idan Pinky'ga ulanish |

Oxirida Pinky'da **ikkita IP manzil** bo'ladi va ikkala tarmoqdan ham unga `ping` qilish mumkin bo'ladi.

```
 Noutbuk (team2_5G) ──── team2 router ──── wlan0 ─┐
                                                   ├── Pinky
 Noutbuk (FASTCAMPUS) ── FASTCAMPUS_10F ── dongle ─┘
```

## Kerakli narsalar

- Pinky (yoqilgan, batareyasi zaryadlangan)
- USB WiFi adapter (Pinky'ning USB portiga ulangan)
- Pinky'ga kirish usuli: monitor + klaviatura **yoki** u bilan bir tarmoqdagi noutbuk
- Pinky foydalanuvchisi: `pinky`, parolni jamoadan so'rang
- WiFi parollari: `team2_5G` va `FASTCAMPUS_10F` (jamoadan so'rang)

Quyidagi buyruqlarda `<TEAM2_PAROL>` va `<FASTCAMPUS_PAROL>` o'rniga haqiqiy parollarni yozing.

## Asosiy tushunchalar (qisqacha)

- **IP manzil**: tarmoqdagi qurilmaning "uy manzili", masalan `192.168.180.53`.
- **Interfeys**: tarmoqqa ulanadigan qism (antenna). `wlan0`, `wlx...` shular.
- **ping**: "eshityapsanmi?" deb xabar yuborib, javob kutadi. Javob kelsa, ulanish bor.
- **SSH**: boshqa kompyuterdan Pinky terminaliga masofadan kirish.
- **sudo**: buyruqni admin huquqi bilan bajarish. Parol so'rasa, Pinky parolini yozing (yozganda ekranda ko'rinmaydi, bu normal).

---

## 1-qadam. Pinky terminaliga kirish

**A usul: monitor va klaviatura.** Pinky'ga HDMI monitor va USB klaviatura ulang. `pinky` bilan login qiling.

**B usul: SSH.** Noutbuk Pinky bilan bitta tarmoqda bo'lishi kerak. Noutbuk terminalida:

```bash
ssh pinky@<PINKY_IP>
```

Muhim: `pinky@` qismini albatta yozing. Usiz SSH noutbukdagi foydalanuvchi nomingiz bilan kirishga urinadi va parol mos kelmaydi. Birinchi marta `yes/no` so'rasa, `yes` deb yozing.

Terminalda `pinky@raspi:~$` ko'rinsa, Pinky ichidasiz.

## 2-qadam. Interfeyslarni ko'rish

```bash
nmcli device
```

Natijada quyidagilarni toping:
- `wlan0` → ichki WiFi
- `wlx...` bilan boshlanadigan nom → USB adapter. Ko'rinmasa, adapterni chiqarib, qayta ulang va buyruqni takrorlang.
- `ap0` → Pinky'ning o'z hotspoti (`192.168.4.1`), unga tegmaymiz.

## 3-qadam. Ichki WiFi (`wlan0`) → `team2_5G`

⚠️ Agar hozir `wlan0` orqali SSH qilgan bo'lsangiz, bu qadamdan keyin SSH uziladi. Bu qadamni monitor va klaviatura bilan bajarish xavfsizroq.

**3.1. Tarmoqlarni qidirish.** Bu majburiy, aks holda `No network found` xatosi chiqishi mumkin:

```bash
sudo nmcli device wifi rescan ifname wlan0
nmcli device wifi list ifname wlan0 | grep -i team2
```

Ro'yxatda `team2_5G` ko'rinishi kerak.

**3.2. Ulanish:**

```bash
sudo nmcli device wifi connect "team2_5G" password "<TEAM2_PAROL>" ifname wlan0 name team2-router
```

`successfully activated` chiqsa, ulandi.

**3.3. Eski FASTCAMPUS profilini o'chirish.** Agar `wlan0` avval FASTCAMPUS'ga ulangan bo'lsa, qayta yoqilganda unga qaytmasligi uchun:

```bash
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
```

(`unknown connection` desa, bunday profil yo'q, bu normal.)

## 4-qadam. USB adapter → `FASTCAMPUS_10F`

Eslatma: bu adapter faqat **2.4 GHz** tarmoqlarni ko'radi. `FASTCAMPUS_10F` unga mos.

**4.1. Tarmoqlarni qidirish:**

```bash
sudo nmcli device wifi rescan ifname wlx588694f526d6
nmcli device wifi list ifname wlx588694f526d6 | grep FASTCAMPUS
```

**4.2. Ulanish:**

```bash
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<FASTCAMPUS_PAROL>" ifname wlx588694f526d6 name fastcampus-dongle
```

**4.3. Pinky qayta yoqilganda avtomatik ulansin:**

```bash
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection modify team2-router connection.autoconnect yes
```

## 5-qadam. IP manzillarni tekshirish

```bash
ip -br addr
```

Taxminiy natija:

```
wlan0            UP   192.168.180.53/24 ...
wlx588694f526d6  UP   192.168.129.116/17 ...
ap0              UP   192.168.4.1/24
```

`wlan0` va `wlx...` ikkalasida ham IP bo'lsa, Pinky ikkala tarmoqqa ulangan. Bu IP'larni yozib oling.

⚠️ IP'larni router beradi. Pinky qayta yoqilganda ular o'zgarishi mumkin, shuning uchun har gal shu buyruq bilan tekshiring.

## 6-qadam. Pinky ichidan ping

Har bir antenna orqali internet bormi?

```bash
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8
```

- `-I wlan0`: xabarni aynan shu antenna orqali yubor
- `-c 4`: 4 marta yubor
- `8.8.8.8`: Google serveri

`4 received, 0% packet loss` chiqsa, yaxshi.

## 7-qadam. Noutbukdan Pinky'ga ping

Noutbuk qaysi WiFi'da bo'lsa, Pinky'ning **o'sha tarmoqdagi** IP'siga ping qiling.

Noutbuk qaysi WiFi'da ekanini bilish:

```bash
nmcli -t -f active,ssid dev wifi | grep '^yes'
```

| Noutbuk ulangan tarmoq | Ping qilinadigan manzil |
|---|---|
| `team2_5G` | `wlan0` IP'si, masalan `ping -c 4 192.168.180.53` |
| `FASTCAMPUS_10F` | dongle IP'si, masalan `ping -c 4 192.168.129.116` |

`0% packet loss` chiqsa, hammasi tayyor! 🎉

SSH ham shu manzil bilan ishlaydi: `ssh pinky@192.168.180.53` yoki `ssh pinky@192.168.129.116`.

---

## Muammolar va yechimlar

| Xabar / belgi | Sabab | Yechim |
|---|---|---|
| `No network with SSID ... found` | Scan qilinmagan, yoki tarmoq uzoqda | `sudo nmcli device wifi rescan ifname <interfeys>` dan keyin qayta urining |
| `Secrets were required` | WiFi paroli xato | Parolni tekshiring |
| USB adapter `team2_5G` ni ko'rmaydi | Adapter faqat 2.4 GHz | `team2_5G` ni ichki WiFi'ga ulang (yoki adapterni `team2_2_4G` ga) |
| `Destination Host Unreachable` (noutbukdan) | Noutbuk va Pinky boshqa-boshqa tarmoqda, yoki IP o'zgargan | 5- va 7-qadamdagi jadvalni tekshiring |
| SSH `zubayda@...'s password` deb so'raydi | `pinky@` yozilmagan | `ssh pinky@<IP>` |
| `wlx...` interfeysi yo'q | Adapter tanilmagan | Qayta ulang; `lsusb` bilan tekshiring |
| SSH birdan uzildi | SSH o'tgan interfeys boshqa tarmoqqa ko'chdi | Pinky'ning boshqa IP'si orqali yoki monitor bilan kiring |

## Qisqa xulosa (barcha buyruqlar)

```bash
# Pinky'da
nmcli device
sudo nmcli device wifi rescan ifname wlan0
sudo nmcli device wifi connect "team2_5G" password "<TEAM2_PAROL>" ifname wlan0 name team2-router
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
sudo nmcli device wifi rescan ifname wlx588694f526d6
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<FASTCAMPUS_PAROL>" ifname wlx588694f526d6 name fastcampus-dongle
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection modify team2-router connection.autoconnect yes
ip -br addr
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8

# Noutbukda
ping -c 4 <Pinky_IP>
ssh pinky@<Pinky_IP>
```
